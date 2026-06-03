# Phase 1 — NaN 5-number + real_problem + Overview fix

**Agent**: Cursor | **Date**: 2026-06-03

## 變更摘要
- `feature_factory_service.py`: `_compute_nan_ratio_quantiles`、`_resolve_true_nan_quality_metrics`；dq report + browse_summary 同源寫入 `nan_ratio_quantiles`；schema `dq_v5`→`dq_v6`；CGSA fast browse 改走 dq isna 掃描（不再用 parquet null_count 當 NaN）。
- `feature_factory_batch_adapters.py`: 回傳 `nan_quantiles`、`real_problem_count`。
- 前端 `BatchQualityOverview`（真問題 + Min/Q1/Med/Q3/Max）、`OverviewDashboard`（NaN Med）、`types.ts`。

## 驗證
- `pytest tests/api/ -q -k "quality or batch or browse or dq or summary"` — pass
- `./scripts/check_decoupling_phase4.sh` — pass
- `npm run build` — pass

## 決策
- Overview 與批次品質共用 dq 真實 isna 路徑；快取缺 quantiles 時 bump dq_v6 強制重算。
