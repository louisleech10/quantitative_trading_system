#!/usr/bin/env bash
# 切換執行端角色分派(使用者指示時才可執行)
#
# 用途:使用者依額度調配實作端時,一句話切換,並自動保持 reviewers 一致
#      (reviewers = 三家扣掉 implementer),避免手改 JSON 產生不一致。
#
# 用法:
#   bash scripts/set_roles.sh claude    # 實作=編排端自任, review=codex+composer+grok(三家全員)
#   bash scripts/set_roles.sh grok      # 實作=grok, review=codex+composer
#   bash scripts/set_roles.sh codex     # 實作=codex, review=composer+grok
#   bash scripts/set_roles.sh --show    # 只看現況,不改
#
# 🔴 `claude` = 編排端(無 CLI 映射,永不可被派工)。填它代表「實作由主委自任、不對外派工」,
#    此時三家委員全員都是合法審查者。出處與代價見 docs/GOV_ROLES_ORCHESTRATOR_AMENDMENT.md。
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
# 🔴 缺 `eligible` 一律 fail-closed〔CODEX-R1-P1-05，20260811-govb49-x-consult-r1〕：
#   原寫法 `d.get('eligible', ['codex','composer','grok'])` 在缺鍵時**靜默落回舊三家硬編**，
#   使用者改了 roster 卻得到「命令成功但角色集合不照 SoT」。角色 SoT 缺鍵＝無從判定，須拒。
ALL=$(python3 -c "
import json,sys
d=json.load(open('$ROLES'))
v=d.get('eligible')
if not isinstance(v,list) or not v or not all(isinstance(x,str) and x.strip() for x in v):
    sys.stderr.write('ERROR: 角色 SoT eligible 缺/壞 ⇒ 無從判定合法家族(fail-closed)\n'); sys.exit(2)
print(' '.join(v))
") || exit 2
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
  # 🔴 fallback 失敗**不得**吞成空集合〔CODEX-R3-P1-03〕：
  #   原寫法 `|| _usable=""` 會讓 `review_families` 壞掉時整個前檢被跳過（fail-open）
  #   ——實測 `del active_stampers` + `review_families=[]` ⇒ rc=0 且 roles.json 被改寫。
  #   這正是 R-19 修過一次的同型錯誤，主委在同一天又犯一次。
  _usable="$(families_get review_families)" || {
    echo "ERROR: active_stampers 缺席且 review_families 讀取失敗 ⇒ 無法評估 quorum(fail-closed)" >&2
    exit 2
  }
elif [ "${_u_rc}" -ne 0 ]; then
  echo "ERROR: active_stampers 不合法 ⇒ 無法評估 quorum 可行性(fail-closed)" >&2
  exit 2
fi
# 空集合亦拒：走到這裡就代表兩個來源都沒給出可用家族
if [ -z "${_usable}" ]; then
  echo "ERROR: 可用家族集合為空 ⇒ 無法評估 quorum 可行性(fail-closed)" >&2
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
  if [ "${_left}" -lt 2 ]; then
    if [ "${SET_ROLES_ALLOW_QUORUM_BREAK:-0}" != "1" ]; then
      echo "ERROR: 切成 implementer=${NEW} 會使可用之非實作者家族只剩 ${_left} 家(${_leftlist:- 無})" >&2
      echo "  中/大實作須 ≥2 非實作者 code review(review_quorum_check.sh)⇒ 下一輪 review 必被擋。" >&2
      echo "  目前可用(active_stampers)= ${_usable}" >&2
      echo "  → 要切成 ${NEW}，須先讓另一家恢復並加回 governance_families.json 的 active_stampers。" >&2
      echo "  → 確知自己在做什麼(例:同時恢復額度)：" >&2
      echo "     SET_ROLES_ALLOW_QUORUM_BREAK=1 SET_ROLES_QUORUM_BREAK_REASON='<理由>' bash scripts/set_roles.sh ${NEW}" >&2
      exit 2
    fi
    # 🔴 逃生口須具名理由並持久化〔CODEX-R3-P2-04〕：
    #   只驗環境值 =1 ⇒ 破壞 quorum 這件事**無法歸因**（history 只寫 old -> new）。
    #   逃生口保留（使用者可能正在恢復額度的同一分鐘切換），但必須留下可稽核的理由。
    _reason="${SET_ROLES_QUORUM_BREAK_REASON:-}"
    case "$(printf '%s' "${_reason}" | tr -d '[:space:]')" in
      "") echo "ERROR: 使用 SET_ROLES_ALLOW_QUORUM_BREAK 須同時給 SET_ROLES_QUORUM_BREAK_REASON='<非空理由>'" >&2
          echo "  破壞 review quorum 是可稽核事件，理由會寫入 governance_roles.json 的 history。" >&2
          exit 2 ;;
    esac
    export SET_ROLES_HISTORY_NOTE="quorum-break(left=${_left}): ${_reason}"
    echo "⚠ 已明示破壞 review quorum：可用非實作者僅剩 ${_left} 家(${_leftlist:- 無})" >&2
    echo "  理由（將寫入 history）：${_reason}" >&2
  fi
fi

# 🔴 reviewers 公式須交集**可派工家族**〔GROK-R1-P0-01，20260811-govb49-x-consult-r1〕：
#   `eligible` 自 2026-08-11 起含編排端 `claude`（可當 implementer、但**無 CLI 映射、永不可派工**）。
#   舊公式 `reviewers = eligible − implementer` ⇒ 下次切回任一 CLI 家族時
#   reviewers 會含 claude ⇒ `_role_gate.sh check-families` strict 整批 rc=2 ⇒ 全名單派工當場死。
#   grok 以隔離 workdir 實跑證明（implementer=codex ⇒ reviewers=[claude,composer,grok] ⇒ rc=2）。
#   正確語義：角色值集合(eligible) ≠ 可派工集合(review_families ∩ 有 CLI 映射)。
_RF="$(families_get review_families ' ')" || {
  echo "ERROR: 讀 review_families 失敗 ⇒ 無從導出 reviewers(fail-closed)" >&2; exit 2; }

python3 - "$ROLES" "$NEW" "$ALL" "$_RF" <<'PY'
import json,sys
path,new,allf,rf=sys.argv[1],sys.argv[2],sys.argv[3].split(),sys.argv[4].split()
d=json.load(open(path))
old=d.get('implementer')
if old==new:
    print(f"無變更:implementer 已是 {new}"); raise SystemExit(0)
# 可派工審查者池 = eligible ∩ review_families − {implementer}；編排端永不入 reviewers
pool=[f for f in allf if f in rf and f!=new]
if len(pool)<2:
    sys.stderr.write(
        "ERROR: eligible ∩ review_families − {%s} 只剩 %d 家 ⇒ 兩家 review 鐵律當場破(fail-closed)\n"
        % (new, len(pool))); sys.exit(2)
d['implementer']=new
d['implementer_backup']=pool[0]
d['reviewers']=sorted(pool)   # 實作者不自審
d['updated_by']='user'
import os
_note=os.environ.get('SET_ROLES_HISTORY_NOTE','').strip()
d.setdefault('history',[]).append(f"{old} -> {new}" + (f"  ※{_note}" if _note else ""))
json.dump(d,open(path,'w'),ensure_ascii=False,indent=2)
open(path,'a').write("\n")
print(f"已切換:implementer {old} -> {new};reviewers = {', '.join(d['reviewers'])}")
PY

echo "--- 切換後角色閘自我驗證 ---"
bash "$(dirname "$0")/verify_role_gate.sh" 2>&1 | tail -3
