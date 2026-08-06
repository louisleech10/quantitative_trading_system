#!/usr/bin/env bash
# reconcile_build.sh — 把委員收集節點的機械前置一次跑完（省 Claude 手工重演）。
#
# 包含 7 步裡的機械部分：①建 session ②cp 委員檔 ③寫 lock ④a 逐字組 byte-faithful synth 骨架
#   ⑤跑 completeness 驗 0 掉項。**不含判斷**：④b 群集/處置與 ⑥改 SPEC/TODO 由 Claude 手動填；
#   ⑦ template_check 是改完文件後另跑的現成腳本。
#
# 純便利加速：不改也不繞任何閘門——產出的 lock/synth/completeness 與手工版一模一樣，只是一個 call。
#
# 用法：
#   bash scripts/reconcile_build.sh <session-name> [--mode review|discovery] <委員檔1> <委員檔2> [...]
#   bash scripts/reconcile_build.sh <session-name> --mode review --rebuild
# 例：
#   bash scripts/reconcile_build.sh p0todo-closure-r4 \
#       handoffs/20260724-p0todo-closure3-codex.md \
#       handoffs/20260724-p0todo-closure3-composer.md
#
# 家族由檔名後綴推定（*-codex.md / *-composer.md / *-grok.md / *-claude.md / *-agy.md）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"
REGISTRY="${SCRIPT_DIR}/audit_events.json"

usage() {
  cat <<'EOF'
用法:
  bash scripts/reconcile_build.sh <session-name> [--mode review|discovery] <委員檔1> <委員檔2> [...]
  bash scripts/reconcile_build.sh <session-name> --mode review --rebuild

選項:
  --mode review|discovery  lock 模式（預設 discovery；旗標位置無關）
  --rebuild                同名就地由 discovery 升級至 review；需 audit OPEN 且 round_id 恰一筆
  -h, --help               顯示本說明
EOF
}

_lookup_round_id() {
  python3 - "${REGISTRY}" "${REPO}" "$1" <<'PY'
import json
import os
import sys

registry_path, repo, session_name = sys.argv[1:]
try:
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    audit_path = os.path.join(repo, registry["audit_log_path"])
    with open(audit_path, encoding="utf-8") as fh:
        lines = fh.readlines()
except Exception as exc:
    print(f"ERROR: audit 讀取失敗(fail-closed): {exc}", file=sys.stderr)
    sys.exit(1)

events = registry.get("debt_events", {})
# 嚴格布林：僅 JSON true；字串/數字/null 不算
open_events = [
    name for name, spec in events.items() if spec.get("opens_debt") is True
]
if len(open_events) != 1:
    print("ERROR: registry 的 opens_debt 事件不是恰一筆", file=sys.stderr)
    sys.exit(1)
open_event = open_events[0]
hits = []
for line_no, raw in enumerate(lines, 1):
    line = raw.strip()
    if not line or not line.startswith("{"):
        continue
    try:
        record = json.loads(line)
    except Exception as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(1)
    if record.get("event") == open_event and record.get("session_name") == session_name:
        hits.append(record)

if len(hits) != 1:
    print(f"ERROR: session_name 命中 {len(hits)} 筆(需恰 1): {session_name}", file=sys.stderr)
    sys.exit(1)
round_id = hits[0].get("round_id")
if not isinstance(round_id, str) or not round_id:
    print("ERROR: committee_round_open 缺非空 round_id", file=sys.stderr)
    sys.exit(1)
print(round_id)
PY
}

_assert_round_open() {
  python3 - "${REGISTRY}" "${REPO}" "$1" <<'PY'
import json
import os
import sys

registry_path, repo, round_id = sys.argv[1:]
try:
    with open(registry_path, encoding="utf-8") as fh:
        registry = json.load(fh)
    audit_path = os.path.join(repo, registry["audit_log_path"])
    with open(audit_path, encoding="utf-8") as fh:
        lines = fh.readlines()
except Exception as exc:
    print(f"ERROR: audit 讀取失敗(fail-closed): {exc}", file=sys.stderr)
    sys.exit(1)

events = registry.get("debt_events", {})
# 嚴格布林：僅 JSON true；字串/數字/null 不算
open_events = [
    name for name, spec in events.items() if spec.get("opens_debt") is True
]
close_events = {
    name for name, spec in events.items() if spec.get("closes_debt") is True
}
terminal_events = {
    name for name, spec in events.items() if spec.get("terminal") is True
}
if len(open_events) != 1 or len(close_events) != 1 or len(terminal_events) != 1:
    print("ERROR: registry 狀態事件契約不完整", file=sys.stderr)
    sys.exit(1)

open_count = 0
closed = False
for line_no, raw in enumerate(lines, 1):
    line = raw.strip()
    if not line or not line.startswith("{"):
        continue
    try:
        record = json.loads(line)
    except Exception as exc:
        print(f"ERROR: audit 第 {line_no} 行 JSON 無法解析(fail-closed): {exc}", file=sys.stderr)
        sys.exit(1)
    if record.get("round_id") != round_id:
        continue
    if record.get("event") == open_events[0]:
        open_count += 1
    elif record.get("event") in close_events or record.get("event") in terminal_events:
        closed = True

if open_count != 1 or closed:
    print(
        f"ERROR: round_id 非 OPEN(開債={open_count}, terminal_or_clear={str(closed).lower()})",
        file=sys.stderr,
    )
    sys.exit(1)
PY
}

_rebuild_guards() {
  local session_lock="$1"
  local session_name="$2"
  local target_mode="$3"
  [ -f "${session_lock}" ] || {
    echo "ERROR: --rebuild 需既有 sources.lock: ${session_lock}" >&2
    return 1
  }
  [ "${target_mode}" = "review" ] || {
    echo "ERROR: --rebuild 僅允許目標 mode=review" >&2
    return 1
  }
  local existing_mode
  existing_mode="$(python3 - "${session_lock}" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as fh:
        lock = json.load(fh)
except Exception:
    sys.exit(1)
print(lock.get("mode", ""))
PY
  )" || {
    echo "ERROR: 既有 sources.lock 無法解析(fail-closed)" >&2
    return 1
  }
  [ "${existing_mode}" = "discovery" ] || {
    echo "ERROR: --rebuild 只允許 discovery → review；現有 mode=${existing_mode:-missing}" >&2
    return 1
  }
  local round_id
  round_id="$(_lookup_round_id "${session_name}")" || return 1
  _assert_round_open "${round_id}" || return 1
}

mode="discovery"
rebuild=0
sess_name=""
declare -a input_files=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --mode)
      [ "$#" -ge 2 ] || { echo "ERROR: --mode 需要值 review|discovery" >&2; exit 2; }
      mode="$2"
      shift 2
      ;;
    --rebuild)
      rebuild=1
      shift
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do input_files+=("$1"); shift; done
      ;;
    *)
      if [ -z "${sess_name}" ]; then sess_name="$1"; else input_files+=("$1"); fi
      shift
      ;;
  esac
done

[ -n "${sess_name}" ] || { usage >&2; exit 2; }
case "${mode}" in
  discovery|review) ;;
  *) echo "ERROR: --mode 非法值 '${mode}'（允許: discovery|review）" >&2; exit 2 ;;
esac
if [ "${rebuild}" = "1" ]; then
  [ "${#input_files[@]}" -eq 0 ] || {
    echo "ERROR: --rebuild 不接受委員檔；既有 sources.lock 內容必須保持不變" >&2
    exit 2
  }
else
  [ "${#input_files[@]}" -ge 1 ] || {
    echo "ERROR: fresh 建立至少需要一個委員檔" >&2
    exit 2
  }
fi

SESS="${REPO}/handoffs/reconcile/${sess_name}"
if [ "${rebuild}" = "1" ]; then
  session_lock="${SESS}/sources.lock"
  _rebuild_guards "${session_lock}" "${sess_name}" "${mode}" || exit 1
  bash "${SCRIPT_DIR}/write_sources_lock.sh" \
    --session "${SESS}" --mode "${mode}" --rebuild \
    || { echo "ERROR: --rebuild lock 就地升級失敗" >&2; exit 1; }
  echo "[reconcile_build] ✅ ${sess_name} 已由 discovery 就地升級為 review"
  exit 0
fi

# --- 推家族 + 驗檔存在（先做完所有輸入檢查，不留下半套 session）---
_valid_fam="codex composer grok claude agy"
declare -a copied=()
declare -a fams=()
for f in "${input_files[@]}"; do
  [ -f "${f}" ] || { echo "ERROR: 委員檔不存在: ${f}" >&2; exit 2; }
  base="$(basename "${f}")"
  fam="$(printf '%s' "${base}" | sed -nE 's/.*-([a-z0-9]+)\.md$/\1/p')"
  case " ${_valid_fam} " in
    *" ${fam} "*) : ;;
    *) echo "ERROR: 檔名推不出合法家族(須 *-{codex|composer|grok|claude|agy}.md): ${f}" >&2; exit 2 ;;
  esac
  fams+=("${fam}")
  copied+=("${base}")
done

# 只有 review lock 才需要 provenance identity；discovery 是 bootstrap 路徑，
# 不需 round_id，也不得因尚未有 committee_round_open 而鎖死施工流程。
round_id=""
if [ "${mode}" = "review" ]; then
  round_id="$(_lookup_round_id "${sess_name}")" || exit 1
fi

# roster CSV（去重、排序）
roster="$(printf '%s\n' "${fams[@]}" | sort -u | paste -sd, -)"

[ ! -e "${SESS}" ] || {
  echo "ERROR: session 已存在，未帶 --rebuild 時拒覆寫: ${SESS}" >&2
  exit 2
}

# --- 建 session + cp ---
mkdir -p "${SESS}/sources"
for f in "${input_files[@]}"; do
  cp "${f}" "${SESS}/sources/$(basename "${f}")"
done
echo "[reconcile_build] session=${SESS}  roster=${roster}  sources=${#copied[@]} round_id=${round_id:-unbound} mode=${mode}"

# --- 寫 lock（fresh；review 的 round_id 由 writer 從 audit 反查取得）---
bash "${SCRIPT_DIR}/write_sources_lock.sh" --session "${SESS}" --roster "${roster}" \
  --mode "${mode}" \
  || { echo "ERROR: write_sources_lock 失敗" >&2; exit 1; }

# --- 組 byte-faithful synth 骨架（④a；正文逐字，與 completeness body-hash 定義一致）---
python3 - "${SESS}" "${sess_name}" "${roster}" "${input_files[@]}" <<'PY'
import re, sys
from pathlib import Path

sess = Path(sys.argv[1]); name = sys.argv[2]; roster = sys.argv[3]; inputs = sys.argv[4:]

# 與 completeness_check.sh _check_body_hashes 逐字對齊（漂了會假失敗）：
H2_LINE = re.compile(r"^\s*##(?!#)\s+")
H2_TOK  = re.compile(r"^\s*##(?!#)\s+(\S+)")
CANON   = re.compile(r"^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$")
FAM     = {"CODEX", "COMPOSER", "GROK", "CLAUDE", "AGY"}


def finding_blocks(path):
    """回傳 [(id, 原始body行list)]；body = ## ID 行後至下一個 ## 前（含 nested ###），原始行照搬。"""
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    out = []; cur = None; buf = []
    for ln in lines:
        if H2_LINE.match(ln):
            if cur is not None:
                out.append((cur, buf))
            m = H2_TOK.match(ln.rstrip("\n"))
            tok = m.group(1) if m else ""
            tok = re.split(r"\s+", tok, 1)[0]
            tok = re.sub(r"[^A-Za-z0-9_-].*$", "", tok)
            if CANON.match(tok) and tok.split("-", 1)[0] in FAM:
                cur, buf = tok, []
            else:
                cur, buf = None, []
            continue
        if cur is not None:
            buf.append(ln)
    if cur is not None:
        out.append((cur, buf))
    return out


header = (
    f"# Reconcile — {name}\n\n"
    f"**來源** {', '.join(Path(p).name for p in inputs)}　|　**roster** {roster}\n\n"
    "<!-- ④b 判斷（Claude 手填）：把下方 findings 群集成修訂項、逐條標處置與對應 ID。\n"
    "     此段不含 ## <ID> heading，不影響 body-hash。填完刪本註解。 -->\n\n"
    "## 群集 / 處置（待 Claude 填）\n\n"
    # ⚠️ Verdict 行是**機器解析**的:gate.sh 的 D-1 檢查以 `grep -qE 'Verdict[[:space:]]*[:：]'`
    #    驗 --adversarial 檔。兩次事故:
    #    ①2026-07-29 主委手寫成「Verdict（綜合）：…」→ Verdict 與冒號間插了字 → 正則不中
    #      → 拒發 token;而修 body 會讓已取得的三家戳記 sha 全失效,得整輪重簽。
    #    ②為修①而在此加「**Verdict: （待填…）**」佔位行 → **該佔位行命中正則**
    #      ⇒ 沒填結論的 synth 也能拿到 token(CODEX-R2-P1-13,端到端實跑 GATE PASS rc=0)。
    #    ⇒ 本行**刻意不含**「Verdict+冒號」形態:未填時 gate 照舊拒發(正確),
    #      同時把required 形狀寫給填寫者看,不讓人憑印象手打。
    "**Verdict** ← 未填。填寫時整行改寫為「Verdict」＋半形冒號＋結論"
    "（可合併／需修補後合併／不可合併）\n\n"
    "（待填）\n\n"
    "---\n\n"
    "## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）\n\n"
)

parts = [header]
per_fam = {}
for p in inputs:
    fam = re.sub(r".*-([a-z0-9]+)\.md$", r"\1", Path(p).name)
    blocks = finding_blocks(sess / "sources" / Path(p).name)
    per_fam[Path(p).name] = len(blocks)
    for fid, body in blocks:
        parts.append(f"## {fid}\n")
        parts.append("".join(body))
        if not parts[-1].endswith("\n"):
            parts.append("\n")

(sess / "synth.md").write_text("".join(parts), encoding="utf-8")
print("[reconcile_build] synth.md 已建；每檔抽到 findings：")
for k, v in per_fam.items():
    print(f"    {k}: {v}")
PY
[ "$?" -eq 0 ] || { echo "ERROR: synth 組建失敗" >&2; exit 1; }

# --- 跑 completeness（⑤：機器驗 0 掉項）---
echo "[reconcile_build] === completeness_check ==="
bash "${SCRIPT_DIR}/completeness_check.sh" --lock "${SESS}/sources.lock"
rc=$?
echo "[reconcile_build] completeness rc=${rc}"
if [ "${rc}" -ne 0 ]; then
  echo "[reconcile_build] ⚠️ completeness 未過——多半是某來源檔有非法 ID / 空殼 finding；看上面訊息指的檔+heading。" >&2
  exit "${rc}"
fi
# ── 群集歸戶自檢（2026-08-06 新增；非阻擋，提示用）──────────────────
# 為何存在：`completeness_check` 只驗「ID 有沒有出現在綜合檔」，
#   **對「歸到哪一群」完全無感**——主委本 session 因此 ID 錯位 9 次，
#   每次都要靠委員語意複核抓，一次一輪。
# 本檢查把「群集表引用的 ID」對回「附錄的斷言首句」，讓錯位與掉項在建檔當下可見。
# 誠實邊界：**目前只印不擋**。升為硬閘併入 `票 B-26`（ID 空間配置閘）一起做，
#   不另立票（使用者 2026-08-06：「票永遠開不完，除非有一勞永逸的解決方式」）。
if [ -x "${SCRIPT_DIR}/reconcile_cluster_attribution_check.sh" ]; then
  echo "[reconcile_build] === 群集歸戶自檢（提示，不擋）==="
  bash "${SCRIPT_DIR}/reconcile_cluster_attribution_check.sh" "${SESS}/synth.md" 2>/dev/null \
    | grep -B2 "未被任何群集引用" || echo "  （建檔當下群集段尚未手填，填完請自行重跑本檢查）"
  echo "[reconcile_build] 手填群集後請重跑：bash scripts/reconcile_cluster_attribution_check.sh ${SESS}/synth.md"
fi

echo "[reconcile_build] ✅ 完成。接著：手填 ${SESS}/synth.md 的『群集/處置』(④b)，再改 SPEC/TODO(⑥) + template_check(⑦)。"
