#!/bin/zsh
# PRE-RED：依序於各 commit 之 worktree 跑 full_record.py（串行）。
# 用法：zsh full_at_commits.sh <scratch> <commit...>  → <scratch>/full_<sha8>.json；每行印摘要
S=${1:?scratch}; shift
SYM=${PRERED_SYMBOL:-BTCUSDT}; TF=${PRERED_TF:-12h}; TAG=${SYM}_${TF}
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
  mkdir -p $S/numba_$C
  OUT=full_$C; [ "$TAG" != "BTCUSDT_12h" ] && OUT=full_${TAG}_$C
  (cd $WT && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $REPO/handoffs/run_receipts/prered_probes/full_record.py $S/$OUT.json $SYM $TF > $S/$OUT.log 2>&1)
  echo "$c ($C) $TAG rc=$? $(tail -1 $S/$OUT.log | cut -c1-200)"
done
