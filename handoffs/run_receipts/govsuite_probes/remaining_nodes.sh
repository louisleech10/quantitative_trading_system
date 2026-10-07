#!/bin/bash
# 用法：remaining_nodes.sh <檔清單> <輸出 node 清單> <已跑 log ...>
# 收集檔清單之全部 node id，扣掉各 log 中已有結果（PASSED/FAILED/ERROR/SKIPPED/XFAIL/XPASS）者
LIST="$1"; OUT="$2"; shift 2
cd /Users/louis/Desktop/quantitative_trading_system || exit 9
FILES=$(cat "$LIST")
[ -z "$FILES" ] && { echo "EMPTY LIST"; exit 8; }
S=$(dirname "$OUT")
venv/bin/python -m pytest --collect-only -qq -p no:cacheprovider $FILES 2>/dev/null \
  | grep "::" | sed 's/ .*//' | sort -u > "$S/_all_nodes.txt"
: > "$S/_done_nodes.txt"
for L in "$@"; do
  grep -E " (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)" "$L" | sed -E 's/ (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS).*//' >> "$S/_done_nodes.txt"
done
sort -u "$S/_done_nodes.txt" -o "$S/_done_nodes.txt"
comm -23 "$S/_all_nodes.txt" "$S/_done_nodes.txt" \
  | grep -v "test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths" > "$OUT"
echo "all=$(wc -l < "$S/_all_nodes.txt") done=$(wc -l < "$S/_done_nodes.txt") remaining=$(wc -l < "$OUT")"
