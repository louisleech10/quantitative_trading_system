# 完整地圖 階段一「訊號有效性初探」— Claude 互審綜合（待委員檢查）

> Round 2 草案。四家獨立版(STAGE1-{CLAUDE,CODEX,CURSOR,GEMINI})+ Claude 讀碼定真相後綜合。
> **此綜合本身須交 codex/cursor/Gemini 檢查有無寫錯/遺漏(使用者流程要求),不是定案。**
> 全棧狀態以「後端 / 前端 / 連結」三欄拆解,分歧處註明用哪段程式碼拍板。

## 分歧裁決紀錄（程式碼定真相,非投票）
| 型 | Claude | Gemini | codex | cursor | **裁決(碼證)** |
|---|---|---|---|---|---|
| 1 單標的時序IC | ✅ | ⛓️💥 | ✅ | ✅ | **✅**(useICAnalysis:123-162 global→longitudinal;Gemini 誤判) |
| 2 Rolling IC | ✅ | ✅ | ✅ | ✅ | **✅**(page.tsx:734-737) |
| 3 Pooled IC | ❌ | ❌ | ❌ | ❌ | **❌ 完全缺** |
| 4 symbol一致性 | 🔶/缺 | ✅ | ⛓️‍💥 | 🔌 | **🔌/⛓️‍💥**(orchestrator:379 `_build_cross_symbol_validation` 確算 consistency_score+sign_conflict;Claude 太悲觀、Gemini 太樂觀) |
| 5 橫截面IC | ✅ | ✅ | ✅ | ✅ | **✅(小規模)**;尺度/正確性有洞 |
| 6 case-control | ⛓️/❌ | ⚠️ | ⚠️/❌ | ⛓️‍💥 | **⛓️‍💥+❌**(event_query≠case-control;真套件全缺) |

## 逐型定案（9 欄,全棧拆三欄）

### 1. 單標的時序 IC
- 🔍 單一標的,因子今天值能否預測它自己未來報酬? | 📐 Rank IC 為主,label=forward return(t→t+h) | 🗂 單標的時序
- 📊 現況：global 模式→後端 longitudinal pipeline,`compute_ic` 向量化
- 🧩 **後端 ✅**(ICEngine+stage4) **前端 ✅**(ICConfigPanel+ICSummaryTable) **連結 ✅**(/analyze→/result) → **判定 ✅ 全棧連通(功能層)**;但 ⛓️‍💥 feature_filter 幽靈(前端送 max_features 後端忽略)、主 analyze 同步阻塞(:209-216 無 to_thread)
- 🛡️ label forward shift;**主路徑無 train/test→過擬合洩漏** | ⚡ 欄獨立可串流,現況全量物化 | 🔧 ①無split ②幽靈filter ③大尺度物化 | 🏷️ 高

### 2. Rolling IC / IC 時間序列
- 🔍 預測力穩定還是只在某時段? | 📐 滾動窗 IC 序列+ICIR | 🗂 單標的時序→per-feature 序列
- 📊 `compute_rolling_ic`(:268)+ICIR;前端 RollingICChart(page.tsx:734-737)
- 🧩 **後端✅ 前端✅ 連結✅ → ✅ 全棧連通**;但依賴 #1 全量跑完,且 grouped/decay 崩潰會連帶整 task failed→rolling 也白算
- 🛡️ 窗 left-closed/right-current | ⚡ rolling 產 ranked matrix+corr copy 記憶體更糟→只對 candidates+Welford 摘要 | 🔧 全序列保留炸記憶體;stride/窗邊界一致性待 golden | 🏷️ 中

### 3. Pooled / Panel 時序 IC（普適性）
- 🔍 綜合所有時間+標的,pattern 普遍有效嗎? | 📐 panel 堆疊算一 IC 或 Fama-MacBeth,**pool 前跨 symbol 標準化** | 🗂 Panel(N×T×features)
- 📊 **無此實作**(ic_engine 無 compute_pooled;orchestrator 無 pipeline)
- 🧩 **後端❌ 前端❌ 連結N/A → ❌ 完全缺**
- 🛡️ pool 標準化分位只能 train window | ⚡ N×T×chunk 串流不物化全 panel | 🔧 整個缺;pool vs 逐symbol 聚合語義須定 | 🏷️ 高(普適性護城河,使用者要)

### 4. symbol 一致性 / 普適性分析
- 🔍 IC 每標的都成立還是只在某幾個?(廣度/穩健) | 📐 逐 symbol IC→sign 一致性比例、勝率、離群 | 🗂 N 獨立時序→分布統計
- 📊 orchestrator `_build_cross_symbol_validation(symbol_ic_matrix)`(:379)算 consistency_score/sign_conflict_features;另有 XGB `CrossSymbolValidator`(孤立,ML 不同物)
- 🧩 **後端 🔌**(IC 矩陣版有、XGB 版孤立) **前端 🔌**(CrossSymbolValidationPanel 在深度 Tab,page.tsx:759-761,僅 cross-sectional 自動產) **連結 ⛓️‍💥**(單幣模式完全無一致性視圖;XGB 未接 IC 主流程) → **判定 🔌/⛓️‍💥**
- 🛡️ 同單標的(各自 forward shift) | ⚡ 逐 symbol 串流+聚合標量,輕 | 🔧 單幣模式缺視圖;兩套實作未整合 | 🏷️ 高

### 5. 橫截面 IC
- 🔍 同一時點訊號能否區分多標的誰較強(排序)? | 📐 每時點 rank corr across symbols+ICIR | 🗂 MultiIndex(ts,symbol)面板
- 📊 `analyze_cross_sectional`(每時點 groupby rank corr);前端 mode+批次選+CrossSectionalICHeatmap;本 session 修 cross_sectional_runs wiring
- 🧩 **後端✅ 前端✅ 連結✅(useICAnalysis:168)→ ✅ 全棧連通(小規模)**;⚠️ 大規模 `pd.concat` 全 panel OOM/極慢;**UI 顯示「最多50因子」是前端假估(page.tsx:119-161),後端無硬限→可送 20k 欄**
- 🛡️ return_{i,t+1} 嚴格次期;`_get_time_index` 秒/毫秒 bug 影響時點分組 | ⚡ concat 爆點→timestamp-block 串流 | 🔧 ①concat ②無split ③50因子假篩 ④timestamp bug | 🏷️ 高

### 6. 🎯 事件 / case-control 研究（主戰場）
- 🔍 正向事件**發生前**有無共通先兆(且異於反案例)? | 📐 顯式事件清單[ts,symbol,正/反]+事件前窗對齊+判別指標(AUC/t-stat,非報酬IC)+正反 matching+事件OOS | 🗂 事件清單+每事件前窗切片(稀疏)
- 📊 IC event 模式僅 `EventFilter`(query 篩列);`SignalDensityAnalyzer`/DataExtraction case search 未接成 case-control
- 🧩 **後端 🔌**(EventFilter query 版有;❌無 case 清單輸入、❌IC 管線未調 SignalDensity) **前端 🎨**(Event 模式+query textarea;❌無正反標籤/前窗/匯入 case search UI) **連結 ⛓️‍💥**(兩端有「事件」字眼但語義錯位:UI 稱 Event 實作是全序列子集 IC;真 case-control 在另一套未接) → **判定 ⛓️‍💥 + ❌核心套件全缺**
- 🛡️ 只能用事件前窗,絕不碰事件當下及之後;正反 matching 防 regime 混淆;事件重疊 purge | ⚡ 事件稀疏→列少;重在 430K 欄判別+跨 symbol 事件 pool | 🔧 顯式事件 ingestion/前窗/判別指標/matching/OOS 全缺 | 🏷️ 🎯 絕對優先

## 階段一結論
- **能跑且做對(小規模)**：Rolling IC。
- **能跑但有正確性洞**：單標的時序 IC、橫截面 IC（皆無 train/test;橫截面有 concat/50因子假篩/timestamp bug）。
- **靜默斷裂(最該警覺)**：feature_filter 幽靈(型1)、case-control 語義錯位(型6,主戰場)。
- **部分/缺**：symbol 一致性(🔌 單幣無視圖)、Pooled IC(❌ 完全缺)。

## 待委員檢查(我這份綜合有無寫錯/遺漏)
1. 型4 裁決 🔌/⛓️‍💥 是否準確?consistency_score 是否真做 sign 一致性(我讀 orchestrator:379 + sed 確認有 sign_array/sign_conflict)?
2. 型1 標 ✅(功能層)但列一堆洞——這樣標會不會讓使用者誤以為「沒事」?要不要降級或加紅字?
3. 有無階段一該有、四家都漏的類型?
4. 任何狀態判定與真實程式碼不符之處(請附檔:行反駁)。
