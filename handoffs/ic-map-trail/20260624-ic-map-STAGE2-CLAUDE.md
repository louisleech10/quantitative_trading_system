# 完整地圖 階段二「品質、動態與細節」— Claude 獨立版（Round 1）

> 9 欄 schema。讀碼查證;不確定標待查證。待 codex/cursor/Gemini 互審。
> 階段二問:訊號撐多久?線性嗎?挑對環境嗎?穩定嗎?

## 1. 分位 / 單調性分析
- 🔍 特徵值極端大時報酬也極端大嗎?還是中間最好?(抓非線性) | 📐 分 N 分位(5/10),看各組 forward return 單調性 + Top-Bottom spread 顯著性;Rank IC 抓不到的非線性 | 🗂 單標的或面板;分組
- 📊 report `quantile_returns`;前端 QuantileReturnChart(page.tsx:727);MonotonicityTester 存在(待查接法)
- 🧩 後端✅(quantile_returns) 前端✅(QuantileReturnChart) 連結✅ → **✅ 全棧連通(待查 monotonicity 是否真算+顯示)**
- 🛡️ 分組用當期,報酬次期;分位邊界用 train window 不可全樣本 | ⚡ 分組 streaming 可;只對 survivors | 🔧 待查 monotonicity 統計是否完整;大尺度全特徵分組成本 | 🏷️ 高(IC 共主,抓非線性)

## 2. IC 衰減 / 半衰期
- 🔍 訊號發生後撐幾根 bar 才失效?我有多少時間反應? | 📐 多 horizon IC → 指數衰減 fit → 半衰期;低 R2 標非指數 | 🗂 單標的時序;多 horizon
- 📊 `compute_ic_decay`(:331)逐特徵 fit;前端 ICDecayChart(page.tsx:722)
- 🧩 後端✅ 前端✅ 連結✅ → **⚠️ 有但壞掉/拖慢**:per-feature `_fit_exponential_decay` 對 low-R2 每特徵 logger.warning(本次 14090 條,熱迴圈違規拖垮);且 grouped 同 task 崩潰連帶白算
- 🛡️ horizon label 嚴格 forward;不可用未來 fit | ⚡ horizon 合併算不做 horizon×全矩陣;只對 survivors;warning 聚合 | 🔧 ①熱迴圈 log ②逐特徵 Python 迴圈 ③43萬欄 R2≈0 多為雜訊診斷非可行訊號 | 🏷️ 中(現有但壞,需修+scale)

## 3. 分組 / 狀態(regime) 條件 IC
- 🔍 訊號只在多頭/高波動才有效嗎? | 📐 按 regime(牛熊/高低波/年季/category)分組各算 IC;比較條件有效性 | 🗂 面板+regime 標籤
- 📊 `compute_grouped_ic`;前端 GroupedICBarChart+RegimeRadarChart(page.tsx:738,745)
- 🧩 後端✅ 前端✅ 連結✅ → **⚠️ 有但壞掉(本任務核心崩潰)**:orchestrator:1139 傳 pydantic GroupedConfig 給 dict-API(ic_engine:377 config.get)→ AttributeError;`by_volatility` schema 預設 true 但無分支;`_get_time_index` numeric 當 ms(秒則 by_year/quarter 軸錯)
- 🛡️ regime 定義(EMA 等)用當期不可未來;split 內分組防洩漏 | ⚡ group row mask × column chunk,只對 survivors,禁 .loc 全矩陣 | 🔧 ①崩潰 ②by_volatility 缺分支 ③timestamp 秒/毫秒 ④全特徵分組重算 | 🏷️ 中(現有但崩潰,緊急修)

## 4. 穩定性 / 一致性 (Win Rate, ICIR)
- 🔍 IC 是靠某幾天極端拉高,還是每天穩定輸出? | 📐 ICIR(IC mean/std)、hit_rate(IC>0 比例)、rolling IC 離散度 | 🗂 單標的時序→rolling 序列統計
- 📊 `compute_icir`(:304)算 ic_std/hit_rate/icir;`compute_ic_autocorrelation`;前端 summary table 顯示 ICIR(待查 hit_rate 是否顯示)
- 🧩 後端✅(icir/hit_rate) 前端🔶(ICIR 有;hit_rate/穩定視圖待查) 連結🔶 → **✅/🔶(後端有,前端視圖完整度待查)**
- 🛡️ rolling 窗 PIT(接型2 全段 rank 爭議) | ⚡ Welford 串流摘要 | 🔧 依賴 rolling(同型2 grouped 崩潰連帶);hit_rate 前端顯示待查 | 🏷️ 中

## 階段二 待委員會詰問
1. 分位/單調性:MonotonicityTester 有沒有真接進主流程+前端顯示?(我標 ✅ 待查)
2. 穩定性:hit_rate/ICIR 前端到底顯示多少?(🔶 待查)
3. decay/grouped 標 ⚠️崩潰——崩潰是「預設觸發」還是「特定條件」?影響嚴重度標法。
4. 階段二 4 型有無該有卻漏的?(如 drift_analyzer 的因子有效性漂移算不算獨立型?)
5. 任何狀態判定與真實碼不符(附檔:行反駁)。
