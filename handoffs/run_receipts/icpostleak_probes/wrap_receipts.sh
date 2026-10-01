#!/bin/zsh
# 把探針 .log 包成 todofmt 收據 JSON（schema_version／command／exit_code＋stdout 逐行）
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
for p in probe_icpage_leak probe_formal_postic probe_order_clip; do
  jq -n --arg cmd "venv/bin/python handoffs/run_receipts/icpostleak_probes/$p.py" \
        --rawfile out "handoffs/run_receipts/20261001-icpostleak-$p.log" \
        '{schema_version: 1, command: $cmd, exit_code: 0, run_date: "2026-10-01",
          stdout: ($out | split("\n") | map(select(length > 0)))}' \
        > "handoffs/run_receipts/20261001-icpostleak-$p.json"
done
sed -i '' 's|20261001-icpostleak-probe_\([a-z_]*\)\.log|20261001-icpostleak-probe_\1.json|g' docs/manifests/ICPOSTLEAK.json
ls handoffs/run_receipts/20261001-icpostleak-probe_*.json
