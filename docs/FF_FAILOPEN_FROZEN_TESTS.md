# FF Fail-Open — Frozen Test Assertion Changes (Batch2)

| file:line | 原斷言 | 新行為 | 理由 |
|-----------|--------|--------|------|
| `tests/feature_engineering/test_failopen_contract.py:test_required_fail_returns_result` | `_execute_layer1_6` 失敗路徑回 `pd.DataFrame` | 回 `LayerExecutionResult`，`status==layer_failed`，`.data` 空表保留 index | Task 2.1/2.2：wrapper 回 typed result，caller 用 `.data` |
| `tests/feature_engineering/test_failopen_contract.py:test_layer2_exception_fail_open` | `layer2.empty` 且 `len(index)==0`；`layer_results` 無 Layer 2 | `LayerExecutionResult.status==layer_failed`；index 長度與輸入一致；`layer_results["Layer 2"]` 存在 | `_safe_execute` 不再吞 L2 例外；fail-closed 記錄 |
| `tests/feature_engineering/test_failopen_contract.py:test_layer3_exception_fail_open` | 同上（L3） | 同上（L3） | 同上 |
| `tests/test_feature_factory_batch2e.py:test_t2b8_l65_fracdiff_per_group_feasible` | registry groups 為 `LayerSource.L3` | groups 改為 `LayerSource.L1`（預設 fracdiff_layers=L1,L2） | 對齊 optimized profile；L3 走 fast path 不呼叫 fracdiff |
| `tests/test_golden_output_generation.py:test_l2_timing_log_emitted` | `_DummyDerivedOperatorEngine` 無 `OPERATOR_CATEGORIES`；polars 預設開 | dummy 加 `OPERATOR_CATEGORIES`；`FFACT_USE_POLARS=0` | L2 走 pandas + `compute_all` dummy 路徑 |
| `tests/feature_engineering/test_failopen_layers.py::test_zero_copy_spill_preserves_memmap_sharing` | `assert_frame_equal(check_exact=False)` + spill 自比 `shares_memory` | `assert result.data is original_df`；spill 對 captured `memmap_base` `shares_memory` | Task 2.2 zero-copy；`_ensure_float32` 全 float32 early-return 保 identity |
| `tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline` | `PYTHONHASHSEED!=0` → `pytest.skip` | subprocess `PYTHONHASHSEED=0` + `_FAILOPEN_GATE_A_WORKER` 重入 | CI 預設必跑 Gate-A |
