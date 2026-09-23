#!/usr/bin/env bash
# 偵察：write guard 路徑中，各 bash 函式發出之外部指令數（xtrace 以 FUNCNAME 標註，不計時）。
set -u
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
out="$(dirname "$0")/prof_func.log"
PS4='+|${FUNCNAME[0]:-main}| ' bash -x scripts/gen_fact_key_blocks.sh --check > /dev/null 2> "${out}"
echo "check rc=$?"
LC_ALL=C awk -F'|' '
  /^\++\|/ {
    fn=$2; cmd=$3; sub(/^ +/, "", cmd); split(cmd, w, " "); c=w[1]
    if (c ~ /^(jq|tr|wc|grep|sort|awk|sed|git|comm|cut|head|tail|shasum|python3|cat|mktemp)$/) n[fn" "c]++
  }
  END { for (k in n) print n[k], k }' "${out}" | sort -rn | head -20
