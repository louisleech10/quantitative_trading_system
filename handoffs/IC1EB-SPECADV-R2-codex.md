# IC1EB SPECADV R2 Codex
TASK_ID: ic1eb-specadv-r2-codex
SOURCE: docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md v2 + TODO v2 + handoffs/IC1EB-SPECADV-codex.md

Verdict: REJECT

## ADV-CODEX closure
- ADV-CODEX-1 CLOSED. SPEC D-A lines 55-58 fixes auto_bw=`int(4*(n/100)**(2/9))`, L=max(auto_bw,h-1), cap/fail-closed, p=t(df=n-1), oracle `use_t=True`, M-I; TODO lines 31-40 mirrors formula/tests. VERIFY: statsmodels 0.14.6 `maxlags=None` SE equals spec lag for n=32/64/100/512; default Normal p 0.009334 != oracle t p 0.014168.
- ADV-CODEX-2 CLOSED. SPEC line 53 states mean(z)=(n-1)/n*rho and bans IC replacement/golden hash; TODO line 32 repeats internal-only rule. VERIFY rank-product n=50 ratio 0.98.
- ADV-CODEX-3 CLOSED. SPEC line 66 and TODO lines 114-118 require horizon before `_label`, fail-closed unresolved metadata, and M-J return_5 maxlags>=4. Current code lines 965-968/989 confirm old bug shape; `_select_label_series` returns Series retaining original column name, so task is implementable.
- ADV-CODEX-4 CLOSED. SPEC line 63 and TODO lines 77/81 require `alpha_source`, `selection_mode="exploratory_low_confidence"`, marginal=p_value_max, and six-grid tests.
- ADV-CODEX-5 STILL-OPEN. SPEC line 64 and TODO lines 93/126/130 establish canonical `significance.fdr.*` and every-hop tests, but SPEC line 65 still says report marks OFF as `fdr:disabled`, reintroducing a fourth report shape/name contradicting "禁第四種名字". Task 4.3 line 142 also uses `threshold_log.fdr_enabled`, though Task 2.2 line 77 already has `fdr_enabled`; this may be internal log but should be reconciled with canonical wording.
- ADV-CODEX-6 CLOSED. SPEC line 64 and TODO lines 134/137 require `p_value?: number|null`, `p_value_adj?: number|null`, `t_stat?: number|null`, finite formatter `'--'`, and old report compatibility.
- ADV-CODEX-7 CLOSED. SPEC line 87 and TODO line 154 require five hashes: index/columns/dtypes/nanmask/values, with numpy value bytes only additional.
- ADV-CODEX-8 CLOSED. SPEC line 89 and TODO lines 10/154/156 replace git baseline operations with pre-produced read-only `handoffs/ic1eb_baseline/`; no git checkout/stash/restore baseline step remains.
- ADV-CODEX-9 CLOSED. SPEC lines 121-122/131 and TODO lines 11/40/54/81 define fixed seeds, binomial 95% bands, `slow_stat`, B=2000, and per-test budget requirement.

## NEW-ISSUE
- NEW-CODEX-R2-1 [BLOCKING] Same as ADV-CODEX-5 residual: SPEC D-G `fdr:disabled` conflicts with canonical `significance.fdr.{enabled,method,alpha_effective}`. This can recreate the ghost-toggle class at report consumption; fix by expressing OFF only as `significance.fdr.enabled=false` plus canonical metadata.

ASSUMPTIONS_VERIFIED: statsmodels 0.14.6 installed; v2 auto_bw matches statsmodels `maxlags=None`; statsmodels default HAC p uses Normal and differs from `use_t=True`; rank-product mean(z)/rho is 0.98 at n=50; current xsec code still renames labels_path to `_label` before old horizon resolver; `_select_label_series` preserves selected Series.name.
TESTS_RUN: `sed -n` read HANDOFF.md/CLAUDE.md/original R1 handoff/SPEC/TODO; `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '340,375p;940,1005p;2458,2505p'`; `rg -n ... docs/IC_PHASE1_1E1B_SIGNIF_*`; Python statsmodels/rank-product verifier passed with outputs summarized above. No pytest/npm because task is read-only SPEC/TODO review.
FAILURES_SEEN: none during verification; review finding is a SPEC/TODO closure failure, not command failure.
SCOPE_CHANGES: none; only wrote this handoff file.
STATUS: DONE
