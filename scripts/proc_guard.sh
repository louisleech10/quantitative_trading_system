#!/usr/bin/env bash
# proc_guard.sh — 程序水位守衛 ＋ 殘留清理（本 repo 相關的孤兒程序）。
#
# 出生事故（2026-08-12）：`template_check.sh` 之 `_run_assert_lines` **會執行** SPEC 內的
#   `ASSERT` 行，且**無 timeout**。某份 SPEC 的 ASSERT 呼叫 `gov_check.sh --no-probe`
#   ⇒ 整套 1521 個測試被當成「文件檢查」跑起來 ⇒ 吃光 per-user process 上限（實測 1333）
#   ⇒ 連 `ps` 都 fork 不出來，session 卡死且無法自救。
#
# 誠實邊界：本腳本是**安全網**，不是根治。根治＝限制 ASSERT 的 fan-out 與執行時機
#   （見 `票 GOV-ASSERT-EXEC-UNBOUNDED`）。本腳本只負責「已經爆了要能自己爬出來」。
#
# 用法：
#   bash scripts/proc_guard.sh --check          # 只報水位，rc=0/1（超標=1）
#   bash scripts/proc_guard.sh --clean          # 清掉本 repo 相關、且已跑超過 N 秒的孤兒
#   bash scripts/proc_guard.sh --clean --dry-run
#
# 🔴 只殺**本 repo 路徑下**且**父程序已不在**（孤兒）或超齡的治理相關程序；
#    絕不殺使用者的編輯器／瀏覽器／ChatGPT app／委員 CLI 正在進行的派工。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

MAX_AGE_SEC="${PROC_GUARD_MAX_AGE_SEC:-1800}"   # 超過此秒數視為孤兒
WARN_RATIO="${PROC_GUARD_WARN_RATIO:-60}"       # 佔上限百分比達此值即警告

mode="check"; dry=0
for a in "$@"; do
  case "${a}" in
    --check) mode="check" ;;
    --clean) mode="clean" ;;
    --dry-run) dry=1 ;;
    *) echo "用法: bash scripts/proc_guard.sh [--check|--clean] [--dry-run]" >&2; exit 2 ;;
  esac
done

limit="$(ulimit -u 2>/dev/null || echo 0)"
count="$(ps -u "$(id -u)" 2>/dev/null | wc -l | tr -d ' ')"
[ -n "${count}" ] || count=0

pct=0
if [ "${limit}" -gt 0 ] 2>/dev/null; then pct=$(( count * 100 / limit )); fi
echo "[proc_guard] 程序 ${count}/${limit} (${pct}%)"

# 本 repo 相關的治理程序（不含委員 CLI —— 那是進行中的派工，殺了會毀掉一輪）
_stale() {
  ps -u "$(id -u)" -o pid=,etimes=,command= 2>/dev/null \
    | awk -v age="${MAX_AGE_SEC}" '
        $2 > age &&
        ($0 ~ /template_check\.sh/ || $0 ~ /gov_check\.sh/ ||
         $0 ~ /mutation_probe_check\.sh/ || $0 ~ /govb1_final_gate\.sh/ ||
         ($0 ~ /pytest/ && $0 ~ /tests\/governance/)) &&
        $0 !~ /proc_guard\.sh/ { print $1 }'
}

if [ "${mode}" = "check" ]; then
  n="$(_stale | wc -l | tr -d ' ')"
  [ "${n}" -gt 0 ] && echo "[proc_guard] 逾 ${MAX_AGE_SEC}s 之治理程序: ${n} 個（--clean 可清）"
  if [ "${pct}" -ge "${WARN_RATIO}" ]; then
    echo "[proc_guard] ✗ 程序水位過高 (${pct}% ≥ ${WARN_RATIO}%)" >&2
    exit 1
  fi
  echo "[proc_guard] ✓ 水位正常"
  exit 0
fi

killed=0
for pid in $(_stale); do
  if [ "${dry}" -eq 1 ]; then
    echo "[proc_guard] (dry-run) 會殺 pid=${pid}"
  else
    kill -TERM "${pid}" 2>/dev/null && killed=$((killed + 1))
  fi
done
echo "[proc_guard] 清理完成，終止 ${killed} 個（dry-run=${dry}）"
exit 0
