# 完整地圖 階段三「統計嚴謹度與防偽」— 定案版（四家審查已納入）

> Round 3 定案。四家獨立版 → Claude 讀碼綜合 → 三家審查(皆 CHANGES,有檔佐證,彼此一致)→ 本版納入全部。
> **階段三殘酷真相:防偽機制程式碼幾乎都存在,但全部沒接進 IC 主流程(deep-tab 孤島或幽靈 toggle)→ 主因子研究幾無防過擬合保護,UI 卻顯示有。**

## 全棧狀態總表（程式碼定案）
| 型 | 判定 | 一句話 |
|---|---|---|
| 1 IC顯著性 | **🔌 P0** | 後端算t/p/CI,但report只帶p、global summary 無t_stat(ic_reporter:155);無IC bootstrap、無HAC(rolling IC當i.i.d.不當);CI未進UI |
| 2 FDR/多重比較 | **⛓️‍💥 P0 高風險假綠** | `_fdr_bh`/`_bonferroni`(statistical_validator:58-166)實作正確,但**全repo僅tests呼叫,orchestrator Stage5零引用**;前端toggle不送API、schema無fdr欄→**使用者以為開了FDR實際仍raw p** |
| 3 Block Bootstrap/Clustered SE | **❌ IC完全缺** | IC路徑零實作;僅XGBoost有i.i.d. bootstrap(方法不對IC) |
| 4 Train/Test Split主路徑 | **❌ 主路徑缺(最高)** | IC analyze全樣本in-sample;TimeSplitter在pattern/XGBoost非IC;連winsorize也全樣本fit分位 |
| 5 Walk-Forward/OOS | **🔌 deep-tab孤島** | RollingOOSValidator在deep tab,不阻止主結果通過;無purge/embargo |
| 6 Purged/CPCV | **🔌 ML孤島** | PurgedTimeSeriesSplit+CPCV完整但IC Gatekeeper不用、case-control未接 |
| 7 極端值影響診斷 | **🔌/❌** | winsorize有但無「極端值對IC敏感度」專診 |

## 逐型定案（9 欄）

### 1. IC 顯著性 (t-stat/p-value/bootstrap CI)
- 🔍 這IC是運氣還是統計顯著? | 📐 IC序列t-test或bootstrap CI;**(Gemini)須Newey-West/HAC校正自相關,或block bootstrap CI(rolling IC非i.i.d.)** | 🗂 rolling IC序列
- 📊 `StatisticalValidator.compute_ic_statistics`/`apply_significance_filter`(p_value_max=0.05);**漏點根因(codex/cursor修正):第一漏在 `_build_summary_table`(orchestrator:1387-1405)只放p_value無t_stat/ci_*,`ic_reporter`(:114/241/275)二次漏匯出;longitudinal主路徑summary無t_stat;cross-sectional則後端直接寫t_stat(orchestrator:259)但p_value=None,前端resolveTStat優先用item.t_stat(ICSummaryTable:76)**
- 🧩 **後端🔌 前端🔌 連結🔌** → **🔌 P0**:主篩選gate直接依賴p_value;把rolling IC當i.i.d.(量化判inadequate);無IC bootstrap、無HAC;CI未暴露UI
- 🛡️ t-test假設IID但IC序列自相關→高估顯著 | ⚡ O(特徵×rolling點),20K可行但重;bootstrap×20K不可接受需top-N/block | 🔧 ①rolling IC當i.i.d. ②apply_significance_filter存在但Stage5未呼叫 ③CI不進report/UI ④無block bootstrap | 🏷️ P0(主gate依賴p_value)

### 2. 🚨 FDR / 多重比較校正
- 🔍 測43萬特徵,多少高IC只是運氣? | 📐 對全部feature p值做BH-FDR或Bonferroni;篩選用adjusted p/q-value;報告同列raw vs adjusted | 🗂 全特徵p值集
- 📊 `adjust_multiple_comparisons()`+`_fdr_bh`/`_bonferroni`(statistical_validator:58-166)**實作正確**,但**全repo僅tests呼叫(test_statistical_validator:44-57),`ic_filter_orchestrator` Stage5零引用,只用p_value_max直接篩**;前端FeatureTierPanel有`fdr_correction` toggle(L3)但`getEffectiveConfig()`不送進custom_overrides(icAnalysisStore:290-325);後端ICConfig schema無fdr欄
- 🧩 **後端🎨(函式有主流程空殼) 前端🎨(checkbox可點靜默無效) 連結⛓️‍💥** → **⛓️‍💥 兩端都有影子但沒連結:使用者以為開了FDR實際仍raw p。🔴高風險假綠**
- 🛡️ FDR本身不防look-ahead只防多重測試假陽性;**未啟用→43萬下假陽性率失控** | ⚡ BH O(N log N) 430K排序極快無瓶頸;**(Gemini)但43萬高度共線非獨立→須先 clustering/orthogonalization 算「有效獨立特徵數」再調p值,否則Bonferroni殺光、BH失準** | 🔧 ①主流程完全沒套用 ②前端顯示「FDR」誤導已防偽 ③易混淆:event_filter `adjusted_p_threshold`(0.05/0.10,event_filter:128)是樣本量tier放寬**不是FDR** ④UI未接線前應灰掉或標「未實作」 | 🏷️ 🎯P0(43萬必要,高風險假綠)

### 3. Block Bootstrap / Clustered SE
- 🔍 換時段/換批symbol還成立? | 📐 block bootstrap(保時序自相關)、clustered SE(同symbol群聚) | 🗂 時序/面板
- 📊 IC路徑零實作;僅XGBoost有i.i.d. bootstrap(方法不對IC——破壞時序自相關)
- 🧩 **後端❌(對IC) 前端❌** → **❌ IC完全缺**
- 🛡️ 一般bootstrap破壞時序自相關→須block | ⚡ 重抽樣只對top-N/survivors | 🔧 IC無block版;事件case-control必要 | 🏷️ 中→P1(FDR/raw p先補,block接著,case-control必要)

### 4. 🎯 Train/Test Split（主路徑）
- 🔍 嚴格不偷看未來、切分後還有效? | 📐 時序train/val/test;feature selection只在train,test最後一次;case-control也按時間切不能random | 🗂 時序切分,index disjoint
- 📊 **IC主流程analyze() Stage0→7同一features_df/label_series全量算IC+篩選(orchestrator:93-160,1092-1152),無hold-out**;`TimeSplitter`(time_splitter.py)+create_time_splitter用於pattern_analysis(XGBoost)非IC;**Stage1 winsorize在全樣本fit分位(data_preprocessor:78)→strict OOS應只在train fit**
- 🧩 **後端❌(IC主路徑) 前端❌** → **❌ 主路徑缺(最高優先洩漏)**
- 🛡️ 本身就是防洩漏機制;缺=全in-sample過擬合;event filter不是train/test isolation | ⚡ split是index操作輕 | 🔧 IC主路徑整個缺;winsorize全樣本fit | 🏷️ 🎯最高(正確性紅線)

### 5. Walk-Forward / Rolling OOS
- 🔍 滾動訓練→驗證的泛化? | 📐 rolling/expanding train窗+forward test窗;看IS/OOS gap、OOS hit rate、退化期 | 🗂 時序滾動
- 📊 IC有`RollingOOSValidator`(deep module);前端OOSDistributionChart(deep tab);WF/CPCV在model-enhancement無前端頁
- 🧩 **後端🔌 前端🔌(deep tab) 連結🔌** → **🔌 deep-tab孤島**:可按深度分析跑Rolling OOS,但**不阻止主結果通過**
- 🛡️ **(codex/cursor精準區分)IC Rolling OOS(rolling_oos_validator:163)train_end直接接test=無purge/embargo→重疊horizon仍洩漏;但ML WalkForwardValidator(walk_forward_validator:18)有purge_gap/embargo,只是在model-enhancement孤島IC不接** | ⚡ 滾動×特徵只對candidates | 🔧 IC版非主gate無purge;ML版有purge但孤島 | 🏷️ 高

### 6. Purged / Combinatorial Purged CV
- 🔍 事件重疊時CV有無標籤洩漏? | 📐 López de Prado purged CV+embargo;CPCV多路徑 | 🗂 時序+事件重疊
- 📊 `PurgedTimeSeriesSplit`+CPCV完整(combinatorial_purged_cv:18,有purge_gap+embargo)但**從model_enhancement_service執行(:100),IC Gatekeeper零引用、case-control不用、前端IC頁無CPCV**(ML孤島);(codex待驗:purge_gap是row-count非event-span)
- 🧩 **後端🔌(ML孤島) 前端❌(IC頁) 連結❌** → **🔌 ML孤島·IC未接**
- 🛡️ 正是防事件OOS洩漏核心(接case-control);**(Gemini)Purge須強制含Embargo(test後空白期不納train,防延遲資訊外溢)** | ⚡ 多路徑重算對candidates | 🔧 與case-control/IC完全未接;PBO可由CPCV估(見型8) | 🏷️ 高(case-control必需)

### 7. 極端值影響診斷
- 🔍 好IC是否被少數極端行情/錯值撐起? | 📐 winsor前後IC對比、剔除極端後IC穩健性 | 🗂 單特徵分布
- 📊 有preprocessing winsorization;`FeatureQualityDiagnostics`有ADF前winsorize/Ljung-Box/coverage/drift/redundancy,**但無「極端值影響」專門診斷**
- 🧩 **後端🔌(預處理有/專診缺) 前端❓** → **🔌/❌**
- 🛡️ 極端值可能真訊號也可能髒資料須區分 | ⚡ 輕 | 🔧 無極端值對IC敏感度專診 | 🏷️ 中

### 8. 🆕 策略選取層級過擬合 (DSR / PBO / MinBTL)（reconcile 後新增）
- 🔍 我盲撈43萬特徵,挑出的「最佳」有多大機率只是運氣(選擇偏差)? | 📐 **(Gemini)Deflated Sharpe Ratio**(把測試次數+特徵相關+報酬偏度納入,向下修正最佳Sharpe/IC,海量盲撈證有效的數學標準)、**PBO**(CSCV算IS最佳者OOS低於中位數的機率,如「60%機率過擬合」)、**MinBTL**(43萬次嘗試需多長歷史才能DSR顯著,防兩年資料窮舉) | 🗂 全特徵IC/Sharpe分布+測試次數
- 📊 **repo無DSR/PBO/MinBTL實作**(grep deflated|PBO僅handoffs/archived)
- 🧩 **後端❌ 前端❌ → ❌ 完全缺**;交叉引用:**PBO是型6 CPCV的產出指標**(CPCV能力在但ML孤島未接)、**DSR/MinBTL屬策略/回測層**(連Stage4實戰寫實的backtest Sharpe)
- 🛡️ 評估須用OOS;DSR的trials數=實際測試的特徵數 | ⚡ DSR/PBO對最終candidates輕量 | 🔧 整個缺;這是43萬盲撈的「元過擬合」風險,FDR(特徵層)不覆蓋策略選取層 | 🏷️ 高(使用者43萬盲撈的核心防線)
- *(歸位:Gemini主張獨立型;codex/cursor主張折型5/6;裁決=列為型8但交叉引用型6 CPCV+Stage4回測,三家可接受)*

## 階段三結論
- **🚨 系統性防偽缺口**:嚴謹度模組(FDR/顯著性HAC/block bootstrap/train-test/walk-forward/purged CV)程式碼幾乎都存在,但**全部沒接進IC主流程**——主因子研究幾乎無防過擬合保護。
- **最危險假綠**:FDR toggle(型2)是幽靈,UI 宣稱防偽後端從未執行;**43萬特徵×0.05=約21,500個純運氣假訊號**,假陽性率失控。
- **最高優先洩漏**:train/test主路徑缺(型4)→全in-sample;連winsorize都全樣本fit。
- **孤島**:walk-forward(型5)/purged CV(型6)在deep tab或ML路徑,IC主流程不用;與case-control(型6主戰場)未接。
- **方法論**:rolling IC當i.i.d.(型1)→t-test高估顯著,須HAC(Newey-West)/block bootstrap。
- **元過擬合(新增型8)**:43萬盲撈的選擇偏差,需DSR/PBO/MinBTL(策略選取層),repo完全缺——FDR只防特徵層不夠。

## 待委員檢查
1. FDR幽靈(型2)判⛓️‍💥+高風險假綠,三家(codex/cursor)程式碼一致確認,準確?
2. 型1 global summary無t_stat、CI不進report——屬實?
3. 階段三是否該加Deflated Sharpe/PBO(過擬合機率)?還是歸FDR/顯著性?
4. 任何狀態與真實碼不符(附檔:行)。
