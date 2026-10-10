#!/bin/zsh
# PRE-RED Task 2.4：五支單週期基準測試逐節點單跑（串行、各自 log）。用法：zsh five_baseline.sh <scratch> <tag>
S=${1:?scratch}; TAG=${2:?tag}
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes
for n in \
  tests/feature_engineering/test_failopen_contract.py::test_l1_baseline_hash_matches_frozen \
  tests/feature_engineering/test_failopen_contract.py::test_required_fail_returns_result \
  tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline \
  tests/feature_engineering/test_failopen_correctness.py::test_v3_healthy_full_run_matches_frozen_baseline \
  tests/feature_engineering/test_failopen_correctness.py::test_v3_ethusdt_1h_matches_frozen_baseline; do
  name=${TAG}_${n##*::}
  zsh $P/one_node.sh $S $name $n > /dev/null 2>&1
  echo "$n => $(grep -E '[0-9]+ (passed|failed)' $S/node_$name.log | tail -1 | sed 's/=//g') | $(grep -E 'drift|KeyError|AssertionError' $S/node_$name.log | head -1 | cut -c1-140)"
done
