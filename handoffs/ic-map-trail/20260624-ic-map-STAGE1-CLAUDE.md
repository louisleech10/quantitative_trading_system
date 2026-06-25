# 完整地圖 階段一「訊號有效性初探」— Claude 獨立版（Round 1）

> 9 欄 schema（SCOPE-FINAL）。讀碼查證現況；不確定處標「待查證」供委員會詰問。本版待 codex/cursor/Gemini 互審。

## 1. 單標的時序 IC
- 🔍 核心問題：單一標的,因子今天的值能否預測它自己未來報酬?
- 📐 業界標準：Spearman(Rank) IC 為主(穩健抗離群)、Pearson 次之;label=forward return(t→t+h)。
- 🗂 資料形狀：單標的時序(1 symbol × T rows × features)。
- 📊 平台現況：global 模式;`ic_engine.compute_ic`(向量化 fast path);run 選擇器選單 run。
- 🧩 全棧狀態：✅ 全棧連通（後端 compute_ic、前端 global 模式+ICSummaryTable、wiring 經 config_hash 已通）。
- 🛡️ 洩漏防禦：label 必 forward shift(t+h),不可用未來;**但主路徑無 train/test 切分→選因子即在全樣本,過擬合風險**。
- ⚡ 大尺度：欄獨立可分塊串流;exact Spearman 每欄 rank(O(T log T))。
- 🔧 漏洞：①無 train/test(I 階段紅線) ②大尺度全量物化(見 CONVERGED.md)。
- 🏷️ 優先級：高(基礎,但正確性洞需 I1 補)。

## 2. Rolling IC / IC 時間序列
- 🔍 核心問題：預測力是穩定的,還是只在某些時段有效?
- 📐 業界標準：滾動窗 IC 序列 + ICIR(mean/std);觀察衰退/不穩。
- 🗂 資料形狀：單標的時序;輸出 per-feature 時間序列。
- 📊 平台現況：`compute_rolling_ic`(:268)+`compute_icir`;前端 RollingICChart。
- 🧩 全棧狀態：✅ 全棧連通（後端+RollingICChart+wiring）。
- 🛡️ 洩漏防禦：窗 left-closed/right-current,禁 centered window。
- ⚡ 大尺度：**現況 rolling 產 ranked matrix+corr copy,記憶體比原矩陣更糟**→只對 candidates 算全序列,Stage A 用 Welford 摘要(待 golden)。
- 🔧 漏洞：全特徵全序列保留=記憶體炸;stride/窗邊界一致性待 golden。
- 🏷️ 優先級：中(現有,需 scale 化)。

## 3. Pooled / Panel 時序 IC（多 symbol 普適性）
- 🔍 核心問題：綜合所有時間+標的,這 pattern 是否普遍有效(非單一幣巧合)?
- 📐 業界標準：把 N symbol 的(feature,label)堆成 panel 算一個 IC;或 Fama-MacBeth。**pool 前須跨 symbol 標準化(尺度不同)**。
- 🗂 資料形狀：Panel(N symbol × T × features)堆疊。
- 📊 平台現況：**無此模式**。global=單 symbol、cross_sectional=每時點跨 symbol 排名(不同問題)。
- 🧩 全棧狀態：❌ 完全缺（前後端皆無）。
- 🛡️ 洩漏防禦：pool 標準化分位只能 train window;不可跨 symbol 用未來。
- ⚡ 大尺度：N×T×chunk_cols 串流;不物化全 panel。
- 🔧 漏洞：缺(待建)。pool vs 逐symbol 聚合語義須定義。
- 🏷️ 優先級：高(普適性是泛用平台護城河,使用者明確需要)。

## 4. symbol 一致性 / 普適性分析
- 🔍 核心問題：IC 是每個標的都成立,還是只在某幾個?(廣度/穩健)
- 📐 業界標準：逐 symbol 各算 IC,看正負方向、勝率(% symbol IC>0)、離群 symbol、IC 分布。
- 🗂 資料形狀：N 個獨立單標的時序 → 聚合成分布統計。
- 📊 平台現況：**無專門功能**。可手動 global 跑 N 次自己比;`cross_symbol_validator` 是 ML 跨標的訓練(不同物)。
- 🧩 全棧狀態：🔶 部分/近乎缺（無一致性統計 UI/後端聚合）。
- 🛡️ 洩漏防禦：同單標的時序(各自 forward shift)。
- ⚡ 大尺度：逐 symbol 串流 + 聚合標量,輕。
- 🔧 漏洞：缺聚合層(勝率/分布/離群偵測)。
- 🏷️ 優先級：高(與 pooled 互補:pooled 看總體、一致性看離散,防「被一個 symbol 拉高」)。

## 5. 橫截面 IC
- 🔍 核心問題：同一時間點,訊號能否區分多標的中誰未來較強(排序)?
- 📐 業界標準：每時點 rank corr(feature_{i,t}, return_{i,t+1}) across symbols;序列平均 + ICIR。
- 🗂 資料形狀：MultiIndex(timestamp, symbol)面板,每時點一個 cross-section。
- 📊 平台現況：cross_sectional 模式;`analyze_cross_sectional`(每時點 groupby rank corr);前端 CrossSectionalICHeatmap;**本 session 已修 cross_sectional_runs wiring**。
- 🧩 全棧狀態：✅ 全棧連通（後端+前端 heatmap+wiring;惟下方漏洞）。
- 🛡️ 洩漏防禦：return_{i,t+1} 嚴格次期;不可混入 t 的未來。
- ⚡ 大尺度：**現況 `pd.concat(frames)` 多 symbol→100 symbol 災難乘 100**;改 timestamp-block 串流(見 CONVERGED A5)。
- 🔧 漏洞：①concat 爆點 ②無 train/test ③`_get_time_index` 秒/毫秒 bug 影響時點分組。
- 🏷️ 優先級：高(現有但 scale+正確性需修)。

## 6. 🎯 事件 / case-control 研究（主戰場）
- 🔍 核心問題：自訂正向事件**發生前**,是否存在共通特徵先兆(且與反案例不同)?
- 📐 業界標準：case-control 設計——顯式事件清單[timestamp,symbol,label∈{正,反}] + 事件前窗(T-k→T-1)對齊;判別指標(正反分離:AUC/t-stat/MI,非連續報酬 IC);正反案例 matching(同波動/regime,防答案只是 regime 差);事件 OOS(train/test 切事件,不在全事件挑因子)。
- 🗂 資料形狀：事件清單 + 每事件前窗特徵切片(稀疏列,非全 T)。
- 📊 平台現況：**IC event 模式僅 `event_filter` 條件查詢(query 篩列),不吃顯式事件清單+正反標籤+事件前窗**;`signal_density_analyzer`、`DataExtraction` case search 相關但未接成 case-control 流程。
- 🧩 全棧狀態：⛓️‍💥/❌ 兩端半成品·未接成 case-control（event_query 有 UI+後端但非事件研究;顯式事件清單/正反/前窗/matching/OOS 完全缺）。
- 🛡️ 洩漏防禦：**只能用事件前窗(T 之前),絕不可碰事件當下及之後**;正反案例時間/regime matching 防混淆;事件重疊需 purge。
- ⚡ 大尺度：事件稀疏→列數遠小於全 T;重在 430K 欄 × 判別計算 + 跨 symbol 事件 pool。
- 🔧 漏洞：整套缺(顯式事件 ingestion、前窗對齊、判別指標、matching、OOS)。
- 🏷️ 優先級：🎯 絕對優先(使用者主戰場,完全缺)。

## 階段一 待委員會詰問
1. 橫截面 IC 全棧標 ✅ 是否過樂觀?(concat 爆點 + 無 split,功能在但「做對」存疑——✅ 是否該降 ⚠️?)
2. symbol 一致性標 🔶 vs ❌:有無我漏看的現成聚合?
3. case-control 全棧該標 ⛓️‍💥(兩端有但沒接成)還是 ❌(等於沒有)?event_query 算不算「部分前端」?
4. Pooled IC 與 symbol 一致性是否該合併為一個「多標的普適性」群,還是分開?
5. 有無階段一該有、我漏列的類型?
