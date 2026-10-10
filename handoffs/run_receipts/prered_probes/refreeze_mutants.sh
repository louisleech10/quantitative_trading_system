#!/bin/zsh
# PRE-RED §G④：重凍後 mutant（外掛經 PYTEST_ADDOPTS 帶入子行程重入之 pytest）。用法：zsh refreeze_mutants.sh <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
cd $REPO
run() {  # $1=plugin $2=node
  env PYTHONPATH=$P PYTEST_ADDOPTS="-p $1" venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING --tb=long "$2" > $S/mut_$1_${2##*::}.log 2>&1
  echo "$1 :: ${2##*::} rc=$? $(grep -oE 'L[1-6] canonical hash drift|must match frozen baseline|[0-9]+ (passed|failed)' $S/mut_$1_${2##*::}.log | sort -u | tr '\n' ' ')"
}
run mut_beta_input_plugin tests/feature_engineering/test_failopen_contract.py::test_l1_baseline_hash_matches_frozen
run mut_beta_input_plugin tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline
run mut_l3_scale_plugin tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline
