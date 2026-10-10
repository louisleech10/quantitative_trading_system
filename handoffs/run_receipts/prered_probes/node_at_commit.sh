#!/bin/zsh
# PRE-RED：於指定 commit 之 worktree 單跑一個（可為重量）pytest 節點，記錄峰值記憶體。
# 用法：zsh node_at_commit.sh <scratch> <commit> <node>
S=${1:?scratch}; c=${2:?commit}; NODE=${3:?node}
REPO=/Users/louis/Desktop/quantitative_trading_system
C=$(git -C $REPO rev-parse --short=8 "$c")
WT=$S/wt_$C
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
L=$S/nodec_$C.log
(cd $WT && /usr/bin/time -l env NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python -m pytest -p no:cacheprovider -o log_cli=false --log-level=WARNING -q --tb=long "$NODE" > $L 2>&1)
echo "$c ($C) rc=$? $(grep -E '[0-9]+ (passed|failed)' $L | tail -1) $(grep -E 'peak memory footprint' $L)"
