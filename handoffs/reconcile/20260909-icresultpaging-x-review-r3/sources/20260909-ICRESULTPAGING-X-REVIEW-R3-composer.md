brief-kind: review
task-id: 20260909-ICRESULTPAGING-X-REVIEW-R3
family: composer
findings-round: R3
標的 commit: HEAD（SPEC R2 修訂＋TODO；**尚未實作**）

## Verdict：可派工

R2 群集 Y1–Y6 均已落文件；本輪以同一反例重跑＋獵新洞，**無新 P0／P1**。進 B0 前最後一件必做事：**無**（Task 0.1 依 SPEC／TODO 建 contract＋golden＋`icresult_paging_phase_gate.sh` 即可開工）。

---

## 被當成事實的未驗證假設（§0）

| 前提 | 判定 | 覆核摘要 |
|---|---|---|
| 兩份文件 template | **fact-verified** | `bash scripts/template_check.sh spec\|todo` → TEMPLATE PASS，rc=0 |
| 39k 報告尺度 | **fact-verified** | `jq -c '{st:(.summary_table\|length), meta_keys:(.metadata\|keys\|length)}' …` → `{"st":39346,"meta_keys":39398}` |
| baseline 未漂移 | **fact-verified** | `shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` → 全 OK |
| completed 後三寫點 | **fact-verified** | `grep 'task_info\["result"\] =' api/services/ic_analysis_service.py` → `:1623`（標準 IC 完成）、`:2339`（full-analysis 完成＋deep）、`:2631`（refilter）；Task 1.0 要求三處皆經 `_set_result` |
| 前端無 IC 報告全段 map 掃描 | **fact-verified** | `grep -rn 'Object.keys(report\|Object.entries(report' frontend/src` → 僅 pattern 元件，無 ic-analysis |
| `selection_scope.scope_id` 投影後可讀 | **fact-verified** | 實機 `scope_id` 為字串 scalar；`collection_to_count_paths` 只把 list／dict 子鍵改 `_count`，`survivor_contract.py:598,615` 讀 `.get("scope_id")` 不受影數影響 |
| G-5 三態 gate 腳本 | **blocked-by:Task 0.1** | `scripts/icresult_paging_phase_gate.sh` 尚不存在；SPEC §G G-5／TODO §B 語意已足：pytest 不含尺寸、gate 只轉印 `SIZE=`、BLOCKED 不假綠不紅、B3 要 PASS |
| `response_model` 加 `view` 是否改預設 bytes | **unverified**（Phase 1） | `get_result` 現無 `response_model`（`api/routes/ic_analysis.py:346-353`）；G-1 raw sha 凍結 |

---

## R2 群集複驗（Y1–Y6）

| 群集 | R2 處置 | R3 複驗 | 狀態 |
|---|---|---|---|
| **Y1** G-6 asc 矛盾 | TODO 改 `asc==[A,B,C,D]` | SPEC §G G-6 與 TODO Task 1.1 驗證皆 `[A,B,C,D]`；手算四列（A/B 同值 A<B 名、C/D None 沉底）與三列（0.5/0.9/None）與 §C-8 comparator 一致 | **CLOSED** |
| **Y2** refilter handshake＋snapshot | §C-7＋Task 1.0 `_snapshot_result`＋G-7a/b/c | `POST /refilter?view=light`、revision 丟棄規則已寫；`:2339`＝full-analysis 第三寫點（與 `:1623` 同形，須經 helper）；現行 `refilter` 仍 `return get_result(task_id)`（`ic_analysis_service.py:2637`），實作時加 `view` 分支 | **CLOSED** |
| **Y3** G-5 pytest.fail vs B1 | 獨立探針三態＋gate 轉印 | §G G-5／TODO §B B1：pytest 用 `shape_fixture.json`；尺寸探針 `SIZE_GATE=PASS\|FAIL\|BLOCKED`；B3 收案要 PASS；繞過需跳過 B3 receipt（流程風險，非文件洞） | **CLOSED** |
| **Y4** funnel adapter | `funnel_stage_adapter`＋G-8 | 六 stage 手算（實機 artifact）：`stage0_ingestion {39373,null}`、`feature_filter {39346,39346}`、`stage1_preprocessing {null,null}`、`stage3_event_filter {null,null}`、`stage5_thresholds {39346,2}`（output 為 dict len）、`stage6_redundancy {0,0}`；stage1 無候選鍵，**裁定：維持 null 不從前 stage 推導**（§C-6 iv 已封） | **CLOSED** |
| **Y5** B2 單批＋page 測試 | B2＝2.1+2.2+2.3；page 三案例 | TODO §B／Task 2.3：light＋`featureDetail=null`⇒六圖載入中、golden detail⇒渲染、funnel null⇒不適用；足以擋「light 已開、圖表讀已刪段」 | **CLOSED** |
| **Y6** wildcard＋keep_keys | 一層 `*`、contract 單一來源 | `filter_log.*` 對六 stage 各處理直接子鍵、行為唯一；`metadata.selection_scope` list→`_count` 後 `scope_id` 仍為字串 | **CLOSED** |

---

## 必答（成對）

### 1a／1b 預設 `/result` 位元組級不變

- **1a**：`view is None` 時誤跑 `project_light_view`、對 live dict 做 `pop`、或加 `response_model` 觸發 pydantic 重序列化、或 `deny_factor_in_ok_oos` 順序／突變改值。
- **1b**：**能**——G-1 `raw_body_sha256`＋mutation P6；抓不到純 OpenAPI 描述漂移。

### 2a／2b light 刪段＋metadata

- **2a**：**當下無**——39k 頂層 metadata 鍵為 `symbol,timeframe,config_hash,event_filter,fit_mode,selection_scope,survivor_output`（probe `meta_keys_present`）；前端 IC 讀 `metadata.period_alignment`／`isolation` 等皆在 `metadata_keep_keys` 聯集；`ExportButtons` 讀頂層 `module_statuses`（G-4d 保留）。
- **2b**：若漏做 `collection_to_count_paths`，`filter_log` 內 `winsorized_features`（1.6MB 級）或 `metadata.selection_scope` 兩 list 會讓 light 遠超 262144；七段已在 `drop_sections`。

### 3a／3b 排序

- **3a**：後端 `sort_policy`（缺值兩向沉底＋`feature_name` 次鍵）與現 `getSortValue`（非有限→`-Infinity`、tie=0）**不同序**；39k `icir` 全 null ⇒ 前端插入序 vs 後端字母序。
- **3b**：**後端為準**（§C-8 明文行為變更；G-2／G-6）。

### 4a／4b refilter／競態

- **4a**：G-2 要求同 `result_revision`；不符 409；G-7a 交錯；G-7b 投影中途 refilter 不混代；G-7c `POST /refilter?view=light`；前端 abort＋丟棄 revision 不符回應。
- **4b**：無版本戳 ⇒ 跨代混頁、勾選 Set 與倖存者不一致、G-2 不可證偽。

### 5a／5b 匯出

- **5a**：**既有** `export_analysis` 讀全量 `task_info["result"]`（`ic_analysis_service.py:1889-1900`）；Task 2.3 明寫零改 `/export`；逐頁 summary **不應**取代。
- **5b**：39k 逐頁 HTTP 為分鐘級；本票已刪該路徑，UAT 用既有 export。

### 6 ≥10× 不必要複雜

**無**。14 特徵全量 golden（不抽樣）＋39k 尺寸探針不進 repo＋contract JSON 為 Rule 5 必要；mutation P1–P11 對應 G-1–G-8。

### 7 B2／IP-RESID

- **交付**：R2 已併 B2 單批（2.1+2.2+2.3）＋page 整合三案例——風險小於拆分。
- **IP-RESID-1/2**：`blocked-by` 落檔格式成立。
- **IP-RESID-3**：並存＋Task 1.3 四格矩陣成立。
- **IP-RESID-4**（keep_keys）：`blocked-by:Task 0.1`，探針改讀 contract 後收；漏斗鍵名已收回 Task（§N 末行註記「原 IP-RESID-4」）。

---

## §1 必查摘要

1. 矛盾/互斥：**無**（Y1 已修）
2. 漏項/端到端：無
3. 不可測驗收：無（G-1～G-8＋三態 G-5）
4. 可疑 quant 假設：無
5. 過度工程：無
6. OOM/並行：無新洞
7. Cache：N/A
8. API/相容：IP-RESID-3 四格矩陣已列
9. 測試品質：B2 page 整合＋G-7b/P10 覆 snapshot
10. Agent 可執行性：Task 精確到檔案
11. 必要性/短命工：無白工（Task 2.3 匯出零改）

---

## COMPOSER-R3-P3-00

**斷言**: 本輪逐項核對 Y1–Y6 與必答 1–7 後無新 P0／P1 finding；R2 修訂已閉合，可派工 B0。

**碼證**: `bash scripts/template_check.sh spec docs/ICRESULT_PAGING_SPEC.md`／`todo docs/ICRESULT_PAGING_TODO.md` → TEMPLATE PASS rc=0；`jq -c '{st:(.summary_table|length), meta_keys:(.metadata|keys|length)}' data_cache/reports/ic_report_ic_gatekeeper.json` → `{"st":39346,"meta_keys":39398}`；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` → 全 OK；G-6 手算四列／三列與 SPEC/TODO 一致；`venv/bin/python handoffs/_light_size_probe.py` → `light_bytes 28019`；漏斗六 stage 手算與 G-8 敘述一致（含 `stage3_event_filter {null,null}`）；`grep task_info\["result"\]` 三寫點 `:1623/:2339/:2631`。

**來源摘要**: docs/ICRESULT_PAGING_SPEC.md#c4f915ce880b

[NONE] 信心度=High；Y1 G-6 SPEC/TODO 已同 `[A,B,C,D]`；Y2 §C-7 handshake＋三寫點含 full-analysis；Y3 G-5 三態與 B1/B3 分工清楚；Y4 funnel 候選鍵序對實機六 stage 可重現、stage1 維持 null；Y5 B2 單批＋page 三案例足擋退化中間態；Y6 wildcard 一層規格對六 stage 唯一、`scope_id` 投影後仍 scalar。

---

ASSUMPTIONS_VERIFIED: template_check×2 rc=0；jq 39346/39398；baseline sha 全 OK；light probe 28019；三 result 寫點；filter_log 六 stage 鍵＋funnel 手算；selection_scope.scope_id scalar；grep 前端無 IC 全段 map；export 路徑 1889+
TESTS_RUN: `bash scripts/template_check.sh spec|todo` rc=0；`jq` 形狀；`shasum -a 256 -c handoffs/20260909-icresult-r3-baseline.sha` rc=0；`venv/bin/python handoffs/_light_size_probe.py`；`jq` filter_log types；grep／讀碼
FAILURES_SEEN: none
SCOPE_CHANGES: none（唯讀審查）
NUMERIC_OR_SCHEMA_IMPACT: none

產出: `handoffs/20260909-ICRESULTPAGING-X-REVIEW-R3-composer.md`

STATUS: DONE
