# 任務卡：tests/phase24/test_factor_return_analyzer.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase24/test_factor_return_analyzer.py::test_compute_risk_metrics_calmar_nan_when_no_drawdown（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。量化主體有效：test_mutation_pos_phase24 與 test_mutation_lookahead_phase24 以獨立手刻的 PIT expanding 參考（:175-198，不經生產碼）逐值比對生產的 position 與 ls_return（atol 1e-12，:308-310、:353），並以夾具自證 PIT≠full-sample（:343），再斷言生產≠真舊 low/high 配對與 full-sample qcut（:312、:354）⇒ 退回前瞻實作必紅，獨立 oracle 可證偽，claim=correctness。:316-326 為 variant 自比之冗餘恆真行，無害。缺陷：test_compute_risk_metrics_calmar_nan_when_no_drawdown 的 :162 `isnan or isfinite` 恆真——生產已把非有限 calmar 轉為 NaN（factor_return_analyzer.py:248-256），斷言永不失敗，和函式名稱宣稱的「無回撤時為 NaN」不符。修法：單調正報酬 max_drawdown=0 ⇒ 斷言 isnan，並補 max_drawdown==0。另 :120 平坦報酬年化波動 <1e-8 實際靠浮點殘差（std≈1.8e-18>0）成立，若 std 精確為 0 生產會回 NaN 而紅（脆弱，非缺陷）。與 tests/momentum/Analysis/test_factor_return_analyzer.py 同源參考，但 AST 不相同，不立碑。
