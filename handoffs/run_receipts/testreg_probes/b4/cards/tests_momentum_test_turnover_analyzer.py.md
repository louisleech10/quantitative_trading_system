# 任務卡：tests/momentum/test_turnover_analyzer.py

- 組：G8；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r12/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r12-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_turnover_analyzer.py::test_quantile_turnover_matches_expected（R(t) 符號數 3）
- 主委分類 note：
  記錄器無紀錄、未實跑；self-ref：test_quantile_turnover_matches_expected 之期望值以同一 pit_expanding_qcut_label 逐行重抄生產公式（turnover_analyzer.py:72-95）而得，改生產碼之 top_mask／diff 邏輯時 oracle 同改，宣稱「計算正確」無獨立依據；修法＝小序列手算 PIT 分位標籤與頂分位進出次數之硬編期望值（斷言不減）。其餘：遞增序列 rank change＝1 手算、autocorr 對 pandas、成本拖累 0.0015 手算且同檔 M8 探針證手算斷言可區分舊混量綱公式、PIT 暖機段為 null（防前視）、負／非有限 turnover raise。
