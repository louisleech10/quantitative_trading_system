# 完整地圖 階段一「訊號有效性初探」— 定案版（四家審查已納入）

> Round 3。四家獨立版 → Claude 讀碼綜合 → codex/cursor/Gemini 三家審查(皆 CHANGES,程式碼有檔佐證)→ 本版納入全部修正。
> 三家審查彼此一致互證;待最終 APPROVE 確認。

> ⚠️ **階段一交叉引用註(四家定案)**：光看 IC(相關性)**不足以**證明訊號有效。務必同時檢視**分位/單調性**(階段二:報酬是否隨因子單調遞增,抓非線性 alpha)與**因子自相關/換手率**(階段四:訊號是否翻轉太快、扣成本後無價值)。三者並列才是完整的「有效性」判定。

## 全棧狀態（後端/前端/連結，程式碼定案）
| 型 | 後端 | 前端 | 連結 | 綜合判定 |
|---|---|---|---|---|
| 1 單標的時序IC | ✅ | ✅ | ✅功能層 | **✅功能連通 / ⚠️選因子正確性未過**(無OOS+幽靈filter) |
| 2 Rolling IC | ✅ | ✅ | ✅ | **✅連通,但預設常因 grouped 崩潰白算 + 無OOS** |
| 3 Pooled IC | ❌ | ❌ | N/A | **❌ 完全缺** |
| 4 symbol一致性 | 🔌(IC矩陣版有/XGB孤立) | 🔌(panel在deep tab) | ⛓️‍💥(`deep_analysis_enabled` 門閂擋,多數人看不到;單幣無視圖) | **🔌/⛓️‍💥** |
| 5 橫截面IC | ✅ | ✅ | ✅ | **✅(小規模);大規模OOM+多正確性洞** |
| 6 case-control | 🔌(僅query版;SignalDensity存在未接) | 🎨(僅query textarea) | ⛓️‍💥(event語義錯位+event_timestamps死線) | **⛓️‍💥 + ❌真套件全缺** |

## 逐型定案（9 欄）

### 1. 單標的時序 IC
- 🔍 單一標的,因子今天值能否預測它自己未來報酬? | 📐 Rank IC 為主,label=forward return(t→t+h) | 🗂 單標的時序
- 📊 global→後端 longitudinal(useICAnalysis:164),`compute_ic` 向量化
- 🧩 後端✅ 前端✅ 連結✅ → **✅ 功能連通(功能層)**;⚠️ 副標「功能連通 ≠ 選因子可信」
- 🛡️ **(Gemini)純算 IC 當描述統計不需切分;但一旦用 IC 做特徵篩選/排序→必須 IS/OOS,否則前視偏誤**;幽靈 feature_filter(前端送 useICAnalysis:176→後端 merge:967→ICConfig 無此欄:319→momentum/Analysis 0 處消費)
- ⚡ 欄獨立可串流;現況全量物化;主 analyze 同步阻塞 event loop(:209 無 to_thread) | 🔧 ①無split ②幽靈filter ③物化炸 ④阻塞假死 | 🏷️ 高

### 2. Rolling IC / IC 時間序列
- 🔍 預測力穩定還是只在某時段? | 📐 滾動窗 IC 序列+ICIR | 🗂 單標的時序→per-feature 序列
- 📊 `compute_rolling_ic`(:268)+ICIR;前端 RollingICChart(page.tsx:734)
- 🧩 後端✅ 前端✅ 連結✅ → **✅ 連通**
- 🛡️ 窗應 left-closed/right-current;**(codex/cursor)現況 Spearman rolling 先對全段 rank(ic_engine:288)再 rolling corr→嚴格 PIT 應窗內 rank,否則選因子有前視**
- ⚡ rolling 產 ranked matrix+corr copy 記憶體更糟→只對 candidates+Welford 摘要(待 golden) | 🔧 ①全序列保留炸記憶體 ②**預設 include_regime_analysis=True→grouped 崩潰(GroupedConfig 傳 dict-API,ic_engine:377)→整 task failed→rolling 白算** ③stride/窗邊界一致性待 golden | 🏷️ 中

### 3. Pooled / Panel 時序 IC（普適性）
- 🔍 綜合所有時間+標的,pattern 普遍有效嗎? | 📐 panel 堆疊算一 IC 或 Fama-MacBeth,**pool 前跨 symbol 標準化** | 🗂 Panel(N×T×features)
- 📊 **無此實作**(ic_engine 無 compute_pooled;orchestrator 無 pipeline)
- 🧩 後端❌ 前端❌ → **❌ 完全缺**
- 🛡️ pool 標準化分位只能 train window(防用全序列 mean/std 偷看未來) | ⚡ N×T×chunk 串流不物化全 panel | 🔧 整個缺;pool vs 逐symbol 聚合語義須定 | 🏷️ 高(普適性護城河,使用者要)

### 4. symbol 一致性 / 普適性分析
- 🔍 IC 每標的都成立還是只在某幾個? | 📐 逐 symbol IC→sign 一致性、勝率、離群 | 🗂 N 獨立時序→分布統計
- 📊 orchestrator `_build_cross_symbol_validation`(:379-441):**consistency_score = 0.7·sign_agreement + 0.3·dispersion**(非純 sign 一致);`sign_conflict_features` 才是明確方向衝突偵測;另有 XGB `CrossSymbolValidator`(孤立)
- 🧩 後端🔌 前端🔌 連結⛓️‍💥 → **🔌/⛓️‍💥**:資料進 cross-sectional report(page.tsx:216),但 panel 被 **`deep_analysis_enabled` 門閂擋(page.tsx:193,750-761),一般 cross-sectional 不設此旗標→多數使用者看不到**;單幣模式完全無一致性視圖;XGB 版未接 IC 主流程
- 🛡️ 同單標的(各自 forward shift) | ⚡ 逐 symbol 串流+聚合標量,輕 | 🔧 單幣無視圖;兩套未整合;panel 門閂可見性 | 🏷️ 高

### 5. 橫截面 IC
- 🔍 同一時點訊號能否區分多標的誰較強? | 📐 每時點 rank corr across symbols+ICIR | 🗂 MultiIndex(ts,symbol)面板
- 📊 `analyze_cross_sectional`(每時點 MultiIndex groupby rank corr,:224);前端 mode+批次選+CrossSectionalICHeatmap;本 session 修 cross_sectional_runs wiring(useICAnalysis:168)
- 🧩 後端✅ 前端✅ 連結✅ → **✅ 全棧連通(小規模)**
- 🛡️ return_{i,t+1} 嚴格次期 | ⚡ **`pd.concat` 多 symbol 全 panel→100 symbol OOM**→timestamp-block 串流 | 🔧 ①concat 爆點 ②無split ③**UI「最多50因子」是前端假估(page.tsx:119),後端無硬限→可送 20k 欄** ④**fallback label 固定 return_1 log(ic_analysis_service:1254),與 UI horizons 可能不一致** ⑤summary `p_value:None` 硬寫(:271) | 🏷️ 高
- *(註:timestamp 秒/毫秒 bug 經 codex/cursor 查證屬 grouped/regime 的 `_get_time_index`,**不影響** cross-sectional MultiIndex 分組,已從本型移除→歸 grouped/regime 階段二)*

### 6. 🎯 事件 / case-control 研究（主戰場）
- 🔍 正向事件**發生前**有無共通先兆(且異於反案例)? | 📐 顯式事件清單[ts,symbol,正/反]+事件前窗對齊+判別指標(AUC/t-stat,非報酬IC)+正反 matching+事件重疊 purge+OOS;**(Gemini)43萬欄盲撈必加多重檢定校正(FDR/Deflated Sharpe)防海量偽陽性 + 波動率縮放/扣大盤(否則訊號只是反映全市場波動)** | 🗂 事件清單+每事件前窗切片(稀疏)
- 📊 IC event 模式僅 `EventFilter`(query 篩列,event_filter:73);`SignalDensityAnalyzer`(有定義正反訊號密度分離,signal_density_analyzer:12)**存在但 IC 管線未調用**;DataExtraction case search 在另一套未接
- 🧩 後端🔌(query版;❌case清單;SignalDensity未接) 前端🎨(query textarea;❌正反/前窗/匯入UI) 連結⛓️‍💥(UI稱Event實作是全序列子集IC) → **⛓️‍💥 + ❌真套件全缺**
- 🛡️ 只用事件前窗,絕不碰事件當下及之後;正反 matching 防 regime 混淆;**事件不足時靜默退回全樣本 IC(ic_filter_orchestrator:1085 fallback=True 回全量)=隱性風險**;`event_timestamps` API 收了(ic_models:67)但 orchestrator 硬編 timestamps=None(:1070)=死線 | ⚡ 事件稀疏→列少;重在 430K 欄判別+跨 symbol 事件 pool | 🔧 顯式事件 ingestion/前窗/判別指標/matching/OOS/FDR/vol-adjust 全缺 | 🏷️ 🎯 絕對優先

## 階段一結論（已依審查修正）
- **能跑且做對(小規模)**：橫截面 IC(小規模)。~~Rolling IC~~ **降級**:有實作但**預設路徑常因 grouped 崩潰致整 task 失敗白算,且無 OOS**。
- **能跑但正確性洞**：單標的時序 IC、橫截面 IC、Rolling IC（皆無 train/test;橫截面有 concat/50因子假篩/return_1 label）。
- **靜默斷裂(最該警覺)**：feature_filter 幽靈(型1)、case-control 語義錯位+event_timestamps 死線+事件不足 fallback 全樣本(型6,主戰場)、consistency panel 被 deep_analysis_enabled 門閂(型4)。
- **部分/缺**：symbol 一致性(🔌)、Pooled IC(❌)。
- **橫切隱患(影響多型)**：GroupedConfig 崩潰、materialize OOM、grouped/regime timestamp 秒/毫秒。

## 三家審查共識（除以下一點外全收）
- codex+cursor 的程式碼修正(全段rank PIT、timestamp 歸位、return_1、deep門閂、fallback全樣本、Rolling降級)全部納入。
- Gemini 量化補充(型1洩漏精修、型6 FDR+vol-adjust)全部納入。
- **一個三對一未決**:Gemini 主張「分位/單調性 + 因子自相關」是階段一共主(光看 IC 不夠);codex+cursor 主張屬階段二/三不算階段一缺。→ **建議**:維持 5 階段結構(分位在階段二、自相關/換手在階段四),但階段一加**交叉引用註**「IC 單獨不足以證明有效,分位單調(階段二)與自相關/換手(階段四)為共主效力檢驗」。此為組織/教學取捨,提請使用者校準。
