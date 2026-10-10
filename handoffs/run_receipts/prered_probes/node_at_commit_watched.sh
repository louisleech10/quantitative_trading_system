#!/bin/zsh
# 於指定 commit 之 worktree 單跑節點（看門狗＋/usr/bin/time）。用法：zsh <本檔> <scratch> <commit> <node>
S=${1:?scratch}; c=${2:?commit}; NODE=${3:?node}
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
C=$(git -C $REPO rev-parse --short=8 "$c")
WT=$S/wt_$C
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
L=$S/nodecw_$C.log
(cd $WT && zsh $P/watch_run.sh $S/watch_nodecw_$C.log -- /usr/bin/time -l env NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=short "$NODE" > $L 2>&1)
echo "$c ($C) rc=$? $(grep -E '[0-9]+ (passed|failed)' $L | tail -1 | tr -d '=') | peak $(grep -E 'peak memory' $L | awk '{printf "%.2fGB", $1/1e9}') $(grep -c WATCHDOG $S/watch_nodecw_$C.log)"
git -C $REPO worktree remove --force $WT > /dev/null 2>&1
