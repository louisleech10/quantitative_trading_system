ASSUMPTIONS_VERIFIED: Verified `insufficient_data` can fallback to full-sample with complete `summary_table`; verified fake `np.arange` timestamps now raise `TimestampDiscontinuityError`; verified sufficient real BTC/1h path marks `applied:true`.

TESTS_RUN:
- `pytest tests/momentum/Analysis/test_ic_1a_cut1_oos.py -q` → 13 passed
- `pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` → 33 passed, includes G-OLD and leakage tests
- `grep -rE "from api\\." momentum/ || true` → no output
- `pytest tests/api/test_ic_analysis_api.py -q -k "not deep and not export"` → failed, not timeout from OOS fallback; API task store remains `running` at progress 1.0 and result endpoint returns 404

FAILURES_SEEN: API round 1 failed on Binance ping during collection under restricted network; fixed test-local ping stub. API round 2 ran analysis but timed out because task status never becomes completed and result is 404.

SCOPE_CHANGES: No service code changed. BLOCKED because root cause now appears in `api/services/ic_analysis_service.py` task completion/result bookkeeping, outside the specified FIX3 scope.

NUMERIC_OR_SCHEMA_IMPACT: No numeric output changes intended. Metadata schema changed for OOS split marker to `requested/applied/oos_guarantees`; fallback reports use `applied:false` and no top-level `scope:test`.

HANDOFF_UPDATED: `handoffs/20260626-1a-cut1-FIX3-CODEX.md`

STATUS: BLOCKED — API test timeout requires approved scope expansion to API task result bookkeeping.