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
