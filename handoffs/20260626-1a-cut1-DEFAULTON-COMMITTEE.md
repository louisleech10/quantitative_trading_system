# 1a cut1 — default-ON 語義 委員會諮詢（OOS 不可行時該怎麼辦）

## 背景
三方數據簽核 PASS，G-OLD/G-NEW 已凍。依使用者定「驗證 PASS 後預設開啟」，我把 `ICConfig.ic_train_test_split` 預設翻 True。

## 問題（實測）
- `min_test_rows = max(rolling_windows)+purge = 126+5 = 131`。
- 既有 IC API 測試用**小/合成 fixture**（n≈300→test≈60 < 131；或 timestamps=`np.arange`（1-spaced）非 12h 規律）。
- default ON → flag-on OOS 路徑對這些 fixture：① 列不足 → `_build_holdout_split_plan` 回 `SkippedResult`（整個分析 skip）；② 不規律 timestamp → `validate` raise `TimestampDiscontinuityError`。
- 結果：**7 個原本 full-sample 下 PASS 的 IC API 測試現在 skip/fail/timeout**（既有 329 momentum 測試未破）。
- 待查附帶疑點：API task 為何 timeout 而非 fast-fail（疑 service 對 skipped/raise 的 task 狀態傳遞）——請一併判斷是否有 task-status propagation bug。

## 決策點：flag ON 但 OOS 不可行時的語義（三選一）
- **(A) 優雅回退 full-sample + 明確標記**（Claude 推薦）：OOS 不可行（列不足/不規律 ts）時，回退全樣本 IC，但結果標 `ic_train_test_split:{applied:false, reason:insufficient_data|irregular_timestamps}`。理由：default-ON 不該讓小/legacy run 整個壞掉；correctness 靠透明標記維持（消費端知道這是 full-sample 非 OOS）；不強迫每個 caller opt-out。leakage 保證在 OOS 適用處成立，不適用處透明等同 legacy。**風險**：full-sample=舊（會偷看）行為，須確保標記不被當成 OOS 誤用。
- **(B) 維持 SkippedResult**：小資料整個不分析。安全（不產偷看數字）但 UX 差，且現有 API 測試/小 run 全壞，需逐一 opt-out（flag off）。
- **(C) 合成/plumbing 測試顯式 flag off**：default ON 不動，把不測 IC 正確性的 plumbing 測試改 legacy 模式。但 default-ON 對任何小/合成 caller 仍會壞，治標。

## 請各位（獨立）回答
1. 三選一（或更好方案）+ 理由，特別針對**correctness（會不會引入隱性洩漏）**。
2. (A) 若採，回退標記欄位設計 + 如何防「full-sample 被誤當 OOS」。
3. API timeout 是否反映 task-status propagation bug（值得修）？
4. 對 leakage 契約鐵律的影響評估。

輸出寫各自檔 `handoffs/20260626-1a-cut1-DEFAULTON-{CODEX,COMPOSER}.md`，STATUS: DONE。
