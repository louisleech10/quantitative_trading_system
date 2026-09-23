#!/usr/bin/env bash
# todofmt_manifest_guard.sh — 寫入 `docs/manifests/*.json` 當下即跑 todofmt 機檢（PostToolUse Edit|Write）。
#   規格：docs/TODOFMT_SPEC.md C-2「實作期補強」。依 CLAUDE.md 產出端覆蓋鐵律：manifest 之格式檢查原只在
#   派工時（gate.sh）執行，改為寫檔當下即報；派工時之檢查不變。
#
# 用法：
#   bash scripts/todofmt_manifest_guard.sh     # hook 模式（stdin＝PostToolUse payload）
#   rc 0＝非管轄之檔，或機檢通過／2＝機檢未過（訊息回給寫入者；PostToolUse 不回滾已寫入之內容）
#
# 管轄：寫入之檔之所在目錄即 repo 之 `docs/manifests`（`-ef` 比對，涵蓋大小寫與別名路徑），且副檔名為 `.json`
#   （casefold）。子目錄、其他路徑一律放行。判定只讀該檔本身，不讀 git 狀態。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

command -v jq >/dev/null 2>&1 || { echo "todofmt_manifest_guard: 找不到 jq ⇒ 無法判定（fail-closed）" >&2; exit 2; }
_payload="$(cat)"
_fp="$(printf '%s' "${_payload}" | jq -r '.tool_input.file_path // empty' 2>/dev/null)" || _fp=""
[ -n "${_fp}" ] || exit 0

_abs="${_fp}"
case "${_abs}" in /*) : ;; *) _abs="${REPO_ROOT}/${_fp}" ;; esac
case "$(printf '%s' "${_abs##*/}" | tr '[:upper:]' '[:lower:]')" in *.json) : ;; *) exit 0 ;; esac
[ -f "${_abs}" ] || exit 0
[ "$(dirname "${_abs}")" -ef "${REPO_ROOT}/docs/manifests" ] || exit 0

_out="$(bash "${SCRIPT_DIR}/todofmt_check.sh" "${_abs}" 2>&1)" && exit 0
echo "[todofmt_manifest_guard] 🔴 ${_fp} 未過 todofmt 機檢（寫入當下檢查；派工時 gate.sh 仍會再驗一次）：" >&2
printf '%s\n' "${_out}" | sed 's/^/  /' >&2
echo "  修正後重寫即會重驗。產出順序見 templates/TODO_GENERATION_PROMPT.md 階段 2（先建空殼與測試檔，再寫 manifest）。" >&2
exit 2
