#!/usr/bin/env bash
# ICHC Task 5.1 — IC wiring 三規則機檢包裝（實作在 ic_wiring_check.py，規則見其檔頭）。
# 用法: bash scripts/ic_wiring_check.sh
# 強制機制: tests/momentum/Analysis/test_ichc_wiring_check.py 以 subprocess 常駐 pytest。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
PY="${REPO}/venv/bin/python"
[ -x "${PY}" ] || PY="python3"
exec "${PY}" "${SCRIPT_DIR}/ic_wiring_check.py"
