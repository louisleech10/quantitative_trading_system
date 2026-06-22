# 20260622 dstar empirical — Codex

## Scope
- Read-only empirical quant; product code unchanged.
- Temp script: `scripts/tmp/dstar_option_a_empirical.py`; outputs: `/tmp/dstar_option_a_empirical/{summary.json,feature_detail*.csv}`.
- Data: real `data_cache/feature_klines/kline_cache.h5`, BTCUSDT 1h.

## Setup
- Full range rows: 20,352.
- Date-windowed rows: 6,552 (`2024-09-01 00:00Z` → `2025-05-31 23:00Z`).
- Features: 20 L1/L2 candidates; actual common recorded d*: 10; L3 excluded by `FFACT_FRACDIFF_APPLY_TO_LAYERS=L1,L2`.
- Product path used: `FeaturePreprocessor.transform()` with winsorization + fracdiff, rank/zscore/gaussian off, d* cache off.

## Results — all overlap
- d* abs delta: mean 0.3693, median 0.3867, p95 0.5830, max 0.6859.
- Feature value Pearson: mean 0.5146, median 0.5462, max 0.9997; allclose 0/10.
- Feature value Spearman: mean 0.5652, median 0.6412, max 0.9996.
- IC abs delta: mean 0.00864, median 0.00694, p95 0.02170, max 0.02352.
- Abs-IC rank Spearman: 0.6848; rank delta mean 1.8 / max 4 among 10.
- Selection overlap: top3 Jaccard 0.50; top5 0.667; abs(IC)>=0.01 Jaccard 0.20; abs(IC)>=0.02 selected none in both.

## Results — skip first 1000 overlap bars
- Rows: 5,552.
- Value Pearson median 0.5289; Spearman median 0.6133; allclose 1/10.
- IC abs delta: mean 0.01418, median 0.01206, p95 0.03262, max 0.03635.
- Abs-IC rank Spearman: 0.8061.
- Selection overlap: top3 Jaccard 0.50; top5 1.00; abs(IC)>=0.01 Jaccard 0.20.

## Largest movers
- Largest d*: `L2_decay_linear_close_20` full 0.1266 vs window 0.8125, Δ 0.6859.
- Largest all-overlap IC Δ: `L1_EMA_20` -0.00991 vs +0.01360, Δ 0.02352.
- Largest trimmed IC Δ: `L1_EMA_20` -0.01692 vs +0.01942, Δ 0.03635.

## Conclusion
- Option A was not empirically confirmed as clearly second-order on this BTCUSDT 1h sample.
- d* Δ is large and feature values are not highly correlated for most tested fracdiff-eligible trend/price features.
- IC impact is smaller than value impact, but ranking/selection is not stable enough to claim “二階確認”.
- Recommended next decision: either accept Option A as a causal/run-self-consistent tradeoff with documented IC sensitivity, or rerun broader symbols/features before treating it as safe.

## Hermetic proof
- `data_cache` full SHA256 diff before/after: empty.
- Before list hash = after list hash = `c093e7ce50a63e7073b0a071f2c022eec03c5197973ddf635517f9a2b9d852c9` over 544 files.
