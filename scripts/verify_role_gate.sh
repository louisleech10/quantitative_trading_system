#!/usr/bin/env bash
# 角色閘 oracle:證明它擋得住 2026-07-24 / 07-29 實際犯過的兩種誤派
# 用法:bash scripts/verify_role_gate.sh
set -uo pipefail
fail=0
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

mk() { # mk <file> <brief-kind>  產出最小合規 brief
  { printf 'brief-kind: %s\n\n' "$2"
    printf '照 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文執行。\n'
    printf 'fact-verified: 測試用\nassumed: 測試用\n'; } > "$1"
}
mk "$TMP/impl.md"   impl
mk "$TMP/review.md" review

run() { bash scripts/cx_run.sh "$1" "$2" /tmp/_rolegate_probe_NOT_HANDOFFS.md > "$TMP/out" 2>&1; echo $?; }

IMPL=$(python3 -c "import json;print(json.load(open('scripts/governance_roles.json'))['implementer'])")
REV=$(python3 -c "import json;print(json.load(open('scripts/governance_roles.json'))['reviewers'][0])")
echo "SoT: implementer=${IMPL}  reviewer(取一)=${REV}"
echo

echo "=== 反例 1:把 impl 派給 reviewer(＝2026-07-29 我犯的錯)==="
rc=$(run "$REV" "$TMP/impl.md")
if [ "$rc" -ne 0 ] && grep -q '角色不符' "$TMP/out"; then
  printf '  ✅ 拒派 rc=%s：%s\n' "$rc" "$(grep -m1 '角色不符' "$TMP/out")"
else printf '  ❌ 未擋住(rc=%s)\n' "$rc"; fail=1; fi

echo "=== 反例 2:把 implementer 排進 code review(＝2026-07-24 我犯的錯)==="
rc=$(run "$IMPL" "$TMP/review.md")
if [ "$rc" -ne 0 ] && grep -q '實作者不自審' "$TMP/out"; then
  printf '  ✅ 拒派 rc=%s：%s\n' "$rc" "$(grep -m1 '實作者不自審' "$TMP/out")"
else printf '  ❌ 未擋住(rc=%s)\n' "$rc"; fail=1; fi

echo "=== 正例 1:impl 派給 implementer → 不得被角色閘擋 ==="
rc=$(run "$IMPL" "$TMP/impl.md")
if grep -q '角色不符' "$TMP/out"; then printf '  ❌ 正確派工被誤擋\n'; fail=1
else printf '  ✅ 未被角色閘擋(rc=%s,後續錯誤與角色無關)\n' "$rc"; fi

echo "=== 正例 2:review 派給 reviewer → 不得被角色閘擋 ==="
rc=$(run "$REV" "$TMP/review.md")
if grep -q '角色不符\|實作者不自審' "$TMP/out"; then printf '  ❌ 正確派工被誤擋\n'; fail=1
else printf '  ✅ 未被角色閘擋(rc=%s)\n' "$rc"; fi

echo "=== 反例 3:註解假宣告繞過(CODEX-R5-P0-01 實跑證實的 P0)==="
# brief 內先出現註解 `# brief-kind: review`,真宣告在後面 → 舊版 head -1 會取到註解那筆
{ printf '# brief-kind: review   <- 假宣告(註解),舊版會被它騙過\n\n'
  printf 'brief-kind: impl\n\n'
  printf 'fact-verified: 測試用\nassumed: 測試用\n'; } > "$TMP/decoy.md"
rc=$(run "$REV" "$TMP/decoy.md")
if [ "$rc" -ne 0 ] && grep -qE '角色不符|不一致.*brief-kind' "$TMP/out"; then
  printf '  ✅ 拒派 rc=%s：%s\n' "$rc" "$(grep -m1 -E '角色不符|不一致' "$TMP/out")"
else printf '  ❌ 註解假宣告仍可繞過(rc=%s；訊息：%s)\n' "$rc" "$(head -1 "$TMP/out")"; fail=1; fi

echo "=== 反例 4:多筆不一致的行首宣告 → 歧義須 fail-closed ==="
{ printf 'brief-kind: closure\n\nbrief-kind: impl\n\n'
  printf 'fact-verified: 測試用\nassumed: 測試用\n'; } > "$TMP/dup.md"
rc=$(run "$REV" "$TMP/dup.md")
if [ "$rc" -ne 0 ] && grep -q '不一致' "$TMP/out"; then
  printf '  ✅ 拒派 rc=%s(歧義 fail-closed)\n' "$rc"
else printf '  ❌ 多筆宣告未 fail-closed(rc=%s)\n' "$rc"; fail=1; fi

echo "=== fail-closed:SoT 缺檔 → 拒派 ==="
mv scripts/governance_roles.json "$TMP/roles.bak"
rc=$(run "$IMPL" "$TMP/impl.md")
mv "$TMP/roles.bak" scripts/governance_roles.json
if [ "$rc" -ne 0 ] && grep -q 'fail-closed' "$TMP/out"; then
  printf '  ✅ SoT 缺檔 → rc=%s 拒派\n' "$rc"
else printf '  ❌ SoT 缺檔竟未拒派(rc=%s)\n' "$rc"; fail=1; fi


echo
[ "$fail" = 0 ] && echo "ROLE GATE ORACLE PASS" || echo "ROLE GATE ORACLE FAIL"
exit "$fail"
