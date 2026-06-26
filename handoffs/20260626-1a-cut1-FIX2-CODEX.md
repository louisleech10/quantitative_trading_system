# 1a cut1 FIX2 Codex Handoff

## Scope
- Fixed `momentum/Analysis/ic_filter_orchestrator.py` only.
- Root cause 1: `_slice_by_mask` used feature timestamp labels to slice a differently indexed label series.
- Root cause 2: stage4 grouped/decay raw kline data used RangeIndex raw data against timestamp-indexed OOS features, producing NaN timestamps.

## Changes
- `_slice_by_mask` now selects feature and label rows by boolean-mask positions via `iloc`.
- Added `_slice_raw_data_by_mask` for stage4 raw kline alignment; when raw rows match feature rows, raw data is sliced positionally and reindexed to OOS feature index.
- Stage4 decay/grouped IC now consume the same OOS raw-data row universe as OOS features/labels.
- `ic_train_test_split` default remains `False`.

## Validation
- G-NEW real full run succeeded and wrote `tests/golden/ic_phase1_1a_cut1/baseline_new_btc_1h_a384e6d2.json`, sha256 `24d69dc6e74f0478902c96cf3d4f3b5f83c632ce0e8833c7c4a7ab5b9a9fa349`.
- 3 leakage invariants passed.
- Full 1a tests + G-OLD + factories passed: 30 passed.
- Decoupling passed: `grep from api. momentum` count 0; `check_decoupling_phase4.sh` passed with 135 Strategy tests.

## Failures Seen
- First G-NEW attempt passed original label-index crash but failed grouped IC with `timestamp column timestamp contains NaN values`.
- Cause confirmed as raw kline RangeIndex reindexing against feature timestamp index in the OOS subset.
- Second attempt succeeded after raw kline positional OOS slicing.

## Remaining
- None for FIX2.
