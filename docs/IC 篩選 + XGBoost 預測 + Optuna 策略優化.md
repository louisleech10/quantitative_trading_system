# 系統架構升級規劃：IC 篩選 + XGBoost 預測 + Optuna 策略優化

## 1. 前言 (Foreword)

本文件旨在指導現有量化交易系統的架構升級。目前的系統開發處於「單點功能」階段（手動設定參數 -> 訓練），我們將轉型為**「工業級因子工廠」**模式。

核心目標是解決「人工挑選指標參數」的效率瓶頸與過度擬合風險，轉而採用**「特徵大爆發 -> IC 統計篩選 -> XGBoost 全特徵融合 -> Optuna 執行優化」**的標準量化流水線。

---

## 2. 核心設計理念 (Core Philosophy)

我們將系統劃分為三個明確的職責層級，各司其職，互不干擾：

1. **原料層 (Feature Engineering & Selection)**：
* **哲學**：寧濫勿缺。大量生成不同參數的技術指標（EMA, RSI, BB...）及其衍生特徵（Diff, Distance）。
* **守門員**：**IC (Information Coefficient)**。在進入 AI 訓練前，利用統計學方法（Pearson Correlation）計算每個特徵與未來漲跌的相關性，自動剔除無效雜訊。


2. **大腦層 (Pattern Recognition - XGBoost)**：
* **哲學**：不做預設立場。將通過 IC 篩選的「高質量特徵全家桶」一次性餵給模型。
* **任務**：讓 XGBoost 自動學習特徵間的非線性關係（如：震盪時看 RSI，趨勢時看 EMA）。
* **輸出**：不直接輸出買賣訊號，而是輸出 **「預測機率 (Probability Score)」**（例如：上漲信心度 0.85）。


3. **執行層 (Strategy Optimization - Optuna)**：
* **哲學**：落地執行。Optuna 不再用來尋找「EMA 該用幾日線」（這是 XGBoost 的工作），而是用來尋找**「交易規則」**。
* **任務**：尋找最佳的「進場閾值（機率 > 多少才買？）」、「止損比例」與「止盈比例」。



---

## 3. 現狀與缺口分析 (Gap Analysis)

基於對目前 codebase 的檢視，我們需要補強以下模組：

| 模組功能 | 現狀 (As-Is) | 目標 (To-Be) | 開發動作 |
| --- | --- | --- | --- |
| **特徵工程** | 依賴 `config/indicators.yaml` 手動設定單一參數。 | 支援**「參數掃描」**生成（例如自動產生 EMA 5, 8, 13...200）。支援**「衍生特徵」**計算（Cross, Diff）。 | **修改/增強** |
| **特徵篩選** | 無。所有計算出的指標都丟進模型。 | 新增 **IC 分析器**。計算特徵與 Label 的相關係數，過濾低 IC 特徵。 | **新增** |
| **模型訓練** | `xgboost_analyzer.py` 針對單一設定跑訓練。 | 支援讀取篩選後的「特徵矩陣」進行單次、全特徵訓練。 | **修改** |
| **策略優化** | `optuna_optimizer.py` 正在嘗試調整指標參數 (EMA Length)。 | Optuna 改為調整**「執行參數」** (Threshold, TP, SL)，輸入源改為 XGBoost 的預測機率。 | **重構/新增** |
| **回測系統** | 尚未完善。 | 需要一個基於「機率訊號」的快速向量化回測引擎。 | **新增** |

---

## 4. 實作路徑與規格 (Implementation Roadmap)

請 AI Agent 依照以下四個階段進行開發：

### Phase 1: 特徵工廠升級 (Feature Factory Upgrade)

* **目標**：讓系統能自動產生「一籃子」特徵，而不需要人工在 Config 檔寫幾百行。
* **需求**：
1. 修改 `FeatureExtractor`，支援**「生成模式 (Generation Mode)」**。
2. 針對 EMA, RSI, BB 等核心指標，實作**對數級距 (Log-Scale)** 的參數生成（如 Fibonacci 數列：5, 8, 13, 21, 34, 55, 89, 144, 233）。
3. 自動計算**衍生特徵**：
* `Distance`: (Close - Indicator) / Indicator
* `Interaction`: EMA_Short - EMA_Long


4. 保持與現有 Data Source 的相容性。



### Phase 2: IC 篩選器 (The IC Gatekeeper)

* **目標**：在訓練前清洗數據，避免維度災難。
* **需求**：
1. 新增模組 `momentum/Analysis/feature_selection.py`。
2. 實作 `calculate_ic(features_df, target_label)` 函數。
3. 實作篩選邏輯：輸入原始 DataFrame，輸出只包含 `abs(IC) > Threshold` 欄位的 DataFrame。
4. 輸出一份「特徵品質報告」，列出哪些指標最有效，哪些是雜訊。



### Phase 3: XGBoost 全特徵融合 (Model Integration)

* **目標**：利用 XGBoost 的樹狀結構自動處理特徵權重。
* **需求**：
1. 修改 `xgboost_analyzer.py` 的訓練流程。
2. **移除**對指標參數的外部迴圈（不再從外部 Loop EMA 5, EMA 10...）。
3. **輸入**改為 Phase 2 輸出的「精選特徵集」。
4. 確保模型輸出包含 `.predict_proba()` 的機率值，並儲存至結果 CSV 中。



### Phase 4: 策略執行優化 (Execution Optimization)

* **目標**：將 AI 的「預測」轉化為「獲利」。
* **需求**：
1. 新增 `momentum/Strategy/backtest_engine.py` (或是利用現有回測架構)。
2. 建立新的 Optuna 任務 `optimize_execution`。
3. **Optuna 搜尋空間 (Search Space)** 定義：
* `entry_threshold`: float (0.5 ~ 0.95) - AI 信心多少才進場？
* `stop_loss_atr`: float (1.0 ~ 5.0) - 用幾倍 ATR 止損？
* `take_profit_ratio`: float (1.0 ~ 5.0) - 盈虧比設定。


4. 利用 XGBoost 產生的機率欄位進行快速回測，尋找上述參數的最佳組合。



---

## 5. 資料流向總結 (Data Flow Summary)

1. **Raw Data** (OHLCV, Glassnode...)
⬇
2. **Feature Generation** (產生 200+ 個特徵：EMA_5...EMA_200, RSI_Diff...)
⬇
3. **IC Selection** (過濾掉 IC < 0.01 的雜訊，剩 50+ 個特徵)
⬇
4. **XGBoost Training** (訓練模型，學習特徵間的非線性關係)
⬇
5. **Probability Output** (產出測試集的預測機率：0.1 ~ 0.99)
⬇
6. **Optuna Optimization** (在機率基礎上，尋找最佳進出場規則)
⬇
7. **Final Strategy** (模型檔 + 執行參數設定檔)

---

## 6. 給 AI Agent 的執行指令 (Prompt)

> 「請閱讀 `docs/ARCH_REFACTOR_IC_XGB_OPTUNA.md`。這是我們系統的最終架構目標。
> 我們將保留現有的資料下載與儲存機制。請優先從 **Phase 1 (特徵工廠升級)** 與 **Phase 2 (IC 篩選器)** 開始實作。
> 請先分析 `momentum/FeatureEngineering` 和 `momentum/Analysis` 的現有程式碼，並告訴我你打算如何修改以達成 Phase 1 & 2 的目標。」