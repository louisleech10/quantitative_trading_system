# FF Fail-Open — Frozen Test Assertion Changes (Batch2+3)

| file:line | 原斷言 | 新行為 | 理由 |
|-----------|--------|--------|------|
| `tests/feature_engineering/test_failopen_contract.py:test_required_fail_returns_result` | `_execute_layer1_6` 失敗路徑回 `pd.DataFrame` | 回 `LayerExecutionResult`，`status==layer_failed`，`.data` 空表保留 index | Task 2.1/2.2：wrapper 回 typed result，caller 用 `.data` |
| `tests/feature_engineering/test_failopen_contract.py:test_layer2_exception_fail_open` | `layer2.empty` 且 `len(index)==0`；`layer_results` 無 Layer 2 | `LayerExecutionResult.status==layer_failed`；index 長度與輸入一致；`layer_results["Layer 2"]` 存在 | `_safe_execute` 不再吞 L2 例外；fail-closed 記錄 |
| `tests/feature_engineering/test_failopen_contract.py:test_layer3_exception_fail_open` | 同上（L3） | 同上（L3） | 同上 |
| `tests/test_feature_factory_batch2e.py:test_t2b8_l65_fracdiff_per_group_feasible` | registry groups 為 `LayerSource.L3` | groups 改為 `LayerSource.L1`（預設 fracdiff_layers=L1,L2） | 對齊 optimized profile；L3 走 fast path 不呼叫 fracdiff |
| `tests/test_golden_output_generation.py:test_l2_timing_log_emitted` | `_DummyDerivedOperatorEngine` 無 `OPERATOR_CATEGORIES`；polars 預設開 | dummy 加 `OPERATOR_CATEGORIES`；`FFACT_USE_POLARS=0` | L2 走 pandas + `compute_all` dummy 路徑 |
| `tests/feature_engineering/test_failopen_layers.py::test_zero_copy_spill_preserves_memmap_sharing` | `assert_frame_equal(check_exact=False)` + spill 自比 `shares_memory` | `assert result.data is original_df`；spill 對 captured `memmap_base` `shares_memory` | Task 2.2 zero-copy；`_ensure_float32` 全 float32 early-return 保 identity |
| `tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline` | `PYTHONHASHSEED!=0` → `pytest.skip` | subprocess `PYTHONHASHSEED=0` + `_FAILOPEN_GATE_A_WORKER` 重入 | CI 預設必跑 Gate-A |
| `tests/feature_engineering/test_failopen_contract.py:test_required_fail_returns_result` | L1 hash 段 `PYTHONHASHSEED!=0` → `pytest.skip` | 抽出 `test_l1_baseline_hash_matches_frozen`；subprocess `PYTHONHASHSEED=0` + `_FAILOPEN_L1_ORACLE_WORKER` 重入 | Batch3：CI 預設必跑 L1 oracle |
| `tests/feature_engineering/test_failopen_manifest.py` | *(新增)* | manifest completeness + merge 偏序 + legacy/unknown 遷移偵測 | Batch3 Task 3.1/3.2 |
| `tests/feature_engineering/test_ic_first_pipeline.py:test_l7_schema_version_metadata` | `raw_v1` / `processed_v1` parquet+manifest 斷言 | `raw_v2` / `processed_v2` | Batch3 round2 schema_version 遷移 |
| `tests/feature_engineering/test_l7_raw_streaming.py` | `raw_v1` manifest/parquet/metadata 斷言 | `raw_v2` | Batch3 round2 schema_version 遷移 |
| `tests/feature_engineering/test_failopen_manifest.py:test_persist_false_generate_features_metadata` | CGSA 路徑（`FFACT_USE_CGSA=1` 預設） | 顯式 `FFACT_USE_CGSA=0` 測非 CGSA `_layer7_validate_and_persist` completeness | Batch3 round3 |
| `tests/feature_engineering/test_failopen_manifest.py` | 並行 RMW 無 barrier/負向 | `test_manifest_concurrent_*` 加 Barrier+鎖內 sleep；`test_manifest_concurrent_merge_fails_without_lock` 證偽 | Batch3 round3 |
