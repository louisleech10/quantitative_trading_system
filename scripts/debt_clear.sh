#!/usr/bin/env bash
# debt_clear.sh — P1-6 Task 2.2：唯一銷帳路徑 + 逃生口 --abandon
#
# 銷帳:
#   bash scripts/debt_clear.sh --round-id <id> --session <name> [--lock <path>]
#
# 逃生口（不受期限限制；讀取路徑走 debt_ledger._round_exists_single）:
#   bash scripts/debt_clear.sh --abandon --round-id <id> \
#     --kind <abandon_kind> --reason <text> --approver <who>
#
# 憲法: bash 3.2；每道守衛 || return（不假設 set -e）；rc 直接取禁經 pipe；
#       sources.lock 一律只讀；完整性呼叫 completeness_check.sh 禁自寫等效。
#
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"
AUDIT_APPEND="${SCRIPT_DIR}/audit_append.sh"
COMPLETENESS="${SCRIPT_DIR}/completeness_check.sh"
DEBT_LEDGER="${SCRIPT_DIR}/debt_ledger.sh"

# source ledger helpers（_round_exists_single 等）
# 判定 sourced 僅靠 debt_ledger 內 BASH_SOURCE（禁 env marker）
# shellcheck source=debt_ledger.sh
. "${DEBT_LEDGER}"

die() {
  echo "ERROR: $*" >&2
  exit 1
}

usage() {
  cat <<'EOF'
用法:
  bash scripts/debt_clear.sh --round-id <id> --session <name> [--lock <path>]
  bash scripts/debt_clear.sh --abandon --round-id <id> \
    --kind <no-findings-expected|collection-failed> \
    --reason <text>=20字 --approver <who>
EOF
}

# ── 參數 ────────────────────────────────────────────────
ROUND_ID=""
SESSION=""
LOCK_PATH=""
DO_ABANDON=0
KIND=""
REASON=""
APPROVER=""
ACTOR="debt_clear"

while [ $# -gt 0 ]; do
  case "$1" in
    -h | --help)
      usage
      exit 0
      ;;
    --round-id)
      [ $# -ge 2 ] || die "--round-id 需要參數"
      ROUND_ID="$2"
      shift 2
      ;;
    --session)
      [ $# -ge 2 ] || die "--session 需要參數"
      SESSION="$2"
      shift 2
      ;;
    --lock)
      [ $# -ge 2 ] || die "--lock 需要參數"
      LOCK_PATH="$2"
      shift 2
      ;;
    --abandon)
      DO_ABANDON=1
      shift
      ;;
    --kind)
      [ $# -ge 2 ] || die "--kind 需要參數"
      KIND="$2"
      shift 2
      ;;
    --reason)
      [ $# -ge 2 ] || die "--reason 需要參數"
      REASON="$2"
      shift 2
      ;;
    --approver)
      [ $# -ge 2 ] || die "--approver 需要參數"
      APPROVER="$2"
      shift 2
      ;;
    --actor)
      [ $# -ge 2 ] || die "--actor 需要參數"
      ACTOR="$2"
      shift 2
      ;;
    *)
      die "未知參數: $1"
      ;;
  esac
done

[ -n "${ROUND_ID}" ] || {
  usage
  die "缺 --round-id"
}

# ── helpers ─────────────────────────────────────────────
_registry_get() {
  # $1 = dotted path under registry root (e.g. constants.reason_min_chars)
  python3 - "${REGISTRY}" "$1" <<'PY'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
path = sys.argv[2].split(".")
cur = reg
for p in path:
    if not isinstance(cur, dict) or p not in cur:
        print(f"ERROR: registry 缺 {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)
    cur = cur[p]
if isinstance(cur, (dict, list)):
    print(json.dumps(cur, ensure_ascii=False))
else:
    print(cur)
PY
}

_sha256_file() {
  local f="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$f" | awk '{print $1}'
  else
    sha256sum "$f" | awk '{print $1}'
  fi
}

_read_lock_json() {
  # stdout = lock JSON text；缺檔/壞 JSON → rc≠0
  local lock="$1"
  [ -f "${lock}" ] || {
    echo "ERROR: sources.lock 不存在: ${lock}" >&2
    return 1
  }
  python3 -c '
import json, sys
p = sys.argv[1]
try:
    with open(p, encoding="utf-8") as fh:
        d = json.load(fh)
except Exception as exc:
    print(f"ERROR: sources.lock 無法解析: {exc}", file=sys.stderr)
    sys.exit(1)
# 只讀；印 canonical
print(json.dumps(d, ensure_ascii=False, sort_keys=True))
' "${lock}"
}

# ① 該輪處於 OPEN
_assert_round_is_OPEN() {
  local rid="$1"
  local st
  st="$(_round_state "${rid}")" || {
    echo "ERROR: 無法判定 round 狀態（不存在或帳本 fail-closed）: ${rid}" >&2
    return 1
  }
  if [ "${st}" = "CLOSED" ]; then
    # 冪等 no-op 由呼叫端處理；此函式只答「是否 OPEN」
    echo "NOT_OPEN:CLOSED" >&2
    return 2
  fi
  if [ "${st}" = "ABANDONED" ]; then
    echo "ERROR: round 已 ABANDONED，不可銷帳: ${rid}" >&2
    return 1
  fi
  if [ "${st}" != "OPEN" ]; then
    echo "ERROR: round 非 OPEN: ${rid} state=${st}" >&2
    return 1
  fi
  return 0
}

# ② completeness_check.sh --lock 實跑 rc=0（rc 直接取）
_run_completeness() {
  local lock="$1"
  [ -x "${COMPLETENESS}" ] || [ -f "${COMPLETENESS}" ] || {
    echo "ERROR: completeness_check.sh 缺失: ${COMPLETENESS}" >&2
    return 1
  }
  bash "${COMPLETENESS}" --lock "${lock}"
  local rc=$?
  if [ "${rc}" -ne 0 ]; then
    echo "ERROR: completeness_check rc=${rc}（拒銷）" >&2
    return 1
  fi
  return 0
}

# ③ lock.mode 必須是 review
_assert_lock_mode_is_review() {
  local lock="$1"
  local mode
  mode="$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(d.get("mode", ""))
' "${lock}")" || return 1
  if [ "${mode}" != "review" ]; then
    echo "ERROR: sources.lock mode 必須是 review（目前: ${mode:-missing}）" >&2
    echo "  建立: bash scripts/reconcile_build.sh <session> --mode review <委員檔...>" >&2
    echo "  升級: bash scripts/reconcile_build.sh <同一 session> --mode review --rebuild" >&2
    return 1
  fi
  return 0
}

# ④ identity binding: lock.round_id == --round-id（lock 只讀）
_assert_identity_binding() {
  local lock="$1"
  local rid="$2"
  local lock_rid
  lock_rid="$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
v = d.get("round_id")
print(v if isinstance(v, str) else "")
' "${lock}")" || return 1
  if [ -z "${lock_rid}" ]; then
    echo "ERROR: sources.lock 缺 round_id（identity binding fail-closed）" >&2
    return 1
  fi
  if [ "${lock_rid}" != "${rid}" ]; then
    echo "ERROR: identity binding 失敗: lock.round_id=${lock_rid} != --round-id=${rid}" >&2
    return 1
  fi
  return 0
}

# ④附加: lock.expected_roster 集合 == open.participants 集合
_assert_roster_equals() {
  local lock="$1"
  local rid="$2"
  local dump
  dump="$(_ledger_core dump_json)" || {
    echo "ERROR: 讀帳本失敗（roster 檢查）" >&2
    return 1
  }
  DEBT_CLEAR_DUMP="${dump}" DEBT_CLEAR_RID="${rid}" DEBT_CLEAR_LOCK="${lock}" python3 <<'PY'
import json, os, sys

dump = json.loads(os.environ["DEBT_CLEAR_DUMP"])
rid = os.environ["DEBT_CLEAR_RID"]
lock = json.load(open(os.environ["DEBT_CLEAR_LOCK"], encoding="utf-8"))

info = (dump.get("rounds") or {}).get(rid)
if not info:
    print(f"ERROR: round 不在帳本: {rid}", file=sys.stderr)
    sys.exit(1)

# open 側：participants（registry 欄名）
open_set = set(info.get("participants") or [])
# lock 側：expected_roster
lock_roster = lock.get("expected_roster")
if not isinstance(lock_roster, list):
    print("ERROR: sources.lock 缺 expected_roster", file=sys.stderr)
    sys.exit(1)
lock_set = set(x for x in lock_roster if isinstance(x, str))

if open_set != lock_set:
    print(
        f"ERROR: roster 集合不相等: open.participants={sorted(open_set)} "
        f"lock.expected_roster={sorted(lock_set)}",
        file=sys.stderr,
    )
    sys.exit(1)
sys.exit(0)
PY
}

# ⑤ 每家最新 result 皆 success 且 output_sha256 == 檔案當前 sha
_assert_all_families_success_and_sha_match() {
  local rid="$1"
  local dump
  dump="$(_ledger_core dump_json)" || {
    echo "ERROR: 讀帳本失敗（family result 檢查）" >&2
    return 1
  }
  DEBT_CLEAR_DUMP="${dump}" DEBT_CLEAR_RID="${rid}" REPO_ROOT="${REPO}" python3 <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

dump = json.loads(os.environ["DEBT_CLEAR_DUMP"])
rid = os.environ["DEBT_CLEAR_RID"]
repo = Path(os.environ["REPO_ROOT"])
info = (dump.get("rounds") or {}).get(rid)
if not info:
    print(f"ERROR: round 不在帳本: {rid}", file=sys.stderr)
    sys.exit(1)

participants = info.get("participants") or []
latest = info.get("latest_results") or {}

if not participants:
    print("ERROR: open.participants 空，無法驗家族結果", file=sys.stderr)
    sys.exit(1)

def file_sha(path_str: str) -> str:
    p = Path(path_str)
    if not p.is_absolute():
        p = repo / p
    if not p.is_file():
        raise FileNotFoundError(str(p))
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

for fam in participants:
    rec = latest.get(fam)
    if not rec:
        print(f"ERROR: 家族 {fam} 無 committee_family_result", file=sys.stderr)
        sys.exit(1)
    if rec.get("result_state") != "success":
        print(
            f"ERROR: 家族 {fam} 最新 result_state={rec.get('result_state')!r}（須 success）",
            file=sys.stderr,
        )
        sys.exit(1)
    op = rec.get("output_path") or ""
    expect = rec.get("output_sha256") or ""
    if not expect:
        print(f"ERROR: 家族 {fam} output_sha256 空", file=sys.stderr)
        sys.exit(1)
    try:
        actual = file_sha(op)
    except Exception as exc:
        print(f"ERROR: 讀取產出檔失敗 ({fam}: {op}): {exc}", file=sys.stderr)
        sys.exit(1)
    if actual != expect:
        print(
            f"ERROR: 家族 {fam} 產出檔 sha 不符（交件後被改動）: "
            f"audit={expect[:12]}… file={actual[:12]}…",
            file=sys.stderr,
        )
        sys.exit(1)
sys.exit(0)
PY
}

# ⑥ 寫 committee_debt_clear（含 lock_sha256 只做記錄）
_emit_clear() {
  local rid="$1"
  local session_id="$2"
  local lock="$3"
  local lock_sha synth_sha roster_json
  lock_sha="$(_sha256_file "${lock}")" || {
    echo "ERROR: 計算 lock sha256 失敗" >&2
    return 1
  }
  # synth.md 與 lock 同 session 目錄
  local synth
  synth="$(python3 -c '
import json, sys
from pathlib import Path
lock = Path(sys.argv[1])
synth = lock.parent / "synth.md"
print(str(synth))
' "${lock}")"
  if [ ! -f "${synth}" ]; then
    echo "ERROR: synth.md 不存在: ${synth}" >&2
    return 1
  fi
  synth_sha="$(_sha256_file "${synth}")" || return 1
  roster_json="$(python3 -c '
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
print(json.dumps(d.get("expected_roster") or [], ensure_ascii=False))
' "${lock}")" || return 1

  bash "${AUDIT_APPEND}" \
    --event committee_debt_clear \
    --field "round_id=${rid}" \
    --field "session_id=${session_id}" \
    --field "lock_sha256=${lock_sha}" \
    --field "synth_sha256=${synth_sha}" \
    --field "roster=@${roster_json}" \
    --field "completeness_rc=0" \
    --field "actor=${ACTOR}" \
    --field "origin_script=debt_clear.sh"
}

_emit_abandon() {
  local rid="$1"
  local kind="$2"
  local reason="$3"
  local approver="$4"
  bash "${AUDIT_APPEND}" \
    --event debt_abandon \
    --field "round_id=${rid}" \
    --field "abandon_kind=${kind}" \
    --field "reason=${reason}" \
    --field "approver=${approver}" \
    --field "actor=${ACTOR}" \
    --field "origin_script=debt_clear.sh"
}

_assert_kind_in_enum() {
  local kind="$1"
  DEBT_CLEAR_KIND="${kind}" DEBT_CLEAR_REG="${REGISTRY}" python3 <<'PY'
import json, os, sys
reg = json.load(open(os.environ["DEBT_CLEAR_REG"], encoding="utf-8"))
allowed = (reg.get("enums") or {}).get("abandon_kind") or []
k = os.environ["DEBT_CLEAR_KIND"]
if k not in allowed:
    print(f"ERROR: --kind 不在 enums.abandon_kind: {k!r} allowed={allowed}", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
PY
}

# ── 銷帳 ────────────────────────────────────────────────
_cmd_clear() {
  local rid="$1"
  local session="$2"
  local lock="$3"

  # ① OPEN（CLOSED → 冪等 no-op）
  local st_rc=0
  _assert_round_is_OPEN "${rid}"
  st_rc=$?
  if [ "${st_rc}" -eq 2 ]; then
    # CLOSED → 冪等 no-op
    echo "OK: already CLOSED (idempotent no-op) round_id=${rid}"
    return 0
  fi
  if [ "${st_rc}" -ne 0 ]; then
    return 1
  fi

  # 只讀 lock
  _read_lock_json "${lock}" >/dev/null || return 1

  # ② completeness（rc 直接取）
  _run_completeness "${lock}" || return 1

  # ③ mode=review
  _assert_lock_mode_is_review "${lock}" || return 1

  # ④ identity binding
  _assert_identity_binding "${lock}" "${rid}" || return 1

  # ④附加 roster 集合相等
  _assert_roster_equals "${lock}" "${rid}" || return 1

  # ⑤ 每家 success + sha 相符
  _assert_all_families_success_and_sha_match "${rid}" || return 1

  # ⑥ emit（含 lock_sha256）
  _emit_clear "${rid}" "${session}" "${lock}" || return 1
  echo "OK: cleared round_id=${rid} session=${session}"
  return 0
}

# ── 逃生口 ──────────────────────────────────────────────
_cmd_abandon() {
  local rid="$1"
  local kind="$2"
  local reason="$3"
  local approver="$4"

  # 四項缺一即拒
  [ -n "${kind}" ] || {
    echo "ERROR: --abandon 缺 --kind" >&2
    return 1
  }
  [ -n "${reason}" ] || {
    echo "ERROR: --abandon 缺 --reason" >&2
    return 1
  }
  [ -n "${approver}" ] || {
    echo "ERROR: --abandon 缺 --approver" >&2
    return 1
  }

  local min_chars
  min_chars="$(_registry_get constants.reason_min_chars)" || return 1
  if [ "${#reason}" -lt "${min_chars}" ]; then
    echo "ERROR: --reason 長度 < constants.reason_min_chars (${min_chars})" >&2
    return 1
  fi

  _assert_kind_in_enum "${kind}" || return 1

  # 該輪存在：走 _round_exists_single（不跑全域序號連續性；
  # 但 duplicate-open 語意 fail-closed 仍須擋——只豁免序號連續性）
  _round_exists_single "${rid}"
  local ex_rc=$?
  if [ "${ex_rc}" -eq 2 ]; then
    echo "ERROR: 帳本 fail-closed（缺檔/壞 JSON/同一 round 非恰一筆 open）: ${rid}" >&2
    return 1
  fi
  if [ "${ex_rc}" -ne 0 ]; then
    echo "ERROR: round_id 不存在: ${rid}" >&2
    return 1
  fi

  # 非 ABANDONED：若帳本可解析（含連續性）則查 state；
  # 若連續性失敗（rc=2 from --round-state），仍允許 abandon（死鎖修法）
  local st
  st="$(_round_state "${rid}" 2>/dev/null)"
  local st_rc=$?
  if [ "${st_rc}" -eq 0 ]; then
    if [ "${st}" = "ABANDONED" ]; then
      echo "ERROR: round 已 ABANDONED（不可逆）: ${rid}" >&2
      return 1
    fi
  fi
  # st_rc=1（不在 cutoff 後 rounds）但 exists-single 已確認存在 → 仍可 abandon
  # st_rc=2 被 _round_state 的 fail-closed 吞掉（我們用 2>/dev/null）；
  # 實際上 _round_state 在 seq gap 時會 rc=2。需直接偵測：

  # 重新用 dump 路徑：若 has_open 因 seq gap 失敗，跳過 ABANDONED 檢查
  # （exists-single 已保證 open 存在；重複 abandon 由 append 後 state 推導，
  #  但第二次 abandon 需要擋。若 seq gap 無法推 state，允許寫第二筆？
  #  SPEC：不可逆。在 gap 下用單筆掃描 abandon 事件。）
  if ! _abandon_already "${rid}"; then
    :
  else
    echo "ERROR: round 已 ABANDONED（單筆掃描）: ${rid}" >&2
    return 1
  fi

  _emit_abandon "${rid}" "${kind}" "${reason}" "${approver}" || return 1
  echo "OK: abandoned round_id=${rid} kind=${kind}"
  return 0
}

_abandon_already() {
  # 單筆掃描是否已有 debt_abandon（不跑連續性）；rc 0=已 abandon，1=尚未
  local rid="$1"
  local audit_path
  audit_path="$(_resolve_audit_path)" || return 0
  [ -f "${audit_path}" ] || return 1
  DEBT_CLEAR_AUDIT="${audit_path}" DEBT_CLEAR_RID="${rid}" python3 <<'PY'
import json, os, sys
path = os.environ["DEBT_CLEAR_AUDIT"]
rid = os.environ["DEBT_CLEAR_RID"]
try:
    raw = open(path, encoding="utf-8").read()
except OSError:
    sys.exit(1)
for line in raw.splitlines():
    s = line.strip()
    if not s.startswith("{"):
        continue
    try:
        rec = json.loads(s)
    except json.JSONDecodeError:
        # 壞 JSON：交給上層 exists 路徑；此處保守視為不可判定→當未 abandon 讓 emit 走
        continue
    if rec.get("event") == "debt_abandon" and rec.get("round_id") == rid:
        sys.exit(0)
sys.exit(1)
PY
}

# ── main ────────────────────────────────────────────────
if [ "${DO_ABANDON}" = "1" ]; then
  _cmd_abandon "${ROUND_ID}" "${KIND}" "${REASON}" "${APPROVER}"
  exit $?
fi

[ -n "${SESSION}" ] || {
  usage
  die "銷帳缺 --session"
}

if [ -z "${LOCK_PATH}" ]; then
  LOCK_PATH="${REPO}/handoffs/reconcile/${SESSION}/sources.lock"
else
  # 顯式 --lock 必須與 --session 綁定一致（禁把錯 session_id 寫入 clear audit）
  lock_sid="$(python3 -c '
import json, sys
try:
    d = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception as exc:
    print(f"ERROR: sources.lock 無法解析: {exc}", file=sys.stderr)
    sys.exit(1)
v = d.get("session_id")
print(v if isinstance(v, str) else "")
' "${LOCK_PATH}")" || die "顯式 --lock 無法讀 session_id"
  if [ -z "${lock_sid}" ]; then
    die "顯式 --lock 缺 session_id（identity binding fail-closed）"
  fi
  if [ "${lock_sid}" != "${SESSION}" ]; then
    die "lock.session_id=${lock_sid} 與 --session=${SESSION} 不一致"
  fi
fi

_cmd_clear "${ROUND_ID}" "${SESSION}" "${LOCK_PATH}"
exit $?
