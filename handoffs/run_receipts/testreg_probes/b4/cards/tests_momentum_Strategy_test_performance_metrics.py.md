# 任務卡：tests/momentum/Strategy/test_performance_metrics.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Strategy/test_performance_metrics.py::test_expectancy_with_mixed_trades（R(t) 符號數 2）
  - tests/momentum/Strategy/test_performance_metrics.py::test_max_drawdown_negative_value（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。total_return／win_rate／profit_factor 有手算值；空輸入回 0、非法 periods_per_year raise、邊界資料比率有限、SQN 分母 0。no-probe。缺陷（量化正確性從嚴）：PerformanceMetrics 是 Optuna 策略目標函數（預設 expectancy）與回測指標來源，章程 E3 明列須手算 Sharpe/MDD（TEST_DESIGN_CHARTER.md:93），但 test_max_drawdown_negative_value 只斷言 ≤0、test_expectancy_with_mixed_trades 只斷言型別，全庫無其他值 oracle（test_strategy_backtest_enhanced 之 sharpe 對照用同一實作）——兩者改為手算精確值（樣本曲線 MDD＝1.06/1.08−1；三筆 pnl 之 expectancy＝0.003）。add:sharpe／sortino／cagr 手算 oracle 與 mutation 探針。
