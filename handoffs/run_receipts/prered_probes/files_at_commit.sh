#!/bin/zsh
# PRE-RED 審碼 r1 後歸因：於指定 commit 之 worktree、以「現行（已刪舊 run）資料狀態之複本」跑指定測試檔，印失敗 node。
# 資料狀態固定為主樹現況（data_cache/features 複製、kline 唯讀連結），故 commit 間之差異只來自程式碼。
# 用法：zsh <本檔> <scratch> <commit> <測試檔...>
S=${1:?scratch}; c=${2:?commit}; shift 2
REPO=/Users/louis/Desktop/quantitative_trading_system
C=$(git -C $REPO rev-parse --short=8 "$c")
WT=$S/wtf_$C
git -C $REPO worktree add -f --detach $WT $C > /dev/null 2>&1 || { echo "worktree add failed $c"; exit 2; }
mkdir -p $WT/data_cache/feature_klines
ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
cp -R $REPO/data_cache/features $WT/data_cache/features
ln -s $REPO/venv $WT/venv
L=$S/filesat_$C.log
(cd $WT && env NUMBA_CACHE_DIR=$S/numba_f$C venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=no -rf "$@" > $L 2>&1)
echo "== $c ($C) $(tail -1 $L | tr -d '=')"
grep -E "^(FAILED|ERROR) " $L | sed -E 's/ - .*//'
git -C $REPO worktree remove --force $WT > /dev/null 2>&1
