#!/usr/bin/env bash
# no_append_only_check.sh — 狀態檔不得以「純檔尾追加」方式更新（流水帳防治）。
#
# ── 為何存在（使用者 2026-08-14 定）────────────────────────────────────
#   「把機制改掉，不管是交接檔和給我看的，都不能有流水帳。」
#
#   **根因不是紀律，是既有機制在獎勵追加**：`plain_docs_sync_check.sh` 的判準
#   **只驗時序**（該檔檔頭自述：「不驗內容是否真的反映現況——可只改一字換綠燈」）。
#   ⇒ 每動一次 `scripts/`，最便宜的合規動作就是在檔尾追加一行日期註記。
#   實測後果：`HANDOFF.md` 長到 495 行、`白話說明/` 九份共 514KB，
#   而使用者要的「現在在哪」被埋在數百行歷史裡。**追加永遠比重寫便宜。**
#
# ── 判準（機械、封閉、不需判斷語意）────────────────────────────────────
#   對每個「狀態檔」：取 HEAD 版與 staged 版。
#   **若 staged 版的前 N 行與 HEAD 版逐字相同（N＝HEAD 行數）且 staged 更長**
#   ⇒ 這次變更是**純檔尾追加** ⇒ rc=1。
#   其餘一律通過（有刪改、有插入中段、檔案變短、新檔、刪檔）。
#
#   ⇒ 這條**強迫改寫現況段**，而不是往下堆。它不管你寫得好不好，
#     只管你有沒有回頭動既有內容。
#
# ── 兩個封閉集合（新增須改本檔，故一定被 review 看到）──────────────────
#   STATE  ＝狀態檔，適用本檢查
#   LEDGER ＝帳本，**追加是正確形態**，明示豁免（摩擦記錄、進度日誌、敘事封存）
#
# ── 誠實邊界 ──────────────────────────────────────────────────────────
#   1. **擋得住「純追加」，擋不住「在中間插一段流水帳」**。後者要判語意，做不到。
#      本檢查是**必要非充分**：它讓最便宜的那條路走不通，不保證產出可讀。
#   2. 只看 staged vs HEAD。未 commit 的中間狀態不管。
#   3. 檔案不在 HEAD（新檔）⇒ 略過；本檢查治的是「既有狀態檔被當成日誌用」。
#
# 用法：
#   bash scripts/no_append_only_check.sh            # 檢查 staged 之狀態檔
#   bash scripts/no_append_only_check.sh --selftest # 自檢（含反例）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

# 🔴 封閉集合，禁萬用字元。新增狀態檔＝改這裡＝一定進 diff 被 review。
_nao_state_files() {
  printf '%s\n' "HANDOFF.md"
  printf '%s\n' "docs/ROADMAP.md"
  printf '%s\n' "白話說明/README.md"
  printf '%s\n' "白話說明/接下來要做什麼.md"
}
# 帳本：追加是正確形態，明示豁免（不列在 STATE 即自動豁免；本函式僅供文件與自檢引用）
_nao_ledger_files() {
  printf '%s\n' "白話說明/流程摩擦記錄.md"
  printf '%s\n' "白話說明/治理進度日誌.md"
  printf '%s\n' "docs/ROADMAP_DETAIL.md"
}

# rc=0 非純追加／不適用；rc=1 純追加
_nao_is_pure_append() {   # $1=old 檔 $2=new 檔
  local o n
  o="$(wc -l < "$1" | tr -d ' ')"
  n="$(wc -l < "$2" | tr -d ' ')"
  [ "${n}" -gt "${o}" ] || return 0            # 沒變長 ⇒ 一定不是純追加
  head -n "${o}" "$2" > "$1.head" 2>/dev/null || return 0
  if cmp -s "$1" "$1.head"; then rm -f "$1.head"; return 1; fi
  rm -f "$1.head"; return 0
}

_nao_scan() {
  local f fail=0 t old new
  t="$(mktemp -d "${TMPDIR:-/tmp}/nao.XXXXXXXX")" || return 2
  while IFS= read -r f; do
    [ -n "${f}" ] || continue
    git diff --cached --quiet -- "${f}" 2>/dev/null && continue   # 本次沒動
    git cat-file -e "HEAD:${f}" 2>/dev/null || continue           # 新檔 ⇒ 略過
    old="${t}/old"; new="${t}/new"
    git show "HEAD:${f}" > "${old}" 2>/dev/null || continue
    git show ":${f}"    > "${new}" 2>/dev/null || continue
    if ! _nao_is_pure_append "${old}" "${new}"; then
      echo "🔴 ${f}：本次變更是**純檔尾追加**（既有內容一字未動）⇒ 拒絕。" >&2
      echo "   狀態檔要的是「現在是什麼」，不是「又發生了什麼」。" >&2
      echo "   修：回頭改寫現況段落；歷史請寫進帳本（流程摩擦記錄／治理進度日誌／ROADMAP_DETAIL）。" >&2
      fail=1
    fi
    rm -f "${old}" "${new}"
  done <<EOF
$(_nao_state_files)
EOF
  rm -rf "${t}"
  return "${fail}"
}

_nao_selftest() {
  local d rc=0
  d="$(mktemp -d "${TMPDIR:-/tmp}/naoself.XXXXXXXX")" || return 2
  printf 'a\nb\nc\n' > "${d}/old"
  printf 'a\nb\nc\nd\n' > "${d}/new_append"     # 純追加 ⇒ 應判 1
  printf 'a\nB\nc\nd\n' > "${d}/new_edit"       # 有改動 ⇒ 應判 0
  printf 'a\nb\n'       > "${d}/new_short"      # 變短   ⇒ 應判 0
  cp "${d}/old" "${d}/o1"; _nao_is_pure_append "${d}/o1" "${d}/new_append"; [ $? -eq 1 ] || { echo "SELFTEST FAIL: 純追加未被判出" >&2; rc=1; }
  cp "${d}/old" "${d}/o2"; _nao_is_pure_append "${d}/o2" "${d}/new_edit";   [ $? -eq 0 ] || { echo "SELFTEST FAIL: 有改動卻被誤判" >&2; rc=1; }
  cp "${d}/old" "${d}/o3"; _nao_is_pure_append "${d}/o3" "${d}/new_short";  [ $? -eq 0 ] || { echo "SELFTEST FAIL: 變短卻被誤判" >&2; rc=1; }
  rm -rf "${d}"
  [ "${rc}" -eq 0 ] && echo "SELFTEST PASS: 純追加判出、有改動放行、變短放行"
  return "${rc}"
}

case "${1:-}" in
  --selftest) _nao_selftest ;;
  ""|--check) _nao_scan ;;
  *) echo "用法: bash scripts/no_append_only_check.sh [--check|--selftest]" >&2; exit 2 ;;
esac
