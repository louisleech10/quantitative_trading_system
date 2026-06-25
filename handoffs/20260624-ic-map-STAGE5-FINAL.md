# 完整地圖 階段五「多因子與系統觀」— 定案版（四家審查已納入）

> Round 3 定案。四家獨立版 → Claude 讀碼綜合 → 三家審查(皆 CHANGES,程式碼一致)→ 本版納入全部。

## 全棧狀態總表
| 型 | 判定 | 一句話 |
|---|---|---|
| 1 相關/VIF/冗餘 | **✅主流程但❌大尺度防線** | Stage6真去重,但**無candidate cap→430K直接O(p²)/O(p³)爆**;max_features_for_correlation=200死配置;前端熱圖硬裁18列只窺一角;Stage4更早對430K全欄算rolling IC=前置災難 |
| 2 正交化/Neutralized IC | **🔌+誤稱** | deep預設關,**名「Neutralized IC」實際只輸出正交轉換summary,無真residual IC**;前端無正交化圖;ShapleyConfig死配置;正交後未回接 |
| 3 擁擠/Centrality | **🔌(最接近「跟其他因子比」)** | deep預設開(intermediate);用IC空間(scale-smart);但被Stage4規模+deep門檻卡,應survivor後自動跑 |
| 4 ML/SHAP | **✅獨立頁但⛓️‍💥無IC橋** | xgboost/lightgbm/SHAP(shap_analyzer)成熟,有purge/embargo;但與IC兩套平行管線,無「IC倖存者→一鍵ML驗證」 |
| 5 因子暴露/歸因 | **🔌+雷達誤導(P0正確性)** | calculate_factor_attribution()**存在卻被runner硬填NaN繞過**;positions=1/T是時間平均exposure非真持倉;market_proxy=label;前端雷達照樣展示讓人誤以為做了投組歸因 |
| 6 多因子組合 | **❌最大缺口** | IC加權因子合成缺;「這因子有獨特新資訊嗎」的產品答案之一缺 |

## 逐型定案（9 欄）

### 1. 相關 / Clustering / VIF（冗餘）
- 🔍 這批因子是不是互相抄答案?保留哪個代表? | 📐 corr/hierarchical clustering/VIF;先IC/ICIR排序再去重;**(Gemini)VIF只看單變數,矩陣條件數(max/min奇異值)衡量整體特徵矩陣穩定性(防回歸權重失真/翻轉)** | 🗂 factor×factor矩陣
- 📊 `RedundancyFilter`(greedy/hierarchical/vif)**Stage6主流程**(orchestrator:138→_stage6_redundancy:1204,對passed_features);前端CorrelationHeatmap(主報告tab);`performance.max_features_for_correlation=200`存在但**全momentum/僅schema一處引用,執行路徑未讀**
- 🧩 **後端✅(主流程真去重非skeleton) 前端✅(CorrelationHeatmap) 連結⚠️** → **✅主流程連通但UI只窺一角(前端硬裁18列,CorrelationHeatmap:21)**
- 🛡️ corr/VIF看同期特徵矩陣不直接用未來label;但上游feature已leak此層不偵測 | ⚡ **O(T×C)建矩陣+O(C²)corr+VIF~O(C³);Stage6輸入C=passed_features無程式內cap;C≈430K→corr矩陣~1.8×10¹¹ floats必OOM;且Stage4更早對430K全欄算rolling IC(ic_engine:268)是前置災難;parallel_ic_calculation未使用** | 🔧 ①max_features_for_correlation=200死配置 ②API feature_filter.max_features寫override但ICConfig無此欄靜默丟棄(幽靈) ③閾值寬鬆C可很大仍全算 ④前端18格與後端規模脫節 | 🏷️ P0(後端fail-closed candidate cap+top-k/分桶/近似corr)

### 2. 正交化 / Residual IC / 邊際IC（Neutralized IC——現為誤稱）
- 🔍 對已知因子回歸後殘差還有預測力嗎?(即:這因子帶來正交的新資訊/alpha增量嗎?) | 📐 **(Gemini)Incremental/Marginal IC:新因子對現有因子庫橫截面回歸取殘差→殘差IC顯著為正才是新資訊**;OLS residual IC、Gram-Schmidt、PCA residual、sector/market/beta/vol neutralized IC;報residual IC/ICIR——**這是階段五『有獨特新資訊嗎』的精確答案** | 🗂 factor矩陣+label
- 📊 `FactorOrthogonalizer`(gram_schmidt QR/pca)deep module(orchestrator:817,**預設enabled:False**,intermediate disabled_modules含它);**`gram_schmidt`/`pca`只輸出transformed shape+corr before/after,不是真「neutralized IC」**;Neutralized IC無獨立模組,相近能力分散(factor_exposure.neutralize_factor_matrix中性化因子值非IC、net_ic成本調整非neutralized);ShapleyConfig(schema:268,enabled:False無runner)死配置
- 🧩 **後端🔌(deep預設關) 前端❌/🔌(deep tab無正交化專屬圖,有centrality/exposure/net IC無orthogonalization chart) 連結⛓️‍💥** → **🔌+誤稱**:可跑、前端無視覺化、預設不跑、**名實不符(claims neutralized IC實為transform summary,無真residual/incremental IC)→建議改名Orthogonalization Summary,另建PIT/rolling residual IC模組**
- 🛡️ **對全樣本矩陣做QR/PCA未見walk-forward/rolling fit→全期PCA再評IC有全樣本資訊滲透** | ⚡ QR/PCA O(n·p²)+;deep若selected大無硬cap | 🔧 ①Neutralized IC概念缺口(與net IC/exposure混淆) ②預設關+無UI ③ShapleyConfig死配置 ④正交後未回接Stage6/7 | 🏷️ P0/P1(先做residual IC正名+rolling/PIT neutralization再加cap)

### 3. 擁擠 / Centrality
- 🔍 因子是否站市場共識中心?越中心越crowded/decay? | 📐 因子IC matrix PCA centrality、eigenvector centrality、rolling centrality、crowding regime | 🗂 rolling_ic matrix(rows=窗,cols=factors)
- 📊 `FactorCentralityAnalyzer`(PCA centrality+correlation fallback+compute_rolling_centrality+detect_crowding_regime);deep `_run_factor_centrality`(orchestrator:758)從rolling_ic建矩陣;**預設enabled:True但僅run_deep_analysis內;foundation tier deep_analysis:False→"not_run"**;前端FactorCentralityChart+PCAExplainedChart(deep tab)
- 🧩 **後端🔌(deep需手動/tier開) 前端✅ 連結🔌** → **🔌(最接近「跟其他因子比」的已串功能)**
- 🛡️ 吃rolling IC不直接看未來label(PIT取決於IC engine);rolling centrality在歷史窗計算方向對 | ⚡ **不對430K原始特徵PCA,只對C欄rolling IC(scale-smart);瓶頸在Stage4先對430K算rolling IC;deep若C≤200 PCA O(T×C²)可接受;rolling centrality每窗重跑PCA可累積** | 🔧 ①依賴rolling IC前置規模 ②deep與主流程脫節應survivor後自動跑 ③n_components預設5無動態cap ④centrality高≠新增資訊充分證據需合residual IC/model lift | 🏷️ P1

### 4. 非線性 ML 特徵重要性 (XGB/LGBM AUC, SHAP)
- 🔍 線性IC看不到的非線性關係?ML認為哪些特徵真在驅動? | 📐 time-series/purged CV AUC、gain/cover/weight、permutation、SHAP mean abs、fold stability | 🗂 cases×features+label;SHAP sample
- 📊 `xgboost_analyzer`/`lightgbm_analyzer`+`SHAPAnalyzer`(shap_analyzer.py,analyze_shap_global/explain_shap_single_case)+SHAPAnalysisService+pattern_analysis路由;**在獨立`/patterns/xgboost-analysis`頁,IC主流程(ic_filter_orchestrator)無XGB/LGBM/SHAP呼叫,ic-analysis/page無ML importance區塊**;有time_series_split/purge_gap/embargo;max_shap_samples=200
- 🧩 **後端✅(Pattern/ML域) 前端✅(Pattern頁) 與IC⛓️‍💥斷裂** → **🔌孤島(對IC用戶)**:兩套平行管線,無「IC倖存者→一鍵ML驗證」
- 🛡️ 樹模型有purge/embargo參數(是否每路徑強制啟用待驗);SHAP是訓練後解釋非PIT問題 | ⚡ SHAP只存200樣本可控;模型吃case-control主戰場比430K全量合理;features=20K訓練重需先篩 | 🔧 ①IC與ML脫節IC頁不告訴使用者「IC好但ML無增益/ML有非線性增益」 ②SHAP與IC排名未融合 ③無IC→ML top-k自動橋 | 🏷️ P0(產品敘事:建IC shortlist→ML validation→SHAP/incremental lift連結)

### 5. 因子暴露 / 歸因
- 🔍 訊號賺錢是只在賭大盤(Beta)還是真Alpha? | 📐 portfolio return~factor returns回歸;beta/alpha/R²/exposure HHI/neutralized exposure | 🗂 positions+factor returns+portfolio returns
- 📊 `FactorExposureAnalyzer`(orchestrator:837,deep),但**deep runner用等權positions對feature values算exposure;factor_attribution回alpha/R²/attribution多為np.nan/空dict,無真portfolio return regression**;用label_series當market_proxy(語義可疑);前端FactorExposureRadar(deep tab);預設intermediate關
- 🧩 **後端🔌 前端🎨(radar) 連結⛓️‍💥** → **🔌+雷達誤導(P0)**:`calculate_factor_attribution()`(factor_exposure_analyzer:104)**有完整實作但_run_factor_exposure(:873)硬填alpha/r_squared/attribution=np.nan/{}根本沒呼叫它**;positions=1.0/len(factor_values)(:843,len=rows/T)是**時間平均exposure非資產/策略持倉**;market_proxy=label_series(:842,語義可疑);前端FactorExposureRadar照樣展示exposure/attribution betas→誤導
- 🛡️ beta neutral用全期covariance;vol neutral用rolling std較好;market_proxy用label語義可疑 | ⚡ O(n·p)exposure可接受;真regression p大O(p²/p³) | 🔧 ①attribution多空 ②positions等權非真持倉 ③market_proxy=label可疑 ④雷達誤導已做歸因 | 🏷️ **P0正確性**(runner接真portfolio_returns+factor_returns+strategy/model positions;無真持倉時UI標「proxy exposure」不要叫attribution)

### 6. 多因子組合 (IC加權/組合IC)
- 🔍 多弱因子合成更穩?合成後經濟意義還在? | 📐 IC/ICIR weighted composite、**(Gemini)Grinold最優配置 Σ⁻¹·IC、HRP(樹狀分層風險平價,比傳統risk parity穩健)**、walk-forward learned weights(**須加換手/摩擦成本懲罰項**)、組合IC/turnover/capacity | 🗂 多因子+權重→composite signal
- 📊 **IC主流程無IC加權因子合成**;TrendAnalyzer有combined_signal但只診斷建議;optimization/strategy有參數+sample weights非「因子組合IC」;ML頁有importance但不回寫IC組合
- 🧩 **後端❌ 前端❌ optimization/strategy⛓️‍💥鄰近非同功能** → **❌ 最大缺口**
- 🛡️ **組合權重必walk-forward fit,只用train window權重評test IC,避免全期ICIR權重偷看未來** | ⚡ 大尺度友善:只對top-k(k≤50/200)矩陣乘O(n·k);不能對20K全量無約束optimizer | 🔧 整個缺;這正是「這因子有獨特新資訊嗎」的產品答案之一 | 🏷️ P0(新增composite factor evaluator,ICIR/NetIC weighted+walk-forward)

## 階段五結論
- **不是完整家族,是三塊分散能力**:Stage6去冗餘主流程✅;centrality/exposure/orthogonalization deep🔌;XGB/LGBM/SHAP pattern獨立頁✅但與IC⛓️‍💥;多因子組合IC基本❌。
- **最危險大尺度點**:RedundancyFilter主流程無後端硬cap,corr/clustering/VIF在430K直接爆;max_features_for_correlation=200死配置;且Stage4更早對430K算rolling IC已是前置災難。
- **誤導型**:正交化名「Neutralized IC」實為transform summary(型2);因子暴露雷達顯示但attribution多空(型5)——使用者以為有實際沒有。
- **最大產品缺口**:邊際/Incremental IC(型2該做沒做)+IC→ML橋(型4)+多因子組合IC含HRP/Grinold(型6)——ML-first平台「這因子有獨特新資訊嗎」的核心答案缺。
- **能力存在卻被繞過(P0)**:型5 calculate_factor_attribution有實作但runner硬填NaN→雷達顯示假歸因。

## 待委員檢查
1. 型1 max_features_for_correlation=200死配置、前端18列、Stage4前置rolling IC災難——屬實?
2. 型2 正交化「Neutralized IC」誤稱(實為transform summary無residual IC)——屬實?
3. 型5 attribution多np.nan空、positions等權——屬實?
4. 型4 SHAP有實作(shap_analyzer)+無IC→ML橋——屬實?型6多因子組合IC真缺?
5. 階段五6型有無該加;狀態與真實碼不符處(附檔:行)。
