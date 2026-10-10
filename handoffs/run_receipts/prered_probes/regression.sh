#!/bin/zsh
# PRE-RED §V 回歸（已核模式）：逐組串行、各自 log。用法：zsh regression.sh <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
cd $REPO
F=tests/feature_engineering/test_failopen_correctness.py
NODES=($(grep -E "^def test_" $F | sed -E 's/^def (test_[a-z0-9_]+).*/\1/' | grep -v '^test_v3_multi_tf_btc_matches_frozen_baseline$' | sed "s|^|$F::|"))
run() {  # $1=name  rest=paths
  local n=$1; shift
  venv/bin/python -m pytest -q -p no:cacheprovider -o log_cli=false --log-level=WARNING -rfE --tb=short "$@" > $S/reg_$n.log 2>&1
  echo "$n rc=$? $(grep -E '[0-9]+ (passed|failed)' $S/reg_$n.log | tail -1 | tr -d '=')"
  grep -E "^(FAILED|ERROR) " $S/reg_$n.log | sed -E 's/ - .*//'
}
run gov tests/governance/test_mutation_scope_extension.py tests/governance/test_todofmt_sample_fftfmeta.py tests/governance/test_todofmt_constitution_sync.py tests/governance/test_prered_allowed_red.py tests/governance/test_redispatch.py
run api tests/api/test_batch_alias.py tests/test_cgsa_resume.py
run contract_layers tests/feature_engineering/test_failopen_contract.py tests/feature_engineering/test_failopen_layers.py
run correctness14 $NODES
run producer tests/feature_engineering/test_failopen_producer.py
echo done
