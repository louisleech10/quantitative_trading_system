# 任務卡：tests/phase24/test_parameter_sensitivity_analyzer.py

- 組：G14；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r18/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r18-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/phase24/test_parameter_sensitivity_analyzer.py::test_batch_analyze_collects_high_and_low_risk（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。家族偵測、風險分級門檻、跳過分支為有效契約斷言；IC 數值未與 scipy 獨立比對，no-probe。缺陷：test_batch_analyze_collects_high_and_low_risk 名稱宣稱「收集高、低風險家族」，但 :137-138 只驗 high_risk_families 與 robust_families 兩個鍵存在，而生產無條件回傳這兩個鍵（parameter_sensitivity_analyzer.py:175-180）⇒ 恆綠。修法：斷言 'stable' 在 robust_families、'noisy' 不在 robust_families（或依實測固定 'noisy' 在 high_risk_families）。test_analyze_from_variants_success 與 test_batch_analyze 只驗鍵，屬 smoke。
