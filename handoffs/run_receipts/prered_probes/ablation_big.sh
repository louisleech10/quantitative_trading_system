#!/bin/zsh
# PRE-RED Task 2.0：大單元兩段式消融（串行）。worktree 須已存在（$S/wt_d229336e、$S/wt_1cbc93f4）。
# 用法：zsh ablation_big.sh <輸出目錄> <symbol> <tf> [worktree 根，預設＝輸出目錄]
S=${1:?scratch}; SYM=${2:?symbol}; TF=${3:?tf}; W=${4:-$S}
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes
PY=/Users/louis/Desktop/quantitative_trading_system/venv/bin/python
T=${SYM}_${TF}
run() {  # $1=sha $2=mode $3=prefix $4=extra
  (cd $W/wt_$1 && env PYTHONHASHSEED=0 NUMBA_CACHE_DIR=$W/numba_$1 ${=5} venv/bin/python $P/ablation.py $2 $3 ${=4} > $3.log 2>&1)
  echo "$1 $2 rc=$? $(tail -1 $3.log | cut -c1-160)"
}
run d229336e new $S/abh_new_$T "$SYM $TF" PRERED_HASH_ONLY=1
run 1cbc93f4 old $S/abh_old_$T "$S/abh_new_$T.json" "PRERED_HASH_ONLY=1 PRERED_REF_META=$S/abh_new_$T.json"
$PY $P/ablation_hash.py plan $S/abh_new_$T.json $S/abh_old_$T.json $S/abh_cols_$T.txt $S/abh_plan_$T.json
run d229336e new $S/abl_new_$T "$SYM $TF" PRERED_COLS=$S/abh_cols_$T.txt
run 1cbc93f4 old $S/abl_old_$T "$S/abl_new_$T.json" PRERED_COLS=$S/abh_cols_$T.txt
$PY $P/ablation_classify.py $S/abl_new_$T $S/abl_old_$T $S/abl_subcls_$T.json > /dev/null
$PY $P/ablation_hash.py merge $S/abh_plan_$T.json $S/abl_subcls_$T.json $S/abl_cls_$T.json
$PY $P/ablation_c2.py $S/abl_new_$T $S/abl_cls_$T.json $S/abl_c2_$T.json 2>/dev/null | head -12
$PY $P/ablation_c3.py $S/abl_new_$T $S/abl_cls_$T.json $S/abl_c3_$T.json | head -12
$PY $P/c3_lowcard.py $S/abl_new_$T $S/abl_c3_$T.json
