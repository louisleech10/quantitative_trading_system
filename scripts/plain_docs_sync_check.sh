#!/usr/bin/env bash
# plain_docs_sync_check.sh — 白話說明/ 過期偵測（產出端強制，非靠紀律）
#
# 為何存在（2026-08-05 使用者指出）：
#   「白話說明和日誌你忘記或沒做即時更新，就斷了」。
#   使用者定死的治理第 3 原則＝「工具必須自帶強制機制，不准靠紀律和記憶」。
#   ⇒ 本腳本把「記得更新白話版」從紀律變成機檢。
#
# 判準（可機械算，無主觀）：
#   白話說明/README.md 內須有一行 `SYNCED-AT: <40 位 commit sha>`。
#   自該 sha 起（不含）至 HEAD，若有任何 commit 觸及 WATCHED 路徑，
#   而該區間內 白話說明/README.md 未被改動 ⇒ rc=1（白話版已過期）。
#
# WATCHED＝「使用者會想知道進度」的路徑：
#   scripts/            實作改動
#   docs/GOVB0_         第 0 批 SPEC/TODO
#   tests/governance/   治理測試（實作的驗收面）
#
# 誠實邊界：
#   本檢查只驗「有沒有動」，**不驗內容是否真的反映現況**——
#   有人可以只改一個字元換綠燈。這屬「擋意外不防蓄意」，與本專案既有機檢同級。
#   內容正確性仍靠 code review。
#
# 憲法：bash 3.2；rc 直接取禁經 pipe；不新增狀態檔。
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: 非 git repo（fail-closed）" >&2; exit 2; }
cd "${REPO}" || exit 2

README="白話說明/README.md"
WATCHED="scripts/ docs/GOVB0_ tests/governance/"

[ -f "${README}" ] || { echo "ERROR: ${README} 不存在（fail-closed）" >&2; exit 2; }

# ── 取 SYNCED-AT 標記（行首錨定；未錨定會被本檔自身的說明文字污染）──
synced="$(LC_ALL=C grep -m1 '^SYNCED-AT: ' "${README}" | awk '{print $2}')"
if [ -z "${synced}" ]; then
  echo "ERROR: ${README} 缺 '^SYNCED-AT: <sha>' 標記（fail-closed）" >&2
  echo "  修：在 README 加一行 SYNCED-AT: \$(git rev-parse HEAD)" >&2
  exit 2
fi

git cat-file -e "${synced}^{commit}" 2>/dev/null || {
  echo "ERROR: SYNCED-AT 的 sha 不是合法 commit: ${synced}（fail-closed）" >&2
  exit 2
}

# ── 區間內是否有 WATCHED 改動 ──
# shellcheck disable=SC2086
watched_n="$(git log --oneline "${synced}..HEAD" -- ${WATCHED} | wc -l | tr -d ' ')"

if [ "${watched_n}" -eq 0 ]; then
  echo "[plain_docs_sync] ✓ 白話說明 為最新（自 ${synced:0:8} 起無實作/規格改動）"
  exit 0
fi

# ── 區間內 README 是否也被改過 ──
readme_n="$(git log --oneline "${synced}..HEAD" -- "${README}" | wc -l | tr -d ' ')"

if [ "${readme_n}" -gt 0 ]; then
  echo "[plain_docs_sync] ✓ 白話說明 已隨改動更新（${watched_n} 個實作 commit／${readme_n} 個 README commit）"
  echo "[plain_docs_sync] ℹ 提醒：更新後請把 SYNCED-AT 推進到最新 sha，否則下次仍會告警"
  exit 0
fi

echo "[plain_docs_sync] ✗ 白話說明已過期" >&2
echo "  自 SYNCED-AT ${synced:0:8} 起有 ${watched_n} 個 commit 觸及實作/規格，但 ${README} 未更新。" >&2
echo "  觸及的 commit：" >&2
# shellcheck disable=SC2086
git log --oneline "${synced}..HEAD" -- ${WATCHED} | sed 's/^/    /' >&2
echo "  修：更新 ${README}（進度區塊）與對應施工清單，並把 SYNCED-AT 改為 \$(git rev-parse HEAD)。" >&2
echo "  出處：使用者 2026-08-05「白話說明和日誌你忘記或沒做即時更新，就斷了」。" >&2
exit 1
