# Batch Alias SPEC/TODO Adversarial Review r4

## Verdict：PASS（可派工）

本輪按 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0+§1，只讀複審 `docs/BATCH_ALIAS_{SPEC,TODO,MANIFEST}.md`、r3 handoff 與真實程式。r3 唯一 BLOCKING（MultiTFGenerator L7 helper 路徑未穿 batch_id）已由 V4 明確修補；未發現新的 blocking。

## r4 核心複驗：_layer7 呼叫點枚舉

Production `momentum/` 內 `rg -n "_layer7_raw_from_cgsa_pipeline|_layer7_validate_and_persist" momentum` 結果：

- 呼叫點 1：`momentum/FeatureEngineering/feature_factory.py:367` → `_layer7_raw_from_cgsa_pipeline`
- 呼叫點 2：`momentum/FeatureEngineering/feature_factory.py:400` → `_layer7_validate_and_persist`
- 呼叫點 3：`momentum/FeatureEngineering/feature_factory.py:3373` → `_layer7_validate_and_persist_cgsa`
- 呼叫點 4：`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:309` → `_factory._layer7_raw_from_cgsa_pipeline`
- 呼叫點 5：`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:600` → `_factory._layer7_raw_from_cgsa_pipeline`
- 呼叫點 6：`momentum/FeatureEngineering/timeframe/multi_tf_generator.py:1364` → `_factory._layer7_validate_and_persist`

同一 grep 另有三個 helper 定義：`feature_factory.py:3014/3243/3360`。未發現第 7 個 production call site、其他 generator、resume 專用 L7 路徑或別名 import 繞路。全 repo 文字搜尋會命中測試 stub/direct helper tests、archived docs、`scripts/fix_spec_v1_to_v1_1.py` 的舊 SPEC 文字替換片段、以及 `_staging_to_remove` 日誌；這些不是 production runtime 生成路徑。

## V4 Reconcile Check

- r3-BLOCKING multi-TF batch_id 穿透：已修補。SPEC V4 §A/Task 1.1、TODO V4 Task 1.1、MANIFEST [BA-1] 都明確要求 `feature_factory.py:306 generate_multi_tf(..., batch_id)`，並要求 `multi_tf_generator.py:309/:600/:1364` 三處 helper 呼叫傳入 batch_id。
- `generate_multi_tf` 簽名變更：已明確。V4 指定 `timeframe/multi_tf_generator.py generate_multi_tf` 加 `batch_id` 參數，且 multi-TF 生成路徑測試需斷言 registry entry 寫入 batch_id。
- 三 helper 簽名與 registry.add：已明確。V4 要求 `_layer7_raw_from_cgsa_pipeline`、`_layer7_validate_and_persist_cgsa`、`_layer7_validate_and_persist` 加 `batch_id: Optional[str] = None`，並在 registry.add 三處 `feature_factory.py:3197/3342/3474` 用區域參數寫入。
- batch service / resume：已足夠。真實 resume 流程 `resume_batch` → `execute_resume` → `_run_batch` → `_process_item_wave` → `_compute_single` → `generate_features`；V4 指定 `_process_item_wave`/executor 從 `checkpoint["batch_id"]` 傳入 `_compute_single(..., batch_id)`，無另一路 resume 繞過 `generate_features` 的生成路徑。

## Findings

### NON-BLOCKING / Clarification — same concrete batch_id 再生成時 batch_alias 是否保留

證據：SPEC/TODO 定義「具體 batch_id → latest overwrite；batch_id 變更時 batch_alias reset」以及 `batch_id=None` 單 run 再生 merge-preserve。

評估：這已可實作，且「batch_id 變更時 reset」足以推出同一 concrete batch_id 再生成應保留 batch_alias。為降低實作者誤解，可在實作時用測試鎖定：existing.batch_id == incoming.batch_id 時保留 batch_alias；existing.batch_id != incoming.batch_id 時 reset batch_alias；incoming batch_id is None 時保留 batch_id/batch_alias。此為清晰度建議，不阻斷派工。

## §1 十類必查摘要

1. 矛盾/互斥：無 blocking；overwrite vs merge-preserve 語義自洽，僅有上述可澄清點。
2. 漏項/端到端：無。r3 漏掉的 multi-TF L7 helper 路徑已補齊。
3. 不可測驗收：無。V4 明確要求 multi-TF 路徑 batch_id 寫入 registry 測試。
4. 可疑 quant 假設：無。純 metadata，不改數值/CGSA 計算語義。
5. 過度工程：無。
6. OOM/並行：無新增風險；batch_id 是 picklable str/None，ProcessPool 可傳。
7. Cache 正確性：無 blocking；registry key 不變，新增 ownership metadata。
8. API/型別/相容：無 blocking；新增欄位 optional，舊 entry .get 相容。
9. 測試品質：無 blocking；V4 含 registry/API/cleanup/frontend 與 multi-TF batch_id 寫入斷言。
10. Agent 可執行性：可執行。檔案、函式、呼叫點、不可做與驗證命令足夠具體。

## 被當成事實的未驗證假設

無 blocking。V4 §A 的核心事實（production `momentum/` 只有六個 L7 helper call sites；multi-TF 是批次主路徑且需穿 batch_id）已用 `rg` 和行號讀檔複驗。唯一語義澄清點已列為 NON-BLOCKING。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md §0+§1、docs/BATCH_ALIAS_{SPEC,TODO,MANIFEST}.md、handoffs/20260616-batch-alias-adversarial-codex-r3.md；已用 rg/nl/sed 驗證 production L7 helper call sites、MultiTFGenerator dispatch、registry.add 三處、batch resume→_compute_single→generate_features 路徑、set_alias/deleting/mark_deleting 現況。
TESTS_RUN: 未跑 pytest/vitest；本任務為 read-only adversarial review。靜態命令包括 `rg -n "_layer7_raw_from_cgsa_pipeline|_layer7_validate_and_persist" momentum`、`rg -n "generate_multi_tf|MultiTFGenerator|_generate_multi_tf" momentum`、`rg -n "_run_batch\\(|execute_resume\\(|resume_batch\\(|_process_item_wave\\(|_compute_single\\(" api momentum tests`。
FAILURES_SEEN: none。
SCOPE_CHANGES: none；只新增本 handoff，未改 docs/momentum/api/frontend/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 本次無；審查對象為 metadata batch_id/batch_alias plumbing，V4 不要求數值輸出變更。
HANDOFF_NOT_UPDATED: 依使用者要求輸出到 handoffs/20260616-batch-alias-adversarial-codex-r4.md；未改根 HANDOFF.md。
STATUS: DONE
