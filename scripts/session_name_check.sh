#!/usr/bin/env bash
# session_name_check.sh — 派工 session／task-id 命名規約的機械強制。
#
# 為何存在（2026-08-06 使用者指出）：
#   「你看任務名長很像，到時候每個人都混亂」。
#   現況實例（同一天、同一批）：
#     govb0-b3-review / govb0-b3-fixreview / govb0-b3-fix2review
#     govb0-b3-stamp  / govb0-b3-fixstamp  / govb0-b3-stamp-grok
#   風險不是美觀：派工的 --adversarial 要指對收斂檔、銷帳要指對 round_id，
#   **指錯一個，整輪的證據鏈就接到別的地方**。主委每次都須先 grep 才敢動＝摩擦。
#
# 規約（新輪次適用；**舊 session 不溯及既往**，依使用者定死的「面向未來」原則）：
#
#   session : <YYYYMMDD>-<epic>-<batch>-<kind>-r<N>
#   task-id : 同上轉大寫（連字號保留）
#
#   epic  : 小寫英數（govb0 / p16 / ic …）
#   batch : b<數字>（可帶小數位，如 b3 / b35 / b4）；非批次型輪次用 x
#   kind  : impl | review | stamp | consult | fix   （**封閉集合**）
#   r<N>  : 第幾次派（**必填**）。重派一律 r2、r3…，
#           禁用舊法的裸數字後綴（`…-review2`）——那看不出是「第二次派」還是「第二個主題」。
#
# 例：
#   20260806-govb0-b35-review-r1    20260806-govb0-b35-review-r2（重派）
#   20260806-govb0-b35-stamp-r1     20260806-govb0-b4-impl-r1
#
# 誠實邊界：只驗**格式**，不驗語意（無法阻止把 impl 輪標成 review）。
#   擋的是「名字長得像、指錯對象」這類意外，不防蓄意誤標。
set -u

usage() {
  echo "用法: bash scripts/session_name_check.sh --session <name> [--task-id <id>]" >&2
  echo "      bash scripts/session_name_check.sh --explain   # 印規約" >&2
}

KIND_RE='impl|review|stamp|consult|fix'
SESSION_RE="^[0-9]{8}-[a-z0-9]+-(b[0-9]+|x)-(${KIND_RE})-r[0-9]+$"

session=""
task_id=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --session)  [ "$#" -ge 2 ] || { usage; exit 2; }; session="$2"; shift 2 ;;
    --task-id)  [ "$#" -ge 2 ] || { usage; exit 2; }; task_id="$2"; shift 2 ;;
    --explain)  sed -n '2,30p' "$0"; exit 0 ;;
    *) usage; exit 2 ;;
  esac
done

[ -n "${session}" ] || { usage; exit 2; }

rc=0

if ! printf '%s' "${session}" | grep -Eq "${SESSION_RE}"; then
  echo "ERROR: session 不符命名規約: ${session}" >&2
  echo "  應為 <YYYYMMDD>-<epic>-<batch>-<kind>-r<N>" >&2
  echo "  kind ∈ {impl, review, stamp, consult, fix}；batch 為 b<數字> 或 x；r<N> 必填" >&2
  echo "  例: 20260806-govb0-b35-review-r1" >&2
  # 常見錯誤指名
  if printf '%s' "${session}" | grep -Eq -- '-(review|stamp|fix|impl|consult)[0-9]+$'; then
    echo "  🔴 偵測到裸數字後綴（如 -review2）：重派請改用 -r2，" >&2
    echo "     否則看不出是『第二次派』還是『第二個主題』。" >&2
  fi
  rc=1
fi

if [ -n "${task_id}" ]; then
  expect="$(printf '%s' "${session}" | tr 'a-z' 'A-Z')"
  if [ "${task_id}" != "${expect}" ]; then
    echo "ERROR: task-id 須為 session 的大寫形式" >&2
    echo "  session=${session}" >&2
    echo "  期望 task-id=${expect}" >&2
    echo "  實際 task-id=${task_id}" >&2
    echo "  理由：兩者不同步時，audit 與收斂檔要靠人眼對應 ⇒ 正是本規約要消除的摩擦。" >&2
    rc=1
  fi
fi

[ "${rc}" -eq 0 ] && echo "[session_name] ✓ ${session}${task_id:+ / ${task_id}}"
exit "${rc}"
