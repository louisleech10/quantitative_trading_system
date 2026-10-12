#!/bin/bash
# V-6 逐項實測狀態核對（伴隨收據 per_item_state.attested 之證據命令；fail-closed）：
#   - junit/*.meta.json 之 nodeid 集合須恰等於契約收據 durations_s 之鍵集合（不多不少）
#   - 每項 ledger_new 恰一個 session、檔存在且首行 kind=session
#   - 每項 argv_norm.args 恰為該項 nodeid
#   - 去 args 後之 argv 指紋、{env, python} 指紋六項皆相同
# 任一不符、缺檔或 JSON 錯誤 ⇒ rc 1。輸出逐項一行與摘要。
set -uo pipefail
RCPT=handoffs/run_receipts/testreg-v6-profile.json
META_DIR=${V6_META_DIR:-handoffs/run_receipts/testreg_probes/v6_run/junit}  # 覆寫只供 mutation 驗證（複本）
fail() { echo "FAIL: $*" >&2; exit 1; }
L=$(jq -er '.ledger.dir' tests/registry/testreg_schema.json) || fail "schema ledger.dir 讀取失敗"
L=${V6_LEDGER_DIR:-$L}  # 覆寫只供 mutation 驗證（複本）
expected=$(jq -er '.durations_s | keys[]' "$RCPT" | sort) || fail "$RCPT 讀取失敗"
shopt -s nullglob
metas=("$META_DIR"/*.meta.json)
[ "${#metas[@]}" -gt 0 ] || fail "無 meta 檔"
seen=""; argv_set=""; env_set=""; bad=0
for m in "${metas[@]}"; do
  nid=$(jq -er '.state_key | split("|")[1]' "$m") || fail "$m state_key 讀取失敗"
  jq -e '(.ledger_new | type) == "array" and (.ledger_new | length) == 1 and (.ledger_new[0] | type) == "string"' "$m" > /dev/null \
    || fail "$m ledger_new 須為恰含一個字串之陣列"
  sid=$(jq -er '.ledger_new[0]' "$m") || fail "$m ledger_new 讀取失敗"
  [ -f "$L/$sid" ] || fail "ledger session 不存在：$L/$sid"
  s=$(head -1 "$L/$sid")
  [ "$(echo "$s" | jq -er '.kind')" = "session" ] || fail "$sid 首行非 kind=session"
  args=$(echo "$s" | jq -er '.argv_norm | fromjson | .args | join(" ")') || fail "$sid argv_norm 讀取失敗"
  # 取值前驗證據欄存在且型別正確（缺欄不得以 null 指紋「一致」放行——審碼 b2 r4）
  rest_json=$(echo "$s" | jq -cSe '.argv_norm | fromjson
    | if (.args | type) == "array" and (.option | type) == "object" then del(.args) | del(.option.file_or_dir)
      else error("argv_norm 缺 args／option") end') || fail "$sid argv_norm 缺欄或型別不符"
  env_json=$(echo "$s" | jq -cSe 'if (.env | type) == "object"
      and ([.env.NUMBA_CACHE_DIR, .env.PYTEST_VERSION, .env.PYTHONPATH] | all(type == "string" and length > 0))
      and (.python | type) == "string" and (.python | length) > 0
    then {env, python} else error("env／python 缺欄") end') || fail "$sid env／python 缺欄或型別不符"
  rest=$(printf "%s" "$rest_json" | shasum -a 256 | cut -c1-12)
  envh=$(printf "%s" "$env_json" | shasum -a 256 | cut -c1-12)
  head_=$(echo "$s" | jq -er 'if (.head | type) == "string" and (.head | test("^[0-9a-f]{40}$")) then .head[0:8] else error("head") end') \
    || fail "$sid head 缺欄或非 40 位提交雜湊"
  ok=yes; [ "$args" = "$nid" ] || { ok=NO; bad=1; }
  printf "%s head=%s args_eq_nodeid=%s argv_rest=%s env_python=%s\n" "${sid%.jsonl}" "$head_" "$ok" "$rest" "$envh"
  seen="$seen$nid"$'\n'; argv_set="$argv_set$rest"$'\n'; env_set="$env_set$envh"$'\n'
done
[ "$(printf "%s" "$seen" | sort)" = "$expected" ] || fail "meta 之 nodeid 集合 ≠ 收據 durations_s 鍵集合"
[ "$(printf "%s" "$argv_set" | sort -u | wc -l | tr -d ' ')" = "1" ] || fail "argv 指紋不一致"
[ "$(printf "%s" "$env_set" | sort -u | wc -l | tr -d ' ')" = "1" ] || fail "{env, python} 指紋不一致"
[ "$bad" = "0" ] || fail "有項之 args 不等於 nodeid"
echo "OK: ${#metas[@]} 項 nodeid 集合＝收據、args 皆＝nodeid、argv／env 指紋各一致"
