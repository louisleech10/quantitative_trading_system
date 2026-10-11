#!/usr/bin/env bash
# testreg_write_guard.sh — TESTREG 產出端登記檢查（PostToolUse Edit|Write；docs/TESTREG_SPEC.md Task 1.5）。
#
# 用法：
#   bash scripts/testreg_write_guard.sh     # hook 模式（stdin＝PostToolUse payload，取 .tool_input.file_path）
#   rc 0＝非管轄之檔，或檢查通過／2＝檢查未過（訊息回給寫入者）
#
# 管轄（路徑相對本檔所在 repo 根；repo 由本檔位置推導，不讀環境變數）：
#   tests/**/test_*.py 或 tests/registry/catalog.json ⇒ testreg.py check --paths <p>
#   pytest.ini（repo 根）                              ⇒ testreg.py check --paths pytest.ini（收集設定縮減 ⇒ 全部測試檔 V20）
#   docs/manifests/*.json                             ⇒ testreg.py check --manifest <p>
#   tests/ 下其他 .py（conftest、fixtures、helper）     ⇒ testreg.py check --helpers <p>
#   tests/registry/ 之非 .py 契約檔                     ⇒ testreg.py validate
#   其餘路徑一律放行（rc 0）。hook 內不跑 pytest、不讀 git 全史。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd -P)"
PY="${REPO_ROOT}/venv/bin/python"
[ -x "${PY}" ] || PY="$(command -v python3)"

command -v jq >/dev/null 2>&1 || { echo "testreg_write_guard: 找不到 jq ⇒ fail-closed" >&2; exit 2; }
_fp="$(jq -r '.tool_input.file_path // empty' 2>/dev/null)" || _fp=""
[ -n "${_fp}" ] || exit 0
case "${_fp}" in /*) _abs="${_fp}" ;; *) _abs="${REPO_ROOT}/${_fp}" ;; esac
_dir="$(cd "$(dirname "${_abs}")" 2>/dev/null && pwd -P)" || exit 0
_abs="${_dir}/$(basename "${_abs}")"
case "${_abs}" in "${REPO_ROOT}"/*) rel="${_abs#"${REPO_ROOT}"/}" ;; *) exit 0 ;; esac

run() {
  _out="$("${PY}" "${SCRIPT_DIR}/testreg.py" --repo "${REPO_ROOT}" "$@" 2>&1)"
  _rc=$?
  [ "${_rc}" -eq 0 ] && exit 0
  echo "[testreg_write_guard] 🔴 ${rel} 未過 TESTREG 產出端檢查（寫入當下；pre-commit 會再擋一次）：" >&2
  printf '%s\n' "${_out}" >&2
  exit 2
}

case "${rel}" in
  tests/registry/catalog.json|pytest.ini) run check --paths "${rel}" ;;
  docs/manifests/*.json) [ "$(dirname "${rel}")" = "docs/manifests" ] && run check --manifest "${rel}"; exit 0 ;;
esac
if printf '%s' "${rel}" | grep -Eq '^tests/([A-Za-z0-9_]+/)*test_[A-Za-z0-9_]+\.py$'; then
  run check --paths "${rel}"
fi
case "${rel}" in
  tests/*.py) run check --helpers "${rel}" ;;
  tests/registry/*) run validate ;;
esac
exit 0
