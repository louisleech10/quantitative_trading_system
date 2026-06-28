# BUG-2 Final Sign-off — Codex

SIGN-OFF: BUG-2 PASS

## Scope
- Reviewed closure of prior Codex HOLD for BUG-2 round3.
- Files inspected: `tests/feature_engineering/atomic/test_handcoded_reference.py`, `momentum/FeatureEngineering/atomic/volume_indicators.py`, `momentum/FeatureEngineering/atomic/entropy_indicators.py`, `momentum/FeatureEngineering/atomic/tail_risk_indicators.py`, `tests/feature_engineering/atomic/test_correctness_mode.py`, `tests/_golden/ff_deepaudit/handcoded_variant_diff.json`, `tests/_golden/ff_deepaudit/handcoded_v0_v1_diff.json`.

## Findings
- PASS: `_KLINGER_EXPECTED_VF` is not impl-derived on the face of the test: it is a literal array with a worked-bar comment. I independently recalculated all 8 bars from the Stock.Indicators-style formula and matched every value.
- PASS: production Klinger uses canonical round3 VF shape: `vf = volume * abs(2.0 * (dm / cm - 1.0)) * trend * 100.0`, with HLC trend comparison and cumulative measurement reset on trend change.
- PASS: entropy correctness guard is truly connected through `guard_indicator_compute(..., fail_open=self._fail_open)`, and `test_correctness_mode.py` has entropy and tail-risk fault-injection probes that prove off=warn/no raise and on=raise.
- PASS: §G v1 diff tables record both simplified v0→canonical v1 and round2 wrong→round3 correct. `handcoded_variant_diff.json` records `Klinger_round2_to_round3` with corr `-0.8045368540270721` and max abs diff `862969.1722874879`.

## Worked Example Recalculation
Formula used: `vf = V * abs(2 * ((dm / cm) - 1)) * trend * 100`; `trend` compares current `(H+L+C)` vs previous `(H+L+C)`; `cm` accumulates `dm` when trend is unchanged, otherwise resets to previous `dm + current dm`.

| bar | HLC | trend | dm | cm | expected VF |
|---:|---:|---:|---:|---:|---:|
| 0 | 33 | 1 | 2 | 2 | 0 |
| 1 | 38 | 1 | 3 | 5 | 48000 |
| 2 | 35 | -1 | 3 | 6 | -70000 |
| 3 | 41 | 1 | 3 | 6 | 80000 |
| 4 | 44 | 1 | 3 | 9 | 120000 |
| 5 | 38 | -1 | 3 | 6 | -75000 |
| 6 | 47 | 1 | 3 | 6 | 85000 |
| 7 | 50 | 1 | 3 | 9 | 126666.66666666667 |

These match `_KLINGER_EXPECTED_VF` exactly within the asserted tolerance.

## Tests Run
- `source venv/bin/activate && python - <<'PY' ...` independent literal recalculation: PASS, values above.
- `source venv/bin/activate && pytest tests/feature_engineering/atomic/test_handcoded_reference.py tests/feature_engineering/atomic/test_correctness_mode.py -q`: PASS, 25 passed.
- `source venv/bin/activate && bash scripts/mutation_probe_check.sh tests/feature_engineering/atomic/test_handcoded_reference.py tests/feature_engineering/atomic/test_correctness_mode.py`: PASS, 5 mutation probes passed. Script emitted one self-ref warning for `test_mutation_correctness_mode_off_vs_on` due registry/map mutation names, but did not fail; the BUG-2 Klinger and entropy/tail probes are still covered by real fault-injection/mutation assertions.

## Residual Notes
- No code changes made by Codex in this review.
- The broader worktree was already dirty before writing this file, including root `HANDOFF.md` and B1 implementation files. I did not modify or revert them.

ASSUMPTIONS_VERIFIED: Klinger worked example values independently recomputed; production Klinger formula inspected; entropy/tail correctness guards and probes inspected; target tests and mutation probe gate run.
TESTS_RUN: independent VF recalculation PASS; pytest target PASS (25 passed); mutation_probe_check PASS (5 probes passed).
FAILURES_SEEN: Initial `scripts/mutation_probe_check.sh` invocation without required path args printed usage only; rerun with explicit test paths passed.
SCOPE_CHANGES: none; review-only, added this handoff file only.
NUMERIC_OR_SCHEMA_IMPACT: none from this review; signed off BUG-2 numerical migration as recorded in §G diff tables.
STATUS: DONE
