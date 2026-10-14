# 任務卡：tests/api/test_optimization_output_service.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_optimization_output_service.py::test_build_zip_bytes_includes_files（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄；斷言與宣稱不符：test_build_zip_bytes_includes_files 名稱宣稱包含檔案，卻只驗回傳 bytes 非空（:175-176）——不寫入任何檔之空 zip 亦有 22 位元組目錄尾，恆綠；修法：以 zipfile 讀回，斷言 namelist 恰為 a.txt／b.txt 且內容為 A／B；其餘兩支為產出檔存在與空資料列數之契約，keep；另 OptimizationOutputService() 建構時即於 repo 根建 optimization_results/（monkeypatch 於建構後），不影響斷言
