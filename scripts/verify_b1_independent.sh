#!/usr/bin/env bash
# B1 獨立驗收（主委端，不採信實作端自報）
# 重點：SPEC v2.4/v2.5 兩度栽在「修法依賴 harness-bound 旗標 → 正式路徑不可達」，
#       故本腳本刻意在【未設 GOVERNANCE_TEST_HARNESS】下跑 --rebuild。
set -uo pipefail
fail=0
chk() { # chk <說明> <期望rc> <cmd...>
  local d="$1" want="$2"; shift 2
  "$@" >/dev/null 2>&1; local got=$?
  if [ "$got" = "$want" ]; then printf '  ✅ %-52s rc=%s\n' "$d" "$got"
  else printf '  ❌ %-52s rc=%s (want %s)\n' "$d" "$got" "$want"; fail=1; fi
}

echo "=== 1. registry v2 形狀 ==="
chk "audit_events.json 為合法 JSON" 0 python3 -m json.tool scripts/audit_events.json
for k in debt_events enums; do
  printf '  ·  %s\n' "$(python3 -c "
import json;d=json.load(open('scripts/audit_events.json'))
if '$k'=='debt_events':
    v=d.get('debt_events',{}); print('debt_events 數量 =', len(v), sorted(v) if len(v)<8 else '')
else:
    e=d.get('enums',{})
    print('round_state=',e.get('round_state'),' result_state=',e.get('result_state'),' abandon_kind=',e.get('abandon_kind'))
")"
done
printf '  ·  attempt_cap 殘留 = %s (應 0)\n' "$(grep -c attempt_cap scripts/audit_events.json)"

echo "=== 2. lock 工具鏈旗標 ==="
bash scripts/reconcile_build.sh --help 2>&1 | grep -q -- '--mode' && echo "  ✅ --help 含 --mode" || { echo "  ❌ --help 缺 --mode"; fail=1; }
bash scripts/reconcile_build.sh --help 2>&1 | grep -q -- '--rebuild' && echo "  ✅ --help 含 --rebuild" || { echo "  ❌ --help 缺 --rebuild"; fail=1; }

echo "=== 3. 反 bypass 紅線：--rebuild 不得依賴 harness / --force ==="
if grep -n 'rebuild' scripts/reconcile_build.sh | grep -qi 'GOVERNANCE_TEST_HARNESS'; then
  echo "  ❌ --rebuild 路徑出現 GOVERNANCE_TEST_HARNESS（SPEC 明禁）"; fail=1
else
  echo "  ✅ --rebuild 路徑未引用 GOVERNANCE_TEST_HARNESS"
fi
if grep -n 'rebuild' scripts/reconcile_build.sh | grep -q -- '--force'; then
  echo "  ❌ --rebuild 路徑出現 --force（SPEC 明禁）"; fail=1
else
  echo "  ✅ --rebuild 路徑未使用 --force"
fi

echo "=== 4. 新測試與既有測試 ==="
chk "test_registry_v2_shape.py 全綠" 0 venv/bin/python -m pytest tests/governance/test_registry_v2_shape.py -q
echo "  ·  既有測試檔改動行數（應 0）: $(git diff -- tests/ | wc -l | tr -d ' ')"

echo "=== 5. 語法 ==="
chk "reconcile_build.sh 語法" 0 bash -n scripts/reconcile_build.sh
chk "write_sources_lock.sh 語法" 0 bash -n scripts/write_sources_lock.sh

echo
[ "$fail" = 0 ] && echo "B1 INDEPENDENT VERIFY PASS" || echo "B1 INDEPENDENT VERIFY FAIL"
exit "$fail"
