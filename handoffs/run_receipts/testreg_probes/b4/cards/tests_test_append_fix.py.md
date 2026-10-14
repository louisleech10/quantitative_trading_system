# 任務卡：tests/test_append_fix.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_append_fix.py::test_multi_range_append（R(t) 符號數 3）
- 主委分類 note：
  記錄器無紀錄、未實跑。非密封：直連真實 Binance 下載（無替身、無 network 標記；conftest 只 stub ping，tests/conftest.py:40），且 `KlineStorageManager()` 預設寫入生產 ./data_cache（kline_storage.py:183,237），測試會改寫真實 K 線快取；生產快取已含 ETHUSDT 1h 歷史時 :109 總數斷言恆成立、:107-108 只能抓整檔覆蓋，對部分覆蓋無鑑別力。修法：cache_dir 改 tmp_path、provider 以錄製之真實回應替身（或標 network 分層），於空快取驗兩區間並存且總筆數等於兩段之和。:9 project_root 實為 tests/（無害）。
