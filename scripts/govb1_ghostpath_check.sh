#!/usr/bin/env bash
# govb1_ghostpath_check.sh — 列出 GOVB1 epic 的「幽靈路徑」。
#
# 幽靈路徑 ＝ 同時滿足三者的檔案：
#   ① `base..HEAD` 的 **endpoint 淨差為零** ⇒ G-7 現在看不到它
#   ② 在 range 內被至少一個**不帶 `Governance-Scope` trailer** 的 commit 觸及
#      ⇒ `path-only-OOE` 豁免已被毒化，**永久失效**
#   ③ 不在 `scripts/govb1_scope.manifest` 的 allow 清單
#
# ⇒ 這種路徑**現在是綠的，但一被改動就會立刻 G-7 紅**，且 OOE trailer 救不了。
#
# 為何存在（2026-08-12）：主委 commit 了一個這樣的檔（`test_cxrun_selfcheck_prompt.py`），
#   全套由 4 紅變 7 紅。三家 consult 裁定「逐案處理、不批次 allow」，並要求
#   「改任一幽靈路徑前先決定 allow 或接受 G-7 紅」。
#   🔴 那是一條純紀律的規則 ⇒ 依使用者定死之「工具必須自帶強制機制，不准靠紀律和記憶」，
#   做成本腳本。跑它比記得它容易。
#
# 用法：bash scripts/govb1_ghostpath_check.sh [--paths-only]
# 退出碼：恆 0（本工具是**盤點**，不是閘門；當閘門用會把既有狀態一律判紅）。
set -u

cd "$(git rev-parse --show-toplevel)" || exit 2

MANIFEST="scripts/govb1_scope.manifest"
FROZEN="scripts/govb1_frozen_hashes.txt"
paths_only=0
[ "${1:-}" = "--paths-only" ] && paths_only=1

BASE="$(grep -m1 '^base_commit:' "${FROZEN}" | awk '{print $2}')"
[ -n "${BASE}" ] || { echo "ERROR: 讀不到 base_commit（fail-closed）" >&2; exit 2; }

n=0
# range 內被觸及過的所有路徑（含淨差為零者）——故走 log 而非 diff
while IFS= read -r p; do
  [ -n "${p}" ] || continue
  # ③ 不在 allow
  grep -qxF "allow ${p}" "${MANIFEST}" && continue
  # ① 淨差須為零（非零者已經是活躍問題，不屬「幽靈」）
  [ -z "$(git diff --name-only "${BASE}" HEAD -- "${p}")" ] || continue
  # ② 是否被無 trailer 的 commit 觸及過
  poisoned=0
  while IFS= read -r line; do
    case "${line}" in *out-of-epic*) ;; *) poisoned=1 ;; esac
  done < <(git log --format='%h %(trailers:key=Governance-Scope,valueonly)' \
             "${BASE}..HEAD" -- "${p}" | tr -d '\n' | sed 's/\([0-9a-f]\{7,\}\)/\n\1/g' | sed '/^$/d')
  [ "${poisoned}" -eq 1 ] || continue
  n=$((n + 1))
  if [ "${paths_only}" -eq 1 ]; then printf '%s\n' "${p}"; else printf '  %s\n' "${p}"; fi
done < <(git log --format='' --name-only "${BASE}..HEAD" | sed '/^$/d' | LC_ALL=C sort -u)

[ "${paths_only}" -eq 1 ] || printf '幽靈路徑 %s 條（改動前須先決定 allow 或接受 G-7 紅）\n' "${n}"
exit 0
