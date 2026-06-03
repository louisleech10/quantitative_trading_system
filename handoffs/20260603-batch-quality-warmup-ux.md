# handoff — batch quality + stats warmup UX (2026-06-03)

## 完成
- **Q1/Q2/Q3** `feature_factory_batch_adapters._to_batch_quality`：NaN 均/峰改取 dq `nan_ratio_mean/max`（np.isnan 掃描）；`alert_count`= `counts.real_problem`；新增 `warmup_only_count`；grade 不再因暖機 NaN 灌 Watch。
- dq report `_assemble_data_quality_report` 暴露 `nan_ratio_mean/max`。
- **W1** `browse_summary` 回傳 `stats_warmup{computed,total,pct,complete}`（`_get_stats_warmup_progress`，沿用 cache 計數）。
- **W2** `FeatureTable` + `StatsWarmupBanner`：暖機未完成顯示「暖機 X%，排序暫定」；完成後隱藏；5s 輪詢 summary。

## 測試
- `pytest tests/api/ -q -k "quality or batch or summary"` → 65 passed
- `./scripts/check_decoupling_phase4.sh` → PASS
- `npm run test -- FeatureTable.test.tsx` → 3 passed
- `npm run build` → （見本次執行）

## 踩坑
- `statsWarmup?.complete !== false` 在 undefined 時仍為 true → 已改為明確判斷。
- batch quality 測試 manifest 須用 `parquet_path`（CGSA list 格式）。
- mid-hole 須 NaN ratio ≥ 5% 才計入 `real_problem`（dq 門檻）。
