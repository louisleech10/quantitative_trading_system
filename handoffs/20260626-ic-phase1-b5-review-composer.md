# IC Phase 1 B5 — Independent Code Review (Composer)

**Reviewer**: Composer 2.5 (adversarial)  
**Date**: 2026-06-26  
**Scope**: Task 3.2 API versioning (`ICResultV2Response`, `ic_response_v2`, route Query, `get_result` branch, subroute regression)  
**SPEC/TODO**: `docs/IC_PHASE1_CONTRACT_TODO.md` Task 3.2  
**Files reviewed**: `api/routes/ic_analysis.py`, `api/services/ic_analysis_service.py`, `api/models/ic_models.py`, `api/core/config.py`, `tests/api/test_ic_response_v2.py`

---

## Verdict

**PASS WITH FINDINGS** — B5 gate tests全部通過；T2/T3/T6 核心契約已落地。有 3 項 **NON-BLOCKING** 與 1 項 **KNOWN-DEBT（B5 範圍外但影響 v2 可用性）**，建議 B6 或 pipeline 接線時追蹤。

---

## 驗證執行

| Check | Result |
|-------|--------|
| `pytest tests/api/test_ic_response_v2.py -v` | **6/6 PASS** |
| `grep -rE "from api\." momentum/` | **0 matches** |
| 前端 IC v2 改動 | **無**（`schema_version` 僅 Feature Factory 既有欄位） |
| `ICArtifactQueryParams` HTTP route | **未實作**（符合 Phase 3 defer） |
| v1 刪除 | **無** |

---

## Findings（依嚴重度）

### F1 [NON-BLOCKING · T6] Export 子端點改測 service，略過 route 層

**證據**：`test_flag_off_subroutes_unchanged` 對 decay/quantile/correlation/grouped 走 TestClient HTTP；export 改為直接呼叫 `ic_analysis_service.export_analysis(..., "json")` 並手動 drain `BytesIO`（L262–273）。

**分析**：
- **內容路徑**：`export_analysis` 從 `task_info["result"]` 讀 raw report，**從未經** `get_result` / `_to_json_compatible`。與 decay 等子端點（經 `get_result` 取子鍵）不同。對「flag-off 匯出 JSON 內容不變」而言，測 service 是合理 SSOT。
- **仍漏測的 route 層**：`StreamingResponse` 包裝、`Content-Disposition` header、`FileResponse` vs bytes 分支、404/422 狀態碼映射。TestClient hang 根因未在測試中記錄修復（如 `stream()` bounded read）；若 route 在 generator/headers 有 regression，現有測試抓不到。
- **預存風險（非 B5 引入）**：實測當 `task_info["result"]` 含 `ICResult` dataclass（非 dict）時，`export_analysis(..., "json")` 的 `json.dumps(report)` **會 TypeError**；baseline fixture 是純 dict 故測試綠。與 `get_result` 的 normalize 路徑不一致——真實 in-memory completed task 可能 export 失敗而 `/result` 正常。

**建議**：B6 補一條輕量 route 測試：`TestClient.get(..., "/export/{id}/json")` 用 `timeout` 或 `stream()` 讀固定 byte cap，至少驗 200 + `Content-Disposition` + body hash；或 mock `StreamingResponse` 為 bytes 回傳的 thin wrapper test。

---

### F2 [NON-BLOCKING · SSOT / 規模] v2 `read()` 全表載入記憶體

**證據**：`_build_v2_result` L315 `rows = create_ic_artifact_writer().read(artifact_path)` 無 `page`/`filters`；`read()` 在 `limit is None` 時 `rows.extend` 全 batch（`ic_artifact_writer.py` L126–127）。

**影響**：回應體僅 `top_n_summary[:N]`（bounded），但 **peak RSS 隨 artifact 總列數成長**，與 3.1 T5「O(page)」精神在 **API read path** 不一致。大 run（90k+ features）可能 OOM。

**建議**：Phase 1 可接受若文件化；後續 v2 應 `read(..., page=...)` 或 metadata 檔提供 `total_features`，top-N 用 sorted scan / predicate。

---

### F3 [NON-BLOCKING · SSOT] `top_n` 未從真實 analyze 請求持久化

**證據**：`_resolve_v2_top_n` 讀 `task_info["deep_analysis_top_n"]` / `deep_analysis_request`；`start_analysis` / `_run_deep_analysis` **未寫入** 這些欄位。僅測試 fixture 人工設 `deep_analysis_top_n: 3`。

**影響**：生產路徑 v2 永遠用 `DeepAnalysisRequest().top_n == 30`，即使用戶在 `ICAnalyzeRequest.deep_analysis_config.top_n` 設了其他值。

**對照 TODO**：Task 3.2 寫「N=現有 DeepAnalysisRequest.top_n 預設 30」——預設值合規，但 **negotiation 與使用者配置未接線**。

---

### F4 [KNOWN-DEBT · 範圍外] Artifact 未在 IC 主流程自動寫入

**證據**：repo 內僅測試 `_write_ranked_artifact` 建立 parquet；`start_analysis` / `_run_analysis` 無 `ic_artifact_writer.write`。`test_no_artifact_uri_none` 覆蓋無檔案時 v2 空 envelope。

**影響**：`IC_RESPONSE_V2=true` + `?schema_version=2` 在真實 completed task 上 **預期多數回** `{schema_version:2, top_n_summary:[], artifact_uri:null, total_features:0}`，直到 pipeline/1a 接線（HANDOFF B3 殘留）。

**判定**：非 B5 契約違反（B5 只定義 read path + negotiation），但 **v2 功能在 E2E 上尚不可用**。

---

## 逐項 Adversarial 核查

### 1. Flag-off byte 不變（T2 / G1 紅線）

| 檢查項 | 結論 |
|--------|------|
| `ic_response_v2=False` → v1 | ✅ `get_result` L296–297 早退 `normalized` |
| 無 `schema_version` → v1 | ✅ `schema_version != 2` |
| `flag off + ?schema_version=2` → v1 | ✅ 同條件；`test_route_v2_negotiation` deep-equal baseline |
| v2 欄位洩漏 | ✅ v1 path 不呼叫 `_build_v2_result`；v2 鍵不出現在 flag-off 回應 |
| `eval_status` 剔除 | ✅ `_to_json_compatible` L1208–1209 對 `ICResult` 且 `ic_response_v2=False`（目前所有 call site 皆預設 False）pop 鍵；`test_flag_off_get_result_no_eval_status_key` 遞迴掃描 + baseline deep-equal |
| 鍵集合/值/None | ✅ `test_flag_off_deep_equal_baseline`：HTTP `/result` vs B0（剔 `generated_at`）全等 |
| 字面 byte 不變 | ⚠️ 測試為 **parsed JSON deep-equal**，非 raw response bytes；符合 TODO G1 白名單定義，非 wire-format byte identity |

**子端點**：decay/quantile/correlation/grouped 在 flag-off 下 hash 不變（`test_flag_off_subroutes_unchanged`）。皆呼叫 `get_result(task_id)` **不帶** `schema_version`，即使全域 flag on 仍走 v1（L220/239/258/274）。

**`get_summary`** L183 亦無 schema_version → v1。✅

---

### 2. v2 negotiation（T3）

```63:66:api/routes/ic_analysis.py
async def get_result(task_id: str, schema_version: Optional[int] = Query(None)):
    ...
    result = ic_analysis_service.get_result(task_id, schema_version)
```

| 情境 | 預期 | 實測 |
|------|------|------|
| flag on + `?schema_version=2` | v2 | ✅ |
| flag on 無參 | v1 | ✅ |
| flag off + `?schema_version=2` | v1 | ✅ |

Route **確實**把 Query 傳入 service。`/result` 無 `response_model`，允許 v1 dict / v2 envelope 雙形狀。✅

邊界：`schema_version` 非 2（0/1/3）皆落 v1（`!= 2`）；未單測但邏輯正確。

---

### 3. SSOT（artifact 衍生）

| 項目 | 結論 |
|------|------|
| `top_n_summary` 來源 | ✅ parquet `read` → `_sort_artifact_rows(..., "icir")` → `[:top_n]`；**非** `summary_table` 重算 |
| `test_v2_top_n_derived_from_artifact` | ✅ 與 artifact 排序後前 N 列全等 |
| `total_features` | ✅ `len(rows)` 全表列數（非 top_n 長度） |
| artifact 路徑冪等 | ✅ `{task_id}_{config_hash}_v2.parquet`；`config_hash` 來自 `req_config_hash` 或 `metadata.config_hash`，不猜測 |
| 無 artifact | ✅ 明確空狀態；`test_no_artifact_uri_none` |
| `ICArtifactQueryParams` | ✅ 僅 model（L58–64 `ic_models.py`），未掛 HTTP；`sort_by` 未接入 `_build_v2_result`（硬編碼 icir，符合 Phase 1） |

---

### 4. 子端點回歸（T6）與 export 測試修法

見 **F1**。衰減/分位/相關/分組：**未弱化**（HTTP + `_hash_json`）。Export：**驗證強度下降在 transport 層**，service 內容回歸仍有效。

---

### 5. 範圍與解耦

- 不改前端 IC：✅  
- 不刪 v1：✅  
- HTTP 篩選端點未實作：✅（`ICArtifactFilter` + `ICArtifactQueryParams` 備妥）  
- `grep -r "from api." momentum/`：✅ 0  

---

## 契約對照摘要（Task 3.2）

| TODO 要求 | 狀態 |
|-----------|------|
| `ic_response_v2` Settings 預設 False | ✅ |
| route Query → service | ✅ |
| flag-off v1 鍵集合不變 | ✅（測試覆蓋） |
| v2 = top-N + artifact_uri + total_features | ✅ |
| artifact 路徑冪等 | ✅ |
| 子端點 matrix regression | ⚠️ export route 層見 F1 |
| `ICArtifactQueryParams` model only | ✅ |

---

## Reviewer 建議（非阻擋合併）

1. **B6**：補 export route smoke（bounded stream）+ 記錄 TestClient hang 根因。  
2. **Pipeline 接線**（B3 殘留）：completed analysis 寫 `{task_id}_{config_hash}_v2.parquet`，否則 v2 僅測試可用。  
3. **可選**：`start_analysis` 持久化 `deep_analysis_config.top_n` 至 `task_info` 供 `_resolve_v2_top_n`。  
4. **可選**：v2 read path 分頁或 metadata `row_count`，避免全表載入。

---

## ASSUMPTIONS_VERIFIED

- Route L66 轉發 `schema_version`（源碼）  
- v1 gate 條件 `not ic_response_v2 or schema_version != 2`（源碼 L296–299）  
- `pytest tests/api/test_ic_response_v2.py` 6/6 PASS（本機 2026-06-26）  
- `export_analysis` 對 in-memory `ICResult` 會 TypeError（本機 python one-liner）  
- `momentum/` 無 `from api.` import（grep）  

## TESTS_RUN

`pytest tests/api/test_ic_response_v2.py -v --tb=short` → **PASS (6)**  
`grep -rE "from api\." momentum/` → **0 matches**

## FAILURES_SEEN

none（review 過程無失敗）

## SCOPE_CHANGES

none（review-only）

## NUMERIC_OR_SCHEMA_IMPACT

- 新增 v2 envelope（`schema_version=2` 時）；flag-off 無 schema 變更（G1 測試背書）  
- v1 路徑剔除 `eval_status`（B2 延續，B5 測試覆蓋）

---

STATUS: DONE
