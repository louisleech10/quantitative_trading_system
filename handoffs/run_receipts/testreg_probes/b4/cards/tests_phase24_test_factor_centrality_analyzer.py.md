# 任務卡：tests/phase24/test_factor_centrality_analyzer.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase24/test_factor_centrality_analyzer.py::test_detect_crowding_regime（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。以合成 IC 矩陣為主，驗 SkippedResult 分類邊界與 PCA 失敗時退回相關法；PCA 中心度數值從未比對（success 只驗鍵與非空，:19-21），no-probe。缺陷：test_detect_crowding_regime 的 :51 feature 只是輸入的回聲，:52 trend∈{rising,falling,flat} 等於非空路徑的全值域（factor_centrality_analyzer.py:185），整個函式恆綠，regime 與 crowding_ratio 都沒驗。修法：輸入 linspace(0.1,0.5,10)、門檻 0.3 ⇒ 斷言 trend=='rising'、crowding_ratio==0.5、regime=='crowded'。add:小矩陣手算中心度（loadings²·evr）以 TOLERANCE 比對。
