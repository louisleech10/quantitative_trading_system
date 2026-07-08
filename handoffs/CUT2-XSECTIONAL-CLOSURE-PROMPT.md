# 派工:Codex 複驗 fix-round 閉合 + 資料正確性簽核(唯讀)

你先前 code review verdict=FAIL(4 findings,見 `handoffs/CUT2-XSECTIONAL-CODEREVIEW-codex.md`)。Composer 已修(fix-round)。**你是原提出方,須逐項重跑同一反例確認真關閉**(章程§B8,不憑「已修」信任),再給資料正確性簽核。

## 逐項複驗(可證偽,重跑反例)
- **FIX-1 BLOCKING F4**:重跑你原 repro(短序列/`len_s≤horizon` 全 NaN)→ 現在是否 `raise InvalidInputError`(非 NO_RAISE 靜默)?看 `_enforce_cross_sectional_label_coverage` 開頭是否無條件擋 all-NaN + `len_s≤horizon`。
- **FIX-2 MAJOR F3 mutation**:`test_cross_sectional_oos_split_mutation_shrunk_purge_fails` 是否已改真動生產(`effective_horizon=0`→`SplitPairLeakageError`)?套套那條是否刪除?
- **FIX-3 MAJOR F1 容孔**:`_append_cross_sectional_labels` 對 kline 缺孔是否改為該列 NaN 不 raise(Option B)、有 kline 列仍斷言對齊無錯位?新測試 kline 挖孔是否驗證?
- **FIX-4 MINOR**:是否 `np.issubdtype(...integer)` 契約?

## 環境
`git diff` 看實作;可跑 `pytest tests/momentum/test_ic_cross_sectional_cut2.py tests/api/test_ic_analysis_service.py -q`。

## 輸出(寫 handoffs/CUT2-XSECTIONAL-CLOSURE-codex.md)
- 逐 finding 標 CLOSED / STILL-OPEN + 重跑證據(反例現在的行為)。
- 全關閉 → **資料正確性簽核**:`SIGNOFF: codex DATA-CORRECT PASS — <一句>`;任一未關 → `STATUS: BLOCKED` 列殘留。
- 結尾 STATUS。
