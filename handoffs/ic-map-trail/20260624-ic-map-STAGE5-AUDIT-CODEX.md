VERDICT: CHANGES

Claude 綜合版主結論大多屬實，但型 5 有重要遺漏需要補強；型 1 的 API `feature_filter.max_features`「幽靈防線」也應寫得更精確。其餘未見需要推翻的錯誤。

**逐條核對**

1. 型 1 屬實：`max_features_for_correlation=200` 是死配置；前端硬裁 18；Stage4 更早全欄 rolling IC 是前置災難。
   證據：
   - [ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:154) 定義 `PerformanceConfig.max_features_for_correlation=200`，但 `rg` 只找到 schema 一處，未進執行路徑。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1224) Stage6 直接 `features_df[passed_features]` 跑 redundancy；[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1229) 對 filtered_df 算完整 corr，無 cap。
   - [redundancy_filter.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/redundancy_filter.py:169) `values.T @ values` 完整 C×C。
   - [CorrelationHeatmap.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/CorrelationHeatmap.tsx:21) 預設 `maxFeatures = 18`。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1105) Stage4 對全 `features_df` 算 IC；[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1106) 對全欄 rolling IC；[ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:289) rolling path 先 rank/轉全欄矩陣。
   改法：後端在 Stage4/Stage6 fail-closed 接 `performance.max_features_for_correlation` 或明確 top-k/candidate pool，報告截斷原因與入選規則；前端 18 只能是視覺裁切，不可當安全邊界。

2. 型 2 屬實：正交化被寫成「Neutralized IC」會誤導；目前是 transform summary，沒有 residual IC；`ShapleyConfig` 死配置也屬實。
   證據：
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:817) `_run_factor_orthogonalization` 只呼叫 orthogonalizer。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:832) 回傳 summary + `transformed_shape`，沒有把 residual/transformed factor 再對 label 算 IC。
   - [factor_orthogonalizer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/factor_orthogonalizer.py:68) Gram-Schmidt summary 是 correlation before/after、residual variance；[factor_orthogonalizer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/factor_orthogonalizer.py:114) PCA summary 是 EVR/loadings。
   - [ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:268) `ShapleyConfig` 存在；未見 runner 引用。
   改法：文案改名為 Orthogonalization Summary；另建 PIT/rolling residual IC 模組，fit neutralizer on train window，再在 test/window 算 residual IC/ICIR。

3. 型 5 屬實，但 Claude 綜合版應補一個更嚴重點：`positions` 不只是「等權非真持倉」，而是按時間列數 T 建權重，語義是時間平均 exposure，不是資產/策略持倉；而且真 attribution 函式存在但 runner 未呼叫。
   證據：
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:842) `market_proxy = label_series`。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:843) `positions = 1.0 / len(factor_values)`，`len(factor_values)` 是 rows/T。
   - [factor_exposure_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/factor_exposure_analyzer.py:94) `positions` 會 reindex 到時間 index；[factor_exposure_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/factor_exposure_analyzer.py:101) 實際做 `factor_values.T @ weights`。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:873) attribution 硬填 `alpha/r_squared/unexplained=np.nan`、`attribution={}`。
   - [factor_exposure_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/factor_exposure_analyzer.py:104) 真 `calculate_factor_attribution()` 存在，但 orchestrator 未呼叫。
   - [FactorExposureRadar.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/FactorExposureRadar.tsx:13) 雷達直接展示 exposure/attribution betas。
   改法：綜合版型 5 改成 P0 正確性問題；runner 接真 `portfolio_returns + factor_returns + strategy/model positions`，沒有真持倉時 UI 標「proxy exposure」，不要叫 attribution。

4. 型 4 屬實：SHAP 有實作；IC 主流程沒有 ML/SHAP；沒有 IC→ML 橋。
   證據：
   - [shap_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/shap_analyzer.py:75) `SHAPAnalyzer`。
   - [shap_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/shap_analysis_service.py:99) 呼叫 `analyze_shap_global()`；[shap_analysis_service.py](/Users/louis/Desktop/quantitative_trading_system/api/services/shap_analysis_service.py:146) 單案例 SHAP。
   - [FeaturesTab.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/pattern/details/tabs/FeaturesTab.tsx:25) Pattern 詳情頁展示 SHAP。
   - [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:609) deep runners 清單無 XGB/LGBM/SHAP。
   改法：新增 IC survivors export / one-click Pattern ML validation / IC vs SHAP reconcile report。

5. 型 6 屬實：IC 主流程缺 IC 加權多因子組合。
   證據：
   - `rg "ic_weight|composite|weighted.*factor|factor_weight"` 未找到 IC composite pipeline。
   - [trend_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/trend_analyzer.py:110) `combined_signal` 是趨勢診斷信號，不是 composite factor IC。
   - [model_config.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/model_config.py:52) `_combinations` 是 LightGBM 參數安全規則，不是因子合成。
   改法：新增 top-k survivor 的 walk-forward ICIR/NetIC weighted composite evaluator，權重只用 train window fit。

6. 六型與 9 欄：六型足夠作為階段五主表；可在「待補」加 `marginal IC increment`、`regime-conditional redundancy/orthogonalization`，但不必升成第 7/8 型。9 欄業界標準與洩漏描述未見重大量化錯誤；430K corr 矩陣約 `430000^2 = 1.849e11` floats，OOM 判斷成立。

**綜合版需改的最小清單**

- 型 5 優先級從 P1 至少升為 P0/P1，補「positions 維度 bug：按 rows/T 等權，不是真 positions」。
- 型 5 補「`calculate_factor_attribution()` 有實作但 orchestrator 未呼叫，現在是硬編碼 NaN/空 dict」。
- 型 1 補清楚 `feature_filter.max_features` 是 API request 被塞進 `config_override.feature_filter`，但 [ICConfig](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:319) 無此欄，Pydantic validate 後不進 IC 執行；它不是後端安全 cap。

HANDOFF_NOT_UPDATED: READ-ONLY 審查 + sandbox read-only，未寫 handoff 檔。
ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md/CLAUDE.md、綜合版與四家原始版；用 `rg/nl/sed` 對照上述代碼路徑。
TESTS_RUN: read-only code inspection only；未跑 pytest。
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: none
STATUS: DONE