#!/usr/bin/env bash
# gap3ux_count_check.sh — GAP-3 UX 計數稽核之**唯一呼叫點**（2026-08-23）
#
# 病根：`spec_count_audit.py --check` 之「掃哪些檔」原本在**兩處**各寫一份——
#   `scripts/gap3ux_pre_review.sh` 與 `scripts/narrow_check_router.sh`。
#   R8 修前者時漏了後者 ⇒ 「加閘／換檔未同步清單」**第四次**（R6 三→四、R7 四→五、
#   R8 r7→r8、R8 pre_review vs router）。
#
# 🔴 教訓（摩擦一百零一之延伸）：把三處字面收斂成「唯一入口」還不夠——
#   **只要那個入口裡仍有寫死的字面，或呼叫散在兩處，漂移就會回來**。
#   ⇒ 本檔把「掃描面」與「呼叫方式」一起收成**單一來源**；
#     `pre_review` 與 `narrow_check_router` 皆只呼叫本檔，不得自帶參數清單。
#
# 掃描面＝SPEC ＋ 所有 `handoffs/*gap3ux*-facts.sh`（glob，不寫死輪次；新增輪次自動納入）。
#
# 用法：bash scripts/gap3ux_count_check.sh
# rc: 直接透傳 spec_count_audit.py（0=無變動；2=有計數字面變動）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

SPEC=docs/GAP3_EVENT_UX_SPEC.md
BASE=handoffs/run_receipts/gap3ux-spec-count-baseline.txt
FACTS_GLOB='handoffs/*gap3ux*-facts.sh'

# shellcheck disable=SC2086
FACTS=$(ls -1 ${FACTS_GLOB} 2>/dev/null | tr '\n' ' ')
[ -n "${FACTS}" ] || { echo "ERROR: 找不到任何 ${FACTS_GLOB}（fail-closed）" >&2; exit 2; }
[ -f "${BASE}" ]  || { echo "ERROR: 基準檔不存在 ${BASE}（fail-closed）" >&2; exit 2; }

# shellcheck disable=SC2086
python3 scripts/spec_count_audit.py --check "${SPEC}" ${FACTS} --baseline "${BASE}"
exit $?
