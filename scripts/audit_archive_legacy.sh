#!/usr/bin/env bash
# audit_archive_legacy.sh — 一次性：把 audit.log 的非債務白名單事件整批封存
#
# 為何存在（使用者 2026-08-05 定死「面向未來，不溯及既往」）：
#   audit.log 已 34,477 行，使 gate_check 每次都要讀完 ⇒ latency 測試紅（改動前的版本同樣紅，
#   非任何一批實作造成）。原線 C 草案想「分析散文、抽取 JSON 沒有的資訊再遷移」——
#   那是對歷史資料做考古，複雜且不收斂。
#   使用者原則：**修正是考慮以後，不要把以前的錯誤或不合規包回來**。
#   ⇒ 本腳本**不解析、不遷移**，只做整批原樣搬移。
#
# 安全前提（已實測，見下 verify 段會再自動驗一次）：
#   `_debt_ledger_core.py:114` 明寫「非白名單 debt／legacy：略過」
#   ⇒ 序號連續性只檢查白名單事件，且其 sequence 為自身獨立編號（實測 1,2,3,4,5…）
#   ⇒ 搬走非白名單行**不會**造成缺號。
#
# 誠實邊界：
#   封存檔為**唯讀歷史**，位元組不失真、隨時可查，但**機器不再讀它**。
#   本腳本一次性；持續性的輪替規則屬 P1-6 線 C 完整版（第 0.5 批）。
#
# 憲法：bash 3.2；rc 直接取禁經 pipe；失敗一律還原。
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: 非 git repo" >&2; exit 2; }
cd "${REPO}" || exit 2

LOG=".claude/gate/audit.log"
ARCHIVE_DIR=".claude/gate/archive"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${ARCHIVE_DIR}/audit-legacy-${STAMP}.log"
BACKUP=".claude/gate/audit.log.bak-${STAMP}"

[ -f "${LOG}" ] || { echo "ERROR: ${LOG} 不存在（fail-closed）" >&2; exit 2; }
mkdir -p "${ARCHIVE_DIR}" || exit 2

# 白名單自 SoT 讀，禁硬編
WL="$(jq -r '.debt_events | keys[]' scripts/audit_events.json 2>/dev/null)"
[ -n "${WL}" ] || { echo "ERROR: 無法自 audit_events.json 讀 debt_events（fail-closed）" >&2; exit 2; }

echo "[archive] 白名單事件："
echo "${WL}" | sed 's/^/    /'

# 備份（失敗時還原用）
cp "${LOG}" "${BACKUP}" || { echo "ERROR: 備份失敗" >&2; exit 2; }
before_n="$(LC_ALL=C grep -ac '' "${LOG}")"

# 用 awk 一次分流：白名單 → 新 active；其餘 → archive
# 🔴 macOS awk 不接受含換行的 -v 變數（實測 "newline in string"）⇒ 先轉為空白分隔
WL_FLAT="$(printf '%s' "${WL}" | tr '\n' ' ')"

# shellcheck disable=SC2016
LC_ALL=C awk -v wl="${WL_FLAT}" '
BEGIN { n=split(wl, a, " "); for (i=1;i<=n;i++) if (a[i]!="") keep["\"event\": \"" a[i] "\""]=1 }
{
  hit=0
  for (k in keep) { if (index($0, k)) { hit=1; break } }
  if (hit) print > ACTIVE; else print > ARCH
}
' ACTIVE="${LOG}.new" ARCH="${ARCHIVE}" "${LOG}"

[ -f "${LOG}.new" ] || { echo "ERROR: 分流未產生 active 檔（fail-closed）" >&2; rm -f "${ARCHIVE}"; exit 2; }

active_n="$(LC_ALL=C grep -ac '' "${LOG}.new")"
arch_n="$(LC_ALL=C grep -ac '' "${ARCHIVE}")"
sum=$((active_n + arch_n))

echo "[archive] 原 ${before_n} 行 → active ${active_n} ＋ archive ${arch_n} = ${sum}"
if [ "${sum}" -ne "${before_n}" ]; then
  echo "ERROR: 行數不守恆（${sum} != ${before_n}）⇒ 還原（fail-closed）" >&2
  rm -f "${LOG}.new" "${ARCHIVE}"
  exit 1
fi

# 就位
mv "${LOG}.new" "${LOG}" || { echo "ERROR: 就位失敗 ⇒ 自備份還原" >&2; cp "${BACKUP}" "${LOG}"; exit 1; }

# ── 驗證：debt_ledger 必須仍可運作且結論不變 ────────────
echo "[archive] === 驗證 ==="
bash scripts/debt_ledger.sh --has-open > /dev/null 2>&1
has_open_rc=$?
if [ "${has_open_rc}" -eq 2 ]; then
  echo "ERROR: debt_ledger fail-closed（rc=2）⇒ 自備份還原" >&2
  cp "${BACKUP}" "${LOG}"
  rm -f "${ARCHIVE}"
  exit 1
fi
echo "[archive] ✓ debt_ledger --has-open rc=${has_open_rc}（0=無OPEN／1=有OPEN；2 才是壞掉）"

rounds_n="$(bash scripts/debt_ledger.sh --list 2>/dev/null | LC_ALL=C grep -c 'round_id=')"
echo "[archive] ✓ debt_ledger --list 可列出 ${rounds_n} 個 round"
if [ "${rounds_n}" -eq 0 ]; then
  echo "ERROR: round 數為 0（原本應 >0）⇒ 自備份還原" >&2
  cp "${BACKUP}" "${LOG}"
  rm -f "${ARCHIVE}"
  exit 1
fi

echo "[archive] ✅ 完成"
echo "  active : ${LOG}（${active_n} 行）"
echo "  archive: ${ARCHIVE}（${arch_n} 行，唯讀歷史，機器不再讀）"
echo "  backup : ${BACKUP}（確認無誤後可刪）"
