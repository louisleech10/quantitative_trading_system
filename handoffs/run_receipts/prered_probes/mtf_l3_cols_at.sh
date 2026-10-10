#!/bin/zsh
# 於各 commit 跑 mtf_l3_cols.py。用法：zsh <本檔> <scratch> <commit...>
S=${1:?scratch}; shift
REPO=/Users/louis/Desktop/quantitative_trading_system
for c in "$@"; do
  C=$(git -C $REPO rev-parse --short=8 "$c")
  WT=$S/wt_$C
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
  (cd $WT && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $REPO/handoffs/run_receipts/prered_probes/mtf_l3_cols.py $S/mtfl3_$C.json 2>&1 | tail -1)
  git -C $REPO worktree remove --force $WT > /dev/null 2>&1
done
