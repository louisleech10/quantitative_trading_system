# VERDICTGATE B3 閉合確認 R2 — codex
task-id: 20260911-VERDICTGATE-B3-REVIEW-R2

## CODEX-R2-P1-01
**斷言**: K5 修前 runtime reproduction 受 repo PreToolUse debt gate 阻擋，故本家不能宣稱 B3 已完成獨立全量閉合。
**碼證**: 3 次隔離執行均被 `[GATE BLOCKED] kind=dispatch ... OPEN 債` 拒絕；修前 blob 實跑讀取 `git cat-file blob d6c52c27:scripts/ticket_batch_check.sh | rg ...` 顯示舊版仍為 `git rev-list ... 2>/dev/null` 無 fail-closed 分支。
**來源摘要**: handoffs/20260911-VERDICTGATE-B3-CLOSURE-R2-BRIEF.md#ecbe61a267eb
此為程序驗證阻塞，非新增程式碼漏洞；K1–K4 與 K5 修後行為均已通過實跑。

K1/K2/K3：`venv/bin/pytest -q tests/governance/test_verdictgate_p3.py` → 47 passed；刪除生產檔、全 delete upstream、零行 fallback、混合 delete、`ROOT/b2oops` commit/push 反例均在該檔通過。
K4：p3 47/47；A6/A8/A14/A15/A16/A18/A19/A21 direct tests 存在且通過；A7 `test_helper_legacy_review_like_without_review_literal`、A9 consult 對照 p2 通過；A10 `test_12_audit_append_impl_token_issued_missing_root_rejected` p1 通過。
K5 修後：`test_33_first_push_zero_range_checks_all_commits`、`test_33_unresolvable_range_fails_closed` 均通過；修後腳本行 98–100 正規化全零 range 並對 rev-list 失敗 rc=1。
debt_clear：3 個 verdict_rejected/reregister 邊界測試 → 3 passed；register-output 先經 `verdict_parse.sh`，再由 debt_clear 驗同 round/family、較晚 sequence 與當前 SHA，無「只重登記舊檔」縫。

ASSUMPTIONS_VERIFIED: R10 synth 三家 APPROVED stamp；R1 synth sha256=eb18a01958683bc053948bf5be3076b3dce6477d83fefd8bc257306208006f0b；tracked source 未改。
TESTS_RUN: p3 47 passed/50.65s；p3 窄反例 17 passed/18.29s；debt_clear 3 passed/4.29s；p2 2 passed；p1 1 passed；`git diff --check` rc=0；K5 修前 runtime probe 未驗證（repo gate rc=2）。
FAILURES_SEEN: K5 修前隔離 runtime probe 連續受 PreToolUse debt gate 拒絕；無程式碼測試失敗。
SCOPE_CHANGES: 僅新增本交件檔；未改 tracked source、tests、HANDOFF.md 或 data_cache。
NUMERIC_OR_SCHEMA_IMPACT: none。
OUTPUT_ARTIFACT: handoffs/20260911-verdictgate-b3-review-r2-codex.md
TMP_CLEANUP: 本輪暫存輸出已清理；`/private/tmp/claude-501` 保留。
RECONCILE-STAMP: codex APPROVED 2026-09-11 sha256:eb18a01958683bc053948bf5be3076b3dce6477d83fefd8bc257306208006f0b task:20260911-VERDICTGATE-B3-REVIEW-R2
VERDICT: blocked
BLOCKED-BY: CODEX-R2-P1-01
CLOSED:
STATUS: BLOCKED — K5 修前 runtime reproduction 未獲 repo gate 放行
