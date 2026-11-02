#!/usr/bin/env bash
# 子代理是否已交件：最後一次 SubagentHandback 之後，該子代理沒有新的工具呼叫。
# 只看子代理自己的 assistant 訊息行；api-request-blob 是請求內容副本（含整段歷史），不算。
# 交件後被通知喚醒、只回文字者仍算已交件（2026-11-02 誤擋：原「末 3 行含交件」判準把它當成在外）；
# 交件後又呼叫工具（被 SendMessage 續派、開背景等候）⇒ 算在外。
# 用法：bash scripts/subagent_delivered.sh <子代理紀錄檔>；rc=0 已交件、rc=1 未交件或檔案不存在。
# 呼叫端：stall_watch_required_check.sh（Stop hook）、agent_stall_watch.sh。
set -u
f="${1:-}"
[ -f "$f" ] || exit 1
calls="$(jq -rR 'fromjson? // empty
  | select(.type != "api-request-blob" and (.message | type) == "object" and .message.role == "assistant")
  | .message.content | arrays | .[]
  | select(type == "object" and .type == "tool_use")
  | "\(input_line_number) \(.name)"' "$f" 2>/dev/null)"
last="$(printf '%s\n' "$calls" | awk '$2 == "SubagentHandback" { n = $1 } END { print n + 0 }')"
[ "$last" -gt 0 ] || exit 1
printf '%s\n' "$calls" | awk -v L="$last" '$1 > L { found = 1 } END { exit found ? 1 : 0 }'
