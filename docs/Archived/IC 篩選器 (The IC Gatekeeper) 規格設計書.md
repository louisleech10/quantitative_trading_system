# Phase 2: IC 篩選器 (The IC Gatekeeper) — 規格設計書 V2 (Frozen)

> **版本**: V2.0 (Frozen)  
> **更新日期**: 2026-02-09  
> **凍結日期**: 2026-02-09  
> **定位**: Phase 2 IC 篩選器之詳細設計規格  
> **前置文件**:  
> - `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` (主架構 V2.1)  
> - `docs/Feature Generation Factory.md` (Phase 1 規格 V2.2)  
> - `docs/IC 篩選器 (The IC Gatekeeper) 進階規劃書.md` (V0.1 規劃書)  
> **對應 Phase**: Phase 2 — IC 篩選器 + 模型驗證修復 (2-3 天)

### V2 變更日誌 (Changelog from V1)

| # | 變更類型 | 影響章節 | 說明 |
|---|---------|---------|------|
| 1 | **修正** | §3, §8 | `statistical_validator.py` 新增模組說明，消除 §8 檔案結構與 §3 模組描述的不一致 |
| 2 | **修正** | §3.9.1 | 篩選流程步驟編號改為對齊 §2.1 八階段流水線的 Stage 編號 |
| 3 | **修正** | §8, §10, §14 | Protocol 名稱統一：移除孤立引用 (`ICacheReader`, `IFeatureReader`)；`IEventFilter`/`IRedundancyFilter` 改為模組內部介面 |
| 4 | **修正** | §6.1 | `filter_log` JSON 的 key 名改為對齊 §2.1 Stage 編號 |
| 5 | **優化** | §3.9 | 新增快取策略設計（支援 `refilter` 不重算 IC）與 Stage 0 輸入驗證設計 |
| 6 | **優化** | §3.7.3 | 淨 IC 公式的 λ 係數明確定義為 `transaction_cost` |
| 7 | **優化** | §3.4.2 | ICIR Rolling Window 自動調整的參考 TF 明確指定為 12h |
| 8 | **修正** | §3 | 標題由 "8 Pillars" 改為 "8 Pillars + Orchestrator" 以正確反映模組結構 |

---

## 1. 專案願景與目標

### 1.1 核心目標

將 IC 篩選器從「簡易相關性過濾器」升級為**業界標準的 Alpha 評估中心 (Alpha Evaluation Center)**。建立一個統計嚴謹、可配置、可擴充的特徵品質評估系統，能夠從 Phase 1 特徵工廠產出的數千個特徵中，**精準篩選出具有穩定預測力的高品質因子**，並為 Phase 3 模型訓練提供乾淨、多元化的特徵矩陣。

### 1.2 與上下游系統的關係

**上游 (Phase 1 Feature Factory)**：
- 接收特徵矩陣 (`features.h5`，800~15000+ 特徵)
- 接收特徵 Metadata (`meta.json`，含物理意義、計算層級、指標分類)
- 接收 Label 矩陣 (`labels.h5`，多 horizon 的 binary/regression label)
- 接收多時間框架 (Multi-TF) 特徵，需支援跨 TF 的 IC 分析

**下游 (Phase 3 Model Training)**：
- 輸出精選特徵矩陣 (`filtered_features.h5`，50~100 個高品質特徵)
- 輸出完整的 IC 報告 (`ic_report.json`，含所有分析結果)
- 輸出特徵重要性排名，供 LightGBM/XGBoost 訓練參考
- 輸出特徵相關性矩陣，供模型解釋性分析 (SHAP) 參考

### 1.3 與現有 Codebase 的關係

**現況分析**：

| 模組 | 現狀 | 問題 | 升級目標 |
|------|------|------|----------|
| IC 計算 | 無正式模組 | Phase 0 僅有概念驗證等級的 Pearson/Spearman | **全新 `ICEngine`** — 完整 IC/ICIR/Rolling IC/Grouped IC/Conditional IC |
| Label 生成 | Phase 1 已有基礎 `LabelGenerator` | 僅支援 binary/return label，缺少對數收益率、風險調整 label | **擴展** `LabelGenerator` — 新增 log returns、risk-adjusted labels、多 horizon 對齊 |
| 特徵篩選 | 無 | 所有特徵直接丟進模型 | **全新** `RedundancyFilter` — 相關性矩陣 + 階層聚類 + VIF |
| 品質報告 | 無 | 無特徵品質可視化 | **全新** `ICReporter` — JSON 結構化報告 + 前端圖表數據 |
| 事件過濾 | 無 | 無條件 IC 支援 | **全新** `EventFilter` — Query String 解析 + Boolean Mask |
| 單調性檢查 | 無 | 無分位數收益分析 | **全新** `MonotonicityTester` — Quantile Analysis + Long-Short Spread |

**設計原則**：
- **統計嚴謹性第一**：所有 IC 計算必須附帶 p-value、信賴區間、樣本數檢查，杜絕偽相關
- **穩定性重於絕對值**：ICIR (IC Information Ratio) 比 IC Mean 更重要 — 業界共識
- **多元化篩選**：不只看個別 IC，還要確保選出特徵集的多元化 (Diversification)
- **事件驅動相容**：同時支援 Global Mode（全歷史）與 Event Mode（條件觸發），完美對接現有案例搜尋框架
- **完全可配置**：所有閾值、窗口、分位數均從 Config 讀取，AI Agent 可動態調整
- **Phase 1 深度整合**：利用 Feature Factory 的七段式命名、Metadata、多數據源特性，實現按類別 / 層級 / 數據源的多維度 IC 分析

### 1.4 關鍵需求 (Key Requirements)

| # | 需求 | 優先級 | 說明 |
|---|------|:------:|------|
| R1 | **多方法 IC 計算** | P0 | Pearson IC + Spearman Rank IC，預設使用 Spearman（抗極端值） |
| R2 | **IC Information Ratio (ICIR)** | P0 | IC 穩定性評估，ICIR > 0.5 為門檻（可配置） |
| R3 | **Rolling IC 時間序列** | P0 | 滾動窗口 IC，檢測因子有效性的時變特性 |
| R4 | **條件 IC (Conditional IC)** | P0 | 事件驅動模式，只在特定條件觸發時計算 IC |
| R5 | **冗餘過濾 (Redundancy Filter)** | P0 | 相關性矩陣 + 階層聚類，確保特徵多元化 |
| R6 | **單調性檢驗 (Monotonicity Test)** | P0 | 分位數收益分析，驗證因子值與回報的單調關係 |
| R7 | **IC 衰減分析 (IC Decay)** | P0 | 多 horizon IC 比較，判斷因子時效性 |
| R8 | **統計顯著性檢驗** | P0 | t-test p-value，過濾偽相關因子 |
| R9 | **分組 IC 分析** | P1 | 按年份、市場狀態、波動率環境分組，檢測因子一致性 |
| R10 | **IC 衰減半衰期 (IC Half-Life)** | P1 | 量化 IC 衰減速度，指導交易頻率決策 |
| R11 | **因子換手率分析 (Turnover Analysis)** | P1 | 分位數組成的期間變化率，評估交易成本影響 |
| R12 | **Long-Short Spread** | P1 | Top 與 Bottom 分位數的收益差，直觀評估因子盈利能力 |
| R13 | **多層級 IC 分析** | P1 | 按 Feature Factory 層級 (Layer 1-6) 分析 IC 分佈 |
| R14 | **多數據源 IC 分析** | P1 | 按數據源 (close, volume, taker_ratio...) 分組的 IC 統計 |
| R15 | **因子覆蓋率分析 (Coverage)** | P1 | 每個因子的有效值比例，低覆蓋率因子需標記 |
| R16 | **樣本外 IC 驗證 (OOS IC)** | P2 | Train/Test IC 對比，檢測 IC 的泛化能力 |
| R17 | **多重共線性檢測 (VIF)** | P2 | Variance Inflation Factor，進階共線性診斷 |
| R18 | **因子中性化 (Factor Neutralization)** | P2 | 市場/板塊中性化後的 Pure IC |
| R19 | **AI Agent 自動化接口** | P1 | MCP Tools 暴露，支援 AI Agent 自主 IC 篩選迭代 |
| R20 | **極端值處理 (Winsorization)** | P0 | IC 計算前的數據清洗，防止極端值扭曲結果 |

---

## 2. 系統架構概觀

### 2.1 IC 篩選器八階段流水線 (8-Stage Pipeline)

```
Stage 0: Data Ingestion (數據載入)
    ↓ 讀取 Phase 1 特徵矩陣 + Label + Metadata
Stage 1: Data Preprocessing (數據預處理)
    ↓ 極端值處理 (Winsorization)、缺失值處理、因子標準化
Stage 2: Label Generation & Alignment (標籤生成與對齊)
    ↓ Future Returns 計算、多 Horizon 對齊、邊界處理
Stage 3: Event Filtering (事件過濾) [必須支援]
    ↓ Query String 解析、Boolean Mask 生成、樣本數安全檢查
Stage 4: IC Calculation (IC 核心計算)
    ↓ Pearson/Spearman IC、ICIR、Rolling IC、IC Decay、Grouped IC
Stage 5: Statistical Validation (統計驗證)
    ↓ p-value 過濾、信賴區間計算、單調性檢驗、覆蓋率檢查
Stage 6: Redundancy Elimination (冗餘剔除)
    ↓ 相關性矩陣、階層聚類、貪婪去重、VIF 檢測
Stage 7: Report Generation & Persistence (報告生成與持久化)
    ↓ JSON 結構化報告、精選特徵矩陣輸出、HDF5 儲存
```

### 2.2 雙模式架構 (Dual-Mode Architecture)

| 模式 | 說明 | 觸發條件 | 典型場景 |
|------|------|---------|---------|
| **Global Mode** | 使用全歷史數據計算 IC | 無 event_query 或 event_query 為空 | 常規因子研究、全市場掃描 |
| **Event Mode** | 僅使用事件觸發時刻的數據計算 IC | event_query 有值 | 案例搜尋框架整合、特定型態研究 |

**Event Mode 與案例搜尋框架的整合**：
- 案例搜尋引擎 (`case_search_engine.py`) 的 30 參數搜尋結果可直接轉為 event_query
- 正例案例 ($T_0$ 時刻) 作為事件觸發點
- 反例案例可作為對照組，計算「正例 IC vs 反例 IC」的差異

### 2.3 數據流向 (Data Flow)

**Input Artifacts**：

| 來源 | 路徑 | 格式 | 內容 |
|------|------|------|------|
| Phase 1 特徵矩陣 | `data_cache/features/{symbol}_{tf}_factory.h5` | HDF5 | n_samples × n_features (float32) |
| Phase 1 特徵 Metadata | `data_cache/features/{symbol}_{tf}_meta.json` | JSON | 每個特徵的層級、類別、參數、物理意義 |
| Phase 1 Label 矩陣 | `data_cache/features/{symbol}_{tf}_labels.h5` | HDF5 | n_samples × n_horizons (int32/float32) |
| 原始 K 線數據 | `data_cache/{symbol}_{tf}.h5` | HDF5 | OHLCV + 衍生欄位 |
| IC 配置 | `config/ic_config.yaml` | YAML | 所有 IC 篩選相關參數 |

**Output Artifacts**：

| 產出 | 路徑 | 格式 | 內容 |
|------|------|------|------|
| 精選特徵矩陣 | `data_cache/features/{symbol}_{tf}_filtered.h5` | HDF5 | n_samples × n_filtered_features |
| IC 分析報告 | `data_cache/reports/ic_report_{case_id}.json` | JSON | 完整 IC 分析結果（供前端/AI） |
| IC 摘要報告 (AI-Readable) | `data_cache/reports/ic_summary_{case_id}.md` | Markdown | 關鍵發現摘要（供 LLM 閱讀） |
| 相關性矩陣 | `data_cache/reports/correlation_matrix_{case_id}.json` | JSON | 特徵間相關性（供前端熱力圖） |
| 篩選日誌 | `data_cache/reports/ic_filter_log_{case_id}.json` | JSON | 每步篩選的特徵數量變化 |

---

## 3. 功能模組詳細設計 (The 8 Pillars + Orchestrator)

### 3.1 模組 A：數據預處理器 (Data Preprocessor)

**目標**：在 IC 計算前清洗數據，確保統計分析的可靠性。這是 V0.1 完全缺失的環節。

#### 3.1.1 極端值處理 (Winsorization)

**業界背景**：量化因子研究中，1~2% 的極端值可以完全扭曲 Pearson IC 的結果。Winsorization 是業界標準的預處理步驟，幾乎所有量化基金（Two Sigma、Citadel、WorldQuant）都會在 IC 計算前進行。

| 處理方法 | 說明 | 適用場景 | 參數 |
|---------|------|---------|------|
| **Winsorize** | 將超出百分位的值截斷至邊界值 | 預設方法，保留分佈形狀 | `lower_percentile=1`, `upper_percentile=99` |
| **MAD Clip** | 基於 Median Absolute Deviation 的截斷 | 分佈高度偏斜時 | `num_mad=5` |
| **Z-Score Clip** | 超出 N 個標準差的值截斷 | 近似正態分佈時 | `max_zscore=3.0` |
| **無處理** | 原始值直接計算 | Debug / 比較用 | — |

**處理策略**：
- **預設使用 Winsorize (1st-99th)**：簡單有效，業界最常用
- **按特徵類別自動調整**：型態辨識特徵 (-100/0/+100) 不做 Winsorize；連續值特徵做
- **可配置**：使用者可在 Config 中選擇方法或關閉

#### 3.1.2 缺失值處理

| 缺失類型 | 處理策略 | 說明 |
|---------|---------|------|
| **期初 NaN** | 保留（IC 計算時自動 dropna） | 長週期指標的正常行為（如 EMA_233 前 233 行為 NaN） |
| **中段零星 NaN** | Forward Fill（最多 3 期） | 短暫數據缺失 |
| **大面積 NaN (>30%)** | 標記該特徵為「低覆蓋率」，發出警告 | 數據源品質問題 |
| **Label NaN** | 刪除對應行（不可填補） | 最後 N 行因未來回報不可知 |

#### 3.1.3 因子標準化 (Factor Standardization)

**業界做法**：部分量化基金在 IC 計算前對因子進行標準化，使不同量綱的因子可比較。

| 方法 | 公式 | 適用場景 |
|------|------|---------|
| **Cross-Sectional Z-Score** | `(x - mean) / std` | 多幣種橫截面分析 |
| **Time-Series Z-Score** | `(x - rolling_mean) / rolling_std` | 單幣種時間序列分析 |
| **Rank Transform** | `percentile_rank(x)` | 消除量綱與分佈差異，Spearman IC 的基礎 |
| **無標準化** | 原始值 | Pearson IC 需要原始值 |

**設計決策**：IC 計算時不強制標準化（Spearman 本身已包含 Rank），但提供選項供進階使用者啟用。

---

### 3.2 模組 B：標籤生成器 (Label Generator) — 擴展

**目標**：擴展 Phase 1 已有的 `LabelGenerator`，支援 IC 分析所需的多種收益率計算方式。

#### 3.2.1 收益率類型

**V0.1 問題**：只支援簡單收益率。業界 IC 研究常用對數收益率（Log Returns），因其具有時間可加性和更好的統計性質。

| Label 類型 | 公式 | 物理意義 | 適用場景 |
|-----------|------|---------|---------|
| **Simple Return** | `(P_{t+N} - P_t) / P_t` | 簡單百分比收益 | 預設方法，直觀 |
| **Log Return** | `ln(P_{t+N} / P_t)` | 對數收益（時間可加性） | 業界標準，減緩極端值影響 |
| **Excess Return** | `R_{asset} - R_{BTC}` | 超額收益（去大盤效應） | 多幣種相對強弱研究 |
| **Risk-Adjusted Return** | `R / σ_rolling` | 風險調整收益 | 考慮波動率的因子有效性 |
| **Winsorized Return** | `winsorize(Simple Return, 1%, 99%)` | 截尾收益 | 防止極端收益扭曲 IC |

#### 3.2.2 多 Horizon 生成

**與 Phase 1 的整合**：Phase 1 的 LabelGenerator 已支援 `horizons: [3, 5, 8, 13, 21]`。本模組擴展如下：

| 設計項 | Phase 1 現狀 | Phase 2 擴展 |
|--------|-------------|-------------|
| Horizon 定義 | 以 K 線根數為單位 | 新增「時間映射」— 自動根據 TF 換算實際時間 |
| 收益率類型 | binary + simple return | 新增 log return、excess return、risk-adjusted |
| 邊界處理 | 最後 N 行 NaN | 新增 NaN 計數統計，確保有足夠有效樣本 |
| 多 TF 對齊 | 未特別處理 | 新增跨 TF Horizon 自動對齊（見 3.2.3） |

#### 3.2.3 多時間框架 Label 對齊

**場景**：當 Feature Factory 使用 `training_tfs: ["1h", "4h", "12h"]` 時，1h 特徵的 `future_5_bar` 代表 5 小時後，而 12h 特徵的 `future_5_bar` 代表 60 小時後。IC 分析需要統一的 horizon 語義。

| 時間框架 | Label `future_5_bar` 實際時間 | 統一語義 `future_24h` 對應 bar 數 |
|---------|----------------------------|-------------------------------|
| 1h | 5 小時 | 24 bars |
| 4h | 20 小時 | 6 bars |
| 12h | 60 小時 | 2 bars |

**設計方案**：
- 提供兩種 Horizon 指定方式：`bar_count`（傳統）vs `time_duration`（如 `"24h"`, `"3d"`, `"1w"`）
- Config 中使用 `time_duration` 時自動根據 TF 換算為 bar count
- IC 報告中同時顯示 bar count 和實際時間，方便解讀

---

### 3.3 模組 C：事件過濾器 (Event Filter) — 核心創新

**目標**：實現條件 IC (Conditional IC)，讓 IC 分析不再被 95% 的盤整數據稀釋。這是本系統相對業界標準工具（Alphalens、FactorLens）的關鍵差異化功能。

#### 3.3.1 事件定義方式

| 事件類型 | Query String 範例 | 說明 | 使用場景 |
|---------|------------------|------|---------|
| **價格突破** | `close > open * 1.03` | 大陽線（漲幅 > 3%） | 突破型策略因子研究 |
| **量能異常** | `volume > volume_SMA_20 * 2` | 成交量 > 20MA 兩倍 | 量能驅動策略 |
| **技術指標** | `close_RSI_14 > 70` | RSI 超買區 | 反轉型策略因子 |
| **波動率環境** | `close_ATR_14 / close > 0.05` | ATR 佔價格比 > 5% | 高波動環境因子 |
| **複合條件** | `(close > close_EMA_55) & (close_ADX_14 > 25)` | 趨勢中且趨勢強 | 趨勢型策略因子 |
| **案例搜尋結果** | 直接匯入案例搜尋引擎的 $T_0$ 時刻 | 無需 Query String | 正/反例分析 |

#### 3.3.2 Query String 解析引擎

**設計**：使用 `pandas.eval()` 解析 Query String，產生 Boolean Mask。

**支援的操作符**：
- 比較：`>`, `<`, `>=`, `<=`, `==`, `!=`
- 邏輯：`&` (AND), `|` (OR), `~` (NOT)
- 算術：`+`, `-`, `*`, `/`
- 括號：`(...)` 支援嵌套
- 函式（需擴展）：`abs()`, `max()`, `min()`

**安全性設計**：
- 白名單機制：只允許 DataFrame 中已存在的欄位名
- 禁止 Python 內建函式調用（防注入）
- 最大表達式長度限制 (500 字元)
- 錯誤提示：`InvalidQueryError` 附帶可讀說明

#### 3.3.3 樣本數安全檢查 (Sample Size Guard)

**業界依據**：IC 的統計檢定力 (Statistical Power) 與樣本數直接相關。Grinold & Kahn (2000) 建議最少 30 個獨立觀測值。

| 樣本數範圍 | 行為 | 報告標記 | 說明 |
|-----------|------|---------|------|
| N ≥ 200 | 正常計算 | ✅ `Sufficient` | 統計可靠 |
| 100 ≤ N < 200 | 計算但附帶警告 | ⚠️ `Marginal` | IC 可參考但需謹慎 |
| 30 ≤ N < 100 | 計算但降低顯著性要求 | ⚠️ `Low Confidence` | p-value 閾值從 0.05 放寬至 0.10 |
| N < 30 | 拒絕計算，回退至 Global Mode | ❌ `Insufficient` | 統計不可靠，自動回退 |

#### 3.3.4 案例搜尋框架直接整合

**場景**：使用者在案例搜尋頁面找到一組正例案例，想要分析哪些因子在這些案例中最有預測力。

**整合方式**：
- 案例搜尋結果包含每個案例的 `trigger_timestamp`
- 直接將 `trigger_timestamps` 列表作為事件時刻，無需 Query String
- 支援「正例 IC vs 反例 IC」比較模式

---

### 3.4 模組 D：IC 核心計算引擎 (IC Engine) — 系統核心

**目標**：業界水準的因子預測力評估。IC Engine 是整個 Gatekeeper 的心臟。

> **實作說明**：IC Engine 的核心計算（IC/ICIR/Rolling IC/Decay）實作於 `ic_engine.py`。其中 **統計驗證** 部分（p-value、t-stat、信賴區間計算）為遵循單一職責原則 (SRP)，獨立實作於 `statistical_validator.py` 作為 IC Engine 的伴隨模組。兩者共同承擔 Stage 4 (IC Calculation) 與 Stage 5 (Statistical Validation) 的職責。

#### 3.4.1 基礎 IC 計算

| 方法 | 公式 | 特性 | 預設 |
|------|------|------|:----:|
| **Pearson IC** | `corr(feature, future_return)` | 線性相關，對極端值敏感 | 否 |
| **Spearman Rank IC** | `corr(rank(feature), rank(future_return))` | 秩相關，抗極端值，捕捉非線性 | ✅ 是 |
| **Kendall Tau** | `concordant_pairs / total_pairs` | 更穩健但計算慢 | 否（可選） |

**業界標準**：絕大多數量化基金預設使用 **Spearman Rank IC**，因為：
1. 不假設線性關係
2. 對極端值穩健
3. 與 LightGBM/XGBoost 的 Rank-based Split 天然相容

#### 3.4.2 IC Information Ratio (ICIR) — 最重要的指標

**業界共識**：ICIR 比 IC Mean 更重要。因為一個「平均 IC = 0.05 但穩定」的因子，遠優於「平均 IC = 0.10 但時好時壞」的因子。

| 指標 | 公式 | 說明 | 篩選門檻 (預設) |
|------|------|------|:-------------:|
| **IC Mean** | `mean(rolling_IC)` | 平均預測力 | `abs(ic_mean) > 0.02` |
| **IC Std** | `std(rolling_IC)` | IC 波動性 | 報告用，不做門檻篩選 |
| **ICIR** | `ic_mean / ic_std` | IC 效率比（「性價比」） | `abs(icir) > 0.5` |
| **IC t-stat** | `ic_mean / (ic_std / sqrt(N))` | 統計顯著性 | `abs(t_stat) > 2.0`（≈ p < 0.05） |
| **IC p-value** | `2 * (1 - t.cdf(abs(t_stat), df=N-1))` | 顯著性概率 | `p_value < 0.05` |
| **IC Hit Rate** | `count(IC > 0) / total_periods` | 正 IC 的頻率 | `hit_rate > 0.55` |

**ICIR 的 Rolling Window**：
- 預設 `window_size=63`（約一季交易日 × 12h = 63 bars）
- 使用者可配置：`[21, 63, 126, 252]`（1月、1季、半年、1年 × 12h）
- 按時間框架自動調整：以 12h 為參考基準 TF，若 TF=4h 則 window ×3（因 `12h/4h=3`），若 TF=1h 則 ×12

#### 3.4.3 Rolling IC 時間序列

**業界做法**：IC 不是一個靜態數字。好的因子，其 IC 應該在大多數時間窗口中保持正值（或負值）。

| 設計項 | 說明 |
|--------|------|
| **計算方式** | 將歷史數據切為多個 rolling window，每個 window 獨立計算 IC |
| **窗口大小** | 預設 `[21, 63, 126]` bars（可配置） |
| **步進 (Step)** | 預設 `stride=1`（每一步都算），可設為 `stride=7`（每週算一次）以節省計算 |
| **輸出** | 每個特徵的 IC 時間序列 `Dict[str, List[float]]` |
| **用途** | 1. 計算 ICIR 的分子分母 2. 繪製 IC 走勢圖 3. 檢測因子失效時間點 |

#### 3.4.4 IC 衰減分析 (IC Decay Analysis)

**業界背景**：因子的預測力會隨 horizon 增大而衰減。IC Decay 曲線告訴我們因子是「短線因子」還是「長線因子」，直接影響交易頻率決策。

| 設計項 | 說明 |
|--------|------|
| **多 Horizon IC** | 對同一個特徵，分別計算 `horizon=[1, 2, 3, 5, 8, 13, 21, 34, 55]` 的 IC |
| **IC Decay 曲線** | X 軸 = Horizon (bars)，Y 軸 = IC Mean |
| **IC Half-Life** | IC 衰減至峰值 50% 的 horizon 數（指數擬合） |
| **Peak Horizon** | IC 最大值對應的 horizon — 判斷因子最強的預測週期 |
| **Decay Rate** | 指數衰減係數 `IC(h) ≈ IC_0 × exp(-λh)`，`λ` 越大衰減越快 |

**IC Half-Life 計算方法**：
1. 對 IC Decay 曲線做指數擬合：`IC(h) = A × exp(-λ × h) + C`
2. Half-Life = `ln(2) / λ`
3. 若 R² < 0.5（擬合不佳），標記為 `non-exponential_decay`

**用途**：
- Half-Life < 3 bars → 超短線因子，適合高頻策略
- Half-Life 5~13 bars → 中線因子，適合 swing trading
- Half-Life > 21 bars → 長線因子，適合趨勢跟蹤

#### 3.4.5 分組 IC 分析 (Grouped IC Analysis)

**V0.1 已有概念，V1 擴展以下分組維度**：

| 分組維度 | 分組方式 | 業界意義 |
|---------|---------|---------|
| **按年份** | 按日曆年分組 | 檢測因子是否在特定年份失效 |
| **按季度** | 按日曆季度分組 | 檢測季節性效應 |
| **按市場狀態 (Regime)** | 牛市/熊市/盤整 | 檢測因子在不同市場環境的穩定性 |
| **按波動率環境** | 高波/中波/低波 | 波動率相關因子的條件有效性 |
| **按特徵類別** | trend/momentum/volatility/volume/pattern | 哪類因子在當前市場最有效 |
| **按數據源** | close/volume/taker_ratio/funding_rate | 哪個數據源的因子預測力最強 |
| **按 Pipeline 層級** | Layer 1/2/3/4/5/6 | 哪層工廠特徵最有價值 |

**Regime 定義**（可配置）：

| Regime | 定義方式 | 預設條件 |
|--------|---------|---------|
| **Bull** | 價格 > 長期均線 | `close > SMA_200` 或 `close > EMA_55` |
| **Bear** | 價格 < 長期均線 | `close < SMA_200` 或 `close < EMA_55` |
| **High Volatility** | ATR 上升 | `ATR_14 / close > percentile_80(ATR_14/close)` |
| **Low Volatility** | ATR 下降 | `ATR_14 / close < percentile_20(ATR_14/close)` |
| **Trending** | ADX 高 | `ADX_14 > 25` |
| **Ranging** | ADX 低 | `ADX_14 < 20` |

**一致性檢驗**：
- 若因子在 Bull 時 IC > 0，但 Bear 時 IC < 0 → 標記為 **`regime_inconsistent`**
- 若因子在所有 Regime 的 IC 方向一致 → 標記為 **`regime_robust`**
- 「不一致」不代表「壞」，而是需要配合 Regime 判斷使用

#### 3.4.6 因子自相關分析 (IC Autocorrelation)

**業界背景**：IC 的自相關性反映因子預測力的持續性（Persistence）。

| 指標 | 說明 | 業界意義 |
|------|------|---------|
| **IC Autocorrelation (Lag-1)** | `corr(IC_t, IC_{t-1})` | IC 的一階自相關 |
| **IC 持續性** | 自相關 > 0.3 | 因子預測力在時間上有延續性，利於策略實施 |
| **IC 反轉** | 自相關 < -0.3 | IC 有反轉傾向，可能需要動態調整方向 |

---

### 3.5 模組 E：單調性測試器 (Monotonicity Tester) — 品質驗證

**目標**：用最直觀的方式驗證因子品質 — 好的因子，其值越大（或越小），未來收益越高。

#### 3.5.1 分位數收益分析 (Quantile Return Analysis)

**方法**：
1. 將特徵值按大小切為 N 組（預設 5 組 = Quintiles）
2. 計算每組的平均未來收益
3. 檢驗收益是否隨分位數 **嚴格單調遞增** 或 **遞減**

**分位數配置**：

| 配置 | 預設值 | 說明 |
|------|--------|------|
| `num_quantiles` | 5 | 分位數數量（Quintiles） |
| `min_group_size` | 50 | 每組最少樣本數，否則減少分位數 |
| `allow_empty_groups` | false | 不允許空組（數據不足時自動降級） |

#### 3.5.2 Long-Short Spread

**業界標準指標**：Top Quantile (Q5) 與 Bottom Quantile (Q1) 的收益差。

| 指標 | 公式 | 說明 |
|------|------|------|
| **Long-Short Return** | `mean_return(Q5) - mean_return(Q1)` | 多空價差 |
| **Long-Short Sharpe** | `L/S Return / std(L/S Return)` | 風險調整多空收益 |
| **Long-Short t-stat** | `L/S Return / (se(L/S Return))` | 統計顯著性 |

**用途**：Long-Short Spread 是量化基金評估因子盈利能力最常用的指標之一。即使 IC 不高，但 Long-Short Spread 夠大且穩定，因子仍有價值。

#### 3.5.3 單調性評分 (Monotonicity Score)

**V0.1 只有 boolean 單調判斷，V1 改為連續評分**：

| 評分方法 | 公式 | 範圍 | 說明 |
|---------|------|------|------|
| **嚴格單調分數** | 相鄰分位數收益的遞增比例 | 0.0 ~ 1.0 | 1.0 = 完美單調 |
| **Spearman Rank (Quantile)** | `corr(quantile_index, mean_return)` | -1.0 ~ 1.0 | 分位數排名 vs 收益的秩相關 |
| **線性擬合 R²** | 分位數中心 vs 平均收益的線性擬合 | 0.0 ~ 1.0 | 越高越線性 |

**篩選門檻**（可配置）：
- `monotonicity_score > 0.6` → 通過（預設）
- 允許「非嚴格單調」但 Long-Short Spread 顯著的因子通過

#### 3.5.4 分位數累計收益曲線 (Cumulative Returns by Quantile)

**業界標準圖表**：5 條曲線（Q1~Q5），好的因子這 5 條線應像扇子展開且不交叉。

| 設計項 | 說明 |
|--------|------|
| **X 軸** | 時間 |
| **Y 軸** | 各分位數組的累計收益 |
| **期望形狀** | Q5 在最上方，Q1 在最下方（做多因子），或反之（做空因子） |
| **警告條件** | 曲線交叉 → 因子不穩定；Q3 (中間) 最高 → 非線性因子，需特殊處理 |
| **輸出格式** | `Dict[str, List[float]]`，每個 key 為 "Q1"~"Q5"，value 為累計收益時間序列 |

---

### 3.6 模組 F：冗餘過濾器 (Redundancy Filter) — 多元化保障

**目標**：確保最終選出的特徵集是「多元化」的，避免 50 個特徵中有 40 個是 EMA 變體。

#### 3.6.1 相關性矩陣計算

**方法**：計算通過 IC 篩選的特徵之間的兩兩 Pearson 相關性。

| 設計項 | 說明 |
|--------|------|
| **計算對象** | 僅對通過 IC/p-value 門檻的特徵計算（非全量） |
| **相關係數類型** | Pearson（線性相關） |
| **效能優化** | 使用 `df.corr()`（底層 NumPy，向量化），O(n²) 但 n < 200 時 < 1 秒 |
| **輸出** | 對稱矩陣 `(n_features × n_features)` |

#### 3.6.2 三階段去重策略

**V0.1 只有簡單的貪婪法，V1 提供三種策略供選擇**：

##### 策略一：貪婪去重 (Greedy Dedup) — 預設

1. 將特徵按 `abs(ICIR)` 降序排列
2. 從排名最高的特徵開始，檢查其與已選特徵的相關性
3. 若與任何已選特徵的 `abs(corr) > threshold`，則剔除該特徵
4. 重複直到所有特徵都檢查完畢

**優點**：簡單、快速、保證保留 ICIR 最高的特徵  
**缺點**：結果依賴排序，可能不是全域最優  
**閾值**：`correlation_threshold = 0.7`（可配置）

##### 策略二：階層聚類 (Hierarchical Clustering)

1. 使用 `1 - abs(corr)` 作為距離矩陣
2. 進行階層聚類（Ward's method 或 Average linkage）
3. 按距離閾值切割樹狀圖，形成聚類
4. 每個聚類中保留 ICIR 最高的代表特徵

**優點**：考慮全域結構，自動確定聚類數  
**缺點**：計算較慢，需要 `scipy.cluster.hierarchy`  
**適用**：特徵數 > 100 時推薦

##### 策略三：VIF 篩選 (Variance Inflation Factor) — 進階

**業界做法**：VIF 是多元回歸中檢測多重共線性的標準工具。

| 步驟 | 說明 |
|------|------|
| 1 | 計算每個特徵的 VIF |
| 2 | 若 VIF > 10（嚴格）或 VIF > 5（寬鬆），該特徵存在嚴重共線性 |
| 3 | 逐一移除 VIF 最高的特徵，重新計算 |
| 4 | 重複直到所有特徵 VIF < threshold |

**優先級**：P2（進階功能，基礎版先用貪婪/聚類即可）

#### 3.6.3 多元化指標 (Diversification Metrics)

**篩選後需報告以下多元化指標**：

| 指標 | 公式 | 良好標準 |
|------|------|---------|
| **平均絕對相關性** | `mean(abs(corr_matrix))` | < 0.3 |
| **最大相關性** | `max(abs(corr_matrix))` | < 0.7 |
| **有效獨立特徵數** | 基於 PCA eigenvalues 估算 | > 0.5 × 總特徵數 |
| **類別覆蓋度** | 選出特徵覆蓋了幾個指標類別 | 至少 3 個類別 |
| **數據源覆蓋度** | 選出特徵覆蓋了幾個數據源 | 至少 2 個數據源 |

---

### 3.7 模組 G：因子換手率分析器 (Turnover Analyzer) — V0.1 缺失

**目標**：評估因子在實際交易中的「換手成本」。業界標準但 V0.1 完全沒有涵蓋的關鍵模組。

#### 3.7.1 業界背景

**換手率 (Factor Turnover)** 是量化基金評估因子實際可交易性的核心指標。即使一個因子有很高的 IC，但如果其 Top/Bottom 分位數的組成每期都大幅變化（高換手），則：
1. 需要頻繁調倉，產生高交易成本
2. 交易成本可能吃掉大部分 Alpha
3. 不適合高手續費市場（如加密貨幣合約）

#### 3.7.2 換手率計算

| 指標 | 公式 | 說明 | 良好標準 |
|------|------|------|---------|
| **分位數換手率** | `(Q5_t ∩ Q5_{t-1}) / |Q5_t|` 的互補 | 頂部分位的成分每期變化比例 | < 30% |
| **排名變化率** | `mean(abs(rank_t - rank_{t-1}))` | 所有因子排名的平均位移 | 越低越好 |
| **因子自相關** | `corr(feature_values_t, feature_values_{t-1})` | 因子值的期間持續性 | > 0.7 |

#### 3.7.3 淨 IC (Turnover-Adjusted IC)

**業界進階做法**：考慮換手成本後的「實際可獲取 IC」。

| 指標 | 公式 | 說明 |
|------|------|------|
| **Gross IC** | 原始 IC（未扣費） | 理論上限 |
| **Turnover Cost** | `turnover_rate × transaction_cost_per_trade` | 換手帶來的成本 |
| **Net IC Proxy** | `Gross IC - λ × Turnover` | 近似淨 IC（λ = Config 中的 `turnover.transaction_cost`，預設 0.001） |

**用途**：在 IC 相近的兩個因子中，優先選擇換手率低的（淨 IC 更高）。

---

### 3.8 模組 H：因子覆蓋率分析器 (Coverage Analyzer) — V0.1 缺失

**目標**：確保選出的因子在大部分時間點都有有效值，避免「稀疏因子」導致模型訓練數據不足。

#### 3.8.1 覆蓋率定義

| 指標 | 公式 | 說明 | 門檻 |
|------|------|------|------|
| **時間覆蓋率** | `count(非NaN) / total_bars` | 因子在時間軸上的有效比例 | > 80% |
| **Cross-Section 覆蓋率** | 在多幣種模式下，同一時刻多少幣種有值 | 因子在橫截面的有效比例 | > 70% |
| **有效起始點** | 因子第一個非 NaN 值出現的位置 | 因子的可用歷史長度 | — |

#### 3.8.2 覆蓋率與 IC 的交叉驗證

**場景**：某個因子 IC 很高但覆蓋率只有 40%（例如只在衍生品數據可用時有值），此時該因子的 IC 可能因為樣本偏差而被高估。

**處理方式**：
- 覆蓋率 < 50% 的因子，IC 報告中標記 `⚠️ Low Coverage` 
- 可選：覆蓋率 < 30% 的因子直接剔除（可配置）
- 報告中顯示「覆蓋率 vs IC」散點圖，協助識別樣本偏差

---

### 3.9 模組 I：IC 篩選協調器 (IC Filter Orchestrator)

**目標**：將以上所有模組串聯為完整的篩選流水線，提供統一的調用入口。

#### 3.9.1 篩選流程

> **編號對齊**：以下步驟編號對應 §2.1 的八階段流水線 (Stage 0-7)。

```
輸入：原始特徵矩陣 (800~15000+) + Labels + Config

Stage 0: 數據載入 + 輸入驗證
    ├── 讀取 features.h5 + meta.json + labels.h5
    └── Schema 驗證（欄位完整性、dtype 檢查、NaN 比例檢查）

Stage 1: 數據預處理
    ├── Winsorization (999 → 800 features，刪除常數特徵)
    └── 覆蓋率初篩 (800 → 750，刪除覆蓋率 < 30% 的)

Stage 2: Label 生成與對齊
    ├── Future Returns 計算（simple/log/excess）
    └── 多 Horizon 對齊（跨 TF 自動換算）

Stage 3: 事件過濾（Event Mode 時啟用）
    ├── Query String → Boolean Mask
    └── 樣本數安全檢查（< 30 → 回退 Global Mode）

Stage 4: IC 計算 (750 features × N horizons)
    ├── Spearman IC Mean / IC Std / ICIR
    ├── p-value / IC Hit Rate
    └── Rolling IC / IC Decay / Grouped IC

Stage 5: 統計驗證 + 門檻篩選
    ├── abs(IC Mean) > 0.02 → 保留
    ├── abs(ICIR) > 0.5 → 保留
    ├── p-value < 0.05 → 保留 (750 → ~150 features)
    ├── Monotonicity Score > 0.6 → 保留
    ├── Long-Short Spread 顯著 → 可放寬 (150 → ~120 features)
    └── Coverage 交叉驗證

Stage 6: 冗餘剔除 + 多元化驗證
    ├── 相關性矩陣計算
    ├── 貪婪去重 (corr_threshold=0.7) → 120 → 50~80 features
    ├── 平均相關性 < 0.3 ✓
    ├── 類別覆蓋 ≥ 3 ✓
    └── 最終特徵集確認

Stage 7: 報告生成 + 持久化
    ├── JSON 結構化報告 (ic_report.json)
    ├── AI 可讀 Markdown 摘要 (ic_summary.md)
    ├── 精選特徵矩陣輸出 (filtered_features.h5)
    └── 篩選日誌 (ic_filter_log.json)

輸出：精選特徵矩陣 (~50-80 features) + 完整報告
```

#### 3.9.2 篩選日誌 (Filter Log)

**每一步記錄**：
- 輸入特徵數 → 輸出特徵數
- 被剔除的特徵列表及原因
- 關鍵閾值與實際分佈統計
- 執行時間

**用途**：可回溯分析為什麼某個特徵被剔除，支援調整閾值重新篩選。

#### 3.9.3 快取策略設計 (Cache Strategy)

**場景**：使用者透過 MCP `refilter(thresholds)` 調整門檻後重新篩選，無需重新從 Stage 0 開始。

| 快取層級 | 快取內容 | 觸發重算條件 | 儲存方式 |
|---------|---------|------------|---------|
| **Stage 4 IC 結果** | 每個特徵的 IC Mean/Std/ICIR/p-value/Rolling IC | 數據變更、Label 變更 | 記憶體 dict + 可選 pickle |
| **Stage 5 單調性結果** | Quantile Returns、Monotonicity Score | 數據變更、分位數設定變更 | 記憶體 dict |
| **Stage 6 相關性矩陣** | 通過門檻的特徵間 corr matrix | 通過門檻的特徵集變更 | 記憶體 numpy array |

**設計要點**：
- `refilter()` 僅重新執行 Stage 5 門檻篩選 → Stage 6 冗餘剔除 → Stage 7 報告，跳過 Stage 0-4
- 快取以 `config_hash` 作為 key，Config 變更時自動失效
- 記憶體優先，大規模分析可選 pickle 持久化

#### 3.9.4 Stage 0 輸入驗證設計

**目標**：防止 Phase 1 Feature Factory 輸出格式不一致導致後續計算錯誤。

| 驗證項 | 檢查內容 | 失敗行為 |
|--------|---------|---------|
| **HDF5 結構** | features.h5 必須包含 float32/float64 數值型 DataFrame | 拋出 `InvalidInputError` |
| **Meta JSON Schema** | meta.json 每個特徵必須有 `name`, `category`, `layer` 欄位 | 缺失欄位填入預設值 + 發出 WARNING |
| **Labels 對齊** | labels.h5 的 index 必須與 features.h5 完全對齊 | 自動取交集 + WARNING |
| **NaN 比例** | 整體 NaN > 90% 的特徵直接剔除 | 記錄至篩選日誌 |
| **資料量** | 總樣本數 < 100 | 拋出 `InsufficientDataError` |

---

## 4. 與 Phase 1 Feature Factory 的深度整合

### 4.1 利用 Feature Metadata 的多維度 IC 分析

Phase 1 的 `meta.json` 為每個特徵提供了豐富的 Metadata，IC 篩選器可以直接利用這些資訊進行多維度分析。

#### 4.1.1 按 Pipeline 層級 (Layer) 的 IC 統計

| Layer | 包含特徵類型 | IC 分析用途 |
|:-----:|------------|-----------|
| Layer 1 | 原子指標 (EMA, RSI, ADX...) | 哪些基礎指標最有預測力？ |
| Layer 2 | 衍生特徵 (Distance, Cross, Momentum) | 哪種算子最能提取 Alpha？ |
| Layer 3 | 滑動聚合 (Slope, Std, Rank...) | 宏觀屬性 vs 當前值，哪個更有效？ |
| Layer 4 | Lag 特徵 | 預測力是否隨 Lag 步數衰減？最佳 Lag 是幾步？ |
| Layer 5 | 橫截面 (CS-Rank, Relative) | 相對值 vs 絕對值，哪個 IC 更高？ |
| Layer 6 | 元特徵 (Consensus, Interaction) | 組合特徵是否比單一指標更有效？ |

**報告輸出**：
```json
{
  "layer_ic_summary": {
    "layer_1_atomic": {"count": 245, "mean_abs_ic": 0.035, "max_ic": 0.12, "pass_rate": "18%"},
    "layer_2_derived": {"count": 200, "mean_abs_ic": 0.042, "max_ic": 0.15, "pass_rate": "24%"},
    "layer_3_rolling": {"count": 300, "mean_abs_ic": 0.028, "max_ic": 0.10, "pass_rate": "12%"},
    "layer_4_lag": {"count": 30, "mean_abs_ic": 0.031, "max_ic": 0.09, "pass_rate": "15%"},
    "layer_6_meta": {"count": 20, "mean_abs_ic": 0.045, "max_ic": 0.11, "pass_rate": "30%"}
  }
}
```

#### 4.1.2 按指標類別 (Category) 的 IC 統計

利用 Metadata 中的 `category` 分類：

| 類別 | 說明 | IC 分析用途 |
|------|------|-----------|
| **trend** | 趨勢指標 (EMA, SMA, KAMA...) | 趨勢因子在當前市場的有效性 |
| **momentum** | 動量指標 (RSI, MACD, CCI...) | 動量因子的預測力排名 |
| **volatility** | 波動指標 (ATR, BB_Width...) | 波動因子的時效性 |
| **volume** | 量能指標 (OBV, ADOSC, Volume_MA_Ratio...) | 量能因子的預測貢獻 |
| **cycle** | 週期指標 (HT_*) | 週期因子的實用性驗證 |
| **pattern** | 型態辨識 (CDL_*) | K 線型態的統計有效性 |
| **statistics** | 統計函式 (LINEARREG, STDDEV...) | 統計特徵的預測力 |

#### 4.1.3 按數據源 (Data Source) 的 IC 統計

利用 Metadata 中的 `data_source` 欄位：

| 數據源 | 範例特徵 | IC 分析用途 |
|--------|---------|-----------|
| `close` | `close_RSI_14`, `close_EMA_21_Distance` | 價格因子的基準預測力 |
| `volume` | `volume_RSI_14`, `volume_EMA_21` | 量能因子是否提供額外資訊？ |
| `taker_ratio` | `taker_ratio_EMA_21`, `taker_ratio_RSI_14` | 買賣力道因子的預測貢獻 |
| `open_interest` | `open_interest_ROC_5` | 衍生品數據的增量價值 |

**關鍵問題**：`volume_RSI_14`（量 RSI）是否比 `close_RSI_14`（價格 RSI）有更高的 IC？這個答案直接影響 Feature Factory 的數據源配置。

#### 4.1.4 Lag 特徵最佳步數分析

Phase 1 的 Lag Features（Layer 4）可能產生大量變體。IC 分析可以精確找出最佳 Lag：

| 分析項 | 說明 | 產出 |
|--------|------|------|
| **Per-Feature Lag IC Curve** | 對每個基礎特徵計算不同 Lag 的 IC | 最佳 Lag 步數 |
| **Average Lag IC Curve** | 所有特徵的平均 Lag IC | 系統級最佳 Lag |
| **Lag IC Heatmap** | (Feature × Lag) 的 IC 熱力圖 | 全域最佳 Lag 模式 |

---

### 4.2 Feature Factory Config 回饋機制

IC 分析的結果可以回饋給 Feature Factory，指導下一輪特徵生成（AutoResearch Loop 的核心）。

| IC 發現 | 回饋 Config 調整 | 說明 |
|---------|----------------|------|
| `volume_*` 因子平均 IC > `close_*` | 增加 volume 數據源的參數密度 | 量因子有價值，加大探索 |
| Layer 2 (衍生) IC 最高 | 增加算子種類 | 衍生算子提取了更多 Alpha |
| Lag_5 是最佳 Lag | 調整 `lag_strategy` 聚焦 Lag 3-8 | 減少無效 Lag 計算 |
| 型態類別 IC 全部 < 0.01 | 關閉 `pattern.enabled: false` | 減少無效特徵 |
| 1h TF 因子 IC 最高 | 增加 1h 特徵的參數擴展 | 更細時間框架更有效 |

**MCP Tool 接口**：
```
IC Gatekeeper → Feature Factory
POST /api/v1/features/config/optimize
body: { ic_report_path: "...", optimization_strategy: "auto" }
→ 自動生成 Config 調整建議
```

---

## 5. 配置與控制策略 (Configuration Strategy)

### 5.1 IC 配置結構 (`config/ic_config.yaml`)

```yaml
# ic_config.yaml — IC 篩選器配置
version: "1.0"

# === 全域設定 ===
global:
  default_method: "spearman"         # pearson | spearman | kendall
  default_horizon: 5                  # 預設 Label Horizon (bars)
  time_duration_mode: false           # true 則使用 "24h"/"3d" 格式

# === Stage 1: 數據預處理 ===
preprocessing:
  winsorization:
    enabled: true
    method: "percentile"              # percentile | mad | zscore | none
    lower_percentile: 1
    upper_percentile: 99
  missing_values:
    max_fill_forward: 3               # Forward Fill 最大期數
    min_coverage: 0.3                 # 覆蓋率 < 30% 直接剔除

# === Stage 2: Label 生成 ===
labels:
  return_type: "simple"               # simple | log | excess | risk_adjusted | winsorized
  horizons: [1, 2, 3, 5, 8, 13, 21]  # 多 Horizon 分析
  horizons_time: null                 # 或 ["6h", "12h", "1d", "2d", "3d", "5d", "10d"]
  winsorize_returns: true             # 對 returns 也做 Winsorize

# === Stage 3: 事件過濾 ===
event_filter:
  enabled: false                      # 預設 Global Mode
  query: null                         # pandas eval() 格式
  # query: "close > open * 1.03"     # 範例：大陽線事件
  min_events: 30                      # 最少事件數
  sample_size_tiers:                  # 樣本數分級
    sufficient: 200
    marginal: 100
    low_confidence: 30

# === Stage 4: IC 計算 ===
ic_calculation:
  methods: ["spearman"]               # 可同時計算多種 ["pearson", "spearman"]
  rolling_windows: [21, 63, 126]      # Rolling IC 視窗大小 (bars)
  rolling_stride: 1                   # Rolling 步進
  ic_decay_horizons: [1, 2, 3, 5, 8, 13, 21]  # IC Decay 分析的 horizons

  # ICIR 計算
  icir:
    window: 63                        # ICIR 的 Rolling Window
    
  # 分組分析
  grouped_analysis:
    by_year: true
    by_quarter: false
    by_regime: true
    by_volatility: true
    by_category: true                 # 使用 Metadata 的 category
    by_data_source: true              # 使用 Metadata 的 data_source
    by_layer: true                    # 使用 Metadata 的 layer
    regime_definitions:
      bull: "close > close_EMA_55"
      bear: "close < close_EMA_55"
      high_vol_percentile: 80
      low_vol_percentile: 20

# === Stage 5: 篩選門檻 ===
thresholds:
  ic_mean_min: 0.02                   # abs(IC Mean) > 0.02
  icir_min: 0.5                       # abs(ICIR) > 0.5
  p_value_max: 0.05                   # p-value < 0.05
  ic_hit_rate_min: 0.55               # IC Hit Rate > 55%
  monotonicity_score_min: 0.6         # 單調性分數 > 0.6
  coverage_min: 0.5                   # 覆蓋率 > 50%

  # Long-Short Spread 可選門檻
  long_short_spread:
    enabled: false                    # 預設不做硬門檻（僅報告）
    min_spread: 0.01                  # 最小多空價差

# === Stage 6: 冗餘剔除 ===
redundancy:
  method: "greedy"                    # greedy | hierarchical | vif
  correlation_threshold: 0.7          # |corr| > 0.7 視為冗餘
  tiebreaker: "icir"                  # icir | ic_mean | monotonicity (保留哪個)
  
  hierarchical:                       # 僅 method=hierarchical 時使用
    linkage_method: "average"         # ward | average | complete
    
  vif:                                # 僅 method=vif 時使用
    max_vif: 10

  # 多元化要求
  diversification:
    min_categories: 3                 # 至少覆蓋 3 個指標類別
    min_data_sources: 2               # 至少覆蓋 2 個數據源
    max_same_category_pct: 0.4        # 同一類別最多佔 40%

# === Stage 7: 換手率分析 ===
turnover:
  enabled: true                       # P1
  transaction_cost: 0.001             # 手續費 (0.1%)
  
# === 報告設定 ===
report:
  top_n_features: 30                  # 報告中詳細列出前 N 個特徵  
  include_decay_analysis: true
  include_quantile_curves: true
  include_correlation_heatmap: true
  include_regime_analysis: true
  include_layer_analysis: true
  include_turnover_analysis: true
  ai_summary: true                    # 生成 AI 可讀 Markdown 摘要

# === 效能設定 ===
performance:
  max_features_for_correlation: 200   # 超過此數量分批計算 corr matrix
  parallel_ic_calculation: true       # 使用多進程加速
  n_jobs: -1                          # 平行計算核心數 (-1=所有)
```

### 5.2 使用者覆寫機制

與 Feature Factory 一致的三層配置優先級：

```
Layer 3: API 即時覆寫 → POST /api/v1/ic/config (最高)
Layer 2: 使用者 Config → config/user_ic_config.yaml
Layer 1: 系統預設 → config/ic_config.yaml (最低)
```

### 5.3 MCP Tools / AI Agent 接口

```
IC Gatekeeper MCP Tools:
├── run_ic_analysis(features_path, labels_path, config_override)
│   → 執行完整 IC 篩選流水線
├── get_top_features(n, horizon, sort_by)
│   → 取得 Top N 特徵（按 IC/ICIR/Monotonicity 排序）
├── get_ic_decay(feature_name)
│   → 取得單一特徵的 IC Decay 曲線
├── get_correlation_matrix(feature_names)
│   → 取得指定特徵的相關性矩陣
├── get_grouped_ic(group_by, feature_names)
│   → 取得分組 IC 統計
├── get_quantile_returns(feature_name, horizon)
│   → 取得單一特徵的分位數收益
├── update_thresholds(partial_config)
│   → 動態更新篩選門檻（AI Agent 迭代用）
├── refilter(thresholds)
│   → 使用新門檻重新篩選（不重新計算 IC）
└── get_filter_log()
    → 取得篩選日誌（每步特徵數變化）
```

**NL2Config 範例**：

| 自然語言 | Config 操作 |
|---------|-----------|
| "只看動量類指標的 IC" | `grouped_analysis.by_category: true` + filter by "momentum" |
| "放寬 ICIR 門檻到 0.3" | `thresholds.icir_min: 0.3` |
| "只分析高波動時期的 IC" | `event_filter.enabled: true`, `event_filter.query: "close_ATR_14 / close > percentile_80"` |
| "用對數收益率重新計算" | `labels.return_type: "log"` |

---

## 6. 完整的 IC 報告規格 (Report Specification)

### 6.1 JSON 報告結構 (`ic_report_{case_id}.json`)

```json
{
  "version": "1.0",
  "generated_at": "2026-02-09T15:30:00",
  "analysis_time_seconds": 4.2,
  
  "metadata": {
    "symbol": "BTCUSDT",
    "timeframe": "12h",
    "mode": "global",
    "event_query": null,
    "sample_size": 1500,
    "sample_size_tier": "sufficient",
    "total_features_input": 832,
    "total_features_output": 62,
    "config_hash": "abc123...",
    "warnings": []
  },
  
  "filter_log": {
    "stage_0_ingestion": {"input": 832, "validated": true, "warnings": []},
    "stage_1_preprocessing": {"input": 832, "output": 780, "removed_reasons": {"constant_feature": 12, "low_coverage": 40}},
    "stage_3_event_filter": {"input": 780, "output": 780, "mode": "global", "events": null},
    "stage_4_ic_calculation": {"input": 780, "computed_metrics": ["spearman_ic", "icir", "rolling_ic", "ic_decay"]},
    "stage_5_statistical_validation": {"input": 780, "output": 152, "threshold": {"ic_mean": 0.02, "icir": 0.5, "p_value": 0.05}, "monotonicity_removed": 24, "post_monotonicity": 128},
    "stage_6_redundancy": {"input": 128, "output": 62, "method": "greedy", "correlation_threshold": 0.7}
  },
  
  "summary_table": [
    {
      "rank": 1,
      "feature_name": "taker_ratio_RSI_14_Slope_W21",
      "category": "momentum",
      "data_source": "taker_ratio",
      "layer": 3,
      "ic_mean": 0.085,
      "ic_std": 0.042,
      "icir": 2.02,
      "p_value": 0.0001,
      "ic_hit_rate": 0.72,
      "rank_ic": 0.082,
      "monotonicity_score": 0.95,
      "long_short_spread": 0.032,
      "coverage": 0.95,
      "turnover_rate": 0.22,
      "ic_half_life": 8.3,
      "peak_horizon": 5,
      "regime_robust": true,
      "physical_meaning": "買賣力道 RSI(14) 在過去 21 根 K 線的線性回歸斜率"
    }
  ],
  
  "ic_decay": {
    "taker_ratio_RSI_14_Slope_W21": {
      "horizons": [1, 2, 3, 5, 8, 13, 21],
      "ic_values": [0.095, 0.090, 0.088, 0.085, 0.070, 0.045, 0.020],
      "half_life": 8.3,
      "peak_horizon": 1,
      "decay_rate": 0.083,
      "decay_type": "exponential"
    }
  },
  
  "quantile_returns": {
    "taker_ratio_RSI_14_Slope_W21": {
      "horizon": 5,
      "num_quantiles": 5,
      "quantile_mean_returns": {"Q1": -0.012, "Q2": -0.003, "Q3": 0.002, "Q4": 0.008, "Q5": 0.020},
      "long_short_spread": 0.032,
      "long_short_tstat": 3.45,
      "monotonicity_score": 0.95,
      "cumulative_returns": {
        "Q1": [0, -0.002, -0.005, -0.008, -0.012],
        "Q5": [0, 0.005, 0.010, 0.015, 0.020]
      }
    }
  },
  
  "grouped_ic": {
    "by_year": {
      "taker_ratio_RSI_14_Slope_W21": {"2023": 0.080, "2024": 0.092, "2025": 0.078}
    },
    "by_regime": {
      "taker_ratio_RSI_14_Slope_W21": {"bull": 0.090, "bear": 0.075, "high_vol": 0.095, "low_vol": 0.060}
    },
    "by_category": {
      "momentum": {"count": 25, "mean_abs_ic": 0.055, "max_ic": 0.085},
      "trend": {"count": 18, "mean_abs_ic": 0.042, "max_ic": 0.072},
      "volatility": {"count": 8, "mean_abs_ic": 0.038, "max_ic": 0.065},
      "volume": {"count": 11, "mean_abs_ic": 0.048, "max_ic": 0.078}
    },
    "by_data_source": {
      "close": {"count": 28, "mean_abs_ic": 0.040},
      "volume": {"count": 15, "mean_abs_ic": 0.045},
      "taker_ratio": {"count": 12, "mean_abs_ic": 0.058}
    },
    "by_layer": {
      "layer_1": {"count": 15, "mean_abs_ic": 0.035},
      "layer_2": {"count": 22, "mean_abs_ic": 0.048},
      "layer_3": {"count": 18, "mean_abs_ic": 0.052},
      "layer_6": {"count": 7, "mean_abs_ic": 0.044}
    }
  },
  
  "correlation_matrix": {
    "features": ["feature_1", "feature_2", "..."],
    "matrix": [[1.0, 0.35, "..."], [0.35, 1.0, "..."]]
  },
  
  "diversification_metrics": {
    "avg_abs_correlation": 0.18,
    "max_correlation": 0.68,
    "effective_independent_features": 45,
    "category_coverage": ["momentum", "trend", "volatility", "volume"],
    "data_source_coverage": ["close", "volume", "taker_ratio"],
    "layer_coverage": [1, 2, 3, 6]
  },

  "rolling_ic_series": {
    "taker_ratio_RSI_14_Slope_W21": {
      "window": 63,
      "timestamps": ["2023-01-01", "2023-01-02", "..."],
      "ic_values": [0.08, 0.09, 0.07, "..."]
    }
  },
  
  "turnover_analysis": {
    "taker_ratio_RSI_14_Slope_W21": {
      "quantile_turnover": 0.22,
      "rank_change_rate": 0.15,
      "factor_autocorrelation": 0.82,
      "net_ic_proxy": 0.078
    }
  }
}
```

### 6.2 AI 可讀摘要報告 (`ic_summary_{case_id}.md`)

**遵循 PRODUCT_VISION.md ADR-002 的 AI 可讀格式要求**：

```markdown
# IC Analysis Summary — BTCUSDT 12h

## Key Findings
- **Top Feature**: taker_ratio_RSI_14_Slope_W21 (ICIR=2.02, Long-Short=3.2%)
- **Best Category**: Momentum (avg |IC|=0.055, 25 features passed)
- **Best Data Source**: taker_ratio (avg |IC|=0.058, outperforms close by 45%)
- **Best Layer**: Layer 3 Rolling Aggregation (avg |IC|=0.052)

## Regime Analysis
- All top 10 features are regime_robust (consistent IC across bull/bear)
- High volatility environment amplifies IC by ~20%

## Recommendations
- Feature Factory Config: increase taker_ratio parameter density
- Optimal prediction horizon: 5 bars (60h)
- Expected model input: 62 features (from 832 raw)

## Risk Warnings
- Pattern features (CDL_*) show negligible IC → recommend disabling
- Layer 4 Lag features show diminishing returns after Lag_8
```

### 6.3 前端圖表數據結構

以下為前端需要渲染的圖表及其數據格式：

| # | 圖表名稱 | 圖表類型 | 數據來源 (JSON key) | 優先級 |
|---|---------|---------|-------------------|:------:|
| 1 | **IC 排名表** | 可排序表格 | `summary_table` | P0 |
| 2 | **IC Decay 曲線** | 折線圖 | `ic_decay` | P0 |
| 3 | **分位數累計收益圖** | 多線折線圖 | `quantile_returns.cumulative_returns` | P0 |
| 4 | **相關性熱力圖** | 色階矩陣 | `correlation_matrix` | P0 |
| 5 | **篩選漏斗圖** | 漏斗圖 | `filter_log` | P0 |
| 6 | **Rolling IC 走勢圖** | 折線圖 + 信帶 | `rolling_ic_series` | P1 |
| 7 | **分組 IC 長條圖** | 分組長條圖 | `grouped_ic.by_category` | P1 |
| 8 | **數據源 IC 比較圖** | 水平長條圖 | `grouped_ic.by_data_source` | P1 |
| 9 | **Pipeline 層級 IC 圖** | 水平長條圖 | `grouped_ic.by_layer` | P1 |
| 10 | **Regime IC 雷達圖** | 雷達圖 | `grouped_ic.by_regime` | P2 |
| 11 | **覆蓋率 vs IC 散點圖** | 散點圖 | `summary_table` (coverage × ic) | P2 |
| 12 | **換手率 vs IC 散點圖** | 散點圖 | `turnover_analysis` × `summary_table` | P2 |

---

## 7. Part B：模型驗證修復 (XGBoost Dashboard Fix)

### 7.1 問題背景

Phase 0 驗證時發現 XGBoost 儀表板部分功能缺失：

| 功能 | 現狀 | 問題描述 |
|------|------|---------|
| **CV AUC Mean** | 顯示 N/A | 交叉驗證 AUC 均值未正確聚合 |
| **CV-OOT Gap** | 顯示 N/A | 缺少 Out-of-Time 驗證數據 |
| **OOT Validation** | 無數據 | 時間窗口切分可能設定錯誤 |
| **PSI Analysis** | 無數據 | Population Stability Index 計算函式可能未被調用 |
| **Fold-level Stability** | 顯示 0 | 每個 fold 的 AUC 分佈未記錄 |
| **Case-level SHAP** | 不可用 | SHAP 計算不支援單案例模式 |
| **Rolling AUC** | 無數據 | 滾動時間窗口 AUC 趨勢未實作 |
| **Strategy Equity Curve** | 無數據 | 需整合回測結果（Phase 5） |

### 7.2 修復策略

| 功能 | 修復方向 | 優先級 | 說明 |
|------|---------|:------:|------|
| **CV AUC Mean/Std** | 修正 CV 指標聚合邏輯 | P0 | 確保每個 fold 的 AUC 正確記錄並聚合 |
| **Fold-level Stability** | 儲存每個 fold 的 AUC | P0 | `fold_aucs: List[float]` 存入結果 |
| **OOT Validation** | 實作 Time-Series Split | P0 | 按時間排序切分，最後 20% 為 OOT |
| **CV-OOT Gap** | 計算 CV AUC - OOT AUC | P0 | Gap > 0.1 發出過擬合警告 |
| **PSI Analysis** | 確認呼叫 + 實作 PSI | P1 | 分佈穩定性檢測（Train vs Test 特徵分佈） |
| **Case-level SHAP** | 擴展 SHAP 為單案例模式 | P1 | `shap.Explanation` 支援顯示單筆預測的解釋 |
| **Rolling AUC** | 實作滾動窗口 AUC | P1 | 類似 Rolling IC 的方法，檢測模型時效性 |
| **Strategy Equity Curve** | 暫不修復 | P2 | 等 Phase 4/5 回測系統完成後整合 |

### 7.3 調查方向

| 調查項目 | 檢查內容 | 預期發現 |
|---------|---------|---------|
| **CV 指標計算** | 檢查 `xgboost_analyzer.py` 的 CV 邏輯 | 可能未 iterate over folds 或未聚合結果 |
| **OOT 數據切分** | 檢查 train/test split 是否 time-aware | 可能使用 random split 而非 time split |
| **PSI 函式** | 搜尋 PSI 相關函式是否存在 | 可能已定義但未被調用 |
| **SHAP 配置** | 檢查 SHAP 計算的樣本數參數 | 可能限制了只取聚合結果 |

### 7.4 OOT 驗證設計

**Out-of-Time (OOT) Validation 是時間序列模型驗證的業界標準**：

| 設計項 | 說明 |
|--------|------|
| **切分方式** | 按時間排序，前 80% 為訓練+CV，最後 20% 為 OOT |
| **CV 方式** | 在前 80% 中使用 Time-Series Split（非 random KFold） |
| **Key Metric** | CV AUC Mean vs OOT AUC |
| **過擬合判定** | Gap = CV AUC - OOT AUC > 0.1 → 警告 |
| **報告內容** | CV AUC（每 fold + mean ± std）、OOT AUC、Gap、OOT Precision/Recall |

### 7.5 PSI (Population Stability Index) 設計

**PSI 用於檢測訓練集和測試集的特徵分佈是否一致**：

| 設計項 | 說明 |
|--------|------|
| **公式** | `PSI = Σ (P_i - Q_i) × ln(P_i / Q_i)`，P=train 分佈，Q=test 分佈 |
| **分箱數** | 10 bins（等頻分箱） |
| **判定標準** | PSI < 0.1 穩定，PSI 0.1~0.25 輕微偏移，PSI > 0.25 顯著偏移 |
| **產出** | 每個特徵的 PSI 值 + 整體 PSI 統計 |
| **用途** | 識別「在訓練集分佈不同於測試集」的特徵 → 可能導致模型泛化差 |

---

## 8. 檔案結構規劃

```
momentum/Analysis/
├── __init__.py
├── ic_filter_orchestrator.py       # 【新增】IC 篩選協調器（八階段流水線）
├── data_preprocessor.py            # 【新增】Stage 1 數據預處理（Winsorization, 缺失值）
├── event_filter.py                 # 【新增】Stage 3 事件過濾（Query 解析, Boolean Mask）
├── ic_engine.py                    # 【新增】Stage 4 IC 核心引擎（IC/ICIR/Rolling/Decay/Grouped）
├── statistical_validator.py        # 【新增】Stage 5 統計驗證（p-value, 信賴區間）
├── monotonicity_tester.py          # 【新增】Stage 5 單調性測試（Quantile, Long-Short）
├── redundancy_filter.py            # 【新增】Stage 6 冗餘過濾（相關性, 聚類, VIF）
├── turnover_analyzer.py            # 【新增】Stage 7 換手率分析（P1）
├── coverage_analyzer.py            # 【新增】Stage 7 覆蓋率分析
├── ic_reporter.py                  # 【新增】Stage 7 報告生成（JSON + Markdown）
│
├── model_validation/               # 【新增】Part B：模型驗證修復
│   ├── __init__.py
│   ├── cv_validator.py             # CV 指標修復（Time-Series Split, Fold AUC）
│   ├── oot_validator.py            # OOT 驗證實作
│   ├── psi_calculator.py           # PSI 分佈穩定性計算
│   ├── rolling_auc.py              # 滾動 AUC 趨勢
│   └── case_shap.py               # 單案例 SHAP 解釋
│
└── ic_config_schema.py             # 【新增】IC Config 的 Pydantic Schema

momentum/FeatureEngineering/labels/
└── label_generator.py              # 【擴展】新增 log returns, excess returns, risk-adjusted

momentum/core/
├── protocols.py                    # 【擴展】新增 IICAnalyzer, ILabelGenerator, ICVValidator Protocol
└── contracts.py                    # 【擴展】新增 ICResult, FilteredFeatureSet 內部 DTO

momentum/factories.py               # 【擴展】新增 create_ic_analyzer(), create_label_generator(), create_cv_validator(), create_psi_calculator()

config/
├── ic_config.yaml                  # 【新增】IC 篩選器預設配置
└── user_ic_config.yaml             # 【新增】使用者覆寫配置（.gitignore）

api/routes/
└── ic_analysis.py                  # 【新增】IC 分析 REST 端點

api/services/
└── ic_analysis_service.py          # 【新增】IC 分析 Service（調用 Factory）

api/models/
└── ic_models.py                    # 【新增】Request/Response Pydantic Models

api/websocket/
└── ic_analysis_ws.py               # 【新增】IC 分析 WebSocket（進度推送）

frontend/src/
├── app/ic-analysis/
│   ├── page.tsx                    # 【新增】IC 分析頁面
│   └── layout.tsx
├── components/ic-analysis/
│   ├── ICConfigPanel.tsx           # 【新增】配置面板
│   ├── ICSummaryTable.tsx          # 【新增】IC 排名表格（可排序/篩選）
│   ├── ICDecayChart.tsx            # 【新增】IC Decay 折線圖
│   ├── QuantileReturnChart.tsx     # 【新增】分位數累計收益圖
│   ├── CorrelationHeatmap.tsx      # 【新增】相關性熱力圖
│   ├── FilterFunnelChart.tsx       # 【新增】篩選漏斗圖
│   ├── RollingICChart.tsx          # 【新增】Rolling IC 走勢圖
│   ├── GroupedICBarChart.tsx       # 【新增】分組 IC 長條圖
│   ├── RegimeRadarChart.tsx        # 【新增】Regime IC 雷達圖
│   └── ExportButtons.tsx           # 【新增】匯出按鈕 (JSON/CSV/PNG)
├── store/
│   └── icAnalysisStore.ts          # 【新增】Zustand Store
└── hooks/
    └── useICAnalysis.ts            # 【新增】Custom Hook
```

---

## 9. 與下游系統的整合

### 9.1 與 Phase 3 LightGBM/XGBoost 的接口

```
IC 篩選器輸出:
  - filtered_features.h5 (~50-80 features, float32)
  - ic_report.json (完整分析報告)
     ↓
Phase 3 輸入:
  - IModelTrainer.train(X=filtered_features, y=label)
  - 利用 ic_report 的 feature_importance 排名做初始化
  - 利用 ic_report 的 physical_meaning 增強 SHAP 解釋性
  - 利用 ic_report 的 regime_analysis 做 Regime-Aware Training
```

### 9.2 與前端 UI 的整合

#### 9.2.1 前端頁面設計

新增 Next.js App Router 頁面 `/ic-analysis`：

```
┌─────────────────────────────────────────────────────────────────┐
│  IC Analysis (Alpha Gatekeeper)                   [分析] [匯出]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─── 左欄：Config 面板 ──────┐  ┌─── 右欄：分析結果 ─────────┐  │
│  │ 📋 分析模式                 │  │                              │ │
│  │ ○ Global ● Event-Driven    │  │  📊 篩選漏斗                  │ │
│  │                             │  │  832 → 780 → 152 → 128 → 62 │ │
│  │ 🎯 事件 Query               │  │  ████████████████░░░░░░░░░░░ │ │
│  │ [close > open * 1.03    ]  │  │                              │ │
│  │                             │  │  📋 Top Features Table        │ │
│  │ ⚙️ 篩選門檻                 │  │  (可排序/篩選/導出)           │ │
│  │ IC Mean: [══●══] 0.02      │  │                              │ │
│  │ ICIR:    [═══●═] 0.5       │  │  📈 IC Decay Chart            │ │
│  │ p-value: [══●══] 0.05      │  │  (選擇特徵 → 顯示 Decay)     │ │
│  │                             │  │                              │ │
│  │ 📏 Horizon                   │  │  📊 Quantile Returns          │ │
│  │ [3] [5] [8] [13] [21]     │  │  (Q1~Q5 累計收益扇形圖)      │ │
│  │                             │  │                              │ │
│  │ 🔗 相關性閾值               │  │  🔥 Correlation Heatmap       │ │
│  │ [═══●═══] 0.7              │  │  (精選特徵相關性)             │ │
│  │                             │  │                              │ │
│  │ 📊 分組分析                  │  │  📊 Grouped IC Bar Charts     │ │
│  │ ☑ 類別 ☑ 數據源             │  │  (by Category/Source/Layer)   │ │
│  │ ☑ Layer □ Regime            │  │                              │ │
│  └─────────────────────────────┘  └──────────────────────────────┘ │
│                                                                 │
│  ┌─── 底部：分析進度 ──────────────────────────────────────────┐  │
│  │ [████████████░░░░░░] 65%  Processing: IC Calculation         │  │
│  │ Stage 4/7 — 計算 152 個特徵的 Rolling IC...                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

#### 9.2.2 後端 API 端點

```
api/routes/ic_analysis.py
api/services/ic_analysis_service.py

端點清單:

# IC 分析（非同步任務）
POST   /api/v1/ic/analyze              → 啟動 IC 分析任務
  body: { 
    features_path: "...", 
    labels_path: "...", 
    config_override: {...}
  }
  response: { task_id: "uuid", status: "running" }

GET    /api/v1/ic/task/{task_id}       → 查詢任務狀態
GET    /api/v1/ic/result/{task_id}     → 取得完整報告 (JSON)
GET    /api/v1/ic/summary/{task_id}    → 取得 AI 摘要 (Markdown)

# IC 查詢
GET    /api/v1/ic/top-features         → Top N 特徵列表
  params: n=30, horizon=5, sort_by=icir
GET    /api/v1/ic/decay/{feature}      → 單一特徵 IC Decay
GET    /api/v1/ic/quantile/{feature}   → 單一特徵分位數收益
GET    /api/v1/ic/correlation           → 相關性矩陣
GET    /api/v1/ic/grouped              → 分組 IC 統計
  params: group_by=category|data_source|layer|regime

# 動態調整
PUT    /api/v1/ic/config               → 更新篩選配置
POST   /api/v1/ic/refilter              → 使用新門檻重新篩選

# 匯出
GET    /api/v1/ic/export/{task_id}     → 匯出精選特徵矩陣 (HDF5)
GET    /api/v1/ic/export-csv/{task_id} → 匯出 IC Summary (CSV)
```

#### 9.2.3 WebSocket 即時通訊

```
WS /ws/ic-analysis/{task_id}
→ 每階段推送:
{
  "stage": 4,
  "stage_name": "IC Calculation",
  "progress": 0.65,
  "message": "Computing Rolling IC for 152 features...",
  "features_remaining": 53
}
→ 完成:
{
  "status": "completed",
  "summary": {
    "total_input": 832,
    "total_output": 62,
    "top_feature": "taker_ratio_RSI_14_Slope_W21",
    "top_icir": 2.02,
    "analysis_time": 4.2
  }
}
```

---

## 10. Protocol 與 Factory 定義

### 10.1 新增 Protocol (`momentum/core/protocols.py`)

> **設計原則**：僅跨 Domain 依賴才放入 `protocols.py`（Rule 2）。模組內部介面定義在各自的模組目錄中。
> **Protocol 總量管控**：現有 3 個 (IKlineReader, IIndicatorEngine, IModelTrainer) + 新增 3 個 = 6 個，低於上限 10。

```
# === 新增至 momentum/core/protocols.py（跨 Domain） ===

IICAnalyzer Protocol:
  - analyze(features: DataFrame, labels: DataFrame, config: dict) → ICReport
  - get_top_features(n: int) → List[FeatureICInfo]
  - get_filtered_features() → DataFrame
  - get_report() → dict

ILabelGenerator Protocol:
  - generate_returns(prices: Series, horizons: List[int]) → DataFrame
  - get_supported_types() → List[str]
  # 說明：擴展 Phase 1 FeatureEngineering 現有的 LabelGenerator 介面，
  #        使 Analysis Domain 可透過 Protocol 注入而非直接 import FeatureEngineering

ICVValidator Protocol:
  - validate(model, X: DataFrame, y: Series) → CVValidationResult
  - get_oot_result() → OOTResult
```

```
# === 模組內部介面（定義在 momentum/Analysis/ 內，不放入 protocols.py） ===

IEventFilter (momentum/Analysis/event_filter.py 內定義):
  - apply_filter(df: DataFrame, query: str) → Tuple[DataFrame, FilterInfo]
  - validate_query(query: str, columns: List[str]) → bool
  # 理由：僅被 IC Filter Orchestrator 在 Analysis Domain 內部使用

IRedundancyFilter (momentum/Analysis/redundancy_filter.py 內定義):
  - filter(features: DataFrame, ic_scores: dict, threshold: float) → DataFrame
  - get_correlation_matrix() → DataFrame
  # 理由：僅被 IC Filter Orchestrator 在 Analysis Domain 內部使用
```

### 10.2 Factory 函式 (`momentum/factories.py`)

```
# 新增 Factory 函式（API Service 調用這些入口）

def create_ic_analyzer(config: Optional[dict] = None) → IICAnalyzer:
    """建立 IC 分析器（主入口）— 內部自行組裝 EventFilter、RedundancyFilter 等模組內部元件"""

def create_label_generator(config: Optional[dict] = None) → ILabelGenerator:
    """建立 Label 生成器"""

def create_cv_validator(config: Optional[dict] = None) → ICVValidator:
    """建立交叉驗證器"""

def create_psi_calculator() → PSICalculator:
    """建立 PSI 計算器"""
```

> **說明**：`EventFilter` 和 `RedundancyFilter` 作為 Analysis Domain 內部元件，由 `create_ic_analyzer()` 內部組裝，不對外暴露獨立 Factory 函式。這符合 Rule 3 的精神 — API Service 只需要知道頂層入口 (`IICAnalyzer`)，不需要了解內部模組結構。

---

## 11. 效能基準與目標

### 11.1 效能目標 (M1 Mac 16GB RAM)

| 操作 | 數據規模 | 目標時間 | 說明 |
|------|---------|---------|------|
| **IC 計算 (全量)** | 200 特徵 × 10K 樣本 | < 2 秒 | Spearman IC |
| **IC 計算 (全量)** | 800 特徵 × 10K 樣本 | < 8 秒 | Spearman IC |
| **Rolling IC** | 200 特徵 × 10K 樣本 × 3 窗口 | < 10 秒 | 三種 Rolling Window |
| **IC Decay** | 200 特徵 × 7 horizons | < 15 秒 | 7 種 Horizon |
| **相關性矩陣** | 200 × 200 | < 1 秒 | pandas corr() |
| **冗餘過濾** | 200 特徵 | < 2 秒 | 貪婪法 |
| **完整分析流程** | 800 特徵 → 62 特徵 | < 30 秒 | 八階段完整 |
| **記憶體峰值** | 800 特徵 × 50K 樣本 | < 2GB | float32 |

### 11.2 效能優化策略

| 策略 | 說明 | 適用場景 |
|------|------|---------|
| **向量化 IC** | 使用 `scipy.stats.spearmanr` 的矩陣版本 | 同時計算所有特徵 |
| **numpy corrcoef** | 底層 C 實作 | 相關性矩陣 |
| **分批計算** | 特徵數 > 200 時分批 | 大規模篩選 |
| **Rolling IC 快取** | 首次計算後快取結果 | 重新篩選時不重算 |
| **float32** | 所有數值用 float32 | 減少記憶體 50% |
| **Numba JIT** | 對不可向量化的 loop | 單調性計算、IC Half-Life 擬合 |

---

## 12. 驗收標準 (Acceptance Criteria)

### 12.1 Part A 功能性驗收 (IC 篩選器)

**核心功能**：
- [ ] **IC 計算**: Pearson 和 Spearman IC 正確計算，與手動驗證一致
- [ ] **ICIR**: ICIR = IC Mean / IC Std 計算正確
- [ ] **Rolling IC**: 三種窗口大小的 Rolling IC 正確生成時間序列
- [ ] **IC Decay**: 多 Horizon IC 正確計算，Half-Life 擬合合理
- [ ] **p-value**: t-test 統計顯著性正確計算
- [ ] **事件過濾**: Query String 正確解析，Boolean Mask 正確生成
- [ ] **樣本數安全**: 事件數 < 30 時自動回退 Global Mode
- [ ] **分位數分析**: Quintile Returns 正確計算，Long-Short Spread 統計檢驗
- [ ] **單調性**: Monotonicity Score 在 0~1 範圍內，與目視驗證一致
- [ ] **冗餘過濾**: 貪婪法正確去重，保留 ICIR 最高者
- [ ] **階層聚類**: 聚類結果合理，每個 cluster 保留代表特徵
- [ ] **多元化指標**: 類別/數據源覆蓋度正確計算
- [ ] **Coverage 分析**: 覆蓋率正確統計，低覆蓋標記
- [ ] **換手率**: Factor Turnover 正確計算

**整合功能**：
- [ ] **Phase 1 整合**: 正確讀取 Feature Factory 的 HDF5 + meta.json
- [ ] **Metadata 利用**: 按 category/layer/data_source 分組分析正確
- [ ] **多 TF 支援**: 多時間框架的 Horizon 對齊正確
- [ ] **Config 三層優先級**: 預設 < 使用者 < API Override 正確
- [ ] **MCP Tools**: 所有 MCP 接口可正確調用

**報告功能**：
- [ ] **JSON 報告**: 結構完整，包含所有分析結果
- [ ] **AI Summary**: Markdown 摘要包含關鍵發現和建議
- [ ] **前端數據**: 所有 12 種圖表的數據格式正確
- [ ] **篩選日誌**: 每步特徵數變化可追溯

### 12.2 Part B 功能性驗收 (模型驗證修復)

- [ ] **CV AUC**: 交叉驗證 AUC Mean ± Std 正確計算
- [ ] **Fold-level**: 每個 fold 的 AUC 可查看
- [ ] **OOT Validation**: Time-based split 正確實作，OOT AUC 合理
- [ ] **CV-OOT Gap**: Gap 指標正確計算，> 0.1 時發出警告
- [ ] **PSI**: 每個特徵的 PSI 正確計算，符合公式定義
- [ ] **Rolling AUC**: 滾動窗口 AUC 趨勢正確
- [ ] **Case SHAP**: 單案例 SHAP 值可正確展示

### 12.3 非功能性驗收

**效能**：
- [ ] IC 計算 200 特徵 × 10K 樣本 < 2 秒 (M1)
- [ ] 完整八階段流程 < 30 秒
- [ ] 記憶體峰值 < 2GB

**品質**：
- [ ] pytest 測試覆蓋率 ≥ 80%
- [ ] 所有函式有 type hints 和 docstring
- [ ] 日誌記錄完整（INFO: 關鍵步驟，ERROR: 含 exc_info）
- [ ] 無 hardcoded 數據

**相容性**：
- [ ] 向後相容：Phase 1 的 Feature Factory 輸出可直接使用
- [ ] 前向相容：輸出格式支援 Phase 3 模型訓練讀取

---

## 13. 實作路線圖 (Implementation Roadmap)

### Phase 2.1：基礎建設 + IC 核心引擎 (Day 1)

1. 建立 `ic_config.yaml` + `ic_config_schema.py`（Pydantic Config Schema）
2. 建立 `data_preprocessor.py`（Winsorization, 缺失值處理, 覆蓋率檢查）
3. 擴展 `label_generator.py`（新增 log returns, excess returns, multi-horizon 對齊）
4. 建立 `ic_engine.py` 核心（Pearson, Spearman, 矩陣版向量化 IC 計算）
5. 實作 ICIR 計算（Rolling Window IC → Mean / Std）
6. 實作 Rolling IC 時間序列（多窗口大小）
7. 實作 IC Decay 分析（多 Horizon + Half-Life 擬合）
8. 建立 `statistical_validator.py`（p-value, t-stat, 信賴區間 — IC Engine 伴隨模組，見 §3.4）
9. 更新 `momentum/core/protocols.py`（新增 IICAnalyzer, ILabelGenerator, ICVValidator 三個跨 Domain Protocol）
10. 更新 `momentum/factories.py`（新增 create_ic_analyzer 等 Factory）

### Phase 2.2：進階分析 + 篩選引擎 (Day 2)

1. 建立 `event_filter.py`（Query String 解析, Boolean Mask, 樣本數安全檢查）
2. 建立 `monotonicity_tester.py`（Quintile Analysis, Long-Short Spread, Monotonicity Score）
3. 建立 `redundancy_filter.py`（貪婪去重, 階層聚類, 多元化指標）
4. 建立 `turnover_analyzer.py`（Factor Turnover, Rank Change, Autocorrelation）
5. 建立 `coverage_analyzer.py`（時間覆蓋率, 有效起始點）
6. 實作分組 IC 分析（by_year, by_regime, by_category, by_data_source, by_layer）
7. 建立 `ic_filter_orchestrator.py`（八階段流水線 + 篩選日誌 + Stage 0 輸入驗證 + 快取策略，見 §3.9.3-3.9.4）
8. 建立 `ic_reporter.py`（JSON 結構化報告 + AI Markdown 摘要）

### Phase 2.3：模型驗證修復 + 整合測試 (Day 3)

1. 建立 `model_validation/cv_validator.py`（Time-Series Split, Fold AUC）
2. 建立 `model_validation/oot_validator.py`（OOT 切分, AUC 計算, Gap 警告）
3. 建立 `model_validation/psi_calculator.py`（PSI 分佈穩定性）
4. 建立 `model_validation/rolling_auc.py`（滾動 AUC 趨勢）
5. 建立 `model_validation/case_shap.py`（單案例 SHAP）
6. 建立 API 端點 + Service（`ic_analysis.py`, `ic_analysis_service.py`）
7. 建立 WebSocket 進度推送
8. 端到端整合測試（Phase 1 Feature Factory → Phase 2 IC Gatekeeper → 輸出）
9. 效能 Profiling（確保 < 30 秒完整流程）
10. 產出驗收報告

---

## 14. 🏗️ 解耦架構檢查清單 (Decoupling Checklist)

**Phase 2 開發完成後必須通過以下全部檢查**：

### Rule 1：momentum/ 不依賴 api/

```bash
grep -r "from api\." momentum/Analysis/ → 必須 0 結果
grep -r "from api\." momentum/Analysis/model_validation/ → 必須 0 結果
```

### Rule 2：跨 Domain 使用 Protocol

- [ ] `IICAnalyzer` Protocol 定義在 `momentum/core/protocols.py`（跨 Domain：API → Analysis）
- [ ] `ILabelGenerator` Protocol 定義在 `momentum/core/protocols.py`（跨 Domain：Analysis → FeatureEngineering）
- [ ] `ICVValidator` Protocol 定義在 `momentum/core/protocols.py`（跨 Domain：API → Analysis）
- [ ] `IEventFilter` 定義在 `momentum/Analysis/event_filter.py` 內部（模組內部，非 Protocol）
- [ ] `IRedundancyFilter` 定義在 `momentum/Analysis/redundancy_filter.py` 內部（模組內部，非 Protocol）
- [ ] Protocol 總量 ≤ 10（現有 3 + 新增 3 = 6）

### Rule 3：API Service 使用 Factory 建構

- [ ] `api/services/ic_analysis_service.py` 使用 `create_ic_analyzer()`
- [ ] 無直接 `ICEngine()` 或 `RedundancyFilter()` 實例化
- [ ] `momentum/factories.py` 已加入所有新 Factory 函式

### Rule 4：Service 間禁止互調

- [ ] `ic_analysis_service.py` 不 import 其他 Service
- [ ] `feature_factory_service.py` 不 import `ic_analysis_service.py`

### Rule 5：Config 單一來源

- [ ] IC 閾值從 `config/ic_config.yaml` 讀取
- [ ] 無 hardcoded 閾值（如寫死 `0.05`）
- [ ] Config Schema 定義在 `momentum/Analysis/ic_config_schema.py`

### Rule 6：Test 配置隔離

- [ ] `pytest tests/momentum/test_ic_engine.py` 可獨立運行
- [ ] `pytest tests/momentum/test_monotonicity.py` 可獨立運行
- [ ] 測試不需要 `run_api.py`

### Rule 7：DTO 不跨層

- [ ] IC 結果返回 dict 或 momentum 內部 DTO（非 api/models/）
- [ ] `api/models/ic_models.py` 僅在 API 層轉換使用

### V2.0/V3.0 相容性

- [ ] **V2.0 Chat**: 支援 "分析 BTCUSDT 的 RSI 特徵 IC" → 自動調用 MCP Tool
- [ ] **V3.0 Agent**: Agent 可自動調整 IC 閾值並迭代篩選
- [ ] **AI 可讀格式**: JSON + Markdown 報告可被 LLM 直接解析

---

## 15. 風險與緩解措施

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|:------:|:----:|---------|
| Event Mode 樣本不足導致 IC 不準 | 中 | 高 | 樣本數安全檢查 + 自動回退 Global Mode |
| IC 篩選過嚴，損失有效特徵 | 中 | 高 | 提供多級門檻，支援動態調整（MCP refilter） |
| 相關性計算效能瓶頸（大特徵集） | 低 | 中 | 分批計算，max 200 特徵/批 |
| 單調性檢查過嚴剔除有效但非線性的因子 | 中 | 中 | Long-Short Spread 可作為替代通過條件 |
| IC Decay Half-Life 擬合失敗 | 低 | 低 | 非指數衰減標記 `non_exponential`，不影響篩選 |
| XGBoost 儀表板修復範圍擴大 | 中 | 中 | 限定 P0 修復項，P1/P2 留待後續 |
| 多 TF Label 對齊錯誤 | 低 | 高 | 單元測試驗證無未來數據洩漏 |
| 報告 JSON 過大影響前端 | 低 | 低 | 曲線採樣 + JSON 壓縮 + 分頁載入 |
| Feature Metadata 缺失或格式不一致 | 中 | 中 | 預設值填充 + 格式驗證 |
| Config 三層合併衝突 | 低 | 中 | 嚴格的 deep merge 策略 + 單元測試 |

---

## 16. 依賴套件 (Dependencies)

### 16.1 必要套件（Phase 2 新增）

```txt
# IC 計算（多數已存在，確認版本）
scipy>=1.10.0             # spearmanr, pearsonr, t-test
pandas>=2.0.0             # DataFrame 操作, eval(), qcut()
numpy>=1.24.0             # 數值計算, corrcoef
scikit-learn>=1.3.0       # hierarchical clustering, VIF
```

### 16.2 確認指令

```bash
# Phase 2 不需要新增套件（scipy, pandas, numpy, scikit-learn 均已在 requirements.txt）
# 驗證版本相容性
pip list | grep -E "scipy|pandas|numpy|scikit-learn"
```

---

## 17. 參考資料 (References)

### 學術文獻

- Grinold, R. C., & Kahn, R. N. (2000). *Active Portfolio Management*. McGraw-Hill. — IC/ICIR 的理論基礎
- Qian, E., Hua, R., & Sorensen, E. (2007). *Quantitative Equity Portfolio Management*. — 因子分析標準流程
- Fama, E. F., & French, K. R. (1993). "Common Risk Factors in the Returns on Stocks and Bonds." — 因子模型經典論文
- Tharp, V. K. (1998). *Trade Your Way to Financial Freedom*. — SQN 與 Expectancy 系統

### 業界工具對標

- **Alphalens (Quantopian)**: IC/Turnover/Quantile Analysis — 本系統功能對標
- **FactorLens**: Rolling IC/Regime IC — 進階分析對標
- **WorldQuant BRAIN**: Alpha 表達式 + IC 篩選流水線 — 整體架構對標
- **Pyfolio**: 績效分析（Phase 5 對標）

### 內部文件

- `docs/Feature Generation Factory.md` — Phase 1 規格（上游接口）
- `docs/IC 篩選 + XGBoost,LightBGM 預測 + Optuna 策略優化.md` — 主架構（Phase 2 章節）
- `docs/IC 篩選器 (The IC Gatekeeper) 進階規劃書.md` — V0.1 規劃（本文件的前身）
- `docs/ARCHITECTURE.md` — 系統解耦架構
- `docs/PRODUCT_VISION.md` — V1/V2/V3 版本演進
