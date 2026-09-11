#!/usr/bin/env bash
# verdictgate_baseline.sh — 全庫透明度報表（VERDICTGATE Task 2.1）。**只有 --report；不凍結、不寫檔、不作判定輸入。**
#
# 用法：bash scripts/verdictgate_baseline.sh --report
# 印：每輪各家 has_verdict|unknown|stamp|no_output；固定三行
#   unknown=<n>／live_roots_unwatched=<root,…>／legacy_open_by_root=<root:b<N>,…>
# 分類與 prev_review_resolve.sh **同一**：root/batch 由 `^(?P<root>.+?)-b(?P<batch>\d+)-`（re.I）；
#   review 判定＝brief_kind=review 或缺欄且不命中 C-4 排除 regex；輪次以同 task_prefix 之 round_open append 序編號。
# 舊產出（無 verdict 欄）一律 unknown——不推導內容（使用者 2026-08-05）；判定面由 C-4 直接讀 audit。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
AUDIT="${REPO_ROOT}/.claude/gate/audit.log"
[ -n "${GATE_DIR_OVERRIDE:-}" ] && AUDIT="${GATE_DIR_OVERRIDE}/audit.log"
if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
  [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] || { echo "ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1" >&2; exit 2; }
  AUDIT="${DEBT_AUDIT_OVERRIDE}"
fi
[ "${1:-}" = "--report" ] || { echo "用法: verdictgate_baseline.sh --report" >&2; exit 2; }
[ -f "${AUDIT}" ] || { echo "unknown=0"; echo "live_roots_unwatched="; echo "legacy_open_by_root="; exit 0; }
python3 - "${AUDIT}" <<'PY'
import json, re, sys
from collections import OrderedDict
audit = sys.argv[1]
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
def prefix_of(t): return re.sub(r"-r\d+$", "", t or "", flags=re.I)
def is_review(r):
    bk = r.get("brief_kind")
    return (bk == "review") if bk else (not EXCL.search(r.get("task_id") or ""))
rounds = OrderedDict()   # (root, batch, prefix) -> {"opens": [...], "roster": set}
for r in rows:
    if r.get("event") != "committee_round_open" or not is_review(r):
        continue
    t = r.get("task_id") or ""
    m = re.match(r"^(?P<root>.+?)-b(?P<batch>\d+)-", t, re.I)
    if not m:
        continue
    key = (m.group("root").lower(), int(m.group("batch")), prefix_of(t).lower())
    st = rounds.setdefault(key, {"opens": [], "roster": set(), "prefix": prefix_of(t)})
    st["opens"].append(r)
    st["roster"] |= set(r.get("quorum_eligible") or r.get("participants") or [])
outs_by_prefix = {}
for r in rows:
    if r.get("event") == "committee_output":
        outs_by_prefix.setdefault(prefix_of(r.get("task_id")).lower(), []).append(r)
# 「活」判準（B2 審碼 CODEX-R1-P2-03／GROK-R1-P2-01）：最新批之 review round 任一尚未 committee_debt_clear
#   亦未 debt_abandon ⇒ 該 root 仍活；全部已清／已棄 ⇒ 不列 live_roots_unwatched（仍可列 legacy_open_by_root）。
closed_rids = {r.get("round_id") for r in rows if r.get("event") in ("committee_debt_clear", "debt_abandon")}
unknown_total = 0
latest_by_root = {}
lines = []
for (root, batch, pl), st in rounds.items():
    st["live"] = any(o.get("round_id") not in closed_rids for o in st["opens"])
    outs = outs_by_prefix.get(pl, [])
    cls = {}
    for fam in sorted(st["roster"]):
        fam_outs = [o for o in outs if o.get("family") == fam or (o.get("family") in (None, "unknown") and (o.get("output_path") or "").endswith(f"-{fam}.md"))]
        if not fam_outs:
            cls[fam] = "no_output"; unknown_total += 1
        elif any(o.get("verdict") in VERDICTS for o in fam_outs):
            cls[fam] = "has_verdict"
        elif all(o.get("verdict") == "null" for o in fam_outs):
            cls[fam] = "stamp"
        else:
            cls[fam] = "unknown"; unknown_total += 1
    lines.append(f"{st['prefix']} rounds={len(st['opens'])} " + " ".join(f"{k}={v}" for k, v in cls.items()))
    if batch >= latest_by_root.get(root, (-1, None, False))[0]:
        latest_by_root[root] = (batch, cls, st["live"])
live_unwatched = sorted(r for r, (b, cls, live) in latest_by_root.items() if live and cls and all(v in ("unknown", "no_output") for v in cls.values()))
legacy_open = sorted(f"{r}:b{b}" for r, (b, cls, live) in latest_by_root.items() if cls and any(v in ("unknown", "no_output") for v in cls.values()))
for l in lines:
    print(l)
print(f"unknown={unknown_total}")
print("live_roots_unwatched=" + ",".join(live_unwatched))
print("legacy_open_by_root=" + ",".join(legacy_open))
PY
