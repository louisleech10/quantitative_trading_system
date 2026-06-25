VERDICT: CHANGES

1. 型1 schema 靜默空圖：屬實，判 🔌 正確。  
證據：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1270) 輸出 `quantile_returns = stage5_results["monotonicity"]`；[monotonicity_tester.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/monotonicity_tester.py:160) 每個 feature 形狀是 `{ quantile_returns: { quantile_mean_returns... }, monotonicity_score, long_short }`；但 [QuantileReturnChart.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/QuantileReturnChart.tsx:13) 讀頂層 `data.quantile_mean_returns`。  
改法：綜合稿保留此點，最好補一句「chart 應讀 `data.quantile_returns.quantile_mean_returns`，或後端 flatten 成 `QuantileReturnData`」。

2. 型2 decay / 型3 grouped 大 run 崩潰：方向正確，但「預設觸發」需加條件。  
證據：前端預設 `featureTier='intermediate'` 且 `grouped_ic: true`、`ic_decay: true` 在 [icAnalysisStore.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/store/icAnalysisStore.ts:84)；stage override 送出在 [icAnalysisStore.ts](/Users/louis/Desktop/quantitative_trading_system/frontend/src/store/icAnalysisStore.ts:292)。後端預設 report 也開 decay/regime：[ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:143)。崩潰點是 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1133) 傳 `GroupedConfig`，而 [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:377) 呼叫 `config.get()`。  
改法：把「intermediate 預設開啟→大run必觸發」改成「intermediate 預設開啟，且有 `kline_reader/raw_data` 時會預設走 grouped 崩潰；無 raw_data/labels-only/cross-sectional 則跳過」。

3. 型2 嚴重度：可標 ⚠️，但不要說 decay 自己必崩。  
證據：decay 先在 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1122) 計算，per-feature fit 在 [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:346)，low-R2 熱迴圈 `logger.warning` 在 [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:943)。grouped 後續崩潰會讓整個 stage/report 丟失，所以「連帶白算」準確。  
改法：型2狀態寫「極慢/熱迴圈 log；在同 stage 被 grouped crash 連帶失敗」。

4. 型3 by_volatility / timestamp：屬實，歸位大致正確。  
證據：`by_volatility` schema 存在於 [ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:76)，但 [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:383) 只處理 `by_year/by_quarter/by_regime/by_category/by_data_source/by_layer`。`_get_time_index()` 對數字 timestamp 固定 `unit="ms"`：[ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:1018)；storage 註解與實作是秒 timestamp + RangeIndex：[kline_storage.py](/Users/louis/Desktop/quantitative_trading_system/momentum/DataExtraction/kline_storage.py:1049)。我也只讀 HDF5 確認樣本 timestamp 為 `1716235200` 秒。  
改法：補明「timestamp 錯軸只影響 by_year/by_quarter，不影響 rule regime 的 bull/bear/high_vol/low_vol」。

5. 型4 穩定性：準確，但漏了兩個原始版重點。  
證據：ICIR/hit_rate 主路徑在 [ic_engine.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_engine.py:304)，summary 接線在 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1387)。cross-sectional 也有 ICIR/hit_rate：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:245)。OOS 在 deep module runner：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:609)，UI deep tab：[page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:750)。  
改法：保留「✅基礎 + 🔌 OOS deep tab；無 train/test→in-sample ICIR」，另補 `ic_autocorrelation` 後端算但不輸出、toggle 假開關，以及 `cross_symbol_validation` 在 cross-sectional report 但 UI 放 deep tab。

6. 第5型 drift_analyzer：不建議獨立成階段二第5型；應歸入型4穩定性，並標「deep/另一路徑」。  
證據：獨立 `DriftAnalyzer` 是 PSI train/test 分佈漂移，主要接 pattern/XGBoost 路徑：[drift_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/drift_analyzer.py:59)、[pattern_analysis.py](/Users/louis/Desktop/quantitative_trading_system/api/routes/pattern_analysis.py:604)。IC deep module 已有 rolling IC concept drift：[feature_quality_diagnostics.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/feature_quality_diagnostics.py:140)，且 deep tab 有 Quality Dashboard：[page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:818)。  
改法：在型4加一行「FeatureQualityDiagnostics deep module 含 rolling IC drift；DriftAnalyzer PSI 屬模型/特徵分佈漂移，不作階段二主四型」。

7. 漏掉原始版重要點：需補。  
建議補入綜合稿的「靜默斷裂/漏洞」：`event_timestamps` schema 有但 service 只 warning 未接線；`feature_filter` 幽靈設定不只效能問題，也會讓使用者以為只跑 top-N；`regime_robust` summary 永遠 None；`ic_autocorrelation` 算了不進 report。這些都在原始 Codex/Cursor/Gemini 版出現，綜合稿目前只部分帶到。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、完整 CLAUDE.md、綜合稿、四份原始稿，並對照上述程式碼與只讀 HDF5 timestamp 樣本。  
TESTS_RUN: read-only；執行 `sed`/`rg`/`nl`/`find` 與 `python -c` 只讀檢查，未跑測試。  
FAILURES_SEEN: here-doc 因 read-only sandbox 無法建立臨時檔，已改用 `python -c`。  
SCOPE_CHANGES: none  
NUMERIC_OR_SCHEMA_IMPACT: none  
HANDOFF_NOT_UPDATED: 使用者明示 READ-ONLY，且 sandbox 為 read-only。  
STATUS: DONE