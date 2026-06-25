# 完整地圖 階段二「品質、動態與細節」— 定案版（四家審查已納入）

> Round 3。四家獨立版 → Claude 讀碼綜合 → 三家審查(皆 CHANGES,有檔佐證,彼此一致)→ 本版納入全部。
> codex 實讀 HDF5 確認 timestamp 為秒(1716235200)。drift 型經 1對2 reconcile 為「列為型5但狀態誠實」。

## 全棧狀態（程式碼定案）
| 型 | 判定 | 一句話 |
|---|---|---|
| 1 分位/單調性 | **🔌 靜默空圖** | 後端算(stage5必跑)、summary score有值,但圖表接錯schema→「暫無數據」;cross-sectional空;全樣本qcut洩漏 |
| 2 IC衰減 | **⚠️ 極慢+連帶白算** | decay自身會算,但熱迴圈14k log極慢 + 同stage grouped崩潰→整job失敗拿不到 |
| 3 regime/grouped | **⚠️ P0崩潰** | GroupedConfig傳dict-API→AttributeError(intermediate預設+有raw kline時觸發);by_volatility假開關;timestamp秒被當ms(by_year/quarter軸錯) |
| 4 穩定性/ICIR | **✅基礎 + 🔌OOS** | ICIR/hit_rate前端有;OOS在deep tab非主gate;無train/test→in-sample過擬合 |
| 5 因子效力漂移 | **🔌/❌** | rolling-IC concept drift在deep Quality Dashboard部分有;結構斷裂(Chow/CUSUM)❌;DriftAnalyzer(PSI特徵分佈)是不同物未接IC |

## 逐型定案（9 欄，audit 已納入）

### 1. 分位 / 單調性分析
- 🔍 特徵越高報酬越高(單調)?還U型?單邊有效? | 📐 每期橫截面分Q5/Q10,各組forward return+**Q5-Q1 spread 用 Newey-West 調整t-stat(金融自相關否則高估顯著)**+單調性分數;**(Gemini)須另看 Top/Bottom vs Benchmark(因子常單邊有效,只看spread誤導)**;常與turnover並看 | 🗂 單標的時序(現況)或面板
- 📊 `MonotonicityTester`(qcut+monotonicity_score+spread t-test);stage5對全columns逐feature必跑;`monotonicity_test`在LOCKED_TOGGLES(不能關);`include_quantile_curves`死配置
- 🧩 **後端✅ 前端✅ 連結🔌** → **🔌 靜默空圖**:report `quantile_returns[feature]={quantile_returns:{quantile_mean_returns...},monotonicity_score,long_short}`(orchestrator:1270 pass-through monotonicity_tester:160)但前端 QuantileReturnChart 讀**頂層** `quantile_mean_returns`(tsx:13)→圖「暫無數據」;summary從巢狀取所以**有分數圖空**;**FactorEquityCurveChart(deep tab,page.tsx:776)同吃錯shape**;REST /quantile/{feature} 同;cross-sectional回空。**修法:後端flatten成QuantileReturnData或前端解包 data.quantile_returns.quantile_mean_returns**
- 🛡️ 必每期當期橫截面分位;**現況整段一次qcut(monotonicity_tester:185)=全樣本含未來分布→洩漏**;無IS/OOS選因子洩漏 | ⚡ O(features×bars×quantiles),45k×1.7k數十分鐘;Stage A候選gate+只對top-K+串流qcut | 🔧 ①全樣本qcut洩漏 ②schema空圖 ③幽靈filter疊加全量迴圈 ④cross-sectional缺 ⑤事件case-control未建模 | 🏷️ 高

### 2. IC 衰減 / 半衰期
- 🔍 預測力撐幾根bar?半衰期?(高頻還波段) | 📐 多horizon IC→指數衰減fit→半衰期;**(Gemini)指數fit在R²低/IC翻負會崩→須加非參數半衰fallback(移動平均IC跌破峰值一半的bar數,不靠擬合)** | 🗂 單標的時序;多horizon
- 📊 `compute_ic_decay`(:331/per-feature fit:346);前端ICDecayChart(half_life/fit_r2);REST /decay/{feature}通
- 🧩 **後端✅ 前端✅ 連結✅** → **⚠️ 極慢+連帶白算**:decay先算(orchestrator:1122),但 low-R2 每特徵 `_fit_exponential_decay` warning(ic_engine:943,14090條熱迴圈)極慢;**同stage grouped崩潰→整report丟失(連帶白算,非decay自崩)**;小fixture✅;cross-sectional空殼
- 🛡️ horizon label嚴格forward;(Gemini)若標的有除權息/分割需還原[crypto多N/A] | ⚡ horizon合併算;只對survivors;warning聚合 | 🔧 ①熱迴圈log ②逐特徵Python迴圈 ③R2≈0多雜訊 ④cross-sectional空 ⑤指數fit脆弱需fallback | 🏷️ 中

### 3. 分組 / 狀態(regime) 條件 IC
- 🔍 訊號只在牛市/高波動才有效?跨年穩定? | 📐 按regime切子樣本各算IC;rule(MA/vol percentile)或unsupervised(HMM/KMeans);**(Gemini)KMeans/HMM有Label Switching致命陷阱(今天Cluster0明天變1)→須以波動率/斜率基準對齊標籤**;雷達圖+全regime同號 | 🗂 features+label+raw OHLCV;regime標籤
- 📊 `compute_grouped_ic`(:365 year/quarter/by_regime rule EMA55+vol percentile/KMeans);前端GroupedICBarChart+RegimeRadarChart;條件 include_regime_analysis=True+raw kline
- 🧩 **後端⚠️ 前端✅ 連結⚠️** → **⚠️ P0崩潰**:orchestrator:1133傳pydantic GroupedConfig給dict-API(ic_engine:377 config.get)→AttributeError;**intermediate預設+有raw_data時觸發;無raw/labels-only/cross-sectional則跳過**;修後為🔌(cross-sectional永遠空);**by_volatility:true但compute_grouped_ic無此分支(high_vol/low_vol在by_regime rule路徑,不同契約)**
- 🛡️ **(Gemini)regime劃分極易踩未來函數(事後看全段才知是牛市)→須rolling lookback指標即時判定**;split內分組 | ⚡ group row mask×column chunk只對survivors禁.loc全矩陣 | 🔧 ①崩潰 ②by_volatility假開關 ③**timestamp秒被當ms(ic_engine:1018,codex實讀HDF5確認1716235200秒)→只影響by_year/quarter,不影響rule regime** ④全特徵分組重算 ⑤cross-sectional空 | 🏷️ 中(緊急修)

### 4. 穩定性 / 一致性 (Win Rate, ICIR)
- 🔍 IC靠某幾天極端拉高還每天穩定? | 📐 ICIR(IC mean/std)+hit_rate(IC>0比例);**(Gemini)ICIR缺尾部風險→加Factor Max Drawdown + Newey-West調整ICIR顯著性** | 🗂 單標的時序→rolling序列統計
- 📊 `compute_icir`(:304 ic_std/hit_rate/icir)+`compute_ic_autocorrelation`(算了但不進report);summary接線(orchestrator:1387);cross-sectional也有icir/hit_rate(:245);前端summary顯示ICIR+**hit_rate已顯示✅**
- 🧩 **後端✅ 前端✅ 連結✅** → **✅基礎全棧連通**;🔌 OOS穩定性(rolling_oos deep module:609,UI deep tab:750)非主gate
- 🛡️ **無train/test→ICIR/勝率全in-sample,實盤一定打折**;rolling窗PIT(接型1全段rank爭議) | ⚡ Welford串流摘要 | 🔧 ①無OOS主gate ②依賴rolling(grouped崩潰連帶) ③ic_autocorrelation算但不輸出 ④rolling Spearman先全段rank | 🏷️ 中

### 5. 🆕 因子效力漂移 / 結構性斷裂（reconcile 後新增）
- 🔍 2018超有效的因子,2023是否因市場微結構改變**永久失效**?(宏觀層,異於型2微觀衰減、型4全段均值) | 📐 **(Gemini)Chow Test(結構斷裂)或CUSUM(累積和),偵測累積報酬曲線斜率永久下折** | 🗂 長時序;rolling IC 序列 / 累積報酬
- 📊 IC deep module `FeatureQualityDiagnostics`(:140)有 rolling IC concept drift;deep tab Quality Dashboard(page.tsx:818);獨立 `DriftAnalyzer`(PSI 特徵分佈漂移,drift_analyzer:59)接 pattern/XGBoost,**未接 IC**
- 🧩 **後端🔌(rolling-IC drift在deep有;Chow/CUSUM❌;PSI在別路徑) 前端🔌(Quality Dashboard deep tab) 連結⛓️‍💥** → **🔌/❌**:concept drift 部分有但 deep-tab gated;結構斷裂正規檢定缺;PSI 是不同 drift 未接 IC
- 🛡️ 斷裂點偵測不可用未來;rolling 評估 PIT | ⚡ rolling IC 序列輕量;Chow/CUSUM 對 survivors | 🔧 結構斷裂檢定缺;兩種 drift 概念(效力 vs 特徵分佈)未釐清/未整合 | 🏷️ 低/中(進階,但防「用已死因子」)

## 階段二結論（audit 修正後）
- **靜默斷裂(新揪)**:分位圖接錯schema→空圖(型1),summary有值但看圖以為沒資料;FactorEquityCurveChart同病。
- **崩潰連鎖**:regime/grouped GroupedConfig P0(型3,intermediate+raw kline觸發)→連帶decay(型2)、依賴rolling的穩定性(型4)大run一起白算。
- **共通洩漏**:全樣本qcut(型1)、無train/test(型1-5全部)、regime劃分look-ahead(型3)、KMeans label switching(型3)。
- **cross-sectional空殼**:分位/decay/grouped在cross-sectional全回空。
- **其他靜默(codex補)**:event_timestamps schema有但service只warning;feature_filter幽靈讓人以為只跑top-N;regime_robust summary永遠None;ic_autocorrelation算了不輸出。
- **量化嚴謹補強(Gemini)**:Newey-West t-stat(型1/4)、Top/Bottom vs benchmark(型1)、非參數半衰fallback(型2)、label alignment(型3)、Factor MDD(型4)。

## 三家審查共識
- codex+cursor 程式碼修正(型1 flatten/FactorEquityCurve、型2 reword+觸發條件、型3 by_volatility/timestamp秒、型4 hit_rate顯示/autocorr不輸出)全納入。
- Gemini 量化補強全納入。
- drift:1對2 reconcile→列為型5但狀態誠實(部分有+結構斷裂缺+PSI不同物),三家皆可接受。
