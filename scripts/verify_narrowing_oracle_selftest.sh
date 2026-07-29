#!/usr/bin/env bash
# verify_narrowing_consistency.sh 的**自證**:用 codex R6-P1-01 的 mutation 證明它該紅時真的紅。
#
# 為何存在:該檢查首版按【整行】判定,SPEC:194 同行另一個斷言的 review token
#   會掩護被拿掉限定的斷言 → 假綠。codex 實跑 mutation 證實。
#   改為逐斷言後,必須能證明「拿掉任一斷言的 review 限定 → 轉紅」。
#
# 用法:bash scripts/verify_narrowing_oracle_selftest.sh
set -uo pipefail
SPEC=docs/P16_COMMITTEE_DEBT_SPEC.md
BAK="handoffs/_narrowbak_$$.md"
fail=0
cleanup() { [ -f "$BAK" ] && cp "$BAK" "$SPEC"; rm -f "$BAK"; }
trap cleanup EXIT

cp "$SPEC" "$BAK"

echo "=== 基線:未變異應 PASS ==="
bash scripts/verify_narrowing_consistency.sh >/dev/null 2>&1
[ $? -eq 0 ] && echo "  ✅ 基線 PASS" || { echo "  ❌ 基線就紅,無法自證"; exit 1; }

echo "=== mutation A:拿掉【第一個】fail-closed 斷言的 --mode review（codex 用的那個）==="
sed 's|以 audit 中不存在的 session 名跑 `reconcile_build` `--mode review` → rc≠0|以 audit 中不存在的 session 名跑 `reconcile_build` → rc≠0|' "$BAK" > "$SPEC"
if ! diff -q "$BAK" "$SPEC" >/dev/null; then
  bash scripts/verify_narrowing_consistency.sh >/dev/null 2>&1
  if [ $? -ne 0 ]; then echo "  ✅ 轉紅（假綠已修復）"; else echo "  ❌ 仍 PASS ＝ 假綠未修"; fail=1; fi
else echo "  ⚠️ mutation 未命中目標字串,檢查 SPEC 措辭"; fail=1; fi
cp "$BAK" "$SPEC"

echo "=== mutation B:拿掉【第二個】斷言的 --mode review ==="
sed 's|以重複（≥2 筆）的 session 名跑 `--mode review` → rc≠0|以重複（≥2 筆）的 session 名跑 → rc≠0|' "$BAK" > "$SPEC"
if ! diff -q "$BAK" "$SPEC" >/dev/null; then
  bash scripts/verify_narrowing_consistency.sh >/dev/null 2>&1
  if [ $? -ne 0 ]; then echo "  ✅ 轉紅"; else echo "  ❌ 仍 PASS ＝ 假綠"; fail=1; fi
else echo "  ⚠️ mutation 未命中目標字串"; fail=1; fi
cp "$BAK" "$SPEC"

# ── CODEX-R7-P1-01 的四種攻法,逐一必須轉紅 ──────────────────────
_mut() { # _mut <說明> <sed 運算式>
  sed "$2" "$BAK" > "$SPEC"
  if diff -q "$BAK" "$SPEC" >/dev/null; then
    printf '  ⚠️ %s：mutation 未命中目標字串\n' "$1"; fail=1; cp "$BAK" "$SPEC"; return
  fi
  bash scripts/verify_narrowing_consistency.sh >/dev/null 2>&1
  if [ $? -ne 0 ]; then printf '  ✅ %s → 轉紅\n' "$1"
  else printf '  ❌ %s → 仍 PASS（假綠）\n' "$1"; fail=1; fi
  cp "$BAK" "$SPEC"
}

echo "=== codex R7 四攻法（半形 ; / 半形 , / 跨行 / 否定語境）==="
_L='以 audit 中不存在的 session 名跑 `reconcile_build` `--mode review` → rc≠0'
_N='以 audit 中不存在的 session 名跑 `reconcile_build` → rc≠0'
# ① 半形 ; 分隔：拿掉第一個斷言的限定,並把其後的全形頓號改半形分號
_mut "攻法① 半形 ;"  "s|${_L}\*\*、\*\*|${_N}**;**|"
# ② 半形 , 分隔
_mut "攻法② 半形 ,"  "s|${_L}\*\*、\*\*|${_N}**,**|"
# ③ 斷言跨行（在斷言中間插換行）
_mut "攻法③ 斷言跨行" "s|${_L}|以 audit 中不存在的 session 名跑\\
\`reconcile_build\` → rc≠0|"
# ④ 否定語境：review 字串在,但語意是「review 之外」
_mut "攻法④ 否定語境" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（review 之外的情況）→ rc≠0|"

echo "=== codex R8 第 5 攻法（全形逗號 ，＝中文最常見子句分隔）==="
_mut "攻法⑤ 全形逗號 ，" "s|${_L}\*\*、\*\*|${_N}**，**|"
echo "=== 補強：全形句號 。 與半形句號 .（過度切分＝安全方向）==="
_mut "攻法⑥ 全形句號 。" "s|${_L}\*\*、\*\*|${_N}**。**|"
_mut "攻法⑦ 半形句號 ." "s|${_L}\*\*、\*\*|${_N}**.**|"

echo "=== codex R9 第 6 攻法（全形冒號 ：）＋ 整類封閉驗證 ==="
_mut "攻法⑧ 全形冒號 ：" "s|${_L}\*\*、\*\*|${_N}**：**|"
# 整類封閉:任取數個未被單獨列舉過的標點,都應轉紅
_mut "攻法⑨ 全形驚嘆號 ！" "s|${_L}\*\*、\*\*|${_N}**！**|"
_mut "攻法⑩ 全形問號 ？" "s|${_L}\*\*、\*\*|${_N}**？**|"
_mut "攻法⑪ 半形冒號 :"   "s|${_L}\*\*、\*\*|${_N}**:**|"
_mut "攻法⑫ 半形分隔 \|"  "s|${_L}\*\*、\*\*|${_N}**\|**|"

echo "=== codex R10 第 7 攻法（前綴否定：非 / 不限 / 排除 … review）==="
_mut "攻法⑬ 前綴否定 非…review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（非 review 模式）→ rc≠0|"
_mut "攻法⑭ 前綴否定 不限…review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（不限 review）→ rc≠0|"
_mut "攻法⑮ 前綴否定 排除…review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（排除 review 的情形）→ rc≠0|"

echo "=== codex R11 第 8 攻法（不+動詞：不帶／不加／不使用／不需要）==="
_mut "攻法⑯ 不帶 review"   "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（不帶 review 旗標）→ rc≠0|"
_mut "攻法⑰ 不加 review"   "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（不加 review）→ rc≠0|"
_mut "攻法⑱ 不使用 review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（不使用 review 模式）→ rc≠0|"
_mut "攻法⑲ 不需要 review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（不需要 review）→ rc≠0|"
_mut "攻法⑳ 未指定 review" "s|${_L}|以 audit 中不存在的 session 名跑 \`reconcile_build\`（未指定 review）→ rc≠0|"

echo "=== 復原後應回到 PASS ==="
bash scripts/verify_narrowing_consistency.sh >/dev/null 2>&1
[ $? -eq 0 ] && echo "  ✅ 復原轉綠" || { echo "  ❌ 復原後仍紅"; fail=1; }

echo
[ "$fail" = 0 ] && echo "NARROWING ORACLE SELFTEST PASS" || echo "NARROWING ORACLE SELFTEST FAIL"
exit "$fail"
