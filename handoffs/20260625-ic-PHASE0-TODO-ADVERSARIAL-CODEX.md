## Verdict：需修補後派工

## Findings
[BLOCKING] High  
證據：Task/原文短句：`Phase 測試 + Gate` 寫「Golden [M-5]：grouped per-group IC mean + row mask hash... baseline 存 tests/fixtures/ic_phase0/baseline_*.json」，但 Task 2.1/2.2 只要求 year==2024，Task 3.5 只要求 feature 數與 metadata，Task 4.1 只泛稱 Golden D。  
會怎麼失敗：執行端可寫完 unit tests 卻沒有任何 Task 負責建立/更新/比對 `baseline_grouped_post_timeaxis.json`、`baseline_feature_filter.json`、`baseline_decay.json`；「golden 不 FAIL」會變成空 gate 或人工猜。這直接削弱高風險 (d) 防假綠。  
修法：把 Golden 拆進具體 Task：2.2 負責 grouped baseline + row mask hash/group sizes；3.5 負責 feature_filter sha256 baseline；4.1/4.2 負責 decay structured-float baseline。每項列檔案、fixture、斷言與命令。

[MAJOR] High  
證據：TODO Task 3.1/3.2 原文「include/exclude/pattern/categories/data_sources/families/max_features」；真實 API/TS 欄位是 `include_features`、`exclude_features`、`include_pattern`、`include_categories`、`include_data_sources`、`include_families`、`max_features`。  
會怎麼失敗：冷啟動 agent 可能新增錯誤 schema 欄位或只實作 category/source/pattern，漏掉 `include_features`/`exclude_features`，導致 API 已有能力在 momentum 端仍不生效。  
修法：TODO 改成精確欄位名，並寫明 metadata 映射：column name 對 `include_features/exclude_features/include_pattern`，metadata `category/data_source|source/family` 對 categories/data_sources/families。

[MAJOR] Medium  
證據：§B 寫 B3「無（可與 B1/B2 平行）」；但 B2 與 B3 都改 `momentum/Analysis/ic_config_schema.py`，且 B3 的 batch gate 又要求 `pytest tests/momentum/ tests/api/ -q`。  
會怎麼失敗：若 B3 真平行或先合，會與 B2 同檔衝突；若在 B1/B2 未落地前跑全量 gate，已知 grouped crash/timeaxis/byvol 問題可能讓 B3 無法獨立綠，和「無依賴」矛盾。  
修法：把 B3 標成「可開發平行，但最終全量 gate/合併依賴 B1+B2」；或明確允許 B3 先跑 targeted tests，最終統一 gate 在 B2 後。

[MINOR] High  
證據：Task 4.4 寫 `fetchTaskStatus:194-212` 與 `setError(status.error)`；目前 hook inline type 只含 `{ task_id; status; progress; current_stage? }`，雖後端 status 實際回 `error`。  
會怎麼失敗：實作者只改邏輯不改 TS response type，`vitest`/build 可能卡型別或用 `any` 繞過。  
修法：TODO 補一條：更新 `fetchTaskStatus` response type 加 `error?: string | null`，測 failed poll 顯示該 error。

## 被當成事實的未驗證假設
- 「B3 無依賴可平行」未被驗證；實際有同檔修改與全量 gate forward dependency。
- 「Golden 可由全域 Gate 自然落地」未被驗證；TODO 沒有 Task owner。
- 「feature_filter 欄位 shorthand 足夠」不成立；真實 API/TS 欄位更精確且包含 include/exclude features。

ASSUMPTIONS_VERIFIED: 已核對 TODO/SPEC/reconcile/manifest/review prompt 與指定程式碼；點名行號多數存在且語義相符。  
TESTS_RUN: read-only review；未執行 pytest/npm。  
FAILURES_SEEN: none。  
SCOPE_CHANGES: none。  
NUMERIC_OR_SCHEMA_IMPACT: none by this review。  
HANDOFF_NOT_UPDATED: read-only sandbox；未寫 handoff 檔。  
STATUS: DONE