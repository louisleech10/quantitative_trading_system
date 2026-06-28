# FF B1 BUG-2 Formula Signoff — Codex

## Signoff

SIGN-OFF: BUG-2 HOLD

主因：現行 `Klinger` implementation 仍不符合我能獨立查到的 canonical KVO volume force 公式；`ForceIndex` 公式可簽 PASS，但 BUG-2 整體不能過。

## Formula Evidence

### Klinger Volume Oscillator

Reviewed implementation:
- `momentum/FeatureEngineering/atomic/volume_indicators.py::_compute_klinger`
- `tests/references/volume_indicators_ref.py::klinger_canonical`

Verified issue:
- Production `vf = volume * (2 * (dm/cm) - 1) * trend * 100`
- Reference has the same `cm` and `vf` logic, so `impl == ref` is self-referential and does not prove formula correctness.

Independent published implementation evidence:
- Stock.Indicators Python docs define KVO default periods as fast 34 / slow 55 / signal 13 and link to its C# core source: https://python.stockindicators.dev/indicators/Kvo/
- Stock.Indicators C# core computes trend from `High + Low + Close`, `dm = High - Low`, `cm = same trend ? previous cm + dm : previous dm + dm`, and `vf = Volume * Math.Abs(2 * ((dm / cm) - 1)) * trend * 100`: https://github.com/DaveSkender/Stock.Indicators/blob/main/src/e-k/Kvo/Kvo.Series.cs

Conclusion:
- Trend basis `(H+L+C)` is consistent.
- CM reset logic is broadly consistent.
- VF magnitude is not consistent: canonical source uses `Abs(...)`; production does not.
- There is also a formula-shape discrepancy: source uses `2 * ((dm/cm) - 1)`, not production's `(2 * (dm/cm) - 1)`.

Real-data check:
- Command: custom Python one-off using `create_kline_storage_manager(cache_dir='data_cache/feature_klines').read_klines('BTCUSDT','12h')`, first 600 rows.
- Current Klinger vs abs/source-shape Klinger: `valid=546`, `corr=-0.8243019307224514`, `max_abs_diff=654473.5349729315`.
- This is material, not warmup noise.

### ForceIndex

Reviewed implementation:
- `raw = close.diff() * volume`
- `talib.EMA(raw.values, timeperiod=13)`

Independent source:
- Investopedia describes Force Index as today's close minus yesterday's close times today's volume, with EMA smoothing and a 13-day EMA for longer-term use: https://www.investopedia.com/articles/trading/03/031203.asp
- The `ta` Python library implements Force Index as `(close - close.shift(1)) * volume`, then EMA window 13 by default: https://raw.githubusercontent.com/bukosabino/ta/master/ta/volume.py

Conclusion:
- ForceIndex formula is PASS.
- My one-off check confirmed production equals the same TA-Lib EMA path with `max_abs_diff=0.0`.

## Code Review Findings

### BLOCKING: Klinger Formula Still Wrong

`volume_indicators.py` lacks absolute value in VF and appears to use the wrong parenthesization relative to the independently checked source. The existing reference test cannot catch this because the reference copies production logic.

Impact:
- `hlcv_volume_Klinger_34_55` values change materially from the checked canonical implementation.
- Current `test_klinger_matches_canonical_reference` is a false confidence test.

### BLOCKING: Oracle Is Not Independent

`tests/references/volume_indicators_ref.py::klinger_canonical` shares the same algorithm structure as production, including `_klinger_cumulative_measurement` and VF expression. It is acceptable as a mirrored implementation smoke test, but not as a formula oracle.

Better oracle options:
- A small checked table with hand-derived OHLCV, dm, trend, cm, vf, ema34, ema55, kvo values.
- Or a pinned comparison against a published implementation such as Stock.Indicators for a small fixture, with version/source documented.

### HIGH: Correctness-Mode Coverage Is Not Actually All Touched Engines

`test_correctness_mode.py` covers seven TA-Lib-backed engines plus microstructure. However this diff also touches `tail_risk_indicators.py` and `entropy_indicators.py`.

Observed:
- `tail_risk_indicators.py` now uses `guard_indicator_compute`, but has no correctness-mode fault-injection test in the reviewed file.
- `entropy_indicators.py` stores `_fail_open` but does not use `guard_indicator_compute` around compute methods, so correctness-mode behavior is not actually exercised there.

This is not the main BUG-2 blocker, but the claim "補全 8 engine" should not be treated as full coverage for all changed atomic engines.

### Schema / §G

ForceIndex and Klinger metadata removing `variant=simplified` is directionally correct only after formulas are actually canonical. ForceIndex qualifies; Klinger does not yet.

The v0→v1 diff table exists, but because Klinger v1 is not canonical, it currently documents migration to a still-wrong variant.

## Tests / Commands

TESTS_RUN:
- `sed`/`nl`/`rg` review of `HANDOFF.md`, `CLAUDE.md`, signoff prompt, production code, references, tests, and B1 result notes.
- Web verification of ForceIndex and KVO implementation references.
- One-off real-kline Python comparison: PASS as diagnostic command; showed Klinger mismatch vs abs/source-shape formula.

FAILURES_SEEN:
- First one-off script used nonexistent `load_klines`; corrected to `read_klines` after reading storage API.

SCOPE_CHANGES:
- none; only this review file was added by Codex.

NUMERIC_OR_SCHEMA_IMPACT:
- Review only. Finding indicates current Klinger numerical output is materially non-canonical; ForceIndex canonical output is acceptable.

ASSUMPTIONS_VERIFIED:
- Production and test reference Klinger are not independent.
- ForceIndex uses EMA13 of `(close - prev_close) * volume`.
- Current Klinger differs materially from independently checked abs/source-shape KVO on real BTCUSDT/12h kline.

STATUS: DONE
