#!/bin/zsh
# PRE-RED：主工作樹單跑一個 pytest 節點（獨立 log，避免一支被砍連帶丟失其他支之訊息）
# 用法：zsh one_node.sh <scratch> <log 名> <node>
S=${1:?scratch}; N=${2:?name}; NODE=${3:?node}
cd /Users/louis/Desktop/quantitative_trading_system
/usr/bin/time -l venv/bin/python -m pytest -p no:cacheprovider -o log_cli=false --log-level=WARNING -q --tb=long "$NODE" > $S/node_$N.log 2>&1
echo "pytest_rc=$?" >> $S/node_$N.log
tail -1 $S/node_$N.log
grep -E "[0-9]+ (passed|failed)|maximum resident" $S/node_$N.log | tail -2
