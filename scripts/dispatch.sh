#!/usr/bin/env bash
# dispatch.sh — 薄 wrapper：補 --task-id / --output 預設後 exec gate.sh dispatch（單一裁決者）。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
WORK_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
GATE_DIR="${GATE_DIR_OVERRIDE:-.claude/gate}"
AUDIT="${GATE_DIR}/audit.log"

_intent=""
_task_id=""
_output=""
have_task_id=0
have_output=0
args=()

while [ $# -gt 0 ]; do
  case "$1" in
    --intent)
      _intent="${2:-}"
      args+=("$1" "${2:-}")
      shift 2
      ;;
    --task-id)
      _task_id="${2:-}"
      have_task_id=1
      args+=("$1" "${2:-}")
      shift 2
      ;;
    --output)
      _output="${2:-}"
      have_output=1
      args+=("$1" "${2:-}")
      shift 2
      ;;
    *)
      args+=("$1")
      shift
      ;;
  esac
done

_slugify() {
  local raw="$1"
  local slug
  slug="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')"
  slug="${slug:0:40}"
  [ -n "$slug" ] || slug="task"
  printf '%s' "$slug"
}

_task_in_audit() {
  local tid="$1"
  [ -f "${AUDIT}" ] || return 1
  grep -q "\"event\": \"committee_dispatch\"" "${AUDIT}" 2>/dev/null || return 1
  grep -q "\"task_id\": \"${tid}\"" "${AUDIT}" 2>/dev/null
}

if [ "${have_task_id}" -eq 0 ]; then
  _task_id="$(date '+%Y%m%d')-$(_slugify "${_intent}")"
fi

if [ "${have_output}" -eq 0 ]; then
  _output="handoffs/${_task_id}-RESULT.md"
fi

# 碰撞 fail-closed：不覆寫既有 output 或已派工 task-id
if [ -f "${WORK_ROOT}/${_output}" ]; then
  echo "ERROR: output 已存在 (${_output})，請顯式給唯一 --task-id / --output" >&2
  exit 1
fi
if _task_in_audit "${_task_id}"; then
  echo "ERROR: task-id 已在 audit (${_task_id})，請顯式給唯一 --task-id" >&2
  exit 1
fi

final_args=()
if [ "${have_task_id}" -eq 0 ]; then
  final_args+=(--task-id "${_task_id}")
fi
if [ "${have_output}" -eq 0 ]; then
  final_args+=(--output "${_output}")
fi

exec bash "${SCRIPT_DIR}/gate.sh" dispatch "${args[@]}" "${final_args[@]}"
