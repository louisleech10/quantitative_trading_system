# T-C CGSA L3 累積磁碟預檢 — Composer 實作 — 2026-06-19

## 改動檔案
- `momentum/FeatureEngineering/core/column_group_registry.py` — B1: `_estimate_chunk_shard_planned_bytes`, `_resolve_cgsa_disk_reserve_bytes`, `_precheck_cgsa_cumulative_disk`
- `momentum/FeatureEngineering/feature_factory.py` — B2: `_cgsa_disk_precheck_enabled`, `_maybe_precheck_cgsa_cumulative_disk`; `_persist_layer_output_groups` 開頭呼叫（涵蓋 serial/parallel/single-TF 三路徑）
- `tests/feature_engineering/test_cgsa_disk_precheck.py` — 單元 + 整合測試

## needed 公式（adv#1 增量制）
```
needed = planned_new_bytes + max_inflight_tmp_bytes + reserve_floor
```
- **不加** `registry_occupied`（`disk_usage().free` 已扣除既佔檔案）
- `planned_new_bytes`：模擬 5000-col chunk + `_compute_shard_slices`，Σ float32 bytes（實際 DataFrame.shape）
- `max_inflight_tmp_bytes` = 最大 planned shard × 2（.tmp 雙份）
- `reserve_floor` = `FFACT_CGSA_DISK_RESERVE_GIB`（預設 2.0 GiB）

## 三路徑接入
共用 `FeatureFactory._maybe_precheck_cgsa_cumulative_disk` → 在 `_persist_layer_output_groups` 開頭呼叫：
1. serial multi-TF（`multi_tf_generator.py` → `factory._persist_layer_output_groups`）
2. parallel primary（同上）
3. single-TF（`_persist_single_tf_l3_l6_to_cgsa` → `_persist_layer_output_groups`）

env `FFACT_CGSA_DISK_PRECHECK`（預設 `"1"`；`"0"` 停用）

## pytest 數字
- `pytest tests/feature_engineering/ -k cgsa_disk_precheck`：**10 passed**
- `python scripts/build_l65_golden_baseline.py --check`：**PASS**

## byte check
磁碟充足時 guard 為 pass-through；golden baseline abs≤1e-6 不變。

## 未做
- 未改 `multi_tf_generator.py` 本體（三路徑經 `_persist_layer_output_groups` 單點接入）
- 未 push
- 未動 `data_cache/`
