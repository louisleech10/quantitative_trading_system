#!/usr/bin/env bash
# verdictgate_check.sh — 開下一批之輪前讀委員裁決的**唯一**判定實作（VERDICTGATE Task 2.2；SPEC C-3／C-4／C-9）。
#
# 用法：bash scripts/verdictgate_check.sh <root> <N> <prev-review-prefix>
#   第三參數**必填**（由 caller 以 scripts/prev_review_resolve.sh 算出；本 checker 不自行找字面 N-1——
#   v4 兩處寫法不一致曾讓 descoped 票越過閘）。空字串＝前批不存在 ⇒ rc=0。
# rc：0 放行；1 擋（stderr 逐條指名）；2 用法錯。
#
# 判定（只讀 audit、不讀 markdown；序＝audit append 序，不以 ts 排序）：
#   1. roster＝前批**全部** review 輪 committee_round_open.quorum_eligible 之聯集（C-9；不讀 family_result 決定 roster）。
#      前批 round 存在但任一 roster 家族無同家含 verdict∈{proceed,blocked} 之 committee_output
#      （stamp 之 verdict="null" 不算；family_result=verdict_rejected 亦屬無 output）且該 round 未 debt_abandon
#      ⇒ 擋，訊息指名家族與「派補裁決輪（brief-kind: closure）」（C-4 v4：缺機械裁決＝缺輸入，fail-closed）。
#   2. blocked_by 聯集 {(family, ID)}：取前批全部輪各家 committee_output（同 task_prefix 之 round，
#      brief_kind∈{review,closure}；上線前無 brief_kind 者依 helper 同一分類）之 blocked_by；
#      每個 (family, ID) 須在**同家**之後續（append 序在後，且該 round brief_kind∈{review,closure}；
#      stamp／consult 之 CLOSED 不解除）committee_output.closed 出現，否則擋。`proceed` 本身不解除任何 ID。
#   3. 閉合輪（brief-kind: closure）自身不受本閘擋——由 caller 依 brief 判定後跳過呼叫。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUDIT="${REPO_ROOT}/.claude/gate/audit.log"
[ -n "${GATE_DIR_OVERRIDE:-}" ] && AUDIT="${GATE_DIR_OVERRIDE}/audit.log"
if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
  [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] || { echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2; exit 2; }
  AUDIT="${DEBT_AUDIT_OVERRIDE}"
fi
[ $# -eq 3 ] || { echo "用法: verdictgate_check.sh <root> <N> <prev-review-prefix>（第三參數必填；空字串＝前批不存在）" >&2; exit 2; }
root="$1"; n="$2"; prev="$3"
printf '%s' "${n}" | grep -qE '^[0-9]+$' || { echo "用法: N 須為整數" >&2; exit 2; }
if [ -z "${prev}" ]; then
  echo "[verdictgate] ${root} b${n}：前批不存在，跳過"; exit 0
fi
[ -f "${AUDIT}" ] || { echo "[verdictgate] audit 不存在，跳過"; exit 0; }
python3 - "${AUDIT}" "${root}" "${n}" "${prev}" <<'PY'
import json, re, sys
audit, root, n, prev = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
EXCL = re.compile(r"-(CONSULT|STAMP|CLOSURE|IMPL|RECON)(-|[0-9]*$)", re.I)
VERDICTS = {"proceed", "blocked"}
rows = []
for raw in open(audit, encoding="utf-8").read().splitlines():
    s = raw.strip()
    if s.startswith("{"):
        try:
            rows.append(json.loads(s))
        except json.JSONDecodeError:
            pass
def prefix_of(t: str) -> str:
    return re.sub(r"-r\d+$", "", t or "", flags=re.I)
def kind_of(r) -> str:
    bk = r.get("brief_kind")
    if bk:
        return bk
    t = r.get("task_id") or ""
    return "other" if EXCL.search(t) else "review"
# 前批 round：同 prefix（大小寫不敏感）
rounds = [r for r in rows if r.get("event") == "committee_round_open" and prefix_of(r.get("task_id")).lower() == prev.lower()]
if not rounds:
    print(f"[verdictgate] {root} b{n}：前批 {prev} 在 audit 無 committee_round_open，跳過")
    sys.exit(0)
review_rounds = [r for r in rounds if kind_of(r) == "review"]
if not review_rounds:
    print(f"[verdictgate] {root} b{n}：前批 {prev} 只有 consult/stamp 輪，非 review，跳過")
    sys.exit(0)
round_ids = {r.get("round_id") for r in review_rounds}
abandoned = {r.get("round_id") for r in rows if r.get("event") == "debt_abandon"}
roster = set()
for r in review_rounds:
    roster |= set(r.get("quorum_eligible") or r.get("participants") or [])
# 本 root 之全部 committee_output（append 序），含 kind
open_by_rid = {r.get("round_id"): r for r in rows if r.get("event") == "committee_round_open"}
outputs = []  # (idx, family, verdict, blocked_by, closed, task_prefix, kind)
for idx, r in enumerate(rows):
    if r.get("event") != "committee_output":
        continue
    t = r.get("task_id") or ""
    if not t.lower().startswith(root.lower() + "-"):
        continue
    rid = r.get("round_id")
    kind = kind_of(open_by_rid[rid]) if rid in open_by_rid else ("other" if EXCL.search(t) else "review")
    outputs.append((idx, r.get("family"), r.get("verdict"), r.get("blocked_by") or [], r.get("closed") or [], prefix_of(t).lower(), kind))
errs = []
# 1. roster 缺機械裁決
prev_l = prev.lower()
has_v = {o[1] for o in outputs if o[5] == prev_l and o[2] in VERDICTS}
live_rids = round_ids - abandoned
if live_rids:
    for fam in sorted(roster):
        if fam not in has_v:
            errs.append(f"前批 {prev} 家族 {fam} 無機械裁決（committee_output.verdict ∈ proceed|blocked）⇒ 缺輸入；派補裁決輪（brief-kind: closure）或 debt_clear --abandon --kind collection-failed（僅真缺席）")
# 2. blocked_by 聯集 vs 同家後續 closed
pending = []  # (idx, family, id)
for o in outputs:
    if o[5] == prev_l and o[6] in ("review", "closure") and o[2] == "blocked":
        for i in o[3]:
            pending.append((o[0], o[1], i))
for idx, fam, i in pending:
    closed_later = any(o[0] > idx and o[1] == fam and o[6] in ("review", "closure") and i in o[4] for o in outputs)
    if not closed_later:
        errs.append(f"前批 {prev} 之 ({fam}, {i}) 為 blocked 且無同家後續 CLOSED（proceed 不解除）")
if errs:
    print(f"[verdictgate] 🔴 {root} b{n} 不得開輪：", file=sys.stderr)
    for e in dict.fromkeys(errs):
        print("   · " + e, file=sys.stderr)
    sys.exit(1)
print(f"[verdictgate] ✓ {root} b{n}：前批 {prev} roster={sorted(roster)} 皆有裁決、blocked 全數閉合")
PY
