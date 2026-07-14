# DECOUPLE-P3 B1 validation receipt

## Pre-change evidence

### T1c pre-change golden

Command: fixed FastAPI `TestClient` request with mocked psutil, memory tier, tier config, empty environment, and missing cache path.

```text
T1C_PRE_STATUS 200
T1C_PRE_JSON {"applied_settings":{"cgsa_memory_buffer":{"env_raw":null,"env_var":"FFACT_CGSA_MEMORY_BUFFER","source":"auto","value":0},"cgsa_shard_bytes":{"env_raw":null,"env_var":"FFACT_CGSA_SHARD_BYTES","source":"auto","value":201326592},"l2_category_workers":{"env_raw":null,"env_var":"FFACT_L2_CATEGORY_WORKERS","source":"auto","value":4},"l3_persist_mode":{"env_raw":null,"env_var":"FFACT_L3_PERSIST_MODE","source":"auto","value":"streaming"},"l3_streaming_buffer_cols":{"env_raw":null,"env_var":"FFACT_L3_STREAMING_BUFFER_COLS","source":"auto","value":5000},"l65_split_threshold":{"env_raw":null,"env_var":"FFACT_L65_SPLIT_THRESHOLD","source":"auto","value":8000},"l65_workers":{"env_raw":null,"env_var":"FFACT_L65_WORKERS","source":"auto","value":6},"l7_workers":{"env_raw":null,"env_var":"FFACT_L7_WORKERS","source":"auto","value":6},"layer3_chunk_size":{"env_raw":null,"env_var":"FFACT_LAYER3_CHUNK_SIZE","source":"auto","value":512},"multi_tf_max_workers":{"env_raw":null,"env_var":"FFACT_MULTI_TF_MAX_WORKERS","source":"auto","value":2}},"cpu":{"logical_cores":8,"physical_cores":4,"usage_pct":23.0},"disk":{"free_gb":0.0,"path":"/private/tmp/decouple-p3-t1c-fixed-missing-cache","total_gb":0.0,"used_pct":0.0},"memory":{"available_gb":6.0,"total_gb":16.0,"used_pct":62.5},"memory_tier":"16gb","recommended_settings":{"FFACT_CGSA_MEMORY_BUFFER":0,"FFACT_L65_WORKERS":6,"FFACT_L7_COMPACTOR_ENABLED":1,"FFACT_L7_WORKERS":6,"FFACT_LAYER3_CHUNK_SIZE":512,"FFACT_MULTI_TF_MAX_WORKERS":2},"tier_table":{"16gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":201326592,"cgsa_stats_q_sample":3000,"cgsa_stats_sync_cap":500,"cgsa_stats_warmup_workers":4,"chunk_bars":100000,"concurrent_symbols":1,"l2_category_workers":4,"l3_persist_mode":"streaming","l3_streaming_buffer_cols":5000,"l65_split_threshold":8000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":3,"layer3_chunk_size":512,"multi_tf_max_workers":2},"24gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":268435456,"cgsa_stats_q_sample":5000,"cgsa_stats_sync_cap":800,"cgsa_stats_warmup_workers":6,"chunk_bars":100000,"concurrent_symbols":2,"l2_category_workers":6,"l3_persist_mode":"hybrid","l3_streaming_buffer_cols":10000,"l65_split_threshold":12000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":2,"layer3_chunk_size":512,"multi_tf_max_workers":3},"32gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":402653184,"cgsa_stats_q_sample":8000,"cgsa_stats_sync_cap":1000,"cgsa_stats_warmup_workers":8,"chunk_bars":100000,"concurrent_symbols":3,"l2_category_workers":7,"l3_persist_mode":"in_memory","l3_streaming_buffer_cols":20000,"l65_split_threshold":16000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":1,"layer3_chunk_size":1024,"multi_tf_max_workers":4},"8gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":100663296,"cgsa_stats_q_sample":1500,"cgsa_stats_sync_cap":200,"cgsa_stats_warmup_workers":2,"chunk_bars":100000,"concurrent_symbols":1,"l2_category_workers":1,"l3_persist_mode":"streaming","l3_streaming_buffer_cols":2000,"l65_split_threshold":2000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":4,"layer3_chunk_size":256,"multi_tf_max_workers":1}},"tier_thresholds_gb":[{"min_total_gb":28,"tier":"32gb"},{"min_total_gb":20,"tier":"24gb"},{"min_total_gb":12,"tier":"16gb"},{"min_total_gb":0,"tier":"8gb"}]}
```

### T3c pre-change baseline

Command: `venv/bin/python -m pytest tests/api -k "ic" -q`

```text
107 passed, 269 deselected, 3391 warnings, 23 errors in 102.56s
All 23 errors: RuntimeError: redirect already active; pytest must remain serial
```

Known issue preserved: `applied_settings.value` remains tier-derived even when `source` reports an environment override; DECOUPLE-P3 explicitly forbids changing it.

## Post-change task gates

### T1a

Command: `venv/bin/python -m pytest tests/test_hardware_api.py -q`

```text
3 passed in 0.34s
```

### T1b

Command: `grep -c "momentum" api/routes/config.py`

```text
0
```

### T1c post-change equality

Command: repeat the fixed pre-change request, load `T1C_PRE_JSON` above, and assert Python dict equality.

```text
T1C_POST_STATUS 200
T1C_POST_JSON {"applied_settings":{"cgsa_memory_buffer":{"env_raw":null,"env_var":"FFACT_CGSA_MEMORY_BUFFER","source":"auto","value":0},"cgsa_shard_bytes":{"env_raw":null,"env_var":"FFACT_CGSA_SHARD_BYTES","source":"auto","value":201326592},"l2_category_workers":{"env_raw":null,"env_var":"FFACT_L2_CATEGORY_WORKERS","source":"auto","value":4},"l3_persist_mode":{"env_raw":null,"env_var":"FFACT_L3_PERSIST_MODE","source":"auto","value":"streaming"},"l3_streaming_buffer_cols":{"env_raw":null,"env_var":"FFACT_L3_STREAMING_BUFFER_COLS","source":"auto","value":5000},"l65_split_threshold":{"env_raw":null,"env_var":"FFACT_L65_SPLIT_THRESHOLD","source":"auto","value":8000},"l65_workers":{"env_raw":null,"env_var":"FFACT_L65_WORKERS","source":"auto","value":6},"l7_workers":{"env_raw":null,"env_var":"FFACT_L7_WORKERS","source":"auto","value":6},"layer3_chunk_size":{"env_raw":null,"env_var":"FFACT_LAYER3_CHUNK_SIZE","source":"auto","value":512},"multi_tf_max_workers":{"env_raw":null,"env_var":"FFACT_MULTI_TF_MAX_WORKERS","source":"auto","value":2}},"cpu":{"logical_cores":8,"physical_cores":4,"usage_pct":23.0},"disk":{"free_gb":0.0,"path":"/private/tmp/decouple-p3-t1c-fixed-missing-cache","total_gb":0.0,"used_pct":0.0},"memory":{"available_gb":6.0,"total_gb":16.0,"used_pct":62.5},"memory_tier":"16gb","recommended_settings":{"FFACT_CGSA_MEMORY_BUFFER":0,"FFACT_L65_WORKERS":6,"FFACT_L7_COMPACTOR_ENABLED":1,"FFACT_L7_WORKERS":6,"FFACT_LAYER3_CHUNK_SIZE":512,"FFACT_MULTI_TF_MAX_WORKERS":2},"tier_table":{"16gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":201326592,"cgsa_stats_q_sample":3000,"cgsa_stats_sync_cap":500,"cgsa_stats_warmup_workers":4,"chunk_bars":100000,"concurrent_symbols":1,"l2_category_workers":4,"l3_persist_mode":"streaming","l3_streaming_buffer_cols":5000,"l65_split_threshold":8000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":3,"layer3_chunk_size":512,"multi_tf_max_workers":2},"24gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":268435456,"cgsa_stats_q_sample":5000,"cgsa_stats_sync_cap":800,"cgsa_stats_warmup_workers":6,"chunk_bars":100000,"concurrent_symbols":2,"l2_category_workers":6,"l3_persist_mode":"hybrid","l3_streaming_buffer_cols":10000,"l65_split_threshold":12000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":2,"layer3_chunk_size":512,"multi_tf_max_workers":3},"32gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":402653184,"cgsa_stats_q_sample":8000,"cgsa_stats_sync_cap":1000,"cgsa_stats_warmup_workers":8,"chunk_bars":100000,"concurrent_symbols":3,"l2_category_workers":7,"l3_persist_mode":"in_memory","l3_streaming_buffer_cols":20000,"l65_split_threshold":16000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":1,"layer3_chunk_size":1024,"multi_tf_max_workers":4},"8gb":{"cgsa_memory_buffer":0,"cgsa_shard_bytes":100663296,"cgsa_stats_q_sample":1500,"cgsa_stats_sync_cap":200,"cgsa_stats_warmup_workers":2,"chunk_bars":100000,"concurrent_symbols":1,"l2_category_workers":1,"l3_persist_mode":"streaming","l3_streaming_buffer_cols":2000,"l65_split_threshold":2000,"l65_workers":6,"l7_workers":6,"l7_zstd_level":4,"layer3_chunk_size":256,"multi_tf_max_workers":1}},"tier_thresholds_gb":[{"min_total_gb":28,"tier":"32gb"},{"min_total_gb":20,"tier":"24gb"},{"min_total_gb":12,"tier":"16gb"},{"min_total_gb":0,"tier":"8gb"}]}
T1C_DICT_EQUAL True
```

### T1d

Command: parse every `Import`/`ImportFrom` in `api/services/hardware_info_service.py`; reject `api.services*`, `api.core.config*`, and `api.routes*`, including package-level imports and aliases.

```text
T1D_VIOLATIONS []
T1D_AST_ALLOW_SET PASS
```

### T2a

Command: parse `git show HEAD:momentum/FeatureEngineering/utils/hardware_utils.py` and the worktree file, remove each module docstring, and compare `ast.dump(..., include_attributes=False)`.

```text
T2A_AST_DUMP IDENTICAL
```

### T2b

Command: `bash scripts/check_decoupling.sh`

```text
Rule 1 PASS
Rule 2 PASS
Rule 3 PASS
R2=0 R3=0
Rule 4 PASS
Rule 5 PASS
Rule 6 PASS
Rule 7 PASS
ALL RULES PASS — Ready to freeze
```

### T3a

Command: `grep -rn "_feature_library._registry" api --include="*.py"`

```text
<no matches>
```

### T3b

Command: `venv/bin/python -m pytest tests/momentum/test_feature_library_registry_facade.py tests/api/test_ic_transform_feature_loading.py -q`

```text
10 passed in 0.24s
```

### T3c post-change baseline comparison

Command: `venv/bin/python -m pytest tests/api -k "ic" -q`

```text
107 passed, 269 deselected, 3391 warnings, 23 errors in 100.20s
All 23 errors: RuntimeError: redirect already active; pytest must remain serial
Comparison: same pass/deselect/warning/error counts and same error cause as pre-change.
```

## Phase gate and hygiene

Command: `venv/bin/python -m pytest tests/api tests/momentum -q`

```text
52 failed, 1298 passed, 18 skipped, 4900 warnings, 171 errors in 415.36s
Directly related hardware, IC selector, FeatureLibrary config-hash/latest, row-index/value-conservation, and new façade tests passed.
Failures/errors cluster in pre-existing redirect fixture state, progress RSS, worker logging, and model fixture paths outside DECOUPLE-P3 scope.
```

```text
INVENTORY_UNCHANGED_BY_GATE
INVENTORY_COMPARE_EXIT=0
```

Final focused recheck after docstring normalization:

```text
venv/bin/python -m pytest tests/test_hardware_api.py tests/momentum/test_feature_library_registry_facade.py tests/api/test_ic_transform_feature_loading.py -q
13 passed in 0.37s
FINAL_T1D_VIOLATIONS []
git diff --check -> exit 0
bash scripts/agent_postflight.sh -> POSTFLIGHT data_cache intact (11744 files / 30115604KB); HEALTH OK
```

## 主委驗收(Claude 實跑 2026-07-14) — 判定: APPROVED
- `bash scripts/check_decoupling.sh` → ALL RULES PASS exit 0
- `pytest tests/test_hardware_api.py tests/momentum/test_feature_library_registry_facade.py tests/api/test_ic_transform_feature_loading.py tests/decoupling -q` → 44 passed
- `git diff tests/test_hardware_api.py | grep -cE '^[-+].*assert'` → 0(斷言零變動,僅 patch 目標)
