# Batch Alias SPEC/TODO Adversarial Review r3

## Verdict：FAIL（V3 仍需修補後派工）

本輪只讀 `templates/`、`docs/`、`handoffs/`、`momentum/`、`api/`、`frontend/`；未改 docs/momentum/api/frontend。已依 `templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md` §0+§1 複審 V3 與真實程式錨點。

## r2 Findings Reconcile Check

- r2-B1 `self._current_batch_id` mutable：**方向已修補但仍有 BLOCKING 漏路徑**。V3 禁 self mutable，改顯式參數穿透（SPEC:38 / TODO:28 / MANIFEST:6）。對照真實程式，`generate_features` 會在 multi-TF config 先分支到 `MultiTFGenerator.generate_multi_tf()`（`feature_factory.py:297-311`），而 multi-TF 內也直接呼叫 `_layer7_raw_from_cgsa_pipeline` / `_layer7_validate_and_persist`（`multi_tf_generator.py:309-317`, `600-608`, `1364-1372`）。V3 只列 `feature_factory.py` 內 @367/@3373/@400，漏 multi-TF call sites，見 BLOCKING #1。
- r2-MAJOR#1 `batch_id=None` 同 key 再生語義：**已修補**。V3 明確定義具體 batch_id overwrite、`None` merge-preserve（SPEC:37-40 / TODO:26,31-32 / MANIFEST:7），並要求測試。
- r2-MAJOR#2 `set_batch_alias` 遇 deleting：**已修補**。V3 明確對齊 `set_alias`，任一 target deleting 則 `RunBusyError` / API 409 / whole transaction fail（SPEC:43-45 / TODO:27,37,42-43 / MANIFEST:8）。真實 `set_alias` deleting gate 在 `feature_registry.py:149-153`。
- r2-MAJOR#3 alias + batch_id reset 組合測試：**已修補**。V3 §V 加入 per-run alias 跨 batch_id reset 保留（SPEC:57-58 / TODO:32）。
- r2-MINOR `_compute_single` batch_id 來源：**已修補**。V3 指定 `_process_item_wave` / executor 由 `checkpoint["batch_id"]` 傳入，而非 task_id（SPEC:38 / TODO:28 / MANIFEST:6）。真實 checkpoint 有 `batch_id`（`feature_factory_batch_service.py:766`），executor 目前尚未傳（`:450-458`），派工方向正確。

## Findings

### [BLOCKING][High] V3 的顯式 batch_id 穿透漏掉 MultiTFGenerator 的 L7 helper 呼叫路徑

證據：
- V3 將 batch_id 鏈定義為 `generate_features(..., batch_id)` 顯式傳三 helper：`_layer7_raw_from_cgsa_pipeline` @367、`_layer7_validate_and_persist_cgsa` @3373、`_layer7_validate_and_persist` @400（SPEC:38 / TODO:28 / MANIFEST:6）。
- 真實 `generate_features` 在 `len(config.timeframes.training) > 1` 時直接 `return multi_generator.generate_multi_tf(...)`，發生在三個 V3 所列 helper 呼叫之前（`feature_factory.py:297-311`）。
- 真實 `MultiTFGenerator` 內另有直接 L7 helper call sites：CGSA serial `_layer7_raw_from_cgsa_pipeline`（`multi_tf_generator.py:309-317`）、CGSA parallel `_layer7_raw_from_cgsa_pipeline`（`:600-608`）、legacy `_layer7_validate_and_persist`（`:1364-1372`）。
- `registry.add` 雖只有三處（`feature_factory.py:3197/3342/3474`），但到達這三處的 caller 不只 V3 列出的 `feature_factory.py` @367/@3373/@400。

會怎麼失敗：
- 若 helper 新增必填 `batch_id`，multi-TF 批次生成會在上述 `MultiTFGenerator` call sites 直接 TypeError。
- 若 helper 新增預設 `batch_id=None`，multi-TF 批次生成會成功但 registry entry 沒有 batch_id，導致整批 rename 找不到或漏掉 multi-TF run。
- 這是 batch 功能的核心端到端缺口，且 multi-symbol batch 常搭配 training timeframes；不能降級為 nit。

修法：
- V3 必須把 `batch_id: Optional[str] = None` 顯式加入 `MultiTFGenerator.generate_multi_tf()`、`_generate_multi_tf_cgsa()`、`_generate_multi_tf_cgsa_parallel()`、`_generate_multi_tf_legacy()`，並傳入上述三個 helper call sites。
- `feature_factory.py:306-311` 呼叫 `generate_multi_tf(..., batch_id=batch_id)`；batch service `_compute_single(..., batch_id)` 的測試要覆蓋 multi-TF config，斷言 registry entry 有 batch_id。
- 若希望縮小 scope，至少在 SPEC/TODO 明確聲明 Phase 1 不支援 multi-TF batch 並加 fail-closed guard；但這會削弱現有 batch 行為，不建議。

## §1 十類必查摘要

1. 矛盾/互斥：有。V3 聲稱三 helper 穿透涵蓋 registry.add，但真實 multi-TF 另有 helper caller。
2. 漏項/端到端：有。batch service → generate_features → MultiTFGenerator → registry.add 未覆蓋。
3. 不可測驗收：有。缺 multi-TF batch_id 寫入 registry 測試。
4. 可疑 quant 假設：無。純 metadata；本 finding 不要求改數值語義。
5. 過度工程：無。
6. OOM/並行：無新增 RAM 風險；顯式參數方向正確。
7. Cache 正確性：有。multi-TF run registry ownership 會缺 batch_id。
8. API/型別/相容：r2 API/deleting/None 語義已足夠明確。
9. 測試品質：需補 multi-TF batch generation registry assertion。
10. Agent 可執行性：不足。實作者照 V3 改 `feature_factory.py` 三處會漏 `MultiTFGenerator` call sites。

## 被當成事實的未驗證假設

- V3 §A「registry.add 三處在三個 helper 內（非 generate_features 本體）」是真的，但隱含假設「只需修改 feature_factory.py @367/@3373/@400 這三條 helper 呼叫鏈」是未驗證且為假；真實 multi-TF generator 也直接呼叫同 helper。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md §0+§1、docs/BATCH_ALIAS_{SPEC,TODO,MANIFEST}.md、r2 handoff；已對照 generate_features:226/297-311、三 helper與 registry.add:3014/3197/3243/3342/3360/3373/3474、MultiTFGenerator helper call sites:309/600/1364、set_alias deleting:149-153、_compute_single:1052、executor:450-458、checkpoint batch_id:766。
TESTS_RUN: 未跑測試；本任務為 read-only adversarial review，使用 rg/nl/sed 靜態查證。
FAILURES_SEEN: none
SCOPE_CHANGES: none；只新增本 handoff，未改 docs/momentum/api/frontend/data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 本次無；finding 只涉及 metadata batch_id plumbing，無數值輸出變更。
HANDOFF_NOT_UPDATED: 使用者明確要求輸出到 handoffs/20260616-batch-alias-adversarial-codex-r3.md；未改根 HANDOFF.md。
STATUS: DONE
