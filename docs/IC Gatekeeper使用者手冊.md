# IC Gatekeeper 使用者手冊 — 步驟一＆二：完整項目索引（Frozen）

> **版本**: Index V1.0 (Frozen)  
> **建立日期**: 2026-02-18  
> **狀態**: 步驟一＆二已完成，六份索引已凍結  
> **來源文件**:  
> - `docs/IC 篩選器 (The IC Gatekeeper) 規格設計書.md`（以下簡稱 **SPEC**）  
> - `docs/IC_Gatekeep_優化SPEC.md`（以下簡稱 **優化SPEC**）  
> - `docs/IC_Gatekeeper_PLAN.md`（以下簡稱 **PLAN**）  
> - `docs/IC_Gatekeep_優化PLAN.md`（以下簡稱 **優化PLAN**）  
> - `config/ic_config.yaml`（實際組態檔，參數預設值以此為準）

---

## 索引 A：功能模組清單

> 列出所有在 SPEC/PLAN 中有獨立章節或設計區塊的功能單元。每個模組下另列其所包含的子項目。

---

### A1. 八階段流水線 (8-Stage Pipeline)（SPEC §2.1）

#### A1-1. Stage 0：數據載入 (Data Ingestion)（SPEC §2.3, §3.9）
- 讀取 Phase 1 特徵矩陣 (`features.h5`)
- 讀取特徵 Metadata (`meta.json`)
- 讀取 Label 矩陣 (`labels.h5`)
- 讀取原始 K 線數據 (`{symbol}_{tf}.h5`)
- 讀取 IC 配置 (`ic_config.yaml`)
- Stage 0 輸入驗證（SPEC §3.9.3）

#### A1-2. Stage 1：數據預處理器 (Data Preprocessor)（SPEC §3.1）
- 極端值處理 (Winsorization)（§3.1.1）
  - Winsorize（百分位截斷）
  - MAD Clip（中位數絕對偏差截斷）
  - Z-Score Clip（標準差截斷）
  - 無處理模式
- 缺失值處理（§3.1.2）
  - 期初 NaN 保留
  - 中段零星 NaN — Forward Fill（最多 N 期）
  - 大面積 NaN 標記為低覆蓋率
  - Label NaN 刪除對應行
- 因子標準化 (Factor Standardization)（§3.1.3）
  - Cross-Sectional Z-Score
  - Time-Series Z-Score
  - Rank Transform
  - 無標準化

#### A1-3. Stage 2：標籤生成器 (Label Generator)（SPEC §3.2）
- 收益率類型（§3.2.1）
  - Simple Return
  - Log Return
  - Excess Return（超額收益）
  - Risk-Adjusted Return（風險調整收益）
  - Winsorized Return（截尾收益）
- 多 Horizon 生成（§3.2.2）
- 多時間框架 Label 對齊（§3.2.3）
  - bar_count 模式
  - time_duration 模式

#### A1-4. Stage 3：事件過濾器 (Event Filter)（SPEC §3.3）
- Query String 解析引擎（§3.3.2）
  - 支援比較/邏輯/算術/括號/函式
  - 白名單安全機制
- Boolean Mask 生成
- 樣本數安全檢查 (Sample Size Guard)（§3.3.3）
  - Sufficient (N ≥ 200)
  - Marginal (100 ≤ N < 200)
  - Low Confidence (30 ≤ N < 100)
  - Insufficient (N < 30)
- 案例搜尋框架直接整合（§3.3.4）

#### A1-5. Stage 4：IC 核心計算引擎 (IC Engine)（SPEC §3.4）
- IC 計算方法
  - Pearson IC
  - Spearman Rank IC
  - Kendall Tau IC
- ICIR (IC Information Ratio)（§3.4.2）
  - IC Mean / IC Std / t-stat / p-value / Hit Rate
  - Rolling Window 自動調整（參考 TF = 12h）
- Rolling IC 時間序列（§3.4.3）
  - 多視窗滾動 IC（預設 [21, 63, 126]）
  - Rolling stride
- IC Decay 衰減分析（§3.4.4）
  - 多 Horizon IC 曲線
  - IC 半衰期 (Half-Life) 計算
- 分組 IC 分析 (Grouped IC)（§3.4.5）
  - 依年份 (by_year)
  - 依季度 (by_quarter)
  - 依市場狀態 (by_regime)
  - 依波動度 (by_volatility)
  - 依指標類別 (by_category)
  - 依資料來源 (by_data_source)
  - 依 Pipeline 層級 (by_layer)
- IC 自相關 (IC Autocorrelation)

#### A1-6. Stage 5：統計驗證 + 單調性測試（SPEC §3.4 實作說明, §3.5）

**統計驗證器 (Statistical Validator)**（SPEC §3.4 實作說明）
- p-value 計算
- t-statistic 計算
- 信賴區間計算
- FDR (False Discovery Rate) 控制

**單調性測試器 (Monotonicity Tester)**（SPEC §3.5）
- 分位數收益分析 (Quantile Return Analysis)
  - 五分位（Quintile）分組
  - 各分位累積收益曲線
- Long-Short Spread（§3.5.2）
  - Long-Short Return
  - Long-Short Sharpe
  - Long-Short t-stat
- 單調性分數 (Monotonicity Score)（§3.5.3）
  - 嚴格單調比例 (Strict Monotonic)
  - Spearman 等級相關
  - R² 擬合度

#### A1-7. Stage 6：冗餘過濾器 (Redundancy Filter)（SPEC §3.6）
- 相關性矩陣計算
- 貪婪去重 (Greedy Deduplication)（預設策略）
  - 相關性門檻 (correlation_threshold = 0.7)
  - Tiebreaker 機制（ICIR / IC Mean / Monotonicity）
- 階層聚類 (Hierarchical Clustering)
  - 連結方法 (linkage_method = average)
- VIF 多重共線性檢測 (Variance Inflation Factor)
  - max_vif = 10.0
- 多元化指標 (Diversification Metrics)
  - 最少類別數 (min_categories)
  - 最少資料源數 (min_data_sources)
  - 同類別上限比例 (max_same_category_pct)

#### A1-8. Stage 7：報告生成（SPEC §3.7, §3.8, §6）

**換手率分析器 (Turnover Analyzer)**（SPEC §3.7）
- 分位數換手率 (Quantile Turnover)
- 等級變化率 (Rank Change Rate)
- 因子自相關 (Factor Autocorrelation)
- 淨 IC 代理估算 (Net IC Proxy)

**覆蓋率分析器 (Coverage Analyzer)**（SPEC §3.8）
- 時間覆蓋率 (Time Coverage)
- 橫截面覆蓋率 (Cross-Section Coverage)
- 有效起始點 (Valid Start Point)

**IC 報告器 (IC Reporter)**（SPEC §6）
- JSON 結構化報告 (`ic_report.json`)
- AI 可讀摘要報告 (`ic_summary.md`)
- 篩選日誌 (`ic_filter_log.json`)
- 相關性矩陣 (`correlation_matrix.json`)

#### A1-9. 流水線協調器 (IC Filter Orchestrator)（SPEC §3.9）
- 八階段流水線編排
- 篩選日誌 (Filter Log) 追蹤
- 快取策略 — 支援 `refilter`（不重算 IC）（§3.9.3）
- Stage 0 輸入驗證（§3.9.4）
- 雙模式支援：Global Mode / Event Mode（§2.2）

---

### A2. 模型驗證 (Model Validation Part B)（SPEC §7）

#### A2-1. CV 驗證器 (CV Validator)（SPEC §7.1）
- Time-Series Split（非隨機 KFold）
- Fold AUC 記錄
- CV AUC Mean ± Std
- OOT (Out-of-Time) 切分

#### A2-2. OOT 驗證器 (OOT Validator)（SPEC §7.4）
- 時間序列切分
- AUC / Precision / Recall / F1
- CV-OOT Gap 計算
- Overfit Warning（Gap > 0.1）

#### A2-3. PSI 計算器 (PSI Calculator)（SPEC §7.5）
- PSI 公式 (Population Stability Index)
- 等頻分箱
- 穩定性分類：stable / slight_shift / significant_shift

#### A2-4. 滾動 AUC 追蹤器 (Rolling AUC Tracker)（SPEC §7.2）
- 滾動窗口 AUC 計算
- 趨勢判斷 (stable / declining / improving)

#### A2-5. 單案例 SHAP 解釋器 (Case SHAP Explainer)（SPEC §7.3）
- 單筆預測 SHAP 解釋
- 批次 SHAP 特徵重要性排名

---

### A3. 十大深度分析模組 (10 Deep Analysis Modules)（優化SPEC §3-§4）

#### A3-1. Module 1：因子回報分析器 (Factor Return Analyzer)（優化SPEC §3.1）
- 分位數回報時間序列 (Quantile Returns)
- 各分位累積收益曲線 (Cumulative Returns)
- 風險指標計算
  - Sharpe Ratio
  - Sortino Ratio
  - Calmar Ratio
  - Max Drawdown
  - Win Rate
- 批次計算 (Batch Compute)

#### A3-2. Module 2：因子中心度分析器 (Factor Centrality Analyzer)（優化SPEC §3.2）
- PCA 中心度計算 (PCA-based Centrality)
- 滾動中心度 (Rolling Centrality)
- 擁擠因子偵測 (Crowding Detection)
- 有效維度 (Effective Rank)

#### A3-3. Module 3：趨勢分析器 (Trend Analyzer)（優化SPEC §3.3）
- 線性迴歸趨勢（Rolling IC / Centrality / Factor Return / LS-Spread）
- 綜合信號 (Combined Signal)：正常 / 警告 / 危險
- IC Decay 交叉參照（Half-Life 整合）

#### A3-4. Module 4：參數敏感度分析器 (Parameter Sensitivity Analyzer)（優化SPEC §3.4）
- 特徵族群偵測 (Feature Family Detection)
- IC 穩定度分析 (IC Stability)
- 過擬合風險分類 (Overfitting Risk)：low / medium / high
- 自動族群偵測 (Auto-Detect Families)

#### A3-5. Module 5：滾動樣本外驗證器 (Rolling OOS Validator)（優化SPEC §3.5）
- Walk-Forward 驗證
- IS (In-Sample) vs OOS (Out-of-Sample) IC 比較
- 衰退比 (Degradation Ratio)
- 評估等級：robust / moderate / overfitting

#### A3-6. Module 6：因子正交化器 (Factor Orthogonalizer)（優化SPEC §4.1）
- Gram-Schmidt 正交化 (QR Decomposition)
- PCA 正交化
- 正交化前後相關性比較
- 退化偵測 (Degenerate Detection)

#### A3-7. Module 7：因子曝險分析器 (Factor Exposure Analyzer)（優化SPEC §4.2）
- 投資組合因子曝險 (Portfolio Exposure)
- 因子歸因迴歸 (Factor Attribution Regression)
- HHI 集中度 (Herfindahl-Hirschman Index)

#### A3-8. Module 8：多空分析器 (Long-Short Analyzer)（優化SPEC §4.3）
- 多方 / 空方分別計算 IC 與報酬
- 不對稱性分析 (Asymmetry Analysis)
- 多空建議 (Recommendation)

#### A3-9. Module 9：特徵品質診斷 (Feature Quality Diagnostics)（優化SPEC §4.4）
- ADF 定態性檢驗 (Augmented Dickey-Fuller)
- Ljung-Box 自相關檢驗
- CUSUM 概念漂移偵測
- PSI 分佈漂移偵測
- 覆蓋率統計 (Coverage Statistics)
- 冗餘預掃描 (Redundancy Pre-Scan)

#### A3-10. Module 10：淨 IC 分析器 (Net IC Analyzer)（優化SPEC §4.5）
- 淨 IC 計算：Net IC = Gross IC − cost × turnover
- 淨因子回報 (Net Factor Return)
- 成本敏感度分析 (Cost Sensitivity)
- 損益兩平成本 (Breakeven Cost)
- 因子容量估計 (Factor Capacity)

---

### A4. 功能層級與開關管理系統 (Feature Tier & Toggle)（優化SPEC §17）

- 三級預設 (Presets)
  - L1🟢 Foundation（基礎）
  - L2🟡 Intermediate（進階）
  - L3🔴 Advanced（完整）
  - Custom（自訂）
- 23 個功能模塊分級分類（§17.3）
- FeatureTierPanel 前端面板（§17.5）
- Orchestrator 整合（§17.6）

---

### A5. 多格式匯出系統 (Multi-Format Export)（優化SPEC §18）

- CSV 摘要 (CSV Summary)（§18.3）
- CSV 詳細 — 8 個模組各自匯出（§18.3）
- AI 可讀 JSON (_ai.json)（§18.4）
- 增強版 Markdown（§18.5）
- HDF5 精選特徵矩陣
- PNG 圖表匯出
- API 匯出端點 GET `/export/{task_id}/{format}`（§18.6）

---

### A6. 特徵瀏覽器 (Feature Browser)（優化SPEC §19）

- Dashboard 總覽（6 張摘要卡片）（§19.3）
- Tab 1：目錄 (Catalog)（10 欄位表格）（§19.4）
- Tab 2：分佈 (Distribution)（直方圖 + 箱線圖 + 統計量）（§19.5）
- Tab 3：時間序列 (Time Series)（ACF + 季節性）（§19.6）
- Tab 4：相關性 (Correlation)（熱力圖 + 散佈圖 + 樹狀圖）（§19.7）
- Tab 5：品質 (Quality)（覆蓋率熱力圖 + ADF）（§19.8）
- Tab 6：數據表 (Data Table)（虛擬分頁）（§19.9）

---

### A7. 配置管理系統 (Config Management)（SPEC §5）

- 三層配置策略：預設 YAML < 使用者 YAML < API Override
- ic_config.yaml 結構（SPEC §5.1）
- Pydantic Config Schema (ic_config_schema.py)（SPEC §5.3）
- MCP Tools 配置介面（SPEC §5.4）
- NL2Config 自然語言轉配置（SPEC §5.5）

---

### A8. API 層 (API Layer)（SPEC §9, 優化SPEC §7）

- REST 端點
  - IC 分析觸發 (`POST /ic-analysis/analyze`)
  - 任務狀態查詢 (`GET /ic-analysis/task/{task_id}`)
  - Top 特徵查詢
  - 重新篩選 (Refilter)
  - 特徵清單 (`GET /features/list`)（優化SPEC §7）
  - 深度分析 (`POST /deep-analysis`)（優化SPEC §7）
  - 完整分析 (`POST /full-analysis`)（優化SPEC §7）
  - 匯出 (`GET /export/{task_id}/{format}`)（優化SPEC §18.6）
  - Feature Browser 6 個端點（優化SPEC §19.10）
- WebSocket 進度推送 (`/ws/ic-analysis/{task_id}`)
- Pydantic Request/Response Models (ic_models.py)
- API Service (ic_analysis_service.py)

---

### A9. 前端 UI (Frontend UI)（SPEC §6, 優化SPEC §8, §19）

- 基礎圖表（SPEC §6 — C1~C12）
  - C1: IC Heatmap
  - C2: IC Distribution
  - C3: Rolling IC Chart
  - C4: IC Decay Chart
  - C5: Monotonicity (Quantile Returns) Chart
  - C6: Correlation Heatmap
  - C7: Filter Funnel Chart
  - C8: Coverage Chart
  - C9: Turnover Chart
  - C10: Regime IC Comparison
  - C11: Top Features Table
  - C12: IC Summary Dashboard
- 深度分析圖表（優化SPEC §8.4 — C13~C22）
  - C13: Factor Return Chart
  - C14: Factor Centrality Chart
  - C15: PCA Explained Chart
  - C16: Trend Dashboard
  - C17: Parameter Sensitivity Heatmap
  - C18: OOS Distribution Chart
  - C19: Long-Short Comparison Chart
  - C20: Factor Exposure Radar
  - C21: Feature Quality Dashboard
  - C22: Net IC Chart
- Feature Selection 2-Stage 機制（優化SPEC §8.1）
- DeepAnalysisConfigPanel（優化SPEC §8.3）
- Partial Failure UI（優化SPEC §8.8）
- Feature Browser 6-tab 頁面（優化SPEC §19.2）
- Zustand Store (icAnalysisStore, featureBrowserStore)（優化SPEC §8.6, §19.13）

---

### A10. MCP Tool 介面 (MCP Tool Interface)（優化SPEC §15）
- `ic_deep_analysis_query` Tool
- Agent 查詢範例
- V1 → V2 → V3 版本演化

---

### A11. 架構基礎設施 (Architecture Infrastructure)

#### A11-1. Protocol 定義（SPEC §10, PLAN §1.1）
- `IICAnalyzer`（跨 Domain Protocol — `momentum/core/protocols.py`）
- `ILabelGenerator`（跨 Domain Protocol）
- `ICVValidator`（跨 Domain Protocol）
- `IEventFilter`（模組內部介面 — 不入 protocols.py）
- `IRedundancyFilter`（模組內部介面）

#### A11-2. Factory 函式（SPEC §10.2, 優化SPEC §6.4）
- `create_ic_analyzer()`
- `create_label_generator()`
- `create_cv_validator()`
- `create_psi_calculator()`
- 深度分析 10 個 Factory（優化SPEC §6.4）

#### A11-3. 例外類別 (Exceptions)（PLAN Changelog V4 #3）
- `InsufficientDataError`
- `InvalidQueryError`
- `InvalidInputError`

#### A11-4. 錯誤處理模式 — SkippedResult（優化SPEC §12）
- `SkippedResult` dataclass
- `DeepAnalysisReport` dataclass
- 6 種錯誤類型分類

---

## 索引 B：術語全集

> 凡在參考文件中出現的所有術語、指標名稱、演算法名稱、數學方法名稱，一律收錄。

| # | 術語名稱（英文） | 出現位置 |
|---|----------------|---------|
| 1 | IC (Information Coefficient) | SPEC §1.1, §3.4 |
| 2 | Spearman Rank IC | SPEC §3.4, §1.4 R1 |
| 3 | Pearson IC | SPEC §3.4, §1.4 R1 |
| 4 | Kendall Tau IC | SPEC §3.4 |
| 5 | ICIR (IC Information Ratio) | SPEC §3.4.2, §1.4 R2 |
| 6 | Rolling IC | SPEC §3.4.3, §1.4 R3 |
| 7 | IC Decay (IC 衰減) | SPEC §3.4.4, §1.4 R7 |
| 8 | IC Half-Life (IC 半衰期) | SPEC §3.4.4, §1.4 R10, 優化SPEC §3.3 |
| 9 | Conditional IC (條件 IC) | SPEC §3.3, §1.4 R4 |
| 10 | Grouped IC (分組 IC) | SPEC §3.4.5, §1.4 R9 |
| 11 | IC Autocorrelation (IC 自相關) | SPEC §3.4 |
| 12 | IC Hit Rate (IC 正報率) | SPEC §3.4.2 |
| 13 | t-statistic (t 統計量) | SPEC §3.4.2, §3.4 實作說明 |
| 14 | p-value (p 值) | SPEC §3.4 實作說明, §1.4 R8 |
| 15 | FDR (False Discovery Rate) | SPEC §3.4 實作說明 |
| 16 | Confidence Interval (信賴區間) | SPEC §3.4 實作說明 |
| 17 | Winsorization (極端值截斷) | SPEC §3.1.1, §1.4 R20 |
| 18 | MAD Clip (中位數絕對偏差截斷) | SPEC §3.1.1 |
| 19 | Z-Score Clip (標準差截斷) | SPEC §3.1.1 |
| 20 | Cross-Sectional Z-Score (橫截面 Z 分數) | SPEC §3.1.3 |
| 21 | Time-Series Z-Score (時間序列 Z 分數) | SPEC §3.1.3 |
| 22 | Rank Transform (等級轉換) | SPEC §3.1.3 |
| 23 | Simple Return (簡單收益率) | SPEC §3.2.1 |
| 24 | Log Return (對數收益率) | SPEC §3.2.1 |
| 25 | Excess Return (超額收益) | SPEC §3.2.1 |
| 26 | Risk-Adjusted Return (風險調整收益) | SPEC §3.2.1 |
| 27 | Winsorized Return (截尾收益) | SPEC §3.2.1 |
| 28 | Horizon (展望窗口) | SPEC §3.2.2 |
| 29 | Multi-TF Alignment (多時間框架對齊) | SPEC §3.2.3 |
| 30 | Event Filter (事件過濾) | SPEC §3.3 |
| 31 | Query String (查詢字串) | SPEC §3.3.2 |
| 32 | Boolean Mask (布林遮罩) | SPEC §3.3.2 |
| 33 | Sample Size Guard (樣本數安全檢查) | SPEC §3.3.3 |
| 34 | Statistical Power (統計檢定力) | SPEC §3.3.3 |
| 35 | Forward Fill (前向填補) | SPEC §3.1.2 |
| 36 | Coverage (覆蓋率) | SPEC §3.8, §1.4 R15 |
| 37 | Monotonicity Score (單調性分數) | SPEC §3.5.3, §1.4 R6 |
| 38 | Quantile Return Analysis (分位數收益分析) | SPEC §3.5 |
| 39 | Quintile (五分位) | SPEC §3.5 |
| 40 | Long-Short Spread (多空利差) | SPEC §3.5.2, §1.4 R12 |
| 41 | Long-Short Return | SPEC §3.5.2 |
| 42 | Long-Short Sharpe | SPEC §3.5.2 |
| 43 | Long-Short t-stat | SPEC §3.5.2 |
| 44 | Strict Monotonic (嚴格單調) | SPEC §3.5.3 |
| 45 | Spearman Rank Correlation (Spearman 等級相關) | SPEC §3.5.3 |
| 46 | R-squared (R² 擬合度) | SPEC §3.5.3, 優化SPEC §3.3 |
| 47 | Redundancy Filter (冗餘過濾) | SPEC §3.6, §1.4 R5 |
| 48 | Correlation Matrix (相關性矩陣) | SPEC §3.6 |
| 49 | Greedy Deduplication (貪婪去重) | SPEC §3.6 |
| 50 | Hierarchical Clustering (階層聚類) | SPEC §3.6 |
| 51 | VIF (Variance Inflation Factor，方差膨脹因子) | SPEC §3.6, §1.4 R17 |
| 52 | Tiebreaker (平手裁決) | SPEC §3.6 |
| 53 | Diversification (多元化) | SPEC §3.6 |
| 54 | Turnover (換手率) | SPEC §3.7, §1.4 R11 |
| 55 | Quantile Turnover (分位數換手率) | SPEC §3.7 |
| 56 | Rank Change Rate (等級變化率) | SPEC §3.7 |
| 57 | Factor Autocorrelation (因子自相關) | SPEC §3.7 |
| 58 | Net IC (淨 IC) | SPEC §3.7.3, 優化SPEC §4.5 |
| 59 | Transaction Cost (交易成本) | SPEC §3.7.3 |
| 60 | Time Coverage (時間覆蓋率) | SPEC §3.8 |
| 61 | Cross-Section Coverage (橫截面覆蓋率) | SPEC §3.8 |
| 62 | Valid Start Point (有效起始點) | SPEC §3.8 |
| 63 | Filter Log (篩選日誌) | SPEC §3.9 |
| 64 | Refilter (重新篩選) | SPEC §3.9.3 |
| 65 | Global Mode (全域模式) | SPEC §2.2 |
| 66 | Event Mode (事件模式) | SPEC §2.2 |
| 67 | Regime (市場狀態) | SPEC §3.4.5 |
| 68 | Bull Market / Bear Market (牛市 / 熊市) | SPEC §3.4.5, config/ic_config.yaml |
| 69 | High Volatility / Low Volatility (高波動 / 低波動) | SPEC §3.4.5, config/ic_config.yaml |
| 70 | EMA (Exponential Moving Average) | config/ic_config.yaml (close_EMA_55) |
| 71 | CV (Cross-Validation，交叉驗證) | SPEC §7.1 |
| 72 | Time-Series Split (時間序列切分) | SPEC §7.1 |
| 73 | Fold AUC | SPEC §7.1 |
| 74 | AUC (Area Under Curve) | SPEC §7 |
| 75 | OOT (Out-of-Time) | SPEC §7.4 |
| 76 | CV-OOT Gap | SPEC §7.4 |
| 77 | Overfitting (過擬合) | SPEC §7.4 |
| 78 | PSI (Population Stability Index) | SPEC §7.5, 優化SPEC §4.4 |
| 79 | Rolling AUC (滾動 AUC) | SPEC §7.2 |
| 80 | SHAP (SHapley Additive exPlanations) | SPEC §7.3 |
| 81 | Feature Importance (特徵重要性) | SPEC §7.3 |
| 82 | Factor Return (因子回報) | 優化SPEC §3.1 |
| 83 | Cumulative Return (累積收益) | 優化SPEC §3.1 |
| 84 | Sharpe Ratio (夏普比率) | 優化SPEC §3.1 |
| 85 | Sortino Ratio (索提諾比率) | 優化SPEC §3.1 |
| 86 | Calmar Ratio (卡爾瑪比率) | 優化SPEC §3.1 |
| 87 | Max Drawdown (最大回撤) | 優化SPEC §3.1 |
| 88 | Win Rate (勝率) | 優化SPEC §3.1 |
| 89 | Risk-Free Rate (無風險利率) | 優化SPEC §3.1 |
| 90 | PCA (Principal Component Analysis，主成分分析) | 優化SPEC §3.2 |
| 91 | Centrality (中心度) | 優化SPEC §3.2 |
| 92 | Crowded Factor (擁擠因子) | 優化SPEC §3.2 |
| 93 | Effective Rank (有效維度) | 優化SPEC §3.2 |
| 94 | Rolling Centrality (滾動中心度) | 優化SPEC §3.2 |
| 95 | Crowded Threshold (擁擠門檻) | 優化SPEC §3.2 |
| 96 | Linear Regression (線性迴歸) | 優化SPEC §3.3 |
| 97 | Combined Signal (綜合信號) | 優化SPEC §3.3 |
| 98 | Trend (趨勢) | 優化SPEC §3.3 |
| 99 | Feature Family (特徵族群) | 優化SPEC §3.4 |
| 100 | Parameter Sensitivity (參數敏感度) | 優化SPEC §3.4 |
| 101 | Overfitting Risk (過擬合風險) | 優化SPEC §3.4 |
| 102 | Walk-Forward Validation (步進式驗證) | 優化SPEC §3.5 |
| 103 | In-Sample (IS，樣本內) | 優化SPEC §3.5 |
| 104 | Out-of-Sample (OOS，樣本外) | 優化SPEC §3.5, §1.4 R16 |
| 105 | Degradation Ratio (衰退比) | 優化SPEC §3.5 |
| 106 | Gram-Schmidt Orthogonalization (Gram-Schmidt 正交化) | 優化SPEC §4.1 |
| 107 | QR Decomposition (QR 分解) | 優化SPEC §4.1 |
| 108 | Factor Orthogonalization (因子正交化) | 優化SPEC §4.1 |
| 109 | Degenerate (退化) | 優化SPEC §4.1 |
| 110 | Factor Exposure (因子曝險) | 優化SPEC §4.2 |
| 111 | Factor Attribution (因子歸因) | 優化SPEC §4.2 |
| 112 | HHI (Herfindahl-Hirschman Index) | 優化SPEC §4.2 |
| 113 | Factor Beta (因子 Beta) | 優化SPEC §4.2 |
| 114 | Alpha (超額報酬) | 優化SPEC §4.2 |
| 115 | Long-Short Analyzer (多空分析) | 優化SPEC §4.3 |
| 116 | Asymmetry (不對稱性) | 優化SPEC §4.3 |
| 117 | Long Quantiles / Short Quantiles (多方分位 / 空方分位) | 優化SPEC §4.3 |
| 118 | ADF (Augmented Dickey-Fuller Test) | 優化SPEC §4.4 |
| 119 | Stationarity (定態性) | 優化SPEC §4.4 |
| 120 | Ljung-Box Test | 優化SPEC §4.4 |
| 121 | Autocorrelation (自相關) | 優化SPEC §4.4 |
| 122 | CUSUM (Cumulative Sum Control Chart) | 優化SPEC §4.4 |
| 123 | Concept Drift (概念漂移) | 優化SPEC §4.4 |
| 124 | Redundancy Pre-Scan (冗餘預掃描) | 優化SPEC §4.4 |
| 125 | Net IC (淨 IC) | 優化SPEC §4.5 |
| 126 | Cost Drag (成本拖累) | 優化SPEC §4.5 |
| 127 | Breakeven Cost (損益兩平成本) | 優化SPEC §4.5 |
| 128 | Factor Capacity (因子容量) | 優化SPEC §4.5 |
| 129 | Participation Rate (參與率) | 優化SPEC §4.5 |
| 130 | Slippage (滑價) | 優化SPEC §4.5 |
| 131 | Cost Scenarios (成本情境) | 優化SPEC §4.5 |
| 132 | SkippedResult (跳過結果) | 優化SPEC §12, 優化PLAN §2 |
| 133 | DeepAnalysisReport (深度分析報告結構) | 優化SPEC §12, 優化PLAN §2 |
| 134 | Feature Tier (功能層級) | 優化SPEC §17 |
| 135 | L1 Foundation / L2 Intermediate / L3 Advanced | 優化SPEC §17.2 |
| 136 | Preset (預設組合) | 優化SPEC §17.4 |
| 137 | AI-Readable JSON (AI 可讀 JSON) | 優化SPEC §18.4 |
| 138 | Filter Funnel (篩選漏斗) | SPEC §6 (C7), 優化SPEC §18.4 |
| 139 | KDE (Kernel Density Estimation，核密度估計) | 優化SPEC §8.4 C18 |
| 140 | Box Plot (箱線圖) | 優化SPEC §8.4 C18, §19.5 |
| 141 | Dendrogram (樹狀圖) | 優化SPEC §19.7 |
| 142 | ACF (Autocorrelation Function，自相關函式) | 優化SPEC §19.6 |
| 143 | FFT (Fast Fourier Transform，快速傅立葉轉換) | 優化SPEC §19.6 |
| 144 | Kaiser Criterion (Kaiser 準則) | 優化SPEC §3.2 |
| 145 | Newey-West (Newey-West 修正) | 優化SPEC §4.5 |
| 146 | Shapley Value (Shapley 值) | 優化SPEC §5 (P2 延遲) |
| 147 | Bootstrap (自助法) | 優化SPEC §5 (P2 延遲) |
| 148 | Factor Neutralization (因子中性化) | SPEC §1.4 R18, 優化SPEC §5 (P2 延遲) |
| 149 | Regime-Aware (市場狀態感知) | 優化SPEC §16 |
| 150 | Jarque-Bera Test | 優化SPEC §19.5 |
| 151 | Precision / Recall / F1 | SPEC §7.4 |
| 152 | Linkage Method (連結方法) | SPEC §3.6 |
| 153 | Metadata (特徵詮釋資料) | SPEC §2.3 |
| 154 | Seven-Segment Naming (七段式命名) | SPEC §1.3 |
| 155 | Factor Standardization (因子標準化) | SPEC §3.1.3 |
| 156 | Label Generator (標籤生成器) | SPEC §3.2 |
| 157 | Data Preprocessor (數據預處理器) | SPEC §3.1 |
| 158 | IC Reporter (IC 報告器) | SPEC §6 |
| 159 | IC Filter Orchestrator (IC 篩選協調器) | SPEC §3.9 |
| 160 | Sample Size Tier (樣本數層級) | SPEC §3.3.3 |
| 161 | Rolling Stride (滾動步長) | SPEC §3.4.3, config/ic_config.yaml |
| 162 | n_components (PCA 主成分數) | 優化SPEC §3.2 |
| 163 | Cost BPS (成本基點) | 優化SPEC §4.5 |

---

## 索引 C：可調參數全集

> 列出所有使用者可調整的參數名稱，含預設值和所在模組。  
> **預設值來源：`config/ic_config.yaml`（實際組態檔，為最終權威來源）**

### C1. 全域設定 (global)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `global.default_method` | `"spearman"` | 全域 — IC 計算方法 |
| `global.default_horizon` | `5` | 全域 — 預設展望窗口 |
| `global.time_duration_mode` | `false` | 全域 — 時間語義模式 |

### C2. 預處理 (preprocessing)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `preprocessing.winsorization.enabled` | `true` | Stage 1 Data Preprocessor |
| `preprocessing.winsorization.method` | `"percentile"` | Stage 1 Data Preprocessor |
| `preprocessing.winsorization.lower_percentile` | `1.0` | Stage 1 Data Preprocessor |
| `preprocessing.winsorization.upper_percentile` | `99.0` | Stage 1 Data Preprocessor |
| `preprocessing.missing_values.max_fill_forward` | `3` | Stage 1 Data Preprocessor |
| `preprocessing.missing_values.min_coverage` | `0.3` | Stage 1 Data Preprocessor |

### C3. 標籤設定 (labels)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `labels.return_type` | `"simple"` | Stage 2 Label Generator |
| `labels.horizons` | `[1, 2, 3, 5, 8, 13, 21]` | Stage 2 Label Generator |
| `labels.horizons_time` | `null` | Stage 2 Label Generator |
| `labels.winsorize_returns` | `true` | Stage 2 Label Generator |

### C4. 事件過濾 (event_filter)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `event_filter.enabled` | `false` ⚠️ | Stage 3 Event Filter |
| `event_filter.query` | `null` | Stage 3 Event Filter |
| `event_filter.min_events` | `30` | Stage 3 Event Filter |
| `event_filter.sample_size_tiers.sufficient` | `200` | Stage 3 Event Filter |
| `event_filter.sample_size_tiers.marginal` | `100` | Stage 3 Event Filter |
| `event_filter.sample_size_tiers.low_confidence` | `30` | Stage 3 Event Filter |

### C5. IC 計算 (ic_calculation)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `ic_calculation.methods` | `["spearman"]` | Stage 4 IC Engine |
| `ic_calculation.rolling_windows` | `[21, 63, 126]` | Stage 4 IC Engine |
| `ic_calculation.rolling_stride` | `1` | Stage 4 IC Engine |
| `ic_calculation.ic_decay_horizons` | `[1, 2, 3, 5, 8, 13, 21]` | Stage 4 IC Engine |
| `ic_calculation.icir.window` | `63` | Stage 4 IC Engine — ICIR |
| `ic_calculation.icir.reference_tf` | `"12h"` | Stage 4 IC Engine — ICIR |

### C6. 分組分析 (grouped_analysis)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `ic_calculation.grouped_analysis.by_year` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_quarter` | `false` ⚠️ | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_regime` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_volatility` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_category` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_data_source` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.by_layer` | `true` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.regime_definitions.bull` | `"close > close_EMA_55"` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.regime_definitions.bear` | `"close < close_EMA_55"` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.regime_definitions.high_vol_percentile` | `80` | Stage 4 Grouped IC |
| `ic_calculation.grouped_analysis.regime_definitions.low_vol_percentile` | `20` | Stage 4 Grouped IC |

### C7. 篩選門檻 (thresholds)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `thresholds.ic_mean_min` | `0.02` | Stage 5 Statistical Validation |
| `thresholds.icir_min` | `0.5` | Stage 5 Statistical Validation |
| `thresholds.p_value_max` | `0.05` | Stage 5 Statistical Validation |
| `thresholds.ic_hit_rate_min` | `0.55` | Stage 5 Statistical Validation |
| `thresholds.monotonicity_score_min` | `0.6` | Stage 5 Monotonicity Tester |
| `thresholds.coverage_min` | `0.5` | Stage 5 Coverage |
| `thresholds.long_short_spread.enabled` | `false` ⚠️ | Stage 5 Monotonicity Tester |
| `thresholds.long_short_spread.min_spread` | `0.01` | Stage 5 Monotonicity Tester |

### C8. 冗餘去除 (redundancy)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `redundancy.method` | `"greedy"` | Stage 6 Redundancy Filter |
| `redundancy.correlation_threshold` | `0.7` | Stage 6 Redundancy Filter |
| `redundancy.tiebreaker` | `"icir"` | Stage 6 Redundancy Filter |
| `redundancy.hierarchical.linkage_method` | `"average"` | Stage 6 Redundancy Filter |
| `redundancy.vif.max_vif` | `10.0` | Stage 6 Redundancy Filter |
| `redundancy.diversification.min_categories` | `3` | Stage 6 Redundancy Filter |
| `redundancy.diversification.min_data_sources` | `2` | Stage 6 Redundancy Filter |
| `redundancy.diversification.max_same_category_pct` | `0.4` | Stage 6 Redundancy Filter |

### C9. 換手率 (turnover)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `turnover.enabled` | `true` | Turnover Analyzer |
| `turnover.transaction_cost` | `0.001` | Turnover Analyzer |

### C10. 報告 (report)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `report.top_n_features` | `30` | IC Reporter |
| `report.include_decay_analysis` | `true` | IC Reporter |
| `report.include_quantile_curves` | `true` | IC Reporter |
| `report.include_correlation_heatmap` | `true` | IC Reporter |
| `report.include_regime_analysis` | `true` | IC Reporter |
| `report.include_layer_analysis` | `true` | IC Reporter |
| `report.include_turnover_analysis` | `true` | IC Reporter |
| `report.ai_summary` | `true` | IC Reporter |

### C11. 效能設定 (performance)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `performance.max_features_for_correlation` | `200` | Stage 6 Redundancy Filter |
| `performance.parallel_ic_calculation` | `true` | Stage 4 IC Engine |
| `performance.n_jobs` | `-1` | 全域效能設定 |

### C12. 因子回報分析 (factor_return)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `factor_return.enabled` | `true` | Module 1 Factor Return Analyzer |
| `factor_return.num_quantiles` | `5` | Module 1 Factor Return Analyzer |
| `factor_return.calculate_risk_metrics` | `true` | Module 1 Factor Return Analyzer |
| `factor_return.risk_free_rate` | `0.0` | Module 1 Factor Return Analyzer |

### C13. 因子中心度分析 (factor_centrality)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `factor_centrality.enabled` | `true` | Module 2 Factor Centrality Analyzer |
| `factor_centrality.n_components` | `5` | Module 2 Factor Centrality Analyzer |
| `factor_centrality.rolling_window` | `60` | Module 2 Factor Centrality Analyzer |
| `factor_centrality.crowded_threshold` | `0.3` | Module 2 Factor Centrality Analyzer |
| `factor_centrality.min_samples_for_pca` | `30` | Module 2 Factor Centrality Analyzer |

### C14. 趨勢分析 (trend_analysis)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `trend_analysis.enabled` | `true` | Module 3 Trend Analyzer |
| `trend_analysis.min_samples` | `20` | Module 3 Trend Analyzer |
| `trend_analysis.significance_level` | `0.05` | Module 3 Trend Analyzer |
| `trend_analysis.r_squared_threshold` | `0.1` | Module 3 Trend Analyzer |
| `trend_analysis.dimensions` | `["ic", "centrality", "factor_return", "ls_spread"]` | Module 3 Trend Analyzer |

### C15. 參數敏感度分析 (parameter_sensitivity)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `parameter_sensitivity.enabled` | `true` | Module 4 Parameter Sensitivity Analyzer |
| `parameter_sensitivity.min_family_size` | `3` | Module 4 Parameter Sensitivity Analyzer |
| `parameter_sensitivity.ic_std_threshold_low` | `0.02` | Module 4 Parameter Sensitivity Analyzer |
| `parameter_sensitivity.ic_std_threshold_high` | `0.05` | Module 4 Parameter Sensitivity Analyzer |
| `parameter_sensitivity.auto_detect_families` | `true` | Module 4 Parameter Sensitivity Analyzer |

### C16. 滾動樣本外驗證 (rolling_oos)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `rolling_oos.enabled` | `true` | Module 5 Rolling OOS Validator |
| `rolling_oos.train_window` | `252` | Module 5 Rolling OOS Validator |
| `rolling_oos.test_window` | `63` | Module 5 Rolling OOS Validator |
| `rolling_oos.step` | `21` | Module 5 Rolling OOS Validator |
| `rolling_oos.min_splits` | `5` | Module 5 Rolling OOS Validator |
| `rolling_oos.assessment_thresholds.robust_hit_rate` | `0.7` | Module 5 Rolling OOS Validator |
| `rolling_oos.assessment_thresholds.robust_max_degradation` | `0.3` | Module 5 Rolling OOS Validator |
| `rolling_oos.assessment_thresholds.moderate_hit_rate` | `0.5` | Module 5 Rolling OOS Validator |
| `rolling_oos.assessment_thresholds.moderate_max_degradation` | `0.5` | Module 5 Rolling OOS Validator |

### C17. 因子正交化 (factor_orthogonalization)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `factor_orthogonalization.enabled` | `false` ⚠️ | Module 6 Factor Orthogonalizer |
| `factor_orthogonalization.method` | `"gram_schmidt"` | Module 6 Factor Orthogonalizer |

### C18. 因子曝險分析 (factor_exposure)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `factor_exposure.enabled` | `false` ⚠️ | Module 7 Factor Exposure Analyzer |
| `factor_exposure.max_single_exposure` | `0.4` | Module 7 Factor Exposure Analyzer |

### C19. 多空分析 (long_short_analysis)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `long_short_analysis.enabled` | `true` | Module 8 Long-Short Analyzer |
| `long_short_analysis.num_quantiles` | `5` | Module 8 Long-Short Analyzer |
| `long_short_analysis.long_quantiles` | `[4, 5]` | Module 8 Long-Short Analyzer |
| `long_short_analysis.short_quantiles` | `[1, 2]` | Module 8 Long-Short Analyzer |

### C20. 特徵品質診斷 (feature_quality_diagnostics)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `feature_quality_diagnostics.enabled` | `true` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.adf_significance` | `0.05` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.ljungbox_lags` | `10` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.ljungbox_significance` | `0.05` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.coverage_threshold` | `0.8` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.drift_window` | `60` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.drift_threshold` | `0.25` | Module 9 Feature Quality Diagnostics |
| `feature_quality_diagnostics.redundancy_threshold` | `0.85` | Module 9 Feature Quality Diagnostics |

### C21. 淨 IC 分析 (net_ic_analysis)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `net_ic_analysis.enabled` | `true` | Module 10 Net IC Analyzer |
| `net_ic_analysis.default_cost_bps` | `5` | Module 10 Net IC Analyzer |
| `net_ic_analysis.slippage_bps` | `2` | Module 10 Net IC Analyzer |
| `net_ic_analysis.cost_scenarios` | `[1, 3, 5, 10, 20]` | Module 10 Net IC Analyzer |
| `net_ic_analysis.participation_rate` | `0.01` | Module 10 Net IC Analyzer |

### C22. 功能層級管理 (feature_tiers)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `feature_tiers.active_preset` | `"intermediate"` | Feature Tier & Toggle |
| `feature_tiers.presets.foundation.deep_analysis` | `false` | Feature Tier — Foundation |
| `feature_tiers.presets.foundation.disabled_modules` | `[]` | Feature Tier — Foundation |
| `feature_tiers.presets.intermediate.deep_analysis` | `true` | Feature Tier — Intermediate |
| `feature_tiers.presets.intermediate.disabled_modules` | `[factor_orthogonalization, factor_exposure]` | Feature Tier — Intermediate |
| `feature_tiers.presets.advanced.deep_analysis` | `true` | Feature Tier — Advanced |
| `feature_tiers.presets.advanced.disabled_modules` | `[]` | Feature Tier — Advanced |
| `feature_tiers.custom_overrides.stage_overrides` | `{}` | Feature Tier — Custom |
| `feature_tiers.custom_overrides.module_overrides` | `{}` | Feature Tier — Custom |

### C23. 深度分析全域 (deep_analysis_global)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `deep_analysis_global.timeout_overrides` | `{}` | 深度分析全域設定 |
| `deep_analysis_global.regime_aware` | `false` ⚠️ | 深度分析全域設定 |

### C24. Shapley 分析 (shapley)

| 參數名稱 | 預設值 | 所在模組 |
|---------|-------|---------|
| `shapley.enabled` | `false` ⚠️ | Shapley 分析（P2 延遲） |
| `shapley.max_factors` | `20` | Shapley 分析 |
| `shapley.use_approximation` | `true` | Shapley 分析 |

---

## 索引 D：預設關閉功能清單

> 列出所有在 `config/ic_config.yaml` 中標記為 `enabled: false` 或邏輯上預設關閉的功能。

| # | 功能名稱 | 參數路徑 | 預設值 | 說明 |
|---|---------|---------|-------|------|
| 1 | **事件過濾器 (Event Filter)** | `event_filter.enabled` | `false` | 預設使用 Global Mode，不啟用事件過濾 |
| 2 | **Long-Short Spread 篩選門檻** | `thresholds.long_short_spread.enabled` | `false` | Long-Short Spread 不作為篩選門檻（但 Monotonicity 分析仍會計算） |
| 3 | **季度分組 IC (by_quarter)** | `ic_calculation.grouped_analysis.by_quarter` | `false` | 預設不做季度分組（加密貨幣季節效應不明顯） |
| 4 | **因子正交化 (Factor Orthogonalization)** | `factor_orthogonalization.enabled` | `false` | Module 6 預設關閉，需手動啟用（進階功能） |
| 5 | **因子曝險分析 (Factor Exposure)** | `factor_exposure.enabled` | `false` | Module 7 預設關閉，需手動啟用（進階功能） |
| 6 | **Shapley 分析 (Shapley Value)** | `shapley.enabled` | `false` | P2 延遲功能，未在當前版本完整實作 |
| 7 | **市場狀態感知 (Regime-Aware)** | `deep_analysis_global.regime_aware` | `false` | 深度分析的市場狀態感知功能預設關閉 |
| 8 | **時間語義模式 (Time Duration Mode)** | `global.time_duration_mode` | `false` | 預設使用 bar count 模式，不啟用時間語義 Horizon |
| 9 | **Foundation 預設中的深度分析** | `feature_tiers.presets.foundation.deep_analysis` | `false` | Foundation 層級不執行深度分析模組 |

**備註**：Intermediate 預設中，`factor_orthogonalization` 與 `factor_exposure` 也被列入 `disabled_modules`，即使深度分析整體啟用也不會執行這兩個模組。

---

## 索引 E：輸出格式全集

> 列出所有輸出類型，含對應的輸出欄位或圖表類型。

### E1. 檔案輸出

| # | 輸出名稱 | 格式 | 路徑模式 | 來源 |
|---|---------|------|---------|------|
| 1 | **精選特徵矩陣** | HDF5 | `data_cache/features/{symbol}_{tf}_filtered.h5` | SPEC §2.3 |
| 2 | **IC 分析報告** | JSON | `data_cache/reports/ic_report_{case_id}.json` | SPEC §2.3, §6 |
| 3 | **IC 摘要報告（AI 可讀）** | Markdown | `data_cache/reports/ic_summary_{case_id}.md` | SPEC §2.3 |
| 4 | **相關性矩陣** | JSON | `data_cache/reports/correlation_matrix_{case_id}.json` | SPEC §2.3 |
| 5 | **篩選日誌** | JSON | `data_cache/reports/ic_filter_log_{case_id}.json` | SPEC §2.3 |

### E2. 匯出格式（Multi-Format Export — 優化SPEC §18）

| # | 格式名稱 | 說明 | 來源 |
|---|---------|------|------|
| 6 | **CSV 摘要** (CSV Summary) | 14+12 欄位的單檔摘要 | 優化SPEC §18.3 |
| 7 | **CSV 詳細** (CSV Detailed) | 8 個模組各自匯出的 CSV 檔案 | 優化SPEC §18.3 |
| 8 | **AI 可讀 JSON** (_ai.json) | 含 interpretation_guide / key_findings / risk_warnings / recommendations / top_features / filter_funnel / module_summaries | 優化SPEC §18.4 |
| 9 | **增強版 Markdown** | Emoji 章節格式的完整分析報告 | 優化SPEC §18.5 |
| 10 | **HDF5** | 精選特徵矩陣 | 優化SPEC §18.2 |
| 11 | **PNG** | 圖表匯出 | 優化SPEC §18.2 |

### E3. JSON 報告結構 — ic_report.json 主要欄位（SPEC §6）

| 欄位路徑 | 說明 |
|---------|------|
| `summary.total_features` | 輸入特徵總數 |
| `summary.filtered_features` | 篩選後特徵數 |
| `summary.filtering_ratio` | 篩選比例 |
| `summary.mode` | global / event |
| `summary.sample_size_tier` | sufficient / marginal / low_confidence |
| `ic_results[]` | 每個特徵的 IC 分析結果陣列 |
| `ic_results[].feature_name` | 特徵名稱 |
| `ic_results[].ic_mean` | IC 平均值 |
| `ic_results[].ic_std` | IC 標準差 |
| `ic_results[].icir` | ICIR 值 |
| `ic_results[].p_value` | p 值 |
| `ic_results[].t_stat` | t 統計量 |
| `ic_results[].hit_rate` | IC 正報率 |
| `ic_results[].monotonicity_score` | 單調性分數 |
| `ic_results[].coverage` | 覆蓋率 |
| `ic_results[].rolling_ic` | Rolling IC 時間序列 |
| `ic_results[].ic_decay` | IC Decay 各 Horizon 值 |
| `ic_results[].ic_half_life` | IC 半衰期 |
| `ic_results[].grouped_ic` | 各分組的 IC 結果 |
| `ic_results[].quantile_returns` | 分位數收益 |
| `ic_results[].long_short_spread` | 多空利差 |
| `ic_results[].turnover` | 換手率指標 |
| `filter_log` | 每階段篩選的特徵數變化 |
| `correlation_matrix` | 精選特徵的相關性矩陣 |
| `deep_analysis` | 深度分析結果（優化SPEC §6.3） |
| `deep_analysis_errors` | 深度分析錯誤（SkippedResult 列表） |

### E4. 基礎圖表 (C1~C12)（SPEC §6）

| 圖表代號 | 名稱 | X 軸 | Y 軸 | 備註 |
|---------|------|------|------|------|
| C1 | IC Heatmap | 特徵 | Horizon | 色彩 = IC 值 |
| C2 | IC Distribution | IC 值 | 頻率 | 直方圖 |
| C3 | Rolling IC Chart | 時間 | IC 值 | 多視窗線圖 |
| C4 | IC Decay Chart | Horizon | IC 值 | 衰減曲線 |
| C5 | Monotonicity Chart | 分位數 | 累積收益 | 分位數收益曲線 |
| C6 | Correlation Heatmap | 特徵 | 特徵 | 色彩 = 相關係數 |
| C7 | Filter Funnel Chart | 階段 | 特徵數 | 漏斗圖 |
| C8 | Coverage Chart | 特徵 | 覆蓋率 | 橫條圖 |
| C9 | Turnover Chart | 時間 | 換手率 | 時間序列 |
| C10 | Regime IC Comparison | Regime | IC 值 | 分組柱狀圖 |
| C11 | Top Features Table | — | — | 表格 |
| C12 | IC Summary Dashboard | — | — | 儀表板卡片組 |

### E5. 深度分析圖表 (C13~C22)（優化SPEC §8.4）

| 圖表代號 | 名稱 | X 軸 | Y 軸 | 備註 |
|---------|------|------|------|------|
| C13 | Factor Return Chart | 時間 | 累積收益 | 各分位數曲線 |
| C14 | Factor Centrality Chart | 時間 | 中心度 | 滾動中心度趨勢 |
| C15 | PCA Explained Chart | 主成分編號 | 解釋方差比 | 累積 + 個別 |
| C16 | Trend Dashboard | 維度 | 綜合判斷 | 正常/警告/危險 |
| C17 | Parameter Sensitivity Heatmap | 特徵族群 | IC 值 | 族群內 IC 分佈 |
| C18 | OOS Distribution Chart | IS/OOS | IC 值 | 箱線圖 + KDE |
| C19 | Long-Short Comparison Chart | 特徵 | Long IC / Short IC | 正負不對稱 |
| C20 | Factor Exposure Radar | 因子 | 曝險 | 雷達圖 |
| C21 | Feature Quality Dashboard | 特徵 | 品質分數 | 多指標面板 |
| C22 | Net IC Chart | 成本情境 | Net IC | 成本敏感度曲線 |

### E6. Feature Browser 圖表（優化SPEC §19）

| 圖表名稱 | 類型 | 說明 |
|---------|------|------|
| Dashboard 摘要卡片 (×6) | 卡片 | 特徵總數、覆蓋率、品質分佈等 |
| Catalog Table | 表格 | 10 欄位特徵目錄 |
| Distribution Histogram | 直方圖 | 特徵值分佈 |
| Distribution Box Plot | 箱線圖 | 特徵值五數概要 |
| Time Series + ACF | 折線圖 + 柱狀圖 | 時間序列 + 自相關 |
| Correlation Heatmap | 熱力圖 | 特徵相關性 |
| Scatter Plot | 散佈圖 | 兩特徵關係 |
| Dendrogram | 樹狀圖 | 階層聚類 |
| Coverage Heatmap | 熱力圖 | 覆蓋率 |
| Data Table | 虛擬分頁表格 | 原始數據 |

### E7. WebSocket 進度事件

| 事件欄位 | 說明 |
|---------|------|
| `task_id` | 任務 ID |
| `status` | pending / running / completed / failed |
| `progress` | 0.0 ~ 1.0 進度比例 |
| `current_stage` | 當前執行階段名稱 |
| `error` | 錯誤訊息（失敗時） |

---

## 索引 F：程式碼位置索引

> **嚴格規則**：僅列出在參考文件中逐字出現的檔案路徑，不推測或補全。

### F1. 核心引擎檔案 (`momentum/Analysis/`)

| 功能名稱 | 檔案路徑 | 主要類別/函式 | 來源章節 |
|---------|---------|-------------|---------|
| IC 篩選協調器 | `momentum/Analysis/ic_filter_orchestrator.py` | `ICFilterOrchestrator` | SPEC §8; PLAN Task 2.2.6 |
| 數據預處理器 | `momentum/Analysis/data_preprocessor.py` | `DataPreprocessor` | SPEC §8; PLAN Task 2.1.2 |
| 事件過濾器 | `momentum/Analysis/event_filter.py` | `EventFilter`, `IEventFilter` | SPEC §8; PLAN Task 2.2.1 |
| IC 核心引擎 | `momentum/Analysis/ic_engine.py` | `ICEngine` | SPEC §8; PLAN Task 2.1.4 |
| 統計驗證器 | `momentum/Analysis/statistical_validator.py` | `StatisticalValidator` | SPEC §8; PLAN Task 2.1.5 |
| 單調性測試器 | `momentum/Analysis/monotonicity_tester.py` | `MonotonicityTester` | SPEC §8; PLAN Task 2.2.2 |
| 冗餘過濾器 | `momentum/Analysis/redundancy_filter.py` | `RedundancyFilter`, `IRedundancyFilter` | SPEC §8; PLAN Task 2.2.3 |
| 換手率分析器 | `momentum/Analysis/turnover_analyzer.py` | `TurnoverAnalyzer` | SPEC §8; PLAN Task 2.2.4 |
| 覆蓋率分析器 | `momentum/Analysis/coverage_analyzer.py` | `CoverageAnalyzer` | SPEC §8; PLAN Task 2.2.5 |
| IC 報告器 | `momentum/Analysis/ic_reporter.py` | `ICReporter` | SPEC §8; PLAN Task 2.2.7 |
| IC Config Schema | `momentum/Analysis/ic_config_schema.py` | Pydantic Config Models | SPEC §8; PLAN Task 2.1.1 |

### F2. 深度分析模組檔案 (`momentum/Analysis/`)

| 功能名稱 | 檔案路徑 | 主要類別 | 來源章節 |
|---------|---------|---------|---------|
| 因子回報分析器 | `momentum/Analysis/factor_return_analyzer.py` | `FactorReturnAnalyzer` | 優化SPEC §3.1 |
| 因子中心度分析器 | `momentum/Analysis/factor_centrality_analyzer.py` | `FactorCentralityAnalyzer` | 優化SPEC §3.2 |
| 趨勢分析器 | `momentum/Analysis/trend_analyzer.py` | `TrendAnalyzer` | 優化SPEC §3.3 |
| 參數敏感度分析器 | `momentum/Analysis/parameter_sensitivity_analyzer.py` | `ParameterSensitivityAnalyzer` | 優化SPEC §3.4 |
| 滾動 OOS 驗證器 | `momentum/Analysis/rolling_oos_validator.py` | `RollingOOSValidator` | 優化SPEC §3.5 |
| 因子正交化器 | `momentum/Analysis/factor_orthogonalizer.py` | `FactorOrthogonalizer` | 優化SPEC §4.1 |
| 因子曝險分析器 | `momentum/Analysis/factor_exposure_analyzer.py` | `FactorExposureAnalyzer` | 優化SPEC §4.2 |
| 多空分析器 | `momentum/Analysis/long_short_analyzer.py` | `LongShortAnalyzer` | 優化SPEC §4.3 |
| 特徵品質診斷 | `momentum/Analysis/feature_quality_diagnostics.py` | `FeatureQualityDiagnostics` | 優化SPEC §4.4 |
| 淨 IC 分析器 | `momentum/Analysis/net_ic_analyzer.py` | `NetICAnalyzer` | 優化SPEC §4.5 |
| 深度分析工具函式 | `momentum/Analysis/utils.py` | 共用工具函式 | 優化SPEC §3.5 (TF 調整邏輯) |

### F3. 模型驗證檔案 (`momentum/Analysis/model_validation/`)

| 功能名稱 | 檔案路徑 | 主要類別 | 來源章節 |
|---------|---------|---------|---------|
| 模型驗證匯出 | `momentum/Analysis/model_validation/__init__.py` | 匯出清單 | PLAN Changelog V4 #6 |
| CV 驗證器 | `momentum/Analysis/model_validation/cv_validator.py` | `CVValidator` | SPEC §8; PLAN Task 2.3.1 |
| OOT 驗證器 | `momentum/Analysis/model_validation/oot_validator.py` | `OOTValidator` | SPEC §8; PLAN Task 2.3.2 |
| PSI 計算器 | `momentum/Analysis/model_validation/psi_calculator.py` | `PSICalculator` | SPEC §8; PLAN Task 2.3.3 |
| 滾動 AUC 追蹤器 | `momentum/Analysis/model_validation/rolling_auc.py` | `RollingAUCTracker` | SPEC §8; PLAN Task 2.3.4 |
| 單案例 SHAP 解釋器 | `momentum/Analysis/model_validation/case_shap.py` | `CaseSHAPExplainer` | SPEC §8; PLAN Task 2.3.4 |

### F4. 架構基礎設施

| 功能名稱 | 檔案路徑 | 主要類別/函式 | 來源章節 |
|---------|---------|-------------|---------|
| 跨 Domain Protocol | `momentum/core/protocols.py` | `IICAnalyzer`, `ILabelGenerator`, `ICVValidator` | SPEC §10.1; PLAN Task 2.1.6 |
| 內部 DTO | `momentum/core/contracts.py` | `ICResult`, `FilteredFeatureSet` | PLAN Task 2.1.6 |
| 例外類別 | `momentum/core/exceptions.py` | `InsufficientDataError`, `InvalidQueryError`, `InvalidInputError` | PLAN Changelog V4 #3 |
| Factory 函式 | `momentum/factories.py` | `create_ic_analyzer()`, `create_label_generator()`, `create_cv_validator()`, `create_psi_calculator()`, 及 10 個深度分析 Factory | SPEC §10.2; 優化SPEC §6.4 |
| Analysis 匯出清單 | `momentum/Analysis/__init__.py` | 模組匯出 | PLAN Changelog V4 #6 |

### F5. 標籤生成器

| 功能名稱 | 檔案路徑 | 主要類別 | 來源章節 |
|---------|---------|---------|---------|
| 標籤生成器 (擴展) | `momentum/FeatureEngineering/labels/label_generator.py` | `LabelGenerator` (擴展) | SPEC §8; PLAN Task 2.1.3 |

### F6. API 層

| 功能名稱 | 檔案路徑 | 主要類別/函式 | 來源章節 |
|---------|---------|-------------|---------|
| IC 分析路由 | `api/routes/ic_analysis.py` | REST 端點 | SPEC §8; PLAN Task 2.4.1; 優化SPEC §7 |
| IC 分析 Service | `api/services/ic_analysis_service.py` | `ICAnalysisService` | SPEC §8; PLAN Task 2.4.1 |
| IC Models | `api/models/ic_models.py` | `ICAnalyzeRequest`, `ICAnalyzeResponse`, `ICTaskStatusResponse` 等 | SPEC §8; PLAN Task 2.4.1; 優化SPEC §7 |
| IC 分析 WebSocket | `api/websocket/ic_analysis_ws.py` | WebSocket 進度推送 | SPEC §8; PLAN Task 2.4.1 |
| Feature Browser 路由 | `api/routes/feature_browser.py` | Feature Browser REST 端點 | 優化SPEC §19.10 |
| Feature Browser Models | `api/models/feature_browser_models.py` | Feature Browser Pydantic Models | 優化SPEC §19.11 |
| Feature Browser Service | `api/services/feature_browser_service.py` | Feature Browser 服務 | 優化SPEC §19.10 |

### F7. 前端

| 功能名稱 | 檔案路徑 | 來源章節 |
|---------|---------|---------|
| IC 分析頁面 | 路徑未在文件中以完整檔案路徑明確標注（SPEC §6 描述前端圖表但未列完整前端檔案路徑，優化SPEC §8.7 描述頁面佈局但使用 URL 路徑）|
| Feature Browser 頁面 | 路徑未在文件中以完整檔案路徑明確標注（優化SPEC §19.2 描述頁面佈局但使用 URL 路徑 `/feature-browser`） |

**說明**：前端元件路徑（如 `frontend/src/components/ic-analysis/*.tsx`）在參考文件中以概述方式提及（如優化SPEC §9 描述 `ic-analysis/` 目錄），但未逐一列出完整的 `.tsx` 檔案路徑。以下為文件中以目錄形式提及的前端路徑：

- `frontend/src/store/icAnalysisStore.ts`（優化SPEC §8.6 描述 Store 結構）
- `frontend/src/store/featureBrowserStore.ts`（優化SPEC §19.13 描述 Store 結構）

### F8. 設定檔

| 功能名稱 | 檔案路徑 | 來源章節 |
|---------|---------|---------|
| IC 組態 | `config/ic_config.yaml` | SPEC §5.1; SPEC §2.3 |

### F9. 測試檔案（以 PLAN 文件「驗證檢查點」為準）

| 功能名稱 | 測試檔案路徑 | 驗證命令 | 來源章節 |
|---------|-------------|---------|---------|
| IC Config | `tests/momentum/test_ic_config.py` | `pytest tests/momentum/test_ic_config.py -v --tb=short` | PLAN Task 2.1.1 |
| Data Preprocessor | `tests/momentum/test_data_preprocessor.py` | `pytest tests/momentum/test_data_preprocessor.py -v --tb=short` | PLAN Task 2.1.2 |
| Label Generator Extended | `tests/momentum/test_label_generator_extended.py` | `pytest tests/momentum/test_label_generator_extended.py -v --tb=short` | PLAN Task 2.1.3 |
| IC Engine | `tests/momentum/test_ic_engine.py` | `pytest tests/momentum/test_ic_engine.py -v --tb=short` | PLAN Task 2.1.4 |
| Statistical Validator | `tests/momentum/test_statistical_validator.py` | `pytest tests/momentum/test_statistical_validator.py -v --tb=short` | PLAN Task 2.1.5 |
| Event Filter | `tests/momentum/test_event_filter.py` | `pytest tests/momentum/test_event_filter.py -v --tb=short` | PLAN Task 2.2.1 |
| Monotonicity Tester | `tests/momentum/test_monotonicity_tester.py` | `pytest tests/momentum/test_monotonicity_tester.py -v --tb=short` | PLAN Task 2.2.2 |
| Redundancy Filter | `tests/momentum/test_redundancy_filter.py` | `pytest tests/momentum/test_redundancy_filter.py -v --tb=short` | PLAN Task 2.2.3 |
| Turnover Analyzer | `tests/momentum/test_turnover_analyzer.py` | `pytest tests/momentum/test_turnover_analyzer.py -v --tb=short` | PLAN Task 2.2.4 |
| Coverage Analyzer | `tests/momentum/test_coverage_analyzer.py` | `pytest tests/momentum/test_coverage_analyzer.py -v --tb=short` | PLAN Task 2.2.5 |
| IC Filter Orchestrator | `tests/momentum/test_ic_filter_orchestrator.py` | `pytest tests/momentum/test_ic_filter_orchestrator.py -v --tb=short` | PLAN Task 2.2.6 |
| IC Reporter | `tests/momentum/test_ic_reporter.py` | `pytest tests/momentum/test_ic_reporter.py -v --tb=short` | PLAN Task 2.2.7 |
| CV Validator | `tests/momentum/test_cv_validator.py` | `pytest tests/momentum/test_cv_validator.py -v --tb=short` | PLAN Task 2.3.1 |
| OOT Validator | `tests/momentum/test_oot_validator.py` | `pytest tests/momentum/test_oot_validator.py -v --tb=short` | PLAN Task 2.3.2 |
| PSI Calculator | `tests/momentum/test_psi_calculator.py` | `pytest tests/momentum/test_psi_calculator.py -v --tb=short` | PLAN Task 2.3.3 |
| Rolling AUC | `tests/momentum/test_rolling_auc.py` | `pytest tests/momentum/test_rolling_auc.py tests/momentum/test_case_shap.py -v --tb=short` | PLAN Task 2.3.4 |
| Case SHAP | `tests/momentum/test_case_shap.py` | （同上） | PLAN Task 2.3.4 |

### F10. 深度分析測試檔案（以優化SPEC §9、優化PLAN 為準）

| 功能名稱 | 測試檔案路徑 | 來源章節 |
|---------|-------------|---------|
| Factor Return Analyzer | `tests/momentum/analysis/test_factor_return_analyzer.py` | 優化SPEC §9 |
| Factor Centrality Analyzer | `tests/momentum/analysis/test_factor_centrality_analyzer.py` | 優化SPEC §9 |
| Trend Analyzer | `tests/momentum/analysis/test_trend_analyzer.py` | 優化SPEC §9 |
| Parameter Sensitivity Analyzer | `tests/momentum/analysis/test_parameter_sensitivity_analyzer.py` | 優化SPEC §9 |
| Rolling OOS Validator | `tests/momentum/analysis/test_rolling_oos_validator.py` | 優化SPEC §9 |
| Factor Orthogonalizer | `tests/momentum/analysis/test_factor_orthogonalizer.py` | 優化SPEC §9 |
| Factor Exposure Analyzer | `tests/momentum/analysis/test_factor_exposure_analyzer.py` | 優化SPEC §9 |
| Long-Short Analyzer | `tests/momentum/analysis/test_long_short_analyzer.py` | 優化SPEC §9 |
| Feature Quality Diagnostics | `tests/momentum/analysis/test_feature_quality_diagnostics.py` | 優化SPEC §9 |
| Net IC Analyzer | `tests/momentum/analysis/test_net_ic_analyzer.py` | 優化SPEC §9 |
| Deep Analysis Integration | `tests/momentum/analysis/test_deep_analysis_integration.py` | 優化SPEC §9 |
| IC Deep Analysis API | `tests/api/test_ic_deep_analysis.py` | 優化SPEC §9 |
| Feature Browser API | `tests/api/test_feature_browser.py` | 優化SPEC §19.16 |

---

## 步驟二：自我審查報告

### 審查一覽

| 審查項目 | 結果 | 說明 |
|---------|------|------|
| 索引 A 覆蓋率 | ✅ 通過 | SPEC §1-§17 所有獨立章節均已涵蓋；優化SPEC §3-§4 十大模組全數列出；§17-§19 三大系統均已涵蓋 |
| 索引 B 完整性 | ✅ 通過 | 163 個術語，涵蓋所有文件中出現的指標、演算法、統計方法名稱 |
| 索引 C 與 YAML 一致性 | ✅ 通過 | 所有參數預設值均以 `config/ic_config.yaml` 實際值為準，不使用文件範例值 |
| 索引 D 完整性 | ✅ 通過 | 9 項預設關閉功能，涵蓋所有 `enabled: false` 及邏輯上預設關閉的功能 |
| 索引 E 覆蓋率 | ✅ 通過 | 涵蓋檔案輸出、匯出格式、JSON 報告結構、C1-C22 圖表、Feature Browser 圖表、WebSocket 事件 |
| 索引 F 嚴謹性 | ✅ 通過 | 所有路徑均為文件中逐字出現，前端元件路徑因文件僅以目錄方式提及而標注說明 |
| 索引間交叉驗證 | ✅ 通過 | 索引 A 每個模組在 C 中有對應參數、在 E 中有對應輸出、在 F 中有對應檔案 |
| 預設值差異標注 | ✅ 通過 | YAML 實際值與 SPEC 文件範例值不同處已以 YAML 為準（如 `rolling_window=60`、`coverage_threshold=0.8`、`cost_scenarios=[1,3,5,10,20]`、`drift_window=60`、`redundancy_threshold=0.85`、`shapley.max_factors=20`） |

### 審查細節

**索引 A 交叉驗證**：
- ✅ A1 八階段流水線的每個 Stage 都列出子項目
- ✅ A2 模型驗證 5 個子模組完整
- ✅ A3 十大深度分析模組完整（Module 1-10）
- ✅ A4-A6 三大擴展系統完整
- ✅ A7-A9 配置/API/前端均已列出
- ✅ A10-A11 MCP Tool 及架構基礎設施已列出

**索引 C 預設值驗證**（以下值以 YAML 為準，與某些文件範例值不同）：
- `factor_centrality.rolling_window` = `60`（非 SPEC 範例的 63）
- `feature_quality_diagnostics.coverage_threshold` = `0.8`（非某些文件範例的 0.7）
- `feature_quality_diagnostics.drift_window` = `60`（非某些文件範例的 63）
- `feature_quality_diagnostics.redundancy_threshold` = `0.85`（非某些文件範例的 0.95）
- `net_ic_analysis.cost_scenarios` = `[1, 3, 5, 10, 20]`（非某些文件範例的 [2, 5, 10, 20]）
- `shapley.max_factors` = `20`（非某些文件範例的 10）

**索引 D 交叉驗證**：
- ✅ 每項關閉功能在索引 C 中有對應參數行（標記 ⚠️）
- ✅ `by_quarter=false` 雖非 enabled 欄位但邏輯上為預設關閉的分析維度

**索引 F 嚴謹性檢查**：
- ✅ 所有 `momentum/Analysis/*.py` 路徑來自 SPEC §8 / 優化SPEC §3-§4
- ✅ 所有 `tests/momentum/test_*.py` 路徑來自 PLAN 驗證檢查點
- ✅ 所有 `tests/momentum/analysis/test_*.py` 路徑來自優化SPEC §9
- ✅ 前端具體元件路徑因文件未逐一列出而標注「路徑未在文件中明確標注」
- ✅ API 層路徑來自 SPEC §8 與 PLAN Task 2.4.1

### 凍結聲明

六份索引經自我審查，確認：
1. **完整性**：所有功能模組、術語、參數、預設關閉功能、輸出格式、程式碼位置均已收錄
2. **準確性**：預設值以 `config/ic_config.yaml` 實際值為最終權威來源
3. **一致性**：索引間相互交叉驗證，無遺漏或矛盾
4. **嚴謹性**：索引 F 僅列出文件中逐字出現的路徑

**狀態：Frozen ✅**

---

> **後續步驟**：索引已凍結，待使用者指示後再繼續步驟三至十二的手冊正文撰寫。

---

---

# IC Gatekeeper 使用者手冊 — 正文

> **版本**: V1.0  
> **建立日期**: 2026-02-21  
> **狀態**: 步驟三＆四（第一章）已完成  
> **適用讀者**: 量化交易研究新手，不需要任何金融或統計背景

---

# 第一章：模組總覽

---

## 1.1 這個模組解決什麼問題

Feature Factory（特徵工廠）在上一個步驟中，像一條全自動生產線，幫你從原始 K 線數據裡製造出數百甚至上千個「候選因子」（候選訊號）。但問題來了：**大多數因子其實是雜訊，根本沒有任何預測能力**——就算某個因子在歷史數據中看起來有效，也可能純粹是統計上的偶然巧合。如果你把所有候選因子都丟進機器學習模型訓練，模型只會記住這些假訊號，在真實市場中一敗塗地，這種現象叫做**過擬合（Overfitting）**。

**IC Gatekeeper（IC 篩選器）** 就是解決這個問題的模組。它用一套嚴格的、多達八個階段的統計測試流水線，逐一審核每個候選因子，測量它對「未來價格方向」的真實預測能力，不放過任何偽裝成訊號的雜訊，最後只留下通過所有關卡的真正有效因子，交給下游的機器學習模型使用。

**簡單來說：Feature Factory 是「大量生產候選訊號」的工廠，IC Gatekeeper 是「嚴格把關品質」的品管部門，兩者缺一不可。**

---

## 1.2 在整體研究流程中的位置

IC Gatekeeper 是整個量化研究流水線的**第二站**，承上啟下，連結特徵生成與機器學習模型：

```
 ┌─────────────────────────────────────────────────────────────────────────┐
 │                       量化研究完整流程                                    │
 │                                                                         │
 │  原始 K 線數據（HDF5）                                                   │
 │       │                                                                 │
 │       ▼                                                                 │
 │  Phase 1：Feature Factory（特徵工廠）                                    │
 │  │   將原始價格/量能/衍生品數據 → 加工為數百～數千個「候選因子」               │
 │  │   輸出：features.h5（特徵矩陣）、meta.json（特徵元資料）                 │
 │  │                                                                      │
 │  ▼                                                                      │
 │  ★ Phase 2：IC Gatekeeper（IC 篩選器 — 本模組）                          │
 │  │   八階段流水線逐一審核每個候選因子的真實預測能力                           │
 │  │       → 計算 IC（資訊係數）                                            │
 │  │       → 統計顯著性驗證（t 統計量、p 值）                                │
 │  │       → 單調性測試（因子排名是否與報酬方向一致？）                        │
 │  │       → 冗餘去除（保留多元化的因子組合）                                 │
 │  │   輸出：篩選後精選特徵矩陣、IC 分析報告、AI 可讀摘要                      │
 │  │                                                                      │
 │  ▼                                                                      │
 │  Phase 3：ML 模型訓練（XGBoost / LightGBM）                              │
 │  │   僅使用通過 IC Gatekeeper 篩選的高品質因子訓練模型                      │
 │  │   讓模型學習因子之間的非線性組合效果                                     │
 │  │                                                                      │
 │  ▼                                                                      │
 │  Phase 4：策略回測與優化（Optuna）                                        │
 │      用模型預測結果執行歷史回測，優化進出場參數                              │
 └─────────────────────────────────────────────────────────────────────────┘
```

- **前一步來自**：Feature Factory（Phase 1）— 輸出特徵矩陣（`features.h5`）、特徵詮釋資料（`meta.json`）、以及標籤矩陣（`labels.h5`），還有原始 K 線數據（`{symbol}_{tf}.h5`）和 IC 設定檔（`ic_config.yaml`）
- **本模組做什麼**：讀取所有輸入 → 經過八個階段的流水線逐一評估因子 → 計算每個因子對未來報酬的真實預測力（IC）→ 篩除低品質、統計不顯著、與其他因子高度重疊的候選因子 → 輸出精選因子清單、完整分析報告、以及（可選）十大深度分析的診斷結果
- **輸出給誰使用**：ML 模型訓練模組（Phase 3，XGBoost / LightGBM）— 使用篩選後的精選特徵矩陣作為訓練輸入，確保模型學到的是真實訊號而非雜訊

---

## 1.3 日常生活比喻

> 想像你是一家頂尖職業籃球隊的總教練，正在為下一個球季招募新球員。
>
> **第一步（Feature Factory）**：你的球探遍訪全國各地的業餘聯賽，拍攝了 1000 位球員的影片，每人都有「速度」「彈跳力」「三分命中率」「傳球能力」等幾十項指標數據——這就是候選因子清單。
>
> **第二步（IC Gatekeeper）**：你可不能把 1000 個人都帶進訓練營，所以你設計了一套嚴格的、八輪淘汰制試訓：
>
> - **第一輪（數據預處理）**：清除明顯存在問題的數據——那個三分命中率「150%」的球員，數據顯然有誤，先修正或剔除。
> - **第二輪（標籤生成）**：確認你要選的是「能幫球隊得分的球員」還是「能防守的球員」——明確你的篩選目標（預測 Horizon）。
> - **第三輪（事件過濾）**：選擇只在特定情境（如季後賽壓力場面）下測試，聚焦你真正關心的市場狀態。
> - **第四輪（IC 計算）**：讓每位球員和 NBA 球星一起訓練，測量他「真實幫助球隊贏球的相關性」（Information Coefficient）——去除 20 分鐘試訓的運氣成分，用 63 場比賽的滾動數據說話。
> - **第五輪（統計驗證）**：確認這個球員的優秀表現不是偶然——他的勝場貢獻率必須通過 t 統計量與 p 值的統計顯著性檢驗。
> - **第六輪（單調性測試）**：最出色的球員表現應該是「排名越前面，幫助球隊贏球越多」，排名一致性不佳的球員即使總體數字好看也要懷疑。
> - **第七輪（冗餘過濾）**：如果你已經有一位全能前鋒，就不需要兩位風格技術完全相同的前鋒——剔除功能高度重疊的球員，確保球隊多元化。
> - **第八輪（報告生成）**：把最終入選的 15 位球員的完整分析報告整理出來，交給後勤部門準備簽約（輸出給 ML 模型訓練）。
>
> 最後，1000 位候選人中也許只有 50-100 位通過了全部試驗。這種嚴格篩選，正是讓你的球隊在正式賽季中表現穩定的關鍵——這就是 IC Gatekeeper 的核心價值。

---

## 1.4 本模組包含哪些子模組

以下清單直接對應 **Frozen 索引 A** 的 11 個主要功能區塊，依核心功能順序排列：

---

### 🔵 核心主流水線（A1）

**A1. 八階段流水線（8-Stage Pipeline）**

IC Gatekeeper 的核心骨幹，每次執行 IC 分析都必定完整經過以下八個階段：

| 編號 | 階段 | 一句話說明 |
|:----:|------|-----------|
| A1-1 | **Stage 0：數據載入（Data Ingestion）** | 讀取 Phase 1 輸出的特徵矩陣、標籤矩陣、原始 K 線與 IC 設定檔，並做輸入完整性驗證 |
| A1-2 | **Stage 1：數據預處理器（Data Preprocessor）** | 截斷極端值（Winsorization）、填補缺失值、對因子做標準化，讓後續統計計算不受「異常大數字」干擾 |
| A1-3 | **Stage 2：標籤生成器（Label Generator）** | 根據設定的「預測窗口」（Horizon），計算未來 N 根 K 線的收益率，作為衡量因子預測力的答案標準 |
| A1-4 | **Stage 3：事件過濾器（Event Filter）** | ⚠️ 預設關閉。可用自訂條件（如「僅在熊市中」）過濾分析樣本，專注特定市場狀態下的因子品質 |
| A1-5 | **Stage 4：IC 核心計算引擎（IC Engine）** | 計算每個因子與未來收益率的預測相關性（IC）、Rolling IC 時間序列、IC Decay 衰減曲線、分組 IC 分析 |
| A1-6 | **Stage 5：統計驗證 + 單調性測試** | 確認 IC 值是真正統計顯著（t 統計量、p 值、FDR 校正），並檢驗分位數排名的單調性（高排名因子是否對應高報酬？） |
| A1-7 | **Stage 6：冗餘過濾器（Redundancy Filter）** | 計算所有通過篩選因子之間的相關性，用貪婪去重演算法剔除功能高度重疊的因子，確保最終因子組合多元化 |
| A1-8 | **Stage 7：報告生成（換手率 + 覆蓋率 + IC Reporter）** | 計算因子換手率（評估交易成本壓力）、覆蓋率（因子是否長期穩定存在），並生成完整的 JSON、Markdown 與 AI 可讀摘要報告 |
| A1-9 | **流水線協調器（IC Filter Orchestrator）** | 統一編排上述八個階段的執行順序，管理快取策略（支援不重算 IC 的快速重新篩選），支援全域模式與事件模式 |

---

### 🟠 模型驗證子系統（A2）

**A2. 模型驗證（Model Validation Part B）**

在因子分析完成後，對整個機器學習模型（而非單一因子）進行穩健性評估：

| 編號 | 子模組 | 一句話說明 |
|:----:|--------|-----------|
| A2-1 | **CV 驗證器（CV Validator）** | 用時間序列交叉驗證評估模型的泛化能力（避免未來數據洩漏） |
| A2-2 | **OOT 驗證器（OOT Validator）** | 在完全未見過的「樣本外時間段」上測試模型，計算樣本內外的 AUC 差距來偵測過擬合 |
| A2-3 | **PSI 計算器（PSI Calculator）** | 偵測特徵的統計分佈是否隨時間發生漂移（訓練期與上線後的分佈不同則模型預測力會衰退） |
| A2-4 | **滾動 AUC 追蹤器（Rolling AUC Tracker）** | 監控模型在滾動時間窗口上的 AUC 走勢，判斷預測能力是否持續衰退 |
| A2-5 | **單案例 SHAP 解釋器（Case SHAP Explainer）** | 解釋「為什麼模型對這個特定 K 線的預測是上漲？」——用 SHAP 值列出哪些因子貢獻了多少 |

---

### 🟡 十大深度分析模組（A3）

**A3. 十大深度分析模組（10 Deep Analysis Modules）**

針對通過基礎篩選的因子，進行進階的多維度診斷分析。每個模組可獨立啟用：

| 編號 | 模組 | 層級 | 一句話說明 |
|:----:|------|:----:|-----------|
| A3-1 | **因子回報分析器（Factor Return Analyzer）** | 🟡 | 把因子分成高中低分組，計算各組的累積收益、Sharpe、最大回撤等，確認「排名越高真的賺越多」 |
| A3-2 | **因子中心度分析器（Factor Centrality Analyzer）** | 🟡 | 用主成分分析（PCA）偵測哪些因子「跟大家都很相似」，避免選到被市場過度擁擠的因子 |
| A3-3 | **趨勢分析器（Trend Analyzer）** | 🟡 | 偵測 Rolling IC、中心度、因子回報的長期趨勢，發出正常 / 警告 / 危險三級信號 |
| A3-4 | **參數敏感度分析器（Parameter Sensitivity Analyzer）** | 🟡 | 同一指標不同參數的 IC 值差異很大嗎？過大代表過擬合風險高，結果不穩健 |
| A3-5 | **滾動樣本外驗證器（Rolling OOS Validator）** | 🟡 | Walk-Forward 方式不斷推進時間窗口，比較訓練期 vs 預測期的 IC，評估因子是否真的可以在未來持續有效 |
| A3-6 | **因子正交化器（Factor Orthogonalizer）** | 🔴 ⚠️ 預設關閉 | 用數學方法去除因子之間的相關性影響，讓每個因子貢獻的預測力「相互獨立」 |
| A3-7 | **因子曝險分析器（Factor Exposure Analyzer）** | 🔴 ⚠️ 預設關閉 | 分析你選到的因子對哪些市場系統性風險有曝險（如過度集中在高波動因子） |
| A3-8 | **多空分析器（Long-Short Analyzer）** | 🟡 | 分別計算「做多信號好不好」和「做空信號好不好」，若兩者不對稱則提醒你這個因子只適合單邊策略 |
| A3-9 | **特徵品質診斷（Feature Quality Diagnostics）** | 🟡 | 一次性執行定態性（ADF）、自相關（Ljung-Box）、概念漂移（CUSUM）等多項品質檢查 |
| A3-10 | **淨 IC 分析器（Net IC Analyzer）** | 🟡 | 把交易成本與換手率扣掉後，計算「實際上手有多少 IC 剩下」——一個換手率很高的因子，扣掉手續費後可能毫無利潤 |

---

### 🟢 系統支援子系統（A4 ~ A11）

| 編號 | 子系統 | 一句話說明 |
|:----:|--------|-----------|
| A4 | **功能層級與開關管理系統（Feature Tier & Toggle）** | 提供 Foundation / Intermediate / Advanced 三種預設組合，讓新手可以一鍵選擇適合自己的分析深度 |
| A5 | **多格式匯出系統（Multi-Format Export）** | 把分析結果匯出為 CSV、AI 可讀 JSON、增強版 Markdown、HDF5、PNG 圖表等格式供不同用途使用 |
| A6 | **特徵瀏覽器（Feature Browser）** | 提供 6 個分頁視覺化介面，讓你像逛資料庫一樣地瀏覽每個因子的分佈、時間序列、相關性與品質 |
| A7 | **配置管理系統（Config Management）** | 三層配置策略（預設 YAML < 使用者 YAML < API 即時覆蓋），單一配置檔控制整個分析管道的所有行為 |
| A8 | **API 層（API Layer）** | 提供 REST 端點（觸發分析、查詢進度、匯出結果）與 WebSocket 即時進度推送 |
| A9 | **前端 UI（Frontend UI）** | 22 張圖表（C1~C22）+ Feature Browser 6-tab 頁面 + 功能層級面板，提供完整視覺化操作介面 |
| A10 | **MCP Tool 介面（MCP Tool Interface）** | 讓 AI Agent（如未來 V2.0/V3.0 版本）能透過自然語言查詢 IC 深度分析結果 |
| A11 | **架構基礎設施（Architecture Infrastructure）** | Protocol 介面定義、Factory 函式、例外類別、錯誤處理模式，確保系統解耦設計規範 |

---

## 1.5 一句話總結

> **IC Gatekeeper 是量化研究的品管守門人：Feature Factory 生產一千個候選訊號，IC Gatekeeper 用八個嚴格的統計關卡篩除九成的雜訊，把剩下真正有預測力、統計顯著、彼此多元化的精選因子，安全移交給下游的機器學習模型——這一道防線，是避免「垃圾進、垃圾出」的核心保障。**

---
