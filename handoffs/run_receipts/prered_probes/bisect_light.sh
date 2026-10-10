#!/bin/zsh
# PRE-RED：在專用 worktree 內 git bisect run 一個輕量 pytest 節點。
# 用法：zsh bisect_light.sh <scratch> <good> <bad> <node>
# 測試檔以 bad 版本（＝現行）之內容覆蓋到每個被測 commit，量的是「生產碼變化」使該斷言首紅之處；
# 跑完還原測試檔再交給 bisect。skip（rc 125）：該 commit 無法收集。
S=${1:?scratch}; GOOD=${2:?good}; BAD=${3:?bad}; NODE=${4:?node}
REPO=/Users/louis/Desktop/quantitative_trading_system
WT=$S/wt_bisect
TESTFILE=${NODE%%::*}
git -C $REPO show $BAD:$TESTFILE > $S/bisect_testfile.py
if [ ! -d "$WT" ]; then
  git -C $REPO worktree add -f --detach $WT $BAD > /dev/null 2>&1 || { echo "worktree add failed"; exit 2; }
  mkdir -p $WT/data_cache/feature_klines
  ln -s $REPO/data_cache/feature_klines/kline_cache.h5 $WT/data_cache/feature_klines/kline_cache.h5
  ln -s $REPO/venv $WT/venv
fi
cat > $S/bisect_step.sh <<EOF
#!/bin/zsh
cd $WT
cp $S/bisect_testfile.py $TESTFILE
env NUMBA_CACHE_DIR=$S/numba_bisect venv/bin/python -m pytest -p no:cacheprovider -q --tb=no -o log_cli=false --log-level=WARNING $NODE > $S/bisect_step.log 2>&1
rc=\$?
git checkout -q -- $TESTFILE 2>/dev/null
if [ \$rc -eq 0 ]; then exit 0; elif [ \$rc -eq 1 ]; then exit 1; else exit 125; fi
EOF
cd $WT
git bisect reset > /dev/null 2>&1
git bisect start $BAD $GOOD > /dev/null
git bisect run zsh $S/bisect_step.sh > $S/bisect_run.log 2>&1
grep -E "is the first bad commit|There are only 'skip'ped" -A1 $S/bisect_run.log | head -3
git bisect reset > /dev/null 2>&1
