#!/usr/bin/env bash
# 清掉 reconcile synth.md 的既有 RECONCILE-STAMP 行（body 變更後舊戳記必然失效）
#
# 為何存在：body 一改，舊戳記的 sha 就對不上。留著等於留一份**指向不存在狀態**的
# 假 provenance——2026-07-28 SPEC 那次就是留著舊戳記，後來才發現指向的 SPEC
# 狀態已不存在。清掉並記錄失效原因，比留著誠實。
#
# 用法：bash scripts/reconcile_clear_stamps.sh <synth.md> "<失效原因>"
set -uo pipefail
SYNTH="${1:?用法: $0 <synth.md> \"<失效原因>\"}"
REASON="${2:?須說明為何舊戳記失效}"

[ -f "$SYNTH" ] || { echo "ERROR: 找不到 $SYNTH"; exit 1; }
grep -q '^## 戳記' "$SYNTH" || { echo "ERROR: $SYNTH 無『## 戳記』區段"; exit 1; }

n=$(grep -c '^RECONCILE-STAMP:' "$SYNTH" || true)
[ "$n" -eq 0 ] && { echo "無既有戳記，不需清理"; exit 0; }

tmp=$(mktemp)
grep -v '^RECONCILE-STAMP:' "$SYNTH" > "$tmp"
printf '> ⚠️ **舊戳記 %s 枚已於 %s 清除**：%s\n\n' \
       "$n" "$(date -u +%Y-%m-%d)" "$REASON" >> "$tmp"
mv "$tmp" "$SYNTH"

LOCK="$(dirname "$SYNTH")/sources.lock"
if [ -f "$LOCK" ]; then
  bash scripts/completeness_check.sh --lock "$LOCK" >/dev/null 2>&1
  echo "completeness_check --lock rc=$?"
fi
echo "已清除 $n 枚戳記；新 body sha256 = $(bash scripts/reconcile_body_hash.sh "$SYNTH" 2>/dev/null | tail -1)"
