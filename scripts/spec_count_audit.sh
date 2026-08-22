#!/usr/bin/env bash
# spec_count_audit.sh — SPEC 驗收欄之「計數字面」稽核（SPEC-COUNT-DRIFT，2026-08-23）
#
# 病根（量化事實）：GAP-3 UAT 缺口 SPEC 之 R6 十五條中，**6 條為主委整合時自傷**，
#   其中 3 條形態完全相同——**SPEC 寫死了一個計數，而它所計之物後來變了**：
#     · R6 群集 A：`pathExclusions` 由 1 筆擴為 3 筆，驗收欄仍寫「該常數之筆數 `=== 1`」
#       （COMPOSER-R6-P1-01／GROK-R6-P0-01 兩家獨立命中）
#     · R6 群集 B：批次維度六改五，Task 7.6 驗收仍寫「detail 回應含**六個鍵**」
#       （CODEX／COMPOSER／GROK 三家全員命中）
#     · R6 群集 F：機械閘由三支增為四支，receipt 產生器仍寫「三支機械閘」
#       （COMPOSER-R6-P2-01）
#   三條皆非判斷錯誤，是**字面沒跟著動**。使用者 2026-08-23 裁定：主委直接修 ＋ 做成機械閘。
#
# 設計（feedback_mechanize_dont_police_prose：封閉集合，不做語意判斷）：
#   只掃**驗收語境**（`- 驗證：` bullet 及其 ①②③… 續行）中的**計數字面**，
#   量詞限縮為指涉「SPEC 內可列舉之物」者：`個鍵`／`支閘`／`個維度`／`維度`／`筆`／`個值`。
#   🔴 **刻意排除** `家`（委員家數，屬敘事非斷言）與所有非驗收語境之散文計數。
#   首版曾用寬集合（含 `個/條/項/組/家/層`＋全文掃描），實掃 **408 命中、絕大多數為誤報**
#   且 `LC_ALL=C` 咬壞中文 ⇒ 依摩擦九十二（新增關鍵字型機檢上線前必須實掃並報誤報數）收窄。
#
# 兩種模式：
#   --list  <SPEC.md>           列出驗收欄之計數字面（Task／章節 ＋ 字面），rc 恆 0
#   --check <SPEC.md> <基準檔>  與基準檔比對；有新增／改變／消失即 rc=2
#
# 🔴 誠實邊界（不得誇大）：
#   1. **本閘不知道正確數字**，只保證「計數字面一旦變動，作者必須重新看過它所計之物」。
#      作者複核後仍寫錯，本閘擋不住 ⇒ 交 adversarial review。
#   2. 只掃驗收語境；正文散文裡的計數不在涵蓋面（那些不會被 Agent 當斷言執行）。
#   3. **正解仍是「不要寫計數字面」**——改用集合相等斷言（R6 群集 A／B 即如此修）。
#      本閘是給「真的必須寫數字」處的最後一道網，不是鼓勵寫計數。
set -u

mode="${1:-}"
f="${2:-}"
base="${3:-}"

usage() {
  echo "用法:" >&2
  echo "  bash scripts/spec_count_audit.sh --list  <SPEC.md>" >&2
  echo "  bash scripts/spec_count_audit.sh --check <SPEC.md> <基準檔>" >&2
}

case "${mode}" in
  --list|--check) : ;;
  *) usage; exit 0 ;;
esac
[ -n "${f}" ] && [ -f "${f}" ] || { usage; exit 0; }

# 驗收語境 ＝ `- 驗證：` 起始之 bullet，直到下一個 `- <欄名>：` 或空行為止。
# 量詞為封閉集合；`家` 刻意不在內（委員家數屬敘事）。
_extract() {
  awk '
    /^- 驗證/            { inv = 1 }
    /^- (內容|存活至|覆蓋風險|邊界|不可做)/ { inv = 0 }
    /^\*\*Task [0-9]+\.[0-9]+[a-z]?/ { ctx = $0; sub(/^\*\*/, "", ctx); sub(/ —.*$/, "", ctx); inv = 0 }
    /^\*\*S-[0-9]+[a-z]?/            { ctx = $0; sub(/^\*\*/, "", ctx); sub(/[（ ].*$/, "", ctx) }
    /S-9 之驗收/                     { inv = 1 }
    inv {
      line = $0
      gsub(/任一/, "", line)      # 「任一維度」之「一」非計數（首版誤配 5 處）
      gsub(/每一/, "", line)
      while (match(line, /[一二三四五六七八九十兩0-9]+(個鍵|支閘|支機械閘|個維度|維度|筆|個值)/)) {
        printf "%s\t%s\n", ctx, substr(line, RSTART, RLENGTH)
        line = substr(line, RSTART + RLENGTH)
      }
      while (match(line, /(筆數|長度|個數|數量)[^0-9]*[=＝]+ *[0-9]+/)) {
        printf "%s\t%s\n", ctx, substr(line, RSTART, RLENGTH)
        line = substr(line, RSTART + RLENGTH)
      }
    }' "$1" | sort -u
}

if [ "${mode}" = "--list" ]; then
  _extract "${f}"
  exit 0
fi

[ -n "${base}" ] && [ -f "${base}" ] || {
  echo "ERROR: --check 需要基準檔（先跑 --list 產生並人工複核過）" >&2; exit 2; }

_cur="${TMPDIR:-/tmp}/.sca_cur.$$"
_extract "${f}" > "${_cur}"
_added="$(comm -23 "${_cur}" "${base}" 2>/dev/null)"
_removed="$(comm -13 "${_cur}" "${base}" 2>/dev/null)"
rm -f "${_cur}"

[ -z "${_added}" ] && [ -z "${_removed}" ] && exit 0

{
  echo "[spec_count_audit] 🔴 ${f} 之驗收欄計數字面有變動 ⇒ 請逐條複核它所計之物的實際數"
  [ -n "${_added}" ]   && { echo "  ── 新增／改變 ──"; printf '%s\n' "${_added}"   | sed 's/^/    + /'; }
  [ -n "${_removed}" ] && { echo "  ── 消失（確認是刻意移除，非誤刪斷言）──"; printf '%s\n' "${_removed}" | sed 's/^/    - /'; }
  echo
  echo "  病根：R6 十五條中 3 條為「計數字面沒跟著它所計之物一起改」"
  echo "        （pathExclusions 1→3 筆／維度 6→5 個／機械閘 3→4 支）。"
  echo "  正解：能改成集合相等斷言的就別寫計數字面；真要寫數字，複核後更新基準："
  echo "        bash scripts/spec_count_audit.sh --list ${f} > ${base}"
} >&2
exit 2
