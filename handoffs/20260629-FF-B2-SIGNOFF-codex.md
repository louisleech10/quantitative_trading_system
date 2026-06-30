# FF B2 causality signoff - Codex leg

## Scope
- Role: independent signoff committee leg.
- Method: read Claude evidence + targeted code review only; no full-chain rerun.
- Inputs read: `HANDOFF.md`, `CLAUDE.md`, `handoffs/20260629-FF-B2-SIGNOFF-PROMPT.md`, `handoffs/20260629-FF-B2-CAUSALITY-SIGNOFF-CLAUDE.md`.

## A. FF causality signoff
**SIGN-OFF: FF-CAUSAL PASS.**

I agree with Claude's conclusion: the current evidence supports using Feature Factory for quantitative research from a causality/look-ahead standpoint. The remaining issues are reproducibility/feature-inventory caveats, not evidence of future leakage.

Evidence accepted:
- Full vs tail-truncated run keeps post-warmup prefix feature values stable; observed mismatch is bounded by roundtrip-safe float16 storage (`FeatureStorage.FLOAT16_MAX_REL_ERROR = 1e-3`, storage only downcasts when roundtrip error is within tolerance).
- Mutation probes for centered rolling, negative lag, and full-fit preprocessing are expected to fail by orders of magnitude beyond float16 tolerance.

Code review checks:
- L2 derived momentum uses positive historical shifts only: `series.shift(lag)` / `selected.shift(lag)` in `operators/derived_operators.py:401-408,576-582`.
- L2 WorldQuant/time-series operators use pandas rolling on the current row's trailing window; no `center=True` found in production path (`derived_operators.py:687-710`).
- L3 numba rolling updates state at `row_idx`, removes `row_idx - window`, and writes output only after the current trailing window is complete (`operators/numba_rolling.py:274-331`); rank/quantile helpers loop over `start=max(0,r-window+1)` through `r` (`_numba_transforms.py:52-77,191-215`).
- L4 lag processor uses positive lag sequences and `shift(lag)` in both fast and chunked paths (`operators/lag_processor.py:44-91`).
- L6.5 forces `causal_preprocessing=True` even if config asks otherwise (`feature_preprocessor.py:149-157`).
- L6.5 winsor/zscore/rank/gaussian use trailing rolling windows (`feature_preprocessor.py:2316-2349,2354-2388,3434-3468`).
- Fracdiff/ADF decision uses calibration prefix only (`_calibration_bars`, `_calibration_series`) and fixed-width convolution outputs begin at `first_valid + width - 1`; no bfill of initial warmup (`feature_preprocessor.py:175-178,3665-3685,3699-3772`).

Caveats agreed:
- float16 persistence means no bit-level reproducibility across windows/dtype flip boundaries. This is bounded by the documented storage gate and is not look-ahead.
- Column-set/NaN differences from row-count-dependent NaN/dead-feature handling remain a productionization concern. This belongs in the stateful-param-audit / persisted feature-list epic.

## B. B2 test design
**B2-DESIGN: 修正後同意.**

I agree with the direction, but the test should not keep exact columns or exact NaN masks as a hard invariant for the main values MR. Current helper shape still has exact columns and exact NaN-mask assertions (`tests/feature_engineering/test_ff_fullchain_truncation_mr.py:282-288,316-322,360-380`), which will false-red on the accepted row-count-dependent mechanisms.

Recommended main MR contract:
1. Columns: compare only the intersection for values, but fail if symmetric column difference is too large. Suggested initial threshold: `max(100 columns, 1% of union columns)`, with samples printed. Rationale: enough room for near-empty/dead-column churn, but too small to hide a layer disappearing.
2. Values: for each common column and rows `[warmup:n_trunc)`, compare only positions where both sides are non-NaN. Use `rtol=2e-3`, `atol=1e-12` as currently documented (`test_ff_fullchain_truncation_mr.py:41-46`).
3. NaN mask: do not require exact mask globally. Instead report total and per-column NaN-mask deltas, and fail if a common column has no both-non-NaN comparable cells post-warmup unless it is explicitly classified as near-empty/row-count-dependent. This keeps the test falsifiable.
4. Add a separate structural guard: common comparable-cell coverage must stay high enough. Suggested initial thresholds: at least 95% of common columns have one comparable post-warmup cell, and at least 99% of non-NaN-overlap cells compared among columns with overlap. These are audit gates, not value tolerances.
5. Keep mutation probes mandatory-red: centered rolling, full-fit winsor, negative L4 lag, fracdiff calibration perturbation, fracdiff full-fit d-star (`test_ff_fullchain_truncation_mr.py:659-805`). These directly answer whether relaxed NaN/column gates would allow true look-ahead.
6. Keep fracdiff as a dedicated stricter MR: d-star equality, fracdiff-column values with `atol=1e-8`, and exact fracdiff NaN mask are appropriate because the calibration design is the object under test.

Challenge answer:
- A true look-ahead can appear only in NaN mask if it merely gates availability without changing overlapping values. The main MR must therefore not ignore NaN masks completely; it should fail on large/common-column mask divergence or loss of comparable coverage, while leaving row-count-dependent near-empty columns informational.
- For value-producing look-ahead (centered rolling, negative lag, full-fit distribution stats), common-valid-region values will expose it, and existing mutation probes demonstrate that the 2e-3 tolerance is still strict enough.

## Tests run
- No full-chain tests rerun by instruction.
- Read-only commands only: `sed`, `rg`, `nl`, `git status --short`.

## Scope / impact
- Files changed: this handoff only.
- Root `HANDOFF.md` not updated because task prompt required writing only this committee handoff, and root `HANDOFF.md` already has unrelated local modifications.
- Numeric/schema impact: none from this signoff document.
