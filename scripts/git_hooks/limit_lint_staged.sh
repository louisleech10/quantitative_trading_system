#!/usr/bin/env bash
# 防上限 checker 之 pre-commit 掛載（ICPERF SPEC v5.85 Task 0.6 (g)，L3；施工前空殼）。
# 施工後：以 `${LIMIT_LINT_PY:-venv/bin/python} ${LIMIT_LINT_SCRIPT:-scripts/limit_lint.py} --mode block --staged --root <repo 根>`
# 檢暫存區內容，退出碼原樣傳回（不吞）。
echo "limit_lint_staged.sh：Task 0.6 L3 尚未施工" >&2
exit 1
