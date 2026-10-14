# 任務卡：tests/momentum/Analysis/test_lightgbm_analyzer.py

- 組：G11；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r15/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r15-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Analysis/test_lightgbm_analyzer.py::test_validate_oot_error_and_severe_branch（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。斷言與宣稱不符：test_validate_oot_error_and_severe_branch 名稱宣稱 severe 分支，末段斷言 gap_status 屬於 {warning,severe,good} 為全值域恆真，且以訓練集前 60 列當 OOT（樣本內 AUC 高，gap 多半 <0.05）未保證觸發 severe。修法：先以同資料算 oot_auc，再傳 cv_auc_mean=oot_auc+0.1 斷言 gap_status==severe 且 cv_oot_gap>=0.08；前段三個 ValueError 斷言有效保留。test_validate_oot_returns_status 亦為全值域斷言但名稱僅宣稱回傳狀態，屬 smoke。fixture synthetic_training_data／trained_lightgbm 在根目錄 conftest.py:177-204
