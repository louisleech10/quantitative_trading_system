#!/bin/zsh
# correctness 檔除多週期外之節點，各自獨立行程串行跑（避免同行程記憶體累積被系統終止）。用法：zsh <本檔> <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
cd $REPO
F=tests/feature_engineering/test_failopen_correctness.py
for n in $(grep -E "^def test_" $F | sed -E 's/^def (test_[a-z0-9_]+).*/\1/' | grep -v '^test_v3_multi_tf_btc_matches_frozen_baseline$'); do
  zsh $P/one_node.sh $S each_$n "$F::$n" > /dev/null 2>&1
  echo "$n => $(grep -E '[0-9]+ (passed|failed|error)' $S/node_each_$n.log | tail -1 | tr -d '=') | peak $(grep -E 'peak memory' $S/node_each_$n.log | awk '{printf "%.2fGB", $1/1e9}') $(grep -E '^pytest_rc=' $S/node_each_$n.log)"
done
echo done
