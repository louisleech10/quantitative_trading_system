# handoff — dq nan_ratio + stats_warmup 還原 (2026-06-03)

## 完成
- **N1** `_assemble_data_quality_report` / `_empty_data_quality_report` 寫入 `nan_ratio_mean` / `nan_ratio_max`（自 `nan_ratios` 聚合）。
- **N2** dq 快取 schema `dq_v4` → `dq_v5`；舊 dq_v4 disk cache 視 miss 重算。
- **N3** 既有 `test_feature_factory_batch_quality.py` dq 快取路徑測試通過。
- **W1** 新增 `_get_stats_warmup_progress`；`browse_summary` / `_browse_summary_from_fast` 回傳 `stats_warmup{computed,total,pct,complete}`。
- **catalog** `_load_cgsa_catalog_disk_cache`：`fast` 缺 `nan_ratios` 時不再 KeyError。

## 測試
- `pytest tests/api/ -q -k "quality or batch or browse or dq"` → 124 passed
- `./scripts/check_decoupling_phase4.sh` → PASS
- `npm run build` → PASS

## 小 scope 擴大
- `tests/api/test_feature_export.py`：`fake_browse_distribution` 加 `**kwargs`（route 已傳 `compute_adf`，舊 mock 致 `-k browse` 假紅；與 dq/warmup 無關）。

## 踩坑
- unit test `_build_service_for_unit` 須補 `_lock` / `_coalesce_browse`，否則 `browse_summary` 呼叫 `_get_stats_warmup_progress` 時 AttributeError。
