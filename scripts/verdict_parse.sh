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
#   全形冒號 `VERDICT：`（不做寬容轉換，指名）；缺每輪必答五行 `業界做法:`／`自建判定:`／`測試耗時:`／`主委查證:`／
#   `量化從嚴:` 或其內容為空／佔位（2026-11-18 使用者要求；內容對應 templates/COMMITTEE_FINDING_TEMPLATE.md 三節「每輪必查」
#   與 CLAUDE.md「使用者原則通用量化主線」）。
# 值集唯一真相源：scripts/governance_verdicts.json（缺 verdict_values 鍵 ⇒ import 期 raise，不 fallback）。
set -u
SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
py="${SCRIPT_DIR}/../venv/bin/python"; [ -x "$py" ] || py="$(command -v python3)"
[ -n "$py" ] || { echo "verdict_parse: 無 python3" >&2; exit 2; }

file="${1:-}"; family="${2:-}"; shift 2 2>/dev/null || true
corpus=""; answers_only=0
while [ $# -gt 0 ]; do
  case "$1" in
    --closed-corpus) corpus="${2:-}"; shift 2 ;;
    # --answers-only：只驗每輪必答五行（consult／stamp 等不走 register-output 之交件，cx_run 格式檢查呼叫）
    --answers-only) answers_only=1; shift ;;
    *) echo "verdict_parse: 未知參數 $1" >&2; exit 2 ;;
  esac
done
[ -n "$file" ] && [ -n "$family" ] || { echo "用法: verdict_parse.sh <output.md> <family> [--closed-corpus <file>]" >&2; exit 2; }
[ -f "$file" ] || { echo "verdict_parse: 檔不存在: $file" >&2; exit 2; }

"$py" - "$file" "$family" "$corpus" "${SCRIPT_DIR}/governance_verdicts.json" "$answers_only" <<'PY'
import json, re, sys
path, family, corpus_path, values_path, answers_only = sys.argv[1:6]
values = json.load(open(values_path, encoding="utf-8"))
VERDICTS = values["verdict_values"]                      # 缺鍵 ⇒ KeyError（刻意不 fallback）
ID_RE = re.compile(values["finding_id_regex"])
text = open(path, encoding="utf-8").read()
lines = text.splitlines()
errs: list[str] = []

# 每輪必答五題（使用者 2026-11-18：「是不是又在自建、是不是業界做法 -> 每一次，每一個問委員的brief都一定要包含類似的問句
#   且一定要委員回答」）：行首半形冒號、同行非空且非佔位、不在 ``` fence 內；全形冒號或前導空白之變體指名拒收。
#   題目由 cx_run.sh 注入每份提示（同一組前綴）；內容品質（敷衍作答）由收斂時主委逐條核，機檢只擋未作答。
REQUIRED_ANSWERS = ("業界做法:", "自建判定:", "測試耗時:", "主委查證:", "量化從嚴:")
_PLACEHOLDER = re.compile(r"^(<[^>]*>|待填|（待填）|TBD|xxx|…|\.\.\.)$", re.I)


def _unfenced(ls: list[str]) -> list[str]:
    out, inside = [], False
    for l in ls:
        if l.lstrip().startswith("```"):
            inside = not inside
            continue
        if not inside:
            out.append(l)
    return out


def _answer_errors(ls: list[str]) -> list[str]:
    e: list[str] = []
    body = _unfenced(ls)
    for pre in REQUIRED_ANSWERS:
        key = pre[:-1]
        hits = [l[len(pre):].strip() for l in body if l.startswith(pre)]
        variants = [l for l in body if not l.startswith(pre) and (l.lstrip().startswith(pre) or l.lstrip().startswith(key + "："))]
        if variants:
            e.append(f"必答行 `{pre}` 須行首半形冒號（發現全形冒號或前導空白之變體：{variants[0].strip()[:40]!r}）")
        if not hits:
            e.append(f"缺必答行 `{pre} …`（行首、半形冒號、同行作答、不在 fence 內）")
        elif not any(h and not _PLACEHOLDER.match(h) for h in hits):
            e.append(f"必答行 `{pre}` 內容為空或佔位")
    return e


if answers_only == "1":
    errs = _answer_errors(lines)
    if errs:
        print("verdict_parse: 拒收（必答） " + path, file=sys.stderr)
        for x in errs:
            print("  · " + x, file=sys.stderr)
        sys.exit(1)
    print(json.dumps({"answers": "ok"}, ensure_ascii=False))
    sys.exit(0)

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

errs.extend(_answer_errors(lines))

if errs:
    print("verdict_parse: 拒收 " + path, file=sys.stderr)
    for e in errs:
        print("  · " + e, file=sys.stderr)
    sys.exit(1)
print(json.dumps({"verdict": verdict, "blocked_by": blocked_by, "closed": closed}, ensure_ascii=False))
PY
