#!/bin/bash
# 用法：run_nodes.sh <node 清單> <log>；清單為空即拒跑（防無參數跑全套）
LIST="$1"; LOG="$2"
cd /Users/louis/Desktop/quantitative_trading_system || exit 9
NODES=$(cat "$LIST")
[ -z "$NODES" ] && { echo "EMPTY LIST, refuse" > "$LOG"; exit 8; }
start=$(date +%s)
venv/bin/python -m pytest -q -p no:cacheprovider $NODES -rfEX > "$LOG" 2>&1
rc=$?
echo "PYTEST_RC=$rc ELAPSED=$(( $(date +%s) - start ))" >> "$LOG"
