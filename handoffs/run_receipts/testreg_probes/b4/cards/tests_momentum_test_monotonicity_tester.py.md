# 任務卡：tests/momentum/test_monotonicity_tester.py

- 組：G8；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r12/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r12-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_monotonicity_tester.py::test_long_short_tstat_matches_scipy（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。rewrite：test_long_short_tstat_matches_scipy 宣稱 t-stat 與 scipy 一致，但 feature 為單調 linspace（:65），PIT expanding qcut 下當根恆為歷史最大值而落最高分位（pit_stats.py:361；同檔 :13 註解自承），valid.min()==valid.max() ⇒ 低／高兩組為同一組，t=0、p=1，比對退化（產線取錯組或高低對調仍綠），且分組沿用產線 _assign_quantiles（self-ref）；修法＝改用 :15-18 之非單調特徵＋相關 label，先斷言低高兩組不同且 bins 有 5 個值，再與 scipy.stats.ttest_ind 比對。其餘：Q5>Q1、spread 由產線分組重算（分組部分 self-ref）、單調分數完美＝1／缺 bin 不計、降級 3 分位、空資料與錯誤分支 NaN、_assign_quantiles 與 pit 輔助函式一致（接線契約）
