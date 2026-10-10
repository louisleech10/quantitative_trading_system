#!/bin/zsh
# PRE-RED：於指定 commit 之 worktree 跑指定（輕量）pytest 節點。用法：zsh light_at_commit.sh <scratch> <commit> <node...>
S=${1:?scratch}; c=${2:?commit}; shift 2
REPO=/Users/louis/Desktop/quantitative_trading_system
C=$(git -C $REPO rev-parse --short=8 "$c")
WT=$S/wt_$C
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
(cd $WT && env NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python -m pytest -p no:cacheprovider -q --tb=line -o log_cli=false --log-level=WARNING "$@" > $S/light_$C.log 2>&1)
echo "$c ($C) pytest_rc=$? $(grep -E '[0-9]+ (passed|failed|error)' $S/light_$C.log | tail -1)"
