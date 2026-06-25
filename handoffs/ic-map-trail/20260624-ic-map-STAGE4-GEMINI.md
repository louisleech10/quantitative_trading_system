使用者可稽核：cat .claude/gate/audit.log
# 階段四 — 實戰寫實度 獨立版

### 1. 多空組合報酬/價差 (Long-Short Spread)
1. 🔍核心問題: 訊號是不對稱的嗎？（只做多賺還是只做空賺？）還是多空雙向皆有顯著貢獻？
2. 📐業界標準: 分位組多空價差 (L-S Spread)、T-stat 顯著性、累積淨值曲線 (Equity Curve)。
3. 🗂資料形狀: 包含多空收益時序 (`cumulative_returns` dict)、`long_short_spread` 值與分位平均收益。
4. 📊平台現況+實作(讀碼): 
   - 後端：`momentum/Analysis/long_short_analyzer.py` 處理不對稱性評估；而 `cumulative_returns` 實際在 `monotonicity_tester.py` 計算並隨 `stage5_results` 回傳。
   - 前端：`LongShortComparisonChart`、`FactorEquityCurveChart`。
5. 🧩全棧狀態: ✅後端 / ✅前端 / ⛓️💥連結中斷 / 🔌Deep Module(預設 `not_run`，非主 Gate)。
6. 🛡️PIT洩漏防禦: 必須確保多空分組邊界與收益計算嚴格遵守時間延遲 (shift)，不引入未來價格。
7. ⚡430K×百symbol尺度: `.groupby()` 與累積 `.cumsum()` 操作，在多 symbol 同跑時需確認是否進行跨 symbol rank。
8. 🔧做對沒/漏洞: **重大前端接軌漏洞 ⛓️💥**。與 Stage 2 的分位圖一模一樣，後端在 orchestrator (L1270) 傳遞的是巢狀 `{ quantile_returns: { cumulative_returns: [...] }, monotonicity_score, ... }`，但前端 `FactorEquityCurveChart.tsx` (L51) 期望直讀頂層 `data?.cumulative_returns`。結果導致**靜默空圖**（圖表顯示「暫無累積淨值資料」）。
9. 🏷️優先級: 高 (修正 frontend 解包路徑，只需極少改動即可救回圖表)。

### 2. 換手率/交易成本/Net IC (Turnover/Cost/Net IC)
1. 🔍核心問題: 訊號翻臉比翻書快嗎？扣除手續費與滑價後，IC 還剩下多少（Net IC）？損益兩平點在哪？
2. 📐業界標準: Turnover (換手率)、不同成本情境下的 Net IC 衰減、Breakeven Cost bps (損益兩平點)。
3. 🗂資料形狀: `turnover` 的時序陣列、多情境成本分析 `cost_scenarios` (預設 1/3/5/10/20 bps)。
4. 📊平台現況+實作(讀碼): 
   - 後端：`NetICAnalyzer` (`default_cost_bps=5`, 內建 `breakeven_cost_bps` 算法)、`TurnoverAnalyzer`。公式實作為 `Net IC = Gross IC - (cost_bps / 10000) × Turnover × 2`。
   - 前端：`NetICChart` (泡泡圖) 與 `TurnoverTimeSeriesChart`。
5. 🧩全棧狀態: ✅後端 / ✅前端 / 🔌連結 (此模組為 Deep Module，orchestrator L582 預設為 `"not_run"`，需手動點開)。
6. 🛡️PIT洩漏防禦: Turnover 的定義必須是相鄰期的絕對變動率，需嚴格處理 symbol 切換與 nan padding，避免跨股 diff。
7. ⚡430K×百symbol尺度: Turnover 大量 `.diff().abs()` 對記憶體友善，但要加 `groupby('symbol')` 防護。
8. 🔧做對沒/漏洞: 實作邏輯完整。預設 `cost_bps=5` (0.05%) 符合 Binance 高階 VIP Taker Fee，但對一般散戶來說偏低 (常態為 10 bps)。若不主動展開該 Deep Tab，系統不會在主 Gate 中阻擋高換手廢因子，**高風險因子可能蒙混過關**。
9. 🏷️優先級: 高 (建議將 Breakeven Cost bps 提拔至主要 Summary Table 中作為防禦警示)。

### 3. 流動性/容量/Slippage (Liquidity/Capacity/Slippage)
1. 🔍核心問題: 這個策略能容納一百萬美金還是一億美金？會不會自己把流動性打穿造成嚴重滑價？
2. 📐業界標準: Estimated Capacity USD、Capacity Tier (High/Medium/Low)、Amihud Illiquidity。
3. 🗂資料形狀: `estimated_capacity_usd`, `capacity_tier`、Backtest 的 `commission` 與 `slippage` 參數。
4. 📊平台現況+實作(讀碼): 
   - 並非完全缺漏，而是**散在各處**：
     - `NetICAnalyzer` 中內建了 `estimate_factor_capacity()`，基於 `turnover` 與 `avg_daily_volume_usd` 計算容量 (L90)。
     - Optuna Vectorized Backtest 引擎直接吃 `commission` 與 `slippage` 參數。
     - Feature Factory 有實作 `Amihud Illiquidity Ratio` 作為微觀結構因子。
5. 🧩全棧狀態: 🔌後端部分實作 / ⚠️前端顯示不明顯 / 孤島化。
6. 🛡️PIT洩漏防禦: `avg_daily_volume_usd` 必須是前 N 日的滾動平均，嚴禁用當期總量去推算當期 Capacity。
7. ⚡430K×百symbol尺度: 非常依賴底層報價的 Volume 資料完整性，容易因為山寨幣 Volume 缺失導致估算為 `unknown`。
8. 🔧做對沒/漏洞: `test_no_volume_for_capacity` 顯示當缺乏 Volume 數據時，容量估算會安全退讓為 `unknown`。然而，目前 Capacity 主要包在 `NetICAnalyzer` 的回傳值裡，前端幾乎沒有專屬的大視覺化區塊，容易被忽略。
9. 🏷️優先級: 中 (初期模型驗證時可接受較低優先級，但實盤上線前必須將 Capacity Tier 拉到最前線阻擋假聖杯)。
