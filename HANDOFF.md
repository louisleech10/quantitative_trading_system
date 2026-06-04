# Handoff
**Agent**: Claude | **Time**: 2026-06-04 | **Branch**: main

## 正在做
- **Coverage Matrix bug 修復 + 重設計（已派 Composer 2.5 完成並驗收，未 commit）**。
- 起因：feature-browser 併入 Feature Factory 後，Coverage Matrix 按「計算」回空。根因（實測）：`CoverageAnalyzer._load_symbol_features` 用舊 V7 路徑 `features/{symbol}/{hash}/`，但實際是 V2 `features/{symbol}/{tf}/{hash}/feature_manifest.json` → 永遠回 None。

## 本次決策
- 中型任務 → 依規則**派 Composer 2.5**（高風險判斷後確認不命中 a-d：coverage 是 UI 診斷、只呼叫 FeatureReader 既有 API）。走完整 SPEC + fail-closed gate（`docs/COVERAGE_MATRIX_V2_SPEC.md`）。
- 設計改為**量化業界做法**：Group 聚合主視圖（260 groups，純讀 manifest `nan_ratio`，零 parquet 載入）+ Worst-offender 下鑽（選 group 才載該 group 數十欄）。避免載 11 萬欄。
- 新增端點 `/group-coverage`、`/group-feature-coverage`；保留舊 `/coverage-matrix` 與其 exact 測試。

## 驗證（Claude 親驗）
- `pytest`（3 檔）**25 passed**；既有 exact 斷言（0.0/0.5/worst_symbol）**原封未放寬**（防假綠）。
- **真實 data_cache**：group-coverage 260×3 symbols **0.13s**、avg 94.8%、worst_group=BBANDS-Upper；下鑽 10 features 0.29s。根因確實修好。
- postflight **data_cache 完整未縮減**（1641 檔）；`npm run build`/`tsc` 執行端回報 OK。

## 待辦
- 使用者實機 refresh Feature Factory 頁，按「計算 Group Coverage」確認熱圖 + 點 group 下鑽正常。
- 是否 commit 由使用者決定（本次含先前 feature-browser 下架 + 本次 coverage 修復，建議分兩 commit）。
- 執行端交接：`handoffs/20260604-coverage-matrix-v2.md`。

## 阻塞
- 無。
