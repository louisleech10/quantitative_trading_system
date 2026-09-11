#!/usr/bin/env bash
# prev_review_resolve.sh — 「前一批 review」之**唯一**解析 helper（VERDICTGATE Task 2.2；SPEC v7 U1／V2）。
#
# 用法：bash scripts/prev_review_resolve.sh <root> <N>
#   stdout＝命中之 round 的 task_id 去掉輪次尾碼 `-r<M>`（大小寫保留，例 `20260911-SPLITUNIFY-B1-REVIEW`、
#   `P16-B5-TASK31-REV`——即與該輪 committee_output.task_id 可對上的真前綴）；無 ⇒ 空字串。rc=0；用法錯 rc=2。
#
# 契約（封閉）：
#   候選＝audit `committee_round_open` 中 task_id **大小寫不敏感**命中 `^<root>-b<K>-`（K<N，由大到小；
#         `x` 層不命中故自然排除）；
#   review 判定＝`brief_kind=review`，或缺欄（上線前 round）且 task_id 不命中 C-4 排除 regex
#         `-(CONSULT|STAMP|CLOSURE|IMPL|RECON)(-|[0-9]*$)`（含尾碼型 `P16-B3-STAMP`）；
#   **不**讀 handoff 檔名、**不**依賴 `-review` 字面（會漏 `P16-B5-TASK31-REV` 型）。
#   gate.sh／committee_run.sh／verdictgate_check.sh 三處只呼叫本 helper，不各自實作。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUDIT="${DEBT_AUDIT_OVERRIDE:-${GATE_DIR_OVERRIDE:-${REPO_ROOT}/.claude/gate}/audit.log}"
case "${AUDIT}" in */audit.log) : ;; *) AUDIT="${AUDIT%/}/audit.log" ;; esac
if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ] && [ "${GOVERNANCE_TEST_HARNESS:-}" != "1" ]; then
  echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2; exit 2
fi
[ -n "${DEBT_AUDIT_OVERRIDE:-}" ] && AUDIT="${DEBT_AUDIT_OVERRIDE}"
root="${1:-}"; n="${2:-}"
[ -n "${root}" ] && printf '%s' "${n}" | grep -qE '^[0-9]+$' || { echo "用法: prev_review_resolve.sh <root> <N>" >&2; exit 2; }
[ -f "${AUDIT}" ] || { printf ''; exit 0; }
python3 - "${AUDIT}" "${root}" "${n}" <<'PY'
import json, re, sys
audit, root, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
EXCL = re.compile(r"-(CONSULT|STAMP|CLOSURE|IMPL|RECON)(-|[0-9]*$)", re.I)
best = {}  # K -> task_prefix（同 K 取 append 序最早者即可；prefix 相同）
for raw in open(audit, encoding="utf-8").read().splitlines():
    s = raw.strip()
    if not s.startswith("{"):
        continue
    try:
        r = json.loads(s)
    except json.JSONDecodeError:
        continue
    if r.get("event") != "committee_round_open":
        continue
    t = r.get("task_id") or ""
    m = re.match(r"^" + re.escape(root) + r"-b(\d+)-", t, re.I)
    if not m:
        continue
    k = int(m.group(1))
    if k >= n:
        continue
    bk = r.get("brief_kind")
    is_review = (bk == "review") if bk else (not EXCL.search(t))
    if not is_review:
        continue
    prefix = re.sub(r"-r\d+$", "", t, flags=re.I)
    best.setdefault(k, prefix)
print(best[max(best)] if best else "")
PY
