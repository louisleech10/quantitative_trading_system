#!/usr/bin/env bash
# quant_standard_check.sh — 量化主線「100% 正確」標準之機械閘（QUANT-STD-100，2026-08-22）
#
# 病根（使用者 2026-08-22 逐字）：
#   「95% 解法就收、殘留具名記錄不當阻塞這是在針對治理 epic 中會有散文化和文字問題，
#     **在量化主線完全不接受，數據/品質一定是要 100% 正確，只能更嚴但不能放水**」
#   「絕對不能犯或不小心有任何一條或引用到，要整條刪除都可以」
#
# 事故：2026-08-22 GAP-3 UX SPEC R3 輪，主委因 findings 由 7 反彈至 18，
#   援引治理 epic 之「95% 解法就收」建議收斂並停止加固 —— 被使用者當場駁回。
#   主委隨後於 SPEC 新增 §C0 政策宣告，但**三家 consult 一致判定「政策宣告擋不住同義語」**：
#     · CODEX-R1-P0-05：「§C0 是政策宣告，不足以機械阻止治理式『95% 就收』被日後 brief、
#       TODO、review 或 reconcile 以同義語援引」
#     · GROK-R1-P1-04：「§C0 僅禁特定用詞與『治理慣例』援引，不足以機械擋住等價放水」
#     · COMPOSER-R1-P1-04：「§C0 措辭不足以機械擋住 repo 內其他文件或 review 輪次再援引；
#       主委『量化主線三檔零命中』之判定過窄，與使用者『整條刪除都可以』的強度不符」
#   ⇒ 本腳本即該政策之機械化。**紀律擋不住第 8 次，閘門才能。**
#
# 🔴 誠實邊界（逐條講清楚，不誇大）：
#   1. 本閘掃的是**文字**。它擋「寫下來的放水」，擋不住「心裡放水但不寫」。
#      真正的防線是 §V 逐條驗收與 mutation ——本閘只是早期示警。
#   2. 同義語族是**封閉黑名單**，理論上列不完。但與治理散文不同，本閘的適用範圍很窄
#      （只掃量化主線路徑），且新增同義語只需加一行；發現漏網即補，屬可收斂的維護。
#   3. 不掃 `docs/GOV*`／`handoffs/**/govb*` 等治理路徑 —— 那條規則本來就出生於治理，
#      在治理領域是合法的（使用者原話「這是在針對治理 epic」）。
#   4. 統計用語之 `95%`（binomial 95% 允收帶、Fisher z 95% CI）**不是**放水語，
#      已於 _STAT_CONTEXT 白名單排除；誤擋會使腳本失去信任而被繞過。
#
# 用法：
#   bash scripts/quant_standard_check.sh                # 掃預設量化路徑
#   bash scripts/quant_standard_check.sh <file> [...]   # 掃指定檔
# rc: 0=無命中；2=命中（訊息在 stderr）
set -u

SCRIPT_DIR="$(cd "$(dirname "${0}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}" || exit 0

# ── 適用範圍：量化主線 ────────────────────────────────────────────────
# 治理路徑刻意排除（見邊界 3）。以**前綴**列舉，新增量化 epic 時加一行。
_QUANT_GLOBS=(
  "docs/GAP1_*.md" "docs/GAP2_*.md" "docs/GAP3_*.md"
  "docs/IC_*.md" "docs/TEST_DESIGN_CHARTER.md" "docs/ML_APPROACH_TAXONOMY.md"
)
# 🔴 **刻意不掃 `handoffs/`**（首版掃了，160 命中中大量來自歷史 handoff）：
#    handoffs 是**歷史紀錄**，記載當時說過什麼；追溯性地把歷史文件判違規既無意義
#    （改不了過去），又會使誤報淹沒真命中。本閘只管**現行有效之規格文件**——
#    那才是 Agent 實作時會讀、會照做的東西。
#    誠實邊界：若日後有人在**新的** brief 裡寫放水語，本閘抓不到 ⇒ 由 §C0 之
#    人工審查與委員 review 承接；這是已知缺口，不宣稱已封。

# ── 放水同義語族（封閉黑名單；發現漏網即加一行）─────────────────────
# 🔴 每一條都須是「主張降低標準」之語，不得放入單純描述性字串。
_LEAK_PATTERNS=(
  '9[05]%[[:space:]]*(解法)?[[:space:]]*就收'
  '9[05][[:space:]]*%?[[:space:]]*(就|即)(可|能)?收(案|斂)?'
  '殘留具名記錄不當阻塞'
  '夠好了?[[:space:]]*(就)?收'
  '先收(再說|起來)'
  '差不多(就)?(可以)?收'
  '不必(追求|做到)[[:space:]]*100'
  '不用(追求|做到)[[:space:]]*100'
  '(可以)?接受的殘留'
  '容許[[:space:]]*(少量|部分)[[:space:]]*(誤差|不正確|錯誤)'
  '(以|用)[[:space:]]*殘留[[:space:]]*(記錄|登記)[[:space:]]*(帶過|放行)'
  '降級[[:space:]]*(為|成)[[:space:]]*(具名)?殘留[[:space:]]*(而|並)?[[:space:]]*放行'
  '一輪定版'
  '不再加(新)?機制'
  '(避免|防)[[:space:]]*無限迴圈[[:space:]]*(而|故|所以)[[:space:]]*(收斂|定版|停)'
)

# ── 統計語境白名單（防誤擋；見邊界 4）───────────────────────────────
_STAT_CONTEXT='binomial|允收帶|信賴區間|CI\)|Fisher|z[[:space:]]*\+|置信|confidence|percentile|分位'

# ── 否定語境白名單（**首版自測 160 命中、絕大多數為此類**）─────────────
# 🔴 首版把 §C0「**禁止**使用這句話」的條文本身標成違規（`SPEC:183/194` 等）。
#    誤報率過高的閘會被忽略或繞過 —— **比沒有更糟**。故加否定語境偵測。
#    判準：同一行若出現「禁止／不得／不適用／駁回／違規／援引錯誤」等**反對該語**之詞，
#    則該行是在**禁止**放水而非**主張**放水 ⇒ 豁免。
_NEGATION_CONTEXT='不適用|不得|禁(止|用)|一律不|不接受|駁回|違規|錯誤|不受理|未動用|不動用|全採較嚴|反制|防止|擋住|拒絕|撤回'

_files=()
if [ "$#" -gt 0 ]; then
  _files=("$@")
else
  for g in "${_QUANT_GLOBS[@]}"; do
    while IFS= read -r f; do
      [ -f "${f}" ] && _files+=("${f}")
    done < <(compgen -G "${g}" 2>/dev/null || true)
  done
fi

[ "${#_files[@]}" -gt 0 ] || exit 0

_hits=0
_report=""
for f in "${_files[@]}"; do
  # 治理路徑一律跳過（邊界 3）
  case "${f}" in
    docs/GOV*|docs/P16_*|scripts/*|*govb*|*GOVB*) continue ;;
  esac
  for pat in "${_LEAK_PATTERNS[@]}"; do
    while IFS= read -r line; do
      [ -n "${line}" ] || continue
      # 統計語境豁免
      if printf '%s' "${line}" | grep -Eq "${_STAT_CONTEXT}"; then continue; fi
      # 否定語境豁免（該行是在禁止放水，不是主張放水）
      if printf '%s' "${line}" | grep -Eq "${_NEGATION_CONTEXT}"; then continue; fi
      # 引用語境豁免：markdown 引用行（`> `）＝逐字引述使用者原話或委員 finding，
      # 屬**紀錄**而非**主張**。§C0 須逐字引用使用者定死之原話才有效力，不得因此被自己的閘擋住。
      if printf '%s' "${line}" | grep -Eq '^[0-9]+:[[:space:]]*>'; then continue; fi
      _hits=$((_hits + 1))
      _report="${_report}  · ${f}:${line}
"
    done < <(grep -nE "${pat}" "${f}" 2>/dev/null | head -5)
  done
done

if [ "${_hits}" -eq 0 ]; then
  exit 0
fi

{
  echo "[quant_standard_check] 🔴 量化主線偵測到「放水語」共 ${_hits} 處"
  printf '%s' "${_report}"
  echo
  echo "  使用者 2026-08-22 定死：量化主線 **100% 正確，只能更嚴不能放水**；"
  echo "  「95% 解法就收」只適用治理 epic 之散文問題，量化路徑一律不受理。"
  echo "  修：刪除該表述，或改寫為具體的、可證偽的驗收條件。"
  echo "  若確為誤擋（例如統計用語），請在 _STAT_CONTEXT 增白名單並於 commit 說明理由。"
} >&2
exit 2
