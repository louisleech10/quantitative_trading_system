# Reconcile — 20260819-gap2-b2-review-r15

**來源** 20260819-gap2-b2-review-codex.md, 20260819-gap2-b2-review-composer.md, 20260819-gap2-b2-review-grok.md　|　**roster** codex,composer,grok

## 群集 / 處置（Claude 填，2026-08-19）

三家共 **4 條**（codex 2：1 MAJOR／1 MINOR；composer sentinel；grok sentinel），下列三個群集**引用全部 4 條，0 掉項**。Verdict：codex「需修補後進 B3」、composer／grok「可進 B3」⇒ 依較嚴：**需修補後進 B3**；2 條全接受，修補走 B2 修補 commit（A1-8 記錄 bootstrap CI 納入觀測統計量之定義）；戳記輪 r16 兼修補驗收。

Verdict：需修補後進 B3——修補 commit 落地後派 stamp r16（含 codex 反例重跑）；APPROVED ⇒ B2 CLOSED → B3。

### L1 — `delta_ci95`（及 B1 `ci95`）percentile CI 不保證含點估；`n_bootstrap=1` 反例可重現
**引用**: CODEX-R15-P1-01
**處置＝接受**：`block_bootstrap_ci` 之分佈**納入觀測統計量**（identity replicate：`out=[stat_fn(*arrays)]` 起始，再加 `n_bootstrap` 個 block 重抽）⇒ CI 恆含點估（`n_bootstrap=1` 亦然）；`marginal_ic.ci95` 同源受惠；O9 加 `n_bootstrap=1` containment 迴歸（兩檔）；原「`n_bootstrap=1` ⇒ `ci[0]==ci[1]`」斷言改為「含點估且 lo≤hi」；A1-8 記錄定義（SPEC O9「CI 含點估」之保證來源）。

### L2 — `combine_factors` 簽名 `params: Any`／`fit_scope: str` 放寬 TODO typed 介面
**引用**: CODEX-R15-P2-02
**處置＝接受**：改 `params: "MarginalICParams"`（`TYPE_CHECKING` 匯入防循環）、`fit_scope: Literal["train","full_sample"]`；runtime guard 不變。

### L3 — 收斂 sentinel（composer／grok）：可進 B3
**引用**: COMPOSER-R15-P3-00, GROK-R15-P3-00
**處置＝接受（記錄）**：段 B 八問兩家獨立重判皆可接受；與 L1／L2 修補不衝突（皆為收緊）。

---

## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）

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
## COMPOSER-R15-P3-00

**斷言**: 本輪對 commit `d026fbed` 段 A–E 與段 B 八項實作期決定逐項核對後，無達 BLOCKING／MAJOR／MINOR 門檻之可證偽缺陷。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0 V-7/8/9 RED+GREEN；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；O4 composite=0.594695 ratio=0.991396 margs∈[0.28,0.31]；O7 composite=−0.499590==sign(train)·gross；`to_dict()` 鍵集==`composite_keys`；`git diff 35bd66a1 d026fbed -- marginal_ic.py` 僅 bootstrap 搬移。

**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0

本輪核對依據：Task 2.1 實作要點 1–6／不可做／邊界／驗證逐條對照 `factor_combiner.py`；段 B 八問獨立重判（complete-case、test_ic_all 位置、NaN/0、tie-break、lazy import、insample、成對 bootstrap、O4 加法性）；mutation 探針與 §G oracle 本機重跑；`marginal_ic` diff 確認 B1 契約未被觸動。未發現需修補後才能進 B3 之項。

---

## GROK-R15-P3-00

**斷言**: 本輪對 commit `d026fbed` 段 A–E（含段 B 八項實作期決定）逐項核對後無 finding。

**碼證**: `venv/bin/python -m pytest tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed rc=0；`bash scripts/gap2_mutation_probe.sh --batch B2` → rc=0（V-7／8／9 RED+RESTORED GREEN；receipt `handoffs/run_receipts/20260818T222930Z-gap2-B2-probe.log`）；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS；O4 composite=0.594695、ratio=0.991396、margs∈[0.2806,0.3081]；O7/O8 composite=−0.499590 == sign(train_ic)·gross；`CompositeResult.to_dict()` 鍵集 == 契約 `composite_keys`（18）；`git diff 35bd66a1 d026fbed -- momentum/Analysis/marginal_ic.py` 僅 bootstrap 搬移＋re-export；雙 import 序 `block_bootstrap_ci` identity；R1 grep 0 命中。

**來源摘要**: momentum/Analysis/factor_combiner.py#2c0dccc7de80；docs/GAP2_MARGINAL_IC_TODO.md#100695426a6c；docs/GAP2_MARGINAL_IC_SPEC.md#2ac97f02dc1d；momentum/Analysis/contracts/ic_survivor_contract.json#a6d68a5a7ff0；tests/momentum/Analysis/test_factor_combiner.py#becfc45d514f；scripts/gap2_mutation_probe.sh#65fea620d5af

核對依據：Task 2.1 要點 1–6／不可做／邊界／驗證對照源碼；段 B 八問獨立重判（complete-case train、test_ic_all 位置、NaN/0、tie-break、lazy import、insample、成對 bootstrap、O4 加法性視角）；mutation 與 §G oracle 本機重跑；registry 四殘留觸發未成立。未發現需修補後才能進 B3 之項。

---


## 戳記

（待三家 append RECONCILE-STAMP）
RECONCILE-STAMP: composer APPROVED 2026-08-19 sha256:9d0650065c052215ade7403008281ed981f548d67d323ffe9029669a3cfea5f2 task:20260819-GAP2-B2-STAMP-R16
RECONCILE-STAMP: grok APPROVED 2026-08-19 sha256:9d0650065c052215ade7403008281ed981f548d67d323ffe9029669a3cfea5f2 task:20260819-GAP2-B2-STAMP-R16
RECONCILE-STAMP: codex APPROVED 2026-08-19 sha256:9d0650065c052215ade7403008281ed981f548d67d323ffe9029669a3cfea5f2 task:20260819-GAP2-B2-STAMP-R17
