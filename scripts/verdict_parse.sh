#!/usr/bin/env bash
# verdict_parse.sh — 委員產出末段機械裁決塊之**唯一**解析實作（VERDICTGATE Task 1.2）。
#
# 用法：bash scripts/verdict_parse.sh <output.md> <family> [--closed-corpus <file>]
#   <family>          小寫家族名（codex|composer|grok|claude|agy）；ID 前綴須＝其大寫。
#   --closed-corpus   一行一個「同 root 同家歷史產出檔路徑」；CLOSED 之 ID 須在其中某檔之 `## <ID>` 集合
#                     （SPEC Task 1.2 邊界②：只查同 root，跨票同 ID 不算）。缺此旗標 ⇒ 不驗 CLOSED 存在性。
# stdout：JSON {"verdict": "...", "blocked_by": [...], "closed": [...]}；rc=0。
# rc=1：拒收（stderr 逐條指名）；rc=2：用法錯／檔不存在／值集 JSON 壞。
#
# 拒收條件（SPEC Task 1.2，逐字）：無 `VERDICT:` 行／≥2 行（歧義）／值不在 verdict_values／
#   blocked 卻無 BLOCKED-BY 或為空／BLOCKED-BY 或 CLOSED 之 ID 前綴家族 ≠ 本產出家族／
#   BLOCKED-BY 之 ID 不在本檔 `## <ID>` 集合／CLOSED 之 ID 不在同 root 同家歷史產出／
#   全形冒號 `VERDICT：`（不做寬容轉換，指名）。
# 值集唯一真相源：scripts/governance_verdicts.json（缺 verdict_values 鍵 ⇒ import 期 raise，不 fallback）。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
py="${SCRIPT_DIR}/../venv/bin/python"; [ -x "$py" ] || py="$(command -v python3)"
[ -n "$py" ] || { echo "verdict_parse: 無 python3" >&2; exit 2; }

file="${1:-}"; family="${2:-}"; shift 2 2>/dev/null || true
corpus=""
while [ $# -gt 0 ]; do
  case "$1" in
    --closed-corpus) corpus="${2:-}"; shift 2 ;;
    *) echo "verdict_parse: 未知參數 $1" >&2; exit 2 ;;
  esac
done
[ -n "$file" ] && [ -n "$family" ] || { echo "用法: verdict_parse.sh <output.md> <family> [--closed-corpus <file>]" >&2; exit 2; }
[ -f "$file" ] || { echo "verdict_parse: 檔不存在: $file" >&2; exit 2; }

"$py" - "$file" "$family" "$corpus" "${SCRIPT_DIR}/governance_verdicts.json" <<'PY'
import json, re, sys
path, family, corpus_path, values_path = sys.argv[1:5]
values = json.load(open(values_path, encoding="utf-8"))
VERDICTS = values["verdict_values"]                      # 缺鍵 ⇒ KeyError（刻意不 fallback）
ID_RE = re.compile(values["finding_id_regex"])
text = open(path, encoding="utf-8").read()
lines = text.splitlines()
errs: list[str] = []

fullwidth = [i + 1 for i, l in enumerate(lines) if l.startswith("VERDICT：")]
if fullwidth:
    errs.append(f"VERDICT 行使用全形冒號（L{fullwidth[0]}）；須半形 `VERDICT: `")
vlines = [(i + 1, l) for i, l in enumerate(lines) if l.startswith("VERDICT:")]
if not vlines:
    errs.append("無 `VERDICT:` 行")
elif len(vlines) >= 2:
    errs.append("同檔 ≥2 個 `VERDICT:` 行（歧義）：L" + ",L".join(str(n) for n, _ in vlines))
verdict = None
if len(vlines) == 1:
    v = vlines[0][1][len("VERDICT:"):].strip()
    if v not in VERDICTS:
        errs.append(f"VERDICT 值 {v!r} 不在 verdict_values {VERDICTS}")
    else:
        verdict = v

def _ids(prefix: str) -> list[str]:
    for l in lines:
        if l.startswith(prefix):
            raw = l[len(prefix):].strip()
            return [x.strip() for x in raw.split(",") if x.strip()] if raw else []
    return []

has_blocked_line = any(l.startswith("BLOCKED-BY:") for l in lines)
blocked_by = _ids("BLOCKED-BY:")
closed = _ids("CLOSED:")
fam_up = family.upper()
own_ids = set(re.findall(r"^## ([A-Z]+-R\d+-P[0-3]-\d{2,})\s*$", text, re.M))

if verdict == "blocked" and (not has_blocked_line or not blocked_by):
    errs.append("VERDICT: blocked 但無 `BLOCKED-BY:` 或其為空")
for tag, ids in (("BLOCKED-BY", blocked_by), ("CLOSED", closed)):
    for i in ids:
        if not ID_RE.match(i):
            errs.append(f"{tag} ID 格式不合: {i!r}")
            continue
        if i.split("-", 1)[0] != fam_up:
            errs.append(f"{tag} ID {i} 前綴家族 ≠ 本產出家族 {fam_up}")
for i in blocked_by:
    if ID_RE.match(i) and i.split("-", 1)[0] == fam_up and i not in own_ids:
        errs.append(f"BLOCKED-BY ID {i} 不在本檔 `## <ID>` 集合")
if corpus_path:
    corpus_ids: set[str] = set()
    for p in open(corpus_path, encoding="utf-8").read().splitlines():
        p = p.strip()
        if not p:
            continue
        try:
            corpus_ids |= set(re.findall(r"^## ([A-Z]+-R\d+-P[0-3]-\d{2,})\s*$",
                                         open(p, encoding="utf-8").read(), re.M))
        except OSError:
            continue
    for i in closed:
        if ID_RE.match(i) and i.split("-", 1)[0] == fam_up and i not in corpus_ids:
            errs.append(f"CLOSED ID {i} 不在同 root 同家任何歷史產出之 `## <ID>` 集合")

if errs:
    print("verdict_parse: 拒收 " + path, file=sys.stderr)
    for e in errs:
        print("  · " + e, file=sys.stderr)
    sys.exit(1)
print(json.dumps({"verdict": verdict, "blocked_by": blocked_by, "closed": closed}, ensure_ascii=False))
PY
