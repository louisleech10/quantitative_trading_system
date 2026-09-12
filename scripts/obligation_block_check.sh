#!/usr/bin/env bash
# obligation_block_check.sh — 義務區塊「只准出現這幾種行」之白名單結構閘。
#
# 出生理由（2026-09-12 使用者當面否決前一版設計）：
#   我原本提議「規格檔內禁止出現『某輪更正』『原寫…已改』等字樣」。使用者指出那是**黑名單**，
#   「禁止不完，會無限發散跟繞過」，且「層層疊疊也是一直疊加」。該判斷與本專案既有傷疤一致
#   （`docs/SCAR_LEDGER.md`：黑名單永遠列不完，`_g2_regions` 一機制衍生四條旁路）。提議撤回。
#
# 本閘改採白名單，且**完全不看字詞**：
#   界標之內只允許兩種行型 ⇒ 「在舊句旁邊補一句更正」在結構上無處可放，換句話說也繞不過。
#
# 界標（機器可讀，HTML 註解不影響渲染）：
#   <!-- OBLIGATIONS-BEGIN id=<識別碼> max=<項數上限> -->
#   **(4.1) …**
#   **(4.2) …**
#   <!-- OBLIGATIONS-END -->
#
# 規則（封閉、可導出，不含任何關鍵字表）：
#   R1 區塊內每一非空行必須是 `**(<主>.<次>) …**` 形式之編號義務項；自由散文即違規。
#   R2 次編號必須自 1 起、**連續且遞增**（不得跳號、不得重號）——跳號代表有東西被刪而沒重排。
#   R3 項數不得超過界標宣告之 max——要加第 max+1 項，得先明確決定調高上限或改既有項。
#   R4 主編號區塊內須一致（同一區塊不得混用 4.x 與 5.x）。
#
# 🔴 **誠實邊界**：本閘擋的是「結構上的疊加」。兩個編號項**語意互斥**它抓不到，
#   那仍然只有委員通讀才行（R7～R12 六輪的擋項多屬此類）。不得宣稱本閘解決全部。
#
# 用法：bash scripts/obligation_block_check.sh [檔案…]（預設掃 docs/*.md）
# rc=0 無違規或無界標；rc=1 有違規（逐條列出行號）。

set -uo pipefail
cd "$(dirname "$0")/.." || exit 2

files=("$@")
if [ ${#files[@]} -eq 0 ]; then
  while IFS= read -r f; do files+=("$f"); done < <(find docs -maxdepth 1 -name '*.md' 2>/dev/null)
fi
[ ${#files[@]} -eq 0 ] && { echo "[obligation_block] 無可檢查檔案"; exit 0; }

rc=0; blocks=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  in_block=0; bid=""; bmax=0; expect=0; major=""; start_line=0
  lineno=0
  while IFS= read -r line; do
    lineno=$((lineno + 1))
    case "$line" in
      *OBLIGATIONS-BEGIN*)
        in_block=1; expect=1; major=""; start_line=$lineno; blocks=$((blocks + 1))
        bid=$(printf '%s' "$line" | sed -nE 's/.*id=([A-Za-z0-9_.-]+).*/\1/p')
        bmax=$(printf '%s' "$line" | sed -nE 's/.*max=([0-9]+).*/\1/p')
        [ -z "$bmax" ] && { echo "[obligation_block] 🔴 ${f}:${lineno} 界標缺 max=<上限>"; rc=1; bmax=0; }
        continue ;;
      *OBLIGATIONS-END*)
        if [ "$in_block" -eq 1 ]; then
          n=$((expect - 1))
          if [ "$bmax" -gt 0 ] && [ "$n" -gt "$bmax" ]; then
            echo "[obligation_block] 🔴 ${f} 區塊 ${bid}（起 ${start_line} 行）項數 ${n} 超過宣告上限 ${bmax}"
            echo "    要加第 $((bmax + 1)) 項，請先明確決定調高上限，或改寫既有項（疊加不是預設）。"
            rc=1
          fi
        fi
        in_block=0; continue ;;
    esac
    [ "$in_block" -eq 1 ] || continue
    [ -z "${line//[[:space:]]/}" ] && continue
    if ! printf '%s' "$line" | grep -qE '^[[:space:]]*\*\*\([0-9]+\.[0-9]+\)[[:space:]]'; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 區塊 ${bid} 內出現非義務項之行（自由散文不是合法行型）"
      echo "    → $(printf '%s' "$line" | cut -c1-72)"
      echo "    修法：把它寫成編號義務項，或改寫既有項；沿革請放收斂檔，不要放在規格裡。"
      rc=1; continue
    fi
    cur_major=$(printf '%s' "$line" | sed -nE 's/^[[:space:]]*\*\*\(([0-9]+)\.[0-9]+\).*/\1/p')
    cur_minor=$(printf '%s' "$line" | sed -nE 's/^[[:space:]]*\*\*\([0-9]+\.([0-9]+)\).*/\1/p')
    [ -z "$major" ] && major="$cur_major"
    if [ "$cur_major" != "$major" ]; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 區塊 ${bid} 混用主編號 ${major} 與 ${cur_major}"; rc=1
    fi
    if [ "$cur_minor" -ne "$expect" ]; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 區塊 ${bid} 編號應為 ${expect} 但寫成 ${cur_minor}（須自 1 起連續遞增）"
      echo "    跳號通常代表刪了某項卻沒重排；重號代表插入時沒看前後。"
      rc=1; expect="$cur_minor"
    fi
    expect=$((expect + 1))
  done < "$f"
  if [ "$in_block" -eq 1 ]; then
    echo "[obligation_block] 🔴 ${f} 界標 ${bid}（起 ${start_line} 行）沒有對應的 OBLIGATIONS-END"; rc=1
  fi
done

if [ "$rc" -eq 0 ]; then
  echo "[obligation_block] ✓ ${blocks} 個義務區塊之行型、編號與項數上限皆合規（檢查 ${#files[@]} 檔）"
fi
exit "$rc"
