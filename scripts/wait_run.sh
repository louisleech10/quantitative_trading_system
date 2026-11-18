#!/usr/bin/env bash
# wait_run.sh — 重型跑之唯一等待程序（背景執行，結束即通知主控）：盯 run_watched 之 log，
# 出現下列任一行即印出該行並退出——
#   [run-watched] exit rc=…     （跑完）
#   [run-watched] stalled …     （卡死／記憶體，已留現場）
#   [watchdog] 牆鐘 … 逾預期 …   （超過估時：只告警，跑不停；主控收到後查原因再決定）
# 2026-11-14 事故：I7 全量 log 第 15512 行於 5,407 秒已寫「逾預期」，主控之等待只盯 exit 行，11 小時後才發現。
# 用法：bash scripts/wait_run.sh <log 路徑> [--after-overrun]     rc：0＝exit 行、3＝逾預期、4＝stalled
#   --after-overrun：已收過逾預期告警並決定續跑時，再起等待程序只等 exit／stalled。
# 不設時間上限（NOCAP）：以輪詢 log 內容判定，跑多久都等。
set -u
log="${1:?用法：wait_run.sh <log> [--after-overrun]}"
seen_over="${2:-}"
# 路徑打錯（目錄不存在）⇒ 立即報錯，不空等（2026-11-14 主委以錯相對路徑起等待程序即無限等）
if [ ! -d "$(dirname "$log")" ]; then echo "wait_run: log 目錄不存在：$(dirname "$log")" >&2; exit 2; fi
while :; do
  if [ -f "$log" ]; then
    # 逾預期優先（未帶 --after-overrun 時）：同一 log 兼有逾預期與 exit 時，不得以 exit 掩蓋逾預期
    line="$(grep -m1 -E '\[watchdog\] 牆鐘 .*逾預期' "$log" 2>/dev/null)"
    if [ -n "$line" ] && [ -z "$seen_over" ]; then echo "$line"; exit 3; fi
    line="$(grep -m1 -E '^\[run-watched\] stalled' "$log" 2>/dev/null)"
    if [ -n "$line" ]; then echo "$line"; exit 4; fi
    line="$(grep -m1 -E '^\[run-watched\] exit rc=' "$log" 2>/dev/null)"
    if [ -n "$line" ]; then echo "$line"; exit 0; fi
  fi
  sleep 30
done
