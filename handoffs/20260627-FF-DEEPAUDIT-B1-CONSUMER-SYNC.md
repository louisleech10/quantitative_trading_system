# BUG-1 Consumer Sync Checklist (Task 1.3)
# Generated: 2026-06-27 | rg 'statistics_BETA|statistics_CORREL|_BETA_|_CORREL_'

| Path | Match / 處置 | Status |
|------|----------------|--------|
| `momentum/FeatureEngineering/atomic/talib_wrapper.py` | BETA/CORREL → `hl`; 新增 `Beta_CloseVolume`/`Correl_CloseVolume` aliases | DONE |
| `momentum/FeatureEngineering/atomic/statistics_indicators.py` | metadata `variant=non_standard_close_volume` for aliases | DONE |
| `momentum/FeatureEngineering/utils/adf_safe_skip.py:55` | `_CORREL_` 保留(hl CORREL); 新增 `Correl-CloseVolume`; BETA/Beta-CloseVolume 排除 ADF | DONE |
| `tests/feature_engineering/test_adf_safe_skip.py` | 欄名 migration hl CORREL / Beta-CloseVolume not-skip | DONE |
| `api/services/feature_factory_service.py:3804` | UI 顯示名 + 非標準別名 | DONE |
| `tests/_golden/failopen/baseline.json` | L1 BETA/CORREL parquet — §G v1 受影響欄; 差異表 `beta_correl_v0_v1_diff.json` | DOCUMENTED |
| `tests/_golden/batch2d/provenance.json` | L2–L7 `close-volume_*_statistics_BETA_*` 衍生 — Affected Column Closure | DOCUMENTED |
| `momentum/Analysis/` IC | 無硬編; smoke + 差異表 `ic_semantic_drift_smoke` | DONE (test_bug1_beta_correl) |
| `momentum/FeatureEngineering/warmup_window.py` | `_BETA_ROLLING_WINDOW` 常數名, 非 statistics BETA 欄 | NO CHANGE |
| `handoffs/*`, `docs/*` | 診斷/規格文件 | NO CHANGE |

## Affected Column Closure (§G)
1. **L1 直接**: `hl_*_statistics_BETA_*`, `hl_*_statistics_CORREL_*`, `close-volume_*_statistics_Beta-CloseVolume_*`, `close-volume_*_statistics_Correl-CloseVolume_*`
2. **L2–L7**: provenance 可追溯至 (1) 的鍵 — 見 `batch2d/provenance.json`（v1 golden 重凍待三方簽核）
3. **未受影響欄**: 其餘 value hash exact（B1 後 Claude 跑 §G v1）

## 差異表路徑
- `tests/_golden/ff_deepaudit/beta_correl_v0_v1_diff.json`
- `tests/_golden/ff_deepaudit/handcoded_variant_diff.json` (BUG-2)
