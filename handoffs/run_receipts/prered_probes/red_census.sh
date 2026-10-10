#!/bin/zsh
# PRE-RED Task 3.1：逐檔串行跑，彙整失敗／錯誤之 node id（供允許仍紅清單）。用法：zsh red_census.sh <scratch> <檔...>
S=${1:?scratch}; shift
REPO=/Users/louis/Desktop/quantitative_trading_system
cd $REPO
: > $S/red_census.txt
for f in "$@"; do
  log=$S/census_${${f:t}%.py}.log
  venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING -rfEs --tb=no "$f" > $log 2>&1
  echo "## $f rc=$? $(grep -E '[0-9]+ (passed|failed|error|skipped)' $log | tail -1 | tr -d '=')" >> $S/red_census.txt
  grep -E "^(FAILED|ERROR) " $log | sed -E 's/ - .*//' >> $S/red_census.txt
done
echo done >> $S/red_census.txt
