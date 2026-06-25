# 階段一 — Antigravity 獨立版

> **備註**：Prompt 說明為「階段二要涵蓋的 4 種分析」，但下方輸出要求寫「逐 6 種分析填 9 欄」。本獨立版遵循範圍定義，精準涵蓋所列出的 **4 種**階段二核心分析，並實際對 repo 程式碼進行驗證。

---

### 1. 分位/單調性分析 (Quantile/Monotonicity Analysis)
1. 🔍 **核心問題（白話）**：特徵值越大，未來的報酬就一定越大嗎？（是單純的線性單調關係，還是 U 型/倒 U 型？）
2. 📐 **業界標準做法**：將特徵按橫截面分 5~10 組（Quantiles），觀察各組未來的平均報酬（Quantile Returns）或累積淨值，並計算首尾組的多空利差 (Long-Short Spread)。
3. 🗂 **資料形狀與輸入**：Cross-sectional (Panel) 較佳，因為需在同一時間點進行排序；若使用單一標的時序做分位數，容易受大盤整體趨勢影響而失真。
4. 📊 **平台現況+實際怎麼實作**：
   - **讀碼查證**：在後端單標的 `analyze()` 模式下，有呼叫 `MonotonicityTester` 實作並算出 `monotonicity_score` 與 `quantile_returns`。
   - **嚴重問題**：在跨標的 pooled 模式（`analyze_cross_sectional()`）中，完全沒有計算，程式碼中將 `monotonicity_score=None` 與 `long_short_spread=None` **硬寫死 (Hardcoded)** 回傳。未實作 Train/Test 切分。
5. 🧩 **全棧實作狀態**：**⚠️有但半殘 (後端跨標的閹割)** + **⛓️💥靜默失效**
   - 前端有 `QuantileReturnChart.tsx`，但跨標的時無數據可用。
   - **幽靈 feature_filter**：前端 `FeatureFilterPanel.tsx` 送出了 `feature_filter`，後端 API (`ic_analysis_service.py:968`) 也嘗試將其塞入 `config_override`，但後端核心 Pydantic schema (`ICConfig`) 完全沒有定義 `feature_filter` 欄位，導致該設定被 Pydantic 默默丟棄，兩端有但完全沒連通。
6. 🛡️ **PIT與洩漏防禦**：最容易踩到「使用全樣本時間算分位數」(Look-ahead bias)。正確做法必須在每一根 K 棒獨立算橫截面分位。且平台無 train/test 分離，結果是在全區間過擬合的。
7. ⚡ **430K×20K×百symbol 尺度對策**：對超大矩陣頻繁做 `.rank()` 或 `.qcut()` 會導致極大記憶體消耗（OOM）。需改用近似分位數演算法 (如 t-digest) 或分 batch 計算。
8. 🔧 **做對沒/漏洞**：跨標的分析直接缺失；沒有 Out-of-sample 驗證。
9. 🏷️ **優先級**：**高**（單調性是特徵進入 ML 模型前的重要門檻）。

---

### 2. IC衰減/半衰期 (IC Decay/Half-life)
1. 🔍 **核心問題（白話）**：這個特徵的預測力能撐多久？（半衰期多長？適合用來做高頻還是波段交易？）
2. 📐 **業界標準做法**：計算特徵對未來 $1, 2, 3, \dots, N$ 期的 IC，畫出 IC 隨 Horizon 遞減的衰減曲線，並用指數衰減模型 (Exponential Decay) 擬合出半衰期。
3. 🗂 **資料形狀與輸入**：特徵矩陣與對應多個 Horizon 的未來報酬矩陣 (Future Returns)。
4. 📊 **平台現況+實際怎麼實作**：
   - **讀碼查證**：單標的 `analyze()` 時，會呼叫 `ic_engine.compute_ic_decay`，計算各期 IC 並擬合出 `half_life`, `peak_horizon`, `decay_rate` 等。
   - **嚴重問題**：在跨標的 pooled 模式（`analyze_cross_sectional()`）中，直接回傳 `ic_half_life=None`，且 `ic_decay={}`。
5. 🧩 **全棧實作狀態**：**⚠️有但半殘 (後端跨標的閹割)**
   - 前端有 `ICDecayChart.tsx`。
   - 後端在跨標的模式下會略過。這與 Prompt 所述「grouped/decay 會崩潰」吻合——因為如果將百個 symbol 的矩陣再複製 shift 7 個 horizon 放進 RAM 算 IC，會直接導致 OOM 崩潰，因此開發者暫時將其閹割。
6. 🛡️ **PIT與洩漏防禦**：計算未來 N 期 Return 時，若遇到除權息或股票分割但未做正確還原 (Adjusted Close)，會產生極大假報酬，導致假 IC 峰值。無 Train/Test。
7. ⚡ **430K×20K×百symbol 尺度對策**：不能在記憶體裡做 dataframe shift 與大矩陣 corr 運算，必須將 shift 計算下放至 DB/Arrow，或是改用 Block chunking 邊讀邊算。
8. 🔧 **做對沒/漏洞**：Cross-sectional 模式下為空殼；記憶體擴展性不足。
9. 🏷️ **優先級**：**高**（決定了預測期的長短及策略能承受的手續費水準）。

---

### 3. 分組/狀態(regime)條件 IC (Grouped/Regime Conditional IC)
1. 🔍 **核心問題（白話）**：這特徵是不是只能在特定的市場環境（如大牛市、高波動）下才有效？
2. 📐 **業界標準做法**：將樣本依據市場狀態 (Regime) 或時間 (Year, Quarter) 切片，分別計算各切片的 IC，觀察 IC 表現的環境抗性與穩定性。
3. 🗂 **資料形狀與輸入**：需額外提供「狀態標籤」 (Regime labels) 或是截取 Timestamp 屬性，搭配特徵與報酬矩陣。
4. 📊 **平台現況+實際怎麼實作**：
   - **讀碼查證**：單標的 `analyze()` 支援 `ic_engine.compute_grouped_ic`，可依 `by_year`, `by_quarter`, `by_regime` 等條件計算。
   - **嚴重問題**：在跨標的 pooled 模式（`analyze_cross_sectional()`）中，再次被硬寫死回傳 `regime_robust=None`, `grouped_ic={}`。
5. 🧩 **全棧實作狀態**：**⚠️有但半殘 (後端跨標的閹割)**
   - 前端備有 `GroupedICBarChart.tsx` 與 `RegimeRadarChart.tsx`。
   - 後端僅支援單標的。因 Pandas 的 `groupby` 在處理 430K×20K 級別資料時效能極差且吃 RAM，大尺度下必崩潰。
6. 🛡️ **PIT與洩漏防禦**：Regime 的劃分極易踩到「未來函數」（例如：事後看整段才知道這是牛市）。必須使用 Rolling lookback 指標（如 MA）來即時判定當下狀態。
7. ⚡ **430K×20K×百symbol 尺度對策**：全面汰換 Pandas 的 in-memory `groupby`，需改用 DuckDB/Polars 這種 out-of-core 的引擎來做聚合運算。
8. 🔧 **做對沒/漏洞**：跨標的未接通；Regime 切分有 look-ahead 風險。
9. 🏷️ **優先級**：**中**（作為進階驗證特徵環境適應性的輔助指標）。

---

### 4. 穩定性/一致性(Win Rate, ICIR) (Stability/Consistency)
1. 🔍 **核心問題（白話）**：這個特徵的預測力是長期持續穩定，還是只是靠少數幾次極端行情賽到的？
2. 📐 **業界標準做法**：計算時序上每一期的橫截面 IC，求出這串 IC 序列的均值 (IC Mean)、標準差 (IC Std)，並計算 Information Ratio (ICIR = Mean / Std)，以及 IC > 0 的比例做為勝率 (Hit Rate / Win Rate)。
3. 🗂 **資料形狀與輸入**：由每期橫截面 IC 所構成的時間序列 (Time-series of cross-sectional ICs)。
4. 📊 **平台現況+實際怎麼實作**：
   - **讀碼查證**：後端 `analyze_cross_sectional` 確實有實作！它對每期 timestamp 做 groupby 計算 `pearson` (rank corr)，再對序列計算 `ic_mean`, `ic_std`, `icir`, `ic_hit_rate`。
   - **事件處理問題**：針對事件過濾，`ic_analysis_service.py` 僅支援 `event_query` 字串，明確拒絕顯式事件清單 (紀錄 `event_timestamps provided but not supported in API yet`)。
5. 🧩 **全棧實作狀態**：**✅全棧連通但暗藏缺陷**
   - 前端有 `ICSummaryTable.tsx` 顯示這些值，後端也確實有算出 pooled 的跨標的 ICIR 與勝率。
   - **缺陷 1**：⛓️💥幽靈 `feature_filter` 讓前端的過濾器失效。
   - **缺陷 2**：顯式事件清單（`event_timestamps`）後端不支援。
6. 🛡️ **PIT與洩漏防禦**：主路徑完全沒有 Train/Test 切分 (Out-of-sample 機制)，算出來的 ICIR 與勝率全是全區間 (In-sample) 的結果，有極嚴重的過擬合風險，實盤一定會打折。
7. ⚡ **430K×20K×百symbol 尺度對策**：目前使用純 Python 對 DataFrame 進行 for loop 的 `groupby` 迭代（`for _, group in grouped:`），在 100 symbol 上速度極慢，缺乏全域的矩陣向量化 (Vectorization) 實作。
8. 🔧 **做對沒/漏洞**：無 Train/Test 機制；顯式事件清單斷鏈；迴圈效能低落。
9. 🏷️ **優先級**：**極高**（這是篩選因子最核心的基石，必須優先重構向量化並加上 OOS）。
