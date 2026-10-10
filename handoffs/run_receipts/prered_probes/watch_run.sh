#!/bin/zsh
# PRE-RED Task 2.5：執行一個探針命令並每 5 秒取樣 RSS、swap、磁碟剩餘；剩餘 < 4 GiB 即終止探針（防換頁檔塞滿磁碟）。
# 用法：zsh watch_run.sh <取樣 log> -- <命令...>
LOG=${1:?log}; shift; [ "$1" = "--" ] && shift
"$@" &
PID=$!
echo "start pid=$PID $(date '+%F %T') cmd=$*" > $LOG
while kill -0 $PID 2>/dev/null; do
  free_kb=$(df -k /System/Volumes/Data | awk 'NR==2{print $4}')
  rss_kb=$(ps -o rss= -g $(ps -o pgid= -p $PID | tr -d ' ') 2>/dev/null | awk '{s+=$1} END{print s+0}')
  swap=$(sysctl -n vm.swapusage | awk '{print $6}')
  echo "$(date '+%T') rss_mb=$((rss_kb/1024)) swap_used=$swap disk_free_mb=$((free_kb/1024))" >> $LOG
  if [ "$free_kb" -lt 4194304 ]; then
    echo "$(date '+%T') WATCHDOG: disk_free < 4GiB，終止 pid=$PID" >> $LOG
    kill -TERM $PID; sleep 5; kill -KILL $PID 2>/dev/null
    break
  fi
  sleep 5
done
wait $PID; rc=$?
echo "end rc=$rc $(date '+%F %T')" >> $LOG
exit $rc
