#!/usr/bin/env bash
# 在 reconcile synth.md 尾端加上「## 戳記」區段——**正確地**加。
#
# 為何存在（2026-07-28／29 連犯兩次）：
#   手打 `printf '\n---\n## 戳記\n' >> synth.md` 會多出一個 `---`，
#   被 completeness_check 併進**最後一條 finding 的 body** → body-hash 不符 → rc=1。
#   第一次（p16-v26close-r7）害整個戳記輪在紅燈下跑完，兩家沒查前置就簽了 APPROVED。
#   第二次（p16-todov11-r2）當場又犯。故做成工具，不再手打。
#
# 關鍵：附錄最後一條 finding 的 body 已自帶結尾的 `---`＋空行，
#       故本腳本**只補一個空行 + 標題**，不再另加分隔線。
#
# 用法：bash scripts/reconcile_add_stamp_section.sh <synth.md> [標的說明]
set -uo pipefail
SYNTH="${1:?用法: $0 <synth.md> [標的說明]}"
TARGET_DESC="${2:-}"

[ -f "$SYNTH" ] || { echo "ERROR: 找不到 $SYNTH"; exit 1; }

if grep -q '^## 戳記' "$SYNTH"; then
  echo "ERROR: $SYNTH 已有『## 戳記』區段，拒絕重複附加"
  exit 1
fi

# 前置：加之前必須是乾淨的（否則是把既有問題帶進戳記輪）
LOCK="$(dirname "$SYNTH")/sources.lock"
if [ -f "$LOCK" ]; then
  bash scripts/completeness_check.sh --lock "$LOCK" >/dev/null 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: 附加前 completeness_check --lock 就是 rc=$rc，先修好再加戳記區"
    exit 1
  fi
fi

{
  printf '\n## 戳記\n\n'
  printf '> 三家 RECONCILE-STAMP；body sha256 = 「## 戳記」前全部內容。\n'
  [ -n "$TARGET_DESC" ] && printf '> 標的 = %s\n' "$TARGET_DESC"
  printf '\n'
} >> "$SYNTH"

# 後置：加完必須仍然乾淨——這正是手打會失敗的地方
if [ -f "$LOCK" ]; then
  bash scripts/completeness_check.sh --lock "$LOCK" >/dev/null 2>&1
  rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "ERROR: 附加後 completeness_check 轉紅 (rc=$rc) — 戳記區破壞了最後一條 finding 的 body"
    exit 1
  fi
  echo "completeness_check --lock rc=0（附加前後皆綠）"
fi

echo "body sha256 = $(bash scripts/reconcile_body_hash.sh "$SYNTH" 2>/dev/null | tail -1)"
echo "OK: 已附加『## 戳記』區段 → $SYNTH"
