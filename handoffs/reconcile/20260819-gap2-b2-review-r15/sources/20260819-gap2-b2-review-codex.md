## Verdict：需修補後進 B3
段 A：六項實作、契約 composite_keys、fit_scope、train-only 符號/權重、非 OLS/Ridge、best_single_test_ic 參考語意均對齊；介面型別另列 P2。
段 B：train 與 test 共用 survivors+label finite mask 是保守且無洩漏的共同樣本選擇；test_ic_all 只進參考欄；NaN/0 reason、原序 tie、lazy private import、train in-sample z、paired CI 均可接受，無新增 finding。
段 C：45 tests passed；V-7/V-8/V-9 各 RED 且還原 GREEN；獨立 block 參考與檔內 seam 真跑；O4 非廉價綠、無 skip/只驗不 crash。
段 D：O4 composite=0.594694902761；sequential marg=[0.308133378783,0.280552595884,0.297057664407,0.297858744084]；ratio=0.991395735062；O7 composite=-0.499590104332=(+1)*gross，符合 SPEC 帶寬。
段 E：G2-R1/R2/R3/R5 觸發條件均未成立，B2 未接 ML、未做二次選擇、未接 xsec、未宣稱獨立 OOS。
## CODEX-R15-P1-01
**斷言**: `delta_ci95` 未保證包含點估；契約允許的 `n_bootstrap=1` 會產生不含 `delta_vs_top_train_single` 的 CI。
**碼證**: `factor_combiner.py:263-269` 直接以 bootstrap quantile 回傳 CI；VERIFY: in-memory O2 (`n=5000, block_len=7, seed=1, n_bootstrap=1`) → `delta=0.173269228317`, `ci=(0.169712579717,0.169712579717)`, `contains=False`；TODO:128 要求 CI 含點估且列 n_bootstrap=1 邊界。
**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80; docs/GAP2_MARGINAL_IC_TODO.md#100695426a6cb; docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d
[MAJOR] 信心度=10/10；這是可重現的數值契約違反，不是統計假設；修正需讓 observed delta 進入 CI envelope（或等價地調整 helper API），並新增 n_bootstrap=1 containment regression。
## CODEX-R15-P2-02
**斷言**: `combine_factors` 的實際介面把 TODO 要求的 `params: MarginalICParams`／`fit_scope: Literal["train","full_sample"]` 放寬成 `Any`／`str`，失去靜態契約守衛。
**碼證**: `factor_combiner.py:149-158`；VERIFY: `inspect.signature(combine_factors)` → `params: 'Any', fit_scope: 'str'`；TODO:114-116 明列 typed signature。
**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80; docs/GAP2_MARGINAL_IC_TODO.md#100695426a6cb
[MINOR] 信心度=10/10；clean runtime 不受影響，但 B4 caller 可傳入未約束物件；以 `Literal` 與 `MarginalICParams`（可在 TYPE_CHECKING 下避免循環）恢復精確註記，並保留現有 runtime guard。
ASSUMPTIONS_VERIFIED: SPEC/TODO/AMENDMENTS 已讀；前置 stamps 最終均 APPROVED；commit=d026fbed；registry 四條殘留觸發均未成立。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed；`bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；雙 import 順序 identity=True；factor_combiner API grep 無命中。
FAILURES_SEEN: stale probe lock 首次重試 rc=3；確認 owner PID 不存在後最小清理並以 PTY 完整重跑 rc=0；未修改 source/SPEC/TODO。
SCOPE_CHANGES: review-only；新增本交件檔；probe 產生 receipt `handoffs/run_receipts/20260818T223216Z-gap2-B2-probe.log`，未碰既有 dirty 檔或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: 未改程式；發現 delta CI 邊界數值契約缺口與型別介面缺口。
HANDOFF_OUTPUT: handoffs/20260819-gap2-b2-review-codex.md
STATUS: DONE
