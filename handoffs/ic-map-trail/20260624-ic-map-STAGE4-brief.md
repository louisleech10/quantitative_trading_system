# 任務：產出「分析類型地圖 — 階段四」你的獨立完整版（Round 1）
READ-ONLY。產出你自己的階段四完整地圖(獨立)。直接寫輸出。
## 本輪：階段四「實戰寫實度」(扣掉手續費/滑價/容量後還賺嗎?)
### 3 種分析
1. 多空組合報酬/價差 (Long-Short Spread)
2. 換手率/交易成本/Net IC
3. 流動性/容量/Slippage
### 每種寫 9 欄
1.🔍核心問題 2.📐業界標準 3.🗂資料形狀 4.📊平台現況+實作(讀碼) 5.🧩全棧狀態(後端/前端/連結→✅/🔌/🎨/⛓️‍💥/⚠️/❌) 6.🛡️PIT洩漏防禦 7.⚡430K×百symbol尺度 8.🔧做對沒/漏洞 9.🏷️優先級
### 重點查證(wiring)
- LongShortAnalyzer/long_short_analysis、NetICAnalyzer(cost_bps/cost_scenarios)/TurnoverAnalyzer、net_ic_analysis/turnover_analysis toggle:都是deep module/tab(預設not_run)還是主gate?
- FactorEquityCurveChart是否同QuantileReturnChart接錯schema(靜默空圖)?
- 容量/流動性/slippage:真完全缺還是散在backtest引擎?
- NetIC成本情境符crypto實際(taker fee)嗎?turnover定義?
## 使用者:泛用平台、無量化背景、主戰場事件case-control、430K×20K×百symbol。
## 誠實邊界:讀碼欄無法讀則標needs-code-verification。揪⛓️‍💥與🔌孤島。
輸出:標題「階段四—<家族>獨立版」,3型×9欄。後互審+我總結被審。
