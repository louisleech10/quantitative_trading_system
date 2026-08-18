# GAP-2 B2 stamp R16 — codex

task-id: `20260819-GAP2-B2-STAMP-R16`
判定: BLOCKED；未向 `handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md` append stamp。
阻擋: `inspect.signature(combine_factors)` 實跑為 `params: "'MarginalICParams'"`，brief 要求 `params: 'MarginalICParams'`；`fit_scope` annotation 符合。
body hash: `bash scripts/reconcile_body_hash.sh handoffs/reconcile/20260819-gap2-b2-review-r15/synth.md` → `9d0650065c052215ade7403008281ed981f548d67d323ffe9029669a3cfea5f2`，與 brief 相等。
1 completeness: `bash scripts/completeness_check.sh --lock handoffs/reconcile/20260819-gap2-b2-review-r15/sources.lock` → PASS；codex 2/2、composer 1/1、grok 1/1，0 掉項。
2 L1: `git show 127e8e77 -- momentum/Analysis/factor_combiner.py` 確認 CI 為 percentile 與 observed point 的 envelope；O2 三因子 `block_len=7, seed=1, n_bootstrap=1` containment 由兩檔測試覆核通過。
3 L2: runtime unknown `fit_scope`／`weights_method` 各 raise `ValueError`；typed signature 因 params annotation 不符而 BLOCKED。
4 probe: 未執行會就地 mutate/寫 receipt 的 probe（brief 禁 repo 寫）；既有 `handoffs/run_receipts/20260818T224246Z-gap2-B2-probe.log` 記錄 V-7/8/9 RED+RESTORED GREEN、post rc=0。
5 regression: `PYTHONDONTWRITEBYTECODE=1 venv/bin/python -m pytest -p no:cacheprovider tests/momentum/Analysis/test_marginal_ic.py tests/momentum/Analysis/test_factor_combiner.py -q` → 45 passed；`bash scripts/mutation_probe_check.sh tests/momentum/Analysis/test_factor_combiner.py` → PASS。
6 scope: `git diff d026fbed 127e8e77 --stat` 非 hook 產物符合 factor_combiner、兩測試檔、AMENDMENTS、handoffs、白話；R1 import grep 0。
未改程式、SPEC、TODO、target；未 commit/push。`/tmp/workdir` 不存在，無可清理項；未觸碰 repo stale probe lock（保留）。
STATUS: BLOCKED — L2 params annotation 不符合 stamp brief 的精確 signature 判準。
POSTCHECK: target body hash 仍相等；外部流程新增 composer／grok APPROVED stamps，本 agent 未新增 codex stamp。
