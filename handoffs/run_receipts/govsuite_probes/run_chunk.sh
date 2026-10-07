#!/bin/bash
# 用法：run_chunk.sh <chunk檔> <log檔>；清單為空即拒跑（防無參數跑全套）
LIST="$1"; LOG="$2"
cd /Users/louis/Desktop/quantitative_trading_system || exit 9
FILES=$(cat "$LIST")
[ -z "$FILES" ] && { echo "EMPTY LIST, refuse" > "$LOG"; exit 8; }
start=$(date +%s)
venv/bin/python -m pytest -q -p no:cacheprovider $FILES \
  --deselect tests/governance/test_govb1_contract_matrix.py::test_r6_u1u2u4_g7_worktree_space_quote_paths \
  -rfEX > "$LOG" 2>&1
rc=$?
echo "PYTEST_RC=$rc ELAPSED=$(( $(date +%s) - start ))" >> "$LOG"
