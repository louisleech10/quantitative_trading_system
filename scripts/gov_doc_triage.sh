#!/usr/bin/env bash
# gov_doc_triage.sh — 治理文件之「能不能封存」機械分流。
#
# ── 為何存在（使用者 2026-08-14 逐字）────────────────────────────────
#   「我甚至覺得這幾萬行的文件留著可能意義也不大，只是一堆雜訊。
#     現在不是有唯一一套治理 epic 的票整理，就留這一套。」
#
#   量到的規模：docs/GOV*.md 42 份 11,157 行。要搬走「純雜訊」那部分，
#   前提是先分辨**哪些被機器引用**——搬錯一份，機檢當場全紅。
#
# ── 四個判準（皆機械可導出，無主觀判斷）────────────────────────────
#   ① fact-key 宿主：`scripts/fact_keys.json` 之任一 key 的 target
#   ② 腳本引用：scripts/*.{sh,py} 之**非註解行**提及該檔名
#   ③ 測試引用：tests/ 底下任一檔提及該檔名
#   ④ 文件連結：其他**不打算封存**的 .md 連到它（搬走會產生死連結，
#      而 check_doc_anchors 已掛 pre-commit ⇒ 會擋 commit）
#
#   四者皆無 ⇒ `可封存`；任一命中 ⇒ `保留` 並列出命中的判準。
#
# ── 誠實邊界 ────────────────────────────────────────────────────────
#   1. 判準 ② 的註解排除與 list_active_mechanisms 同型，**擋不掉 heredoc 內字面量**
#      （shell 層 grep 無法分辨）。⇒ 偏向**誤判為保留**，這是安全方向。
#   2. 本工具只給建議，**不自己搬檔**。搬檔是不可逆動作，須人確認。
#   3. 「可封存」不等於「該封存」——只表示搬走不會弄壞機器。
#
# 用法：bash scripts/gov_doc_triage.sh          # 全部
#       bash scripts/gov_doc_triage.sh --archivable  # 只列可封存者（供接管線）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

_only_archivable=0
[ "${1:-}" = "--archivable" ] && _only_archivable=1
_T="$(mktemp -d "${TMPDIR:-/tmp}/govtriage.XXXXXXXX")" || exit 2
trap 'rm -rf "${_T}"' EXIT

# fact-key 宿主集合（target 可為字串或陣列）
_hosts="$(LC_ALL=C jq -r '
    to_entries[] | select(.key != "_schema") | .value.target //empty
    | if type=="array" then .[] else . end' scripts/fact_keys.json 2>/dev/null | LC_ALL=C sort -u)"

# ── 第一趟：算「硬引用」（fact-key／腳本／測試）。文件連結留到第二趟做不動點 ──
# 🔴 為何要不動點：治理文件彼此大量互連。若把「被任一 .md 連到」直接判成保留，
#   42 份會**全部**保留（實測如此），因為它們互相連結。
#   但**整群一起搬**時，群內連結一起搬走並不會斷 ⇒ 只有「被保留檔連到」才是真阻擋。
#   ⇒ 候選＝無硬引用者；反覆剔除「被非候選 .md 連到」者，直到集合不再變動。
_LINK_ROOTS="docs/ handoffs/ 白話說明/ templates/ tests/ scripts/ CLAUDE.md AGENTS.md HANDOFF.md README.md"

for f in docs/GOV*.md; do
  [ -f "${f}" ] || continue
  b="$(basename "${f}")"
  hits=""

  printf '%s\n' "${_hosts}" | LC_ALL=C grep -qx "${f}" && hits="${hits}fact-key宿主 "

  # 非註解行提及（.sh 用 #，.py 亦用 #）
  if LC_ALL=C grep -rl --include='*.sh' --include='*.py' -- "${b}" scripts/ 2>/dev/null \
     | while IFS= read -r s; do
         LC_ALL=C grep -v '^[[:space:]]*#' "${s}" 2>/dev/null | LC_ALL=C grep -q -- "${b}" && { echo hit; break; }
       done | LC_ALL=C grep -q hit; then
    hits="${hits}腳本引用 "
  fi

  LC_ALL=C grep -rq --include='*.py' --include='*.txt' -- "${b}" tests/ 2>/dev/null && hits="${hits}測試引用 "

  if [ -n "${hits}" ]; then
    printf '保留\t%s\t%s\t(%s)\n' "$(wc -l < "${f}" | tr -d ' ')" "${f}" "${hits% }"
  else
    printf '候選\t%s\t%s\t()\n' "$(wc -l < "${f}" | tr -d ' ')" "${f}"
  fi
done > "${_T}/pass1"

# ── 第二趟：不動點。被**非候選** .md 連到者剔出候選 ──
LC_ALL=C awk -F'\t' '$1=="候選" { print $3 }' "${_T}/pass1" | LC_ALL=C sort > "${_T}/cand"
_round=0
while :; do
  _round=$((_round + 1))
  : > "${_T}/drop"
  while IFS= read -r f; do
    [ -n "${f}" ] || continue
    b="$(basename "${f}")"
    # 連到 f 的 .md（排除 Archived 與自己）
    # shellcheck disable=SC2086
    LC_ALL=C grep -rl --include='*.md' -- "${b}" ${_LINK_ROOTS} 2>/dev/null \
      | LC_ALL=C grep -v "^docs/Archived/" | LC_ALL=C grep -v "^${f}$" \
      | LC_ALL=C sort -u > "${_T}/linkers"
    # 只要有任一 linker 不在候選集合內 ⇒ 剔除
    if LC_ALL=C comm -23 "${_T}/linkers" "${_T}/cand" | LC_ALL=C grep -q .; then
      printf '%s\n' "${f}" >> "${_T}/drop"
    fi
  done < "${_T}/cand"
  [ -s "${_T}/drop" ] || break
  LC_ALL=C comm -23 "${_T}/cand" "${_T}/drop" > "${_T}/cand.new"
  mv "${_T}/cand.new" "${_T}/cand"
  [ "${_round}" -lt 20 ] || { echo "gov_doc_triage: 不動點未在 20 輪內收斂 → 保守全判保留" >&2; : > "${_T}/cand"; break; }
done

# ── 輸出 ──
while IFS=$'\t' read -r st ln f rs; do
  if LC_ALL=C grep -qx "${f}" "${_T}/cand" 2>/dev/null; then
    printf '可封存\t%s\t%s\n' "${ln}" "${f}"
  elif [ "${_only_archivable}" -eq 0 ]; then
    [ "${st}" = "候選" ] && rs="(被保留檔連結)"
    printf '保留\t%s\t%s\t%s\n' "${ln}" "${f}" "${rs}"
  fi
done < "${_T}/pass1"
rm -rf "${_T}"
