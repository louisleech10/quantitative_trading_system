# FF_FAILOPEN_UNIFIED Batch4 Phase4

## Task 4.1
- Modified `momentum/FeatureEngineering/feature_factory.py` and `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`.
- L1-L6 and all four multi-timeframe paths fail closed on `layer_failed`/timeframe failure by default; explicit partial flags retain failed metadata and continue.
- `engine_partial` remains non-fatal. Runtime gate flags are excluded from `config_hash`.
- Added NaN/Inf ratio quality degradation with Task 0.1 NaN artifact defaults; leading/trailing warmup NaNs are excluded from abnormal-NaN counts.
- L6.5 frame-path failure retains unprocessed features and records effective preprocessing config with `preprocessing_applied=false`.

## Task 4.2
- Modified `momentum/FeatureEngineering/core/column_group_registry.py`, multi-TF orchestration, and `api/services/feature_factory_service.py`.
- Timeframe rollback selects registry groups by stored timeframe across all layers, stages files through atomic rename, restores state on staging/manifest failure, and raises deletion failures.
- CGSA callers rollback failed timeframes; degraded generation/restart results map to `completed_degraded`.

## Task 4.3
- Modified `momentum/FeatureEngineering/feature_validator.py`.
- Validator winsorization is skipped when L6.5 winsorization is active; otherwise it uses the existing causal rolling winsor kernel and rescans NaN/Inf afterward.
- Full-sample quantile winsorization was removed from this path.

## Tests and evidence
- Added `tests/feature_engineering/test_failopen_producer.py` and `tests/feature_engineering/test_failopen_winsor.py`.
- Updated the conflicting legacy multi-TF assertion in `tests/test_multi_tf_generator.py`; registered the change in `docs/FF_FAILOPEN_FROZEN_TESTS.md`.
- Phase4 failopen gate: 54 passed in 201.74s on the final worktree.
- Batch2/multi-TF/IC-first/L7 regression gate: 74 passed in 46.78s.
- Targeted L7 compatibility rerun: 1 passed in 0.05s.
- `git diff --check`, target `py_compile`, and momentum-to-api import scan passed.

## Remaining risk
- L6.5 degradation is directly covered for the frame path; CGSA raw-sink failures remain governed by their existing transactional writer behavior.
- No tracked changes exist under `data_cache/`, `tests/golden/l65/`, root `HANDOFF.md`, or `templates/`.

## Round2（測試缺口補齊，僅測試檔）

**範圍**：只改 `tests/feature_engineering/test_failopen_producer.py`；未動 production / data_cache / golden / HANDOFF / templates。

### B1 — 四 generator 真路徑 fail-closed 整合
- 新增 `test_four_generator_paths_fail_closed_integration`（8 cases：`allow_partial` × 4 paths）。
- 路徑：`legacy`（`FFACT_USE_CGSA=0`）、`cgsa_serial`、`cgsa_parallel_primary`（monkeypatch `_run_tf_l1_l6_results`）、`cgsa_parallel_worker`（mock `_tf_worker_entry`）。
- 注入：缺 `1h` kline（legacy/serial）或 pipeline/worker 失敗（parallel）；經真實 `generate_multi_tf` 編排。
- 預設 → `pytest.raises(RuntimeError)`；`allow_partial_timeframes=True` → `skipped_timeframes` 含 `1h` 且繼續完成。
- 輔助：`_CgsaStubFactory`、`_ThreadPoolAsProcessPool`（patch `concurrent.futures.ProcessPoolExecutor`）、`_multi_tf_config()`（`training=["12h","1h"]`）。

### B2 — API `completed_degraded`
- `test_api_restore_partial_manifest_maps_completed_degraded`：manifest `quality_status=partial` → `_restore_persisted_tasks()` → `completed_degraded`。
- `test_api_generation_partial_maps_completed_degraded`：mock `_generate_features_with_phase_d` 回傳 partial metadata → `_run_task` 完成狀態 `completed_degraded`。

### N2 — NaN 門檻 partial
- `test_nan_threshold_marks_partial`：`nan_ratio=0.10` > `max_nan_ratio=0.01` → `quality_status=='partial'`。

### 驗收
- `pytest tests/feature_engineering/test_failopen_producer.py tests/feature_engineering/test_failopen_winsor.py tests/feature_engineering/test_failopen_manifest.py tests/feature_engineering/test_failopen_layers.py tests/feature_engineering/test_failopen_golden.py tests/feature_engineering/test_failopen_contract.py tests/test_multi_tf_generator.py -q` → **77 passed** in 194.83s。
- 未發現 production 實作缺陷；無 scope 擴大。
