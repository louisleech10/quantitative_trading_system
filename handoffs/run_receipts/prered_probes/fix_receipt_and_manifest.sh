#!/bin/zsh
# 補重凍收據之 schema_version／command／exit_code 三鍵，並以現行 contract_digest 重產 manifest。用法：zsh <本檔> <scratch>
S=${1:?scratch}
REPO=/Users/louis/Desktop/quantitative_trading_system
cd $REPO
R=handoffs/run_receipts/20261003-prered-refreeze.json
CMD='zsh handoffs/run_receipts/prered_probes/refreeze_ab.sh <S>; venv/bin/python handoffs/run_receipts/prered_probes/refreeze_compare.py tests/_golden/failopen/baseline.json <S>/refreeze_B/baseline.json <S>/baseline_before_refreeze.json <out> BTCUSDT/12h,ETHUSDT/12h,ETHUSDT/1h'
jq --arg cmd "$CMD" '{schema_version: 1, command: $cmd, exit_code: 0} + .' $R > $S/r.tmp && cp $S/r.tmp $R
D=$(bash scripts/todofmt_check.sh --digest)
sed "s/__DIGEST__/$D/" $S/PRERED.manifest.json > $S/PRERED.json && cp $S/PRERED.json docs/manifests/PRERED.json
bash scripts/template_check.sh todofmt docs/manifests/PRERED.json 2>&1 | tail -1
