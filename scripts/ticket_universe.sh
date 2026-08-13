#!/usr/bin/env bash
# ticket_universe.sh — 治理票之全集列舉與對帳（`governance-sot-plan` 之 S0.1）。
#
# 病根：61 張票原本是一次性腳本抽出來後填進表的，**抽法沒留下、也無對帳**
#   ⇒ 日後新增票時只寫一邊（backlog 或 SoT），沒有任何東西會發現不一致
#   ⇒ 「兩套對不齊」這個本 epic 花最多力氣收拾的病，會在新增票時復發。
#
# 🔴 票號格式**寫死於本檔**，非由資料自證——自證＝無檢查（同 `_FK_RESERVED` 之紀律）。
#   實測依據：backlog 之 `^## ` 標題中，符合本格式者恰 61 張且**無格式例外**；
#   其餘 `^## ` 標題為群組標題等非票項（如「第一群：凍結程序 v0.5」），刻意不納入。
_TU_TICKET_RE='^## (B-[0-9]+)( |$)'
#
# 🔴 `B3R` **不是票**：backlog 無 `## B3R` 標題，它是批次代號（見 governance-batch-status）。
#   舊表曾把它當票，那是型別混用；本檔不予收錄，亦不設白名單例外。
#
# 用法：
#   bash scripts/ticket_universe.sh --list    # 列出全集（一行一票號，LC_ALL=C 排序）
#   bash scripts/ticket_universe.sh --count   # 只印張數
#   bash scripts/ticket_universe.sh --check   # 與 SoT 對帳；不一致 ⇒ rc=1（fail-closed）
# rc: 0=一致；1=不一致或列舉失敗；2=用法錯誤
set -uo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKLOG="${REPO_ROOT}/handoffs/20260801-GOV-AMEND-BACKLOG.md"
REG="${SCRIPT_DIR}/fact_keys.json"
SOT_KEY="governance-ticket-sot"

_tu_die() { printf '%s\n' "$*" >&2; exit 1; }

# 全集：由 backlog 標題導出。**不另存副本**——副本就是第二套。
_tu_list() {
  [ -f "${BACKLOG}" ] || _tu_die "ticket_universe: 缺 backlog ${BACKLOG} → fail-closed"
  LC_ALL=C grep -oE "${_TU_TICKET_RE}" "${BACKLOG}" 2>/dev/null \
    | LC_ALL=C sed -E 's/^## //; s/ $//' \
    | LC_ALL=C sort -u
}

_tu_sot() {
  [ -f "${REG}" ] || _tu_die "ticket_universe: 缺註冊表 ${REG} → fail-closed"
  command -v jq >/dev/null 2>&1 || _tu_die "ticket_universe: 缺 jq → fail-closed"
  # 🔴 jq rc 不得吞（本 epic 三次同型事故）：先落變數再驗
  _tus_out="$(LC_ALL=C jq -er --arg k "${SOT_KEY}" '
      (.[$k].columns | index("票")) as $i
      | if $i == null then error("no-ticket-column") else . end
      | [ .[$k].rows[] | .[$i] ] | sort | .[]' "${REG}")" \
    || _tu_die "ticket_universe: 讀 SoT 票欄失敗（jq 非零）→ fail-closed"
  printf '%s\n' "${_tus_out}"
}

case "${1-}" in
  --list)  _tu_list ;;
  --count) _tu_list | LC_ALL=C wc -l | tr -d ' ' ;;
  --check)
    _tu_u="$(_tu_list)" || exit 1
    _tu_s="$(_tu_sot)"  || exit 1
    [ -n "${_tu_u}" ] || _tu_die "ticket_universe: 全集為空（backlog 格式改了？）→ fail-closed"

    # 🔴 **單向**檢查，非集合相等。理由（使用者 2026-08-13 指出主委設計矛盾）：
    #   backlog 已宣告作廢、不再編輯 ⇒ 若要求「恰等於」，新增一張票就會逼人去寫作廢檔。
    #   舊模型（backlog 是票的正本）已不成立，全集由 SoT 自己定義。
    _tu_only_bl="$(LC_ALL=C comm -23 <(printf '%s\n' "${_tu_u}") <(printf '%s\n' "${_tu_s}"))"
    _tu_new="$(LC_ALL=C comm -13 <(printf '%s\n' "${_tu_u}") <(printf '%s\n' "${_tu_s}"))"

    _tu_rc=0
    # ① 遷移完整性：backlog 有而 SoT 缺 ⇒ 當初漏搬
    [ -z "${_tu_only_bl}" ] || {
      echo "TICKET-UNIVERSE: 下列票在 backlog（已作廢）有、但 SoT 缺 ⇒ 遷移漏搬 → fail-closed:" >&2
      printf '%s\n' "${_tu_only_bl}" | sed 's/^/    /' >&2
      _tu_rc=1; }
    # ② 新票只寫 SoT 是**正確行為**，不判紅；改以票號格式擋打錯字（防幽靈票之正解）
    while IFS= read -r _tu_t; do
      [ -n "${_tu_t}" ] || continue
      printf '%s' "${_tu_t}" | LC_ALL=C grep -qE '^B-[0-9]+$' || {
        echo "TICKET-UNIVERSE: SoT 之票號格式非法：${_tu_t}（須為 B-<正整數>）→ fail-closed" >&2
        _tu_rc=1; }
    done <<EOF
${_tu_new}
EOF
    [ "${_tu_rc}" = "0" ] && {
      printf 'TICKET-UNIVERSE PASS: SoT %s 張（其中 %s 張為 backlog 之後新增，屬正常）。\n' \
        "$(printf '%s\n' "${_tu_s}" | grep -c . )" \
        "$(printf '%s\n' "${_tu_new}" | grep -c . )"; }
    exit "${_tu_rc}" ;;
  -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
  *) echo "用法: bash scripts/ticket_universe.sh --list|--count|--check" >&2; exit 2 ;;
esac
