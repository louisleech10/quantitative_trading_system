VERDICT: CHANGES

1. `turnover.enabled` 假開關：屬實  
證據：[ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:59) 把 `turnover_analysis` 映到 `turnover.enabled`，但 Stage 5 在 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:1175) 無條件呼叫 `self._turnover.compute_all(features_df)`；[turnover_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/turnover_analyzer.py:139) 也不讀 `enabled`。  
改法：Stage 5 依 `config.turnover.enabled` gate；若 disabled，回 `{}` 並讓 summary `turnover_rate` 為 null。

2. crypto 成本 5bps 偏樂觀、`slippage_bps` 未讀：大致屬實  
證據：`default_cost_bps=5` 與 `slippage_bps=2` 在 [ic_config_schema.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_config_schema.py:255) / [config/ic_config.yaml](/Users/louis/Desktop/quantitative_trading_system/config/ic_config.yaml:181)。`NetICAnalyzer` 只讀 `default_cost_bps/cost_scenarios/participation_rate`，見 [net_ic_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/net_ic_analyzer.py:21)，公式只用 `use_cost`，見 [net_ic_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/net_ic_analyzer.py:31)。  
改法：把 fee 與 slippage 拆欄，`effective_cost_bps = fee_bps + slippage_bps` 或明確改名為 fee-only。`20bps round-trip` 屬市場假設，本次未能用 live 官方費率驗證；但若 taker 10bps/leg，判斷成立。

3. capacity 函式存在但 volume 未餵、backtest 成本與 IC 孤島：屬實  
證據：capacity 需要 `avg_daily_volume_usd`，缺值回 unknown，見 [net_ic_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/net_ic_analyzer.py:90)。`_run_net_ic` 只傳 `{"ic_mean": ...}`，沒傳 volume，見 [ic_filter_orchestrator.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/ic_filter_orchestrator.py:913)。Backtest 有 commission/slippage 且扣 round-trip，見 [vectorized_backtest.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Strategy/vectorized_backtest.py:41) 和 [vectorized_backtest.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Strategy/vectorized_backtest.py:246)。  
改法：把 per-symbol ADV/quote volume 接入 Net IC metric；統一 IC 與 backtest 的 fee/slippage config。

4. 型 1 schema 空圖與 spread 定義：部分需改寫  
屬實：`report.quantile_returns[feature]` 是包裝層 `{quantile_returns, monotonicity_score, long_short}`，見 [monotonicity_tester.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/monotonicity_tester.py:160)。但 `QuantileReturnChart` 讀頂層 `quantile_mean_returns`，見 [QuantileReturnChart.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/QuantileReturnChart.tsx:13)；`FactorEquityCurveChart` 讀頂層 `cumulative_returns`，見 [FactorEquityCurveChart.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/FactorEquityCurveChart.tsx:51)。  
不屬實或需澄清：`LongShortComparisonChart` 讀 `deepAnalysisReport.long_short_analysis`，見 [page.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/app/ic-analysis/page.tsx:809)，不受這個 quantile schema 錯層直接影響。Claude 綜合應改成「影響 basic QuantileReturnChart + deep FactorEquityCurveChart，不是 C19 LongShortComparisonChart」。  
主 vs deep spread 定義不一致屬實：主流程是 Qmax-Qmin，見 [monotonicity_tester.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/monotonicity_tester.py:113)；deep 預設 Q4/Q5 vs Q1/Q2，見 [long_short_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/long_short_analyzer.py:23)。

5. 階段四 3 型是否該加  
不建議加第 4 型。現有 3 型足夠：L/S return、turnover/net IC、liquidity/capacity/slippage。`breakeven cost` 屬型 2；`capacity-adjusted IC` 屬型 3 子項。可在型 3 補「capacity-adjusted net IC / participation-rate scenarios」，不用新增類型。

6. 9 欄標準/洩漏防禦與漏項  
主要漏項：Claude 綜合沒有明講目前 `qcut` 是全樣本分位，不是 rolling/train-window 分位；嚴格 PIT 下這是風險。證據：[monotonicity_tester.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/monotonicity_tester.py:181) 和 [turnover_analyzer.py](/Users/louis/Desktop/quantitative_trading_system/momentum/Analysis/turnover_analyzer.py:30)。  
次要漏項：`NetICChart` 成本下拉硬編 `[1,3,5,10,20]`，不讀後端 scenarios，見 [NetICChart.tsx](/Users/louis/Desktop/quantitative_trading_system/frontend/src/components/ic-analysis/NetICChart.tsx:39)。  
原始版重要點大多已收進綜合；需要補上「C19 不受 schema 錯層直接影響」與「全樣本 qcut/PIT 風險」。

ASSUMPTIONS_VERIFIED: 已讀 HANDOFF.md、CLAUDE.md、五份 stage4 handoff；用程式碼驗證 orchestrator、analyzers、config、frontend charts、types、backtest。
TESTS_RUN: read-only；未跑 pytest/build。查證使用 `sed/nl/rg`。
FAILURES_SEEN: web 搜尋官方費率未返回結果；市場費率未 live 驗證。
SCOPE_CHANGES: none。
NUMERIC_OR_SCHEMA_IMPACT: none，未改檔。
HANDOFF_NOT_UPDATED: read-only sandbox 且任務明示 READ-ONLY。
STATUS: DONE