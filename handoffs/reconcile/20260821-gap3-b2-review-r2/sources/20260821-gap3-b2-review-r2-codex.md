TASK_ID: 20260821-GAP3-B2-REVIEW-R2; FAMILY: codex; SCOPE: R1 修補 diff 9e168635..77140942 -- momentum/ tests/；review-only；禁改碼
## Verdict：需修補後再審；不可進三家 RECONCILE-STAMP
## CODEX-R2-P1-01
**斷言**: CODEX-R1-P1-01 NOT-CLOSED：B2.2/B2.5 common 只有旗標/模式名，沒有可機械核對的 cluster-CI 與宏/微實際報告。
**碼證**: `tables.py:61-82,211-249` 無 cluster-CI 欄；`all_bars_eval.py:153-180,183-207` 只有 overall/strata，CI 是逐 signal-row bootstrap；R1 新測試只驗 common flags/keys。RECHECK: `rg -n "cluster|macro|micro|ci" momentum/Analysis/event_samples/all_bars_eval.py momentum/Analysis/event_samples/tables.py`。
**來源摘要**: docs/GAP3_EVENT_TODO.md#df04bdabf37d; momentum/Analysis/event_samples/tables.py#a0f52eebfd6b; momentum/Analysis/event_samples/all_bars_eval.py#d4c399431ec3
MAJOR 信心度=High；TODO §B2 line 210 要求每張表/報告列 macro、micro、raw/effective n、cluster CI、degraded、LOSO/formal gate；修法需輸出實際欄位並以 cluster-aware negative test 鎖定。
## CODEX-R2-P1-02
**斷言**: CODEX-R1-P1-02 NOT-CLOSED：連續性仍以資料自身 median step 加端點差判定，且缺少的 entry semantic 會靜默變成 trigger_open。
**碼證**: `all_bars_eval.py:107-113` 先排序並以 `median(diff(open_time_ms))` 自訂網格，`:21-34` 只驗兩端差；`[0,2Δ,2Δ,4Δ]` 可通過而含 duplicate+missing bar，整體 `[0,2Δ,4Δ,...]` 亦無 expected-TF 參照；`:86,93` 未驗 k≥0 且 `get(...,"trigger_open")`。RECHECK: `nl -ba momentum/Analysis/event_samples/all_bars_eval.py | sed -n '21,113p'`。
**來源摘要**: docs/GAP3_EVENT_SPEC.md#544c2922ef2e; docs/GAP3_EVENT_TODO.D-001.md#69d05c3d05e6; momentum/Analysis/event_samples/all_bars_eval.py#d4c399431ec3
MAJOR 信心度=High；錯誤網格會進固定分母，缺 semantic 會改持有報酬 estimand；修法需用契約/TF expected step、逐鄰檢查/duplicate reject，並對 required semantic 與 offset fail-closed。
## CODEX-R2-P1-03
**斷言**: CODEX-R1-P1-03 NOT-CLOSED：survivor builder 對 partial event_context 不拒，validator 在未傳 report_meta 時也接受六鍵全 null。
**碼證**: `survivor_contract.py:467-474` 只在 `not event_context` 時拒；`:290-295` 只有 `report_meta.event_filter.label_source=event_label_value` 才驗 non-null；R1 測試 `test_conditional_ic_requires_event_context_fail_closed` 的 validator 路徑明確傳入 report_meta。RECHECK: `nl -ba momentum/Analysis/survivor_contract.py | sed -n '281,295p;459,475p'`。
**來源摘要**: handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md#1b0044ca37a3; momentum/Analysis/survivor_contract.py#7c0f75688555; tests/momentum/Analysis/test_survivor_contract.py#a66d2148f7c0
MAJOR 信心度=High；直接 builder/consumer 路徑仍可產生或接受不完整 provenance；修法需 builder 驗六鍵集合完整且 validator 從 payload/contract 可獨立判 conditional IC，並補不帶 report_meta/partial context 反例。
## CODEX-R2-P1-04
**斷言**: GROK-R1-P1-01 NOT-CLOSED：insufficient 分支雖設 conditional_ic_abandoned，但沒有下游消費，主線 return_N 仍流入正式 IC stages。
**碼證**: `ic_filter_orchestrator.py:2867-2873` 只寫旗標/label_source；`analyze():1030-1038` 隨後仍呼叫 `_stage4_ic_calculation`；`rg -n "conditional_ic_abandoned|conditional_ic_unavailable" momentum api` 未找到消費分支。RECHECK: `rg -n "conditional_ic_abandoned|conditional_ic_unavailable" momentum api --glob '*.py'`。
**來源摘要**: handoffs/reconcile/20260821-gap3-b2-review-r1/synth.md#1b0044ca37a3; momentum/Analysis/ic_filter_orchestrator.py#fb37d99fb693
MAJOR 信心度=High；方案② 的「下游以旗標判 unavailable」尚未實作，報告仍可能含主線數值；需讓下游明確輸出 unavailable/阻止 conditional survivor，並以 A′ 測試鎖定無可消費 numeric conditional IC。
ASSUMPTIONS_VERIFIED: CODEX-R1-P2-04 CLOSED（validator 使用 import contract accepted）；CODEX-R1-P2-05 CLOSED（override 有 np.isfinite gate）；GROK-R1-P2-02 CLOSED（sensitivity_micro 等權、uniqueness_weighted 獨立）；上述以現行碼證核對，未宣稱 pytest 重跑。
TESTS_RUN: `git diff --check 9e168635..77140942 -- momentum/ tests/` → rc=0；`rg` 靜態 recheck 如各 finding 所列；acceptance pytest 與 golden --check 依 brief 未重跑。
FAILURES_SEEN: none。SCOPE_CHANGES: none；未改產品碼、測試、SPEC/TODO 或 data_cache；僅新增本交件檔。NUMERIC_OR_SCHEMA_IMPACT: review-only，未改輸出。
HANDOFF_OUTPUT: handoffs/20260821-gap3-b2-review-r2-codex.md
RECONCILE-STAMP: codex APPROVED 2026-08-21 sha256:819d918d0ef4a6125f09cdd952ea8116d3e6a232bffef4d1cd0d6a852320cc22 task:20260821-GAP3-B2-REVIEW-R2
STATUS: DONE
