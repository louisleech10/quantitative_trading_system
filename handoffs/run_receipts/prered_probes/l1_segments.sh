#!/bin/zsh
# PRE-RED：依序於各候選 commit 跑 L1 探針（串行），輸出各分量摘要表。
# 用法：zsh l1_segments.sh <scratch> <commit...>
S=${1:?scratch}; shift
P=/Users/louis/Desktop/quantitative_trading_system/handoffs/run_receipts/prered_probes
for c in "$@"; do
  full=$(git -C /Users/louis/Desktop/quantitative_trading_system rev-parse --short=8 "$c")
  zsh $P/l1_at_commit.sh $full $S > /dev/null 2>&1
  if [ -f $S/l1_$full.json ]; then
    echo "$c ($full) $(jq -r '[.canonical_sha256[0:8], "col=" + .column_order_sha256[0:8], "dt=" + .dtypes_sha256[0:8], "idx=" + .index_sha256[0:8], "val=" + .values_sha256[0:8], "nan=" + .nan_mask_sha256[0:8], "nancnt=" + (.nan_count|tostring), "cols=" + (.columns|tostring)] | join(" ")' $S/l1_$full.json)"
  else
    echo "$c ($full) PROBE_FAILED: $(tail -3 $S/l1_$full.log | tr '\n' ' ' | cut -c1-300)"
  fi
done
