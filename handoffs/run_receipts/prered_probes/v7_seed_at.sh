#!/bin/zsh
# PRE-RED：於既有 worktree 跑 v7 種子 run 探針。用法：zsh v7_seed_at.sh <scratch> <sha8>
S=${1:?scratch}; C=${2:?sha}
(cd $S/wt_$C && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python /Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes/v7_seed_manifest.py > $S/v7seed_$C.log 2>&1)
echo "$C rc=$?"
grep -E "L7manifest|result_status|Error" $S/v7seed_$C.log | grep -v "INFO\|DEBUG" | cut -c1-900
