#!/usr/bin/env bash
# B1-FIX 獨立驗收（主委端，不採信實作端自報）
# 專攻三家裁決的四項；F2/F3 是主委上一輪【漏掉】的洞，故本輪逐一實跑。
set -uo pipefail
fail=0
S=handoffs/reconcile/p16-b1-ruling          # F1 剛建成的真 session
ok()  { printf '  ✅ %s\n' "$1"; }
bad() { printf '  ❌ %s\n' "$1"; fail=1; }

echo "=== F1：fresh discovery 不做 audit 反查（bootstrap P0）==="
[ -d "$S" ] && ok "被鎖死的 reconcile 已可建成" || bad "session 未建成"

echo "=== F1b：fresh --mode review 無對應開債 → 仍須拒 ==="
bash scripts/reconcile_build.sh p16-b1fix-negtest --mode review \
     handoffs/20260729-p16-b1-ruling-codex.md handoffs/20260729-p16-b1-ruling-grok.md >/dev/null 2>&1
rc=$?
[ "$rc" -ne 0 ] && ok "fresh review 無開債 → rc=${rc}（拒建，正確）" \
                || bad "fresh review 竟建成 rc=0（identity binding 失效）"
[ -d handoffs/reconcile/p16-b1fix-negtest ] && bad "拒建卻留下目錄" || ok "拒建未留殘檔"

echo "=== F2：write_sources_lock --rebuild 不得接受外來 round-id ==="
# 同 F3：補齊必填參數並比對訊息，避免被別的守衛擋下而誤判閉合
bash scripts/write_sources_lock.sh --session "$S" --roster codex,composer,grok \
     --mode review --round-id BOGUS-ROUND --rebuild > /tmp/_f2.log 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -qE '拒收呼叫端 --round-id|identity' /tmp/_f2.log; then
  ok "帶任意 --round-id 的 --rebuild → rc=${rc}，且訊息確為 identity 相關拒收"
else
  bad "F2 未確證（rc=${rc}；訊息：$(head -1 /tmp/_f2.log)）"
fi
rm -f /tmp/_f2.log

echo "=== F3：public writer 不得直接建 review lock 塞任意 round ==="
# ⚠️ GROK-R3-P2-01：初版此步漏傳 --roster，拿到的 rc=2 是「必填 --roster」
#    而非 identity binding 拒收 → 假 PASS。故本步必須①補齊其他必填參數
#    ②比對錯誤訊息，證明擋下來的真的是我們要驗的那道守衛。
bash scripts/write_sources_lock.sh --session "$S" --roster codex,composer,grok \
     --mode review --round-id FORGED > /tmp/_f3.log 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -q '拒收呼叫端 --round-id' /tmp/_f3.log; then
  ok "writer 直建 review + 任意 round → rc=${rc}，且錯誤訊息確為 identity binding 拒收"
else
  bad "F3 未確證（rc=${rc}；訊息：$(head -1 /tmp/_f3.log)）"
fi
rm -f /tmp/_f3.log

echo "=== F2/F3 反 bypass：修法不得依賴 harness ==="
if grep -n 'rebuild' scripts/write_sources_lock.sh | grep -qi 'GOVERNANCE_TEST_HARNESS'; then
  bad "--rebuild 路徑引用 GOVERNANCE_TEST_HARNESS（違反紅線）"
else ok "--rebuild 路徑未引用 harness"; fi

echo "=== F4：mutation 探針是真 oracle ==="
bash scripts/mutation_probe_check.sh tests/governance/test_registry_v2_shape.py >/dev/null 2>&1
rc=$?
[ "$rc" -eq 0 ] && ok "mutation_probe_check rc=0" || bad "mutation_probe_check rc=${rc}"

echo "=== 防假綠：既有測試零改動 ==="
n=$(git diff -- tests/ | grep -cE '^-.*assert' || true)
[ "$n" -eq 0 ] && ok "既有測試無斷言被刪（-assert 行數 ${n}）" || bad "有 $n 行 assert 被刪"

echo
[ "$fail" = 0 ] && echo "B1-FIX INDEPENDENT VERIFY PASS" || echo "B1-FIX INDEPENDENT VERIFY FAIL"
exit "$fail"
