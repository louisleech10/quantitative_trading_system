# IC1EB 統計嚴謹度諮詢 — Codex
Task: ic1eb-rigor-codex | Date: 2026-07-09 | Mode: read-only, only this handoff written

## Q1 檢定層
結論: bar-level Spearman contribution series + Newey-West/Bartlett HAC t-test is a defensible default for feature-level IC screening. It is the econometrics standard for a mean/intercept test under heteroskedasticity and autocorrelation; statsmodels documents `cov_hac` as Newey-West HAC with Bartlett default and the same automatic lag formula used by SPEC (`floor[4(T/100)^(2/9)]`): https://www.statsmodels.org/stable/generated/statsmodels.stats.sandwich_covariance.cov_hac.html. The key design win is abandoning overlapping rolling-IC pooled i.i.d. t-tests, which are the actual anti-rigorous part in current code (`statistical_validator.py` pools rolling windows then `ttest_1samp`).
必須升級? No for this knife. Stationary/bootstrap kernels are useful robustness checks, but making stationary bootstrap the production primary kernel would add block-length/randomness/compute instability without clearly improving the default screen. SPEC's circular block bootstrap as test-side validation leg is the right minimum.

## Q2 多重比較層
結論: BH is acceptable as this knife's default if applied to the full finite-p evaluated set and guarded by property tests; do not switch default to BY. BH is standard, powerful, and statsmodels classifies `fdr_bh` as Benjamini/Hochberg for non-negative dependence while `fdr_by` is the Benjamini/Yekutieli dependence-conservative variant: https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html. Correlated factor libraries are usually positively dependent in clusters; PRDS is not provable from code, but it is a plausible working assumption when paired with empirical M-B FDR simulation and SelectionScope.
BY: controls arbitrary dependence but pays harmonic/log penalty; with hundreds/thousands of features it is likely too conservative for a research gate. Romano-Wolf/Westfall-Young stepdown: statistically attractive because resampling can preserve dependence and targets FWER/stepdown error control; literature convention: Westfall-Young resampling, Romano-Wolf stepdown/data-snooping. Recommendation: default remains BH for 1e+1b; register `fdr_method = by` and `stepdown_method = romano_wolf|westfall_young` as later optional strict modes, not in this knife.

## Q3 更上層 data-snooping
同意: White Reality Check, Hansen SPA, Deflated Sharpe, and PBO/CSCV are strategy/backtest/model-selection data-snooping controls, not feature IC screen controls. They belong in a separate strategy/backtest epic. This repo already names these in `docs/TEST_DESIGN_CHARTER.md` under strategy/backtest, not IC selection.

## Q4 其餘統計面盤點
ICIR/hit_rate thresholds: `ic_engine.py:305-330` computes `icir=mean/std` and hit rate; `ic_filter_orchestrator.py:2587-2598` gates on fixed thresholds. Verdict: acceptable descriptive/ranking statistics for this knife, but high priority later calibration/documentation because they are selection gates without inferential uncertainty.
monotonicity_tester: `monotonicity_tester.py:78-121` uses independent two-sample `ttest_ind` for high vs low quantile returns, while monotonicity score itself is descriptive. Verdict: material statistical risk if pvalue is ever displayed/used as inference; currently gate consumes score/spread, not long-short pvalue. Roadmap P1: HAC/block-bootstrap long-short spread inference or mark pvalue descriptive.
ic_decay: `ic_engine.py:332-365` and `:915-964` fit `A exp(-lambda h)+C`, report r2, half-life, warning. Verdict: acceptable descriptive diagnostic; not a significance test. Roadmap P2: uncertainty bands only if used for selection.
grouped IC: `ic_engine.py:381-440` computes subgroup ICs by year/quarter/regime/metadata without subgroup inference; SPEC explicitly keeps grouped values byte-stable. Verdict: acceptable descriptive statistics, but P1 if UI/report compares groups as "robust"; add subgroup n and uncertainty later.
event tier sample rule: `event_filter.py:93-144` is an engineering sample-tier rule returning 0.05/0.10, not a power/sample-size calculation. SPEC D-E correctly migrates this to alpha policy with explicit exploratory low_confidence metadata. Verdict: covered by current knife enough; later improvement is power-based sample-size policy.
SelectionScope: contract exists in `contracts.py:724-742` and tests, but current production has no use; SPEC Task 2.3 covers it. Verdict: covered by current knife.
cross_sectional p/t: `ic_filter_orchestrator.py:1040-1095` currently computes i.i.d. t_stat over time slices and `p_value=None`; SPEC D-H covers minimal HAC p/q. Verdict: covered by current knife.

## Q5 總裁決
RIGOR-VERDICT: FREEZE-OK
理由: SPEC v2.1 is rigorous enough for the IC feature-screening layer: it fixes the main invalid test, adds full-evaluated-set BH-FDR, fail-closed NaN behavior, SelectionScope auditability, statsmodels oracle checks, and bootstrap validation tests. Minimal amendment is not required before freeze. Non-blocking roadmap registrations: BY method option, Romano-Wolf/Westfall-Young strict stepdown option, monotonicity long-short HAC/bootstrap inference, grouped/subsample uncertainty, and strategy-layer Reality Check/SPA/Deflated Sharpe/PBO epic.

ASSUMPTIONS_VERIFIED: read `HANDOFF.md`, `CLAUDE.md`, SPEC v2.1, TODO; code-read receipts: `statistical_validator.py`, `monotonicity_tester.py`, `event_filter.py`, `ic_engine.py`, `ic_filter_orchestrator.py`, `contracts.py`; external convention receipts: statsmodels HAC/multitest docs plus FDR/FWER literature names.
TESTS_RUN: read-only consultation; no pytest/build run. Commands used include `sed -n` on required docs and target code, `rg -n` for IC statistical callsites, and web lookups for statsmodels/literature convention receipts.
FAILURES_SEEN: `sed momentum/Analysis/ic_decay_analyzer.py` failed because decay lives in `momentum/Analysis/ic_engine.py`; resolved by `rg --files momentum/Analysis` and targeted reads.
SCOPE_CHANGES: none; no production/test/docs changes; only `handoffs/IC1EB-RIGOR-codex.md` written.
NUMERIC_OR_SCHEMA_IMPACT: none from this consultation.
STATUS: DONE
