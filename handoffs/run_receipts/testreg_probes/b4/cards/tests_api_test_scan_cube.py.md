# 任務卡：tests/api/test_scan_cube.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_scan_cube.py::test_wiring_scan_grid_strips_report_before_returning（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄；no-probe：docstring 所引 mutation 腳本 handoffs/20260907-scancube-mutate.py 不在 repo 亦無 git 歷史；其餘為立方體寫讀契約（逐列原樣、排除節明示、三個 fail-closed 閘、路徑不變式、prune 恰留 keep、原子替換、分頁不重不漏、stub 鍵機械守衛），keep；rewrite 理由兩項：①測試自己在 :526-527 pop report 再斷言未洩漏，生產端剝除（ic_analysis_service.py:1465-1467）從未被執行，斷言與 docstring 宣稱不符；②:524 monkeypatch scan_cube.DEFAULT_ROOT 無效——build_cube 之 root 預設值於定義時綁定（scan_cube.py:185），_build_scan_cube 不傳 root ⇒ 實寫 repo 之 data_cache/ic_scan_cubes/t1 並對真實目錄跑 keep_tasks=20 之 prune（實況該目錄已有 9/11 殘留之 t1）；修法：替身 create_scan_cube_store 綁 tmp root，並改經生產掃描網格收尾段驗剝除，斷言不減
