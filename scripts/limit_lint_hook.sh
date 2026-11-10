#!/usr/bin/env bash
# 防上限 checker 之 PostToolUse:Edit|Write 掛載（ICPERF SPEC v5.85 Task 0.6 (g)，L3）。
# stdin＝hook payload；以 git HEAD 版為舊版，只檢產品路徑之新增或修改行；block 規則依語料收據
# tests/_golden/icperf/limit_lint_corpus_receipt.json。rc 2＝擋（PostToolUse 於寫入後回報，屬產出端早期攔截）。
# 非產品路徑、payload 無法解析 ⇒ rc 0。與 pre-commit（scripts/git_hooks/limit_lint_staged.sh）共用同一實作。
here="$(cd "$(dirname "$0")" && pwd)"
py="${LIMIT_LINT_PY:-$here/../venv/bin/python}"
[ -x "$py" ] || py="python3"
"$py" "$here/limit_lint.py" --hook --mode block
exit $?
