#!/usr/bin/env bash
# 清理呆滯／孤兒的派工程序與殘留檔（使用者 2026-07-29 要求：維持派工與背景乾淨）
#
# 為何存在（本 session 實際發生過的三種髒法）：
#   ① 委員 CLI 撞外部容量限制（resource_exhausted / model at capacity）後留下半死程序
#   ② 舊式 nohup+& 啟動造成 harness 追蹤不到的孤兒（nohup 已被 settings.json deny 封死）
#   ③ 委員在 repo 內建 probe 目錄（handoffs/_probe_*）未自清
#
# 用法：
#   bash scripts/cleanup_stale_dispatch.sh            # 只報告，不動手
#   bash scripts/cleanup_stale_dispatch.sh --kill     # 砍掉超過門檻的程序 + 清 probe 殘留
#   bash scripts/cleanup_stale_dispatch.sh --kill --minutes 45
#
# 預設門檻 30 分鐘：正常一輪委員 2–10 分鐘；超過 30 分鐘幾乎都是卡住或半死。
set -uo pipefail
KILL=0; THRESH_MIN=30
while [ $# -gt 0 ]; do
  case "$1" in
    --kill) KILL=1; shift ;;
    --minutes) THRESH_MIN="$2"; shift 2 ;;
    *) echo "未知參數: $1"; exit 2 ;;
  esac
done

# etime 轉秒（格式 [[DD-]HH:]MM:SS）
_etime_sec() {
  printf '%s' "$1" | awk -F'[-:]' '{
    if (NF==4) print ($1*86400)+($2*3600)+($3*60)+$4;
    else if (NF==3) print ($1*3600)+($2*60)+$3;
    else print ($1*60)+$2;
  }'
}

echo "┌─ 派工衛生檢查  $(date '+%H:%M:%S')  門檻=${THRESH_MIN} 分鐘 ─────────"
stale=0; alive=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  pid=$(printf '%s' "$line" | awk '{print $1}')
  et=$(printf  '%s' "$line" | awk '{print $2}')
  sec=$(_etime_sec "$et")
  desc=$(printf '%s' "$line" | grep -oE '(cx_run\.sh [a-z]+|committee_run\.sh)' | head -1)
  [ -z "$desc" ] && desc="(委員 CLI)"
  if [ "$sec" -gt $((THRESH_MIN*60)) ]; then
    stale=$((stale+1))
    printf '│ 🔴 呆滯 pid=%-7s 已跑 %-10s %s\n' "$pid" "$et" "$desc"
    if [ "$KILL" = "1" ]; then
      kill -TERM "$pid" 2>/dev/null && printf '│     → 已送 TERM\n' || printf '│     → TERM 失敗(可能已結束)\n'
    fi
  else
    alive=$((alive+1))
    printf '│ 🟢 正常 pid=%-7s 已跑 %-10s %s\n' "$pid" "$et" "$desc"
  fi
done < <(ps -eo pid,etime,args | grep -iE 'cx_run\.sh|committee_run\.sh|cursor-agent|/grok |codex exec' | grep -v grep)

[ "$((stale+alive))" -eq 0 ] && echo "│ ⚪ 無任何委員程序"

# ── 呆滯／空轉的背景 shell（非委員 CLI）─────────────────
# 事故（2026-07-29，使用者發現）：主委為繞過 harness 的 sleep 限制寫了
#   `until [ "$(date +%s)" -gt "$(( $(date +%s) + 0 ))" ]; do :; done`
#   ——`X > X` 恆假 ⇒ **無限 busy-wait**，空轉 3 小時、吃 11.4% CPU，
#   且後面的重派永遠不會執行（主委當時誤以為它在等待）。
# ⇒ 只掃委員 CLI 不夠，**任何長時間高 CPU 的背景 shell 都要抓**。
echo "│ ── 背景 shell（非委員 CLI）──"
spin=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  pid=$(printf '%s' "$line" | awk '{print $1}')
  et=$(printf  '%s' "$line" | awk '{print $2}')
  cpu=$(printf '%s' "$line" | awk '{print $3}')
  sec=$(_etime_sec "$et")
  # 條件：跑超過門檻，且 CPU > 5%（空轉迴圈的特徵；正常等待的 shell 近 0%）
  cpu_int=${cpu%%.*}
  if [ "$sec" -gt $((THRESH_MIN*60)) ] && [ "${cpu_int:-0}" -gt 5 ]; then
    spin=$((spin+1))
    printf '│ 🔥 空轉 pid=%-7s 已跑 %-10s CPU=%s%%  ← 疑似 busy-wait 迴圈\n' "$pid" "$et" "$cpu"
    [ "$KILL" = "1" ] && { kill -TERM "$pid" 2>/dev/null && printf '│     → 已送 TERM\n'; }
  fi
done < <(ps -eo pid,etime,pcpu,args | grep -E '/bin/(ba|z)?sh -c' | grep -v grep)
[ "$spin" -eq 0 ] && echo "│ ✅ 無空轉背景 shell"

# ── repo 內 probe 殘留 ──────────────────────────────────
probes=$(ls -d handoffs/_probe_* handoffs/_narrowprobe_* handoffs/_np* 2>/dev/null || true)
if [ -n "$probes" ]; then
  n=$(printf '%s\n' "$probes" | grep -c . )
  printf '│ 🧹 repo 內 probe 殘留 %s 個\n' "$n"
  printf '%s\n' "$probes" | sed 's/^/│     /'
  if [ "$KILL" = "1" ]; then
    printf '%s\n' "$probes" | while read -r d; do [ -n "$d" ] && rm -rf "$d"; done
    echo "│     → 已清除"
  fi
else
  echo "│ ✅ 無 probe 殘留"
fi

echo "└──────────────────────────────────────────────────────────"
[ "$KILL" = "0" ] && [ "$stale" -gt 0 ] && echo "有 ${stale} 個呆滯程序；加 --kill 才會實際砍除。"
exit 0
