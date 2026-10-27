#!/usr/bin/env bash
# timeout_write_guard.sh — NOCAP Task 0.2b：寫碼當下擋新增之時間上限（PreToolUse Edit｜Write｜MultiEdit）。
#   判定邏輯見 scripts/timeout_write_guard.py；rc 0 放行／2 擋。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY="${REPO_ROOT}/venv/bin/python"
[ -x "${PY}" ] || PY="python3"
exec "${PY}" "${SCRIPT_DIR}/timeout_write_guard.py"
