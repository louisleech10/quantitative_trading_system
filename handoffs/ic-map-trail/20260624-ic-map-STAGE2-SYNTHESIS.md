# 完整地圖 階段二「品質、動態與細節」— Claude 互審綜合（待委員檢查）

> Round 2 草案。四家獨立版 + Claude 讀碼定真相。**此綜合須交 codex/cursor/Gemini 檢查(使用者流程)。**

## 全棧狀態（程式碼定案）
| 型 | 後端 | 前端 | 連結 | 判定 |
|---|---|---|---|---|
| 1 分位/單調性 | ✅(MonotonicityTester,stage5必跑) | ✅(QuantileReturnChart+summary score) | **🔌 圖表接錯schema→靜默空圖** | **🔌/⚠️**(summary有值但圖常「暫無數據」;cross-sectional空;全樣本qcut洩漏) |
| 2 IC衰減/半衰期 | ✅邏輯 | ✅(ICDecayChart) | ✅形狀 | **⚠️ 大run崩潰/極慢**(grouped連帶+14k熱迴圈log);小fixture✅;cross-sectional空殼 |
| 3 regime/grouped | ⚠️崩潰 | ✅(GroupedICBarChart/RegimeRadar) | ✅形狀但預設觸發崩潰 | **⚠️ 有但壞掉(P0崩潰)**;by_volatility契約漂移;cross-sectional空 |
| 4 穩定性/ICIR | ✅(icir/hit_rate) | ✅(summary ICIR) | ✅ | **✅基礎+🔌 OOS穩定性在deep tab非主gate**;無train/test→ICIR全in-sample |

## 逐型定案（9 欄）

### 1. 分位 / 單調性分析
- 🔍 特徵越高報酬越高(單調)?還是U型/只極端有用?Long-short spread 顯著? | 📐 每期橫截面分Q5/Q10,各組 forward return + Q5-Q1 spread t-test + 單調性分數;常與 turnover 並看 | 🗂 單標的時序(現況)或面板;分組
- 📊 `MonotonicityTester`(monotonicity_tester.py:qcut+compute_monotonicity_score+spread t-test);orchestrator `_stage5` 對全 columns 逐 feature 迴圈必跑;`monotonicity_test` 在 LOCKED_TOGGLES(永遠執行不能關);`include_quantile_curves` schema 有但 orchestrator 未消費(死配置)
- 🧩 **後端✅ 前端✅ 連結🔌** → **🔌/⚠️**:report 寫 `quantile_returns[feature]={quantile_returns:{...},monotonicity_score,long_short}`(orchestrator:1270)但前端 QuantileReturnChart 期望頂層 `quantile_mean_returns`(QuantileReturnChart.tsx:13-17)→**圖表常「暫無數據」靜默空圖**;summary table 的 score 有值;REST `/quantile/{feature}` 同形狀問題;cross-sectional 回 `quantile_returns:{}` 空
- 🛡️ **必每期只用當期橫截面分位;現況對整段時序一次 qcut=全樣本分位含未來分布→洩漏**;無 IS/OOS 選因子洩漏 | ⚡ O(features×bars×quantiles),45k×1.7k 實測數十分鐘;對策 Stage A 候選 gate+只對 top-K+串流 qcut | 🔧 ①全樣本qcut洩漏 ②輸出schema與前端不一致(空圖) ③幽靈filter疊加全量迴圈 ④cross-sectional缺 ⑤事件case-control未建模 | 🏷️ 高(IC共主,ML門檻)

### 2. IC 衰減 / 半衰期
- 🔍 預測力撐幾根bar?半衰期多短?(高頻還波段) | 📐 多horizon IC→指數衰減fit→半衰期;peak horizon | 🗂 單標的時序;多horizon
- 📊 `compute_ic_decay`(:331)逐特徵fit;前端 ICDecayChart(half_life/fit_r2);REST /decay/{feature} 通
- 🧩 **後端✅ 前端✅ 連結✅** → **⚠️ 大run崩潰/極慢**:per-feature `_fit_exponential_decay` 對 low-R2 每特徵 warning(14090條熱迴圈)+grouped同task崩潰連帶白算;小fixture✅;cross-sectional空殼
- 🛡️ horizon label嚴格forward;(Gemini)若標的有除權息/分割需正確還原否則假IC峰值[crypto多N/A但原則記] | ⚡ horizon合併算不做horizon×全矩陣;只對survivors;warning聚合 | 🔧 ①熱迴圈log ②逐特徵Python迴圈 ③43萬R2≈0多雜訊診斷 ④cross-sectional空 | 🏷️ 中(現有但壞)

### 3. 分組 / 狀態(regime) 條件 IC
- 🔍 訊號只在牛市/高波動才有效?跨年穩定? | 📐 按regime切子樣本各算IC;rule(MA/vol percentile)或unsupervised(HMM/KMeans);雷達圖+全regime同號穩健性;panel每(date,symbol)先標regime再pool | 🗂 features+label+raw OHLCV;regime標籤
- 📊 `compute_grouped_ic`(:365):year/quarter用_iter_time_groups;by_regime→rule(EMA55+vol percentile:1052)或RegimeDetector KMeans;前端 GroupedICBarChart+RegimeRadarChart;條件 include_regime_analysis=True+raw kline
- 🧩 **後端⚠️ 前端✅ 連結⚠️** → **⚠️ 有但壞掉(P0崩潰)**:orchestrator:1139傳pydantic GroupedConfig給dict-API(ic_engine:377 config.get)→AttributeError;**intermediate預設開啟→大run必觸發**;修後為🔌(cross-sectional永遠空grouped_ic);`by_volatility:true`但無分支(契約漂移)
- 🛡️ **(Gemini)regime劃分極易踩未來函數(事後看整段才知是牛市)→必用rolling lookback指標即時判定當下**;split內分組防洩漏 | ⚡ group row mask×column chunk只對survivors禁.loc全矩陣 | 🔧 ①崩潰 ②by_volatility缺分支 ③timestamp秒/毫秒(_get_time_index:1018影響by_year/quarter軸) ④全特徵分組重算 ⑤cross-sectional空 | 🏷️ 中(緊急修)

### 4. 穩定性 / 一致性 (Win Rate, ICIR)
- 🔍 IC靠某幾天極端拉高還是每天穩定? | 📐 ICIR(IC mean/std)+hit_rate(IC>0比例)+rolling離散度;Information Ratio | 🗂 單標的時序→rolling序列統計
- 📊 `compute_icir`(:304)算ic_std/hit_rate/icir;`compute_ic_autocorrelation`;StatisticalValidator對rolling IC做t-test;前端summary table顯示ICIR;cross-sectional有summary_table.icir/ic_hit_rate
- 🧩 **後端✅ 前端✅ 連結✅** → **✅基礎全棧連通**;🔌 OOS穩定性(rolling_oos)屬deep module+deep tab非主gate
- 🛡️ **主路徑無train/test→ICIR/勝率全in-sample,實盤一定打折(過擬合)**;rolling窗PIT(接型2全段rank爭議) | ⚡ Welford串流摘要 | 🔧 ①無OOS主gate ②依賴rolling(同型3 grouped崩潰連帶) ③rolling Spearman先全段rank可疑 | 🏷️ 中

## 階段二結論
- **靜默斷裂(新揪)**：分位圖表接錯 schema→「暫無數據」空圖(型1),雖 summary 有值,但使用者看圖會以為沒資料。
- **崩潰連鎖**：regime/grouped 的 GroupedConfig P0 崩潰(型3)→ 連帶 decay(型2)、依賴 rolling 的穩定性(型4)在大 run 一起白算。
- **共通洩漏**：全樣本 qcut(型1)、無 train/test(型1-4 全部)、regime 劃分 look-ahead(型3)。
- **cross-sectional 空殼**：分位/decay/grouped 在 cross-sectional 模式全回空(只 longitudinal 算)。

## 待委員檢查
1. 型1 分位圖 schema 不一致(orchestrator:1270 vs QuantileReturnChart.tsx:13-17)是否屬實?判 🔌 準確?
2. 型3 by_volatility 契約漂移、timestamp 影響範圍是否正確歸位?
3. 階段二是否該加第 5 型「因子有效性漂移(drift_analyzer)」?還是歸入型4穩定性/型2衰減?
4. 任何狀態與真實碼不符(附檔:行)。
