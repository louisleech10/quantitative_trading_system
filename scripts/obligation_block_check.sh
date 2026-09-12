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
#   <!-- OBLIGATIONS-BEGIN id=<識別碼> -->
#   **(4.1) …**
#   **(4.2) …**
#   <!-- OBLIGATIONS-END -->
#
# 規則（封閉、可導出，不含任何關鍵字表）：
#   R1 區塊內每一非空行必須是 `**(<主>.<次>) …**` 形式之編號義務項；自由散文即違規。
#   R2 次編號必須自 1 起、**連續且遞增**（不得跳號、不得重號）——跳號代表有東西被刪而沒重排。
#   R3 🔴 **區塊內不得出現裁決編號**（`<家族>-R<輪>-P<嚴重度>-<序號>`，即本專案 finding ID 文法）。
#      理由（2026-09-12 使用者第二次否決）：編號結構本身擋不住疊加，只是把它從「段落之間」
#      搬到「項目裡面」——例如某項寫成「…（R10 某條與主委自產條）」或「R12 更正：原句為…」。
#      委員讀到那些字就會去處理**前一輪**的問題，造成錯亂。⇒ 義務項只能陳述**系統現在該怎樣**，
#      不得陳述**本文件自己的歷史**；而「引用了裁決編號」正是後者的機器可判形式。
#      這不是散文黑名單：被禁的是本專案已定義之**識別碼文法**，換句話說繞不過，也無須列舉詞彙。
#      沿革不會消失，它住在各輪收斂檔，並且就是以這些編號為索引。
#   R4 主編號區塊內須一致（同一區塊不得混用 4.x 與 5.x）。
#
# 🔴 **刻意不設項數上限**（同日使用者否決前一版）：委員一次舉出十餘條真缺陷是正常的，
#   上限會擋住正當成長。「義務很多」與「層層疊加」是兩件事，本閘只管後者。
#
# R5 **歷史專區**（2026-09-12 使用者定）：「如果要寫歷史或日誌，那就要有一個專區專放，
#   不要穿插在項目中間，項目中都只能有最新版本。」⇒ 於**含義務區塊之檔案**內，
#   任何帶裁決編號之行**只准**出現在歷史專區界標之內：
#     <!-- HISTORY-BEGIN -->  …沿革、取代索引、輪次裁決…  <!-- HISTORY-END -->
#   專區外出現編號即違規。R3 管的是義務區塊內，R5 把同一條紀律推到**整份文件**：
#   歷史有地方放（不是刪掉），但只有那一個地方。
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
  in_hist=0
  has_ob=$(grep -c 'OBLIGATIONS-BEGIN' "$f" 2>/dev/null || true)
  [ -z "$has_ob" ] && has_ob=0
  lineno=0
  while IFS= read -r line; do
    lineno=$((lineno + 1))
    case "$line" in
      *OBLIGATIONS-BEGIN*)
        in_block=1; expect=1; major=""; start_line=$lineno; blocks=$((blocks + 1))
        bid=$(printf '%s' "$line" | sed -nE 's/.*id=([A-Za-z0-9_.-]+).*/\1/p')
        continue ;;
      *OBLIGATIONS-END*)
        in_block=0; continue ;;
      *HISTORY-BEGIN*) in_hist=1; continue ;;
      *HISTORY-END*)   in_hist=0; continue ;;
    esac
    # R5：含義務區塊之檔案，帶裁決編號之行只准出現在歷史專區內
    if [ "$has_ob" -gt 0 ] && [ "$in_hist" -eq 0 ] && [ "$in_block" -eq 0 ] \
       && printf '%s' "$line" | grep -qE '[A-Z]{3,}-R[0-9]+-P[0-3]-[0-9]{2,}'; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 裁決編號出現在歷史專區之外"
      echo "    → $(printf '%s' "$line" | grep -oE '[A-Z]{3,}-R[0-9]+-P[0-3]-[0-9]{2,}' | tr '\n' ' ')"
      echo "    修法：歷史與日誌只能放在專區 <!-- HISTORY-BEGIN --> … <!-- HISTORY-END --> 之內；"
      echo "          項目與正文只留最新版本，不得穿插沿革。"
      rc=1
    fi
    [ "$in_block" -eq 1 ] || continue
    [ -z "${line//[[:space:]]/}" ] && continue
    if ! printf '%s' "$line" | grep -qE '^[[:space:]]*\*\*\([0-9]+\.[0-9]+\)[[:space:]]'; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 區塊 ${bid} 內出現非義務項之行（自由散文不是合法行型）"
      echo "    → $(printf '%s' "$line" | cut -c1-72)"
      echo "    修法：把它寫成編號義務項，或改寫既有項；沿革請放收斂檔，不要放在規格裡。"
      rc=1; continue
    fi
    if printf '%s' "$line" | grep -qE '[A-Z]{3,}-R[0-9]+-P[0-3]-[0-9]{2,}'; then
      echo "[obligation_block] 🔴 ${f}:${lineno} 區塊 ${bid} 內出現裁決編號（義務項不得陳述本文件之歷史）"
      echo "    → $(printf '%s' "$line" | grep -oE '[A-Z]{3,}-R[0-9]+-P[0-3]-[0-9]{2,}' | tr '\n' ' ')"
      echo "    修法：把該項改寫成「系統現在該怎樣」的單一陳述；沿革以該編號為索引留在收斂檔。"
      echo "    理由：編號結構擋不住疊加，只是把它搬進項目裡；讀者會因此去處理前一輪的問題。"
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
  echo "[obligation_block] ✓ ${blocks} 個義務區塊之行型、編號連續性與「不得引用裁決編號」皆合規（檢查 ${#files[@]} 檔）"
fi
exit "$rc"
