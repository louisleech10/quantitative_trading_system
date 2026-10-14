# 任務卡：tests/test_xgboost_advanced_metrics.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_xgboost_advanced_metrics.py::test_expectancy_calculator（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。ML 診斷工具之值域／形狀契約（precision@k 鍵與閾值域、bootstrap CI 上下界序、permutation importance 長度與 std≥0、fold 穩定性分割完整、cross-symbol verdict 列舉），no-probe。缺陷（恆綠、量化期望值從嚴）：test_expectancy_calculator 之 price_changes 只取 0.02／-0.01 兩值，期望值為其加權平均必 ≤0.02，`expectancy <= 0.05` 與 `total_trades >= 0` 恆真，公式寫錯（如勝敗號反、漏乘勝率）仍綠。修法：固定小輸入手算 win_rate、avg_win、avg_loss、expectancy 精確比對
