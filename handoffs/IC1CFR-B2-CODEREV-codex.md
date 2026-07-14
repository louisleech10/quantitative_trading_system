# IC1CFR-B2 Code Review — Codex
task-id: IC1CFR-B2 | date: 2026-07-15 | scope: Frozen TODO Phase 2 + `git diff HEAD` + RESULT；唯讀，僅本檔產出

## BLOCKING
1. **[P1, confidence 10/10] 缺鍵三態未全警示**：`FactorReturnChart.tsx:141-154` 對 `data==null` 顯示 `factor-return-empty`「暫無 Factor Return 資料」，不是指定下架警示；現測 `FactorReturnChart.test.tsx:69-77` 反而固化此錯誤。獨立 `/tmp` probe 以 union/自造 legacy finite/缺鍵三態渲染，僅缺鍵失敗。修正 null branch 為同一 unavailable 文案並更新測試後才可過 Gate。

## 核驗結果
- 兩圖 legacy finite：自造不同 payload（9.8765/17.5308）實渲染均無有限值、無 Recharts；union 佔位亦警示。Equity 缺鍵警示正確；Return 缺鍵為上列 blocker。
- `types.ts:2120,2236-2262`：`ICReport.factor_returns` 真接 `FactorReturnDataOk | FactorReturnDataUnavailable`，不是旁路型別；`npm --prefix frontend run build` exit 0（tsc 通過）。
- M3/M4：在 `/tmp` 複本把兩 extractor 恢復有限點後，兩個具名 probe 均轉紅；基線指定 vitest 3 files = 20 passed。
- producer `monotonicity_tester.py` 未動；兩元件 production 路徑無 fallback 數值。

## scope 擴張裁決
- (a) **ACCEPT，必要 B1 enabler**：phase26 把 generic skip/timeout/error oracle 移至 `factor_centrality`，保留原分類斷言；另新增 FR unavailable/count 斷言。測試函式數未減，非放寬假綠。
- (b) **ACCEPT，必要 suite-isolation enabler**：redirect 僅 setup 持有、deactivate 改無條件 finally；spy 與 API 內容斷言未刪。33 個 resolved nodeid 仍 33/33 可收集，無 skip/deletion。
- (c) **ACCEPT，必要 gate parser 修正**：合成 probe 證 logger `pkg.mod:file.py` 被拒，真 `ERROR tests/...py`、`ERROR collecting tests/...py`、`FAILED ...::test` 仍被解析；未放寬 baseline 差集。

ASSUMPTIONS_VERIFIED: Frozen TODO reconcile 三方 APPROVED；受審 test 無刪除；scope 三擴張皆由實際控制流/diff/probe 核對。
TESTS_RUN: vitest 指定 3 檔→20 passed；frontend build→exit0；`python scripts/ic1cfr_stopgap_freeze.py --check-nodeids`→exit0, baseline77/current44/new0/resolved33；resolved 33 nodeids collect→33 collected；`git diff --check`(受審檔)→exit0；`/tmp` M3/M4 mutation→具名測試各紅；獨立三態 probe→2 passed/1 expected contract failure。
FAILURES_SEEN: 獨立 probe 證 FactorReturn 缺鍵未警示（未修，blocking）；M3/M4 mutation failure 為預期自證。
SCOPE_CHANGES: review 僅新增本檔；工作樹受審檔未改。
NUMERIC_OR_SCHEMA_IMPACT: B2 下架兩圖有限值；FactorReturnData 改 §U union；本 review 無 runtime/schema 改動。
CODE-REVIEW: REJECT (1 BLOCKING)
