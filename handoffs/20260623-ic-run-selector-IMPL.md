# IC Run Selector 實作收尾 — 2026-06-23

## Batch STATUS
| Batch | STATUS | 主要改檔 |
|---|---|---|
| A-0 | DONE | tests/fixtures/gen_ic_run_selector_baseline.py, ic_run_selector_baseline.json |
| 1 (A-1/2/3) | DONE | ic_models.py, ic_analysis_service.py, feature_library.py, feature_reader.py |
| 2 (B-1/2/3) | DONE | ic_models CrossRunRef, load_multi config_hashes, service cross path |
| 3 (C-1/2/2b) | DONE | list_features_v2, route query params, useICAnalysis/page fetch |
| 4 (D-1..6) | DONE | types.ts, icAnalysisStore, ICConfigPanel, page.tsx, vitest |
| 5 (E-1/2) | DONE | ICConfigPanel batch picker, useICAnalysis cross_sectional_runs |
| 6 (F-1/2) | DONE | feature_factory_service training_timeframes, leaf label |
| 7 (G-1..5) | DONE | test_ic_run_selector.py, test_ic_list_features.py, vitest G-4/G-5 |

## Gate 測試
- pytest `-k ic_run_selector`: **11 passed**
- vitest ic-analysis+useICAnalysis: **5 passed**
- npm run build: **PASS**
- grep `from api.` momentum/: **0**

## §G Golden（真實 BTCUSDT 12h）
- backward_compat (find_latest=90f586…): sha256≠1c4b…, row_count=1696 ✓
- disambig 1c4b825… vs 90f586…: 不同 sha256 (73 vs 45419 cols), identity==請求 ✓
- ML load_multi: config_hashes=None, kwargs byte 穩定 ✓

## 關鍵決策
- kline 用 `data_cache/feature_klines`（非 legacy kline_cache.h5）
- orchestrator 仍吃 HDF5：service materialize + catalog metadata
- baseline 大 run 僅凍結 load 指標；小 run 跑端到端 IC

## 踩坑
- legacy list_features 路徑不含 tf → 加 list_features_v2
- grouped_ic/regime 預存 bug：測試 config 關閉 regime/decay

---

## Codex Review 修補 — 2026-06-23（Composer 2.5）

| # | STATUS | 修補 |
|---|---|---|
| BLOCKING #1 fail-closed | DONE | `find_latest_materialized` + `is_materialized`（registry）；explicit `config_hash` 禁 legacy fallback；`ensure_fresh`/IC no-hash 用 materialized |
| BLOCKING #2 hermetic golden | DONE | `ic_run_selector_mini_registry.json` + `FFACT_FEATURE_REGISTRY_PATH` fixture；`test_live_registry_skips_orphan_latest` canary |
| BLOCKING #3 橫截面混 tf | DONE | `ICConfigPanel` 依 `(batch_id, timeframe)` 分組，≥2 symbols 才 offer |
| BLOCKING #4 G-3 真 caller | DONE | `CrossSymbolTrainingService.run_cross_symbol_validation` spy `load_multi`；baseline gen 同步 |
| BLOCKING #5 gate marker | DONE | markers 已掛；gate 11 passed |
| NON-BLOCKING page.tsx | DONE | fetch 失敗先 `setAvailableFeatures([])` |

### 驗證
- gate `-m "ic_run_selector or backward_compat or disambig or analyze_real_run or list_features"`: **11 passed**
- `pytest tests/api tests/momentum -q`: **1215 passed**, 4 failed（batch_alias/worker_logging/e2e/perf，非本任務引入）
- vitest IC: **5 passed** | `npm run build`: **PASS**
- grep `from api.` momentum/: **0**
