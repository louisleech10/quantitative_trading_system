#!/usr/bin/env bash
# 防上限 checker 之 pre-commit 掛載（ICPERF SPEC v5.85 Task 0.6 (g)，L3）。
# 以 `${LIMIT_LINT_PY:-venv/bin/python} ${LIMIT_LINT_SCRIPT:-scripts/limit_lint.py} --mode block --staged --root <repo 根>`
# 檢暫存區內容（相對 HEAD 之新增或修改行），退出碼原樣傳回（不吞）。
# 兜底 Bash 重導、外部編輯器、委員 CLI 等不經 Edit／Write 之寫入；與 PostToolUse（scripts/limit_lint_hook.sh）同一實作。
root="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "limit_lint_staged.sh：非 git 工作樹" >&2; exit 1; }
py="${LIMIT_LINT_PY:-$root/venv/bin/python}"
[ -x "$py" ] || py="$(command -v python3)"
"$py" "${LIMIT_LINT_SCRIPT:-$root/scripts/limit_lint.py}" --mode block --staged --root "$root"
exit $?
