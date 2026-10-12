#!/bin/bash
# 逐項：session id、head、args 是否恰為 nodeid、去 args 後之 argv 指紋、env／python 指紋
L=$(jq -r '.ledger.dir' tests/registry/testreg_schema.json)
for m in handoffs/run_receipts/testreg_probes/v6_run/junit/*.meta.json; do
  sid=$(jq -r '.ledger_new[0]' "$m")
  s=$(head -1 "$L/$sid")
  nid=$(jq -r '.state_key | split("|")[1]' "$m")
  args=$(echo "$s" | jq -r '.argv_norm | fromjson | .args | join(" ")')
  rest=$(echo "$s" | jq -cS '.argv_norm | fromjson | del(.args) | del(.option.file_or_dir)' | shasum -a 256 | cut -c1-12)
  envh=$(echo "$s" | jq -cS '{env, python}' | shasum -a 256 | cut -c1-12)
  printf "%s head=%s args_eq_nodeid=%s argv_rest=%s env_python=%s\n" "${sid%.jsonl}" "$(echo "$s" | jq -r '.head[0:8]')" "$([ "$args" = "$nid" ] && echo yes || echo NO)" "$rest" "$envh"
done
