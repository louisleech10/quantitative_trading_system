# 任務:code review FF 深稽 B0 diff(Codex,跨家族複查)

實作者=Composer 2.5。被審=未 commit 的 B0 diff(`git diff` + 新檔 `tests/fixtures/DATA_MANIFEST.json`/`data_manifest.py`/`test_data_manifest.py`、`pytest.ini`、`tests/conftest.py` + 16 個遷移 marker 的測試檔)。
依據 SPEC/TODO Task 0.1+0.2。Claude 已初驗(無斷言放寬、manifest mutation 可證偽、entries=30、v8 失敗為 pre-existing IC 非 B0)。

你複查(每點 PASS/問題+反例):
1. **防假綠**:16 個遷移檔有沒有任何放寬/刪斷言、或把 correctness 測試默默改成 skip 仍存在?marker 遷移是否只加 marker + skip→fail,未動測試邏輯?
2. **marker 機制**:`requires_kline` fixture 缺檔真 FAIL 非 skip?`-m "not requires_kline"` 逃生口正確?有沒有該掛 marker 卻漏掉、或不該掛卻掛了(把非 correctness 測試也硬 FAIL)?
3. **DATA_MANIFEST**:校驗器 sha256/缺項/row_count 三 mutation 真可證偽?entries 是否確為 10×3=30 真實 symbol/TF?sha256 計算方式合理(對應 storage manager 讀法)?
4. **解耦**:新碼有無 `momentum/` import `api/`?logging 用對?
5. 其他結構/正確性盲點。

輸出寫 `handoffs/20260627-FF-DEEPAUDIT-B0-CODEREVIEW-codex.md`:結論(可合併/須修)+ 問題清單(檔:行+反例+修法)。只寫 review 檔。完成 STATUS: DONE。
