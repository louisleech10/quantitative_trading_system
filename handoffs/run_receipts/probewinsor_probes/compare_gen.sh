#!/usr/bin/env bash
# PROBEWINSOR 偵察：比對 gen.<case>.current.json 與 gen.<case>.fixed.json。用法：bash compare_gen.sh <case> ...
set -u
D="$(cd "$(dirname "${0}")" && pwd)/out"
for c in "$@"; do
  a="${D}/gen.${c}.current.json"; b="${D}/gen.${c}.fixed.json"
  [ -f "${a}" ] && [ -f "${b}" ] || { echo "== ${c}: 缺檔"; continue; }
  jq -n --slurpfile A "${a}" --slurpfile B "${b}" --arg c "${c}" '
    ($A[0]) as $a | ($B[0]) as $b |
    ($a.public_fingerprints|keys) as $ka | ($b.public_fingerprints|keys) as $kb |
    ([$ka[] | select(($b.public_fingerprints[.]) != null and ($a.public_fingerprints[.]) != ($b.public_fingerprints[.]))]) as $diff |
    ([$ka[] | select(($b.public_fingerprints[.]) != null and ($a.public_fingerprints[.].nan) != ($b.public_fingerprints[.].nan))]) as $nandiff |
    {case: $c,
     ingest: [$a.output_window.ingest_start, $b.output_window.ingest_start],
     depth: [$a.output_window.max_warmup_bars, $b.output_window.max_warmup_bars],
     quality: [$a.quality_status, $b.quality_status],
     columns: [($ka|length), ($kb|length)],
     only_current: ($ka - $kb | length), only_fixed: ($kb - $ka | length),
     value_or_nan_diff_cols: ($diff|length), nan_mask_diff_cols: ($nandiff|length),
     diff_sample: ($diff[:8]),
     warmup_insufficient: [($a.warmup_insufficient_columns|length?), ($b.warmup_insufficient_columns|length?)],
     warmup_insufficient_removed: (($a.warmup_insufficient_columns // []) - ($b.warmup_insufficient_columns // []) | .[:10]),
     warmup_insufficient_added: (($b.warmup_insufficient_columns // []) - ($a.warmup_insufficient_columns // []) | .[:10]),
     stable_start_diff: ([($a.stable_start // {}) | keys[] as $k | select(($a.stable_start[$k]) != (($b.stable_start // {})[$k]))] | length),
     found_keys: $a.found_keys}'
done
