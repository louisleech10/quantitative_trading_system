#!/usr/bin/env bash
# mount_triage.sh — 全部腳本之掛載分流：每支只有「已掛」「可掛」「不掛」三種去向。
#
# 為何存在（使用者 2026-08-14T18:40+08:00 定死）：
#   「全部的票和腳本，該掛哪／為何沒掛／能不能掛，可以掛的就要掛上去，
#     只有掛和不掛兩種結果，不掛就要有原因，耗費時間太多也是原因。
#     沒有什麼可能、推理、想看看——你用推理都全錯。」
#
# 🔴 本檔只做**機械可判定**的部分，不做判斷：
#   ① 有沒有失敗條件（無 ⇒ 掛了也不會擋任何東西 ⇒ 判定為「不掛：無拒絕語意」）
#   ② 現在有沒有被呼叫（settings.json／git hooks／被已掛者呼叫）
#   ③ 讀什麼輸入（決定它只能掛哪一類掛載點）
#   判定不了的一律標 NEEDS-PROBE，交實測，**不得用推理填**。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SETTINGS=".claude/settings.json"
GITHOOKS="scripts/git_hooks"

# ── 已掛集合：settings.json 之 hook 指令 ＋ git hooks 內呼叫者 ＋ 其遞移呼叫（深度 3）──
_mt_mounted_roots() {
  LC_ALL=C jq -r '(.hooks // {}) | to_entries[] | .value[] | (.hooks // [])[] | .command // ""' "${SETTINGS}" 2>/dev/null \
    | LC_ALL=C sed -nE 's#^bash +([^ ]*/)?(scripts/)?([A-Za-z0-9_]+\.(sh|py)).*#\3#p'
  [ -d "${GITHOOKS}" ] && LC_ALL=C grep -rhoE '(scripts/)?[A-Za-z0-9_]+\.(sh|py)' "${GITHOOKS}" 2>/dev/null \
    | LC_ALL=C sed -E 's#^scripts/##'
}
_mt_calls() {   # $1=腳本 basename → 它呼叫的腳本 basename
  [ -f "scripts/$1" ] || return 0
  LC_ALL=C grep -ohE '(\$\{SCRIPT_DIR\}/|scripts/)[A-Za-z0-9_]+\.(sh|py)' "scripts/$1" 2>/dev/null \
    | LC_ALL=C sed -E 's#.*/##'
}
_mt_mounted_set() {
  local cur next i
  cur="$(_mt_mounted_roots | LC_ALL=C sort -u)"
  for i in 1 2 3; do
    next="$(for s in ${cur}; do echo "${s}"; _mt_calls "${s}"; done | LC_ALL=C sort -u)"
    [ "${next}" = "${cur}" ] && break
    cur="${next}"
  done
  printf '%s\n' "${cur}"
}

MOUNTED="$(_mt_mounted_set)"

# ── 逐支分類 ──
printf '%-38s %-8s %-10s %s\n' "腳本" "失敗條件" "掛載" "去向"
for f in scripts/*.sh scripts/*.py; do
  [ -f "${f}" ] || continue
  b="$(basename "${f}")"
  # ① 失敗條件：是否存在非零退出路徑（排除註解行）
  if LC_ALL=C grep -vE '^[[:space:]]*#' "${f}" \
     | LC_ALL=C grep -qE '(exit|return)[[:space:]]+[1-9]|sys\.exit\([1-9]|rc=1|_rc=1'; then
    fail="有"
  else
    fail="無"
  fi
  # ② 掛載
  if printf '%s\n' "${MOUNTED}" | LC_ALL=C grep -qxF "${b}"; then mnt="已掛"; else mnt="未掛"; fi
  # ③ 是否為**治理域**：有沒有引用治理資產。非治理域者不在本 epic 範圍。
  if LC_ALL=C grep -qE '\.claude/gate|handoffs/|docs/GOV|fact_keys|govflow|audit\.log|committee|reconcile|debt_' "${f}" 2>/dev/null; then
    gov="治理"
  else
    gov="非治理"
  fi
  # ④ 是否為**檢查型**：檢查不改狀態；會寫入 repo 內檔案者屬產生器／操作。
  #    判準用「有無寫入重導或 cp/mv/mkdir 指向非暫存路徑」，機械可判。
  if LC_ALL=C grep -vE '^[[:space:]]*#' "${f}" 2>/dev/null \
     | LC_ALL=C grep -qE '(^|[^>])>[[:space:]]*"?\$\{?(SCRIPT_DIR|REPO_ROOT|REG|SRC|LOG|out)|(cp|mv|mkdir)[[:space:]]+-?[a-z]*[[:space:]]*"?(scripts|docs|handoffs|白話)'; then
    typ="操作"
  else
    typ="檢查"
  fi
  # ⑤ 去向（只有三種，判不了的標 NEEDS-PROBE）
  if   [ "${mnt}" = "已掛" ];    then dest="已掛"
  elif [ "${gov}" = "非治理" ];  then dest="不掛：非治理檢查（本 epic 範圍外）"
  elif [ "${fail}" = "無" ];     then dest="不掛：無拒絕語意（掛了也不會擋任何東西）"
  elif [ "${typ}" = "操作" ];    then dest="不掛：產生器／操作型，非檢查"
  else dest="NEEDS-PROBE"
  fi
  printf '%-38s %-8s %-10s %s\n' "${b}" "${fail}" "${mnt}" "${dest}"
done
