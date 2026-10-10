#!/bin/zsh
# PRE-RED：FF 既有紅（含 frame 二支以確認狀態）於 HEAD 單組串行重跑
S=${1:?scratch dir}
cd /Users/louis/Desktop/quantitative_trading_system
venv/bin/python -m pytest -p no:cacheprovider -o log_cli=false --log-level=WARNING -rfE --tb=short \
  tests/feature_engineering/test_failopen_contract.py::test_l1_baseline_hash_matches_frozen \
  tests/feature_engineering/test_failopen_contract.py::test_required_fail_returns_result \
  tests/feature_engineering/test_failopen_correctness.py::test_v3_healthy_full_run_matches_frozen_baseline \
  tests/feature_engineering/test_failopen_correctness.py::test_v3_ethusdt_1h_matches_frozen_baseline \
  tests/feature_engineering/test_failopen_correctness.py::test_v3_multi_tf_btc_matches_frozen_baseline \
  tests/feature_engineering/test_failopen_correctness.py::test_v7_cgsa_resume_matches_fresh \
  tests/feature_engineering/test_failopen_layers.py::test_layer_golden_matches_baseline \
  tests/test_cgsa_resume.py::test_cgsa_config_hash_passed_correctly \
  tests/api/test_batch_alias.py::test_patch_batch_alias_deleting_returns_409 \
  --durations=0 > $S/ff9_head.log 2>&1
echo "pytest_rc=$?" >> $S/ff9_head.log
