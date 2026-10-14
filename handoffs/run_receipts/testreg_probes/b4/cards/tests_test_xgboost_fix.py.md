# 任務卡：tests/test_xgboost_fix.py（G-c：檔內無測試函式）

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite_targets：[]（整檔；T 為空）
- 主委分類 note：
  0 個測試函式：全部邏輯為模組層程式碼，pytest 收集期即訓練三次 XGBoost；每段以 try/except 包住只 print（:56-59、:79-82、:97-101），測試 3 宣稱「numpy 無 feature_names 應拋 ValueError」未拋也只 print，任何結果皆不紅（恆綠）；X/y 無種子。無函式層 nodeid 可立碑 ⇒ 整檔改寫為測試函式（numpy＋feature_names 成功、DataFrame 成功、numpy 缺名 pytest.raises(ValueError)）
