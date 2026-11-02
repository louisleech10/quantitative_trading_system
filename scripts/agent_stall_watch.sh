#!/usr/bin/env bash
# 子代理停滯監看（2026-11-02 使用者要求；事故：路 H3 排隊放行後未被喚醒，空轉 3.5 小時）。
# 用法：bash scripts/agent_stall_watch.sh <子代理紀錄檔>... （主委以 run_in_background 跑；路徑由 Stop hook stall_watch_required_check.sh 列出）
# 判準：任一受監看紀錄檔逾 STALL_SEC（預設 900）秒無新寫入且無重型跑，或逾 STALL_HARD_SEC（預設 3600）秒無新寫入
#       （不論有無重型跑）⇒ 印出並退出（喚醒主委）。
# 受監看檔皆不存在或皆已交件（scripts/subagent_delivered.sh）⇒ 退出。不 kill、不改任何檔。
set -u
STALL_SEC="${STALL_SEC:-900}"
# 絕對上限（ICPERF SPEC v5.59 (af)）：全機他工作之重型行程（含其他 session）最多把告警延後到此
STALL_HARD_SEC="${STALL_HARD_SEC:-3600}"
[ "$#" -ge 1 ] || { echo "用法：$0 <output 檔>..." >&2; exit 2; }
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1"; }  # mtime 跨平台：GNU 先
while :; do
  sleep "${POLL_SEC:-60}"
  now=$(date +%s); alive=0
  heavy=$(ps -ax -o command | grep -E "pytest|icperf_|run_watched|ic_analysis" | grep -cv grep)
  for f in "$@"; do
    [ -f "$f" ] || continue
    bash "$(dirname "$0")/subagent_delivered.sh" "$f" && continue  # 已交件（判準見 subagent_delivered.sh）
    alive=1; age=$(( now - $(mtime "$f") ))
    if { [ "$heavy" -eq 0 ] && [ "$age" -ge "$STALL_SEC" ]; } || [ "$age" -ge "$STALL_HARD_SEC" ]; then
      echo "STALL: $f 已 ${age}s 無新寫入（重型行程 ${heavy} 個；上限 ${STALL_HARD_SEC}s 不論有無重型跑）⇒ 查證後 SendMessage 叫它續做"; exit 0
    fi
  done
  [ "$alive" -eq 1 ] || { echo "DONE: 受監看子代理皆已交件或不存在"; exit 0; }
done
