## CODEX-R1-P1-01

**斷言**: G2 的預設 `scenario="C"` 會在同一 dedupe cluster 只留一列，可能刪掉不同 `label_id` 的合法事件。
**碼證**: `generator.py:254-258` 接受 manifest 的 `in_primary`；`dedupe.py:118-123` 以 cluster 取首列；實跑 `MULTILABEL_C 124 30 ['up1']`（`up5` 全被去掉）。
**來源摘要**: momentum/Analysis/event_samples/generator.py#3a17e7319b19; momentum/Analysis/event_samples/dedupe.py#6f8d8418dbe0；正文：信心度 High。修法：dedupe 保留每個 `label_id` 或明確改成 label-aware policy；RECHECK：真實 ETHUSDT 多 label、預設 C 應逐 label_id 留存，並重跑 generator adapters。
## CODEX-R1-P1-02

**斷言**: D3 的 `label` 角色只要求含 outcome，未拒絕混入 `pit_feature`，因此 label 可同時引用特徵與結果欄。
**碼證**: `condition_engine.py:80-85,230-235` `_role_violation` 只判 `feature`；實跑 `parse_condition("f > 0 and future_x > 0", ..., "label")` → `LABEL_ROLE_ACCEPTED {'f': 'pit_feature', 'future_x': 'future_outcome'}`。
**來源摘要**: momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b; momentum/Analysis/contracts/condition_engine_contract.json#110d3196292f；正文：信心度 High。修法：label 僅允許 outcome roles（或另定明確 result-only validator）；RECHECK：混合 role、純 future、feature/selection 雙案例與 M6 seam 均須分別拒收/通過。
## CODEX-R1-P1-03

**斷言**: 平台產生器接受任意 `GeneratorConfig.control_kind`，可產出 `user_labeled_other` 但仍標 `kind_source=platform_auto`、`event_source=platform_generator`。
**碼證**: `generator.py:56-70,197-216` 直接寫入設定值；實跑 override probe → `OVERRIDE_CONTROL_KIND 41 ['user_labeled_other'] ['platform_auto'] ['platform_generator']`。
**來源摘要**: momentum/Analysis/event_samples/generator.py#3a17e7319b19; momentum/Analysis/event_samples/import_contract.py#58c331ca3d5d；正文：信心度 High。修法：平台路徑強制 `platform_same_trigger_rule`，user kinds 僅由 import path 接受；RECHECK：正負 label 全列同值，override 應 loud fail，並驗 validator/provenance。
## CODEX-R1-P2-04

**斷言**: 引擎契約快取是可變 module singleton；任一 caller 可改寫 SoT，且 `allowed_filtering_params` 尚未封閉為單一 API 來源。
**碼證**: `condition_engine.py:34,37-43` 返回原 dict；mutation probe → `MUTABLE_CONTRACT_CACHE ...` 並改變 role prefix；`requests.py:46-53` 仍硬編碼 `{'price_change'}`。
**來源摘要**: momentum/Analysis/event_samples/condition_engine.py#27854f2fde3b; api/models/requests.py#938ff6900fed；正文：信心度 High。修法：深度不可變映射/防禦性 copy，並讓 request validator 使用契約出口；同步 `event_filter.py:53-62` Protocol 的 `condition_spec` keyword。RECHECK：mutation regression、API allowed-list、typing/adapter tests；屬 B5 follow-up，非本批 B4 blocker。
## CODEX-R1-P2-05

**斷言**: `IEventFilter` Protocol 未宣告實作已提供的 `condition_spec` keyword-only 參數，型別契約與 runtime adapter 不一致。
**碼證**: `event_filter.py:53-62` Protocol 只有 query/timestamps；`event_filter.py:90-97` concrete method 才有 `condition_spec`；既有 `test_event_filter.py` 僅覆蓋 runtime legacy/adapter。
**來源摘要**: momentum/Analysis/event_filter.py#b74d2dea231f；正文：信心度 Medium。修法：Protocol 與 concrete signature 同步並補型別層呼叫測試；RECHECK：`venv/bin/python -m pytest tests/momentum/test_event_filter.py -q` 及 type-check。屬介面完整性問題，不單獨阻擋 B4。
## Verdict

**結論/逐項 1-3**: 需修補後派工，不能進 B4；B3.1 safe AST、digest、W6/M6 通過，但 label mixed-role=P1；B3.2 G1/G3/G5/G6、B2.5 eligibility/label、G6 shift/accounting、single-class/0-hit 通過，但 G2/control override=P1。
**逐項 4-6**: G-1 legacy path 17 passed、無 cycle/R1-R7、whitelist diff clean；契約 JSON 作引擎 SoT 可接受，optional provenance defaults 與 G6 estimand path 可接受；B3.3 五算子 W7/strict-cross/warmup/NaN/O(n) 及 `[1,inf,2] -> [nan,nan,nan]` adversarial 通過。
**TESTS_RUN**: `venv/bin/python -m pytest tests/momentum/event_samples/ -q -k "condition_engine or generator_adapters"` → 49 passed/131 deselected；`...feature_engineering/ -q -k state_counters` → 17 passed；`...test_mutation_guard.py -q -k M6` → 1 passed/11 deselected；`venv/bin/python scripts/gap3_freeze_golden.py --check` → CHECK PASS sha `163c4cecb100`；P1 修補及上述 RECHECK 後再進 B4。 STATUS: DONE
