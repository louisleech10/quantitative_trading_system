# INSTREV Phase B Review Close — Codex

## 結論
- REVIEW-1: STILL-OPEN. Auto-fix 對非 UTF-8 staged md 已不改 index，但 checker 仍因同一 blob traceback crash。
- REVIEW-2: CLOSED. Staged executable md auto-fix 後 mode 保留 100755。
- REVIEW-3: CLOSED. explicit task-id 測試已移除放行式斷言，且 tmp mutation 會 fail。
- OVERALL VERDICT: BLOCKED — REVIEW-1 尚未滿足「checker 不因非 UTF-8 staged markdown crash」。

## 重跑輸出
- `source venv/bin/activate && pytest tests/governance/test_precommit_autofix.py tests/governance/test_dispatch_wrapper.py -v --tb=short` → 13 passed in 2.21s。
- 非 UTF-8 反例(tmp git repo): before=`616263ff2020200a`, after=`616263ff2020200a`, mode=`100644`, hook rc=1；stderr 為 `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff...` traceback，來源 `_git_staged_blob()` → `_run_git(["show", ":docs/bad.md"])` text decode。
- executable mode 反例(tmp git repo): rc=0, before_mode=`100755`, after_mode=`100755`; bytes 從 `...747261696c696e672020200a` 變 `...747261696c696e670a`，只移除一般 prose trailing spaces。
- explicit task-id mutation(tmp copy): 將 `scripts/dispatch.sh` 的 `have_task_id=1` 改為 `have_task_id=0` 後跑 `pytest ...::test_dispatch_explicit_task_id_not_overridden -q --tb=short` → rc=1；失敗摘要 `assert '20990101-explicit-id' in ['20260706-x']`。
- `rg -n "returncode in \\(0, 1\\)|returncode in|\\bor proc\\.returncode\\b" tests/governance/test_dispatch_wrapper.py` → rc=1/no matches。

## Scope / Notes
- 本次只覆寫本檔；反例 repo 與 mutation 均在 `/tmp`，未 git checkout，未寫 `.claude/gate/audit.log`。
- 既有 worktree 開始前已有 Phase B diff 與 `.claude/gate/audit.log` 變更；本次未回退或改動。
