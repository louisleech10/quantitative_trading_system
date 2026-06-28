# 派工:FF 深稽 B0 實作(Composer 2.5)

讀:`docs/FF_DEEPAUDIT_P0_SPEC.md` + `docs/FF_DEEPAUDIT_P0_TODO.md`(已過兩輪雙家族 adversarial+戳記)。本批只做 **Task 0.1 + Task 0.2**(治理地基),不碰 B1/B2。

## §0 鐵律(違反即退回)
- `momentum/` 內 logging 用 `from momentum.core.logging import get_logger`(**禁** import `api.core.logging`,解耦 Rule 1)。
- 真實 kline:`data_cache/feature_klines/kline_cache.h5`(10 symbols × {1h,4h,12h};**用 storage manager `create_kline_storage_manager(cache_dir='data_cache/feature_klines')` 讀**,非 pd.HDFStore——該檔非 pandas 格式)。禁合成 fixture 代替 correctness。
- mutation TDD-first:聲稱驗正確性的測試,先寫 failing probe 證明「改壞會 FAIL」再寫實作;驗收報告附 fail 摘要。
- 防假綠:不放寬既有斷言。
- 環境已修(numpy 1.26.4 + tables 3.9.2 連 hdf5 320);跑測試用 `source venv/bin/activate`。

## Task 0.1 — requires_kline marker + 雙 job
- `pytest.ini` 註冊 `requires_kline` marker;`tests/conftest.py` 提供 `requires_kline_data(symbol, tf)` fixture,缺檔 `pytest.fail(...)` 非 `pytest.skip`。
- skip→marker 遷移:見 TODO Task 0.1 清單(`rg 'pytest\.skip.*kline' tests/` 補全);只 correctness 類掛 marker,非 correctness 列保留理由。
- 驗證:暫移走某 kline → 掛 marker 測試 FAIL(非 skip);`pytest -m "not requires_kline"` 不收集。mutation 附 fail 摘要。

## Task 0.2 — DATA_MANIFEST.json + 校驗器
- 新建 `tests/fixtures/DATA_MANIFEST.json`(10 symbol × 3 TF:symbol/TF/最少列數/sha256 指紋)+ `tests/fixtures/data_manifest.py` 校驗器 + `tests/fixtures/test_data_manifest.py`。
- 驗證(三 mutation 必 FAIL):改 sha256 / 缺 symbol×TF / row_count below min。
- kline 二進位禁納 repo,只存指紋。

## 收尾
- 交接寫 `handoffs/20260627-FF-DEEPAUDIT-B0-RESULT.md`(跑了哪些測試/測什麼/通過條件/mutation fail 摘要),不覆寫根 HANDOFF。
- 完成輸出 STATUS: DONE 或 STATUS: BLOCKED — <原因>。兩輪解不了的疑問→BLOCKED 不 solo 硬幹。
