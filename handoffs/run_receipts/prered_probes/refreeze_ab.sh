#!/bin/zsh
# PRE-RED Task 2.4 ④：單週期三單元重凍（A＝golden、B＝獨立暫存目錄），串行、各自全新生成。用法：zsh refreeze_ab.sh <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
U=BTCUSDT/12h,ETHUSDT/12h,ETHUSDT/1h
cd $REPO
env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_refreeze venv/bin/python scripts/freeze_failopen_baseline.py --units $U > $S/refreeze_A.log 2>&1
echo "A rc=$?"
mkdir -p $S/refreeze_B
env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_refreeze venv/bin/python scripts/freeze_failopen_baseline.py --units $U --out-dir $S/refreeze_B > $S/refreeze_B.log 2>&1
echo "B rc=$?"
