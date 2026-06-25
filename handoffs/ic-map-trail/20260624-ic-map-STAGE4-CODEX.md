# 階段四—實戰寫實度獨立版

狀態符號：✅完整可用；🔌後端有但未主流程/未完整接上；🎨前端顯示層；⛓️‍💥接線或語意斷裂；⚠️可用但假設偏弱；❌缺。

## 1. 多空組合報酬/價差 (Long-Short Spread)

| 欄位 | 地圖 |
|---|---|
| 🔍核心問題 | 因子最高分位做多、最低分位做空，是否真的產生穩定價差？多空兩邊是否對稱，還是只靠單邊貢獻？ |
| 📐業界標準 | 應看 top-bottom spread、t-stat、分位單調性、long/short leg 分拆、累積 L/S equity、回撤、換手後淨報酬；事件 case-control 場景還要分事件窗、symbol、regime。 |
| 🗂資料形狀 | 後端主流程：`quantile_returns[feature] = { quantile_mean_returns, long_short_spread, long_short_tstat, cumulative_returns }`。Deep module：`long_short_analysis[feature] = { long_analysis, short_analysis, asymmetry, recommendation }`。 |
| 📊平台現況+實作(讀碼) | 主流程 Stage 5 用 [monotonicity_tester.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/monotonicity_tester.py:15) 產出分位報酬與 `long_short_spread`，並進 summary table。`LongShortAnalyzer` 在 [long_short_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/long_short_analyzer.py:18) 是 deep module，由 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:893) `_run_long_short` 呼叫。 |
| 🧩全棧狀態 | 後端：✅主流程有 spread，🔌LongShortAnalyzer 是 deep module。前端：🎨`QuantileReturnChart` 顯示均值與 spread；🎨`LongShortComparisonChart` 只在 deep tab。連結：⚠️主流程 spread 與 deep LongShort 是兩套語意，使用者可能以為同一件事。 |
| 🛡️PIT洩漏防禦 | 讀碼只看到 feature 與 label 對齊後 dropna；是否 PIT 取決於 upstream label/feature materialization。此模組本身不驗證 label horizon、事件窗邊界、symbol 分離。標記：⚠️needs upstream PIT verification。 |
| ⚡430K×百symbol尺度 | 主流程對每 feature 做 `qcut`、cumsum，可跑但對 20K features × 百 symbol 成本高；deep LongShort 對 selected/top_n 跑，預設 top 30，較可控。若全量 deep 跑 20K，會很重。 |
| 🔧做對沒/漏洞 | 做對：有分位均值、spread、t-stat、cumulative_returns；`FactorEquityCurveChart` 讀 `cumulative_returns`，目前未見 schema 接錯。漏洞：equity curve 是 label cumsum proxy，不扣成本、不按實際持倉/資金/槓桿/容量；LongShortAnalyzer 不產出可交易淨值曲線。 |
| 🏷️優先級 | P0：把「主流程分位 spread」與「deep LongShort leg analysis」在 UI 明確分名。P1：加入成本後 L/S equity、drawdown、per-symbol/event-window split。 |

## 2. 換手率/交易成本/Net IC

| 欄位 | 地圖 |
|---|---|
| 🔍核心問題 | 因子 IC 扣掉換手造成的交易成本後，還有沒有有效訊號？高 IC 是否被高 turnover 吃掉？ |
| 📐業界標準 | 應計算 portfolio/quantile membership turnover、rank autocorrelation、成本情境、gross vs net IC 排名穩定性、breakeven cost、net factor return；成本需符合市場實際 fee/slippage。 |
| 🗂資料形狀 | 主流程：`turnover_analysis[feature] = { quantile_turnover, rank_change_rate, autocorrelation, time_series }`。Deep：`net_ic_analysis = { features: { gross_ic, net_ic, turnover, cost_bps, profitable_after_cost, breakeven_cost_bps, cost_sensitivity, capacity }, summary }`。 |
| 📊平台現況+實作(讀碼) | `TurnoverAnalyzer` 在 [turnover_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/turnover_analyzer.py:14) 是主流程 Stage 5，每次 IC analyze 都算。`NetICAnalyzer` 在 [net_ic_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/net_ic_analyzer.py:17) 是 deep module，由 `_run_net_ic` 從主報告讀 `summary_table` + `turnover_analysis`。 |
| 🧩全棧狀態 | 後端：✅Turnover 主流程；🔌Net IC deep module。前端：🎨Turnover chart 放 deep tab 但讀 `report.turnover_analysis`；🎨NetICChart 讀 `deepAnalysisReport.net_ic_analysis`。連結：⛓️‍💥Turnover toggle 是 stage override，但 UI 顯示被 deep tab 包住；關掉 deep 可能看不到主流程已有 turnover。 |
| 🛡️PIT洩漏防禦 | Turnover 目前是單一 feature time-series 的 top quantile mask 變化，不是橫截面投組成分 turnover；PIT 風險較低，但語意可能錯。Net IC 取 `ic_mean` 與 turnover proxy，沒有檢查交易發生時點、rebalance lag、事件後可交易性。 |
| ⚡430K×百symbol尺度 | Turnover `compute_all(features_df)` 對全 feature 跑 `qcut`、rank、time_series；20K features 會產生大量 arrays，記憶體/輸出壓力高。Net IC 只對 selected/top_n deep features，較可控。 |
| 🔧做對沒/漏洞 | 做對：Net IC 公式 `gross_ic - cost_bps/10000 * turnover * 2`、cost scenarios、breakeven cost 已有。漏洞：`slippage_bps` 在 config schema 有，但 `NetICAnalyzer` 沒讀用；前端成本下拉硬編 `[1,3,5,10,20]`，不讀後端 scenarios；crypto taker fee 常見約 5-10 bps 單邊，現預設 5 bps 且未加 slippage，偏樂觀。Turnover 定義不是 portfolio turnover。 |
| 🏷️優先級 | P0：修正/標明 turnover 定義。P0：Net IC 納入 `slippage_bps` 或改名為 fee-only。P1：前端成本情境從後端資料動態讀。 |

## 3. 流動性/容量/Slippage

| 欄位 | 地圖 |
|---|---|
| 🔍核心問題 | 訊號放大到真實資金後，是否因成交量不足、市場衝擊、滑價、費率而失效？430K×20K×百symbol 下哪些因子只是在小容量假設下好看？ |
| 📐業界標準 | ADV/quote volume、participation rate、spread、order book depth、market impact model、slippage curve、capacity estimate、capacity-adjusted net return；crypto 還要 maker/taker、funding、不同交易所 liquidity。 |
| 🗂資料形狀 | 目前沒有獨立 liquidity/capacity/slippage analysis report。Net IC feature 裡可有 `capacity = { estimated_capacity_usd, capacity_tier }`，但只有當 `avg_daily_volume_usd` 被傳入 metric 時才有數值。Backtest engine 有 `commission`、`slippage` scalar。 |
| 📊平台現況+實作(讀碼) | `NetICAnalyzer.estimate_factor_capacity()` 有容量估算，但 `_run_net_ic` 只傳 `summary_table` 的 `ic_mean`，未傳 volume，所以 capacity 多半 `unknown`。Strategy backtest 在 [vectorized_backtest.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Strategy/vectorized_backtest.py:41) 有固定 commission/slippage，optimization service 可傳 objective config。 |
| 🧩全棧狀態 | 後端：🔌容量函式存在但 IC pipeline 無 volume wiring；🔌backtest 有 scalar slippage。前端：⚠️types 有 capacity 欄位，但 `NetICChart` 不展示容量。連結：⛓️‍💥IC Gatekeeper 與 backtest 成本/滑價是兩個孤島。完整 liquidity/capacity/slippage：❌。 |
| 🛡️PIT洩漏防禦 | 缺完整實作。若未來接 volume，必須用當期以前可見 volume/ADV，不能用未來全樣本均值；事件 case-control 需避免用事件後流動性改善/惡化回填容量。 |
| ⚡430K×百symbol尺度 | 容量分析需要 per-symbol volume/quote volume 或 order book 聚合。若只用 scalar cost 可便宜但失真；若接 full liquidity tensor，需要分 symbol chunk、摘要化輸出，避免 20K features × time × symbol 全量回傳前端。 |
| 🔧做對沒/漏洞 | 做對：backtest 至少扣固定 commission/slippage；Net IC API 形狀預留 capacity。漏洞：IC 階段沒有真實流動性資料 wiring；slippage_bps schema 未用；無 spread/depth/participation 實測；容量 tier 只按 turnover 門檻，不按真正市場容量。 |
| 🏷️優先級 | P0：標記 UI「容量/滑價未完整支援」。P1：把 Feature/label 對應 symbol 的 quote volume/ADV 接入 Net IC。P1：統一 IC 與 backtest 的 fee/slippage config。P2：order-book/depth-based slippage。 |

## Wiring 查證結論

- `LongShortAnalyzer/long_short_analysis`：deep module，不是主 gate；主 gate 另有 Stage 5 `long_short_spread` proxy。
- `TurnoverAnalyzer/turnover_analysis`：主流程 Stage 5 會跑；但前端 Turnover 時序目前放在 deep tab，造成「主流程資料被 deep UI 包住」的語意斷裂。
- `NetICAnalyzer/net_ic_analysis`：deep module，依賴主流程 `turnover_analysis`；預設 IC analyze 不跑 deep，`ICAnalyzeRequest.deep_analysis=False`。
- `FactorEquityCurveChart`：目前讀 `quantile_returns.cumulative_returns`，後端有產出；未見同 `QuantileReturnChart` 接錯 schema 的證據。問題是它不是成本後真 equity。
- 容量/流動性/slippage：不是完全沒有字樣，但完整分析缺。容量散在 NetICAnalyzer 且 volume 沒接上；slippage 散在 backtest scalar，未接 IC Gatekeeper。

## 互審+我總結被審

互審重點：
- 最危險的 ⛓️‍💥 是「Turnover 主流程已算，但 UI 深度 tab 才看得到」。
- 最危險的 🔌 是「Net IC 有 schema/公式，但 `slippage_bps` 沒進公式，capacity 沒 volume」。
- 最容易誤導泛用使用者的是「Equity Curve」命名，因為它看起來像真策略淨值，實際是分位 label 累積 proxy。

我的總結：
階段四目前是「研究診斷雛形」，不是「實戰可交易驗證」。Long/Short 與 Turnover 有可用基礎，Net IC 有框架但成本模型偏簡化；容量/流動性/滑價尚未形成完整全棧能力。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md；以 rg/sed 查證 LongShort/Turnover/NetIC analyzer、IC orchestrator、API models、前端 store/page/chart/types、backtest slippage。
TESTS_RUN: read-only 任務；未跑 pytest/build。查證命令為 `rg`/`sed`，無寫入。
FAILURES_SEEN: `rg` 首次輸出過大被截斷，後續改用定向讀碼解決。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none，未改 code/schema。
HANDOFF_NOT_UPDATED: sandbox 為 read-only，且本任務明示 READ-ONLY。
STATUS: DONE