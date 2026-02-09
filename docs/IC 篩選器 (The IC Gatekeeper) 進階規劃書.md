# Phase 2: IC 篩選器 (The IC Gatekeeper) 進階規劃書

> **版本**: V0.1  
> **更新日期**: 2026-02-09  
> **關鍵變更**:  
> - 整合 V0.05 的核心規格，新增實作層級細節，包括模組化檔案結構、關鍵函數輸入/輸出格式、依賴套件確認，以及驗收標準。  
> - 強調與 Phase 1 (特徵工廠) 的無縫整合，支援全球/事件驅動模式，並強化錯誤處理與效能優化。  
> - 新增 5.1 實作模組細節 (從先前建議中提取)，以指導程式碼開發；擴展報告規格以包含視覺化數據結構；新增 6. 風險與驗收標準。  
> - 確保向後相容：保留簡易 IC 計算作為 fallback，預設使用 Spearman 方法（抗極端值）。

這份文件將作為開發 Phase 2 的核心規格說明書 (SPEC)，轉變 IC 篩選器為專業 Alpha 評估工具。基於 V2.0 的業界標準 (條件 IC、ICIR、單調性檢查等)，融入實作計劃細節，如模組分離、介面擴展和效能基準。

## 1. 核心邏輯擴充 (Core Logic Enhancements)

簡易版只計算了全域的 Pearson/Spearman，這在業界是不夠的。我們需要增加維度，特別是針對「事件驅動」策略的支援。V3 新增效能考量：所有計算需在 M1 Mac 上 < 2 秒/100 特徵 × 10 萬樣本。

### 1.1 目標變數的嚴格定義 (Target Label Definition)

* 現狀問題：簡易版未定義 target_label 是什麼。

* 業界標準：必須是 「未來 N 期的收益率 (Future Returns)」，而非 0/1 分類。

* 新增規格：

  * 需實作 LabelGenerator，產生 Forward Returns (未來回報)。

  * Lag 處理：計算 T 時刻的特徵 IC 時，必須對應 (Price_T+N - Price_T) / Price_T。

  * 多週期目標：需同時計算針對 Future_1H, Future_4H, Future_24H 的 IC，找出該特徵在「哪個時間尺度」最有效。

  * V3 補充：支援簡單收益率或對數收益率 (log returns) 以減緩極端值影響；處理邊界 (最後幾行返回 NaN) 以避免數據洩漏。

### 1.2 事件驅動過濾 (Event-Driven Filtering / Conditional IC) (新增)

* 現狀問題：全域 IC (Global IC) 會將 95% 的盤整時間與 5% 的突破時間混在一起算，稀釋了「特定型態」的有效性。

* 業界標準：條件 IC (Conditional IC) —— 只在特定條件觸發時計算相關性。

* 新增規格：

  * Event Filter 模組：

    * 支援 Query String 過濾（例如：Close > Open * 1.03 或 Volume > MA_Vol_20 * 2）。

    * Global Mode：若 Query 為空，則使用全歷史數據計算。

    * Event Mode：若 Query 有值，只保留符合條件的 $T_0$ 行數進行 IC 運算。

  * 樣本數安全檢查 (Sample Size Check)：

    * 若篩選後的事件數量過少（例如 < 100 次），IC 統計不具顯著性，需回傳 Low Confidence 警告或拒絕計算。

  * V3 補充：使用 pandas eval() 解析 Query 生成 boolean mask；整合至特徵提取流程，支持配置檔預設 Query；記錄警告至 logger。

### 1.3 ICIR (IC Information Ratio) - 穩定性指標

* 現狀問題：簡易版只看 Mean IC。若特徵不穩定（時正時負），會害死模型。

* 業界標準：ICIR = Mean(IC) / Std(IC)。

* 新增規格：

  * 計算 Rolling IC（時間序列 IC）：每一天/每一週算出一個 IC 值。

  * 計算 IC 的標準差 (Volatility of IC)。

  * 篩選標準：除了 Abs(IC) > 0.02，還需 ICIR > 0.5（數值可調）。確保因子是「穩定地」提供預測力。

  * V3 補充：預設 window_size=252 (一年交易日) 計算 Rolling IC；支援多 Lag 衰減曲線，輸出為時間序列 List 以供報告視覺化。

### 1.4 分組 IC 分析 (Grouped IC / Regime Analysis)

* 現狀問題：全域 IC 會掩蓋局部失效的問題。

* 業界標準：檢查因子在不同環境下的表現。

* 新增規格：

  * 按年份分組 (Yearly IC)：檢查特徵是否在特定年份失效？

  * 按市場狀態分組 (Regime IC)：檢查特徵在「高波/低波」或「牛/熊」狀態下的 IC 表現。

  * 用途：若某特徵在不同環境下 IC 方向相反（例如牛市正相關、熊市負相關），應剔除或需加入Regime判斷。

  * V3 補充：Regime 定義可基於 VIX (高波>30) 或 SMA (牛市: Close > SMA_200)；輸出為 Dict 如 {'2023': 0.18, 'bull': 0.20}。

## 2. 特徵互相關與冗餘剔除 (Collinearity & Redundancy)

簡易版只各別看每個特徵好不好，沒看特徵之間是否重複。V3 強調多元化：確保選出特徵相關性 < 0.7。

### 2.1 相關性矩陣過濾 (Correlation Matrix Filter)

* 業界痛點：特徵工廠產生的 EMA_5 和 EMA_8 相關性可能高達 0.99。若 Top 10 特徵都是 EMA 變體，模型會因為共線性失效。

* 新增規格：

  * 在通過 IC 篩選的特徵中，計算兩兩特徵的相關性。

  * 去重邏輯：若 Feature A 與 Feature B 相關性 > 0.7，則保留 ICIR 較高 的那個，剔除另一個。

  * 目標：確保選出的 50 個特徵是「多元化 (Diversified)」的。

  * V3 補充：使用階層聚類 (scikit-learn linkage) 或貪婪算法實現剔除；計算 corr matrix 需高效 (pandas corr())。

## 3. 單調性分析 (Monotonicity / Quantile Analysis)

這是檢驗因子品質最直觀的方法，用於確認因子值與回報之間是否存在線性或單調關係。V3 新增嚴格檢查：若非單調，返回警告並可選剔除。

### 3.1 分位數收益分析 (Quantile Return Analysis)

* 概念：好的特徵，其特徵值最大的那一組（Top Quantile），未來收益應最高；最小的那一組，收益應最低。

* 新增規格：

  * 將特徵值切分為 5 等份 (Quintiles)。

  * 計算每一等份的 平均未來收益。

  * 檢驗標準：收益是否隨分位數 「嚴格單調遞增」或「遞減」？

  * 用途：若 IC 很高但分位數收益非線性（例如中間高兩邊低），說明該特徵可能由極端值貢獻，需做去極值處理或剔除。

  * V3 補充：使用 pd.qcut() 分位；計算累計收益 (cumulative returns) 作為報告曲線數據；預設 num_quantiles=5，可調。

## 4. 完整的 IC 報告規格 (The Report SPEC)

除了 JSON 檔，定義報告中具體包含的欄位，以便前端圖表呈現。V3 擴展數據結構以支援視覺化 (e.g., X-Y 對、曲線數據)。

### 4.1 報告結構 (JSON Output Spec)

1. Analysis Metadata (分析環境)

   * Mode: Global vs Event-Driven

   * Filter Condition: Close > Open * 1.03 (若有)

   * Sample Size: N = 1500 events

   * V3 補充：新增 'analysis_time': float (計算時間秒數), 'warnings': List[str] (e.g., 'Low sample size')。

2. Summary Table (總表)

   * Feature Name

   * IC Mean (平均預測力)

   * IC Std (波動率)

   * ICIR (性價比，最重要)

   * Rank IC (秩相關，抗極端值)

   * Autocorrelation (特徵自身的換手率)

   * V3 補充：新增 'p_value': float (顯著性), 'monotonic': bool (從單調性測試)。

3. IC Decay (IC 衰減曲線)

   * X軸：未來期數 (Lag 1, 3, 5, 10, 24)

   * Y軸：IC Mean

   * 用途：判斷該因子是「短線因子」還是「長線因子」。

   * V3 補充：輸出為 Dict[Lag, IC] 如 {'1': 0.15, '4': 0.12}，適合繪製線圖。

4. Cumulative Returns by Quantile (分層累計收益圖)

   * 5 條曲線，分別代表 Q1 (Low) 到 Q5 (High) 的特徵值組別的累計收益。

   * 驗收標準：好的因子，這 5 條線應該像扇子一樣展開，且不交叉。

   * V3 補充：輸出為 Dict[int, List[float]] 如 {'Q1': [0.01, 0.02, ...], 'Q5': [0.05, 0.07, ...]}，包含時間序列以供累計曲線繪製。

## 5. 總結：Phase 2 的修正後待辦事項 (Revised TODO List)

在您開始寫程式碼之前，您的 PLAN 應該包含以下模組的設計：

1. [Module] Label Generator: 負責產生 Future_Return_N，並處理時間對齊。

2. [Module] Event Filter (新增):

   * 實作 Query String 解析。

   * 實作 $T_0$ 遮罩 (Mask) 生成與樣本數檢查。

3. [Module] IC Engine:

   * 實作 Pearson/Spearman。

   * 實作 ICIR 計算。

   * 實作 Rolling IC (時間序列 IC)。

4. [Module] Redundancy Filter: 實作特徵間的相關性矩陣與剔除邏輯。

5. [Module] Monotonicity Tester: 實作分位數分析，檢查單調性。

6. [Report] Reporter: 產出包含 Meta, IC Decay, Quantile Return 的詳細數據結構。

### 5.1 實作模組細節 (Implementation Details) (V3 新增)

基於先前建議，細化檔案結構與整合：

- **新增檔案** (置於 `momentum/Analysis/`): `label_generator.py`, `event_filter.py`, `ic_engine.py`, `redundancy_filter.py`, `monotonicity_tester.py`, `ic_reporter.py`。每個模組單一責任，總計 6 個檔案。

- **修改現有檔案**: `feature_selection.py` (作為協調器，注入新模組)；`feature_extractor.py` (注入事件參數)；`protocols.py` (擴展介面)；配置檔 (新增 Query 設定)；測試檔 (擴展覆蓋)。

- **關鍵函數輸入/輸出** (詳見先前建議，簡述): 
  - `generate_labels`: Input: klines_df, lags; Output: Dict[str, pd.Series]。
  - `apply_event_filter`: Input: features_df, query_str; Output: Tuple[pd.DataFrame, bool, int]。
  - `calculate_advanced_ic`: Input: features_df, target_labels; Output: Dict[str, Dict]。
  - `filter_redundancy`: Input: features_df, ic_dict; Output: pd.DataFrame。
  - `test_monotonicity`: Input: feature_series, returns_series; Output: Dict。
  - `generate_full_report`: Input: ic_dict, monotonicity_results; Output: Dict (JSON)。

- **依賴套件**: 確認 `scipy`, `pandas`, `numpy`, `scikit-learn` (升級至指定版本)；無新增。

## 6. 風險與驗收標準 (Risks & Success Criteria) (V3 新增)

### 6.1 風險與緩解措施

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|---------|
| 事件過濾樣本不足導致 IC 不準 | 中 | 高 | 安全檢查 + 回退全球模式，記錄警告。 |
| 相關性計算效能瓶頸 (大特徵集) | 低 | 中 | 使用 pandas corr() + 分批處理，若 >200 特徵限縮。 |
| 單調性檢查過嚴剔除有效特徵 | 中 | 中 | 設可調門檻 (e.g., 允許輕微非單調)，人工驗證 Top 20。 |
| 報告數據過大影響前端 | 低 | 低 | 限制曲線長度 (e.g., 采样)，JSON 壓縮。 |

### 6.2 驗收標準

- **功能性**: IC 計算 < 2 秒/100 特徵；報告完整 (JSON 可視化)；支援事件模式 (手動驗證 Top 10 特徵合理)。
- **效能**: M1 Mac 基準，篩選後特徵數可控 (200+ → 50+)；記憶體峰值 < 1GB。
- **品質**: 測試覆蓋 ≥ 80% (pytest)；日誌完整；向後相容簡易版。

這樣規劃後，您的 IC 篩選器就不再是一個簡單的過濾網，而是一個專業的 Alpha 評估中心，且完全支援您想做的「正反案例（事件驅動）」研究。