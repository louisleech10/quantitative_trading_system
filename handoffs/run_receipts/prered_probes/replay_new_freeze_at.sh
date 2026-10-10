#!/bin/zsh
# PRE-RED Task 2.4 邊界①：於舊 commit 之 worktree 以「新版」凍結腳本重放指定單元，輸出至 <scratch>/replay_<sha8>/baseline.json
# 用法：zsh replay_new_freeze_at.sh <scratch> <commit> <units>
S=${1:?scratch}; c=${2:?commit}; U=${3:?units}
REPO=/Users/louis/Desktop/quantitative_trading_system
C=$(git -C $REPO rev-parse --short=8 "$c")
WT=$S/wt_$C
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
cp $REPO/scripts/freeze_failopen_baseline.py $WT/scripts/freeze_failopen_baseline.py
OUT=$S/replay_$C
(cd $WT && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python scripts/freeze_failopen_baseline.py --units "$U" --out-dir $OUT > $S/replay_$C.log 2>&1)
echo "rc=$? out=$OUT/baseline.json"
