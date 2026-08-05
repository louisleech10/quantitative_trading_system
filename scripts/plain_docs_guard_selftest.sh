#!/usr/bin/env bash
# plain_docs_guard_selftest.sh — 證明 plain_docs_sync_check.sh 的「進度單一出處」守衛非空心。
#
# 為何存在（2026-08-05）：
#   使用者問「你到底是要強制更新還是沒有？看有些更新有些又沒有」。
#   根因＝進度被抄在四個檔裡，其中 第0批-在做什麼.md 的 WATCHED 是**規格**（凍結後永不變動），
#   ⇒ 它寫著「實作還沒開始」時實際已完成 4 批，而所有檢查全綠。
#   修法＝進度只留 README／施工清單，其餘檔禁止出現進度表，並由守衛強制。
#   本腳本證明該守衛**改壞會紅**——否則「加了守衛」只是宣稱。
#
# 判準：注入進度表 ⇒ 必須 rc=2；移除後 ⇒ 必須非 2。任一不成立即 FAIL。
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null || echo .)"
cd "${REPO}" || exit 2

TARGET="白話說明/第0批-在做什麼.md"          # WATCHED=規格，故禁含進度
CHECK="scripts/plain_docs_sync_check.sh"

[ -f "${TARGET}" ] || { echo "SKIP: ${TARGET} 不存在（可能已封存）"; exit 0; }
[ -f "${CHECK}" ]  || { echo "ERROR: ${CHECK} 不存在"; exit 2; }

before_lines="$(wc -l < "${TARGET}")"
restored=0

_restore() {
  [ "${restored}" -eq 1 ] && return 0
  sed -i '' -e '$d' "${TARGET}" 2>/dev/null || sed -i -e '$d' "${TARGET}"
  restored=1
  after="$(wc -l < "${TARGET}")"
  if [ "${after}" -ne "${before_lines}" ]; then
    echo "ERROR: 還原失敗 ${TARGET}（${before_lines} → ${after} 行）——請人工檢查" >&2
    exit 2
  fi
}
trap _restore EXIT INT TERM

printf '| 實作 | ⬜ 還沒開始 |\n' >> "${TARGET}"
bash "${CHECK}" > /dev/null 2>&1
mut_rc=$?                                    # rc 直接取，禁經 pipe

_restore
bash "${CHECK}" > /dev/null 2>&1
res_rc=$?

fail=0
if [ "${mut_rc}" -ne 2 ]; then
  echo "FAIL: 注入進度表後 rc=${mut_rc}（期望 2）⇒ 守衛空心，未偵測到違規" >&2
  fail=1
fi
if [ "${res_rc}" -eq 2 ]; then
  echo "FAIL: 移除後 rc 仍為 2 ⇒ 守衛恆真，無鑑別力" >&2
  fail=1
fi

[ "${fail}" -eq 0 ] || exit 1
echo "PASS: 進度單一出處守衛可證偽（注入 rc=${mut_rc}／還原 rc=${res_rc}）"
exit 0
