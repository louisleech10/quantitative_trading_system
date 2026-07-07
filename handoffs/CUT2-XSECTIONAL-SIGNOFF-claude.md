# 第二刀主體 資料正確性簽核 — Claude 獨立驗證腿

> 日期 2026-07-07 | Claude 獨立(非盲信執行端)。三方 scope=生成→計算→merge(多symbol對齊)→split→無洩漏。

## 我獨立做的檢查(非讀執行端報告)
1. **自跑驗收測試**:`pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py` → **18 passed**(Claude 本機實跑,非引執行端數字)。
2. **解耦**:`grep -r "from api\." momentum/` → 0。
3. **無假綠(diff 既有斷言)**:既有測試僅一處合理 caller 更新(`ic_train_test_split=False` 保 full-sample),matrix/validation 斷言未動;`test_ic_analysis_service.py` 純新增無刪斷言。
4. **F1 對齊正確性**(投偵察 receptor VERIFY:20260707T023954Z 已證修法):per-symbol datetime 對齊、forward log-return、末列 NaN、per-symbol 各異(無跨界污染)。
5. **F3 test-only 隔離(R1)**:污染測試(填 train 列 999)→ 輸出 hash 不變=真只用 test frame。**真 red-on-break**。
6. **F3 purge red-on-break**:mutation 已改真動生產(`_build_cross_sectional_global_split(effective_horizon=0)`→`SplitPairLeakageError`),非套套(原 Codex/Claude 疑點已閉)。
7. **F4 fail-closed**:守衛開頭無條件擋 all-NaN + `len_s≤horizon`(Codex BLOCKING 已修);monkeypatch 實關守衛證非假綠。
8. **F2 fail-closed**:單軸 labels_path raise「單軸不支援」,廣播分支已移除。
9. **scope**:特徵值/欄/列數未變(僅 label 對齊 + split 選列 + metadata);單幣 analyze 未動(2 個 pre-existing fail 於 HEAD 亦 fail,git stash 已驗,非本刀)。

## 殘留(非 blocking,登記)
- 既有 `test_ic_filter_orchestrator.py` 2 測試 pre-existing fail(單幣 analyze 合成 fixture 非連續時間軸撞 rows-purge 校驗)→ 與本刀正交,另立(非本刀引入,HEAD 已驗)。 VERIFY-EXEMPT:doc-example:cut2-signoff

SIGNOFF: claude DATA-CORRECT PASS — 獨立自跑 18 passed;F1 對齊/F3 test-only 隔離/F4 fail-closed/F2 fail-closed 均實測可證偽;無假綠、無 scope 越界;Codex BLOCKING 已閉合。
