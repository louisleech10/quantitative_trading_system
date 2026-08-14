#!/usr/bin/env bash
# G-7 前移檢查（commit-msg 階段）：staged 檔含 scope 外路徑而訊息無 trailer ⇒ 擋。
#
# 為何存在（S6.1，2026-08-14T10:30+08:00）：
#   G-7 的判定式是 `base..HEAD` 的 endpoint 淨差 ⇒ **寫檔當下算不出來**，
#   `docs/GOV_ENFORCEMENT_REGISTRY.md` 之 `E-005` 因此登記為豁免，
#   理由寫「本票不存在可前移的靜態子集」。🔴 那句是錯的：
#   「這次 staged 的路徑在不在 scope 白名單內」**只需 manifest 與路徑**，
#   commit 當下完全可算；缺的只是「訊息有沒有帶 trailer」，而 commit-msg 拿得到訊息檔。
#
#   代價實證（2026-08-14 同一天內兩次）：新建 `docs/GOV_*.md` 與 `scripts/*.sh` 後
#   commit 未帶 trailer ⇒ G-7 直到 14 分鐘的 pre-push 才紅，而
#   🔴 **G-7 的豁免是「該路徑在範圍內*只*被帶 trailer 的 commit 觸及」⇒ 補後續 commit 解不掉**，
#   只能 `reset --mixed` ＋ `--amend` 重寫歷史。本檢查把那個代價收斂成 commit 當下的一行提示。
#
# 🔴 單一來源：白名單一律向 `govb1_final_gate.sh --print-scope` 取，**不自行複寫 allow−deny**。
#   複寫必漂移，且漂移方向必然是「前移檢查較寬」⇒ 放行後仍在 pre-push 紅 ⇒ 前移形同未做。
#
# 🔴 不死鎖：白名單導不出來（例如 manifest 雜湊在合法變更當下不符）⇒ **要求 trailer**，
#   而不是一律拒絕。否則「修 manifest 的那一筆 commit」永遠提交不了——
#   與 S3.2 記錄的「一致性型檢查掛 PreToolUse 會死鎖」是同一種病。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 0

msg_file="${1:-}"
[ -n "${msg_file}" ] && [ -f "${msg_file}" ] || exit 0

TRAILER_KEY='Governance-Scope'

# --- 1) staged 路徑 ---
# 🔴 三家 r2 之 CODEX-R2-P0-03 於隔離 repo 實構出三條靜默放行，逐條修在這裡：
#   ① `| tr '\0' '\n'` 會把**含換行的路徑**切成兩個碎片，驗到的不是原始路徑；
#      且 git 的 rc 被 pipe 吃掉——`GIT_INDEX_FILE=<不存在>` 時 git 失敗卻 rc=0 放行。
#      ⇒ 改 `while read -r -d ''` 逐筆讀 NUL，並**先把輸出落檔再取 rc**。
#   ② `--diff-filter=ACMRD` 漏 `T`（type change，如檔案改成 symlink）⇒ 補上。
#   ③ `--name-only` 對 rename **隱去舊名**（GROK-R2-P2-01：scope 外 git mv 進 scope 內即漏擋）
#      ⇒ 改 `--name-status`，R/C 記錄的**舊名與新名都納入**判定。
_tmp="$(mktemp)"
git diff --cached --name-status -z --diff-filter=ACMRDT > "${_tmp}" 2>/dev/null; _grc=$?
if [ "${_grc}" -ne 0 ]; then
  echo "🔴 G-7 前移檢查：無法讀取 staged 內容（git diff rc=${_grc}）⇒ fail-closed，請修復後再 commit。" >&2
  rm -f "${_tmp}"
  exit 1
fi
# 🔴 路徑存**陣列**不存換行分隔字串：含換行的路徑用字串裝會在下一層再被切開一次，
#   等於修了 tr 卻在自己的迴圈裡重犯同一個錯。
_paths=()
while IFS= read -r -d '' _st; do
  [ -n "${_st}" ] || continue
  # R/C 之記錄形態：<status>\0<舊名>\0<新名>；其餘：<status>\0<路徑>
  IFS= read -r -d '' _p1 || break
  _paths+=("${_p1}")
  case "${_st}" in
    R*|C*)
      IFS= read -r -d '' _p2 || break
      _paths+=("${_p2}")
      ;;
  esac
done < "${_tmp}"
rm -f "${_tmp}"
[ "${#_paths[@]}" -gt 0 ] || exit 0

# --- 2) scope 白名單（單一來源；導不出來即視為「全部未涵蓋」）---
scope=""
scope_err=""
if [ -f scripts/govb1_final_gate.sh ]; then
  # 🔴 rc 直接落變數再判，不經 pipe、不靠隱含 $?（本專案最常見的空心來源）
  scope="$(bash scripts/govb1_final_gate.sh --print-scope 2>&1)"; _rc=$?
  if [ "${_rc}" -ne 0 ] || [ -z "${scope}" ]; then
    scope_err="${scope}"
    scope=""
  fi
else
  scope_err="缺 scripts/govb1_final_gate.sh"
fi

# --- 3) 逐路徑判涵蓋（與 _g7_covered 同規則：以 / 結尾＝前綴，否則字面相等）---
_uncovered=()
for p in "${_paths[@]}"; do
  [ -n "${p}" ] || continue
  hit=0
  while IFS= read -r d; do
    [ -n "${d}" ] || continue
    case "${d}" in
      */) case "${p}" in "${d}"*) hit=1 ;; esac ;;
      *)  [ "${p}" = "${d}" ] && hit=1 ;;
    esac
    [ "${hit}" -eq 1 ] && break
  done <<EOF
${scope}
EOF
  [ "${hit}" -eq 1 ] || _uncovered+=("${p}")
done

[ "${#_uncovered[@]}" -gt 0 ] || exit 0

# --- 4) trailer 判定：交給 **git 自己的解析器**，不自寫 ---
# 🔴 原本以 awk 取最後一段再 grep，CODEX-R2-P0-03 實構出反例：
#   訊息末段為「Governance-Scope: out-of-epic」後面再接一行 `garbage`，
#   我的 grep 判「有 trailer」而 `git interpret-trailers --parse` **無輸出**
#   ——git 要求最末段整段都是 trailer 才算。判準與 G-7 消費端不一致 ⇒ 放行了會紅的 commit。
#   單一來源原則：凡「git 認不認」的問題一律問 git。
_trailers="$(git interpret-trailers --parse < "${msg_file}" 2>/dev/null)"; _trc=$?
if [ "${_trc}" -eq 0 ] \
   && printf '%s\n' "${_trailers}" | grep -qE "^${TRAILER_KEY}:[[:space:]]*[^[:space:]]"; then
  exit 0
fi

{
  echo "🔴 G-7 前移檢查未過：本次 staged 含 **scope 外路徑**，但 commit 訊息的最後一段沒有 ${TRAILER_KEY} trailer。"
  echo
  echo "scope 外路徑："
  for _u in "${_uncovered[@]}"; do printf '  · %s\n' "${_u}"; done
  [ -n "${scope_err}" ] && { echo; echo "（白名單導出失敗，已保守視為全部未涵蓋）：${scope_err}"; }
  echo
  echo "修法：在 commit 訊息**最後一段**加上（git 只解析最末段，放中間無效）："
  echo "  ${TRAILER_KEY}: out-of-epic <一句話說明這些路徑為何在 epic scope 外>"
  echo
  echo "🔴 現在不加就只能重寫歷史：G-7 的豁免是「該路徑在範圍內**只**被帶 trailer 的 commit 觸及」，"
  echo "   一旦有一筆無 trailer 的 commit 碰過它，補後續 commit 解不掉。"
} >&2
exit 1
