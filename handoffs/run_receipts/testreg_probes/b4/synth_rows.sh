#!/usr/bin/env bash
# TESTREG b4：由 reconcile_build.sh 之 log 與各家交件檔，產 synth 群集表之列（處置預設「採納」、類別取委員自標）。
# 用法：bash synth_rows.sh <reconcile_build.log> <委員檔1> [<委員檔2> ...]
set -u
LOG="$1"; shift
TMP="$(mktemp)"
for f in "$@"; do
  grep -E "^## [A-Z]+-R[0-9]+-P[0-3]-[0-9]+|^\*\*類別" "$f" | paste - - | sed 's/^## //; s/\*\*類別\*\*: //'
done > "$TMP"
grep -E "^── |斷言前20字" "$LOG" | paste - - | sed 's/── //; s/   斷言前20字: /\t/' | awk -F'\t' '{print $1"\t"$3}' |
  awk -F'\t' 'NR==FNR{c[$1]=$2; next} {sev=$1; sub(/.*-P/,"P",sev); sub(/-.*/,"",sev); print "| "$2" | "sev" | "$1" | 採納 | "c[$1]" |"}' "$TMP" -
rm -f "$TMP"
