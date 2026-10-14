# 任務卡：tests/api/test_xgboost_sequence_features.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_xgboost_sequence_features.py::test_build_sequence_features_flatten（R(t) 符號數 1）
  - tests/api/test_xgboost_sequence_features.py::test_flatten_sequence_features（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄；量化正確性缺口（look-ahead 從嚴）：生產碼視窗刻意不含 row_idx（TO，xgboost_batch_service.py:1176-1181）、docstring :10 宣稱只用到 TO-1，但 test_build_sequence_features_flatten 只驗 shape (4,)，把視窗改成含 TO（range(start+1,row_idx+1)）仍綠；test_flatten_sequence_features 只驗名稱不驗值，拿掉 :1222 之 .T 致值與名稱錯配（a_w3_t-2 實為 b 之值）仍綠；修法＝前者斷言 values 等於第 1、2 列（x=[2,3]、y=[6,7]）並另驗 row_idx 不入窗，後者斷言 values=[1,3,5,2,4,6]；add: aggregate 之 mean／last 值斷言；no-probe
