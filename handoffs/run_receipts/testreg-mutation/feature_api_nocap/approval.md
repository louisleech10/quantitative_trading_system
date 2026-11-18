# TESTREG 改寫核可：tests/api/test_feature_api.py::test_feature_extraction_api（移除 60 秒等候上限）

- 目標：`tests/api/test_feature_api.py::test_feature_extraction_api`（原地改寫，compare＝同名測試）。
- 改寫內容：`for _ in range(60): … time.sleep(1) … else: pytest.fail("任務 60 秒內未完成")` 改為以
  `tests._nocap_wait.ProgressWait` 輪詢至非 running（不設上限；卡死由狀態未變且 CPU 無進度判定並留堆疊，NOCAP Task 2.2），
  之後 failed ⇒ `pytest.fail(任務失敗)`、其他非 completed 終態 ⇒ `pytest.fail(附 status／error)`、completed ⇒ 原
  `n_features >= 20` 斷言。另：模組 autouse fixture 將路由層特徵儲存改指 tmp（不寫 data_cache/features）。
- 核可來源：TESTSEL 收尾 I2 主委裁定（2026-11-13，對話）：退回「測試內時間上限違反 NOCAP」；選 (i)「走 TESTREG rewrite
  收據程序（不保留不實訊息）」。V19 判減之唯一實質元素＝`pytest.fail("任務 60 秒內未完成")`（其餘 7 項為佔位編號位移）。
- 收據：`receipt.json`（receipts.mutation；8 個只改 api/ 之 mutant，舊目標 8 個斷言位置各被殺於 call 期，改寫後之同名測試
  亦皆被殺；m8〔任務停在 running〕之改寫版由 ProgressWait 判卡死失敗）。
