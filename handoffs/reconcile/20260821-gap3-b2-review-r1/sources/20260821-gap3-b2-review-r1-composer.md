# GAP-3 B2 批 code review R1 — COMPOSER

family: composer  
task-id: 20260821-GAP3-B2-REVIEW-R1  
scope: B2 實作＋測試（`git diff 582a9180..HEAD -- momentum/ tests/ scripts/gap3_freeze_golden.py`）；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`＋`docs/GAP3_EVENT_TODO.D-001.md`  
brief: `handoffs/20260821-gap3-b2-review-brief.md`  
禁改碼：review-only

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R1 複核結論 |
|---|---|---|
| event_samples 123 passed；survivor 51 passed；`gap3_freeze_golden.py --check` PASS canonical_sha=163c4cec… | fact-verified（brief） | **本輪重跑** → 123 passed / 51 passed / CHECK PASS（同一 canonical_sha） |
| GAP-2 消費側 pytest -k "survivor or gap2 or stage6b" | fact-verified（brief） | 未重跑（brief 附主委 receipt）；survivor v1 顯式拒＋v2 六鍵測試 51 passed 佐證契約側 |
| assumed: label 覆寫在 `_stage3_event_filter` 尾端是唯一插入點 | **攻後＝成立** | 事件過濾＋index 交集後才覆寫 label；split mask 重算在 stage3 之後（`analyze:1007-1012`）；stage4/5 只吃已覆寫之 `label_series` |
| assumed: v2 六鍵经 `event_context` 透传、B2.3/B2.4 同批 orchestrator 接線 | **攻後＝成立（白名單語境）** | diff 僅 +37 行：`event_label_values`／`event_context` keyword＋stage3 label 分支＋`build_survivor_output(event_context=…)`；無 stage4/5 內部改動 |
| assumed: B2.5 六計數分帳（n_unknown／n_tail_excluded／n_missing） | **攻後＝成立** | `all_bars_eval.py:92-105` 分 reason 記帳；assert 守恆（174-175）；`test_all_bars_eval.py` 手算 exact |
| assumed: B2.1 macro＝symbol 先算再等權、micro＝uniqueness 加權 | **攻後＝成立** | `tables.py:148-165` 與 `_weighted_stats`；`test_forward_return_hand_example_exact` 綠 |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ -q → 123 passed in 27.03s rc=0
venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q → 51 passed in 10.81s rc=0
venv/bin/python scripts/gap3_freeze_golden.py --check → CHECK PASS canonical_sha=163c4cecb1006dc42dea0804acc365d83fe7cdbaf05ba64b1d794168dd67e463 rc=0
git diff 582a9180..HEAD --stat momentum/Analysis/ic_filter_orchestrator.py → +37 lines（白名單 B2.3 最小接線）
```

---

## 必答（brief 七題）

### 1. 逐 Task 對 TODO 驗收（B2.1–B2.5）

| Task | verdict | 摘要 |
|---|---|---|
| B2.1 事件後報酬表 | **PASS** | `event_forward_return_table` 完整 AR-3 `_common_constraint_block`；horizon config 化；超界排除不灌 0；macro/micro/raw 並列 |
| B2.2 正反例辨別表 | **PARTIAL** | OOS only、kind 分層、unclassifiable、置亂 oracle 齊；**common 缺 `formal_pooled_inference_allowed` 與 raw/effective n**（見 P2-01） |
| B2.3 條件 IC 接線 | **PASS** | `ic_feed.py` 餵入＋orchestrator stage3 label 覆寫；缺 label loud；A′ fallback 透傳 `event_label_values`；§G-1 `--check` 綠 |
| B2.4 survivor v2 | **PASS** | json v1→2；半套拒；v1 payload 顯式拒；`event_context` 填六鍵或全 null |
| B2.5 all-bars evaluator | **PARTIAL** | D4 六計數＋prevalence 並排＋M4/M7 mutation 可證偽；**缺 AR-3 機械欄與 `event_split_plan` 必需輸入**（見 P1-01） |

越權改檔：**none** — orchestrator +37 行限 analyze/A′/stage3/survivor 透傳；survivor_contract +24；其餘新增 `event_samples/*` 與測試。

### 2. §G-1 行為不變

**成立。** 本輪 `gap3_freeze_golden.py --check` PASS，`canonical_sha` 與 brief 一致；`event_label_values=None` 時 stage3 不進 label 覆寫分支（`ic_filter_orchestrator.py:2875-2892` 整段 guarded），與凍結前逐位元組路徑一致（非僅信 sha——讀 diff 可見唯一行為差在 `is not None` 分支）。

### 3. B2.3 語意

**成立。** 條件 IC 只吃 `label_value`（stage3 覆寫 + `ic_feed` 缺值 ⇒ unavailable）；feature 列＝`last_bar_open_ms`（PIT cutoff bar）；缺 label ⇒ `AlignmentViolationError` 或 feed `missing_label_value`；A′ 重跑保留 keyword（`1165-1169`）。**未見**靜默退回主線 `return_N` 路徑（有 `event_label_values` 時必走覆寫或 loud fail）。

### 4. B2.4 升版

**成立。** 51 passed 含 v2 鍵集、全 null／全非 null、半套拒、v1 顯式拒；`--check` 升版後仍 PASS ⇒ GAP-2 序列型行為不變。

### 5. B2.5 固定分母

**核心 D4 成立；揭露欄一項待釐清。** eligibility 與六計數分帳通過手算 exact（`test_denominator_hand_example_real_kline`）；`prevalence_learn`／`prevalence_full` 並排＋lift 語意對。`signal_frequency=pred.mean()` 分母＝**eligible 且已計分**列（非全 K 線）——與 `prevalence_full`（eligible 內 label 基率）一致，**非** case-control 基率混淆；若產品要「全 bar 訊號密度」需另鍵，現行未誤讀 D4-3。

### 6. AR-3 共同約束

| 產出 | macro/micro | raw/effective n | cluster CI | degraded/LOSO | `formal_pooled_inference_allowed` |
|---|---|---|---|---|---|
| B2.1 forward_return | ✓ | ✓ | ✓ | ✓ | ✓ |
| B2.2 discrimination | N/A（OOS 辨別 estimand） | ✗ | ✗ | 部分 | ✗ |
| B2.3 ic_feed | N/A | N/A | N/A | split_summary | N/A |
| B2.5 all_bars | N/A | counts 有、非 event n | ✗ | ✗ | ✗ |

M11 只看 `event_split._degraded_flags` seam，**未** assert B2.5 報告欄。

### 7. 可進 B3？

**需修補 P1-01 後可進 B3。** B2.3/B2.4/§G-1 無 BLOCKING；B2.5 AR-3 機械揭露缺口會讓 B3.2 G6 消費端無法判 formal pooled inference（P1，非數值錯）。

---

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

## Verdict：需修補後派工（P1-01 修復＋測試後可進 B3；P2-01 可同批或 B3 前小修）

B2.3/B2.4/§G-1/D4 核心數值路徑與 mutation M4/M7/M11 seam 本輪驗證通過；白名單 orchestrator diff 最小。阻擋項＝B2.5 AR-3 機械欄缺失（P1），非 IC 接線或 survivor 升版缺陷。

---

ASSUMPTIONS_VERIFIED: 123+51 pytest 本輪重跑 rc=0；golden --check PASS sha=163c4cec…；stage3 label 插入點／六計數分帳／macro-micro 語意攻前提後成立  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ -q` → 123 passed rc=0；`venv/bin/python -m pytest tests/momentum/Analysis/test_survivor_contract.py -q` → 51 passed rc=0；`venv/bin/python scripts/gap3_freeze_golden.py --check` → PASS rc=0  
FAILURES_SEEN: none（review 過程）  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b2-review-r1-composer.md`

STATUS: DONE
