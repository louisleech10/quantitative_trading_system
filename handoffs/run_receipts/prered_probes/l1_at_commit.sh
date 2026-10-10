#!/bin/zsh
# PRE-RED：於指定 commit 之隔離 worktree 跑 l1_components.py。
# 用法：zsh l1_at_commit.sh <commit> <scratch dir>   → 產 <scratch>/l1_<commit>.json
set -u
C=${1:?commit}
S=${2:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
WT=$S/wt_$C
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
mkdir -p $S/numba_$C
cd $WT
env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $REPO/handoffs/run_receipts/prered_probes/l1_components.py $S/l1_$C.json > $S/l1_$C.log 2>&1
rc=$?
echo "commit=$C probe_rc=$rc $(tail -1 $S/l1_$C.log)"
exit $rc
