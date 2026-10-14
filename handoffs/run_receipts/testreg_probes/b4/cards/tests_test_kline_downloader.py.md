# 任務卡：tests/test_kline_downloader.py

- 組：G12；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r16/synth.md
- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r16-{codex,composer,grok}.md
- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）：
  - tests/test_kline_downloader.py::test_1_single_download_ethusdt（R(t) 符號數 3）
  - tests/test_kline_downloader.py::test_2_different_timeframe_btcusdt（R(t) 符號數 3）
  - tests/test_kline_downloader.py::test_3_batch_download（R(t) 符號數 3）
  - tests/test_kline_downloader.py::test_4_storage_integration（R(t) 符號數 3）
  - tests/test_kline_downloader.py::test_5_provider_registry（R(t) 符號數 3）
  - tests/test_kline_downloader.py::test_6_error_handling（R(t) 符號數 3）
- 主委分類 note：
  記錄器無紀錄、未實跑。整檔改寫：六支之 assert 全包在 try/except Exception 內，失敗被吞後 return False（:116-118、:433-435），pytest 一律判綠（假綠）；test_3 只 log 不斷言；test_6 期望 ValueError 未拋時只 return False；打真實 Binance 並寫入 cwd ./test_data。修法：BinanceProvider 以替身（固定 OHLCV）＋tmp_path，移除吞例外，改 assert 與 pytest.raises(ValueError)；OHLC 檢查改全量而非前 10 根（:104）。
