# GAP-3 B2 批 code review R1 — grok

task-id: 20260821-GAP3-B2-REVIEW-R1
family: grok
brief-kind: review
brief: handoffs/20260821-gap3-b2-review-brief.md
diff: `git diff 582a9180..HEAD -- momentum/ tests/ scripts/gap3_freeze_golden.py`
權威: `docs/GAP3_EVENT_TODO.md`（FROZEN）Phase B2＋`docs/GAP3_EVENT_SPEC.md` D1/D4／§G／§C＋`docs/GAP3_EVENT_TODO.D-001.md`
禁改碼：review-only

## Verdict：需修補後派工（不可直接進 B3）

本輪有 **2×MAJOR（P1）**、**2×MINOR（P2）**；**無 P0 BLOCKING**。B2.1／B2.4／§G-1／D4 分母核心與 mutation M4/M7/M11 可證偽性成立；阻擋進 B3 的主因＝（1）條件 IC 在 `insufficient` 路徑靜默改吃主線 `return_N`；（2）B2.5 AR-3 機械欄缺席。

### 必答（brief 七題）

1. **逐 Task 對 TODO**  
   - B2.1：**PASS**（手算 exact、CI 決定性、horizon 排除、AR-3 `_common_constraint_block` 齊）。  
   - B2.2：**PARTIAL**（OOS／kind／oracle 齊；`common` 缺 `formal_pooled_inference_allowed` 與 raw/effective n → P2-01）。  
   - B2.3：**PARTIAL**（餵入層＋stage3 覆寫＋缺 label loud＋§G-1 綠；**insufficient 早退跳過覆寫 → P1-01**）。orchestrator diff 限 keyword／stage3 尾／A′／survivor 透傳，未改 stage4/5 內部。  
   - B2.4：**PASS**（v2 六鍵全 null／全非 null、半套拒、v1 顯式拒；B2.4 commit 另動 orchestrator `event_context`——白名單字面「只在 B2.3」，同批最小接線可接受但須記帳）。  
   - B2.5：**PARTIAL**（D4 六計數＋基率並排＋M4/M7 綠；**缺 AR-3／`event_split_plan` → P1-02**）。  
   越權改檔：**無**（白名單外產品檔未改；`event_split._degraded_flags` 為 M11 seam）。

2. **§G-1 行為不變**：**成立（讀 diff＋brief fact，本輪未重跑 `--check`）**。凍結 commit `672ea36a`；`event_label_values is None` 時 stage3 覆寫整段不執行（`ic_filter_orchestrator.py` 2875 守衛）；`event_context` 未傳 ⇒ survivor 六鍵全 null。brief 附 canonical_sha=`163c4cec…` 於 B2.3／B2.4 後各 PASS——本家**未**並行重跑 golden（brief：只准一次）。

3. **B2.3 語意**：**有一條靜默退回主線 `return_N` 路徑（P1-01）**。happy path／缺 label loud／PIT cutoff＝`last_bar_open_ms` 成立；`tier==insufficient` 早退在覆寫前，繼續用主線 `label_series` 跑全樣本 IC。

4. **B2.4 升版**：**成立**（契約 v2＋validator；GAP-2 消費側以 brief／commit 訊息為 fact，本輪未重跑 `-k survivor or gap2 or stage6b`）。

5. **B2.5 固定分母**：**D4-1／D4-3 核心成立**。`n_tail_excluded`（答案窗未完）／`n_unknown`（warmup／價格無效）／`n_missing`（僅 eligible 內 score 缺）分帳＋assert 守恆；`prevalence_learn`∥`prevalence_full`＋lift 用 `prev_full`；`signal_frequency=pred.mean()` 分母＝已計分 eligible，非學習樣本洩口。

6. **AR-3**：**B2.1 齊；B2.2 部分；B2.5 缺**（見 P1-02／P2-01）。M11 只鎖 `_degraded_flags` 產生點，未 assert 各表報告欄。

7. **可進 B3？**：**否——先修 P1-01＋P1-02**；P2 可同批或緊隨。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| fact: event_samples 123／survivor 51／golden PASS | **本輪部分複驗** | 聚焦 pytest 20 passed（tables／all_bars／conditional_ic／M4·M7·M11）；**未**重跑全套 123／51／`--check`（避並行 golden） |
| fact: GAP-2 消費側 81 passed | **未覆核** | 依 brief／commit 訊息；契約側 51 測試存在 |
| assumed: label 覆寫在 `_stage3_event_filter` 尾、split mask 重算前＝唯一插入點 | **插入點位置成立；覆蓋面不完整** | 覆寫在過濾＋index 交集後、return 前；但 `tier==insufficient` 早退使該插入點**根本執行不到**（P1-01） |
| assumed: v2 六鍵 `event_context` 同批接線不違白名單 | **語意可接受／字面違規** | B2.4 commit 改 orchestrator +8 行；白名單寫「orchestrator 只在 B2.3」；同批最小透傳、無 stage4/5 改動 |
| assumed: B2.5 六計數分帳對 D4-1 | **成立** | `all_bars_eval.py` 92–105＋174–175 assert；手算 100→98/2 |
| assumed: B2.1 macro＝symbol 等權、micro＝uniqueness 加權＝AR-3 | **macro 成立；micro 標籤與 SPEC 不符** | SPEC B1.3 micro＝**event 等權**；實作 `sensitivity_micro`＝uniqueness 加權；純等權在 `raw_all_unweighted`（P2-02） |

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

## 被當成事實的未驗證假設（§0）

見上表。另：composer 同輪稱「未見靜默退回 return_N」——本家以 P1-01 碼徑獨立推翻該樂觀結論（insufficient 早退）。本輪**未**重跑 `gap3_freeze_golden.py --check`（brief 禁並行）。

ASSUMPTIONS_VERIFIED: stage3 插入點位置；B2.5 六計數分帳；macro symbol-等權；B2.4 v2 契約鍵；orchestrator 白名單最小 diff；insufficient×label 早退碼徑
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/test_tables.py tests/momentum/event_samples/test_all_bars_eval.py tests/momentum/event_samples/test_gap3_conditional_ic.py tests/momentum/event_samples/test_mutation_guard.py -q -k "M4 or M7 or M11 or forward or discrimination or conditional_ic or denominator or prevalence or label"` → **20 passed**, 11 deselected, rc=0（~12.9s）；`gap3_freeze_golden.py --check`／全套 123／survivor 51 → **未跑**（避並行；依 brief fact）
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b2-review-r1-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

STATUS: DONE
