#!/usr/bin/env bash
# 等待派工完成——**會偵測執行端死掉**,不像純 `until [ -f ... ]` 迴圈那樣無限空等。
#
# 為何存在(2026-07-29 實際發生兩次):
#   ①codex 撞 sandbox Rejected 後直接退出、沒寫產出檔 → 主委的 until 迴圈空等 47 分鐘才被發現
#   ②主委宣稱「進行中」但其實根本沒派 → 使用者問了才發現
#   純檔案存在檢查看不出「還在跑」與「已經死了」的差別。本腳本三態明確回報。
#
# 用法:
#   bash scripts/wait_for_dispatch.sh <out1.md> [out2.md ...] [--pattern <pgrep關鍵字>] [--timeout <秒>]
#
# rc: 0=全部產出完成 / 1=執行端已消失但產出不全(死掉) / 2=逾時 / 3=參數錯
set -uo pipefail

outs=(); pattern=""; timeout_s=3600
while [ $# -gt 0 ]; do
  case "$1" in
    --pattern) pattern="$2"; shift 2 ;;
    --timeout) timeout_s="$2"; shift 2 ;;
    *) outs+=("$1"); shift ;;
  esac
done
[ ${#outs[@]} -gt 0 ] || { echo "用法: $0 <out.md>... [--pattern X] [--timeout N]"; exit 3; }
[ -n "$pattern" ] || pattern="cx_run"

start=$(date +%s)
while :; do
  done_n=0
  for o in "${outs[@]}"; do [ -s "$o" ] && done_n=$((done_n+1)); done
  if [ "$done_n" -eq "${#outs[@]}" ]; then
    echo "DISPATCH COMPLETE: ${done_n}/${#outs[@]} 產出齊全"
    for o in "${outs[@]}"; do printf '  %s (%s bytes)\n' "$o" "$(wc -c < "$o" | tr -d ' ')"; done
    exit 0
  fi

  # ← 關鍵:執行端不在了但產出不全 = 死掉,不再空等
  if ! pgrep -f "$pattern" >/dev/null 2>&1; then
    sleep 5   # 寬限一次,避免抓在程序交棒的瞬間
    done_n=0; for o in "${outs[@]}"; do [ -s "$o" ] && done_n=$((done_n+1)); done
    if [ "$done_n" -eq "${#outs[@]}" ]; then echo "DISPATCH COMPLETE(尾聲): ${done_n}/${#outs[@]}"; exit 0; fi
    if ! pgrep -f "$pattern" >/dev/null 2>&1; then
      echo "DISPATCH DIED: 執行端程序已消失,但只有 ${done_n}/${#outs[@]} 個產出"
      for o in "${outs[@]}"; do
        if [ -s "$o" ]; then printf '  ✅ %s\n' "$o"
        else
          printf '  ❌ %s (未產出)\n' "$o"
          rl="${o%.md}.runlog"
          [ -f "$rl" ] && printf '     runlog 尾: %s\n' "$(tail -2 "$rl" | tr '\n' ' ' | cut -c1-160)"
        fi
      done
      exit 1
    fi
  fi

  now=$(date +%s)
  if [ $((now-start)) -ge "$timeout_s" ]; then
    echo "DISPATCH TIMEOUT: 逾 ${timeout_s}s,完成 ${done_n}/${#outs[@]}"; exit 2
  fi
  sleep 20
done
