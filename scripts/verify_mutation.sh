#!/usr/bin/env bash
# verify_mutation.sh — 一鍵驗證「守衛測試是真 oracle」:改壞→須轉紅→**保證還原**→須轉綠。
#
# 為何存在(2026-07-25):我這 session 手做了 5+ 次「python 改檔 → pytest → git checkout 還原」,
#   步驟散、且**還原漏做就髒工作區**(Grok 同輪就踩過 git checkout 意外)。
#   本腳本用 trap 保證無論中途成功/失敗/被中斷都還原。
#
# 🔴 2026-08-25 使用者授權根治「併發不安全」:改檔已移入 **git worktree 隔離副本**
#   (`scripts/mutation_worktree.py`),**主 repo 一個位元組都不動** ⇒ 三家委員可**平行**跑,
#   不必排隊。舊版就地改真實檔,併發時互相破壞 baseline,症狀=「部分條目 pre_rc != 0
#   未執行 ⇒ 整份 NOT-CLOSED」,已實際出現兩次(GAP-3 B1 R5、survivor R2)。
#   CLI 與 stdout 判詞字串**逐字不變**(委員報告會引用)。
#
# 用法:
#   bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>
# 例:
#   bash scripts/verify_mutation.sh scripts/verify_task_provenance.py \
#     'return (' 'return (0,) if False else (' tests/governance/test_stamp_no_task_rejected.py
#
# 通過條件(兩者都要,缺一即 rc≠0):①變異後測試**轉紅** ②還原後測試**轉綠**
#   ——只紅不綠=測試本身壞;只綠不紅=測試假綠(抓不到該抓的)。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

file="${1:-}"; old="${2:-}"; new="${3:-}"; target="${4:-}"
[ -n "${file}" ] && [ -n "${old}" ] && [ -n "${new}" ] && [ -n "${target}" ] || {
  echo "用法: bash scripts/verify_mutation.sh <檔> <原字串> <變異字串> <pytest目標>" >&2; exit 2; }
[ -f "${file}" ] || { echo "ERROR: 檔不存在: ${file}" >&2; exit 2; }

py="venv/bin/python"; [ -x "${py}" ] || py="$(command -v python3 || command -v python)"
[ -n "${py}" ] || { echo "ERROR: 找不到 python" >&2; exit 2; }

[ -f "scripts/mutation_worktree.py" ] || {
  echo "ERROR: 缺 scripts/mutation_worktree.py(隔離執行環境)" >&2; exit 2; }

# 改檔與 pytest 全在隔離副本內完成;主 repo 不被觸碰,故無須 trap 還原。
exec "${py}" scripts/mutation_worktree.py verify "${file}" "${old}" "${new}" "${target}"
