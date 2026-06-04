# Coverage Matrix V2 — 執行端收尾（2026-06-04）

## 完成項
- Phase 1.1–1.4：V2 `_load_symbol_features`、`compute_group_coverage_matrix`、`compute_group_feature_coverage`、service/model/route
- Phase 2.1–2.2：`SymbolCoverageMatrix` 兩層 UI + `types.ts` 新 payload 型別

## 驗證
- `pytest tests/api/test_feature_browser_service.py tests/api/test_feature_browser_routes.py tests/feature_library/test_phase4.py` → 25 passed
- `npm run build` → 成功
- `grep -r "from api\." momentum/` → 0

## 決策
- 主視圖 matrix 值為 **coverage**（1−nan_ratio），與 legacy coverage-matrix 的 nan_ratio 矩陣不同；前端用 `getCellClassFromCoverage`
- `summary.worst_group` = divergence 最大之 group（worst-offender 下鑽提示）
- 既有 `POST /coverage-matrix` 與 `test_get_coverage_matrix` 斷言未改
