# 1a cut1 — default-ON 語義 委員會諮詢（CODEX 獨立回答）

## 1. 三選一 + correctness 判斷

選 **A'：回退 full-sample，但必須是「顯式 legacy evaluation」，不是「OOS 成功但資料少」**。

理由：
- B correctness 最硬，但 default-ON 後會讓小資料/API plumbing caller 大量壞掉，且目前 `analyze()` 回 skipped 會產生非完整 report，破壞 API consumer。
- C 只修測試，不修產品語義；任何小資料 caller 仍會踩同一坑。
- A 可接受，但前提是 **回退結果絕不能被 OOS 消費端誤讀**。full-sample 本質是 legacy 口徑，會有舊的 train/test leakage 風險；它只能表示「本 run 未做 OOS」，不能表示防洩漏契約成立。

我建議把 A 收斂成 A'：default ON 表示「優先嘗試 OOS」；若 OOS 不可行，輸出完整 legacy report，但 metadata/summary/filter_log 明確標成 non-OOS fallback。

## 2. A 若採：欄位設計與防誤用

建議 metadata：

```json
"ic_train_test_split": {
  "enabled": true,
  "attempted": true,
  "applied": false,
  "evaluation_scope": "full_sample_legacy",
  "reason": "insufficient_data|irregular_timestamps|test_rows_below_rolling_warmup",
  "error_type": "INSUFFICIENT_DATA|TIMESTAMP_DISCONTINUITY",
  "train_rows": 96,
  "test_rows": 19,
  "min_test_rows": 131,
  "oos_contract": "not_applicable",
  "leakage_contract": "legacy_full_sample_not_oos"
}
```

防誤用要求：
- OOS 成功時才允許 `evaluation_scope: "test"` / `scope: "test"`。
- fallback 時不要寫 `scope: "train_test_holdout"`，不要寫 `train_time_bounds/test_time_bounds` 當成已生效 split。
- `summary_table` 每列最好加 `eval_status: "unknown_legacy"` 或 `evaluation_scope: "full_sample_legacy"`；若 artifact v2 有 `selection_scope_id`，應用 `full_sample_legacy:<config_hash>`，不要用 OOS scope id。
- UI/API 若顯示「OOS」徽章，必須只看 `applied === true`，不能只看 `enabled === true`。
- golden/contract test 要覆蓋：insufficient rows fallback 產完整 report、metadata applied false、top-features/refilter/export 不把它當 OOS。

## 3. API timeout 是否是 task-status propagation bug？

目前讀碼判斷：**不是典型 task terminal-state propagation bug**。

`api/services/ic_analysis_service.py` 對例外會設 `failed`；對 `analyze()` 回傳 `{"status":"skipped"}` 則會設 task `completed` 並存 result。問題是 skipped result 不是完整 report，後續 API 測試期待 `metadata/summary_table/filtered_df/_report/_ic_cache`，因此會 fail/404/空結果。timeout 較可能來自測試等待或 downstream 行為不符合完整 report 假設，而不是 task 永遠 running。

但值得修一個語義 bug：IC task status 不該把「主分析 skipped」無條件標成普通 completed。若保留 skipped，status 應是 `skipped` 或 `completed_with_skip`；若採 A'，則回傳完整 report 並標 fallback。

## 4. leakage 契約影響

A' 不削弱 OOS leakage 契約，因為它不聲稱 OOS 已執行。契約應拆成兩層：

- `applied=true`：嚴格 OOS 防洩漏契約成立，train-only fit、purge、test-only IC/stat/redundancy 必須全部成立。
- `applied=false`：OOS 契約不適用，結果是 legacy full-sample，允許為相容性輸出，但必須被下游視為不可作 OOS correctness 證據。

最大風險不是 full-sample 本身，而是 **full-sample 被標成 OOS**。所以我反對靜默 fallback；支持顯式 fallback + 下游只認 `applied === true`。

HANDOFF_NOT_UPDATED: read-only sandbox；本回合未寫 handoffs 檔。

ASSUMPTIONS_VERIFIED: 讀到 `ICConfig.ic_train_test_split=True`；`_build_holdout_split_plan` rows 不足回 `SkippedResult`；timestamp discontinuity 由 split contract raise；`analyze()` 對 split/stage4 skipped 直接回 skipped dict；service 對 skipped dict 仍標 task completed。
TESTS_RUN: none（read-only 諮詢，未執行測試）
FAILURES_SEEN: none
SCOPE_CHANGES: none
NUMERIC_OR_SCHEMA_IMPACT: 建議新增 metadata/report 標記；不建議改數值計算口徑，僅明確區分 OOS vs legacy full-sample。
STATUS: DONE