# B6 backend (B6a+B6b) — Composer 2.5

task=B6-backend-composer | 2026-06-22 | scope=B6a+B6b only (B6c API/UI 後續)

## 改檔
- `momentum/FeatureEngineering/warmup_window.py`（新）：`OutputWindow`、`estimate_max_warmup_bars`、`resolve_output_window`、trim/insufficient helpers
- `momentum/FeatureEngineering/feature_factory.py`：generate 入口 resolve window、`_layer0` ingest_start、`_trim_for_public_output`、metadata（warmup_insufficient/label_tail_nan_bars/cumulative_anchor）、L7 normal+CGSA+IC-first trim
- `momentum/FeatureEngineering/timeframe/multi_tf_generator.py`：per-TF ingest_start（次 TF 用 primary ingest 時間跨度）、parallel worker
- `momentum/FeatureEngineering/feature_storage.py`：`row_slice` on `write_raw_from_registry_stream` + `persist_registry_to_parquet`
- `tests/feature_engineering/test_b6_warmup_trim.py`（新）

## max_warmup 來源（minimal preset, 12h primary）
- L1 TA-Lib+CDL+advanced atomic 窗、L2 momentum/WQ、L3 rolling、L4 lag seq、L5 beta=60（cross-sectional 開時）、L6 meta ATR55、L6.5 winsor/rank/zscore/calibration/fracdiff max_lag/ADF sample + native-tf scale、validator winsor fallback=252
- 實測 `estimate_max_warmup_bars(minimal,12h)` → **500**（calibration_bars 主導）

## trim 路徑
- normal L7 `_layer7_validate_and_persist`
- CGSA L7_raw `_layer7_raw_from_cgsa_pipeline`（stream `row_slice`）
- CGSA L7 validate `_layer7_validate_and_persist_cgsa`
- IC-first `write_raw`（pre_ic frame + label trim）
- multi-TF `_layer0` + worker

## 驗證（真實 kline_cache.h5, hermetic）
- `pytest tests/ -k warmup`：**9 passed**
- hermetic：`tmp_path/features` + `FFACT_CGSA_WORK_DIR`；跑前後 `data_cache/features` 全量 diff 空
- flag 關：`build_l65_golden_baseline.py --check` PASS
- 品質增益（BTCUSDT 12h 120d 窗, POSITION_INDEPENDENT, K=min(50,max_warmup/4)）：valid_frac on≥off+0.05（測試斷言通過）
- T2：persist 輸出首列≥start、row_count 對齊 output window
- 因果：max(ingest_index)<start（ingest 測試）
- warmup 不足：近 dataset 開頭可出 `warmup_insufficient` + `label_tail_nan_bars=21` + `cumulative_anchor`

## flag / byte
- `FFACT_WARMUP_TRIM` 預設 `0`；**不納 config_hash**
- flag 關行為不變（golden PASS）；flag 開不承諾全史 byte parity（Option 1）

## 踩坑
- `_current_raw_data or raw_data` 對 DataFrame 會觸發 ambiguous truth → 改 `is not None`
- CGSA 短路徑 `features_df` 無欄；整合測試需 `FFACT_USE_CGSA=0` 或讀 raw artifact
- 短窗 + dead_drop 會把特徵剔光 → 測試關 `l7_dead_feature_drop`
