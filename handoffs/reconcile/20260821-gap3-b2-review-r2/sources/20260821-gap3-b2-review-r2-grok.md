# GAP-3 B2 review R2 — grok（closure／sentinel）

task-id: 20260821-GAP3-B2-REVIEW-R2
family: grok
brief-kind: closure
brief: handoffs/20260821-gap3-b2-review-r2-brief.md
patch: `git diff 9e168635..77140942 -- momentum/ tests/`（commit 77140942「B2 review R1 全修」）
R1 裁決: handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md

## Verdict：可進三家 RECONCILE-STAMP（本家 4/4 CLOSED；本輪無新 finding）

### 必答

1. **原提出方逐條 CLOSED？**  
   | ID | 處置 | 本輪碼證摘要 |
   |---|---|---|
   | GROK-R1-P1-01 | **CLOSED** | insufficient＋`event_label_values` ⇒ `label_source=mainline_return_N`／`conditional_ic_abandoned=True`／`statistic_kind=conditional_ic_unavailable`；A′ 測試鎖定前兩欄；手跑 `run_analyze(min_events=30, n=3)` 三欄皆到位 |
   | GROK-R1-P1-02 | **CLOSED** | `evaluate_all_bars(..., event_split_plan=, manifest=)`；`common=_common_constraint_block(...)`；無 plan ⇒ `formal_pooled_inference_allowed=False`＋`reason=no_event_split_plan`；`test_common_constraint_block_present` 綠 |
   | GROK-R1-P2-01 | **CLOSED** | `binary_discrimination_table` 之 `common` 走同一 helper；assert 含 `formal_pooled_inference_allowed`／`n_events_raw`／`degraded` 等；`test_discrimination_oos_only_and_kind_strata` 綠 |
   | GROK-R1-P2-02 | **CLOSED** | `sensitivity_micro=block(weighted=False)`；`uniqueness_weighted` 獨立鍵；權重 0.5/0.5 時 mean 相異（0.00619 vs −0.00518）；測試改鎖等權 |

2. **修補新引入問題？**  
   **無**（見 sentinel `GROK-R2-P3-00`）。方案② loud 續算與 AR-3／micro 鍵名修補未引出可證偽 P0–P2 缺陷；A′ survivor 雖仍帶六鍵 context，但 `sample_scope.kind=full`＋`degraded=true`，與成功條件 IC 之 `kind=event` 機械可分，不另開 finding。

3. **可進三家 RECONCILE-STAMP？**  
   **可以（grok 本輪 APPROVED）**——前提為同輪 codex／composer 對其原 finding 亦 CLOSED 且無新 BLOCKING。本檔戳記見文末。

### R1 閉合逐條（原提出方重跑）

**Closure P1-01（原 ID GROK-R1-P1-01）— CLOSED**
- 碼：`ic_filter_orchestrator.py` insufficient 分支於 `event_label_values is not None` 設三欄後 return（主線 `label_series` 續算）。
- 測：`test_conditional_ic_orchestrator_aprime_fallback_passthrough` assert `fallback`／`conditional_ic_abandoned`／`label_source==mainline_return_N`。
- 手跑：同上三欄＋`statistic_kind=conditional_ic_unavailable`。

**Closure P1-02（原 ID GROK-R1-P1-02）— CLOSED**
- 碼：`all_bars_eval.py` 簽名增 keyword；輸出 `common` 複用 `_common_constraint_block`。
- 測：`test_common_constraint_block_present`（無 plan／有 plan+degraded）。

**Closure P2-01（原 ID GROK-R1-P2-01）— CLOSED**
- 碼：`tables.py` `binary_discrimination_table` → `out["common"]=_common_constraint_block(event_split_plan, manifest)`；可選 `manifest=`。
- 測：discrimination 測断言 AR-3 鍵集與 `formal_pooled_inference_allowed=False`（single_symbol degraded）。

**Closure P2-02（原 ID GROK-R1-P2-02）— CLOSED**
- 碼：`sensitivity_micro`＝event 等權；`uniqueness_weighted` 獨立。
- 探針：兩相鄰事件 uniqueness_weight=0.5 → micro mean ≠ uniqueness mean。

### §0 前提攻擊（brief assumed）

| 前提 | 判定 | 證據 |
|---|---|---|
| **assumed**：GROK-R1-P1-01 採方案② loud 揭露續算（非拒算）；A′ 仍產報告；下游以 `conditional_ic_abandoned` 判 unavailable | **成立（攻擊不推翻）** | A′ 仍產 IC report＋survivor；metadata 三欄到位。攻擊點「survivor JSON 不含 abandoned 字串」：對照 `kind=full`／`degraded=true` vs 成功路徑 `kind=event`，standalone survivor 仍可機械區分；六鍵為嘗試過的 event_context 殘留、未把 kind 標成 event。方案②與 A′ 透傳契約一致；不另開 finding。 |
| **assumed**：B2.5 連續性以「決策 bar→窗末 open_time 差＝(h+k)×中位步長」足夠（crypto 連續網格） | **成立（攻擊不推翻）** | `_is_eligible` 端點差≠(h+k)·step ⇒ `missing_bar`；手跑連續 OK／缺口缺根；`test_grid_gap_counted_as_missing_bar` 綠。誠實邊界：非固定步長網格可能假陽性——本專案 crypto 錨定 TF 連續網格，與 brief／TODO 範圍一致；SPEC/TODO 重審＝不受理。 |
| fact-verified: 181 passed | **本輪複驗成立** | 見 TESTS_RUN |

## GROK-R2-P3-00

**斷言**: 本輪逐項核對後無 finding——GROK-R1-P1-01／P1-02／P2-01／P2-02 四條原反例均 CLOSED，修補 diff 未引入新的可證偽 P0–P2 缺陷；brief 兩條 assumed 攻擊不推翻。

**碼證**: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → **181 passed** rc=0（31.62s）；`git diff 9e168635..77140942 --stat -- momentum/ tests/` → 11 files +216/−39；A′ 手跑 `conditional_ic_abandoned=True`／`label_source=mainline_return_N`／`statistic_kind=conditional_ic_unavailable`；B2.2/B2.5 `common.formal_pooled_inference_allowed` 無 plan＝False；權重 0.5 時 `sensitivity_micro.mean≠uniqueness_weighted.mean`；連續網格 OK、缺口→`missing_bar`；A′ survivor `kind=full`＋`degraded=true` vs 成功 `kind=event`。

**來源摘要**: handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md#1b0044ca37a3；handoffs/20260821-gap3-b2-review-r1-grok.md#5cdad93444cb；momentum/Analysis/ic_filter_orchestrator.py#fb37d99fb693；momentum/Analysis/event_samples/tables.py#a0f52eebfd6b；momentum/Analysis/event_samples/all_bars_eval.py#d4c399431ec3；tests/momentum/event_samples/test_gap3_conditional_ic.py#05b18478c0ac；docs/GAP3_EVENT_TODO.md#df04bdabf37d；handoffs/20260821-gap3-b2-review-r2-brief.md#255d22e82f76

正文：閉合義務四條全 CLOSED；§0 兩 assumed 已攻；不受理 SPEC/TODO 重審／B3–B5／FF／B1 已蓋章。禁捏造湊數。

## 被當成事實的未驗證假設（§0）

無新增；brief 兩條 assumed 已攻擊（上表）。

ASSUMPTIONS_VERIFIED: GROK 四條 R1 修補落地；方案② loud 續算與 A′ 透傳一致；連續性端點檢對 crypto 網格足夠；181 passed；patch=77140942
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/event_samples/ tests/momentum/Analysis/test_survivor_contract.py -q` → 181 passed in 31.62s rc=0；A′／micro≠uw／continuity／AR-3 common 手跑探針
FAILURES_SEEN: none
SCOPE_CHANGES: none（禁改碼；只產本檔＋交接檔）
NUMERIC_OR_SCHEMA_IMPACT: none（review-only）
OUTPUT: handoffs/20260821-gap3-b2-review-r2-grok.md
HANDOFF_NOT_UPDATED: 根 HANDOFF.md 由 Claude 維護

## 戳記
RECONCILE-STAMP: grok APPROVED 2026-08-21 sha256:114bf200b87b26e6dcd799ee91f679357e049df1c821967362bcd8bb4b2557f5 task:20260821-GAP3-B2-REVIEW-R2

STATUS: DONE
