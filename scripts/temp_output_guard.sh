#!/usr/bin/env bash
# temp_output_guard.sh — 要再用之檔不得落在系統暫存（PreToolUse Bash／Edit／Write／MultiEdit；全專案）。判定見 scripts/temp_output_guard.py。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/temp_output_guard.py"
