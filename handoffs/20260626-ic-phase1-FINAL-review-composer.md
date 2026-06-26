# IC Phase 1 B0–B6 — Final Holistic Code Review (Composer)

**Reviewer**: Composer 2.5（非實作者）  
**Date**: 2026-06-26  
**Scope**: 1-contract 完整實作 B0–B6（含未追蹤檔 + 已修改 7 檔 git diff）  
**Prior reviews**: B3/B4/B5 已獨立 review；本輪補 B1/B2/B6 + export 共用路徑 + 整體一致性  
**SPEC/TODO**: `docs/IC_PHASE1_CONTRACT_SPEC.md`, `docs/IC_PHASE1_CONTRACT_TODO.md`

---

## Verdict

**COMMIT-READY — PASS WITH FINDINGS**

Phase 1 契約層目標（B0 baseline、B1 DTO、B2 eval_status、B3 split/leakage、B4 artifact、B5 v2 negotiation、B6 G3 golden + export route）已落地且測試覆蓋到位。**無 BLOCKING 正確性/洩漏/解耦問題**。已知債務（pipeline 未接線、v2 E2E 空 envelope、v2 read 全表 RSS）已在 HANDOFF 與 B4/B5 review 標記，**不阻 commit**；建議 commit 訊息或 Phase 1a follow-up 明列。

---

## 驗證執行

| Check | Command / 方法 | Result |
|-------|------------------|--------|
| Phase1 聚焦測試 | `pytest tests/momentum/core/ tests/momentum/Analysis/test_ic_artifact.py tests/momentum/Analysis/test_ic_split_adapter.py tests/golden/ic_phase1_contract/ tests/api/test_ic_response_v2.py -q` | **61/61 PASS** |
| 解耦 Rule 1 | `grep -rE "from api\." momentum/` | **0 matches** |
| 解耦腳本 | `./scripts/check_decoupling_phase4.sh` | **PASS**（135 Strategy tests） |
| Git diff 範圍 | 7 modified + ~20 untracked（契約/測試/handoff） | 已全讀 |

---

## 1. B1 — Contract DTO（`momentum/core/contracts.py`）

### 1.1 四個 frozen dataclass

| 型別 | 要點 | 判定 |
|------|------|------|
| `SplitPlan` | `split_label`/`index_kind`/`purge_semantic` discriminator、`base_universe_hash` 必填、`__post_init__` purge_gap 邊界 | ✅ |
| `RowMaskPlan` | `to_mask`/`from_mask` roundtrip、`length` 與 `base_len` 守恆 | ✅ |
| `SelectionScope` | `evaluated_features ⊆ universe_features`、`n_tests` 一致 | ✅ |
| `AlignmentSpec` | pandas `freq` 驗證、`validate_alignment` → `NotImplementedError("1-align 落地")` | ✅（Phase 1 stub 符合 SPEC） |

### 1.2 B1 Findings

| ID | 嚴重度 | Finding |
|----|--------|---------|
| F-B1-1 | **INFO** | `ICResult` 仍為**非 frozen** `@dataclass`（既有型別）；B1 新增契約皆 `frozen=True`。不影響 Phase 1，但長期可考慮統一。 |
| F-B1-2 | **MINOR** | `ic_split_adapter.py` 直接 import `contracts` 內 **private** helper（`_coerce_timestamp_array`、`_normalize_symbol_*`）。功能正確，但把內部 helper 變成 de-facto public API；後續 refactor 易碎。建議 1a 收斂為 module-level public helper 或同檔案共用函式。 |
| F-B1-3 | **INFO** | `split_per_symbol` 開頭 `data.copy()` — 大 frame 記憶體翻倍；契約層可接受，接主 pipeline 時需評估。 |
| F-B1-4 | **INFO** | `validate_alignment` 為 dead stub（刻意）；測試 `test_alignment_contract.py` 僅驗 spec 欄位與 `NotImplementedError`。 |

**B1 測試**：`test_split_contract.py`（含真實 kline）、`test_rowmask_contract.py`、`test_scope_contract.py`、`test_alignment_contract.py` — 覆蓋 discriminator、fail-closed、roundtrip。

---

## 2. B2 — EvaluationStatus + v1 序列化剔除

### 2.1 契約

```python
class EvaluationStatus(str, Enum):
    EVALUATED = "evaluated"
    NOT_EVALUATED = "not_evaluated"
    SKIPPED = "skipped"
    UNKNOWN_LEGACY = "unknown_legacy"
```

- `ICResult.eval_status` 預設 `UNKNOWN_LEGACY` — 建構向後相容 ✅  
- `filter_evaluated()` 僅保留 `EVALUATED` ✅  

### 2.2 Flag-off 剔除路徑

`api/services/ic_analysis_service.py::_to_json_compatible`：

- 對 `isinstance(value, ICResult) and not ic_response_v2` → `payload.pop("eval_status", None)`  
- `get_result` 呼叫 `_to_json_compatible(result)` **未傳** `ic_response_v2=True` → v1 路徑恆剔除 ✅  
- v2 路徑走 `_build_v2_result`（artifact SSOT），不經 ICResult JSON 序列化 ✅  

### 2.3 B2 Findings

| ID | 嚴重度 | Finding |
|----|--------|---------|
| F-B2-1 | **INFO** | `_to_json_compatible(..., ic_response_v2=True)` **無任何 caller**；`eval_status` 保留路徑為預留，目前死參數分支。 |
| F-B2-2 | **MINOR** | 剔除僅針對 **`ICResult` dataclass 實例**；若未來 result dict 手寫 `"eval_status"` 鍵，v1 不會自動剔除。現有 baseline 為純 dict 無該鍵；`test_flag_off_get_result_no_eval_status_key` 用 dataclass 注入驗證。 |
| F-B2-3 | **INFO** | 主 IC pipeline **尚未**在計算端設定 `eval_status=EVALUATED`；全 run 預設 `UNKNOWN_LEGACY` 直到 1a 接線。符合 Phase 1 opt-in 範圍。 |

---

## 3. B6 — G3 golden + export route

### 3.1 G3 `test_split_leakage_golden.py`

- 真實 `data_cache/feature_klines/kline_cache.h5` BTC+ETH 1h ✅（符合三方簽核鐵律）  
- 正例：`validate_split_integrity` + symbol purity  
- 反例：`CrossSymbolLeakageError`（sorted multi-symbol）、`TimestampDiscontinuityError`（gap/unsort/duplicate）  
- `test_split_per_symbol_golden`：每 symbol 獨立 splitter、expected global row indices、purge 不跨界 ✅  

### 3.2 Export route 改動審查（`api/routes/ic_analysis.py`）

**變更**：`type == "bytes"` 時由 `StreamingResponse(BytesIO)` 改為 `Response(content=getvalue())`；`type == "file"` 仍 `FileResponse` 不變。

| 問題 | 結論 |
|------|------|
| 是否影響其他 export caller？ | **僅 IC** `/export/{task_id}/{format}`。`feature_factory.py` 自有 `StreamingResponse`，未改。 |
| Content-Disposition / media_type | ✅ 同一 `headers` dict；`test_export_route_streaming` 驗 200 + `content-disposition` + body `{` 前綴 |
| FileResponse 分支 | ✅ `hdf5` 格式 `type: "file"` 走 L353–357，未觸碰 |
| 大檔 OOM vs streaming？ | **無新增 OOM 風險**：`export_analysis` 早已 `json.dumps(...).encode()` / `BytesIO(...)` **全量 materialize**；舊 `StreamingResponse(BytesIO)` 並非真 streaming。瓶頸在 service 層記憶體，非 route 層。極大 report 風險為**預存**，非 B6 引入。 |
| TestClient hang | ✅ 根治；`test_export_route_streaming` bounded `iter_bytes` 2s deadline PASS |

| ID | 嚴重度 | Finding |
|----|--------|---------|
| F-B6-1 | **MINOR** | Route L372–376 `StreamingResponse` **fallback 已 unreachable**：`export_analysis` 僅回 `"bytes"` 或 `"file"`。可刪除或留註解「保留給未來 stream type」；否則為 dead code。 |
| F-B6-2 | **INFO**（沿用 B5 F1） | `export_analysis` 對 raw `report` 做 `json.dumps(report)` **不經** `_to_json_compatible`；若 in-memory result 含 `ICResult` dataclass 會 TypeError。Baseline 為 dict；與 `get_result` 路徑不一致——**預存風險**，非本批 regression。 |

---

## 4. 整體一致性（B1–B6 DTO / eval_status 語義）

### 4.1 eval_status 跨層對照

| 層 | 型別 | 值域 |
|----|------|------|
| B2 `EvaluationStatus` | `Enum` | `evaluated` / `not_evaluated` / `skipped` / `unknown_legacy` |
| B2 `ICResult.eval_status` | `EvaluationStatus` | 同上 |
| B4 `ICArtifactSchema.eval_status` | `str` | `str(result.eval_status.value)` via `build_ic_artifact_rows` |
| B4 Parquet `eval_status` | Arrow `string` | 與上同 |
| B5 `ICArtifactFilter.eval_status` | `Optional[str]` | 未綁 enum（HTTP 端點 deferred） |

**語義一致** ✅：`ICArtifactSchema` 是 `ICResult.eval_status` 的字串投影；`filter_evaluated` 與 artifact 寫入使用同一 enum 來源。

### 4.2 命名對照

| 概念 | B1 | B4 artifact |
|------|-----|-------------|
| FDR 範圍 ID | `SelectionScope.scope_id` | `selection_scope_id` |
| Universe 身份 | `base_universe_hash` | 同欄位名 |
| Split 標籤 | `SplitPlan.split_label` | `SelectionScope.split_label` |

**一致** ✅；`scope_id` → `selection_scope_id` 前後綴差異有文件意圖（artifact 欄位扁平化）。

### 4.3 schema_version 雙軌（刻意）

- API `ICResultV2Response.schema_version = 2`（HTTP 協商）  
- Artifact `ICArtifactSchema.schema_version = 1`（Parquet 檔案格式）  

不同 namespace，**非 bug**；但 commit 後建議在 SPEC 加一句避免消費者混淆。

---

## 5. 解耦與 opt-in 範圍

| 規則 | 狀態 |
|------|------|
| `momentum/` 不 import `api/` | ✅ 0 matches |
| 引擎經 `factories.py` | ✅ `create_ic_split_adapter`, `create_ic_artifact_writer` |
| DTO 邊界 | ✅ 契約在 `momentum/core/contracts.py`；API models 在 `api/models/` |
| 契約未接主 pipeline | ✅ `start_analysis` / `_run_analysis` 無 split adapter / artifact write；HANDOFF B3 殘留④ 明列 1a 接線 |

**API → momentum 依賴**（允許）：`ICResult` 用於 `_to_json_compatible` isinstance；`create_ic_artifact_writer` 用於 v2 read path。

---

## 6. 跨批次 regression / dead code 掃描

| 項目 | 判定 |
|------|------|
| Flag-off v1 byte 不變（G1） | ✅ `test_flag_off_deep_equal_baseline` + `test_flag_off_subroutes_unchanged` |
| 子端點 decay/quantile/correlation/grouped | ✅ hash 不變 |
| v2 negotiation 雙向 | ✅ flag on + `?schema_version=2` vs flag off 強制 v2 query |
| B3 洩漏（L1–L6） | ✅ 三方簽核 PASS（`b3-FINAL-SIGNOFF`）；本輪未重審 adapter 實作細節 |
| Dead: `validate_alignment` stub | 刻意 |
| Dead: `ICArtifactQueryParams` HTTP | Phase 3 defer |
| Dead: `StreamingResponse` export fallback | F-B6-1 |
| Dead: `ic_response_v2=True` in `_to_json_compatible` | F-B2-1 |
| Dead: factory `create_ic_split_adapter` in production path | opt-in；僅測試/adversarial 使用 |

**未見本批引入的測試斷言弱化或 gate 放寬。**

---

## 7. 沿用 B4/B5 已知債務（非本輪 BLOCKING）

| 來源 | 摘要 |
|------|------|
| B4 F-G2 | `ICArtifactSchema` float 非 Optional vs Parquet nullable — dict 直寫可產 null |
| B5 F2 | `_build_v2_result` `read()` 全表入 RAM；top-N  bounded 但 peak RSS 隨列數成長 |
| B5 F3 | `_resolve_v2_top_n` 未從 `start_analysis` 請求持久化；生產預設 30 |
| B5 F4 | Artifact 未在 IC 主流程自動寫入；`IC_RESPONSE_V2=true` E2E 多為空 envelope |
| HANDOFF | ICSplitAdapter `allowed_symbols` / `expected_freq` 接線、1a pipeline 整合 |

---

## 8. 建議 commit 前 checklist

- [x] 61 Phase1 聚焦 pytest PASS  
- [x] 解耦 grep + phase4 script PASS  
- [x] G1 baseline `generated_at` 剔除 deep-equal  
- [x] G3 真實 kline golden  
- [ ] （可選）刪除 unreachable `StreamingResponse` export fallback（F-B6-1）  
- [ ] （可選）文件一句澄清 API schema_version 2 vs artifact schema_version 1  
- [ ] commit 訊息註明：Phase 1 = contract layer only；v2 / split / artifact **需 1a 接線才 E2E 可用**

---

## ASSUMPTIONS_VERIFIED

- `export_analysis` 所有非 file 格式皆 `type: "bytes"`（grep 證實）；buffered Response 不改記憶體輪廓。  
- `eval_status` 字串值在 `build_ic_artifact_rows` 與 `EvaluationStatus` enum 一致（讀碼 + `test_ic_artifact` 四種狀態 roundtrip）。  
- `momentum/` 零 `from api.`；`ic_split_adapter` / `ic_artifact_writer` 僅依賴 `momentum.core.*`。  
- B6 export route test 在 buffered Response 下 2s 內完成 bounded read。

## TESTS_RUN

- `pytest tests/momentum/core/ tests/momentum/Analysis/test_ic_artifact.py tests/momentum/Analysis/test_ic_split_adapter.py tests/golden/ic_phase1_contract/ tests/api/test_ic_response_v2.py -q` → **61 passed**  
- `./scripts/check_decoupling_phase4.sh` → **PASS**

## FAILURES_SEEN

- none（本 review session）

## SCOPE_CHANGES

- none（read-only review）

## NUMERIC_OR_SCHEMA_IMPACT

- Phase 1 新增契約型別與 opt-in v2 API；**flag-off v1 輸出 byte 不變**（測試證實）。  
- Export route：HTTP 傳輸層由 pseudo-stream 改 buffered；payload 內容不變。

---

**STATUS: DONE**
