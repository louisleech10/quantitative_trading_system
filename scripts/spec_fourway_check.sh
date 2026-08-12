#!/usr/bin/env bash
# P1-6 SPEC 四向擁有權 **smoke check**（非語意檢查）
#
# ⚠️ 誠實邊界（codex R8-P1-02 指正後降級，2026-07-28）：
#   本腳本只做**固定字串 `grep -c`**。它**不解析 Task 區段邊界**、不驗 mutation 對應、
#   不驗鎖交接契約。因此它**擋不住**：換同義句、把改法寫進**錯的 Task**、
#   空泛的 happy path。第④項（矛盾絕對句）更只是**印出清單供人工比對**，非自動判定。
#   → 定位＝**回歸 smoke check**（防「我改完忘了同步某處」），**不是**收斂保證。
#   → **刻意不做成通用 map 驅動閘門**：2026-07-27 已試過通用版（`doc_consistency_check.sh`
#      + map.tsv + 14 測試），實測 35 份 SPEC 只有 P16 真受保護、又與探針閘門衝突，
#      使用者裁定撤除。**不重蓋。**
#   → 故**不接入 `gov_check.sh`**，不作為任何 gate 的前置條件。
#
# 為何存在：R4→R7 連續四輪、共 7 次同型 finding 都是「改一處漏多處」。
# 對策逐輪演進：兩類複掃 → 9 類 → 加語意檢查 → 加責任落點 → 改法+驗證雙落點
# → 仍在 R7 漏掉（因為改法落在了「錯的 Task」，且全檔留著矛盾的絕對句）。
#
# 四向 = 每條要求須同時確認：
#   ① 落在「擁有該腳本的那個 Task」的改法段
#   ② 該 Task 的驗證段
#   ③ §V 有對應 mutation
#   ④ 全檔無與之矛盾的絕對句   ← v2.7 新增，正是 R7 P0 的成因
#
# 用法：bash scripts/spec_fourway_check.sh [SPEC路徑]
# rc=0 全綠；rc=1 有向次未達預期
set -uo pipefail
SPEC="${1:-docs/P16_COMMITTEE_DEBT_SPEC.md}"
fail=0

chk() {  # chk <說明> <期望數> <grep pattern>
  local desc="$1" want="$2" pat="$3" got
  got=$(grep -c -- "$pat" "$SPEC")
  if [ "$got" = "$want" ]; then
    printf '  ✅ %-44s %s\n' "$desc" "$got"
  else
    printf '  ❌ %-44s got=%s want=%s\n' "$desc" "$got" "$want"
    fail=1
  fi
}

echo "=== 標的：$SPEC ($(wc -l < "$SPEC" | tr -d ' ') 行, sha=$(shasum -a 256 "$SPEC" | cut -c1-20)) ==="

# 🔴 只驗範本錨點；文件內 ASSERT **預設不執行**（預設值定於 template_check.sh，此處無需帶旗標）。
#   本呼叫端曾是「人工盤點漏掉、正則掃描也看不見」的第四處——正是預設值反轉的理由。
#   見 docs/GOV_ASSERT_PATHA_NOTE.md。
bash scripts/template_check.sh spec "$SPEC" >/dev/null 2>&1
rc=$?
if [ "$rc" = 0 ]; then echo "  ✅ template_check rc=0"; else echo "  ❌ template_check rc=$rc"; fail=1; fi

echo "--- 向① 改法落在擁有該腳本的 Task ---"
chk 'reconcile_build 的 --rebuild 在 Task 0.1' 1 '接受 `--rebuild`，實作 Task 2.2 1b'
# R8 起：唯一性判定的擁有權從 Task 1.2 移到 Task 1.1（鎖的持有者），故斷言跟著移
chk '原子 predicate+append 在 Task 1.1 改法⑥' 1 '為何必須長在本 Task'
chk 'Task 1.2 只准呼叫該 API（不自行取鎖）'    1 '也不得自行取鎖後呼叫 `audit_append.sh`'

echo "--- 向② 同一 Task 的驗證段 ---"
chk 'Task1.2 驗證：重複 session 名'          1 '第二次以同一 `--session` 名開債'
chk 'Task1.2 驗證：並行同名（原子性）'        1 '兩程序並行以同一 `--session` 名開債'
chk 'Task2.2 驗證：--rebuild 行為'           1 '1b `--rebuild` 的行為驗收'
chk 'Task0.1 驗證：session_name 欄'          1 '`committee_round_open.fields` 含 `session_name`'

echo "--- 向③ §V mutation ---"
mut=$(grep -cE '^ *\| M3[234] \|' "$SPEC")
if [ "$mut" = 3 ]; then printf '  ✅ %-44s %s\n' 'M32/M33/M34 在位' "$mut"
else printf '  ❌ %-44s got=%s want=3\n' 'M32/M33/M34 在位' "$mut"; fail=1; fi

echo "--- 向④ 矛盾絕對句（v2.7 新增；R7 P0 的成因）---"
# 這些是被 --rebuild 修法推翻的舊絕對句，正文一律不得殘留
for bad in '不存在事後重凍' '不需要、也不提供事後重凍' '無事後重凍' '換一個 session 名重建'; do
  n=$(grep -c -- "$bad" "$SPEC")
  # 檔頭沿革敘述允許出現（作為「已廢除」的歷史說明），故只擋正文
  n_body=$(awk 'NR>60' "$SPEC" | grep -c -- "$bad")
  if [ "$n_body" = 0 ]; then printf '  ✅ 正文無殘留：%-30s (全檔 %s，皆在檔頭沿革)\n' "$bad" "$n"
  else printf '  ❌ 正文殘留：%-32s %s 處\n' "$bad" "$n_body"; fail=1; fi
done

echo "--- 向④ 人工比對清單（否定句逐條；非自動判定）---"
grep -nE '不提供|正式路徑不可達' "$SPEC" | cut -c1-110 | sed 's/^/      /'

echo
if [ "$fail" = 0 ]; then
  echo "FOURWAY SMOKE PASS  ⚠️ 僅固定字串比對；不解析 Task 邊界、不驗語意。PASS 不等於已收斂。"
else
  echo "FOURWAY SMOKE FAIL"
fi
exit "$fail"
