# FRACDIFF-MAXLAG B0 Task 0.1 — Codex handoff

ASSUMPTIONS_VERIFIED:
- Read `HANDOFF.md`, `CLAUDE.md`, `AGENTS.md`, `docs/FRACDIFF_MAXLAG_SPEC.md`, `docs/FRACDIFF_MAXLAG_TODO.md`.
- Verified run contract helpers exist: `_fracdiff_mr_config_payload()` and `_fracdiff_window_bars(...)`; current window resolves to 2081 bars.
- Verified real kline cache exists at `data_cache/feature_klines/kline_cache.h5`.
- Verified current production auto max_lag path is still `len(df)//10` capped at 252; `DStarCache` payload records `fracdiff_hash`, `max_lag`, `row_count`, `time_range`, and `stats()`.

TESTS_RUN:
- `PYTHONPYCACHEPREFIX=/tmp/fracdiff_pycache python -m py_compile tests/feature_engineering/ff_maxlag_golden_helpers.py scripts/freeze_fracdiff_maxlag_golden.py` — pass.
- Lightweight digest import smoke — pass (`row_count=2`, `column_count=2`).
- `PYTHONPYCACHEPREFIX=/tmp/fracdiff_pycache python scripts/freeze_fracdiff_maxlag_golden.py` — interrupted/failed before any golden JSON receipt; log at `handoffs/run_receipts/20260703T014400Z-fracdiff-maxlag-golden-G1.log`.

FAILURES_SEEN:
- Initial script did not set `FFACT_CGSA_WORK_DIR`; FeatureFactory default wrote CGSA scratch under ignored `data_cache/cgsa_work/BTCUSDT_1h_b0102a55`, violating AGENTS data_cache redline.
- Run was stopped with KeyboardInterrupt during first BTCUSDT G1 run before digest/parquet receipt completion.
- Script was patched afterward to isolate CGSA work under per-run artifact dir and suppress pandas fragmentation warnings, but not rerun due redline violation.

SCOPE_CHANGES:
- Added allowed non-production files: `tests/feature_engineering/ff_maxlag_golden_helpers.py`, `scripts/freeze_fracdiff_maxlag_golden.py`.
- Added failed run log/artifacts under `handoffs/run_receipts/`.
- No production files under `momentum/` modified.

NUMERIC_OR_SCHEMA_IMPACT:
- No production numeric/schema behavior changed.
- No G1/G2 golden baseline frozen; validation conditions not satisfied.

BLOCKER:
- AGENTS redline was hit by creation/modification of `data_cache/cgsa_work/BTCUSDT_1h_b0102a55`; per contract, stop and return `STATUS: BLOCKED`.
