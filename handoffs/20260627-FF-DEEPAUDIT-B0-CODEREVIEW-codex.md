# FF 深稽 B0 code review — Codex

結論: **須修後再合併**。

## Review 範圍
- 依據: `docs/FF_DEEPAUDIT_P0_SPEC.md` Task 0.1/0.2、`docs/FF_DEEPAUDIT_P0_TODO.md` B0、`handoffs/20260627-FF-DEEPAUDIT-B0-REVIEW-PROMPT.md`。
- 被審: 未提交 diff + 新增 `tests/fixtures/DATA_MANIFEST.json`、`tests/fixtures/data_manifest.py`、`tests/fixtures/test_data_manifest.py`。

## 問題清單

### P0 — `DATA_MANIFEST` 測試未掛 `requires_kline`，PR smoke 逃生口失效
- 位置: `tests/fixtures/test_data_manifest.py:23`、`tests/fixtures/test_data_manifest.py:28`、`tests/fixtures/test_data_manifest.py:36`、`tests/fixtures/test_data_manifest.py:45`。
- 反例: `pytest --collect-only -q tests/fixtures/test_data_manifest.py -m "not requires_kline"` 仍收集 5 個測試。這些測試會呼叫 `validate_manifest()` 並讀 `data_cache/feature_klines/kline_cache.h5`，所以缺 kline 的 PR smoke job 仍可能 fail。
- 影響: 違反 Task 0.1 「PR job `-m "not requires_kline"` smoke」與 Task 0.2 真 kline correctness 測試分流設計。
- 修法建議: 將整個 `tests/fixtures/test_data_manifest.py` 或至少讀真實 kline 的 4 個 manifest validation/mutation 測試標記 `pytest.mark.requires_kline`；若保留 `test_manifest_file_is_versioned` 在 smoke，需確認它不讀實際 kline。

### P0 — B0 scope 外改動了 golden/baseline 二進位與數值檔
- 位置: `tests/golden/l65/test_inventory.txt:1`、`tests/golden/l65/tier2_reduced/d_star_ETHUSDT_1h_2000rows.json:2`、`tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.parquet`、刪除 `tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.BLOCKED`。
- 反例: `git diff --stat` 顯示 parquet 從 390697 bytes 變 445436 bytes；`d_star_ETHUSDT_1h_2000rows.json` 從 close/high/low/open/close_mean/log_close 換成 volume/close_std/volume_mean；`test_inventory.txt` 變成 `BLOCKER: no L6.5/preprocessing tests collected`。
- 影響: Task 0.1/0.2 只允許 marker + manifest 地基；這些 golden/baseline 變動改變數值/輸出大小，未在 B0 SPEC 中授權，也未附三方數據簽核或 §G v0/v1 差異表。這是資料正確性紅線。
- 修法建議: B0 diff 中移除上述 golden/parquet/BLOCKED 變動；若需要重凍，應放到 §G 指定的 B0 後/B1 前 baseline freeze 流程，帶差異表與簽核。

## 逐項複查

1. 防假綠: **部分 PASS，仍有 P0 scope 問題**。16 個遷移檔主要是加 `requires_kline` 與 `pytest.skip`→`pytest.fail`，未看到刪除既有 `assert` 的 diff；但 golden/parquet 變動不是 marker 遷移，不能當作 B0 附帶變更。
2. marker 機制: **FAIL**。已註冊 `pytest.ini:35`，多數 correctness 測試可被 `-m "not requires_kline"` 排除；但 `tests/fixtures/test_data_manifest.py` 漏 marker，逃生口仍會跑真 kline manifest validation。
3. DATA_MANIFEST: **核心校驗 PASS，分流 FAIL**。`DATA_MANIFEST.json` 為 30 筆、10 symbols × {1h,4h,12h}；sha256/缺項/row_count 三 mutation 均可證偽。sha256 以 h5py dataset bytes 計算，對應目前 storage manager 讀法合理。
4. 解耦: **PASS**。`rg "from api\\." momentum` 無結果；新增 B0 碼未讓 `momentum/` import `api/`。
5. 其他盲點: `tests/conftest.py:75` 只捕捉 `ManifestValidationError`；`verify_kline_entry()` 在 manifest 有 entry 但實際 dataset 缺失時可能由 `compute_dataset_fingerprint()` 丟 `KeyError`，最後變 pytest ERROR 而不是明確 `pytest.fail`。這不是主阻塞，但建議一併收斂成 fail 訊息。

## 實測摘要
- `pytest -q tests/fixtures/test_data_manifest.py`: 5 passed。
- `pytest --collect-only -q tests/fixtures/test_data_manifest.py -m "not requires_kline"`: 5 tests collected，證明漏標 marker。
- `pytest --collect-only -q tests/feature_engineering -m requires_kline`: 66 selected / 586 deselected。
- manifest 快查: entries=30、unique keys=30、symbols=10、timeframes=`12h/1h/4h`。
- `rg "from api\\." momentum`: 0 results。

STATUS: DONE
