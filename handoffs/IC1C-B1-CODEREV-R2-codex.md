# IC1C-B1 Code Review R2 (Codex, 2026-07-14)

## Verdict
- 4/4 原 BLOCKING 均 CLOSED；rework delta 未見新 blocking。

## Closure
1. CLOSED — `/tmp` 唯讀重跑 `freeze_new()`：`GROSS_ONLY:4+COST_ENABLED:4+SKIPPED:3`，雙樹 `result`/`result_cost_enabled`；新檔與凍結 `g_new.json` sha256 同為 `d77ce573...d12151e`，`cmp` byte-equal。
2. CLOSED — allowlist 為腳本常數且先驗後建 manifest；`self_test_allowlist_rejects_bogus()` PASS。對實際 G-NEW 注入 `bogus_unapproved_field`+`bogus_summary`，validator 回兩條 `added unapproved key`；未核可變更確實紅。
3. CLOSED — `test_compute_net_factor_return_empty_aligned` 已移植 T1，實跑通過；RESULT 改寫理由表明列其為「非錯舊斷言」及保留原因。
4. CLOSED — RESULT 的 `SCOPE_CHANGES` 已明列 rework 與 session 副作用，不再稱 none。mtime 邊界顯示 runtime/config/T3/export 均早於首輪 review；其後實作 delta 為 freeze 腳本、T1、重凍 artifacts/RESULT，另有必需 handoff/audit 留痕；`test_inventory.txt` 現已 clean。

## Delta scan
- `git diff --check -- scripts/ic1c_freeze_baseline.py tests/momentum/Analysis/test_net_ic_analyzer.py` → PASS。
- allowlist 同時限制 feature added/removed/value-change、summary added/removed/value-change、required summary values；SKIPPED 另受精確 schema/reason 檢查。
- workspace 仍有首輪 B1 runtime diff與既有 `.claude/*` 變動；本輪 reviewer 未改 implementation/HANDOFF/data_cache。

ASSUMPTIONS_VERIFIED: SPEC/TODO reconcile checker 均三家 APPROVED；真 kline temp freeze byte-equal；四條反例逐條實跑/核對。
TESTS_RUN: `venv/bin/pytest -p no:cacheprovider <T1+SCHEMA+T3+export> -q` → 59 passed；target empty_aligned → 1 passed；allowlist self-test+actual G-NEW bogus probe → PASS/兩項拒絕；temp freeze+`cmp`+`shasum -c` → PASS。
FAILURES_SEEN: 首次 temp freeze 因 `OUT_DIR` 不在 `REPO_ROOT` 於 `relative_to` 失敗；第二輪僅將輸出根與 git-head accessor 指向 `/tmp` 後完整 PASS。早先 heredoc/長鏈通道無輸出，拆命令後各驗證通過。
SCOPE_CHANGES: reviewer 僅新增本檔；未改 implementation、根 HANDOFF 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: review-only；確認重凍 G-NEW 雙樹 schema 與既有凍結檔 byte-equal。
CODE-REVIEW-R2: APPROVE
