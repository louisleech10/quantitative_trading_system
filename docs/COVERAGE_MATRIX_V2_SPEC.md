# 跨 Symbol Coverage Matrix — V2 路徑修復 + Group 聚合/Worst-offender 下鑽 — SPEC

> 來源 PLAN/診斷：本 session 實測重現（coverage_analyzer 用舊 V7 路徑→0 features）　|　日期：2026-06-04　|　對應 TODO：直接從本 SPEC 派工（中型，跳獨立 TODO）

## §RISK 風險分級（gate 讀此決定要求強度）
- **大小**：**中**（單一 module + 既有 caller；接 CLAUDE.md 任務分派規則 → 派 Composer 2.5）。
- **命中高風險原則**：**皆否**。(a) 不改資料品質 gate/精度/淨化，coverage 公式（1−nan_ratio）不變；(b) 只**呼叫** `FeatureReader` 既有 V2 read-only API，不改它，`compute_symbol_coverage_matrix` 唯一消費者是 `feature_browser_service`（已 grep 確認，不在 IC Gatekeeper 選因子路徑）；(c) 單 phase 可單 commit revert；(d) 此 Coverage Matrix 是 UI 診斷，不餵 ML 訓練/回測。
- 不命中 (a)/(d) → §G Golden 移 §N 標 N/A，改以 §V 確定性 fixture 值測兜底。

## §A 假設與待使用者確認（事故：拿推論代替問人）
- **已驗證事實**（grep / python 實測，逐項附驗證方式）：
  - V2 儲存佈局 = `data_cache/features/{symbol}/{tf}/{config_hash}/feature_manifest.json`（`find` 實測 + python 載入成功）。舊 `_load_symbol_features` 找 `{symbol}/{hash}/manifest.json` 與 `{symbol}_{tf}_factory.h5` → 皆不存在 → 回 None（實測重現）。
  - BTCUSDT/1h：**115,544 features、20,352 rows、260 groups**（`load_manifest_v2` 實測）。
  - `manifest.artifacts[*].groups[g]` 含 `nan_ratio`、`row_count`、`column_count`、`columns`、`path/file`（python 印出 keys 實測）→ **group×symbol coverage 可純讀 manifest 算出，零 parquet 載入**。
  - `FeatureReader` V2 API：`feature_run_dir(symbol,tf,hash)` / `load_manifest_v2(symbol,tf,hash,artifact_kind="raw")` / `load_columns_v2(symbol,tf,hash,cols,artifact_kind="raw")` / `_get_v2_artifact(manifest,kind)`。參考實作：`momentum/Analysis/ic_engine.py:140-177`。
- **待使用者確認**：無（下列已確認）。
- **已確認結果**（使用者 2026-06-04）：
  - 設計＝**Group 聚合主視圖 + Worst-offender 下鑽**（非「前 N 個」）。
  - 量化/統計呈現原則：大規模缺值不列舉，按 group 聚合 + 按跨-symbol 離散度排序找異常（Claude 提出，使用者採納）。

## §C 約束（引用 + 只列本任務相關）
- 解耦 7 條：`momentum/` 不 import `api/`；service 經 factory 取得引擎（`create_coverage_analyzer`/`create_feature_reader`）不直接 new；DTO 不跨域。
- 不可違反原則：不弱化 NaN/inf 處理；coverage = 1 − nan_ratio 語義不變；no fake data（全部從真實 manifest/parquet 算）。
- 本任務特別注意：
  - **記憶體鐵律**：主視圖**禁止**載入全部 115k 欄；group 聚合只讀 manifest `nan_ratio`；per-feature 僅在下鑽選定 group 時 `load_columns_v2` 載該 group（數十欄）。
  - `compute_symbol_coverage_matrix` 既有簽名與既有測試（`tests/api/test_feature_browser_service.py::test_get_coverage_matrix` 斷言 exact 值 0.0/0.5、worst_symbol）為**回溯相容基準**，新增能力不得破壞舊 legacy HDF5 fixture 路徑（測試用 `{symbol}_{tf}_factory.h5`）。

## §G Golden / Baseline（高風險(a/d)必填；否則移 §N 標 N/A+理由）
- N/A，理由見 §N。改以 §V 確定性 fixture 值測（exact nan_ratio）兜底。

## §P Phase 與依賴（事故：宣稱無依賴卻有 forward dependency）

### Phase 1 — 後端：V2 路徑修復 + group 聚合 + 下鑽（依賴：無）
**Task 1.1 — `_load_symbol_features` 支援 V2 路徑**
- 目標：能讀到 V2 佈局的特徵。檔案：`momentum/Analysis/coverage_analyzer.py::CoverageAnalyzer._load_symbol_features`。既有 caller：`compute_symbol_coverage_matrix`（同檔）。
- 改法：在現有「V7 dir 掃描」與「legacy HDF5」**之前**，新增 V2 分支：掃 `base/{symbol}/{timeframe}/*/feature_manifest.json`，取最新（`sorted(reverse=True)`）config_hash；`reader.load_manifest_v2(symbol, timeframe, hash, artifact_kind="raw")` 拿到 manifest 後，若呼叫端需 DataFrame 則 `load_columns_v2`。**保留** V7 與 legacy HDF5 fallback（向後相容既有測試 fixture）。
- 驗證（可證偽）：新增 `pytest tests/api/test_feature_browser_service.py::test_v2_layout_loads`——以真實風格 V2 fixture（symbol/tf/hash/feature_manifest.json + parquet）斷言載到非空、欄數正確。`_load_symbol_features("BTCUSDT","1h","data_cache/features")` 在有資料機器上回非 None（手動驗，非 CI）。
- 邊界（≥2）：① V2 與 legacy HDF5 同時存在 → 優先 V2；② `{symbol}/{tf}` 目錄不存在 → 回 None 不拋例外（沿用現行 warning）。
- 不可做：不得刪除/改寫既有 V7、legacy HDF5 分支；不得改 `FeatureReader`。

**Task 1.2 — group×symbol coverage 聚合（純 manifest，零資料載入）**
- 目標：產出 group × symbol 平均 coverage 主視圖資料。檔案：`coverage_analyzer.py` 新增 `compute_group_coverage_matrix(symbols, timeframe, feature_base_path)`。既有 caller：新建，供 service 呼叫。
- 改法：逐 symbol 解析最新 manifest → 對每個 group 取 `group_info["nan_ratio"]`（coverage=1−nan_ratio）。回傳 `{groups: [...], symbols: [...], matrix: {group:{symbol:coverage}}, divergence: {group: max−min across symbols}, summary}`。**不開任何 parquet**。按 divergence 由大到小排序 groups。
- 驗證：新增 `test_group_coverage_from_manifest`——V2 fixture 兩 symbol，某 group 在 A/B nan_ratio 不同 → 斷言該 group divergence>0 且排序在前；coverage 值 = 1−manifest nan_ratio（exact）。
- 邊界（≥2）：① 某 symbol 缺某 group → 該格回 None，不計入該 group divergence；② symbol manifest 不存在 → 該 symbol 整欄 None + summary 標記。
- 不可做：不得為了聚合而載入 parquet（違記憶體鐵律）。

**Task 1.3 — 下鑽：選定 group 的 per-feature coverage**
- 目標：對單一 group 載入其欄位算 per-feature coverage。檔案：`coverage_analyzer.py` 新增 `compute_group_feature_coverage(symbols, timeframe, group_name, feature_base_path, top_n=100)`。
- 改法：對每 symbol，從 manifest 找該 group 的 columns → `load_columns_v2(symbol, tf, hash, columns, artifact_kind="raw")` 只載這數十欄 → 逐欄 `1 − notna/total`。回傳 features × symbols 矩陣 + 每 feature 跨-symbol divergence，按 divergence 排序取 top_n。
- 驗證：`pytest tests/api/test_feature_browser_service.py::test_group_drilldown_per_feature`——V2 fixture，斷言 `set(result.features) <= set(manifest group columns)`、每格 coverage `== 1 - nan/total`（exact）、`features` 順序依 divergence 遞減（`assert div[i] >= div[i+1]`）。
- 邊界（≥2）：① group 不存在 → ValueError("group not found")；② top_n > 實際欄數 → 回全部不報錯。
- 不可做：不得載入非選定 group 的欄位。

**Task 1.4 — service / model / route 串接**
- 目標：暴露 group 聚合與下鑽。檔案：`api/services/feature_browser_service.py`（新增 `get_group_coverage`、`get_group_feature_coverage` 薄包裝，沿用 ≥2 symbol 驗證）；`api/models/feature_browser_models.py`（新增 `GroupCoverageResponse`、`GroupFeatureCoverageRequest/Response`，保留既有 `CoverageMatrixRequest/Response`）；`api/routes/feature_browser.py`（新增 `POST /feature-browser/group-coverage`、`POST /feature-browser/group-feature-coverage`，沿用 `asyncio.wait_for` timeout 模式 + `_http_error`）。`api/models/__init__.py` 同步註冊新 model。
- 驗證：新增 `tests/api/test_feature_browser_routes.py::test_group_coverage_endpoint_200` / `test_group_feature_coverage_endpoint_200`（V2 fixture，200 + 結構斷言）。既有 coverage-matrix route 測試**不得移除/放寬**。
- 邊界（≥2）：① <2 symbol → 400；② 逾時 → 504（沿用現行）。
- 不可做：不得改既有 `coverage-matrix` 端點契約（仍保留供回溯相容；前端改用新端點後可於後續迭代再評估下架，不在本 SPEC）。

### Phase 2 — 前端：主視圖（group 熱圖）+ 下鑽（依賴：Phase 1）
**Task 2.1 — `SymbolCoverageMatrix.tsx` 改兩層呈現**
- 目標：group×symbol 熱圖為主視圖，點 group 列下鑽 per-feature 表。檔案：`frontend/src/components/feature-factory/SymbolCoverageMatrix.tsx`。既有 caller：`app/feature-factory/page.tsx`（props 不變：`entries`）。
- 改法：移除「最多 features 100 + 計算」單一矩陣流程，改為：(1) 選 timeframe + symbols → 呼叫 `POST /group-coverage` 顯示 group×symbol 熱圖（按 divergence 排序，最異常在上）；(2) 點某 group → 呼叫 `POST /group-feature-coverage`（帶 `group_name`、`top_n`）顯示該 group per-feature 子表。沿用既有色階 `getCellClass`、summary badge。loading/error/empty 三態齊全。
- 驗證：`npm run build` 通過；手動 — 3 symbol×1h 下主視圖顯示 260 groups 量級熱圖，點一列出現 per-feature 子表。
- 邊界（≥2）：① <2 symbol → 既有提示；② 某 group 某 symbol 無值 → 灰格 `--`。
- 不可做：不得在前端一次請求全部 115k；不得保留會載全量的舊 empty-featureNames 路徑。

**Task 2.2 — types.ts 對齊**
- 目標：型別對齊新回應。檔案：`frontend/src/lib/types.ts` 新增 `GroupCoverageResponsePayload`、`GroupFeatureCoverageResponsePayload`；`CoverageMatrixResponsePayload` 若不再被引用則移除（grep 確認）。
- 驗證：`npx tsc --noEmit` exit code `== 0`（0 錯誤）；`grep -rn "CoverageMatrixResponsePayload" frontend/src` 若無引用則該型別已移除（回傳 0 筆）。
- 邊界：N/A（純型別）。
- 不可做：不得保留無引用孤兒型別。

## §V 驗證策略與邊界測試目錄
- 測試層級：單元（coverage_analyzer 三個新方法 + V2 路徑）/ 整合（兩個新 route）/ 確定性值測（exact nan_ratio fixture，代 Golden）/ 邊界。皆 `pytest tests/...` 獨立跑，不需 run_api.py。
- **防假綠**：`tests/api/test_feature_browser_service.py::test_get_coverage_matrix`（exact 0.0/0.5/worst_symbol）與 `test_feature_browser_routes.py` 既有 coverage 斷言**一字不改不放寬**；新斷言對應新 group/drilldown 行為。執行端交回後 Claude **diff 既有斷言**確認未被動手腳。
- **邊界目錄**（打勾對應 Task）：✓ 空/缺 manifest（1.1/1.2 邊界②）✓ 全 NaN group（coverage=0）✓ 某 symbol 缺 group（1.2 邊界①）✓ group 不存在（1.3 邊界①）✓ <2 symbol（1.4/2.1）。OOM 降載：主視圖零載入即為防 OOM 設計。
- 驗收 fixture 要求：以 `feature_manifest.json` + 對應 parquet 真實風格建構（symbol/tf/hash 三層），**不可** mock 掉 `FeatureReader`（要驗真實讀取路徑）。

## §R 回退
- Phase 1/2 各自獨立 commit，可單獨 revert。新端點為**新增**、既有 `coverage-matrix` 端點與測試保留 → 任何階段回退不影響舊行為。前端 `SymbolCoverageMatrix` 改動集中單檔，revert 即還原。

## §N N/A 登記（被省略的必填段，逐一標理由）
- **§G Golden：N/A** — 本任務不碰 ML 訓練/回測正確性，coverage 公式（1−nan_ratio）與資料品質 gate 皆不變，僅修「讀哪個路徑」+ 新增「聚合/下鑽呈現」。數值正確性以 §V 的 exact-value 確定性 fixture 測試保證（等價於針對性 golden），不需凍結全量 baseline。
