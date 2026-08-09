#!/usr/bin/env bash
# 切換執行端角色分派(使用者指示時才可執行)
#
# 用途:使用者依額度調配實作端時,一句話切換,並自動保持 reviewers 一致
#      (reviewers = 三家扣掉 implementer),避免手改 JSON 產生不一致。
#
# 用法:
#   bash scripts/set_roles.sh grok      # 實作=grok, review=codex+composer
#   bash scripts/set_roles.sh codex     # 實作=codex, review=composer+grok
#   bash scripts/set_roles.sh --show    # 只看現況,不改
#
# ⚠️ 授權:本檔的 implementer 由**使用者**決定。Claude 只有在使用者明確指示時才可執行本腳本,
#    不得自行切換。每次切換會記錄 updated/updated_by/history,可稽核。
set -uo pipefail
ROLES="$(dirname "$0")/governance_roles.json"
FAMS="$(dirname "$0")/governance_families.json"

[ -f "$ROLES" ] || { echo "ERROR: 缺 $ROLES"; exit 2; }

if [ "${1:-}" = "--show" ] || [ -z "${1:-}" ]; then
  python3 - "$ROLES" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(f"實作端(implementer) : {d['implementer']}")
print(f"審查端(reviewers)   : {', '.join(d['reviewers'])}")
print(f"最後更新            : {d.get('updated','?')} by {d.get('updated_by','?')}")
h=d.get('history',[])
if h:
    print("切換紀錄:")
    for r in h[-5:]: print(f"  - {r}")
PY
  exit 0
fi

NEW="$1"
# 合格家族 = 三家【正式委員】,取自 roles SoT 的 eligible 欄。
# ⚠️ 不可直接用 governance_families.json:該檔含 agy(唯讀研究,禁實作)與 claude(編排端),
#    首版誤用它 → reviewers 被寫成 agy/claude/composer/grok(實測抓出)。
ALL=$(python3 -c "
import json
d=json.load(open('$ROLES'))
print(' '.join(d.get('eligible', ['codex','composer','grok'])))
")
case " $ALL " in *" $NEW "*) : ;; *)
  echo "ERROR: '$NEW' 不是合法家族。合法值: $ALL"; exit 2 ;;
esac

# ---------------------------------------------------------------------------
# 🔴 quorum 可行性前檢〔2026-08-09；出處＝handoffs/reconcile/20260809-govb1-x-consult-r1
#   /synth.md C4，codex+composer 兩家 APPROVED〕
#
# 病：`reviewers = 三家 − implementer`（下方 :57）是**紙上名單**，不管那幾家能不能用。
#   而 review_quorum_check.sh 要求 **≥2 個非實作者家族**（:49-51，且 :38 排除實作者）。
#   grok 額度封鎖（403）期間：
#     implementer=grok      → 非實作者池 {codex, composer} → 2 家可用 ✅
#     implementer=codex     → {composer, grok} → 僅 1 家可用 ❌ quorum 當場破
#     implementer=composer  → {codex, grok}    → 僅 1 家可用 ❌ quorum 當場破
#   ⇒ 現行三個 eligible 值中**唯有 grok 能保住兩家審查者**，而那是巧合不是設計。
#   任何人憑直覺 `set_roles.sh codex` 都會在**下一次派 review 時**才發現鐵律已破。
#
# 修法：切換**前**就用機器算一次。可用集合＝governance_families.json 的
#   `active_stampers`（本期實際能蓋章者；缺 key ⇒ 回退 review_families）。
#   |可用集合 − {新 implementer}| < 2 ⇒ **拒絕切換**（fail-closed），
#   並印出「要切成這家，得先讓誰恢復」。
# 逃生口：SET_ROLES_ALLOW_QUORUM_BREAK=1 —— **刻意留**，因為使用者可能正是要
#   在恢復額度的同一分鐘內切換；但必須是明示動作，不能是預設靜默。
# ---------------------------------------------------------------------------
_SR_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/governance_families.sh
. "${_SR_DIR}/governance_families.sh"
_usable="$(families_active_stampers 2>/dev/null)"; _u_rc=$?
if [ "${_u_rc}" -eq 3 ]; then
  _usable="$(families_get review_families)" || _usable=""
elif [ "${_u_rc}" -ne 0 ]; then
  echo "ERROR: active_stampers 不合法 ⇒ 無法評估 quorum 可行性(fail-closed)" >&2
  exit 2
fi
if [ -n "${_usable}" ]; then
  _left=0; _leftlist=""
  IFS=',' read -ra _us <<< "${_usable}"
  for _f in "${_us[@]}"; do
    _f="$(printf '%s' "${_f}" | tr -d '[:space:]')"
    [ -z "${_f}" ] && continue
    [ "${_f}" = "${NEW}" ] && continue
    _left=$((_left + 1)); _leftlist="${_leftlist} ${_f}"
  done
  if [ "${_left}" -lt 2 ] && [ "${SET_ROLES_ALLOW_QUORUM_BREAK:-0}" != "1" ]; then
    echo "ERROR: 切成 implementer=${NEW} 會使可用之非實作者家族只剩 ${_left} 家(${_leftlist:- 無})" >&2
    echo "  中/大實作須 ≥2 非實作者 code review(review_quorum_check.sh)⇒ 下一輪 review 必被擋。" >&2
    echo "  目前可用(active_stampers)= ${_usable}" >&2
    echo "  → 要切成 ${NEW}，須先讓另一家恢復並加回 governance_families.json 的 active_stampers。" >&2
    echo "  → 確知自己在做什麼(例:同時恢復額度)：SET_ROLES_ALLOW_QUORUM_BREAK=1 bash scripts/set_roles.sh ${NEW}" >&2
    exit 2
  fi
fi

python3 - "$ROLES" "$NEW" "$ALL" <<'PY'
import json,sys
path,new,allf=sys.argv[1],sys.argv[2],sys.argv[3].split()
d=json.load(open(path))
old=d.get('implementer')
if old==new:
    print(f"無變更:implementer 已是 {new}"); raise SystemExit(0)
d['implementer']=new
d['implementer_backup']=[f for f in allf if f!=new][0]
d['reviewers']=sorted(f for f in allf if f!=new)   # 實作者不自審
d['updated_by']='user'
d.setdefault('history',[]).append(f"{old} -> {new}")
json.dump(d,open(path,'w'),ensure_ascii=False,indent=2)
open(path,'a').write("\n")
print(f"已切換:implementer {old} -> {new};reviewers = {', '.join(d['reviewers'])}")
PY

echo "--- 切換後角色閘自我驗證 ---"
bash "$(dirname "$0")/verify_role_gate.sh" 2>&1 | tail -3
