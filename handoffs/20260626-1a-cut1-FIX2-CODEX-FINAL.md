Implemented FIX2 in [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py).

Changed:
- `_slice_by_mask` now slices labels positionally with `iloc`, so mismatched feature/label indexes no longer crash.
- Added raw kline positional OOS slicing for stage4 decay/grouped IC, fixing the follow-on real-run NaN timestamp failure.
- `ic_train_test_split` remains default OFF.
- Wrote progress handoff: [20260626-1a-cut1-FIX2-CODEX.md](/Users/louis/Desktop/quantitative_trading_system/handoffs/20260626-1a-cut1-FIX2-CODEX.md)

ASSUMPTIONS_VERIFIED: `label_series` can have a different index than `features_df`; real raw kline data uses RangeIndex while OOS features use timestamp index; positional slicing fixes both without changing row selection.
TESTS_RUN: `freeze_baseline_new.py --max-features 50 --timeout-seconds 1200` PASS, wrote `baseline_new_btc_1h_a384e6d2.json` sha256 `24d69dc6e74f0478902c96cf3d4f3b5f83c632ce0e8833c7c4a7ab5b9a9fa349`; 3 leakage invariants PASS; `pytest tests/momentum/Analysis/test_ic_1a_cut1_*.py tests/momentum/test_factories.py -q` PASS 30/30; `grep -rE "from api\\." momentum/ | wc -l` = 0; `./scripts/check_decoupling_phase4.sh` PASS 135/135.
FAILURES_SEEN: First G-NEW rerun exposed grouped IC raw-data alignment failure: `timestamp column timestamp contains NaN values`; fixed by slicing raw kline rows positionally for the OOS subset.
SCOPE_CHANGES: Stayed within dispatch scope; only `momentum/Analysis/ic_filter_orchestrator.py` changed by this FIX2 pass, plus the requested handoff file and generated G-NEW baseline artifact.
NUMERIC_OR_SCHEMA_IMPACT: G-NEW baseline regenerated for flag-on OOS path; no schema change; flag default unchanged OFF.

STATUS: DONE