#!/bin/zsh
# PRE-RED Task 2.0（多週期 2247c394 逐欄）：於 2247c394^ 與 2247c394 各跑 multi_cols.py（串行，看門狗包住）後比對。
# 用法：zsh multi_cols_pair.sh <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
for c in 2247c394^ 2247c394; do
  C=$(git -C $REPO rev-parse --short=8 "$c")
  WT=$S/wt_$C
  if [ ! -d "$WT" ]; then
    git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed $C"; exit 2; }
    mkdir -p $WT/data_cache/feature_klines
    ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
    ln -s $REPO/venv $WT/venv
  fi
  (cd $WT && zsh $P/watch_run.sh $S/watch_mcols_$C.log -- env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$C venv/bin/python $P/multi_cols.py $S/mcols_$C.json > $S/mcols_$C.log 2>&1)
  echo "$c ($C) rc=$? $(tail -1 $S/mcols_$C.log | cut -c1-160)"
done
$REPO/venv/bin/python $P/multi_cols.py compare $S/mcols_d6de3ba6.json $S/mcols_2247c394.json 'BETA|CORREL|Klinger|ForceIndex'
