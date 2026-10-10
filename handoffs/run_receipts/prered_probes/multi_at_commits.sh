#!/bin/zsh
# PRE-RED：依序於各 commit 之 worktree 跑 multi_record.py（串行）。用法：zsh multi_at_commits.sh <scratch> <commit...>
S=${1:?scratch}; shift
REPO=/Users/louis/Desktop/quantitative_trading_system
for c in "$@"; do
  C=$(git -C $REPO rev-parse --short=8 "$c")
  WT=$S/wt_$C
  if [ ! -d "$WT" ]; then
    git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "$c worktree add failed"; continue; }
    mkdir -p $WT/data_cache/feature_klines
    ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
    ln -s $REPO/venv $WT/venv
  fi
  (cd $WT && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $REPO/handoffs/run_receipts/prered_probes/multi_record.py $S/multi_$C.json > $S/multi_$C.log 2>&1)
  echo "$c ($C) rc=$? $(tail -1 $S/multi_$C.log | cut -c1-200)"
done
