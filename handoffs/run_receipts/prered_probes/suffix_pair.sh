#!/bin/zsh
# PRE-RED：兩趟尾段比對。用法：zsh suffix_pair.sh <scratch> <新 commit sha8> <舊 commit sha8>
# 兩者之 worktree 須已由 full_at_commits.sh 建好（$S/wt_<sha8>）。
S=${1:?scratch}; NEW=${2:?new}; OLD=${3:?old}
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes/full_suffix.py
(cd $S/wt_$NEW && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$NEW venv/bin/python $P out $S/suffix_$NEW.json > $S/suffix_out_$NEW.log 2>&1)
echo "pass1 rc=$? $(tail -1 $S/suffix_out_$NEW.log | cut -c1-300)"
(cd $S/wt_$OLD && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$OLD venv/bin/python $P in $S/suffix_$NEW.json $S/suffix_cmp_${OLD}_${NEW}.json > $S/suffix_in_$OLD.log 2>&1)
echo "pass2 rc=$? $(tail -1 $S/suffix_in_$OLD.log | cut -c1-600)"
