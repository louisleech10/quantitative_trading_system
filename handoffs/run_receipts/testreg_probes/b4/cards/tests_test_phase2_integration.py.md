# 任務卡：tests/test_phase2_integration.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_phase2_integration.py::TestAPIEndpoints::test_get_strategy_detail_endpoint（R(t) 符號數 1）
  - tests/test_phase2_integration.py::TestAPIEndpoints::test_invalid_strategy_returns_404（R(t) 符號數 1）
  - tests/test_phase2_integration.py::TestAPIEndpoints::test_list_strategies_endpoint（R(t) 符號數 1）
  - tests/test_phase2_integration.py::TestOptunaOptimizerDynamicParameters::test_multi_objective_dynamic_sampling（R(t) 符號數 2）
  - tests/test_phase2_integration.py::TestOptunaOptimizerDynamicParameters::test_strategy_metadata_parameter_sampling（R(t) 符號數 2）
- 主委分類 note：
  記錄器無紀錄、未實跑。缺陷一（只驗測試自算之值、未呼叫生產）：TestOptuna 兩支宣稱測 OptunaOptimizer 動態採樣，實為在測試內自寫採樣迴圈直呼 optuna trial.suggest_int 再驗其落在範圍內，等於驗 optuna 函式庫；生產採樣迴圈在 optuna_optimizer.py:1057-1072 從未被呼叫（OptunaOptimizer 匯入未用）。修法：經 OptunaOptimizer 之 objective（或抽出之採樣函式）驗。缺陷二（斷言與宣稱不符）：TestAPIEndpoints 三支宣稱測 GET /strategies、/strategies/{id} 與 404，實為直呼 strategy_registry、在測試內複製路由組裝邏輯後驗自組 dict；生產路由 api/routes/optimization.py:295、:344 全庫無測試打到。修法：改 TestClient 打路由並驗回應碼與 StrategyDetailResponse 欄位。其餘正常：registry 約束驗證有效／無效對照、invalid strategy 拋 ValueError、three_line 預設值 7/25/70 與 config/strategies.yaml 硬編一致、三策略訊號形狀／dtype 契約（mock indicator 之 calculate_indicators_from_dataframe 即生產 three_line_strategy.py:81 呼叫者，替身有效）。test_strategy_calculation_backward_compatible 只驗 callable（註解已自承，屬 smoke 不改）
