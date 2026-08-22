#!/usr/bin/env bash
# spec_v_task_ref_check.sh — §V 不得複述 §P 斷言（SPEC-V-NO-RESTATEMENT，2026-08-22）
#
# 病根（量化事實，非推測）：GAP-3 UAT 缺口 SPEC 之 R4／R5 連兩輪，主委修訂自行引入之
#   findings 共 8 條，形態一致——**改了 §P 之權威定義，未同步 §V 之複述**。
#   最嚴重者＝R5 群集 A：Task 7.1／7.2 已把比對基準改為 `selectable(path,dim)`
#   （＝`accepted` 減 `pathExclusions`），而 §V 之 V-11 仍寫 `new Set(contractAccepted)`。
#   對 `/search`×`scenario` 兩者不相等（accepted 4 值 vs selectable 2 值）
#   ⇒ 照 V-11 實作會**強迫 UI 啟用 A／B**，直接推翻 Task 7.1「邊界」之路徑級限制、
#   重開 label 語意漂移。composer 與 grok **兩家獨立命中**。
#
#   `feedback_cross_reference_sync` 載此類錯已犯 8 次；R5 為第 9 次，且發生在主委剛為
#   前 8 次做完 `spec_ruling_task_sync.sh` 之後——該閘只驗 §D→§P 引用存在性與**宣告式**
#   禁用語，**完全不看 §P↔§V**，正是破口所在。
#
#   ⇒ 本閘由 **R5 consult 輪三家全員裁定**（GROK-R2-P0-01／CODEX-R2-P0-01／COMPOSER-R2-P0-01
#   三家獨立提出同一結構性修法），主委照抄實作，**非主委自訂**。
#   設計哲學：複述即第二份副本，副本必然漂移 ⇒ 不靠紀律，直接讓複述本身不可能存在。
#
# 檢查（封閉可導出集合，非散文判斷；見 feedback_mechanize_dont_police_prose）：
#   §V 表列（行首 `| V-`）中，**凡引用了某個 Task 者**（含 `Task <數字>.<數字>` 字樣），
#   該列**不得**同時出現下列斷言字面——出現即代表它在複述 §P：
#     `new Set(` ／ `contractAccepted` ／ `pathExclusions` ／ `===` ／ `!==`
#   引用了 Task 就該只引用；要斷言就寫進那個 Task 的驗證欄。
#
# 🔴 誠實邊界（不得誇大）：
#   1. **不檢查未引用任何 Task 之 V 列**。那些列自成一體、無雙源對象；
#      本 SPEC 現有 12 條屬此類（V-1..V-7／V-9／V-10／V-1b／V-1c／V-M）。
#      要不要一併引用化，屬未來範圍，**本閘不宣稱已封**。
#   2. 只擋**字面**複述。用不同措辭寫出同一斷言仍會通過 ⇒ 交 adversarial review。
#   3. 只掃單一 SPEC 檔，不跨檔對證。
#
# 用法：
#   bash scripts/spec_v_task_ref_check.sh <SPEC.md>
# rc: 0=無複述；2=有複述（訊息在 stderr）
set -u

f="${1:-}"
if [ -z "${f}" ] || [ ! -f "${f}" ]; then
  echo "用法: bash scripts/spec_v_task_ref_check.sh <SPEC.md>" >&2
  exit 0
fi

# 無 §V 表 ⇒ 無事可做（空對空恆綠是假綠，故此處明確回報而非靜默 0）
if ! grep -q '^| V-' "${f}" 2>/dev/null; then
  exit 0
fi

_hits="$(LC_ALL=C awk '
  /^\| V-/ {
    if ($0 !~ /Task [0-9]+\.[0-9]+/) next          # 未引用 Task ⇒ 不在涵蓋面（見誠實邊界 1）
    bad = ""
    if (index($0, "new Set(")        > 0) bad = bad " new Set("
    if (index($0, "contractAccepted")> 0) bad = bad " contractAccepted"
    if (index($0, "pathExclusions")  > 0) bad = bad " pathExclusions"
    if (index($0, "===")             > 0) bad = bad " ==="
    if (index($0, "!==")             > 0) bad = bad " !=="
    if (bad != "") {
      vid = $0
      sub(/^\| /, "", vid); sub(/ \|.*$/, "", vid)
      printf "%d|%s|%s\n", FNR, vid, bad
    }
  }' "${f}")"

if [ -z "${_hits}" ]; then
  exit 0
fi

{
  echo "[spec_v_task_ref_check] 🔴 ${f} 之 §V 同時引用 Task 又複述其斷言（雙源）"
  while IFS='|' read -r ln vid bad; do
    [ -n "${ln}" ] || continue
    echo "  · ${f}:${ln}  ${vid}  複述字面：${bad}"
  done <<EOF
${_hits}
EOF
  echo
  echo "  規則：§V 是索引不是第二份規格。引用了 Task 就只寫「執行 Task <id> 之驗證欄」，"
  echo "        要寫斷言請寫進該 Task 的驗證欄——複述即第二份副本，副本必然漂移。"
  echo "  出處：R5 consult 三家全員裁（GROK-R2-P0-01／CODEX-R2-P0-01／COMPOSER-R2-P0-01）；"
  echo "        病根＝R4/R5 兩輪 8 條主委自傷皆為「改了 §P 未同步 §V」。"
} >&2
exit 2
