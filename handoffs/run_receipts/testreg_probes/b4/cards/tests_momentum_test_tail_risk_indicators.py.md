# 任務卡：tests/momentum/test_tail_risk_indicators.py

- 組：G8；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r12/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r12-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/momentum/test_tail_risk_indicators.py::test_mdd_invalid_price（R(t) 符號數 1）
  - tests/momentum/test_tail_risk_indicators.py::test_tail_risk_extreme（R(t) 符號數 1）
  - tests/momentum/test_tail_risk_indicators.py::test_tail_risk_many_nans（R(t) 符號數 1）
  - tests/momentum/test_tail_risk_indicators.py::test_tail_risk_one_sided（R(t) 符號數 1）
  - tests/momentum/test_tail_risk_indicators.py::test_udvr_zero_downside（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑；合成 close（A6 邊界用途可接受）。三支恆綠：①one_sided 嚴格遞增 ⇒ loss_sum 恆 0→NaN，gpr.dropna() 為空表，(空 <= 100).all() 恆 True，且 clip(upper=100) 本已保證；②udvr_zero_downside 之 isna().any() 由 rolling 暖機列即必然成立，與零下行無關；③mdd_invalid_price 之 isna().any() 亦由 2w-2 暖機 NaN 必然成立，未驗第 30 列被遮。修法：①斷言 gpr 全 NaN 且非 inf（或構造近單邊序列觸上限 100）②斷言暖機後之 udvr 為 NaN ③斷言第 30 列各 mdd 欄為 NaN、其前後有效列非 NaN。no-probe；add: CVaR／RV／MDD 小表手算 oracle（現無任何數值期望值）。
