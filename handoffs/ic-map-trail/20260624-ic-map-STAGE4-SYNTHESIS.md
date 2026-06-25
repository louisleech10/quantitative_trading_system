# 完整地圖 階段四「實戰寫實度」— Claude 互審綜合（待委員檢查）

> Round 2 草案。四家獨立版 + Claude 讀碼。codex+cursor 程式碼一致。**須交三家檢查。**

## 全棧狀態總表
| 型 | 判定 | 一句話 |
|---|---|---|
| 1 多空組合報酬/價差 | **⛓️‍💥/🔌** | 主流程有spread進summary+deep LongShortAnalyzer,但①QuantileReturnChart schema嵌套vs扁平→靜默空圖②主(Qmax−Qmin)vs deep(Q4+5vsQ1+2)定義不一致③thresholds預設關④cross-sectional null;equity curve是cumsum proxy不扣成本 |
| 2 換手/成本/Net IC | **✅Turnover主流程(但toggle幽靈) + 🔌Net IC deep** | Turnover永遠算(turnover.enabled不gate,:1175幽靈)但圖在deep tab;Net IC公式heuristic;**crypto成本5bps偏樂觀(實~20bps+)**;slippage_bps config未讀(幽靈) |
| 3 流動性/容量/Slippage | **🔌/❌** | estimate_factor_capacity骨架存在但_run_net_ic無volume→capacity"unknown";backtest有slippage但與IC孤島;完整❌ |

## 逐型定案（9 欄）

### 1. 多空組合報酬 / 價差 (Long-Short Spread)
- 🔍 買訊號前10%空後10%,報酬曲線?賺不賺? | 📐 分位多空淨值+spread t-test;**Newey-West(自相關)**;cumulative return | 🗂 分位+報酬;主流程quantile_returns含cumulative_returns
- 📊 **雙軌**:(A)主流程`MonotonicityTester.compute_long_short_spread`→summary_table.long_short_spread(high_mean−low_mean)+quantile_returns巢狀;(B)deep `LongShortAnalyzer`(long_quantiles=[4,5]/short=[1,2],asymmetry/recommendation,可"not_run":582);前端QuantileReturnChart(basic)、FactorEquityCurveChart+LongShortComparisonChart(deep tab)
- 🧩 **後端✅(主+deep) 前端🎨 連結⛓️‍💥** → **⛓️‍💥/🔌**:①`report.quantile_returns[feat]`巢狀{quantile_returns:{...},monotonicity_score,long_short}但QuantileReturnChart期望頂層quantile_mean_returns→**basic/deep圖可能靜默空圖**(階段二confirmed同病);②主spread(Qmax−Qmin)vs deep(Q4+5vsQ1+2)**定義不一致**;③`thresholds.long_short_spread`預設關;④LongShortComparisonChart需手動跑深度分析;⑤cross-sectional全欄long_short_spread:null
- 🛡️ 報酬次期;分位邊界train window;無train/test(接階段三型4) | ⚡ 主流程每feature qcut+cumsum,20K×百symbol重;deep對top30較可控 | 🔧 ①schema空圖 ②主/deep定義不一致 ③equity curve是label cumsum proxy**不扣成本/持倉/槓桿/容量** ④cross-sectional缺 ⑤DSR未套(海量最佳spread選擇偏差,接Stage3型8) | 🏷️ 高(wiring bug讓主UI可能看不到分位圖,無量化背景會以為「因子沒用」)

### 2. 換手率 / 交易成本 / Net IC
- 🔍 訊號變太快,賺的夠付手續費嗎? | 📐 換手率=相鄰期持倉變動;Net IC=IC扣成本;多成本情境;**標準組合turnover(非單變量flip)** | 🗂 持倉時序;cost scenarios
- 📊 **Turnover主流程**`TurnoverAnalyzer.compute_all`(turnover_analyzer:14,Stage5**無條件執行未檢查enabled**:1175)=quantile_turnover(頂分位membership diff.abs.mean)+rank_change_rate+autocorrelation+time_series;**Net IC deep**`NetICAnalyzer`(net_ic_analyzer:17,default_cost_bps=5,cost_scenarios=[1,3,5,10,20])`_run_net_ic`讀summary_table.ic_mean+turnover_analysis,輸出gross_ic/net_ic/breakeven_cost_bps/cost_sensitivity/capacity;net_ic=gross_ic−(cost_bps/10000)×turnover×2
- 🧩 **後端✅Turnover主流程/🔌Net IC deep 前端🎨 連結🔌/⛓️‍💥** → ①Turnover永遠算但**`turnover.enabled` toggle不gate計算(幽靈,:1175)**;②前端TurnoverTimeSeriesChart在deep tab(featureToggles.turnover_analysis控顯示)→**關掉deep可能看不到主流程已算的turnover**;③ICSummaryTable有turnover_rate✅;④Net IC在deep報告須兩步;⑤cross-sectional turnover ❌
- 🛡️ turnover用當期持倉不可未來 | ⚡ Turnover對每欄qcut+diff,430K**線性爆炸**;Net IC對deep survivors輕 | 🔧 ①turnover定義非標準組合turnover(單變量頂分位flip rate) ②**Net IC公式量綱heuristic非嚴謹factor portfolio net return** ③**crypto成本預設5bps偏樂觀(Binance taker~10bps/leg,round-trip~20bps+)** ④slippage_bps:2 config存在但NetICAnalyzer未讀(幽靈) ⑤turnover.enabled假開關 | 🏷️ 高(高換手是實戰淘汰主因;成本需crypto校準;turnover應進主gate預設展示)

### 3. 流動性 / 容量 / Slippage
- 🔍 訊號放大到真實資金後,因成交量不足/市場衝擊/滑價/費率失效?哪些因子只在小容量假設下好看? | 📐 ADV占比、容量上限、price impact/slippage模型;策略容量 | 🗂 需volume/orderbook+報酬
- 📊 `NetICAnalyzer.estimate_factor_capacity()`**容量函式存在**,但`_run_net_ic`只傳ic_mean**未傳volume→capacity多半"unknown"**;Strategy backtest(vectorized_backtest:41)有固定commission/slippage,但與IC pipeline孤島
- 🧩 **後端🔌(容量函式存在無volume wiring/backtest有scalar slippage) 前端⚠️(types有capacity欄但NetICChart不展示) 連結⛓️‍💥(IC Gatekeeper與backtest成本是兩孤島)** → **🔌/❌ 完整liquidity/capacity/slippage缺**
- 🛡️ 容量用當期以前可見volume/ADV不可未來;事件case-control避免用事件後流動性回填 | ⚡ 對candidates算ADV占比輕 | 🔧 ①volume未餵入→capacity unknown ②backtest成本孤島 ③完整容量分析缺 | 🏷️ 中(百symbol實盤可行性,研究階段可後置)

## 階段四結論
- **靜默空圖延燒**:QuantileReturnChart schema 問題(階段二)也讓階段四的分位/多空圖空圖(型1)。
- **假開關**:turnover.enabled 不 gate 計算(型2)、slippage_bps config 未讀(型2)——又兩個幽靈。
- **成本假設不符 crypto 實際**:預設 5bps 偏樂觀,實際 round-trip ~20bps+,會高估 Net IC(型2)。
- **可見性斷裂**:turnover 主流程已算但圖被 deep tab 包住,關深度分析看不到(型2)。
- **孤島**:容量函式存在但無 volume(型3)、backtest 成本與 IC 兩套未接(型3)。
- **定義/公式不嚴謹**:主vs deep spread 定義不一致(型1)、Net IC 量綱 heuristic(型2)、turnover 非標準組合 turnover(型2)。

## 待委員檢查
1. turnover.enabled 假開關(orchestrator:1175 無條件 compute_all)屬實?
2. crypto 成本 5bps 偏樂觀、slippage_bps 未讀——屬實?
3. capacity estimate_factor_capacity 存在但 volume 未餵→unknown,屬實?
4. 階段四3型有無該加(break-even cost已在Net IC;capacity-adjusted IC?)
5. 狀態與真實碼不符處(附檔:行)。
