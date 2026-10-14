# 任務卡：tests/api/test_gap3_ic_progress_fields.py

- 組：G6；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r10/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r10-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/api/test_gap3_ic_progress_fields.py::test_gap3_ic_progress_fields_populated_for_implicit_latest_and_full_analysis（R(t) 符號數 3）
- 主委分類 note：
  記錄器無紀錄、未實跑；過 response_model 後之 feature_count 欄、current_stage 開放集合、解析不到回 None 不填假值（含 service 端 _resolve_feature_count）、歧義 hash 不猜；rewrite 之支在 allowed_red（owner FFSTORE、owned-by-later-ticket，舊特徵 run 已刪）：前提依賴本機 data_cache/features/registry.json 有可物化之 BTCUSDT/12h latest（非密閉，且該 registry 會被其他測試寫入 pytest 暫存路徑之 entry），修法不動斷言：比照 test_gap3_ic_stop_gate.py 之 inject_latest_run 把受控 entry＋tmp manifest 注入 service registry；同支之 /full-analysis 只以 inspect.getsource 找 '"feature_count"' 字面屬弱斷言（add: 打 /full-analysis 後讀 task_info 鍵）；test_gap3_ic_progress_fields_resolver_reads_registry_only 亦讀本機 registry（無帶 feature_count 時 skip），現 42 筆皆帶值故會執行，不列
