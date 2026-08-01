#!/usr/bin/env bash
# debt_ledger.sh — P1-6 Task 2.1：只讀 audit 推導未結案債（不另存狀態檔）
#
# 子命令:
#   --list                 列出 cutoff 後各輪狀態（含 OPEN/CLOSED/ABANDONED）
#   --has-open             rc 0=無 OPEN 債／1=有 OPEN 債／2=fail-closed
#   --abandoned-count      依 abandon_kind 分開輸出兩個數字
#   --round-exists-single <round_id>
#                          只做該 round 存在性掃描（不跑全域序號連續性）
#                          rc 0=存在／1=不存在／2=fail-closed（缺檔/壞 JSON）
#   --round-state <round_id>
#                          印 OPEN|CLOSED|ABANDONED（含序號連續性；不存在→rc=1）
#
# 環境:
#   DEBT_AUDIT_OVERRIDE    測試隔離 audit 路徑；必須 GOVERNANCE_TEST_HARNESS=1
#   DEBT_CUTOFF_OVERRIDE   覆寫 registry cutoff_ts；必須 GOVERNANCE_TEST_HARNESS=1
#
# 憲法: bash 3.2；禁 declare -A／flock；rc 直接取禁經 pipe；不另存狀態檔。
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法:
  bash scripts/debt_ledger.sh --list
  bash scripts/debt_ledger.sh --has-open
  bash scripts/debt_ledger.sh --abandoned-count
  bash scripts/debt_ledger.sh --round-exists-single <round_id>
  bash scripts/debt_ledger.sh --round-state <round_id>
EOF
}

# ── 路徑／cutoff 解析（與 audit_append 同型）────────────────
_resolve_audit_path() {
  if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_AUDIT_OVERRIDE}"
    return 0
  fi
  python3 - "${REGISTRY}" "${REPO}" <<'PY'
import json
import os
import sys

reg_path, repo = sys.argv[1], sys.argv[2]
try:
    with open(reg_path, encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
rel = reg.get("audit_log_path")
if not isinstance(rel, str) or not rel:
    print("ERROR: registry 缺 audit_log_path", file=sys.stderr)
    sys.exit(1)
print(os.path.join(repo, rel))
PY
}

_resolve_cutoff() {
  # stdout = ISO-8601 cutoff；fail → rc≠0
  if [ -n "${DEBT_CUTOFF_OVERRIDE:-}" ]; then
    if [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
      echo "ERROR: DEBT_CUTOFF_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2
      return 1
    fi
    printf '%s\n' "${DEBT_CUTOFF_OVERRIDE}"
    return 0
  fi
  python3 - "${REGISTRY}" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        reg = json.load(fh)
except Exception as exc:
    print(f"ERROR: registry 讀取失敗: {exc}", file=sys.stderr)
    sys.exit(1)
c = reg.get("cutoff_ts")
if not isinstance(c, str) or not c:
    print("ERROR: registry 缺 cutoff_ts", file=sys.stderr)
    sys.exit(1)
print(c)
PY
}

# ── Python 核心：掃描 audit ──────────────────────────────
# 模式經 argv 傳入：
#   list | has_open | abandoned_count | round_exists | round_state | dump_json
# dump_json：stdout 完整結構化結果（給 debt_clear 消費）
_ledger_core() {
  local mode="$1"
  local round_id_arg="${2:-}"
  local core_py
  # 效能：resolve+scan 合併為**單次** python；核心在 _debt_ledger_core.py
  # （舊版 3×python 啟動使 prod --has-open≈150ms，gate_check cold 超 SPEC <100ms）。
  # -S：跳過 site；.py 檔可享 bytecode 快取。_resolve_* 仍給 _iter_json_lines 用。
  core_py="${SCRIPT_DIR}/_debt_ledger_core.py"
  if [ ! -f "${core_py}" ]; then
    echo "ERROR: debt_ledger 核心缺失: ${core_py}" >&2
    return 2
  fi
  DEBT_LEDGER_MODE="${mode}" \
  DEBT_LEDGER_ROUND_ID="${round_id_arg}" \
  DEBT_LEDGER_REGISTRY="${REGISTRY}" \
  DEBT_LEDGER_REPO="${REPO}" \
  python3 -S "${core_py}"
  return $?
}

# ── 具名函式（TODO 要求；供 source 或 CLI 呼叫）──────────
_iter_json_lines() {
  # stdout: 合法 JSON 行；壞 JSON → rc=2
  local audit_path
  audit_path="$(_resolve_audit_path)" || return 2
  [ -f "${audit_path}" ] || {
    echo "ERROR: audit 檔缺失: ${audit_path}" >&2
    return 2
  }
  DEBT_LEDGER_AUDIT="${audit_path}" python3 <<'PY'
import json, os, sys
path = os.environ["DEBT_LEDGER_AUDIT"]
try:
    raw = open(path, encoding="utf-8").read()
except OSError as exc:
    print(f"ERROR: 讀 audit 失敗: {exc}", file=sys.stderr)
    sys.exit(2)
for line_no, line in enumerate(raw.splitlines(), 1):
    s = line.strip()
    if not s or not s.startswith("{"):
        continue
    try:
        json.loads(s)
    except json.JSONDecodeError as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(2)
    print(s)
PY
}

_assert_seq_continuity() {
  _ledger_core has_open >/dev/null
  local rc=$?
  # has_open 的 0/1 皆表示連續性通過；2=fail
  if [ "${rc}" -eq 2 ]; then
    return 2
  fi
  return 0
}

_round_exists_single() {
  # $1=round_id；不跑全域序號連續性
  local rid="${1:-}"
  [ -n "${rid}" ] || {
    echo "ERROR: _round_exists_single 需要 round_id" >&2
    return 2
  }
  _ledger_core round_exists "${rid}"
}

_round_state() {
  # $1=round_id；stdout=OPEN|CLOSED|ABANDONED
  local rid="${1:-}"
  [ -n "${rid}" ] || {
    echo "ERROR: _round_state 需要 round_id" >&2
    return 2
  }
  _ledger_core round_state "${rid}"
}

_latest_result_per_family() {
  # $1=round_id；stdout=JSON object family→result
  local rid="${1:-}"
  [ -n "${rid}" ] || return 2
  local dump
  dump="$(_ledger_core dump_json)" || return $?
  DEBT_LEDGER_DUMP="${dump}" DEBT_LEDGER_RID="${rid}" python3 <<'PY'
import json, os, sys
dump = json.loads(os.environ["DEBT_LEDGER_DUMP"])
rid = os.environ["DEBT_LEDGER_RID"]
info = (dump.get("rounds") or {}).get(rid)
if not info:
    print("{}", end="")
    sys.exit(0)
print(json.dumps(info.get("latest_results") or {}, ensure_ascii=False, sort_keys=True))
PY
}

_cmd_list() {
  _ledger_core list
}

_cmd_has_open() {
  # ⚠️ 不可用 pipeline 取 rc（JSON parse 失敗 rc=2 會被吞）
  _ledger_core has_open
}

_cmd_abandoned_count() {
  _ledger_core abandoned_count
}

# ── CLI 入口 ────────────────────────────────────────────
_debt_ledger_main() {
  if [ $# -lt 1 ]; then
    usage
    exit 2
  fi
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --list)
      _cmd_list
      exit $?
      ;;
    --has-open)
      _cmd_has_open
      exit $?
      ;;
    --abandoned-count)
      _cmd_abandoned_count
      exit $?
      ;;
    --round-exists-single)
      [ $# -ge 2 ] || die "--round-exists-single 需要 <round_id>"
      _round_exists_single "$2"
      exit $?
      ;;
    --round-state)
      [ $# -ge 2 ] || die "--round-state 需要 <round_id>"
      _round_state "$2"
      exit $?
      ;;
    --dump-json)
      # 內部／測試用
      _ledger_core dump_json
      exit $?
      ;;
    *)
      echo "ERROR: 未知參數: $1" >&2
      usage
      exit 2
      ;;
  esac
}

# 被 source 時不跑 CLI（debt_clear 會 source 本檔）。
# 判定 sourced **只可用 BASH_SOURCE**（bash 自身提供、呼叫端無法偽造）。
# 禁止任何外部 marker（含 DEBT_LEDGER_SOURCED）——env 當「內部呼叫」標記違反反 bypass 紅線。
if [ "${BASH_SOURCE[0]-}" = "${0}" ] || [ -z "${BASH_SOURCE[0]-}" ]; then
  _debt_ledger_main "$@"
fi
