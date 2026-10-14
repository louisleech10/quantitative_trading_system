# 任務卡：tests/momentum/Analysis/model_validation/test_walk_forward_validator.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/model_validation/test_walk_forward_validator.py::test_W9_all_periods_below_random（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。W9 恆真：`assessment in {unstable, moderate, robust}`（:129）即 _assess_stability 之全部回傳值域（walk_forward_validator.py:275-280），任何實作皆綠；且前提錯——y 整體取反後模型於取反標籤上重新訓練，OOS AUC 仍高，根本不會「低於隨機」。修法：讓 OOS 標籤相對訓練關係翻轉（如只翻轉各測試窗之 y，或用固定反向打分之替身模型），斷言 assessment==unstable 且 degradation_periods 非空。其餘：W1／W6 邊界、W4 單類窗 test_auc None、W7 全失敗 n_periods==0 正常；W2／W10 只驗回傳型別（W10 名為 memory_warning 但未斷言警告），屬 smoke。no-probe。覆蓋缺口（洩漏從嚴）：無斷言驗 test_start_idx−train_end_idx==purge_gap（walk_forward_validator.py:265-273），:195-196 只驗 end>start。add:purge 間隔與 expanding 模式 train_end<test_start 之斷言。
