#!/usr/bin/env bash
# 重生成兩份 factkey fixture，並**自動補回 drifted 的竄改列**。
#
# 為何存在（2026-08-13）：改 scripts/fact_keys.json 後必須重生成 fixture，
# 但 --write 會把 drifted 的竄改一併蓋成 clean ⇒ 正反對照失效、drifted 那條測試恆綠（空心）。
# 主委在單一 session 內手動補了六次，且其中兩次忘記、由產出端守衛攔下
# （「FIXTURE 鑑別力已失」）。⇒ 依「工具必須自帶強制機制，不准靠紀律和記憶」做成腳本。
#
# 用法：bash scripts/regen_factkey_fixtures.sh
# 🔴 本腳本 fail-closed：補完若兩份 fixture 仍逐位元組相同，即 rc≠0（鑑別力未恢復）。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

CLEAN="tests/governance/fixtures/govb1/factkey_clean"
DRIFT="tests/governance/fixtures/govb1/factkey_drifted"
HOST="docs/GOVERNANCE_EXECUTION_ORDER.md"
# 竄改點＝序 140 那列的票號欄；改成不存在之票號，使該檔與 clean 恰差一列。
FROM='最小版見 034） | B-37 |'
TO='最小版見 034） | B-99（竄改） |'

for d in "${CLEAN}" "${DRIFT}"; do
  GOVB1_FACTKEY_ROOT="${d}" bash scripts/gen_fact_key_blocks.sh --write >/dev/null 2>&1 || {
    echo "regen 失敗: ${d}" >&2; exit 2; }
done

# 補竄改：**字面**替換，不用 sed -i（BSD/GNU 行為不同），也不用 awk 的 sub()——
# 🔴 sub() 的第一參數是**正則**，而錨點含 `|`（alternation）與全形括號，
#    會靜默匹配不到而讓竄改補不上（實測：本腳本第一版即因此回報「鑑別力未恢復」）。
LC_ALL=C awk -v from="${FROM}" -v to="${TO}" '
  {
    i = index($0, from)
    if (i > 0) $0 = substr($0, 1, i - 1) to substr($0, i + length(from))
    print
  }
' "${DRIFT}/${HOST}" > /tmp/_drift.new || exit 2
cp /tmp/_drift.new "${DRIFT}/${HOST}"

# fail-closed：兩份必須有差異，否則鑑別力仍是失效的
if cmp -s "${CLEAN}/${HOST}" "${DRIFT}/${HOST}"; then
  echo "🔴 補竄改後兩份 fixture 仍相同 → 鑑別力未恢復（竄改錨點可能已漂）" >&2
  echo "   錨點 FROM='${FROM}'；請確認該字串仍存在於生成內容中。" >&2
  exit 3
fi
n="$(LC_ALL=C diff "${CLEAN}/${HOST}" "${DRIFT}/${HOST}" | LC_ALL=C grep -c '^[<>]')"
[ "${n}" -eq 2 ] || {
  echo "🔴 兩份 fixture 差異列數為 ${n}（期望 2＝恰一列不同的雙向） → fail-closed" >&2
  exit 4; }
echo "✅ fixture 已重生成且鑑別力就位（恰一列不同）"
