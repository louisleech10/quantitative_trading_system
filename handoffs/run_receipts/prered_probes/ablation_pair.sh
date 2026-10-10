#!/bin/zsh
# PRE-RED Task 2.0：新版（d229336e）→ 舊版（d229336e^）消融，依序串行。worktree 須已存在（$S/wt_<sha8>）。
# 用法：zsh ablation_pair.sh <scratch> [symbol] [tf]
S=${1:?scratch}; SYM=${2:-BTCUSDT}; TF=${3:-12h}
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes
NEW=d229336e; OLD=1cbc93f4
(cd $S/wt_$NEW && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$NEW venv/bin/python $P/ablation.py new $S/abl_new_${SYM}_${TF} $SYM $TF > $S/abl_new_${SYM}_${TF}.log 2>&1)
echo "new rc=$? $(tail -1 $S/abl_new_${SYM}_${TF}.log | cut -c1-200)"
(cd $S/wt_$OLD && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_$OLD venv/bin/python $P/ablation.py old $S/abl_old_${SYM}_${TF} $S/abl_new_${SYM}_${TF}.json > $S/abl_old_${SYM}_${TF}.log 2>&1)
echo "old rc=$? $(tail -1 $S/abl_old_${SYM}_${TF}.log | cut -c1-200)"
venv/bin/python $P/ablation_classify.py $S/abl_new_${SYM}_${TF} $S/abl_old_${SYM}_${TF} $S/abl_cls_${SYM}_${TF}.json
