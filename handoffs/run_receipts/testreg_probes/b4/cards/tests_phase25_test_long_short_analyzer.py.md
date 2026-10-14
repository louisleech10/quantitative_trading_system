# 任務卡：tests/phase25/test_long_short_analyzer.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase25/test_long_short_analyzer.py::test_asymmetric_quantile_def（R(t) 符號數 1）
  - tests/phase25/test_long_short_analyzer.py::test_both_sides_negative_ic（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑；本檔為 dba5716f（long_short PIT 分箱）前之舊副本，該提交只遷移孿生檔 tests/momentum/Analysis/test_long_short_analyzer.py。疑似既有紅兩支（讀碼推定）：① test_quantile_exceeds_samples existing-red:dba5716f——n=60 低於 bin min_samples=100（pit_stats.py:39、:342-343）⇒ 生產回 SkippedResult('cannot form quantiles')（long_short_analyzer.py:110-119），:22 isinstance dict 必紅；孿生檔同名函式已改斷言 SkippedResult ⇒ 擬 E2 立碑。② test_assign_quantiles_none_for_constant_feature existing-red:dba5716f——呼叫已刪私有 helper _assign_quantiles_with_fallback ⇒ AttributeError ⇒ 擬 E0 立碑。缺陷：test_empty_side 之 :41 為 dict or SkippedResult 恆真（n=80 實走 SkippedResult），孿生檔同名函式已改為單側空須 samples==0 且 recommendation==不建議 ⇒ 擬 E2；test_both_sides_negative_ic 與 test_asymmetric_quantile_def 只斷言回傳值屬於生產自身 enum（_recommendation 與 _classify_asymmetry 只會回這些值）⇒ 恆綠、名稱宣稱之情境未被驗——改寫為斷言具體結果（遞增 linspace 下 PIT 標籤全落最高箱 ⇒ long ic<0、short samples==0、recommendation==不建議；非對稱設定須驗 long／short 樣本數對應所設分位集合）。test_insufficient_ls_samples 與 helper 分支三支正常。
