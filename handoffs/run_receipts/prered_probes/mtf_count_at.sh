#!/bin/zsh
# test_mtf_12h_l1_l3_direct 於各 commit 之結果與 L3 存活欄數斷言。用法：zsh <本檔> <scratch> <commit...>
S=${1:?scratch}; shift
REPO=/Users/louis/Desktop/quantitative_trading_system
P=$REPO/handoffs/run_receipts/prered_probes
N=tests/feature_engineering/test_failopen_correctness.py::test_mtf_12h_l1_l3_direct_matches_preserve_dtype_executor
for c in "$@"; do
  C=$(git -C $REPO rev-parse --short=8 "$c")
  zsh $P/light_at_commit.sh $S $c $N
  grep -oE "assert [0-9]+ == [0-9]+" $S/light_$C.log | head -1
  git -C $REPO worktree remove --force $S/wt_$C > /dev/null 2>&1
done
