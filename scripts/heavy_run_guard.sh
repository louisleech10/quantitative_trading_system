#!/usr/bin/env bash
# heavy_run_guard.sh — NOCAP Task 0.3：重型命令須背景執行且經共用監看（PreToolUse Bash）。判定見 scripts/heavy_run_guard.py。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY="${REPO_ROOT}/venv/bin/python"
[ -x "${PY}" ] || PY="python3"
exec "${PY}" "${SCRIPT_DIR}/heavy_run_guard.py"
