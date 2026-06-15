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
| `tests/test_multi_tf_generator.py::test_lower_tf_missing_degrades_but_primary_succeeds` | lower TF 缺資料預設 skip 並成功 | 改名 `test_lower_tf_missing_fails_closed_unless_partial_enabled`；預設 `pytest.raises`，僅 `allow_partial_timeframes=True` 保留 skip | Batch4 Task 4.1：TF 預設 fail-closed |
| `tests/feature_engineering/test_ic_first_pipeline.py::_ic_fixture` / `test_memory_budget_after_raw_persist` | `write_raw` 無 `layer_results` → manifest `run_status=unknown` | fixture 走真實 persist：`row_index` + `_healthy_layer_results`（L1–L6 ok）→ `run_status=complete`；`test_ic_group_read_failure_partial_mode` 仍用 `allow_partial_ic` 測 group 讀取 partial（非 unknown） | Batch5 consumer gate：strict IC 拒 unknown；測試補 completeness 證據，不放寬 production gate |
| `tests/test_primary_self_align_skip.py` | `result.metadata["actual_timeframes"]` | 改名 `present_timeframes`（對齊 manifest 語彙；3 producer 收斂單一函式） | Batch1 follow-up T5：`actual_timeframes`→`present_timeframes` |
| `tests/api/test_feature_factory_batch_resume.py` | browse stable_id `browse_{s}_{tf}`（無 hash，同 s/tf 多 run 只留首個） | `browse_{s}_{tf}_{full_config_hash}`（同 s/tf 多 hash 並存；reconciliation 依 full hash） | Batch2 Run 生命週期 N7/pass2：browse ID 全鏈 full-hash 遷移 |
