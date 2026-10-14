# 任務卡：tests/test_kline_storage.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_kline_storage.py::test_append（R(t) 符號數 1）
  - tests/test_kline_storage.py::test_basic_write_read（R(t) 符號數 1）
  - tests/test_kline_storage.py::test_cache_index（R(t) 符號數 1）
  - tests/test_kline_storage.py::test_data_integrity（R(t) 符號數 1）
  - tests/test_kline_storage.py::test_data_validation（R(t) 符號數 1）
  - tests/test_kline_storage.py::test_metadata（R(t) 符號數 1）
- 主委分類 note：
  記錄器無紀錄、未實跑。整檔改寫：全檔無任何 assert，所有檢查失敗以 return False 表示（pytest 視為通過，空心）；test_metadata／test_append／test_data_validation 等依賴 test_basic_write_read 先寫入之共享目錄（順序耦合，單跑即無資料）；寫入 repo 內 ./data/test_kline_storage；fetch_binance_klines 打真實 Binance（:35-93）。修法：tmp_path 隔離、以固定 OHLCV 或 byte-faithful 錄製寫入，assert 寫讀往返相等、metadata 欄位、append 去重與 OHLC／taker_ratio 約束。
