#!/bin/zsh
# PRE-RED：於 worktree 匯出某層全部欄陣列。用法：zsh dump_layer.sh <scratch> <sha8> <layer>
S=${1:?scratch}; C=${2:?sha}; L=${3:?layer}
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes/full_suffix.py
(cd $S/wt_$C && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $P dump $L $S/dump_${L}_$C.npz > $S/dump_${L}_$C.log 2>&1)
echo "rc=$? $(tail -1 $S/dump_${L}_$C.log)"
