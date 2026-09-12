#!/usr/bin/env bash
# plain_docs_order_check.sh — 白話文件之「編號條目必須遞增」機械閘。
#
# 出生理由（2026-09-12 使用者反映）：「每個檔案包含白話說明都寫的層層疊疊，
#   然後又穿插在各段中間，我根本不知從何看起。」查證屬實——
#   `白話說明/流程摩擦記錄.md` 的補記實際排列為 6,7/8,9,10/11,12,14,…,25,13，
#   第 13 筆掉在最底下。根因不是大意，是 Edit 必須錨定既有文字，
#   最省事的錨點是「下一段開頭」⇒ 新內容永遠插在舊內容**前面**；
#   連續十二次用同一個錨點，就把它推到最後。
#
# 為何是機械閘而非紀律：三個成因（錨點偏差／加一句比替換便宜／無閘可見）
#   都與自制力無關，`docs/SCAR_LEDGER.md` 之「文字問題用白名單機械卡」適用。
#
# 檢查對象（封閉集合，不做語意判斷）：
#   ① `**補記（同日，第 N 筆…）**`  ② `### 閉合第 N 輪`
# 規則：同一檔案內，同一型樣之編號**必須非遞減**；`N／M` 形式取第一個數。
# 內文交叉引用（未出現在行首之編號）不計。
#
# 🔴 **刻意不含通用 `### 第 N …`**：首版含之，立刻在 `白話說明/G3-D2灰色項目說明.md`
#   誤判——`### 第 0/1/3/4/5 段`（計畫章節）與 `### 第 0 段做了什麼（白話）`（回顧節）
#   共用前綴但語意不同，後者本來就該排在後面。⇒ 只收「編號即順序」語意明確之型樣；
#   寧可漏，不可吵（噪音閘會被無視，等同沒有）。新增型樣前先確認該前綴不會被兩種語意共用。
#
# 用法：bash scripts/plain_docs_order_check.sh [檔案…]（預設掃 白話說明/*.md）
# rc=0 全部遞增；rc=1 有亂序（逐條列出）。

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  while IFS= read -r f; do files+=("$f"); done < <(find 白話說明 -maxdepth 1 -name '*.md' 2>/dev/null)
fi
[ ${#files[@]} -eq 0 ] && { echo "[order_check] 無可檢查檔案"; exit 0; }

rc=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  for pat in '補記（同日，第' '### 閉合第'; do
    prev=0; prev_line=0; bad=0
    while IFS=$'\t' read -r lineno num; do
      if [ "$num" -lt "$prev" ]; then
        [ "$bad" -eq 0 ] && echo "[order_check] 🔴 ${f}（型樣：${pat}）編號非遞增："
        echo "    第 ${lineno} 行的編號 ${num} 小於第 ${prev_line} 行的 ${prev}"
        bad=1; rc=1
      fi
      prev="$num"; prev_line="$lineno"
    done < <(grep -n "^\*\*${pat}\|^${pat}" "$f" 2>/dev/null \
             | sed -E 's/^([0-9]+):.*'"${pat}"' *([0-9]+).*/\1\t\2/' \
             | grep -E '^[0-9]+\t[0-9]+$')
  done
done

if [ "$rc" -eq 0 ]; then
  echo "[order_check] ✓ 編號條目皆遞增（檢查 ${#files[@]} 檔）"
else
  echo "[order_check] 修法：把該條目搬回正確位置；**新增一律加在該節結尾**，"
  echo "             不要用「下一段開頭」當錨點往前插（那正是本閘出生的原因）。"
fi
exit "$rc"
