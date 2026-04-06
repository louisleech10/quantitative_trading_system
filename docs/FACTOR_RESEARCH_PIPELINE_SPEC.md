# 因子研究流水線 UI 擴充規格書

> **版本**: V0.6  
> **建立日期**: 2026-04-01  
> **更新日期**: 2026-04-03  
> **文件性質**: 功能規格書（Specification）— 後續由此生成 PLAN/TODO 給 AI Agent 實作  
> **狀態**: Draft → Under Review  
> **V0.5 變更摘要**: 
> - §5 header：V0.3 修訂原則 → V0.4
> - §5.1：新增前端 50 因子上限驗收條件（對齊 §10 風險緩解）
> - §5.2：Turnover Y 軸說明改為比例值 0~1（rank_change_rate 可 > 1）
> - §6 Phase B B3：引用從過時的 §4.2 B8 修正為 B6
> - §7：新增 Phase 轉換準則（A→B、B→C 明確條件）
> - §9 情境 A step 10：Regime Radar 從「均有正 IC」改為「顯示各狀態差異」（實戰導向）
> **關聯文件**:  
> - [PRODUCT_VISION.md](./PRODUCT_VISION.md) — 產品願景與版本演進  
> - [IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md](./IC%20篩選%20+%20XGBoost,LightBGM%20預測%20+%20Optuna%20策略優化.md) — ML 主線架構  
> - [ARCHITECTURE.md](./ARCHITECTURE.md) — 系統解耦架構原則  

---

## 目錄

1. [背景與動機](#1-背景與動機)
2. [目的與範疇](#2-目的與範疇)
3. [最終目標](#3-最終目標)
4. [系統現況盤點](#4-系統現況盤點)
   - [4.4 架構觀察：後端超前前端的功能差距](#44-架構觀察後端超前前端的功能差距)
5. [功能規格（逐項）](#5-功能規格逐項)
6. [分階段實作路線圖](#6-分階段實作路線圖)
7. [擴充時機判斷準則](#7-擴充時機判斷準則)
8. [非功能性需求](#8-非功能性需求)
9. [成功驗收標準](#9-成功驗收標準)
10. [風險與假設](#10-風險與假設)
11. [名詞解釋](#11-名詞解釋)

---

## 1. 背景與動機

### 1.1 問題陳述

本系統目前已完成特徵工廠（Feature Factory）、IC 深度分析（IC Analysis）、XGBoost/LightGBM 訓練的後端核心。**後端已擁有 24 個計算引擎**，但從「生成因子」到「送入 ML 訓練」之間，**前端未完整串接已有的後端能力**，加上缺少跨頁面工作流銜接，導致：

1. **後端能力浪費**：14 個深度分析模組已可用，但部分結果（IC 半衰期數值、Turnover 時序、截面 IC）在前端看不到
2. **研究效率低落**：用戶面對 20,000~60,000 個因子，缺少端到端流程將其縮減至 20~50 個
3. **跨 Symbol 截面未暴露**：後端 `analyze_cross_sectional()` 完整，但前端 mode 選項未開放
4. **研究結果無法持久化**：篩選標記在 session 結束後消失，無 Watchlist 機制
5. **關鍵圖表缺失**：多空累積淨值曲線（Equity Curve）無前端元件，這是判斷因子實戰可行性的核心工具

### 1.2 業界最佳實踐對比

| 業界標準流程 | 本系統現況 | 落差 |
|---|---|---|
| IC 排名 → 初篩至 top 50~100 | Feature Browser 有 IC Dashboard | ✅ 已完成 |
| Rolling IC 穩定性驗證 | IC Analysis 有 Rolling IC Chart | ✅ 已完成 |
| ICIR 排序（穩定性 > 絕對值） | ICSummaryTable 已有 ICIR 排序 | ✅ 已完成 |
| Statistical validation（p-value, FDR） | 後端 StatisticalValidator 完整 | ✅ 已完成 |
| 冗餘過濾（相關性/VIF/聚類） | 後端 RedundancyFilter 三種方法 | ✅ 已完成 |
| Factor Turnover 評估交易成本 | 後端 TurnoverAnalyzer + NetICChart 泡泡圖 | 🟡 缺獨立時序圖 |
| IC 半衰期數值輔助決策換手頻率 | 後端已計算 `ic_half_life` | 🟡 前端未標注數值 |
| 多空累積淨值曲線（Equity Curve） | QuantileReturnChart 只有靜態平均值 | ❌ 缺累積時序曲線 |
| 截面 IC（Cross-Sectional IC） | 後端 `analyze_cross_sectional()` 完整 | 🟡 前端 mode 選項未暴露 |
| Regime 條件分析（牛/熊/震盪） | 後端 RegimeAnalyzer + RegimeRadarChart | ✅ 已完成 |
| OOS 驗證（樣本外回測） | 後端 RollingOOSValidator + OOSDistributionChart | ✅ 已完成 |
| ML 特徵重要性（XGB/LGB/SHAP） | 後端 3 個 Analyzer + 前端 ModelAttribution | ✅ 已完成 |
| 因子 Neutralization 去多重暴露 | 有 ZScore，但不是 Neutralization | ❌ 概念不同（Phase D） |
| Watchlist / 因子標記系統 | 無 | ❌ 完全缺失 |

---

## 2. 目的與範疇

### 2.1 目的

打造一條**可重複執行、與 ML 訓練直接銜接**的因子研究工作流，讓用戶能夠：

- 從 10,000 個原始因子，**有系統地縮減到 20~50 個高品質因子**
- 在送入 LightGBM / XGBoost 之前，**每個候選因子都有統計支撐（IC、Turnover、Half-Life）**
- 支援**多 Symbol 截面分析**，避免單一幣種的 overfitting
- 研究結果**可匯出、可標記、可復現**

### 2.2 範疇

**本規格書涵蓋**（僅列待做項目，已完成功能見 §4.1）：

- IC Analysis 頁面前端補完：Half-Life 數值標注、截面 IC mode 暴露、Turnover 獨立時序圖
- 新增 Equity Curve 前端元件 + 後端 endpoint 封裝
- 跨頁面 Factor Watchlist 機制（localStorage → 未來後端持久化）
- 多 Symbol Coverage Matrix（需新增前後端）

**本規格書不涵蓋**：

- LightGBM / XGBoost 訓練本體（已有獨立規格：`Phase3_LightGBM_XGBoost_Spec.md`）
- Optuna 策略優化（已有獨立規格：`Optuna重構_SPEC.md`）
- 資料下載、K 線管理
- 部署、Docker、CI/CD

---

## 3. 最終目標

### 3.1 操作流程目標（V1.0 完成後）

用戶能夠完成以下端到端研究流程，**全程在 UI 操作，不需要寫程式**：

```
步驟 1  Feature Factory — 因子生成
        設定指標參數 → 生成 1,000~10,000 個因子
        ↓ 完成後自動跳轉推薦訊息

步驟 2  Feature Browser — 初篩（快速篩選，5~10 分鐘）
        2-1  Quality Scorecard：淘汰 NaN > 30% 的因子         → 剩 ~60%
        2-2  IC Dashboard top_k 排名：保留 |IC| > 0.02 的     → 剩 ~200
        2-3  命名段落篩選：聚焦特定 Indicator / Source         → 剩 ~100
        2-4  Correlation Matrix：合併相關性 > 0.9 的同族       → 剩 ~50
        2-5  加入 Watchlist 標記為「候選」                       （Phase B）

步驟 3  IC Analysis — 基礎 IC 篩選（8 階段流水線，自動）
        3-1  Rolling IC：確認因子預測力時序穩定
        3-2  IC Decay + Half-Life：決定最佳持有 bars
        3-3  Quantile Return：初步確認多空分離
        3-4  統計驗證（p-value / FDR）：排除隨機 IC
        3-5  冗餘過濾（相關性/VIF/聚類）：去重

步驟 3.5  Deep Analysis — 實戰深度驗證（14+ 模組可選，重點開啟 4~6 個）
        3.5-1  Factor Return + Equity Curve：看因子能否真正賺錢
        3.5-2  Factor Turnover + Net IC：扣費後是否還有 alpha
        3.5-3  Regime Analysis：牛市/熊市/震盪各自表現
        3.5-4  OOS Validation：樣本外 IC 是否崩塌
        3.5-5  截面 Rank IC：多 Symbol 有效性確認
        3.5-6  更新 Watchlist 標記為「已驗證」                   （Phase B）

步驟 4  ML 訓練
        從 Watchlist 匯出「已驗證」因子清單
        → 填入 LightGBM / XGBoost 訓練的特徵選擇
        → 執行訓練 + Optuna 優化
```

> **V0.4 說明**：步驟 3 與 3.5 都在同一個 `IC Analysis` 頁面操作，不涉及頁面切換。差異在於後端計算範圍：步驟 3 為自動 8 階段流水線（一鍵執行）；步驟 3.5 為人工在 `DeepAnalysisConfigPanel` 中勾選特定模組後再次執行。兩者可依序執行，也可合併為一次執行。

### 3.2 量化目標

**軟體可測量指標**（驗收可用）：
- 研究一輪完整流程（生成 → 篩選 → ML 訓練）所需 UI 操作時間：**< 30 分鐘**
- 可追溯性：Watchlist 匯出的 JSON，**可在 3 個月後重新載入並對應到相同因子名稱**

**業務成果指標**（供參考，非軟體驗收條件）：
- 送入 ML 的因子集中，ICIR > 0.5 的比例達 > 70%（取決於因子設計品質與市場條件）

---

## 4. 系統現況盤點

> **V0.3 全面重寫**：基於完整程式碼盤點（10 個後端核心類別 + 14 個深度分析模組 + 25 個 IC Analysis 前端元件 + 14 個 Feature Browser 元件 + 31 個 Feature Factory 元件），以三級分類重新審查。

> ℹ️ **如果您只關心「待做什麼」**，可直接跳到 [**§4.2 Category B**](#42-category-b---%E5%B7%B2%E6%9C%89%E4%BD%86%E5%89%8D%E5%BE%8C%E7%AB%AF%E4%B8%8D%E5%AE%8C%E6%95%B4%E6%88%96%E9%9C%80%E5%84%AA%E5%8C%96) 和 [**§4.3 Category C**](#43-category-c---%E7%BC%BA%E5%A4%B1%E9%9C%80%E6%96%B0%E5%A2%9E%E5%89%8D%E5%BE%8C%E7%AB%AF)。Category A 為完整盤點紀錄，供查閱用。

> 評分說明：✅ 前後端完整可直接使用 | 🟡 已有但不完整或需優化 | ❌ 缺失需新增

---

### 4.1 Category A — ✅ 前後端完整（可直接使用）

以下功能**已有後端計算 + 前端 UI + API 串接**，用戶可直接操作：

#### Feature Factory 頁面（31 元件）

| 功能 | 前端元件 | 後端 | 說明 |
|---|---|---|---|
| 設定面板（指標選擇/參數/數據源） | `ConfigPanel` + `IndicatorSelector` + `GlobalParamSliders` | `/api/v1/features/config` | 完整可配置 |
| Preset 系統（一鍵套用預設） | `PresetSelector` | `/api/v1/features/config/presets/{name}` | 預設管理 |
| 特徵數量預覽 | `FeatureCountSummary` + `FeatureDistribution` | `/api/v1/features/preview` | 即時預估 |
| 生成任務執行 + 進度 | `GenerationProgress` | `/api/v1/features/generate` | 即時 WebSocket |
| 批次多 Symbol 生成 | `BatchGenerationPanel` + `BatchProgressPanel` + `BatchQualityOverview` | `/api/v1/features/batch` | 多標的並行 |
| 特徵瀏覽（分頁/篩選/排序） | `FeatureTable` + `FeatureExplorer` + `FeatureListTree` | `/api/v1/features/browse/{task_id}` | cursor 分頁 |
| 命名段落篩選（Feature Table） | `FeatureNameSegmentFilter` | 後端 segment 解析 | ✅ 全量 ok |
| NaN 模式分析 | `NaNPatternChart` | 後端統計 | 缺失值視覺化 |
| 匯出（CSV/JSON/Markdown） | `ExportButtons` | `/api/v1/features/export/{task_id}/{format}` | 含 AI 可讀 JSON |
| Schema 自省 | `JsonOverrideEditor` | `/api/v1/features/schema` | 原始 JSON 編輯 |
| 設定匯入匯出 | `ConfigIOButtons` | 前端本地 | 保存/載入設定檔 |
| K 線資料下載管理 | `FeatureKlineDownloadPanel` | K 線下載 API | 資料準備 |

#### Feature Browser 頁面（14 元件）

| 功能 | 前端元件 | 後端 API | 說明 |
|---|---|---|---|
| 總覽統計（因子數/覆蓋率/NaN） | `DashboardOverview` | `/feature-browser/overview` | 全局快照 |
| 因子目錄（搜尋/排序/分頁） | `FeatureCatalogTable` | `/feature-browser/overview` | 完整因子列表 |
| IC / ICIR 排行榜 | `ICDashboard` | `/feature-browser/ic-dashboard` | 快速初篩核心工具 |
| Rolling IC 時序 | 內建於 ICDashboard sparkline | `/feature-browser/rolling-ic/{name}` | 穩定度確認 |
| 品質評分（ADF/覆蓋/飄移/冗餘） | `QualityScorecard` + `DataQualityPanel` | `/feature-browser/quality-scorecard` | A~F 評級 + 漏斗 |
| 相關矩陣 | `CorrelationHeatmap` | `/feature-browser/correlation-matrix` | 去重依據 |
| VIF 多重共線 | 內建於 DataQualityPanel | `/feature-browser/vif` | VIF > 10 標記 |
| 分佈直方圖 | `FeatureDistributionPanel` | `/feature-browser/distribution/{name}` | 單因子值域 |
| 漂移監控（PSI） | `DriftMonitor` | `/feature-browser/drift-monitor` | 時序穩定檢查 |
| 時序圖 | `FeatureTimeSeriesPanel` | `/features/time-series` | 曲線視覺化 |
| SHAP 重要性 | `ModelAttribution` | `/feature-browser/shap-summary` | ML 模型解釋 |
| 多方法重要性比較 | `ModelAttribution` | `/feature-browser/importance-comparison` | 排列/SHAP/係數 |

#### IC Analysis 頁面（25 元件 — 核心 8 階段流水線）

| 功能 | 前端元件 | 後端模組 | 說明 |
|---|---|---|---|
| **IC 計算 + ICIR 排名表** | `ICSummaryTable`（排序/篩選/匯出） | `ICEngine.compute_ic()` / `compute_icir()` | 核心排名表 |
| **Rolling IC 多窗口時序** | `RollingICChart` | `ICEngine.compute_rolling_ic()` | 21/63/126 窗口 |
| **IC Decay 衰減曲線** | `ICDecayChart` | `ICEngine.compute_ic_decay()` | 指數擬合 |
| **分位數收益分析** | `QuantileReturnChart` | `MonotonicityTester.compute_quantile_returns()` | Q1~Q5 柱狀圖 |
| **相關矩陣** | `CorrelationHeatmap` | `RedundancyFilter.compute_correlation_matrix()` | 熱力圖 |
| **篩選漏斗** | `FilterFunnelChart` | 8 階段各自的 pass/fail 統計 | Stage 0→7 視覺化 |
| **分組 IC（年/季/Regime）** | `GroupedICBarChart` + `RegimeRadarChart` | `ICEngine.compute_grouped_ic()` | 時段/市場狀態拆分 |
| **Net IC（扣成本後）** | `NetICChart` | `NetICAnalyzer` + `TurnoverAnalyzer` | 泡泡散佈圖 |
| **因子曝險雷達** | `FactorExposureRadar` | `FactorExposureAnalyzer` | 靜態截面 |
| **參數敏感度熱力圖** | `ParameterSensitivityHeatmap` | `ParameterSensitivityAnalyzer` | 參數微調影響 |
| **IC Trend 趨勢儀表板** | `TrendDashboard` | `TrendAnalyzer` | 趨勢與建議 |
| **OOS 樣本外分佈** | `OOSDistributionChart` | `RollingOOSValidator` | IS vs OOS 比較 |
| **多空比較** | `LongShortComparisonChart` | `LongShortAnalyzer` / `MonotonicityTester` | Long vs Short 收益 |
| **PCA 解釋方差** | `PCAExplainedChart` | 降維分析 | 方差比例 |
| **品質儀表板** | `FeatureQualityDashboard` | CoverageAnalyzer + StatisticalValidator | 多維品質指標 |
| **因子中心度** | `FactorCentralityChart` | `FactorCentralityAnalyzer` | 因子空間中心度 |
| **Tier 分層管理（L1/L2/L3）** | `FeatureTierPanel` | 後端 config tier 切換 | 基礎/中階/進階 |
| **設定面板** | `ICConfigPanel` + `DeepAnalysisConfigPanel` | config API | 閾值/方法/模組開關 |
| **篩選面板** | `FeatureFilterPanel` | IC/覆蓋/相關性篩選 | 互動篩選 |
| **匯出（PNG/CSV/JSON/MD/AI）** | `ExportButtons` | 多格式 | 含 AI 可讀摘要 |
| **Refilter 無需重算** | `FeatureFilterPanel` | `/api/v1/ic/refilter` | 調整閾值即時篩選 |
| **錯誤邊界** | `ChartErrorBoundary` + `PartialFailureBanner` | — | 局部失敗不影響全頁 |

---

### 4.2 Category B — 🟡 已有但前/後端不完整或需優化

以下功能**後端已實作但前端未完整暴露**，或**前端已有但資料連接不完整**：

| # | 功能 | 後端狀態 | 前端狀態 | 缺口 | 估計工作量 |
|---|---|---|---|---|---|
| B1 | **IC Half-Life 數值標注** | ✅ `ICEngine.compute_ic_decay()` 回傳 `half_life` + `decay_rate` + `fit_r2` | 🟡 `ICDecayChart` 只畫曲線，未標注數值 | 前端讀取 `half_life` 欄位，加垂直虛線 + 標籤 | 0.5 天（純前端） |
| B2 | **截面 IC 模式切換** | ✅ `analyze_cross_sectional()` 完整實作 + API `/api/v1/ic/analyze` 已支援 `mode: "cross_sectional"` | 🟡 `ICConfigPanel` mode 只有 `global`/`event`，缺 `cross_sectional` | 加入第三個 mode 選項 + Symbol 多選器 + 截面結果表格 | 1 天（前端） |
| B3 | **Factor Turnover 時序圖** | ✅ `TurnoverAnalyzer` 有 `compute_quantile_turnover()` / `compute_rank_change_rate()` / `compute_all()` | 🟡 `NetICChart` 泡泡圖 Z 軸讀 turnover，無獨立時序圖 | 新增 Turnover 時序折線圖元件 | 0.5 天（前端） |
| B4 | **命名段落篩選超過 5000 因子時的後端 segment API** | ✅ segment 解析 | ✅ limit 已從 200→5000 | 超過 5000 時需後端回傳 segment 選項，不傳全部因子名 | 0.5 天（規劃）——尚無迫切需求 |
| B5 | **Equity Curve（累積淨值）** | 🟡 `MonotonicityTester.compute_quantile_returns()` 已回傳 `cumulative_returns`（需確認是 dict 或時序 array）；`FactorReturnAnalyzer` + `LongShortAnalyzer` 可計算時序 | ❌ `FactorReturnChart` 只顯示靜態 summary，`QuantileReturnChart` 只畫柱狀平均值 | 新增前端元件讀取 `cumulative_returns` + 封裝新 endpoint（若現有格式不符） | 1.5 天（前+後） |
| B6 | **Deep Analysis 模組前端渲染完整性** | ✅ 14+ 模組全部可用 | 🟡 `DeepAnalysisConfigPanel` 有開關，但 4 個模組結果無前端圖表（SignalDensity/Calibration/LearningCurve/Pareto） | 🟢 低優先 — 這 4 個模組皆為研究輔助/ML 專用，非交易決策核心 | 各 0.5 天（按需） |

---

### 4.3 Category C — ❌ 缺失，需新增前後端

以下功能**完全不存在**，需要從零設計：

| # | 功能 | 重要程度 | 說明 | 估計工作量 |
|---|---|---|---|---|
| C1 | **Factor Watchlist（因子標記系統）** | 🔴 高 | 跨頁面因子標記（候選/已驗證/淘汰），是「篩選工作流」的最後一環。缺此功能，研究結果在 Session 結束後即消失，無法持久化。 | 2 天 |
| C2 | **Symbol Coverage Matrix（多標的熱力圖）** | 🟡 中 | 多 Symbol 場景下，確認每個因子在每個 Symbol 的 NaN 比例。只在使用 ≥ 3 個 Symbol 時才有意義。 | 1.5 天 |
| C3 | **Factor Neutralization** | 🟢 低 | 去除市值/波動率暴露。加密貨幣單標的交易場景下極少使用，是多標的投組場景才需要的學術功能。**建議推遲至 V2.0 以後**。 | 3+ 天 |

---

### 4.4 架構觀察

> **核心發現**：本系統最大瓶頸不是「缺少後端能力」，而是「前端未完整暴露已有功能」。

**量化證據**：
- 後端 IC Analysis 有 **10 個核心類 + 14 個深度分析模組 = 24 個計算引擎**
- 前端 IC Analysis 有 **25 個元件**，但只串接了約 70% 的後端能力
- IC Decay `half_life`、截面 IC `cross_sectional` mode、Turnover 時序 — 三者後端都已完成，只差前端 UI

**深度分析模組完整清單**（後端全部可用，通過 `DeepAnalysisConfigPanel` toggle 啟用）：

| 模組 | 類別 | 前端元件 | 對交易的實用價值 |
|---|---|---|---|
| `FactorReturnAnalyzer` | Long-Short 收益 | `FactorReturnChart` | 🔴 高：因子是否真能賺錢 |
| `LongShortAnalyzer` | 多空表現對比 | `LongShortComparisonChart` | 🔴 高：多空分離程度 |
| `TurnoverAnalyzer` | 換手率 | `NetICChart`（部分） | 🔴 高：交易成本影響 |
| `NetICAnalyzer` | 扣費後 IC | `NetICChart` | 🔴 高：實際可用 alpha |
| `RegimeAnalyzer` | 市場狀態分析 | `RegimeRadarChart` | 🔴 高：因子在不同行情下表現 |
| `RollingOOSValidator` | 樣本外驗證 | `OOSDistributionChart` | 🔴 高：過擬合檢測 |
| `TrendAnalyzer` | IC 趨勢 | `TrendDashboard` | 🟡 中：因子衰弱預警 |
| `ParameterSensitivityAnalyzer` | 參數敏感度 | `ParameterSensitivityHeatmap` | 🟡 中：策略穩健性 |
| `FactorExposureAnalyzer` | 因子曝險 | `FactorExposureRadar` | 🟡 中：風險分解 |
| `FactorCentralityAnalyzer` | 因子中心度 | `FactorCentralityChart` | 🟢 低：研究輔助 |
| `SignalDensityAnalyzer` | 訊號密度 | — | 🟢 低：訊號分佈 |
| `CalibrationAnalyzer` | 機率校準 | — | 🟢 低：ML 所需 |
| `LearningCurveAnalyzer` | 學習曲線 | — | 🟢 低：ML 所需 |
| `ParetoAnalyzer` | Pareto 前沿 | — | 🟢 低：多目標最佳化 |
| `CrossSymbolValidator` | 跨 Symbol 驗證 | — | 🟡 中：多標的場景 |
| `XGBoostAnalyzer` | XGBoost 重要性 | `ModelAttribution` | ✅ 已暴露 |
| `SHAPAnalyzer` | SHAP 解釋 | `ModelAttribution` | ✅ 已暴露 |
| `LightGBMAnalyzer` | LightGBM 重要性 | `ModelAttribution` | ✅ 已暴露 |

---

## 5. 功能規格（逐項）

> 每項包含：業界慣例說明 / 使用場景 / 輸入輸出 / API 需求 / 前端元件設計 / 驗收標準
> 
> **V0.4 修訂原則**：
> - 從實戰交易角度重新排優先序，**不做學術研究**
> - 將已有後端的功能與全新功能明確分開
> - 移除或降低 Factor Neutralization 等學術功能的優先序

---

### 5.1 截面 Rank IC（Cross-Sectional IC）— **前端暴露**

> ⚠️ **後端已完整實作**，只需前端 UI 修改。

**業界用途**  
驗證因子在多個標的上是否普遍有效，而不是只對單一 Symbol 過擬合。這是從「單標的研究」過渡到「多標的組合策略」的必要步驟。

**現狀**  
- ✅ 後端：`ic_filter_orchestrator.analyze_cross_sectional()` 完整可用，API `/api/v1/ic/analyze` 已接 `mode: "cross_sectional"`
- ❌ 前端：`ICConfigPanel.tsx` 的 mode 只有 `global` / `event`

**重要釋義：mode 與 event filter 的關係**  
- `global`：全量數據計算 IC（無競合）
- `event`：僅符合條件的子集計算 IC（EventFilter 篩後）
- `cross_sectional`：多 Symbol 同一時間點的截面 IC
- `cross_sectional` 與 `event` **互斥**，因為截面 IC 需要所有時間點的完整數據

**需做的事**  
1. `ICConfigPanel.tsx`：新增 `cross_sectional` mode radio 按鈕
2. mode = `cross_sectional` 時：顯示 Symbol 多選器（從 `scan_config.yaml` 讀取） + timeframe 選擇
3. 結果頁：顯示截面 IC 統計摘要表（Mean IC / ICIR / Positive Rate / t-stat per feature）

**不需做的事**  
- 不需新增後端 endpoint（已有）
- 不需新增後端計算邏輯（已有）

**驗收標準**  
- [ ] `ICConfigPanel` 出現第三個 mode：`截面 IC`
- [ ] 選擇 ≥ 2 個 Symbol 後可啟動分析，結果顯示在 `ICSummaryTable`
- [ ] 結果包含 Mean IC / ICIR / t-stat
- [ ] 前端限制每次最多 50 個因子進行截面 IC（超過時顯示提示而非送出請求）

---

### 5.2 Factor Turnover 時序圖 — **前端新增元件**

> ⚠️ **後端已完整實作**，只需新增前端時序圖元件。

**業界用途**  
高 IC 但高換手的因子，扣掉交易成本後可能沒有 alpha。Turnover 時序圖讓你看到「換手率在什麼時期飆高」，配合 Regime 分析判斷是否為市場異常。

**現狀**  
- ✅ 後端：`TurnoverAnalyzer` 有 `compute_quantile_turnover()` / `compute_rank_change_rate()` / `compute_all()`
- 🟡 前端：`NetICChart` 的泡泡圖 Z 軸讀 `turnover`，但無獨立時序折線圖

**需做的事**  
1. 在 IC Analysis 深度分析結果區新增 `TurnoverTimeSeriesChart.tsx`
2. 從現有 deep analysis report 中讀取 turnover 時序資料
3. 顯示 quantile_turnover + rank_change_rate 雙線 + 自相關數值

**驗收標準**  
- [ ] Turnover 時序折線可見，Y 軸為比例值（0~1，其中 1 = 100% 全換手；rank_change_rate 可能 > 1）
- [ ] hover tooltip 顯示具體 turnover 數值

---

### 5.3 IC 半衰期數值標注（Half-Life）— **前端標注**

> ⚠️ **後端已計算並回傳**，只需前端顯示。

**業界用途**  
IC 半衰期直接告訴你：這個因子的預測力能持續多久。半衰期 = 3 bars（12h K 棒）→ 建議 3 根 K 棒換倉一次。這是**設計策略換手頻率的關鍵依據**。

**現狀**  
- ✅ 後端：`ICEngine.compute_ic_decay()` 回傳 `half_life`、`decay_rate`、`fit_r2`、`decay_type`
- ✅ 後端：orchestrator 產出 report 含 `ic_half_life` 欄位
- ❌ 前端：`ICDecayChart.tsx` 只畫衰減曲線，未顯示半衰期數值

**需做的事**  
1. `ICDecayChart.tsx`：從 report 讀取 `half_life` 值
2. 在曲線圖上畫垂直虛線標注 half-life 位置
3. 顯示文字標籤：`Half-Life = N bars (≈ X 小時)` + `擬合 R² = 0.XX`
4. 若 `decay_type == "fit_failed"` 或 `fit_warning == true`，顯示警告標記

**驗收標準**  
- [ ] IC Decay 資料存在時，半衰期虛線與數值自動顯示
- [ ] 擬合品質差時（R² < 0.5 或 fit_failed），顯示警告標記
- [ ] 非指數衰減時，標注「不規則衰減」

---

### 5.4 多空累積淨值曲線（Long/Short Equity Curve）— **前後端均需工作**

**業界用途**  
Quantile Return 柱狀圖只告訴你「平均而言，Q5 比 Q1 賺得多」。但 Equity Curve 告訴你**整段歷史的逐K棒累積損益**，讓你看到最大回撤、因子失效期、以及不同 Regime 下的真實表現。**這是判斷因子能否實戰的最直觀指標。**

**現狀**  
- 🟡 後端：`MonotonicityTester.compute_quantile_returns()` 已回傳 `cumulative_returns` 欄位（需確認是 dict 或時序 list）；Deep Analysis 的 `FactorReturnAnalyzer` + `LongShortAnalyzer` 可計算收益時序
- ❌ 前端：`QuantileReturnChart` 只畫靜態柱狀平均值；`FactorReturnChart` 只讀 summary 單值

**實作前必須先確認**（阻塞題）：  
> 開始實作前，需先讀取 `MonotonicityTester.compute_quantile_returns()` 的回傳值，確認 `cumulative_returns` 是：
> - (a) 時序陣列 `[{bar_index, q1_cum, q2_cum, ..., q5_cum, ls_spread_cum}]` → 可直接繪製
> - (b) 或只是 summary 單值 `{q1: 0.12, q5: 0.45}` → 需新增後端 endpoint 回傳時序
> 
> 若為 (b)，Phase A 工作量從 1.5 天增加至 2.5 天。

**需做的事**  
1. 後端：確認 `cumulative_returns` 格式為時序陣列（若目前只是 summary 單值，需調整為逐 bar 累積）
2. 前端：新增 `EquityCurveChart.tsx` — ComposedChart，三條線（Long Q5 / Short Q1 / L-S Spread）
3. 摘要欄：Total Return / Max Drawdown / Sharpe Ratio

**驗收標準**  
- [ ] 三條線顏色區分可見（綠/紅/白）
- [ ] Max Drawdown 期間以帶狀陰影標注
- [ ] hover tooltip 顯示日期、淨值、當期回撤

---

### 5.5 Symbol Coverage Matrix — **需新增前後端**

**業界用途**  
多 Symbol 場景下，確認每個因子在每個 Symbol 的資料完整度。避免模型學到「因子在某幣種永遠為 NaN」的虛假模式。

**優先序條件**：只在使用 ≥ 3 個 Symbol 時才有意義。

**需做的事**  
1. 後端：新增 endpoint 計算 features × symbols 的 NaN 比率矩陣
2. 前端：新增 `SymbolCoverageMatrix.tsx` — 熱力圖

**驗收標準**  
- [ ] 50 Symbol × 100 因子矩陣在 15 秒內渲染
- [ ] 點擊格子顯示 NaN 比例 + 有效筆數

---

### 5.6 Factor Watchlist（因子標記系統）— **需新增前端**

**業界用途**  
研究員需要跨 Session 標記因子：「候選」→「已驗證」→「送入 ML」。這是整條研究流水線的**收尾環節**，缺此功能等於每次研究都從頭開始。

**資料結構**

```typescript
interface WatchlistEntry {
  feature_name: string;
  task_id: string;
  status: 'candidate' | 'verified' | 'rejected' | 'watching';
  note: string;
  ic_snapshot: number | null;
  added_at: string;
}
```

**儲存機制**  
- V1：localStorage（跨頁面有效，最多 500 因子）
- V2（Phase D 以後）：後端持久化 `data_cache/watchlists/`

**重要限制：task_id 生命週期**  
> Watchlist entry 中的 `task_id` 參考特定一次 Feature Factory 產出。若用戶重新生成因子（新 task_id），舊 Watchlist entry 的 task_id 仍有效（因為因子名稱即為唯一識別），但將無法在新 task 中查看對應詳細。V1 版的 Watchlist 以 `feature_name` 而非 `task_id` 作為主鍵，`task_id` 僅作為來源註記。

**需做的事**  
1. `WatchlistPanel.tsx` — 全域右側抽屜（Drawer）
2. Feature Browser / IC Analysis 列表每行加「⭐ 加入 Watchlist」
3. 匯出 `watchlist_YYYYMMDD.json`

**驗收標準**  
- [ ] 跨頁面標記持久化（Feature Browser ↔ IC Analysis）
- [ ] 匯出 JSON 可直接用於 ML 訓練的 `selected_features`

---

### 5.7 Time Series 命名篩選完整性（補強）

**已修復（2026-04-01）**：`browseFeatures` limit 從 200 升至 5000。

**待驗證**：因子超過 5000 時是否需改為後端 segment API。

**驗收標準**  
- [ ] 1,000 個因子時，Indicator 下拉選項完整
- [ ] 5,000 個因子時，載入 < 3 秒

---

### ~~5.8 IC 半衰期 × Rolling Band 組合視圖（進階）~~

> **V0.3 降級為 Phase D（低優先）**：此功能視覺上有趣但對交易決策的增量價值有限。IC 半衰期單獨標注（§5.3）+ Rolling Band 單獨運作已足夠。組合視圖在 V1.0 實戰流程中並非瓶頸。

---

## 6. 分階段實作路線圖

> **V0.3 重寫**：基於 §4 完整盤點結果，重新計算工作量。核心發現：後端已實作 24 個計算引擎，大部分項目只需前端工作。

### Phase A：暴露已有能力 + 核心前端補完（預計 3.5 天，若 Equity Curve 需新 endpoint 則 4.5 天）

**目標**：讓 §3.1 步驟 3 + 3.5 的「基礎 IC 驗證 + Deep Analysis 實戰驗證」在 UI 上完全可操作。

| # | 項目 | 類型 | 工作量 | 對應規格 | 後端狀態 |
|---|---|---|---|---|---|
| A1 | IC Decay 半衰期數值標注 | 純前端 | 0.5 天 | §5.3 | ✅ 後端回傳 `half_life` / `fit_r2` |
| A2 | 截面 IC mode UI 開關 + 結果表 | 純前端 | 1 天 | §5.1 | ✅ 後端 `analyze_cross_sectional()` |
| A3 | Factor Turnover 獨立時序圖 | 純前端 | 0.5 天 | §5.2 | ✅ 後端 `TurnoverAnalyzer` |
| A4 | Equity Curve（累積淨值）| 前後端 | 1.5~2.5 天 | §5.4 | 🟡 需先確認後端 `cumulative_returns` 格式（見 §5.4 阻塞題） |
| A5 | ~~修復命名篩選 limit~~ | — | — | §5.7 | ✅ **已完成** |
| A6 | ~~修復 Rolling Band stackId~~ | — | — | — | ✅ **已完成** |
| | **Phase A 小計** | | **3.5~4.5 天** | | |

**Phase A 完成判斷**：用戶在 IC Analysis 頁面可以 ① 看到 IC Decay 半衰期數值 ② 切換截面 IC mode ③ 看到獨立 Turnover 時序圖 ④ 看到多空累積淨值曲線。

---

### Phase B：因子研究工作流閉環（預計 4 天）

**目標**：讓 §3.1 完整流程走通，從 Feature Factory → Feature Browser → IC Analysis → ML Training 全程零中斷。

| # | 項目 | 類型 | 工作量 | 對應規格 |
|---|---|---|---|---|
| B1 | Factor Watchlist（localStorage 版）| 純前端 | 2 天 | §5.6 |
| B2 | Symbol Coverage Matrix | 前後端 | 1.5 天 | §5.5 |
| B3 | Deep Analysis 模組前端完整性驗證 | 純前端 | 0.5 天 | §4.2 B6 |
| | **Phase B 小計** | | **4 天** | |

**Phase B 完成判斷**：用戶可完成 §9 Scenario A 完整流程（生成 → 篩選 → 標記 → 匯出 → ML 訓練）。

---

### Phase C：多 Symbol 截面強化（預計 2 天）

**前提**：Phase B 完成 + 實際使用 ≥ 3 個 Symbol 進行研究。

| # | 項目 | 類型 | 工作量 |
|---|---|---|---|
| C1 | 截面 IC 結果深入分析（逐 Symbol IC 熱力圖） | 前端 | 1 天 |
| C2 | CrossSymbolValidator 前端元件 | 前端 | 1 天 |

---

### Phase D：自動化、持久化與學術功能（V2.0 配合期）

**前提**：Phase C 完成，系統穩定運行 1+ 月。

| 項目 | 說明 |
|---|---|
| Watchlist 後端持久化 | `localStorage` → `data_cache/watchlists/` |
| Watchlist → ML 一鍵串接 | 匯出後自動填入 LightGBM 特徵選擇頁 |
| 自動篩選建議（Auto-Suggest） | 根據 IC / ICIR / Turnover 閾值自動推薦因子 |
| IC × Rolling Band 組合視圖 | §5.8，視覺上有趣但增量價值有限 |
| Factor Neutralization | 去除市值/波動率暴露。加密貨幣單標的場景極少用 |

---

## 7. 擴充時機判斷準則

以下是判斷「何時可以進行下一個 Phase 擴充」的具體標準，不以時間表為強制依據：

| 準則 | 說明 |
|---|---|
| **穩定性準則** | Feature Factory 同一設定重跑，特徵數、IC 值誤差 < 0.1%，才考慮擴充多 Symbol |
| **資料量準則** | Symbol Coverage Matrix 和截面 IC 只在 ≥ 3 個 Symbol 有完整資料時才有意義 |
| **體驗準則** | 現有已實作功能無明顯視覺 Bug（Y 軸錯誤、時間軸截斷等）才進入下一 Phase |
| **Phase 轉換準則** | Phase A → B：Phase A 4 項全部完成 + 用戶已走過至少 1 次完整流程（步驟 1→4）；Phase B → C：Phase B Watchlist 可用 + 開始使用 ≥ 3 Symbol |
| **ML 銜接準則** | 截面 IC 只在準備執行「多 Symbol 聯合訓練」時才優先開發，否則推遲 |

---

## 8. 非功能性需求

### 8.1 效能

| 場景 | 要求 |
|---|---|
| Feature Browser 載入 5,000 個因子的名稱清單 | < 3 秒 |
| Rolling IC 計算（1,000 bars × 50 個因子） | < 5 秒（後端） |
| 截面 IC（30 Symbol × 50 因子 × 500 bars） | < 30 秒（後端） |
| Equity Curve（1 個因子 × 1 Symbol × 3,000 bars） | < 3 秒 |
| Time Series 圖表互動（Brush 拖動 Y 軸重算） | < 100ms（前端 useMemo） |

### 8.2 解耦架構（必須遵守）

所有後端新增 endpoint / 服務，必須遵循 `REFACTOR_ARCHITECTURE_V4`：

- 計算邏輯放在 `momentum/Analysis/` 或 `momentum/FeatureEngineering/`
- API 層只做薄路由，服務層調用 Factory 建構引擎
- `momentum/` 禁止 import `api/`

### 8.3 可測試性

- 每個新增後端 endpoint 必須有至少 1 個 pytest unit test
- 前端新增元件必須有手動測試 checklist（記錄於對應的 PLAN TODO 文件）

### 8.4 資料安全

- Watchlist 中儲存的因子名稱不含用戶原始資金或交易資訊，無敏感資料疑慮
- Symbol 清單來自後端 `config/scan_config.yaml`，不允許用戶任意輸入 URL 或路徑（防 SSRF）

---

## 9. 成功驗收標準

### 整體流程驗收（Phase B 完成後執行）

以下場景需完整走通，不中斷：

**Scenario A — 單 Symbol 完整研究流程**

1. Feature Factory 生成 BTCUSDT 12h，約 1,000 個因子
2. Feature Browser → Quality Scorecard 淘汰 NaN > 30%
3. Feature Browser → IC Dashboard 篩選 top 50（|IC| > 0.02）
4. Feature Browser → Correlation Matrix 合併 > 0.9 相關群組
5. 5 個因子加入 Watchlist，標記「候選」
6. IC Analysis → 啟動 8 階段流水線，結果表顯示 IC / ICIR / p-value
7. IC Analysis → IC Decay 確認半衰期 ≤ 5 bars，**數值標注可見**（§5.3）
8. IC Analysis → Deep Analysis → Equity Curve 確認 Long-Short Spread > 0（§5.4）
9. IC Analysis → Deep Analysis → Factor Turnover **時序圖** < 40%（§5.2）
10. IC Analysis → Deep Analysis → Regime Radar 確認各市場狀態下的 IC 差異（找出因子在哪種行情有效）
11. IC Analysis → Deep Analysis → OOS Validation 確認樣本外 IC 未崩塌
12. 3 個因子更新 Watchlist 標記為「已驗證」
13. 匯出 `watchlist_verified.json`
14. 開啟 LightGBM 訓練頁，手動貼入因子清單，執行訓練（V1.0 為手動貼上；Phase D 將實現一鍵串接）

**Scenario B — 多 Symbol 截面驗證（Phase C 完成後執行）**

1. Feature Factory 同設定生成 ETHUSDT + SOLUSDT（共 3 個 Symbol）
2. Feature Browser → Coverage Matrix（§5.5）確認三 Symbol 資料覆蓋率
3. IC Analysis → 截面 IC mode（§5.1），選擇 3 個 Symbol
4. 確認截面 Mean IC > 0.01 的因子
5. 匯出 Watchlist，執行多 Symbol 聯合訓練

**單項功能驗收標準**

| 功能 | 通過條件 |
|---|---|
| IC Half-Life 標注（§5.3） | IC Decay 圖有垂直虛線 + 數值標籤 + R² |
| 截面 IC mode（§5.1） | ICConfigPanel 第三個 mode 可選，結果表有 Mean IC / ICIR |
| Turnover 時序圖（§5.2） | 獨立折線圖 Y 軸為比例值 0~1（rank_change_rate 可 > 1），hover 有數值 |
| Equity Curve（§5.4） | 三條線（L/S/Spread），Max DD 陰影，hover 有淨值 |
| Watchlist（§5.6） | 跨頁面標記持久化，匯出 JSON 格式正確 |
| Coverage Matrix（§5.5） | 50×100 矩陣 < 15 秒渲染 |

---

## 10. 風險與假設

| 風險 | 說明 | 緩解方案 |
|---|---|---|
| 截面 IC 計算量過大 | 50 Symbol × 10,000 因子 × 500 bars，計算量巨大 | 限制截面 IC 每次最多 50 個因子；後端加 timeout 保護 |
| 因子命名規範不一致 | 不同版本 Feature Factory 輸出的命名段落可能不同 | 後端 browse_features 回傳時做 segment 正規化 |
| Recharts 圖表效能瓶頸 | 3,000 筆 × 5 條線的 ComposedChart 可能卡頓 | 前端 downsample（Brush 縮放時繪製可見範圍，最多 1,500 筆；全量數據僅用於 Brush 導航） |
| Watchlist localStorage 容量 | 5,000 個因子 × JSON 資料，約 500KB，接近 localStorage 5MB 上限 | V0.1 限制單一 Watchlist 最多 500 個因子 |
| Rolling Band 夾心法背景色耦合 | `fill="#0d1117"` 與 chart container 背景色寫死，若換主題會破版 | 未來抽取 CSS variable `--chart-bg`，或改用 SVG clipPath |

---

## 11. 名詞解釋

| 術語 | 說明 |
|---|---|
| **IC（Information Coefficient）** | 因子值與未來收益的 Spearman 相關係數。絕對值 > 0.02 通常視為有效 |
| **ICIR（IC Information Ratio）** | IC 均值 / IC 標準差。> 0.5 通常視為穩定因子 |
| **截面 IC（Cross-Sectional IC）** | 同一時間點對 N 個 Symbol 計算的 IC，反映因子普適性 |
| **IC 半衰期（Half-Life）** | IC Decay 曲線中，IC 值降至初始 50% 時對應的持有 bars 數 |
| **Factor Turnover** | 因子每期 top Q 持倉的更換比例，衡量換手成本 |
| **Equity Curve** | 假設按因子值做多/空，逐期累積的資金曲線 |
| **Long-Short Spread** | Top 分位組 - Bottom 分位組的平均收益差 |
| **Factor Neutralization** | 去除因子中市值、行業等系統性暴露，提取純 alpha 部分 |
| **Watchlist** | 用戶手動標記的重點因子清單，支援跨 Session 保存與匯出 |
| **夾心法（Sandwich Technique）** | 本系統解決 Recharts stackId Y 軸問題的 Area 渲染技巧 |
| **Symbol Coverage Matrix** | 多 Symbol × 多因子的資料覆蓋率熱力圖 |
| **8 階段流水線（8-Stage Pipeline）** | IC Analysis 核心流程：Ingestion → Preprocessing → Label Gen → Event Filter → IC Calc → Stat Validation → Redundancy → Report |
| **Deep Analysis** | 8 階段流水線之後的進階驗證，含 14+ 可選模組（Regime/OOS/FactorReturn/Turnover 等），透過 `DeepAnalysisConfigPanel` 啟用 |

---

## 變更記錄

| 版本 | 日期 | 說明 |
|---|---|---|
| V0.1 | 2026-04-01 | 初版建立。基於現況盤點對話，涵蓋 §5.1 ~ §5.8 共 8 項功能規格，分 Phase A~D 實作 |
| V0.2 | 2026-04-03 | 快速修正：§4.3 三項錯誤事實（ICIR/Turnover/截面IC 已有後端），新增 §4.4 架構差距表 |
| V0.3 | 2026-04-03 | 完整重審（Round 1）：§1.2 對比表 14 行 / §3.1 新增 Deep Analysis / §4 三級盤點(A/B/C) / §5 全重寫 / §6 重算工作量 / §9 新增驗收細項 |
| V0.4 | 2026-04-03 | 全文審查（Round 2）：修正 18 項矛盾與不一致——§1.1 問題陳述對齊實際 / §2.2 範疇精簡 / §3.2 指標分類 / §4.2 移除 QA task / §5 mode 釋義+阻塞題 / §6-9 工作量修正 / §10-11 補充 |
| V0.5 | 2026-04-03 | 全文審查（Round 3）：6 項實戰導向修正——Phase 轉換準則、50 因子限制、Regime 驗收實際化、交叉引用修復 |
| V0.6 | 2026-04-03 | 全文審查（Round 4）：最終一致性檢查——§9 Turnover Y 軸與 §5.2 對齊 / V0.5 header 清理 / V0.4 changelog 自含 |

---

*下一步：此規格書評審通過後，由 AI Agent 依照 Phase A,B,C,D 項目生成 `FACTOR_RESEARCH_PIPELINE_PLAN.md` 及對應 TODO。*
