# fracdiff-maxlag-d1d2-codex-20260703

## 五欄
ASSUMPTIONS_VERIFIED: 已讀 R3 reconcile 雙戳記裁決；確認 `_assert_d_star_gate` mismatch 訊息含 `d_star`;確認 collect-only 可收集 D1/D2 兩測試。
TESTS_RUN: `pytest --collect-only tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_fracdiff_tail_perturbation_invariant tests/feature_engineering/test_ff_fullchain_truncation_mr.py::test_mutation_fracdiff_calibration_perturb_fails` PASS, collected 2; `pytest -m "not slow" tests/feature_engineering/test_fracdiff_maxlag_derivation.py tests/feature_engineering/test_dstar_cache_key_mutation.py -q` PASS, 15 passed; `git diff --check` PASS。
FAILURES_SEEN: none。
SCOPE_CHANGES: none；只改指定測試檔與 helper，新增本 handoff。
NUMERIC_OR_SCHEMA_IMPACT: none；測試/fixture path 控制變更，未改 production 數值、schema、輸出大小。

## 檔案清單
- `tests/feature_engineering/test_ff_fullchain_truncation_mr.py`
- `tests/feature_engineering/ff_truncation_mr_helpers.py`
- `handoffs/20260703-FRACDIFF-MAXLAG-D1D2-codex.md`
