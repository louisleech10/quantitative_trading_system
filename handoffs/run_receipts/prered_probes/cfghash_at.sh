#!/bin/zsh
# 於各 commit 印凍結設定之 config_hash。用法：zsh cfghash_at.sh <scratch> <commit...>
S=${1:?scratch}; shift
REPO=/Users/louis/Desktop/quantitative_trading_system
for c in "$@"; do
  C=$(git -C $REPO rev-parse --short=8 "$c")
  WT=$S/wt_$C
  if [ ! -d "$WT" ]; then
    git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1
    mkdir -p $WT/data_cache/feature_klines
    ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
    ln -s $REPO/venv $WT/venv
  fi
  out=$(cd $WT && env NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $REPO/handoffs/run_receipts/prered_probes/cfghash_step.py 2>/dev/null | tail -1)
  echo "$c ($C) $out"
  git -C $REPO worktree remove --force $WT > /dev/null 2>&1
done
