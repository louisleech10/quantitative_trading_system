# PA-CUMSUM review — codex
task-id: `20260818-PACUMSUM-X-REVIEW-R23`; target: `7d516540`; review scope: brief 段 A–C；未改碼／未 commit／未 push。
## Verdict：需修補後合併
### 段 A
公式、`final_return_pct` ×100 與 `proba > threshold` 持倉語意正確；空手期複利乘 `1+0` 不變也正確，但只在單一、按時間排列的投資序列成立。舊鍵在執行期消費者已清除；全 repo 仍有文件舊契約。
### 段 B
預設複利對單一標的帳戶淨值合理，不能套用到多標的 batch。actual-return 的 NaN 仍被 route `fillna(0)`，直接 engine 呼叫則 raise；inf 會未捕捉成 500。`y_pred_proba` NaN 應明確 raise/回 4xx，不應靜默空手。
### 段 C
5 條測試可證偽：把 compound `cumprod` mutation 成 `cumsum` 後實跑為 4 failed、1 passed；baseline 為 5 passed。前端切換新增行為沒有單測，建議補最小切換 final 值不同案例。
## CODEX-R23-P1-01
**斷言**: 多標的 batch 的所有 symbol 報酬會被當成同一帳戶連乘，compound equity 數字因此可正常回傳但不代表任何有定義的組合。
**碼證**: `xgboost_batch_service.py:223-248,599-658,1005-1008` 明確支援多 symbol 且保留 per-row symbols；`pattern_analysis.py:1047-1051` 將整欄送入；`prediction_analyzer.py:177` 對整欄 `np.cumprod`。RECHECK: 同一 timestamp 兩 symbol `[+10%,-10%]` 的結果會是 `-1%`，但 API 沒有權重/分組契約。
**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8
[MAJOR] 信心度=High；跨資產 row 順序和 symbol 邊界被吞掉，預設複利會污染多標的績效。修法是只允許單 symbol，或回傳 per-symbol／明確權重的 portfolio schema；不可只在前端改標籤。
## CODEX-R23-P1-02
**斷言**: `y_pred_proba` 含 NaN 時目前被無聲轉成空手，會把缺失預測當成低於 threshold 並改變績效。
**碼證**: `prediction_analyzer.py:168-170` 只有 `y_pred_proba > threshold`、沒有 finite gate；VERIFY: `venv/bin/python -c ...` → `[0.0, 0.2] [0.0, 0.2]`，NaN row 未 raise。RECHECK: 將第一個 proba 改為 NaN，應先拒絕而非輸出零報酬。
**來源摘要**: momentum/Analysis/prediction_analyzer.py#60defe07cff8
[MAJOR] 信心度=High；這是靜默資料品質錯誤，且新 actual-return gate 並未涵蓋 prediction gate。修法是 `np.isfinite(y_pred_proba)` fail-closed，route 將資料錯誤轉為明確 4xx；另決定 actual-return `fillna(0)` 是否仍允許。
## CODEX-R23-P2-03
**斷言**: 新 API 欄位的公開契約仍不完整且 active roadmap 自相矛盾，消費者可依舊鍵或不明語意實作。
**碼證**: `EquityCurveData` bare annotations 在 `api/models/pattern_analysis_models.py:503-512`；VERIFY schema → 7 個欄位 description 全為 `null`；`docs/ROADMAP.md:72-74`、`docs/IC1D_ATTRIBUTION_SPEC.md:281,288` 仍寫 `strategy_returns`/cumsum，target commit 未改 `docs/API_SPECIFICATION.md`。
**來源摘要**: api/models/pattern_analysis_models.py#8c41e1a2fbc3
[MINOR] 信心度=High；runtime route/frontend 已同步，故非 P1 runtime blocker；修法是 Field descriptions／API response example 及 active docs 同步，Archived 文件須明標歷史版本。
### A11y／測試建議（非另列 finding）: `NaiveStrategyEquityChart.tsx:58-65` 宣告 tablist/tab 但沒有 tabpanel/aria-controls 或箭頭鍵導覽；補 component test：compound 顯示 `strategy_compound` 終值，點 simple 後顯示不同 `strategy_simple` 終值；build 已通過（既有 5 個 hook warnings）。
ASSUMPTIONS_VERIFIED: 公式／百分比／threshold 語意；route fillna；runtime 舊鍵 grep；多 symbol caller；API schema descriptions；mutation 可使 compound 測試變紅。
TESTS_RUN: `venv/bin/python -m pytest tests/momentum/Analysis/test_prediction_analyzer_equity.py -q` → 5 passed；isolated mutation → 4 failed/1 passed；`npm run build` → compiled successfully；decoupling baseline → BASELINE OK。
FAILURES_SEEN: mutation 失敗為預期且已在 isolated `/tmp/codex-pacumsum-review-Eyszgf` 完成；主工作區無 mutation。
SCOPE_CHANGES: none；未改 code、測試、docs、git history 或 data_cache；產出檔：`handoffs/20260818-pacumsum-review-codex.md`。NUMERIC_OR_SCHEMA_IMPACT: 發現多 symbol compound 數值語意與 API 欄位文件風險；本次未修改輸出 schema。
STATUS: DONE
