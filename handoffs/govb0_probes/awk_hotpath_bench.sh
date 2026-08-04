#!/usr/bin/env bash
# awk_hotpath_bench.sh — 量測 gate_check.sh 熱路徑加入一次 awk 的成本。
# 對照組：現行做法（grep 一次）vs 新做法（awk 剝引號 + grep）。各跑 200 次取總時間。
# 出處：CODEX-R3-P0-02 要求「awk 須附效能 receipt」。唯讀。
set -u

CMD='git commit -m "fix: something
codex 並獨立重跑探針確認
done" && bash scripts/x.sh'

N=200

strip_awk() {
  printf '%s' "$1" | awk '
    BEGIN{ inq=0; q="" }
    {
      line=""; n=length($0)
      for(i=1;i<=n;i++){
        c=substr($0,i,1)
        if(inq){ if(c==q){ inq=0; q="" } }
        else { if(c=="\"" || c=="'\''"){ inq=1; q=c } else line=line c }
      }
      print line
    }'
}

RE='(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]'

echo "N=$N 次，指令長度=$(printf '%s' "$CMD" | wc -c | tr -d ' ') bytes"

t0=$(date +%s)
i=0; while [ $i -lt $N ]; do
  printf '%s' "$CMD" | grep -Eq "$RE" || true
  i=$((i+1))
done
t1=$(date +%s)
echo "A. 現行（僅 grep）        : $((t1-t0)) 秒 / $N 次 = $(( (t1-t0)*1000 / N )) ms 每次"

t2=$(date +%s)
i=0; while [ $i -lt $N ]; do
  printf '%s' "$(strip_awk "$CMD")" | grep -Eq "$RE" || true
  i=$((i+1))
done
t3=$(date +%s)
echo "B. 新做法（awk + grep）   : $((t3-t2)) 秒 / $N 次 = $(( (t3-t2)*1000 / N )) ms 每次"

echo
echo "差額 = $(( (t3-t2) - (t1-t0) )) 秒 / $N 次 = $(( ((t3-t2)-(t1-t0))*1000 / N )) ms 每次工具呼叫"
echo "對照：CLAUDE.md 記載權限分類器每次 2300-3000 ms；正常工具呼叫約 80 ms。"
