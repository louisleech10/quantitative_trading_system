# Reconcile — 20260821-gap3-b2-review-r1

**來源** 20260821-gap3-b2-review-r1-codex.md, 20260821-gap3-b2-review-r1-composer.md, 20260821-gap3-b2-review-r1-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（主委 Claude 裁決；全部寫回，suite 181 passed、golden --check PASS）

**Verdict**: 需修補後合併——11 條 findings 全數採納修補（已落檔）；R2 由原提出方重跑同一反例閉合，全 CLOSED 後三家 RECONCILE-STAMP → B2 CLOSED。

| 群集 | 對應 ID | 處置 |
|---|---|---|
| X1 AR-3 共同欄機械落地 | CODEX-R1-P1-01, COMPOSER-R1-P1-01, GROK-R1-P1-02, COMPOSER-R1-P2-01, GROK-R1-P2-01 | **採納**：`_common_constraint_block` 改收 Optional plan/manifest（缺 plan ⇒ `formal_pooled_inference_allowed=False`＋`reason=no_event_split_plan`）；B2.2 增 `manifest=` keyword、`common` 走同 helper；B2.5 增 `event_split_plan=`/`manifest=` keyword＋`common` 欄；測試斷言旗標 |
| X2 B2.5 eligibility 連續性＋entry 語意 | CODEX-R1-P1-02 | **採納**：`_is_eligible` 增網格連續檢（決策→窗末 open_time 差＝(h+k)×步長，否則 `missing_bar`）；`entry_price_semantic` 五值映射 `_entry_price`；缺根／next_open 手算 exact 測試 |
| X3 六鍵 event_context 接通 | CODEX-R1-P1-03 | **採納**：`ic_feed` 產 `event_context`（manifest/label_definition sha256＋三規則＋control_kind；批內不唯一 loud）；helper 透傳；`build_survivor_output` 於 conditional_ic 缺 context 拒、`validate_survivor_output` 於 conditional_ic 六鍵 null 拒；整合測試讀 survivor payload 對證 |
| X4 control_kind accepted | CODEX-R1-P2-04 | **採納**：validator 改 `accepted` 集合；`platform_random_bars` 反例入測試 |
| X5 label 覆寫有限值閘 | CODEX-R1-P2-05 | **採納**：`np.isfinite` 檢查 ⇒ `AlignmentViolationError`；inf 整合測試 |
| X6 insufficient 靜默退回主線 | GROK-R1-P1-01 | **採納（方案②）**：insufficient 分支於 `event_label_values` 提供時標 `label_source=mainline_return_N`／`conditional_ic_abandoned=true`／`statistic_kind=conditional_ic_unavailable`；A′ 測試鎖定兩欄。不採方案①（拒算）：A′ 透傳契約要求仍產報告，下游以旗標判 unavailable |
| X7 micro 鍵名錯位 | GROK-R1-P2-02 | **採納**：`sensitivity_micro`＝event 等權；uniqueness 加權改獨立鍵 `uniqueness_weighted`；測試更新 |

白名單檢視：orchestrator 改動仍限 `analyze/_run_full_sample_fallback/_stage3_event_filter` 之 keyword 透傳與事件分支（B2.3 範圍）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

## CODEX-R1-P1-01
**斷言**: AR-3 共同欄未在正式 B2 表/報告一致落地，B2.2/B2.5 無法機械判定 macro、micro、raw/effective n、cluster CI、degraded、LOSO 與 formal pooled gate。
**碼證**: TODO:210 要求每張表列全套欄；`tables.py:221-242` 的 B2.2 `common` 只有部分摘要，`all_bars_eval.py:152-173` 沒有共同區塊，且 B2.1 macro 僅 `mean/n_symbols`（`tables.py:151-154`）。
**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；momentum/Analysis/event_samples/tables.py#9dff52e142b5；momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd。
## CODEX-R1-P1-02
**斷言**: B2.5 eligibility 未驗資料連續性/PIT 合法性，且持有報酬固定取 `open[i-k]`，未依 D1-6/實際 entry semantic 映射；缺口或非 open 進場會被報成可用結果。
**碼證**: `all_bars_eval.py:21-31` 只檢 warmup、tail、有限正價格；`:78-109` 未檢 timestamp continuity/cutoff，並硬編 `hold=(close[i+h]-open[i-k])/open[i-k]`；TODO:288 明列 continuity、PIT、實際進場價。
**來源摘要**: momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd；docs/GAP3_EVENT_TODO.md#df04bdabf37d。
## CODEX-R1-P1-03
**斷言**: B2.3→B2.4 的六鍵 event context 未接通：feed 只產 timestamps/label values，實際 analyze helper 未傳 `event_context`；因此事件 survivor 可落成六鍵全 null，而 validator/test 仍放行。
**碼證**: `ic_feed.py:35-65` 無六鍵 context；`tests/momentum/helpers/ichc_run.py:30-68` 只轉兩個 event 參數；`survivor_contract.py:462-465` 缺 context 即全 null，與 contract:257 的 conditional IC 六鍵全非 null 不一致；test:610-616 固化此 loophole。
**來源摘要**: momentum/Analysis/event_samples/ic_feed.py#6a3d48a225ad；tests/momentum/helpers/ichc_run.py#239c098c7b82；momentum/Analysis/survivor_contract.py#ef7015934eeb；momentum/Analysis/contracts/ic_survivor_contract.json#270696d74f32。
## CODEX-R1-P2-04
**斷言**: survivor v2 validator 取 `control_kind.enum` 而非 import contract 的 `accepted` 集合，故會接受目前明定拒絕的 `platform_random_bars`。
**碼證**: `survivor_contract.py:368-371` 只比對 enum；`event_import_contract.json:43-48` 將 `platform_random_bars` 列 enum 但列入 rejected，並明定恆拒。
**來源摘要**: momentum/Analysis/survivor_contract.py#ef7015934eeb；momentum/Analysis/contracts/event_import_contract.json#7111b2d7060e。
## CODEX-R1-P2-05
**斷言**: conditional IC 直接 label override 未做 finite gate；`event_label_values` 的 `inf/-inf` 會通過存在性檢查與 float cast，繼續進入 IC，而非 loud unavailable/reject。
**碼證**: `ic_filter_orchestrator.py:2875-2887` 僅檢 key 是否存在並 `float(...)`，沒有 `np.isfinite`/有限值拒絕；同檔 `:2890-2892` 隨即標記 conditional IC。
**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#eccdb0be9fb8。
## COMPOSER-R1-P1-01

**斷言**: `evaluate_all_bars` 未接受 B2 批共同約束要求的 `event_split_plan` 輸入，報告 dict 亦缺 `degraded`／`loso_status`／`formal_pooled_inference_allowed` 等 AR-3 機械可讀欄，違反 TODO Phase B2 前言與 SPEC §215「每張表/報告必列」——B3.2 G6 直接呼叫時下游無法 fail-closed 判 pooled inference。

**碼證**: `docs/GAP3_EVENT_TODO.md` Phase B2 前言 L210「B2.1/B2.2/B2.3/B2.5…必需輸入＝event_split_plan＋cluster manifest；每張表必列…`formal_pooled_inference_allowed` 旗標」；`all_bars_eval.py:40-44` 簽名僅 `(model_scores_or_rule, bars, manifest_config)`；輸出 `152-173` 無 `degraded`/`loso_status`/`formal_pooled_inference_allowed`；對照 `tables.py:61-72` `_common_constraint_block` 完整實作；`test_all_bars_eval.py` 無 AR-3 斷言。RECHECK：`rg 'formal_pooled_inference' momentum/Analysis/event_samples/all_bars_eval.py` → 0；`pytest tests/momentum/event_samples/test_all_bars_eval.py -q` 仍綠但不覆蓋此欄。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d; momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High；失敗模式＝B3 G6 全 K 線報告與事件表 AR-3 欄不一致，審計/合規端無法機械禁 formal pooled inference。修法：簽名增 optional `event_split_plan`（或 manifest_config 內嵌 summary），輸出增 `_common_constraint_block` 同型欄＋測試 assert。

---

## COMPOSER-R1-P2-01

**斷言**: `binary_discrimination_table` 的 `common` 區塊未列 `formal_pooled_inference_allowed` 與 `n_events_raw`/`n_events_effective`，與 B2.1 共用 helper 不一致，AR-3 機械可讀性缺口（非 estimand 錯，但違批内「每張表必列」字面）。

**碼證**: `tables.py:236-241` 僅 `stats_modes/degraded/loso_status/insufficient_events_in_test`；缺 `formal_pooled_inference_allowed`（B2.1 在 `71` 行計算）；函式未接 `EventManifest` 故無 raw/effective n。RECHECK：`pytest tests/momentum/event_samples/test_tables.py -q -k discrimination` → 4 passed，未 assert `formal_pooled_inference_allowed`。

**來源摘要**: momentum/Analysis/event_samples/tables.py#9dff52e142b5; docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High；修法：複用 `_common_constraint_block`（需增 manifest 參數）或至少從 `event_split_plan.summary` 衍生 `formal_pooled_inference_allowed`。

---

## GROK-R1-P1-01

**斷言**: 當呼叫端已傳 `event_label_values`（條件 IC 意圖）且 stage3 命中 `tier==insufficient` 時，函式在 label 覆寫之前 early-return 全樣本＋主線 `label_series`，後續 stage4+ 以 `return_N` 繼續算 IC，且不設 `label_source=event_label_value`／`statistic_kind=conditional_ic`——構成 brief Q3 所問「靜默退回主線 return_N」路徑；A′ 測試只 assert `fallback is True`、未鎖 label 來源。

**碼證**: `ic_filter_orchestrator.py` 2862–2867（`tier==insufficient` → `return features_df, label_series, info`，此時 `label_series` 仍為 stage2 主線）；2875–2892（`event_label_values` 覆寫在早退之後，insufficient 永不執行）；`analyze` 1007–1038 於 stage3 後直接進 feature filter／stage4，無「conditional_ic 不可算 ⇒ unavailable」分支。對照 U5／TODO B2.3「樣本不足 → 標不可算」與「不把主線 return_N 靜默當事件 label」。`test_gap3_conditional_ic.py::test_conditional_ic_orchestrator_aprime_fallback_passthrough`（約 116–122）僅 assert fallback，不 assert `label_source`。RECHECK：構造 `min_events`＞傳入 timestamps 數且帶 `event_label_values`，檢查 report 是否出現 `label_source=event_label_value`（預期無）與是否仍產出數值 IC。

**來源摘要**: momentum/Analysis/ic_filter_orchestrator.py#eccdb0be9fb8；tests/momentum/event_samples/test_gap3_conditional_ic.py#2bb79fbadacf；docs/GAP3_EVENT_TODO.md#df04bdabf37d；docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MAJOR] 信心度=High。失敗模式＝呼叫端以為在跑條件 IC，實際吃主線報酬標籤的全樣本 IC；`fallback` 只揭露事件數不足，不揭露 label 來源切換。修法（擇一，須測）：①`event_label_values is not None` 且 insufficient ⇒ `unavailable:insufficient_events`／loud，禁續算；②續算則強制 metadata `label_source=mainline_return_N`＋`conditional_ic_abandoned=true` 並測鎖定。

---

## GROK-R1-P1-02

**斷言**: `evaluate_all_bars` 未接 B2 全批共同約束要求的 `event_split_plan`（＋cluster manifest），輸出亦無 `degraded`／`loso_status`／`formal_pooled_inference_allowed`／macro·micro 等 AR-3 機械可讀欄，違反 TODO Phase B2 前言與 SPEC「B2.1/B2.2/B2.3/B2.5…每張表/報告必列」——B3.2 G6 直呼時下游無法 fail-closed 禁 formal pooled inference。

**碼證**: `docs/GAP3_EVENT_TODO.md` L210（共同約束含 B2.5）；`docs/GAP3_EVENT_SPEC.md` Phase B2 前言同文；`all_bars_eval.py` 40–44 簽名僅 `(model_scores_or_rule, bars, manifest_config)`；輸出 152–173 無 AR-3 欄；對照 `tables.py` 61–72 `_common_constraint_block`。`test_all_bars_eval.py`／M11 皆不 assert B2.5 報告之 `formal_pooled_inference_allowed`。RECHECK：`grep formal_pooled_inference momentum/Analysis/event_samples/all_bars_eval.py` → 0。

**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d；momentum/Analysis/event_samples/all_bars_eval.py#572fea6ecdfd；docs/GAP3_EVENT_SPEC.md#544c2922ef2e；momentum/Analysis/event_samples/tables.py#9dff52e142b5

[MAJOR] 信心度=High。註：Task B2.5 簽名本身未列 `event_split_plan`，與批前言共同約束**自相張力**——實作跟了 Task 簽名、丟了 AR-3；審查以共同約束＋AR-3 為準。修法：簽名或 `manifest_config` 納入 split summary／cluster 旗標，輸出對齊 `_common_constraint_block`＋測試。

---

## GROK-R1-P2-01

**斷言**: `binary_discrimination_table` 的 `common` 未列 `formal_pooled_inference_allowed` 與 `n_events_raw`／`n_events_effective`，與同檔 B2.1 `_common_constraint_block` 不一致，AR-3「每張表必列」字面未滿足（估計量本身未證偽錯誤）。

**碼證**: `tables.py` 236–241 僅 `stats_modes/degraded/loso_status/insufficient_events_in_test`；B2.1 於 71 行計算 `formal_pooled_inference_allowed`；辨別表未接 `EventManifest`。`test_tables.py -k discrimination` 未 assert 該旗標。RECHECK：讀 `binary_discrimination_table` 回傳 `common` keys。

**來源摘要**: momentum/Analysis/event_samples/tables.py#9dff52e142b5；docs/GAP3_EVENT_SPEC.md#544c2922ef2e

[MINOR] 信心度=High。修法：複用 `_common_constraint_block`（增 manifest）或至少自 `event_split_plan.summary` 衍生 `formal_pooled_inference_allowed`。

---

## GROK-R1-P2-02

**斷言**: brief assumed「micro＝uniqueness 加權 event 等權＝符合 AR-3」不成立——SPEC B1.3／事件切分定案之 micro＝**event 等權**；B2.1 將 uniqueness 加權掛在 `sensitivity_micro`，純 event 等權落在 `raw_all_unweighted`，標籤與 AR-3／SPEC 敏感度定義錯位（單 symbol／權重全 1 時數值碰巧重合，多事件重疊時 estimand 漂移）。

**碼證**: SPEC／TODO B1.3：「統計 primary＝macro（symbol 等權）、micro（event 等權）＝敏感度」；`tables.py` 148–166 註解寫「micro＝event 等權／uniqueness 加權」並以 `block(df, weighted=True)`（讀 `uniqueness_weight`）填 `sensitivity_micro`，`weighted=False` 才是等權且鍵名為 `raw_all_unweighted`。RECHECK：構造兩事件 uniqueness_weight≠1，比較 `sensitivity_micro` mean vs 等權 mean。

**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e；momentum/Analysis/event_samples/tables.py#9dff52e142b5；handoffs/20260821-gap3-b2-review-brief.md#1b69a6e5d89b

[MINOR] 信心度=Medium-High。失敗模式＝下游把 `sensitivity_micro` 當 AR-3 micro 引用時，實際吃的是 uniqueness 加權。修法：`sensitivity_micro` 改純等權，uniqueness 加權改獨立鍵（或文件＋契約顯式更名並改 AR-3 文案——須 D-延伸，非本輪改 SPEC）。

---

