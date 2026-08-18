#!/usr/bin/env bash
# GAP-1 Task 2.4 — 策略層 wiring 閘門包裝（實作在 strategy_wiring_check.py：AST 比對契約 ↔ report.py／strategy_validation/*.py）。
# 用法: bash scripts/strategy_wiring_check.sh   （exit 0 全綠／1 違反／2 缺檔或語法錯）
# 強制機制: tests/momentum/Analysis/strategy_validation/test_wiring_check.py 以 subprocess 常駐 pytest（含六條 mutation）。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY="${REPO}/venv/bin/python"
[ -x "${PY}" ] || PY="python3"
exec "${PY}" "${SCRIPT_DIR}/strategy_wiring_check.py" "$@"
