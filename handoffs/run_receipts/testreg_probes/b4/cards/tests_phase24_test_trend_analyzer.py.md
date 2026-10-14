# 任務卡：tests/phase24/test_trend_analyzer.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase24/test_trend_analyzer.py::test_analyze_multi_dimension_combined_signal（R(t) 符號數 1）
  - tests/phase24/test_trend_analyzer.py::test_analyze_trend_down（R(t) 符號數 1）
  - tests/phase24/test_trend_analyzer.py::test_combine_signal_branches（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。缺陷三處：(1) test_analyze_multi_dimension_combined_signal 的 :44 recommendation∈{正常,警告,危險} 是 _combine_signal 的全值域（trend_analyzer.py:179-204）⇒ 恆綠；輸入 IC 線性下降、中心度線性上升、half_life=3，依規則應為「危險」，修法斷言 =='危險'。(2) test_analyze_trend_down 對完全線性下降序列（p≈0、r²=1）也接受 'flat'（:17），而 'flat' 正是顯著性門檻失效時的退化值（trend_analyzer.py:56-59），斷言遮住了主邏輯，修法斷言 =='down'。(3) test_combine_signal_branches 的 :87 接受 警告／危險，遮住 half_life<5 的升級分支（flat+up+4.0 應為危險），修法斷言 =='危險'。其餘分支斷言有效。winsorize 0.01/0.99 用於趨勢估計、非標籤，無洩漏疑慮。
