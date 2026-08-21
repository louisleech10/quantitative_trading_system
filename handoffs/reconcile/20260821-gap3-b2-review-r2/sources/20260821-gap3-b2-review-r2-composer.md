# GAP-3 B2 批 code review R2 閉合輪 — COMPOSER

family: composer  
task-id: 20260821-GAP3-B2-REVIEW-R2  
scope: 修補 diff `9e168635..77140942`（`momentum/`＋`tests/`）；R1 synth `handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md`；權威 `docs/GAP3_EVENT_TODO.md` FROZEN＋`docs/GAP3_EVENT_SPEC.md`；禁改碼  
brief: `handoffs/20260821-gap3-b2-review-r2-brief.md`  
R1 本家: `handoffs/20260821-gap3-b2-review-r1-composer.md`

RECONCILE-STAMP: composer APPROVED 2026-08-21 sha256:d4c399431ec3dfac5a732bba3de00c5680a41d69329889748aecc4d27b6cbb7b task:20260821-GAP3-B2-REVIEW-R2

---

## 被當成事實的未驗證假設（§0）

| brief 前提 | 標注 | R2 複核結論 |
|---|---|---|
| 修補後 181 passed（event_samples 129＋survivor 52）；golden `--check` PASS | fact-verified（brief） | **本輪重跑** → 181 passed in 29.82s rc=0；golden `--check` 依 brief 不再跑（避免並行） |
| assumed: GROK insufficient ⇒ loud 續算（方案②）非拒算 | **攻後＝成立（白名單）** | 非本家 R1 原提出方；`test_gap3_conditional_ic.py` A′ 分支已 assert `label_source=mainline_return_N`／`conditional_ic_abandoned=true`（synth X6）；composer 不代判 codex/grok 閉合 |
| assumed: B2.5 連續性＝決策 bar→答案窗末 open_time 差＝(h+k)×中位步長（crypto 連續網格） | **攻後＝成立（本批 scope）** | `_is_eligible` L31-34 端點差分＋`step_ms=median(diff)`；缺根 ⇒ `missing_bar`（`test_grid_gap_counted_as_missing_bar` 刪第 50 根 ⇒ 2×missing_bar、eligible 手算一致）；非 crypto 不規則網格未宣稱覆蓋——落在 TODO/SPEC 未重審之不受理範圍 |

VERIFY（本輪實跑）:
```
venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q → 181 passed rc=0
venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py::test_common_constraint_block_present tests/momentum/event_samples/test_tables.py::test_discrimination_oos_only_and_kind_strata -q → 2 passed rc=0
rg 'formal_pooled_inference|_common_constraint_block' momentum/Analysis/event_samples/all_bars_eval.py → 命中 L205-207（common 委派 helper）
git diff 9e168635..77140942 --stat -- momentum/ tests/ → 11 files +216/-39
```

---

## 1. 本家 R1 finding 閉合（章程 §B8）

| R1 ID | 原斷言摘要 | 重跑反例／RECHECK | 判 |
|---|---|---|---|
| COMPOSER-R1-P1-01 | B2.5 缺 `event_split_plan` 輸入＋報告缺 AR-3 機械欄 | **修補前**（R1）：簽名僅 `(model_scores_or_rule, bars, manifest_config)`、`rg formal_pooled_inference all_bars_eval.py`→0。**修補後**：`all_bars_eval.py:70-71` 增 keyword `event_split_plan=`／`manifest=`；`:205-207` `out["common"]=_common_constraint_block(...)` 含 `degraded`／`loso_status`／`formal_pooled_inference_allowed`／`reason`；無 plan ⇒ `False`+`no_event_split_plan`；`test_common_constraint_block_present` 綠 | **CLOSED** |
| COMPOSER-R1-P2-01 | B2.2 `common` 缺 `formal_pooled_inference_allowed` 與 raw/effective n | **修補前**（R1）：`tables.py:236-241` 僅四鍵。**修補後**：`:61-82` 共用 `_common_constraint_block`；`:248` 辨別表走同 helper；`:193` 增 optional `manifest=`；`test_discrimination_oos_only_and_kind_strata` assert 全套鍵＋`formal_pooled_inference_allowed is False`、無 manifest 時 `n_events_raw is None` | **CLOSED** |

---

## 2. brief 必答

1. **原提出方逐條 CLOSED？** composer **2/2 CLOSED**（P1-01、P2-01）；codex 5 條＋grok 4 條由各自 R2 自跑，本輪不代判。
2. **修補新引入問題？** **無** — `_common_constraint_block` 集中化未改 estimand；181 passed 含 AR-3／missing_bar／entry_semantic 回歸；未捏造湊數 finding。
3. **可進三家 RECONCILE-STAMP？** **composer 側可** — 本家 R1 反例已閉合、sentinel 0 finding；**待 codex／grok 同輪 CLOSED 且無新 BLOCKING 後** quorum 戳 synth → B2 CLOSED。

---

## COMPOSER-R2-P3-00

**斷言**: 本輪逐項核對後無 finding；COMPOSER-R1-P1-01／P2-01 原 RECHECK（B2.5 keyword+common、B2.2 全套 `_common_constraint_block`）均已 CLOSED，修補 diff 未引入新的 AR-3 機械欄或 all-bars／辨別表可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 181 passed rc=0；`test_common_constraint_block_present`／`test_discrimination_oos_only_and_kind_strata` → 2 passed rc=0；`all_bars_eval.py:65-72,205-207` keyword+common；`tables.py:61-82,186-194,248` 共用 helper+manifest kw；brief assumed 連續性網格攻擊不推翻（`test_grid_gap_counted_as_missing_bar`）；`git diff 9e168635..77140942` 對照 synth X1 採納項。

**來源摘要**: momentum/Analysis/event_samples/all_bars_eval.py#d4c399431ec3; momentum/Analysis/event_samples/tables.py#a0f52eebfd6b; handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md#1b0044ca37a3; docs/GAP3_EVENT_TODO.md#df04bdabf37d

正文：[MINOR] 信心度=High。逐項重掃 B2.5／B2.2 AR-3 路徑、mutation M4/M7 seam、連續性 assumed 攻擊後仍與 brief /crypto 網格前提一致；GROK insufficient 路徑屬 X6 非本家原提出方。禁捏造湊數。

---

## Verdict：可進 B2 CLOSED（composer 側；待 codex/grok R2 quorum）

本家 R1 兩條 **CLOSED**；修補與 synth X1 群集（`_common_constraint_block` 機械落地）一致；181 passed。composer 無阻擋項。

---

ASSUMPTIONS_VERIFIED: 181 passed 本輪重跑；P1-01/P2-01 RECHECK 修補後碼證+測試綠；B2.5 網格連續性 assumed 攻擊不推翻  
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 181 passed rc=0；`venv/bin/python -m pytest tests/momentum/event_samples/test_all_bars_eval.py::test_common_constraint_block_present tests/momentum/event_samples/test_tables.py::test_discrimination_oos_only_and_kind_strata -q` → 2 passed rc=0  
FAILURES_SEEN: none  
SCOPE_CHANGES: none（review-only）  
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）  
HANDOFF_OUTPUT: `handoffs/20260821-gap3-b2-review-r2-composer.md`

STATUS: DONE
