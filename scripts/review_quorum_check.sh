#!/usr/bin/env bash
# review_quorum_check.sh — 機器強制:中/大實作 batch 須 ≥2 個「非實作者」家族 code review。
#
# 根因(2026-07-15 使用者抓):規則 ORCH §1「code review=Codex+Composer 雙家」早已明寫,
#   但 Claude 憑印象只派單家、連錯三批(B0/B1/B2)未自察。prose/memory 是被動的,擋不住重犯
#   → 依 feedback_rules_are_scar_tissue「prose 再犯→做成閘門」,做成 gate。
#
# 家族來源（兩層聯集；VERDICTGATE B2 依 CODEX-R1-P1-01／GROK-R1-P1-01 擴充）:
#   ① 解析 committee_dispatch 之 task_id 尾碼(Claude 控制的命名 `<prefix>-review[N]-<family>`)；
#   ② committee_output 之 family 欄（B1 起由 gate.sh 依檔名尾碼＋roster 對證寫入；legacy 列
#      family=unknown 者以 output_path 尾碼 `-<family>.md` 推得）——committee_run 派出的輪 task_id
#      形如 `<ROOT>-B1-REVIEW-R1`（無家族尾碼、大寫），只靠①恆計 0；B2 前 gate.sh 之舊回溯 grep 命不中
#      時整段跳過（fail-open），B2 改由 helper 定位前批後本檢查真的會跑，故必須認得②。
#   比對一律**大小寫不敏感**（`-REVIEW-` 與 `-review-` 同義）。家族白名單仍由下方釘住之 case 行判定
#   （scripts/governance_families.json review_families 之投影；drift 測試鎖此行）。
# **排除實作者家族** → 自動作廢「實作者自審」(不計入 quorum)。
#
# 用法: bash scripts/review_quorum_check.sh <review-task-prefix> <implementer-family>
#   例: bash scripts/review_quorum_check.sh 20260715-la0-b2 grok
# 退出: 0=≥2 個非實作者家族 review 留痕; 1=不足/缺 audit。
# 相容 bash 3.2(macOS):不用 mapfile / declare -A。
set -u
AUDIT="${GATE_DIR_OVERRIDE:-.claude/gate}/audit.log"
if [ -n "${DEBT_AUDIT_OVERRIDE:-}" ]; then
  [ "${GOVERNANCE_TEST_HARNESS:-}" = "1" ] || { echo "REVIEW-QUORUM FAIL: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1"; exit 1; }
  AUDIT="${DEBT_AUDIT_OVERRIDE}"
fi
prefix="${1:-}"
implementer="${2:-}"
[ -n "${prefix}" ] || { echo "REVIEW-QUORUM FAIL: 缺 <review-task-prefix>"; exit 1; }
[ -n "${implementer}" ] || { echo "REVIEW-QUORUM FAIL: 缺 <implementer-family>"; exit 1; }
[ -f "${AUDIT}" ] || { echo "REVIEW-QUORUM FAIL: 無 audit.log (${AUDIT})"; exit 1; }

# 候選家族（一行一個，未過白名單）：①dispatch task_id 尾碼 ②committee_output family／output_path 尾碼
distinct=""
while IFS= read -r fam; do
  [ -n "${fam}" ] || continue
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
$(python3 - "${AUDIT}" "${prefix}" <<'PY'
import json, re, sys
audit, prefix = sys.argv[1], sys.argv[2].lower()
for raw in open(audit, encoding="utf-8").read().splitlines():
    s = raw.strip()
    if not s.startswith("{"):
        continue
    try:
        r = json.loads(s)
    except json.JSONDecodeError:
        continue
    ev = r.get("event"); t = (r.get("task_id") or "").lower()
    if not (t.startswith(prefix) and "review" in t):
        continue
    if ev == "committee_dispatch":
        print(t.rsplit("-", 1)[-1])
    elif ev == "committee_output":
        fam = (r.get("family") or "").lower()
        if not fam or fam == "unknown":
            m = re.search(r"-([a-z]+)\.md$", (r.get("output_path") or "").lower())
            fam = m.group(1) if m else ""
        print(fam)
PY
)
EOF

distinct="$(printf '%s' "${distinct}" | sed -E 's/^ +//; s/ +$//')"
count=0
for _f in ${distinct}; do count=$((count+1)); done

if [ "${count}" -ge 2 ]; then
  echo "REVIEW-QUORUM PASS: batch ${prefix} 已獲 ${count} 個非實作者家族 review: ${distinct}(implementer=${implementer} 已排除)"
  exit 0
fi
echo "REVIEW-QUORUM FAIL: batch ${prefix} 僅 ${count} 個非實作者家族 review: ${distinct:-無}(需 ≥2;implementer=${implementer} 不計)"
echo "  → 中/大實作須 ≥2 非實作者家族 code review(codex/composer/grok 任二;ORCH §1);補派第二家後再派下一批。"
exit 1
