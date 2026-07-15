#!/usr/bin/env bash
# review_quorum_check.sh — 機器強制:中/大實作 batch 須 ≥2 個「非實作者」家族 code review。
#
# 根因(2026-07-15 使用者抓):規則 ORCH §1「code review=Codex+Composer 雙家」早已明寫,
#   但 Claude 憑印象只派單家、連錯三批(B0/B1/B2)未自察。prose/memory 是被動的,擋不住重犯
#   → 依 feedback_rules_are_scar_tissue「prose 再犯→做成閘門」,做成 gate。
#
# 家族來源:**解析 task_id 尾碼**(Claude 控制的命名 `<prefix>-review[N]-<family>`),
#   不信 audit.log 的 family 欄(gate.sh 推導有 bug:不認 grok、預設 composer)。
# **排除實作者家族** → 自動作廢「實作者自審」(不計入 quorum)。
#
# 用法: bash scripts/review_quorum_check.sh <review-task-prefix> <implementer-family>
#   例: bash scripts/review_quorum_check.sh 20260715-la0-b2 grok
# 退出: 0=≥2 個非實作者家族 review 派工留痕; 1=不足/缺 audit。
# 相容 bash 3.2(macOS):不用 mapfile / declare -A。

set -u
AUDIT="${GATE_DIR_OVERRIDE:-.claude/gate}/audit.log"
prefix="${1:-}"
implementer="${2:-}"
[ -n "${prefix}" ] || { echo "REVIEW-QUORUM FAIL: 缺 <review-task-prefix>"; exit 1; }
[ -n "${implementer}" ] || { echo "REVIEW-QUORUM FAIL: 缺 <implementer-family>"; exit 1; }
[ -f "${AUDIT}" ] || { echo "REVIEW-QUORUM FAIL: 無 audit.log (${AUDIT})"; exit 1; }

# 掃 committee_dispatch 的 task_id;取含 <prefix> 且含 "review" 者,擷取尾碼家族,去重、排除實作者。
distinct=""   # 空白分隔的去重家族清單
while IFS= read -r tid; do
  case "${tid}" in
    "${prefix}"*review*) : ;;      # 屬本 batch 的 review 派工
    *) continue ;;
  esac
  fam="${tid##*-}"                  # 尾碼家族
  case "${fam}" in
    codex|composer|grok) : ;;
    *) continue ;;
  esac
  [ "${fam}" = "${implementer}" ] && continue   # 排除實作者自審
  case " ${distinct} " in
    *" ${fam} "*) : ;;             # 已計
    *) distinct="${distinct} ${fam}" ;;
  esac
done <<EOF
$(grep '"event": "committee_dispatch"' "${AUDIT}" 2>/dev/null | grep -oE '"task_id": "[^"]+"' | sed -E 's/"task_id": "//; s/"//')
EOF

distinct="$(printf '%s' "${distinct}" | sed -E 's/^ +//; s/ +$//')"
count=0
for _f in ${distinct}; do count=$((count+1)); done

if [ "${count}" -ge 2 ]; then
  echo "REVIEW-QUORUM PASS: batch ${prefix} 已獲 ${count} 個非實作者家族 review: ${distinct}(implementer=${implementer} 已排除)"
  exit 0
fi
echo "REVIEW-QUORUM FAIL: batch ${prefix} 僅 ${count} 個非實作者家族 review: ${distinct:-無}(需 ≥2;implementer=${implementer} 不計)"
echo "  → 中/大實作須 Codex+Composer 雙家 code review(ORCH §1);補派第二家後再派下一批。"
exit 1
