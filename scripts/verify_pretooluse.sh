#!/usr/bin/env bash
# verify_pretooluse.sh — PreToolUse coarse-guard for HANDOFF/handoffs operational claims.
#
# 誠實邊界：careless-proof + tamper-evident，非防惡意偽造；只掃本次 Edit/Write 新增文字。
# 退出碼：0=放行；2=擋下（fail-closed）；工具缺失=2。
set -u

INPUT="$(cat)"
command -v jq >/dev/null 2>&1 || {
  echo "[VERIFY-PRETOOLUSE] jq 缺失，fail-closed" >&2
  exit 2
}

tool_name="$(jq -r '.tool_name // empty' <<<"$INPUT" 2>/dev/null)" || exit 2
[ -z "$tool_name" ] && exit 0

case "$tool_name" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

file_path="$(jq -r '.tool_input.file_path // empty' <<<"$INPUT" 2>/dev/null)" || exit 2
[ -z "$file_path" ] && exit 0

ROOT_RAW="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "[VERIFY-PRETOOLUSE] 不在 git repo，fail-closed" >&2
  exit 2
}
cd "$ROOT_RAW" || exit 2

py_early="venv/bin/python"
[ -x "$py_early" ] || py_early="python3"
_realpath() {
  "$py_early" -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1" 2>/dev/null \
    || realpath "$1" 2>/dev/null \
    || readlink -f "$1" 2>/dev/null \
    || printf '%s' "$1"
}
ROOT="$(_realpath "$ROOT_RAW")"
abs_file="$(_realpath "$file_path")"

case "$abs_file" in
  "$ROOT"/*) ;;
  *)
    if printf '%s' "$file_path" | grep -Eq '(HANDOFF\.md|handoffs/|docs/)'; then
      echo "[VERIFY-PRETOOLUSE] 無法正規化 repo 內目標路徑（fail-closed）: ${file_path}" >&2
      exit 2
    fi
    exit 0
    ;;
esac

rel_path="${abs_file#"$ROOT"/}"

if ! printf '%s' "$rel_path" | grep -Eq '^(HANDOFF\.md|handoffs/.+|docs/.+)$'; then
  exit 0
fi

new_text=""
if [ "$tool_name" = "Edit" ]; then
  new_text="$(jq -r '.tool_input.new_string // empty' <<<"$INPUT" 2>/dev/null)" || exit 2
else
  content="$(jq -r '.tool_input.content // empty' <<<"$INPUT" 2>/dev/null)" || exit 2
  if [ -f "$rel_path" ]; then
    tmp_new="$(mktemp)"
    trap 'rm -f "$tmp_new"' EXIT
    printf '%s' "$content" >"$tmp_new"
    new_text="$(
      diff -u "$rel_path" "$tmp_new" 2>/dev/null \
        | grep '^+' \
        | grep -v '^+++' \
        | sed 's/^+//' \
        || true
    )"
    rm -f "$tmp_new"
    trap - EXIT
  else
    new_text="$content"
  fi
fi

[ -z "$new_text" ] && exit 0

py="venv/bin/python"
[ -x "$py" ] || py="$(command -v python3 || command -v python)"  # 無 venv(如 CI)→ 系統 python3
checker="scripts/verification_claim_check.py"
if [ -z "$py" ] || [ ! -f "$checker" ]; then
  echo "[VERIFY-PRETOOLUSE] python/checker 缺失，fail-closed" >&2
  exit 2
fi

printf '%s' "$new_text" | "$py" "$checker" --stdin-operational "$rel_path"
rc=$?
if [ "$rc" -eq 1 ]; then
  echo "[VERIFY-PRETOOLUSE] operational claim 無 backing，擋下 Edit/Write" >&2
  exit 2
fi
exit "$rc"
