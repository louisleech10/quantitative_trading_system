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
#   bash scripts/reconcile_build.sh <session-name> <委員檔1> <委員檔2> [...]
# 例：
#   bash scripts/reconcile_build.sh p0todo-closure-r4 \
#       handoffs/20260724-p0todo-closure3-codex.md \
#       handoffs/20260724-p0todo-closure3-composer.md
#
# 家族由檔名後綴推定（*-codex.md / *-composer.md / *-grok.md / *-claude.md / *-agy.md）。
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO="$(cd "${SCRIPT_DIR}/.." && pwd)"

sess_name="${1:-}"
shift || true
[ -n "${sess_name}" ] && [ "$#" -ge 1 ] || {
  echo "用法: bash scripts/reconcile_build.sh <session-name> <委員檔1> <委員檔2> [...]" >&2
  exit 2
}

SESS="${REPO}/handoffs/reconcile/${sess_name}"
if [ -e "${SESS}" ]; then
  echo "ERROR: session 已存在，拒覆寫（每輪用新名字，勿踩上一輪）: ${SESS}" >&2
  exit 2
fi

# --- 推家族 + 驗檔存在 ---
_valid_fam="codex composer grok claude agy"
declare -a copied=()
declare -a fams=()
for f in "$@"; do
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

# roster CSV（去重、排序）
roster="$(printf '%s\n' "${fams[@]}" | sort -u | paste -sd, -)"

# --- 建 session + cp ---
mkdir -p "${SESS}/sources"
for f in "$@"; do
  cp "${f}" "${SESS}/sources/$(basename "${f}")"
done
echo "[reconcile_build] session=${SESS}  roster=${roster}  sources=${#copied[@]}"

# --- 寫 lock（fresh，不需 harness）---
bash "${SCRIPT_DIR}/write_sources_lock.sh" --session "${SESS}" --roster "${roster}" --mode discovery \
  || { echo "ERROR: write_sources_lock 失敗" >&2; exit 1; }

# --- 組 byte-faithful synth 骨架（④a；正文逐字，與 completeness body-hash 定義一致）---
python3 - "${SESS}" "${sess_name}" "${roster}" "$@" <<'PY'
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
echo "[reconcile_build] ✅ 完成。接著：手填 ${SESS}/synth.md 的『群集/處置』(④b)，再改 SPEC/TODO(⑥) + template_check(⑦)。"
