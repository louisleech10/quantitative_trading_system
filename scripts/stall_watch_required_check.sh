#!/usr/bin/env bash
# Stop hook：有子代理在外（近 2 小時有寫入、尾端無 SubagentHandback）卻沒開 agent_stall_watch ⇒ 擋下結束回合。
# 子代理紀錄＝<transcript 去 .jsonl>/subagents/agent-*.jsonl（meta.json 之 finished 於「等自己背景工作」時亦為 true，不可用）。
# 出處：2026-11-02 路 H3 排隊放行後未被喚醒、空轉 3.5 小時；使用者：「不準靠紀律或記憶解決」「Hook也是算機械吧」。
set -u
tp="$(jq -r '.transcript_path // empty' 2>/dev/null || true)"
[ -n "$tp" ] || exit 0
sub="${tp%.jsonl}/subagents"
[ -d "$sub" ] || exit 0
out=()
while IFS= read -r f; do
  tail -c 30000 "$f" | grep -q '"name":"SubagentHandback"' || out+=("$f")
done < <(find "$sub" -name 'agent-*.jsonl' -mmin -120 2>/dev/null)
[ "${#out[@]}" -gt 0 ] || exit 0
ps -ax -o command | grep -v grep | grep -q "agent_stall_watch.sh" && exit 0
{
  echo "【子代理無人監看】仍有子代理在外，卻沒有背景跑停滯監看："
  for f in "${out[@]}"; do echo "  · $f"; done
  echo "  請以 run_in_background 跑：bash scripts/agent_stall_watch.sh ${out[*]}"
} >&2
exit 2
