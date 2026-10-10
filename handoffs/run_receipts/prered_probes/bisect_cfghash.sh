#!/bin/zsh
# bisect：凍結設定之 config_hash 首次偏離 1dbe534e… 之 commit。用法：zsh bisect_cfghash.sh <scratch> <good> <bad>
S=${1:?scratch}; GOOD=${2:?good}; BAD=${3:?bad}
REPO=/Users/louis/Desktop/quantitative_trading_system
WT=$S/wt_bisect
git -C $REPO worktree remove --force $WT > /dev/null 2>&1
git -C $REPO worktree add -f --detach $WT $BAD > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
mkdir -p $WT/data_cache/feature_klines
ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
ln -s $REPO/venv $WT/venv
cat > $S/bisect_cfg_step.sh <<EOF
#!/bin/zsh
cd $WT
env NUMBA_CACHE_DIR=$S/numba_bisect venv/bin/python $REPO/handoffs/run_receipts/prered_probes/cfghash_step.py > $S/bisect_cfg_last.log 2>&1
EOF
cd $WT
git bisect start $BAD $GOOD > /dev/null
git bisect run zsh $S/bisect_cfg_step.sh > $S/bisect_cfg_run.log 2>&1
grep -E "is the first bad commit" -A3 $S/bisect_cfg_run.log | head -4
git bisect reset > /dev/null 2>&1
