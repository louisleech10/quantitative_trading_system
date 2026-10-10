#!/bin/zsh
# PRE-RED：於主工作樹（HEAD）跑 L1 五分量探針並與凍結基準並列
S=${1:?scratch}
cd /Users/louis/Desktop/quantitative_trading_system
mkdir -p $S/numba_head
env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$S/numba_head venv/bin/python handoffs/run_receipts/prered_probes/l1_components.py $S/l1_HEAD.json > $S/l1_HEAD.log 2>&1
echo "probe_rc=$?"
tail -1 $S/l1_HEAD.log
K='{canonical_sha256,column_order_sha256,dtypes_sha256,index_sha256,values_sha256,nan_mask_sha256,rows,columns,nan_count}'
echo "HEAD:"; jq -c "$K" $S/l1_HEAD.json
jq -c '{window,index_first_last}' $S/l1_HEAD.json
echo "FROZEN:"; jq -c ".single_tf.BTCUSDT[\"12h\"].layers.L1 | $K" tests/_golden/failopen/baseline.json
