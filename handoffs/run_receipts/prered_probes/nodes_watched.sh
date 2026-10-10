#!/bin/zsh
# 逐節點各自行程、看門狗包住（磁碟剩 < 4GiB 即停）串行跑。用法：zsh <本檔> <scratch> <tag> <node...>
S=${1:?scratch}; TAG=${2:?tag}; shift 2
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
cd $REPO
for n in "$@"; do
  name=${TAG}_$(echo ${n##*::} | tr -c 'A-Za-z0-9_\n' '_')
  zsh $P/watch_run.sh $S/watch_$name.log -- /usr/bin/time -l venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=short "$n" > $S/node_$name.log 2>&1
  rc=$?
  echo "${n##*::} rc=$rc $(grep -E '[0-9]+ (passed|failed|error)' $S/node_$name.log | tail -1 | tr -d '=') | peak $(grep -E 'peak memory' $S/node_$name.log | awk '{printf "%.2fGB", $1/1e9}') $(grep -c WATCHDOG $S/watch_$name.log | sed 's/^0$//;s/^1$/WATCHDOG/')"
done
echo done
