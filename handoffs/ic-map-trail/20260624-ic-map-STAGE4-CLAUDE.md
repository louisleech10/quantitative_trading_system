# 完整地圖 階段四「實戰寫實度」— Claude 獨立版（Round 1）

> 9 欄。階段四問:扣掉手續費/滑價/容量限制後,還賺得到嗎?讀碼查證,wiring 待委員會驗。

## 1. 多空組合報酬 / 價差 (Long-Short Spread)
- 🔍 買訊號前10%、空後10%,報酬曲線長怎樣?賺不賺? | 📐 分位多空組合淨值曲線、Q_top−Q_bottom spread + t-test;cumulative return;**Newey-West t-stat(自相關)** | 🗂 分位分組+報酬;單標的或面板
- 📊 `LongShortAnalyzer`(long_short_analyzer.py);前端 LongShortComparisonChart+FactorEquityCurveChart;orchestrator "long_short_analysis" toggle,可"not_run"(:582)
- 🧩 後端🔌(deep module) 前端🔌(deep tab chart) 連結🔌 → **🔌 deep module/tab**:預設"not_run",非主gate;FactorEquityCurveChart 同型1分位的接錯shape風險(待查)
- 🛡️ 報酬次期;分位邊界train window;無train/test(接階段三型4) | ⚡ 多空只對survivors;分組streaming | 🔧 deep非主流程;DSR未套(海量盲撈最佳spread選擇偏差,接Stage3型8) | 🏷️ 中

## 2. 換手率 / 交易成本 / Net IC
- 🔍 訊號變太快,賺的夠付手續費嗎? | 📐 換手率=相鄰期持倉變動;Net IC=IC扣成本(cost_bps × turnover);多成本情境(1/3/5/10/20bps) | 🗂 持倉時序;cost scenarios
- 📊 `NetICAnalyzer`(net_ic_analyzer.py,default_cost_bps=5,cost_scenarios=[1,3,5,10,20])+`TurnoverAnalyzer`(orchestrator:25,79);前端 TurnoverTimeSeriesChart+NetICChart;toggle "turnover_analysis"/"net_ic_analysis",可"not_run"(:584)
- 🧩 後端🔌(deep module,cost情境完整) 前端🔌(deep tab) 連結🔌 → **🔌 deep module/tab**:預設"not_run"非主gate
- 🛡️ turnover計算用當期持倉不可未來;成本假設須符實際(crypto taker fee) | ⚡ turnover/net_ic輕量;對survivors | 🔧 deep非主流程;成本參數是否符實際市場待查 | 🏷️ 中(高換手因子的關鍵過濾,Gemini階段二也強調)

## 3. 流動性 / 容量 / Slippage
- 🔍 這訊號能容納多少資金不滑價?百symbol下實際下得了單嗎? | 📐 ADV(平均日成交量)占比、容量上限估算、slippage模型(price impact);策略容量 | 🗂 需volume/orderbook;與報酬
- 📊 **未見專門實作**(grep capacity/liquidity/slippage 無 IC 相關命中)
- 🧩 後端❌ 前端❌ → **❌ 完全缺**
- 🛡️ 容量估算用當期流動性不可未來 | ⚡ 對candidates算ADV占比輕 | 🔧 整個缺;crypto有volume但無容量分析 | 🏷️ 中(百symbol實盤可行性,但研究階段可後置)

## 階段四 待委員會詰問
1. long-short/turnover/net_ic 確認都是 deep module/tab(預設not_run)非主gate?
2. NetIC 成本情境是否符 crypto 實際(taker fee/maker rebate)?turnover 定義對嗎?
3. FactorEquityCurveChart 是否同型1分位接錯schema(靜默空圖)?
4. 容量/流動性真的完全缺?還是散在別處(backtest引擎?)
5. 階段四3型有無該加(如 break-even cost、capacity-adjusted IC)?
