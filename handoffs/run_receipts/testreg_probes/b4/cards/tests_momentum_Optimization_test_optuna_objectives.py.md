# 任務卡：tests/momentum/Optimization/test_optuna_objectives.py

- 組：G13；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r17/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r17-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/Optimization/test_optuna_objectives.py::test_multi_objective_auto_nsga2_sampler（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。可插拔 objective 經真 OptunaOptimizer（暫存 sqlite）跑 5 trials、兩種 objective 之 search space／evaluate 回型（float／2-tuple）。缺陷：test_multi_objective_auto_nsga2_sampler 名稱宣稱多目標自動切 NSGA-II（生產 optuna_optimizer.py:710-714），但只斷言 directions 長度 2 與 trials 數；sampler_type 給 TPE 而 optuna TPE 本身支援多目標，刪掉自動切換仍綠——補斷言 study.sampler 為 NSGAIISampler。np.random 未設種子，斷言不依值故不致 flaky。
