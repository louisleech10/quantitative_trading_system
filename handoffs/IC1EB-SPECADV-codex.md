# IC1EB SPEC/TODO Adversarial Review — Codex

TASK_ID: ic1eb-specadv-codex
SPEC: docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md
TODO: docs/IC_PHASE1_1E1B_SIGNIF_TODO.md
PLAN: N/A
REVIEW_FOCUS: 完整審查；D-A/D-C/D-E/D-H/full-stack/§A fact-vs-assumption

Verdict: REJECT

## Findings

### ADV-CODEX-1 [BLOCKING] Confidence: High
Evidence: SPEC D-A: `maxlags=max(自動頻寬, h-1)`; SPEC §G: `OLS z_t~1, cov_type=HAC`; TODO Task 1.1: `auto_bw=Newey-West 自動頻寬` and `p=2*sf(|t|, df=n_valid-1)`.
Problem: `auto_bw` is not a deterministic policy. Different agents can choose different Newey-West bandwidth rules, caps, or `use_t` behavior and produce different p/q/pass sets. Low-cost verify also shows statsmodels HAC default p-value uses normal distribution unless `use_t=True`, while TODO mandates t(df=n-1).
Failure consequence: Golden and implementation can disagree while both claim "statsmodels oracle"; pass/fail changes become implementation-defined.
Suggested fix: Specify exact `auto_bw(n_valid)` formula, integer rounding, `maxlags < n_valid` handling, explicit maxlags override behavior, and oracle as `fit(..., cov_type="HAC", cov_kwds={"maxlags": L}, use_t=True)` or manual `stats.t.sf` from the same HAC SE. Add a test asserting default statsmodels p != accepted oracle p unless `use_t=True`.
RECHECK: `source venv/bin/activate && python - <<'PY' ... OLS(z,1).fit(cov_type='HAC') vs use_t=True ... PY` should show the chosen oracle exactly.

### ADV-CODEX-2 [MAJOR] Confidence: High
Evidence: SPEC D-A: `z_t=u_t·v_t (Spearman ρ 的逐 bar 貢獻;mean(z)≈IC)`; TODO Task 1.1: `ic_hat=mean(z)`.
Problem: With sample-standardized ranks (`ddof=1`), `mean(u*v)` is `(n-1)/n * Spearman rho`, not exactly rho. This scaling cancels in a t-stat if SE is computed on the same z, but it does not cancel if `ic_hat`, bootstrap comparisons, or golden value hashes treat it as the IC estimate.
Failure consequence: Tests may compare the wrong point estimate or hide a scale discrepancy under "≈"; future code may overwrite/compare IC fields incorrectly.
Suggested fix: State the exact estimator: either use `sum(u*v)/(n-1)` for rho, or keep `mean(z)` only for HAC intercept testing and explicitly prohibit using it as a replacement for existing IC point estimates. Add tie-heavy test coverage.
RECHECK: Run the rank-product snippet in TESTS_RUN; output shows `mean_z_over_rho 0.98` for n=50.

### ADV-CODEX-3 [BLOCKING] Confidence: High
Evidence: SPEC D-H: `同一 kernel 對逐期 IC序列 ... NW maxlags 同 D-A 下限 h-1`; TODO Task 3.1: `h 由 _resolve_effective_label_horizon`; current code `analyze_cross_sectional` uses `_resolve_cross_sectional_label_horizon(label_col)` and returns 1 for non-`return_N` labels (`ic_filter_orchestrator.py:359-364`), while labels_path is assigned to internal `_label` (`:965-968`).
Problem: The cross_sectional plan does not specify how to preserve label horizon when `labels_path` supplies `return_5` but the working label column becomes `_label`. The existing path would resolve h=1, not h=5.
Failure consequence: HAC maxlags can be below the true overlapping-label dependency, making cross_sectional p-values anti-conservative while claiming D-H fixed them.
Suggested fix: In Task 3.1, carry `effective_horizon` before renaming labels to `_label`: resolve from `labels_df` selected column when labels_path is used, resolve from in-frame `return_N` when present, and fail closed when neither is parseable. Add a regression with cross_sectional labels_path containing `return_5` and assert maxlags lower bound is 4.
RECHECK: `nl -ba momentum/Analysis/ic_filter_orchestrator.py | sed -n '359,364p;947,990p'`.

### ADV-CODEX-4 [MAJOR] Confidence: High
Evidence: SPEC D-E: `low_confidence→α=max(p_value_max,0.10)`; TODO Task 2.2: same four-grid alpha policy.
Problem: Low-confidence/event-low-sample tier relaxes FDR alpha from 0.05 to 0.10. That is a product/statistical policy, not a technical necessity. It directly permits higher expected false discovery when sample confidence is lowest.
Failure consequence: The "顯著性正確化" knife can still select more noise in low-confidence regimes; reviewers may mistake this as mathematically corrected FDR rather than an intentional exploratory relaxation.
Suggested fix: Either keep FDR alpha fixed/stricter for low_confidence, or require explicit user-approved semantics: e.g. mark `selection_mode="exploratory_low_confidence"`, report `alpha_source`, and block production gate consumption unless explicitly enabled.
RECHECK: Inspect SPEC lines 31 and TODO lines 75/79; verify tests include low_confidence q=0.08 passing only under an explicitly named exploratory policy.

### ADV-CODEX-5 [MAJOR] Confidence: High
Evidence: SPEC D-G says backend schema `fdr.enabled=true`; TODO Task 4.1 defines `SignificanceSchema{fdr_enabled...}` and maps `fdr_correction→significance.fdr_enabled`; SPEC D-F says metadata `significance(...)`; D-G says report `fdr:disabled`.
Problem: The full-stack contract has four names/shapes for the same concept (`fdr.enabled`, `fdr_enabled`, `fdr_correction`, `fdr:disabled`) and no API model/schema assertion. This is exactly the class of ghost-toggle bug the knife is supposed to close.
Failure consequence: Frontend can send one key, backend schema can store another, reporter can emit a third, and e2e may pass only through config_override dicts while UI remains broken.
Suggested fix: Declare one canonical API path and report path, e.g. `significance.fdr.enabled`, `significance.fdr.method`, `significance.fdr.alpha_effective`. Map frontend `fdr_correction` to that path only at the UI boundary. Add tests at `icAnalysisStore.getEffectiveConfig` JSON, API request model, `_apply_tier_config`, stage5 consumption, and report metadata.
RECHECK: `rg -n "fdr_correction|fdr_enabled|fdr.enabled|fdr:disabled|significance" docs/IC_PHASE1_1E1B_SIGNIF_* frontend/src momentum/Analysis`.

### ADV-CODEX-6 [MAJOR] Confidence: High
Evidence: Existing TS type `ICFeatureInfo.p_value: number` (`frontend/src/lib/types.ts:1994-2006`); SPEC G-3: `p=NaN→p 閘 fail`; TODO Task 2.4: `NaN 序列化=null`; TODO Task 4.2 only adds `p_value_adj?: number|null; t_stat?: number|null`.
Problem: The nullable schema migration is incomplete. After fail-closed HAC, `p_value` can serialize as `null`, but frontend type still requires `number`. Existing UI also renders `{item.p_value?.toFixed(4)}` without `?? '--'`, so null/undefined display can be blank rather than explicit.
Failure consequence: TypeScript build or runtime UI can break on valid fail-closed results; old reports/new reports have inconsistent nullability.
Suggested fix: Change `p_value?: number | null` (and relevant API/DTO if present), add `p_value_adj?: number | null`, render both via a shared finite-number formatter returning `--`, and add old-report compatibility tests.
RECHECK: `nl -ba frontend/src/lib/types.ts | sed -n '1994,2006p'` and `nl -ba frontend/src/components/ic-analysis/ICSummaryTable.tsx | sed -n '430,445p'`.

### ADV-CODEX-7 [MAJOR] Confidence: Medium
Evidence: SPEC G-1: non-significance fields byte-equal by `.to_numpy().tobytes()` sha256; TODO Task 5.1 repeats sha256 equality.
Problem: Hashing only numeric matrix bytes omits index, column names/order contract, dtype map, and NaN mask as first-class artifacts. `.to_numpy()` can also coerce mixed dtypes, and equal values under swapped feature labels can escape if column metadata is not hashed.
Failure consequence: A regression that changes feature identity, row alignment, dtype, or null-mask semantics can pass G-1 while preserving numeric bytes.
Suggested fix: Hash a structured payload: index values, column names in order, dtype strings, value bytes per dtype block, and `isna()` mask bytes. Keep `.to_numpy().tobytes()` only as an additional value hash.
RECHECK: Review SPEC line 55 and TODO line 152; ensure G-1 artifact includes `index_sha256`, `columns_sha256`, `dtypes_sha256`, `nanmask_sha256`, `values_sha256`.

### ADV-CODEX-8 [MAJOR] Confidence: Medium
Evidence: TODO Task 5.1: `改前(git stash 或基準 commit 產物)vs 改後`; user task explicitly bans `git checkout/restore tracked 檔`; AGENTS forbids unsafe git/history operations and only output file may be written in this review.
Problem: Golden acquisition tells implementers to use git state mutation (`git stash`) or baseline commit without a safe, non-mutating procedure. In this repo's agent contract, that is an execution trap.
Failure consequence: An executor may mutate tracked files, lose user changes, or violate the "no checkout/restore" rule while trying to build old-vs-new golden.
Suggested fix: Replace with a safe baseline procedure: pre-implementation runner writes old reports/hashes to `handoffs/` or tmp, implementation reads those immutable artifacts; or use a separate disposable worktree outside the shared workspace only if explicitly approved by Claude/user. Do not mention `git stash` as a task step.
RECHECK: `nl -ba docs/IC_PHASE1_1E1B_SIGNIF_TODO.md | sed -n '148,156p'`.

### ADV-CODEX-9 [NON-BLOCKING] Confidence: Medium
Evidence: TODO Task 1.3: circular block bootstrap `B=2000`; Phase 1 gate includes statistical property tests; M-A uses 200 seeds and M-B 100 seeds.
Problem: Statistical tests with bootstrap B=2000 and hundreds of seeds may be slow/flaky unless acceptance bands, deterministic RNG, and runtime budget are specified per test tier.
Failure consequence: Agents may time out, shrink tests ad hoc, or produce non-reproducible red/green receipts.
Suggested fix: Define fixed seeds, binomial acceptance intervals in code, maximum runtime expectation, and mark long statistical tests separately if they exceed normal unit-test budget.
RECHECK: Inspect TODO lines 38, 51-56, 79, and Phase gates.

## §1 十類逐類結論
1. 矛盾/互斥: ADV-CODEX-1 (statsmodels oracle vs t df policy), ADV-CODEX-5 (FDR schema names).
2. 漏項/端到端: ADV-CODEX-3 (cross_sectional labels_path horizon), ADV-CODEX-5/6 (full-stack schema/nullability).
3. 不可測驗收: ADV-CODEX-1 (undefined auto_bw), ADV-CODEX-7 (incomplete golden hash), ADV-CODEX-9 (statistical test runtime/flakiness).
4. 可疑 quant 假設: ADV-CODEX-1/2/3/4.
5. 過度工程: 無；scope is large but matches a/b/d risk.
6. OOM/並行: 無 direct OOM issue; statistical seed/bootstrap runtime noted in ADV-CODEX-9.
7. Cache 正確性: data_cache read-only is specified; no direct cache-key issue found.
8. API/型別/相容: ADV-CODEX-5/6.
9. 測試品質: ADV-CODEX-1/3/7/9.
10. Agent 可執行性: ADV-CODEX-1/5/8.

## §2 錨點 + 空殼獵取
Required anchors present: §RISK, §A, §C, §G, §P, §V, §R, §N all present in SPEC.
§RISK: substantive; correctly declares a,b,d.
§A: mostly receipt-backed, but D-A/D-E contain assumptions elevated into decisions; see ADV-CODEX-1/2/4.
§C: consumer map substantive, but full-stack naming is not canonical; see ADV-CODEX-5.
§G: substantive golden plan, but G-1 hash is incomplete; see ADV-CODEX-7.
§P/§V: tasks are concrete; Task 1.1 auto bandwidth and Task 3.1 horizon are under-specified; see ADV-CODEX-1/3.
§R/§N: present and non-empty.
TODO §0: contains decoupling, data_cache, no fake-green, logging, and HAC/FDR constraints. It does not restate all seven decoupling rules, but the relevant subset is present.
Empty-shell findings: No pure empty section found; issues are substantive ambiguity rather than blank templates.

## §3 不可違反原則
Cross-tier repeatability: at risk until ADV-CODEX-1 defines deterministic bandwidth and p-distribution.
Multi-symbol stability/OOM: no direct violation found.
Data quality/no fake/no contamination: ADV-CODEX-4 risks selecting noise under low_confidence; ADV-CODEX-7 risks missing identity/alignment regressions.
No fake optimization/skip checks: no direct weakening found, but ADV-CODEX-8 could induce unsafe baseline workflow.

## 被當成事實的未驗證假設
- `mean(z)≈IC` is an approximation, not exact with the stated `ddof=1` rank z-score. VERIFY below shows `(n-1)/n` scaling.
- `maxlags=max(auto_bw,h-1)` is asserted as policy, but `auto_bw` is not defined.
- `low_confidence→α=0.10` is treated as technical migration of event tier, but it is a statistical/product policy that increases allowed FDR.
- cross_sectional D-H assumes h can be sourced like D-A, but current labels_path path renames label to `_label`; horizon is lost unless specified.

## VERIFY / TESTS_RUN
- `sed -n '1,220p' HANDOFF.md`; read current task state.
- `sed -n '1,260p' CLAUDE.md`; read project rules.
- `sed -n '1,260p' templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md`; read V13 review contract.
- `sed -n '1,260p' docs/IC_PHASE1_1E1B_SIGNIF_SPEC.md`; read full SPEC (109 lines).
- `sed -n '1,260p' docs/IC_PHASE1_1E1B_SIGNIF_TODO.md`; read full TODO (164 lines).
- `sed -n '1,220p' handoffs/IC1EB-RECON-{claude,codex}.md` and `sed -n '1,240p' handoffs/IC1EB-RECON-composer.md`; read three recon files.
- `sed -n '1,260p' docs/IC_PHASE1_1A_ALIGN_SPEC.md`; read 1-align precedent.
- `rg -n "def _base_universe_hash|SelectionScope|fdr_correction|..." momentum api frontend/src tests`; verified current source hooks and contract lines.
- `source venv/bin/activate && python - <<'PY' ... PY`; stdout summary: statsmodels 0.14.6; rank-product `mean_z_over_rho 0.98 expected 0.98`; HAC default p `0.110848...`, `use_t` and scipy t p `0.117278...`; custom BH matches statsmodels for finite p-values.
- `find data_cache/features -maxdepth 1 -type f | sed -n '1,20p'; test -f data_cache/feature_klines/kline_cache.h5 && echo kline_cache_exists`; stdout showed BTCUSDT files and `kline_cache_exists`.
- `rg -n "from api\\." momentum || true`; stdout empty, decoupling rule currently passes.

ASSUMPTIONS_VERIFIED: current source contains the cited hooks; statsmodels 0.14.6 installed; statsmodels HAC default p differs from t(use_t=True); rank-product scaling is `(n-1)/n`; BH finite-p output matches statsmodels; data_cache feature/kline paths exist; momentum has no `from api.` imports.
TESTS_RUN: read/rg/nl/python commands listed in VERIFY; no pytest/npm run because task is read-only SPEC/TODO review.
FAILURES_SEEN: none.
SCOPE_CHANGES: none; only wrote this review file.
STATUS: DONE
