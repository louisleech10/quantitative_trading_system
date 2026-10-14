# 任務卡：tests/momentum/Strategy/test_vectorized_backtest.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Strategy/test_vectorized_backtest.py::test_calculate_equity_curve_skip_unknown_timestamp_exit（R(t) 符號數 2）
  - tests/momentum/Strategy/test_vectorized_backtest.py::test_trailing_stop_triggered（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。合成小表（回測邏輯層可接受）驗出場原因、冷卻、早退、非法輸入、成本扣減（有成本 pnl 較小＝METAMORPHIC）、年化 metadata 與 rf=0 下 sharpe 比值＝sqrt(8760/730)（代數獨立 oracle）。缺陷①test_trailing_stop_triggered：斷言接受 {trailing_stop,take_profit,stop_loss} 任一，停損／停利命中也綠，未證移動停損；手推本 fixture 於第 1 根即 trailing 出場（stop 98、tp 106、trailing 102、low 101），可直接改斷言 exit_reason=='trailing_stop' 並鎖出場價 102，不需動生產。缺陷②test_calculate_equity_curve_skip_unknown_timestamp_exit：把章程 §A21 明禁之「unknown exit timestamp silent skip」鎖為期望（權益曲線全 1.0＝該筆 PnL 靜默消失），量化正確性從嚴屬 oracle 錯；須隨生產 :362-363 改為 raise 或具名記錄後改斷言。弱點不列缺陷：test_normal_backtest_with_trades 名稱稱有交易但只驗 list 型別、test_consecutive_stop_losses 只驗 any。add:commission/slippage 單筆 PnL 手算 exact（章程 E3）、信號延遲 1 bar MR。no-probe
