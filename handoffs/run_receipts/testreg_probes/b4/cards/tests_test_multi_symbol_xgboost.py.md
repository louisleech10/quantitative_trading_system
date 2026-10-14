# 任務卡：tests/test_multi_symbol_xgboost.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_multi_symbol_xgboost.py::test_api_model（R(t) 符號數 2）
  - tests/test_multi_symbol_xgboost.py::test_case_storage（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。test_service_signature 斷言 start_batch_analysis 首參為 symbols（契約）；test_api_model 只建構 XGBoostBatchAnalysisRequest（建構成功＝接受 list，smoke，可順手補 assert）。test_case_storage 無任何 assert，只 print 案例數，且讀全域單例 get_case_storage_manager 之真實存檔（宣稱「多標的案例獲取」而無斷言，空心）。修法：tmp 目錄建 CaseStorageManager 寫入兩標的案例，assert get_cases_by_symbol 依標的隔離且合併數正確。
