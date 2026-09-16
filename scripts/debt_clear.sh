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
ZF_VERIFIED=""
ACTOR="debt_clear"

# 🔴 「預期零 findings」標籤之真偽檢查（票 B-48，2026-08-14T17:10+08:00 使用者核可）
#   病根即該票標題：宣告「預期零 findings」，該輪卻實收 5 個 findings（含 1 個 BLOCKING P0）。
#   實測全期：180 輪標此 kind，其中 **20 輪標籤不實**——那些 findings 未經處置即結案，
#   無任何紀錄可證明它們被看過。此前該標籤**純靠紀律**，零機械綁定。
#   零 findings 之 sentinel（`## <FAMILY>-R<n>-P3-00`）是合法形態，須排除；
#   初版判準未排除它，把 4 輪合法 sentinel 誤判成不實（24 → 20）。
_DC_FINDING_RE='^#{2,6}[[:space:]]+[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}'
_DC_SENTINEL_RE='P3-00$'

_dc_zero_findings_guard() {   # $1=round_id；rc=0 放行，rc=1 擋
  _dcz_rid="$1"
  [ -f "${AUDIT_LOG:-.claude/gate/audit.log}" ] || return 0
  _dcz_outs="$(LC_ALL=C grep -E '^\{' "${AUDIT_LOG:-.claude/gate/audit.log}" \
    | LC_ALL=C jq -r --arg r "${_dcz_rid}" '
        select(.round_id == $r and .event == "committee_round_open")
        | ((.expected_outputs // {}) | to_entries | map(.value) | join(","))' 2>/dev/null | head -1)"
  [ -n "${_dcz_outs}" ] || return 0        # 查不到開輪紀錄 ⇒ 不阻擋（非本閘之判定範圍）
  _dcz_hits=""
  IFS=',' read -ra _dcz_paths <<< "${_dcz_outs}"
  for _dcz_p in "${_dcz_paths[@]}"; do
    [ -f "${_dcz_p}" ] || continue
    _dcz_f="$(LC_ALL=C grep -nE "${_DC_FINDING_RE}" "${_dcz_p}" 2>/dev/null \
              | LC_ALL=C grep -vE "${_DC_SENTINEL_RE}" || true)"
    [ -n "${_dcz_f}" ] && _dcz_hits="${_dcz_hits}$(printf '%s' "${_dcz_f}" | sed "s#^#    ${_dcz_p}:#")"$'\n'
  done
  [ -n "${_dcz_hits}" ] || return 0
  {
    echo "🔴 debt_clear 拒絕：本輪標為「預期零 findings」，但產出檔內有實質 findings"
    echo ""
    printf '%s' "${_dcz_hits}"
    echo ""
    echo "「預期零 findings」的意思是委員沒有東西要報。上列 findings 若未處置即結案，"
    echo "它們不會出現在任何收斂檔，等於**憑空消失**（票 B-48 之病，全期已發生 20 次）。"
    echo ""
    echo "三條出路："
    echo "  1. findings 是真的 ⇒ 改走正常銷帳："
    echo "       bash scripts/debt_clear.sh --round-id ${_dcz_rid} --session <名> --lock <sources.lock>"
    echo "     把 findings 收進收斂檔逐條處置。這本來就是該做的事，本閘只是不讓你跳過。"
    echo "  2. findings 屬他輪引用 ⇒ 加 --zero-findings-verified \"<理由>\"（寫入 audit，可被稽核）"
    echo "  3. 本來就該用別的 kind ⇒ --kind collection-failed（不受本檢查約束）"
  } >&2
  return 1
}

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
    # 🔴 逃生口：產出檔內之 findings 屬**他輪引用**而非本輪新提時使用。
    #   沒有逃生口就是死鎖（本 epic 已撞過六次「規矩 A 要你做的事、規矩 B 不准你做」）。
    #   濫用之防護＝理由寫進 audit ⇒「用了幾次」本身可量測，
    #   逃生口若被當橡皮圖章用，那個數字會自己浮出來。
    --zero-findings-verified)
      [ $# -ge 2 ] || die "--zero-findings-verified 需要理由"
      ZF_VERIFIED="$2"
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

# ②b 群集歸戶閘（VERDICTGATE Task 4.1；SPEC C-1）：附錄每個 ID 必列於群集表＋逐字引用斷言前 20 字＋處置 token；
#    `延後→X` 之 X 須存在於同票 TODO（`docs/<EPIC>_TODO.md`，EPIC＝session 第二段大寫；缺檔則不傳 --todo ⇒ 有延後即拒）。
#    與 synth_attribution_hook.sh 同一模組（scripts/_synth_attr.py）；本處為全量模式。
_run_attribution() {
  local lock="$1" synth epic todo_arg=""
  synth="$(dirname "${lock}")/synth.md"
  [ -f "${synth}" ] || { echo "ERROR: synth.md 缺失: ${synth}" >&2; return 1; }
  epic="$(printf '%s' "${SESSION}" | awk -F- '{print toupper($2)}')"
  [ -n "${epic}" ] && [ -f "docs/${epic}_TODO.md" ] && todo_arg="docs/${epic}_TODO.md"
  if [ -n "${todo_arg}" ]; then
    bash "${SCRIPT_DIR}/reconcile_cluster_attribution_check.sh" "${synth}" --todo "${todo_arg}"
  else
    bash "${SCRIPT_DIR}/reconcile_cluster_attribution_check.sh" "${synth}"
  fi
  local rc=$?
  [ "${rc}" -eq 0 ] || { echo "ERROR: 群集歸戶閘 rc=${rc}（ID 未列／引用不逐字／無處置 token／延後目標不存在；拒銷）" >&2; return 1; }
  return 0
}

# ③b synth 處置欄概念須見於修訂標的（只對 -x-review- 層）
_run_synth_xref() {
  local lock="$1" synth target
  synth="$(dirname "${lock}")/synth.md"
  case "${SESSION}" in *-x-review-*) : ;; *) return 0 ;; esac
  [ -f "${synth}" ] || { echo "ERROR: synth.md 缺失: ${synth}" >&2; return 1; }
  target="$(grep -m1 -oE '^\*\*修訂標的\*\*：[^ ]+' "${synth}" | sed 's/^\*\*修訂標的\*\*：//')"
  if [ -z "${target}" ]; then
    echo "ERROR: ${synth} 未宣告修訂標的（在群集段加一行：**修訂標的**：docs/<X>_SPEC.md）" >&2
    return 1
  fi
  [ -f "${target}" ] || { echo "ERROR: 修訂標的不存在: ${target}" >&2; return 1; }
  bash "${SCRIPT_DIR}/spec_xref_check.sh" --synth "${synth}" "${target}"
  local rc=$?
  [ "${rc}" -eq 0 ] || { echo "ERROR: synth 處置欄概念未見於 ${target}（拒銷）" >&2; return 1; }
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
# ④前置 暫停委員之真缺席（SPLITUNIFY b9 review-r38 實戰，2026-09-14）
#   病：r38 派出時三家；grok 因帳戶餘額耗盡（402）**一個字都沒產出**（result_state=failed、
#   output_sha256 空），使用者隨即把委員暫停成兩家。此時：銷帳要求每個 participant 皆 success ⇒ 擋；
#   `--abandon --kind collection-failed` 又因「該輪已有其他家結果」被 C-9 收窄擋；grok 無額度不能重派
#   ⇒ 死結。與 r37 那次（format-failed 無出口）同型：解除阻塞的路徑本身被閘擋住
#   （docs/SCAR_LEDGER.md「銷帳路徑不得設閘」）。
#   收窄解鎖——下列條件**全部**成立才把該家視為缺席、不要求交件：
#     ① 不在 active_stampers（暫停＝使用者之名冊決定，非主委自判）
#     ② 最新 result_state == failed 且 output_sha256 為空
#     ③ 該輪**任何時點**皆無同家之 committee_output（有登記過產出者一律不得消失）
#     ④ 該輪登記之產出路徑（round_open.expected_outputs 與結果列 output_path）**實體不存在或為 0 byte**
#   另：扣掉缺席者後剩餘 participant 須 ≥2（兩家 review 下限，與 review_quorum_check 一致）。
#   🔴 review-r39 修補（codex 實跑打穿 r38 版）：
#     `CODEX-R39-P1-01`：cx_run 對 CLI 非零退出**一律**記 failed＋空 sha（`_emit_family_result`），
#       ⇒ 空 sha 不能證明沒產出——CLI 寫完 findings 後 timeout 即是此形，r38 版會把它銷掉。故加 ④，
#       且 ③ 由「failure 之後」放寬為「整輪任何時點」。路徑不合法／不可讀／無路徑可查 ⇒ 視為有產出證據。
#     `CODEX-R39-P1-02`：active_stampers 一律經共用 getter `families_active_stampers`（三態 rc），
#       不得自讀 JSON——自讀版不驗重複與 ⊆ review_families，打錯字之名冊會把真家族判成「暫停」而放行。
#       rc=3（缺 key）⇒ 無暫停者；rc=1 ⇒ fail-closed。getter 檔缺席 ⇒ 不給任何豁免（只會更嚴）。
#   stdout：逗號分隔之缺席家族（可為空）。
_paused_absent_families() {
  local rid="$1"
  [ -f "${SCRIPT_DIR}/governance_families.sh" ] || return 0
  # shellcheck source=governance_families.sh
  . "${SCRIPT_DIR}/governance_families.sh"
  local active _as_rc
  active="$(families_active_stampers ',')"
  _as_rc=$?
  case "${_as_rc}" in
    0) : ;;
    3) return 0 ;;
    *)
      echo "ERROR: active_stampers 不合法（暫停缺席判定 fail-closed；原因見上方 stderr）" >&2
      return 1
      ;;
  esac
  local dump
  dump="$(_ledger_core dump_json)" || {
    echo "ERROR: 讀帳本失敗（暫停缺席判定）" >&2
    return 1
  }
  local _ap6
  _ap6="$(_resolve_audit_path 2>/dev/null || true)"
  DEBT_CLEAR_DUMP="${dump}" DEBT_CLEAR_RID="${rid}" DEBT_CLEAR_AUDIT="${_ap6}" \
    DEBT_CLEAR_ACTIVE="${active}" REPO_ROOT="${REPO}" python3 <<'PY'
import json, os, sys
from pathlib import Path

dump = json.loads(os.environ["DEBT_CLEAR_DUMP"])
rid = os.environ["DEBT_CLEAR_RID"]
info = (dump.get("rounds") or {}).get(rid) or {}
participants = info.get("participants") or []
latest = info.get("latest_results") or {}
active = {x for x in os.environ["DEBT_CLEAR_ACTIVE"].split(",") if x}
repo = Path(os.environ["REPO_ROOT"]).resolve()

audit_path = os.environ.get("DEBT_CLEAR_AUDIT") or ""
outputs = []
expected = {}
if audit_path and Path(audit_path).is_file():
    for raw in Path(audit_path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s.startswith("{"):
            continue
        try:
            r = json.loads(s)
        except json.JSONDecodeError:
            continue
        if r.get("round_id") != rid:
            continue
        if r.get("event") == "committee_output":
            outputs.append(r)
        elif r.get("event") == "committee_round_open" and isinstance(r.get("expected_outputs"), dict):
            expected = r["expected_outputs"]


def has_output_evidence(fam, rec):
    cands = [p for p in (expected.get(fam), rec.get("output_path")) if p]
    if not cands:
        return True
    for p in cands:
        q = Path(p)
        q = q if q.is_absolute() else repo / q
        try:
            q = q.resolve()
            q.relative_to(repo)
            if q.exists() and q.stat().st_size > 0:
                return True
        except (ValueError, OSError):
            return True
    return False


absent = []
for fam in participants:
    if fam in active:
        continue
    rec = latest.get(fam) or {}
    if rec.get("result_state") != "failed" or (rec.get("output_sha256") or "") != "":
        continue
    if any(o.get("family") == fam for o in outputs):
        continue
    if has_output_evidence(fam, rec):
        continue
    absent.append(fam)

remaining = [f for f in participants if f not in absent]
if absent and len(remaining) < 2:
    print(
        f"ERROR: 暫停缺席 {absent} 扣除後剩餘 participant 僅 {remaining}（<2）⇒ 不足兩家 review，拒銷",
        file=sys.stderr,
    )
    sys.exit(1)
print(",".join(absent))
PY
}

_assert_roster_equals() {
  local lock="$1"
  local rid="$2"
  local dump
  dump="$(_ledger_core dump_json)" || {
    echo "ERROR: 讀帳本失敗（roster 檢查）" >&2
    return 1
  }
  DEBT_CLEAR_DUMP="${dump}" DEBT_CLEAR_RID="${rid}" DEBT_CLEAR_LOCK="${lock}" \
    DEBT_CLEAR_PAUSED_ABSENT="${PAUSED_ABSENT:-}" python3 <<'PY'
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

paused = {x for x in os.environ.get("DEBT_CLEAR_PAUSED_ABSENT", "").split(",") if x}
if paused and lock_set == open_set - paused:
    print(f"[debt_clear] roster：lock 不含暫停缺席 {sorted(paused)}（見 _paused_absent_families）⇒ 視為相等")
elif open_set != lock_set:
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
  local _ap5
  _ap5="$(_resolve_audit_path 2>/dev/null || true)"
  DEBT_CLEAR_DUMP="${dump}" DEBT_CLEAR_RID="${rid}" DEBT_CLEAR_AUDIT="${_ap5}" REPO_ROOT="${REPO}" \
    DEBT_CLEAR_PAUSED_ABSENT="${PAUSED_ABSENT:-}" python3 <<'PY'
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

dump = json.loads(os.environ["DEBT_CLEAR_DUMP"])
rid = os.environ["DEBT_CLEAR_RID"]
audit_path = os.environ.get("DEBT_CLEAR_AUDIT") or ""


def reregistered_output(fam, after_seq):
    """VERDICTGATE B3 審碼 R1 實戰：cx_run 拒收裁決塊 ⇒ family_result=verdict_rejected；主委修檔後
    `gate.sh register-output` 只寫 committee_output（registry 綁 family_result 單一 origin=cx_run.sh，
    gate 不得補寫）。與 verdictgate_check 同語意：拒收後**其後**同 round 同家之 committee_output 即視為已交件；
    其 output_path／output_sha256 取代拒收列做 sha 對證。"""
    if not audit_path or not Path(audit_path).is_file():
        return None
    best = None
    for raw in Path(audit_path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s.startswith("{"):
            continue
        try:
            r = json.loads(s)
        except json.JSONDecodeError:
            continue
        if r.get("event") != "committee_output" or r.get("round_id") != rid or r.get("family") != fam:
            continue
        seq = r.get("sequence")
        if after_seq is not None and (seq is None or seq <= after_seq):
            continue
        best = r
    return best
def round_brief_kind(rid_):
    """該 round 之 committee_round_open.brief_kind；讀不到 ⇒ 空字串（fail-closed：不走 stamp 解鎖）。"""
    if not audit_path or not Path(audit_path).is_file():
        return ""
    for raw in Path(audit_path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s.startswith("{"):
            continue
        try:
            r = json.loads(s)
        except json.JSONDecodeError:
            continue
        if r.get("event") == "committee_round_open" and r.get("round_id") == rid_:
            return str(r.get("brief_kind") or "")
    return ""
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

paused = {x for x in os.environ.get("DEBT_CLEAR_PAUSED_ABSENT", "").split(",") if x}
for fam in participants:
    if fam in paused:
        print(f"[debt_clear] 家族 {fam}：暫停中且該輪未產出（failed、output_sha256 空）⇒ 不要求交件")
        continue
    rec = latest.get(fam)
    if not rec:
        print(f"ERROR: 家族 {fam} 無 committee_family_result", file=sys.stderr)
        sys.exit(1)
    if rec.get("result_state") in ("verdict_rejected", "format-failed", "failed"):
        # 🔴 SPLITUNIFY b9 r37 實戰（2026-09-14）：B3 當初只補了 `verdict_rejected` 這一支，
        #   `format-failed` 這條**同型**路徑仍被一律擋下 ⇒ 銷帳被鎖、同輪重派又被
        #   「有 OPEN 債即拒發 token」擋住，形成死結，只能請使用者在自己 terminal 跑 cx_run。
        #   那違反本機制的原始設計原則「清帳不被擋，故非死鎖」（2026-07-25 使用者二次拍板）。
        #   ⇒ 兩支統一走同一條出口。
        # 🔴 但 `format-failed` 之出口**比 `verdict_rejected` 更嚴**：後者只要求「其後有同 round
        #   之 committee_output」；前者是**格式**不合規，光重新 register 不代表格式已修好 ⇒
        #   另要求該產出檔實跑 `completeness_check --single` 通過。不是放寬，是補上缺的那半。
        state = rec.get("result_state")
        rr = reregistered_output(fam, rec.get("sequence"))
        if not rr:
            print(
                f"ERROR: 家族 {fam} 最新 result_state={state!r} 且其後無同 round 之 committee_output"
                f"（主委須修檔後 bash scripts/gate.sh register-output <task> <檔> 解鎖）",
                file=sys.stderr,
            )
            sys.exit(1)
        if state in ("format-failed", "failed"):
            out_rel = rr.get("output_path") or ""
            out_abs = out_rel if os.path.isabs(out_rel) else str(repo / out_rel)
            chk = subprocess.run(
                ["bash", str(repo / "scripts" / "completeness_check.sh"),
                 "--single", out_abs, "--family", fam, "--round-id", rid],
                capture_output=True, text=True,
            )
            if chk.returncode != 0:
                print(
                    f"ERROR: 家族 {fam} 為 {state}，其後雖已重新 register-output，"
                    f"但該檔 completeness_check --single 仍 rc={chk.returncode}（須 0）\n"
                    f"{(chk.stdout or '')[-800:]}{(chk.stderr or '')[-800:]}",
                    file=sys.stderr,
                )
                sys.exit(1)
            if state == "failed":
                # 🔴 `failed` ＝ CLI 自身非零退出 ⇒ **無法從 rc 得知該家是否真的跑完**
                #   （`format-failed` 至少 rc=0、只是格式不合）。故本支**再加一道**：
                #   產出檔須帶終結標記 `VERDICT:` 與 `STATUS: DONE`，證明不是中途被截斷。
                #   🔴 這是主委自訂之附加條件（委員未給），具名交下一輪覆核。
                try:
                    body = Path(out_abs).read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    print(f"ERROR: 家族 {fam} 產出檔讀不進來：{exc}", file=sys.stderr)
                    sys.exit(1)
                missing = [tk for tk in ("VERDICT:", "STATUS: DONE")
                           if not any(ln.startswith(tk) for ln in body.splitlines())]
                if missing:
                    print(
                        f"ERROR: 家族 {fam} 為 failed（CLI 非零退出），產出檔缺終結標記 {missing}"
                        f"——無法證明該家跑完，拒絕視為已交件",
                        file=sys.stderr,
                    )
                    sys.exit(1)
            print(f"[debt_clear] 家族 {fam} {state} 之後已重新 register-output 且單檔格式檢查 rc=0 ⇒ 視為已交件")
        else:
            print(f"[debt_clear] 家族 {fam} verdict_rejected 之後已重新 register-output（seq {rr.get('sequence')}）⇒ 視為已交件")
        rec = {"output_path": rr.get("output_path"), "output_sha256": rr.get("output_sha256")}
    elif rec.get("result_state") != "success":
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
        # 2026-09-13 DOCROT stamp-r3 死鎖（使用者裁定「修根因」）：cx_run 對 stamp 輪**從未跑**
        #   completeness --single 即記 success（見 cx_run _run_format_check_if_needed 之 kind 限定），
        #   而本檢查要求 success 檔不得改、C-9 不得 abandon、cx_run 拒重派 ⇒ 空殼交件無任何出路。
        #   收窄解鎖：**只限 stamp 輪**，且其後同 round 同家有主委顯式 register-output（committee_output，
        #   本身經 verdict 解析＋family 綁定）且該登記 sha == 檔案當前 sha ⇒ 視為已交件（留審計）。
        #   非 stamp 輪維持原判（success 檔不得改）。cx_run 已同步改為 stamp 輪也跑 --single，
        #   故此路徑對**新** stamp 輪只在「主委顯式重登」時才走得到。
        if round_brief_kind(rid) == "stamp":
            rr = reregistered_output(fam, rec.get("sequence"))
            # 〔CODEX-R1-P1-01／GROK-R1-P1-01，CXSTAMP review-r1〕path 綁定：重登之 committee_output
            #   必須是**同一份交件檔**（正規化路徑相等）。否則 cx_run 對 stamp-target 之自動登記、
            #   或任意異路徑之登記，都能讓被竄改的交件銷帳（兩家實跑 rc=0 反例）。
            def _norm(p):
                q = Path(p)
                return str((q if q.is_absolute() else repo / q).resolve())
            if rr and rr.get("output_path") and rr.get("output_sha256") and _norm(rr["output_path"]) == _norm(op):
                try:
                    rr_actual = file_sha(rr["output_path"])
                except Exception:
                    rr_actual = ""
                if rr_actual == rr["output_sha256"]:
                    print(
                        f"[debt_clear] 家族 {fam}：stamp 輪 success 檔 sha 不符，但其後已顯式 register-output"
                        f"（seq {rr.get('sequence')}，sha 相符）⇒ 視為已交件（cx_run 舊版對 stamp 輪未跑格式檢查之解鎖路徑）"
                    )
                    continue
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
  # B-64 Task 1.3：第 5 參數非空 ⇒ 以「該輪自查核快照後未變動」為鎖內寫入條件（遲到結果／重複棄置皆被拒）。
  local snapshot="${5:-}"
  # B-64 b1 review-r2（CODEX-R2-P1-01）：第 6 參數＝<產出路徑>@<sha256|none>，鎖內一併重驗
  local snapshot_out="${6:-}"
  local snapshot_sha="${7:-}"
  # B-64 b1 review-r5（CODEX-R5-P1-02）：第 8 參數＝查核當下之 <dev>:<ino>|none（物件身分綁定）
  local snapshot_devino="${8:-}"
  local _rd_guard=()
  [ -n "${snapshot}" ] && _rd_guard=(--require-round-unchanged "${rid}@${snapshot}")
  if [ -n "${snapshot_out}" ] && [ -n "${snapshot_sha}" ]; then
    # 🔴 fail-closed：helper 未給物件身分時不得只綁雜湊（同 bytes 換物件即可繞過）
    if [ -z "${snapshot_devino}" ]; then
      echo "ERROR: 快照缺 snapshot_output_dev_ino，拒絕只以雜湊綁定產出檔" >&2
      return 1
    fi
    _rd_guard+=(--require-file-path "${snapshot_out}" --require-file-sha256 "${snapshot_sha}" \
                --require-file-dev-ino "${snapshot_devino}")
  fi
  bash "${AUDIT_APPEND}" \
    ${_rd_guard[@]+"${_rd_guard[@]}"} \
    --event debt_abandon \
    --field "round_id=${rid}" \
    --field "abandon_kind=${kind}" \
    --field "reason=${reason}" \
    --field "approver=${approver}" \
    --field "actor=${ACTOR}" \
    --field "zero_findings_verified=${ZF_VERIFIED}" \
    --field "origin_script=debt_clear.sh"
}
# 🔴 逃生口必須落審計：`--zero-findings-verified` 的唯一防護就是「用了幾次是可查的」。
#   不寫進 audit 的逃生口＝無聲的萬用鑰匙。初版只解析旗標未落審計，等於沒有防護。

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
_emit_round_metric() {
  local rid="$1" session="$2" lock="$3"
  if [ ! -f "${SCRIPT_DIR}/_docrot2_metrics.py" ] || [ ! -f "${SCRIPT_DIR}/_finding_category.py" ]; then
    echo "ERROR: 缺 scripts/_docrot2_metrics.py 或 scripts/_finding_category.py（收案量測事件之唯一實作）⇒ 拒銷（fail-closed）" >&2
    echo "DOCROT2_METRIC_REASON=helper-missing" >&2
    return 1
  fi
  python3 "${SCRIPT_DIR}/_docrot2_metrics.py" emit-round --round-id "${rid}" --session "${session}" --lock "${lock}"
  local rc=$?
  [ "${rc}" -eq 0 ] || { echo "ERROR: docrot2_round_metric 未寫入 rc=${rc}（拒銷）" >&2; return 1; }
  return 0
}

_assert_redispatch_archives_dispositioned() {
  # B-64 Task 1.7：帶保存檔之輪，銷帳須證明保存檔未被改動、收斂檔引用其路徑且其 finding 逐條有處置列。
  #   helper 缺失而該輪有帶保存檔之發放事件 ⇒ fail-closed（不得靜默放行）。
  local rid="$1" lock="$2" synth
  synth="$(dirname "${lock}")/synth.md"
  [ -f "${synth}" ] || { echo "ERROR: synth.md 缺失: ${synth}" >&2; return 1; }
  if [ -f "${SCRIPT_DIR}/_redispatch_check.py" ]; then
    python3 "${SCRIPT_DIR}/_redispatch_check.py" archive-check --round-id "${rid}" --synth "${synth}" || return 1
    return 0
  fi
  local _ap7
  _ap7="$(_resolve_audit_path)" || return 1
  [ -f "${_ap7}" ] || return 0
  DEBT_CLEAR_AUDIT="${_ap7}" DEBT_CLEAR_RID="${rid}" python3 <<'PY' || return 1
import json, os, sys
rid = os.environ["DEBT_CLEAR_RID"]
for raw in open(os.environ["DEBT_CLEAR_AUDIT"], encoding="utf-8").read().splitlines():
    s = raw.strip()
    if not s.startswith("{"):
        continue
    try:
        r = json.loads(s)
    except json.JSONDecodeError:
        continue
    if (r.get("event") == "redispatch_token_issued" and r.get("round_id") == rid
            and (r.get("prev_output_archive") or "none") not in ("", "none")):
        print("ERROR: _redispatch_check.py 缺失而本輪有保存檔，不得銷帳（fail-closed）", file=sys.stderr)
        sys.exit(1)
sys.exit(0)
PY
  return 0
}

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

  # ②b 群集歸戶閘（Task 4.1：completeness 之後、synth_xref 之前）
  _run_attribution "${lock}" || return 1

  # ③ mode=review
  _assert_lock_mode_is_review "${lock}" || return 1

  # ③b synth 處置欄 vs 修訂標的（spec_xref_check --synth；使用者 2026-09-11：
  #    「每個要整理委員產出時候都會要用到」）。只對 SPEC/TODO 審查層（session 含 -x-review-）
  #    fail-closed：synth 須宣告 `**修訂標的**：<docs/...md>`，且處置欄概念皆見於該檔。
  #    程式碼審查層（-b<N>-review-）修的是碼不是文件，不套。
  _run_synth_xref "${lock}" || return 1

  # ④ identity binding
  _assert_identity_binding "${lock}" "${rid}" || return 1

  # ④前置 暫停委員之真缺席（見 _paused_absent_families）
  PAUSED_ABSENT="$(_paused_absent_families "${rid}")" || return 1

  # ④附加 roster 集合相等
  _assert_roster_equals "${lock}" "${rid}" || return 1

  # ⑤前置 B-64 Task 1.7：保存檔未被改動、收斂檔引用其路徑且其 finding 逐條有處置列
  _assert_redispatch_archives_dispositioned "${rid}" "${lock}" || return 1

  # ⑤ 每家 success + sha 相符
  _assert_all_families_success_and_sha_match "${rid}" || return 1

  # ⑤b DOCROT2 Task 3.2：收案前寫 docrot2_round_metric（僅門檻後之輪；同輪已有即不再寫）。
  #   計算與寫入唯一實作＝scripts/_docrot2_metrics.py emit-round；helper 缺失、缺欄或寫入失敗 ⇒ 拒銷（fail-closed）。
  _emit_round_metric "${rid}" "${session}" "${lock}" || return 1

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

  # 🔴 票 B-48：僅 no-findings-expected 受此約束；其餘 kind 之事實查核條件不同（另議）
  if [ "${kind}" = "no-findings-expected" ] && [ -z "${ZF_VERIFIED}" ]; then
    _dc_zero_findings_guard "${rid}" || return 1
  fi

  local min_chars
  min_chars="$(_registry_get constants.reason_min_chars)" || return 1
  if [ "${#reason}" -lt "${min_chars}" ]; then
    echo "ERROR: --reason 長度 < constants.reason_min_chars (${min_chars})" >&2
    return 1
  fi

  _assert_kind_in_enum "${kind}" || return 1

  # VERDICTGATE Task 2.2（SPEC C-9 解鎖②收窄，CODEX-R3-P1-03）：collection-failed **只准**用於該輪
  #   無任何 committee_family_result（真缺席）；有結果卻 abandon ⇒ 拒（有結果者走修檔再 register-output 解鎖）。
  # B-64 Task 1.3：重派達上限、皆已結束且最新結果仍非 success ⇒ 略過 C-9 之「已有結果即拒」，
  #   改以「該輪自查核快照後未變動」為鎖內寫入條件（遲到結果與重複棄置皆使寫入被拒）。
  _RD_SNAPSHOT=""
  if [ "${kind}" = "collection-failed" ] && [ -f "${SCRIPT_DIR}/_redispatch_check.py" ]; then
    _RD_SNAPSHOT_OUT=""
    _RD_SNAPSHOT_SHA=""
    _RD_SNAPSHOT_DEVINO=""
    _rd_out="$(python3 "${SCRIPT_DIR}/_redispatch_check.py" exhausted-check --round-id "${rid}" 2>/dev/null)" \
      && _RD_SNAPSHOT="$(printf '%s\n' "${_rd_out}" | sed -n 's/^snapshot_sequence=\([0-9][0-9]*\)$/\1/p')" \
      && _RD_SNAPSHOT_OUT="$(printf '%s\n' "${_rd_out}" | sed -n 's/^snapshot_output_path=\(.*\)$/\1/p')" \
      && _RD_SNAPSHOT_SHA="$(printf '%s\n' "${_rd_out}" | sed -n 's/^snapshot_output_sha=\(.*\)$/\1/p')" \
      && _RD_SNAPSHOT_DEVINO="$(printf '%s\n' "${_rd_out}" | sed -n 's/^snapshot_output_dev_ino=\(.*\)$/\1/p')"
    if [ -n "${REDISPATCH_TEST_AFTER_EXHAUSTED_CHECK_CMD:-}" ]; then
      if [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ]; then
        bash -c "${REDISPATCH_TEST_AFTER_EXHAUSTED_CHECK_CMD}" || true
      else
        echo "ERROR: REDISPATCH_TEST_AFTER_EXHAUSTED_CHECK_CMD 僅允許 GOVERNANCE_TEST_HARNESS=1" >&2
        return 2
      fi
    fi
  fi
  if [ "${kind}" = "collection-failed" ] && [ -z "${_RD_SNAPSHOT}" ]; then
    local _ap
    _ap="$(_resolve_audit_path)" || return 1
    if [ -f "${_ap}" ] && DEBT_CLEAR_AUDIT="${_ap}" DEBT_CLEAR_RID="${rid}" python3 - <<'PY'
import json, os, sys
rid = os.environ["DEBT_CLEAR_RID"]
for raw in open(os.environ["DEBT_CLEAR_AUDIT"], encoding="utf-8").read().splitlines():
    s = raw.strip()
    if not s.startswith("{"):
        continue
    try:
        r = json.loads(s)
    except json.JSONDecodeError:
        continue
    if r.get("event") == "committee_family_result" and r.get("round_id") == rid:
        print(f"ERROR: --abandon --kind collection-failed 拒：round {rid} 已有 committee_family_result（family={r.get('family')} state={r.get('result_state')}）——有結果者須修檔後 register-output 解鎖，不得 abandon（C-9）", file=sys.stderr)
        sys.exit(0)
sys.exit(1)
PY
    then
      return 1
    fi
  fi

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

  # B-64 Task 1.3 要點 4：耗盡例外之寫入須帶「該輪自查核快照後未變動」條件（第 5 參數）
  _emit_abandon "${rid}" "${kind}" "${reason}" "${approver}" "${_RD_SNAPSHOT:-}" "${_RD_SNAPSHOT_OUT:-}" "${_RD_SNAPSHOT_SHA:-}" "${_RD_SNAPSHOT_DEVINO:-}" || return 1
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
