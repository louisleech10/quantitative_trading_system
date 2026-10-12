#!/bin/bash
# V-6 逐項實測狀態核對（伴隨收據 per_item_state.attested 之證據命令；fail-closed，任一不符或讀取錯誤 rc 1）。
# 以伴隨收據 per_item_state 為預期值，逐一機械核對 attested 所列每一事實：
#   ① junit/*.meta.json 之 nodeid 集合＝契約收據 durations_s 鍵集合＝per_item_state.items 鍵集合（不多不少）
#   ② 每項 meta 之 ledger_new 恰含一個字串，且等於 items[nodeid].session（＋".jsonl"）
#   ③ 該 session 檔存在、首行 kind=session；首行 head（40 位）與 diff_digest 等於 items[nodeid] 所記
#   ④ argv_norm.args 恰為 [nodeid]；去 args 後之 argv 之 sha256 等於 per_item_state.argv_rest_sha256
#   ⑤ env 為含 NUMBA_CACHE_DIR／PYTEST_VERSION／PYTHONPATH 非空字串之物件、python 為非空字串，
#      {env, python} 之 sha256 等於 per_item_state.env_python_sha256
#   ⑥ 每個出現之 head 至 per_item_state.code_compare_to 之已提交程式碼與測試路徑差 ⊆ per_item_state.code_diff_allowed
#   ⑦ code_diff_allowed 之每檔於 per_item_state.no_reference_roots 下皆無引用（grep -rlF 檔名）
# 覆寫（只供 mutation 驗證複本）：V6_META_DIR、V6_LEDGER_DIR、V6_COMPANION。
set -uo pipefail
RCPT=handoffs/run_receipts/testreg-v6-profile.json
COMP=${V6_COMPANION:-handoffs/run_receipts/testreg-v6-profile-run.json}
META_DIR=${V6_META_DIR:-handoffs/run_receipts/testreg_probes/v6_run/junit}
fail() { echo "FAIL: $*" >&2; exit 1; }
L=$(jq -er '.ledger.dir' tests/registry/testreg_schema.json) || fail "schema ledger.dir 讀取失敗"
L=${V6_LEDGER_DIR:-$L}
P='.per_item_state'
exp_keys=$(jq -er '.durations_s | keys[]' "$RCPT" | sort) || fail "$RCPT 讀取失敗"
exp_short=$(jq -er '.durations_s | keys[] | split("::")[1]' "$RCPT" | sort) || fail "$RCPT 讀取失敗"
item_keys=$(jq -er "$P.items | keys[]" "$COMP" | sort) || fail "$COMP per_item_state.items 讀取失敗"
[ "$exp_short" = "$item_keys" ] || fail "per_item_state.items 鍵集合 ≠ 契約收據 durations_s 之函式層名集合"
argv_exp=$(jq -er "$P.argv_rest_sha256 | select(test(\"^[0-9a-f]{64}\$\"))" "$COMP") || fail "argv_rest_sha256 缺或格式不符"
env_exp=$(jq -er "$P.env_python_sha256 | select(test(\"^[0-9a-f]{64}\$\"))" "$COMP") || fail "env_python_sha256 缺或格式不符"
cmp_to=$(jq -er "$P.code_compare_to | select(test(\"^[0-9a-f]{40}\$\"))" "$COMP") || fail "code_compare_to 缺或非 40 位"
shopt -s nullglob
metas=("$META_DIR"/*.meta.json)
[ "${#metas[@]}" -gt 0 ] || fail "無 meta 檔"
seen=""; heads=""
for m in "${metas[@]}"; do
  nid=$(jq -er '.state_key | split("|")[1]' "$m") || fail "$m state_key 讀取失敗"
  short=${nid##*::}
  item=$(jq -ce --arg k "$short" "$P.items[\$k]" "$COMP") || fail "per_item_state.items 無 $short"
  jq -e '(.ledger_new | type) == "array" and (.ledger_new | length) == 1 and (.ledger_new[0] | type) == "string"' "$m" > /dev/null \
    || fail "$m ledger_new 須為恰含一個字串之陣列"
  sid=$(jq -er '.ledger_new[0]' "$m") || fail "$m ledger_new 讀取失敗"
  [ "$sid" = "$(echo "$item" | jq -er '.session').jsonl" ] || fail "$short 之 session $sid ≠ 收據所記"
  [ -f "$L/$sid" ] || fail "ledger session 不存在：$L/$sid"
  s=$(head -1 "$L/$sid")
  [ "$(echo "$s" | jq -er '.kind')" = "session" ] || fail "$sid 首行非 kind=session"
  head_=$(echo "$s" | jq -er 'if (.head | type) == "string" and (.head | test("^[0-9a-f]{40}$")) then .head else error("head") end') \
    || fail "$sid head 缺欄或非 40 位提交雜湊"
  [ "$head_" = "$(echo "$item" | jq -er '.head')" ] || fail "$short 之 head $head_ ≠ 收據所記"
  dd=$(echo "$s" | jq -er '.diff_digest | select(type == "string")') || fail "$sid diff_digest 缺欄"
  [ "$dd" = "$(echo "$item" | jq -er '.diff_digest')" ] || fail "$short 之 diff_digest ≠ 收據所記"
  echo "$s" | jq -e --arg n "$nid" '.argv_norm | fromjson | .args == [$n]' > /dev/null || fail "$sid argv_norm.args ≠ [nodeid]"
  rest_json=$(echo "$s" | jq -cSe '.argv_norm | fromjson
    | if (.args | type) == "array" and (.option | type) == "object" then del(.args) | del(.option.file_or_dir)
      else error("argv_norm 缺 args／option") end') || fail "$sid argv_norm 缺欄或型別不符"
  env_json=$(echo "$s" | jq -cSe 'if (.env | type) == "object"
      and ([.env.NUMBA_CACHE_DIR, .env.PYTEST_VERSION, .env.PYTHONPATH] | all(type == "string" and length > 0))
      and (.python | type) == "string" and (.python | length) > 0
    then {env, python} else error("env／python 缺欄") end') || fail "$sid env／python 缺欄或型別不符"
  [ "$(printf "%s" "$rest_json" | shasum -a 256 | cut -c1-64)" = "$argv_exp" ] || fail "$short 之 argv 指紋 ≠ 收據所記"
  [ "$(printf "%s" "$env_json" | shasum -a 256 | cut -c1-64)" = "$env_exp" ] || fail "$short 之 {env, python} 指紋 ≠ 收據所記"
  printf "%s head=%s session=%s argv_env=ok\n" "$short" "${head_:0:8}" "${sid%.jsonl}"
  seen="$seen$nid"$'\n'; heads="$heads$head_"$'\n'
done
[ "$(printf "%s" "$seen" | sort)" = "$exp_keys" ] || fail "meta 之 nodeid 集合 ≠ 收據 durations_s 鍵集合"
allowed=$(jq -er "$P.code_diff_allowed[]" "$COMP" | sort) || fail "code_diff_allowed 讀取失敗"
paths=()
while IFS= read -r p; do paths+=("$p"); done < <(jq -er "$P.code_paths[]" "$COMP") || fail "code_paths 讀取失敗"
[ "${#paths[@]}" -gt 0 ] || fail "code_paths 為空"
for h in $(printf "%s" "$heads" | sort -u); do
  d=$(git -c core.quotepath=off diff --name-only "$h" "$cmp_to" -- "${paths[@]}") || fail "git diff $h $cmp_to 失敗"
  extra=$(comm -23 <(printf "%s\n" "$d" | sed '/^$/d' | sort) <(printf "%s\n" "$allowed"))
  [ -z "$extra" ] || fail "$h → $cmp_to 之程式碼路徑差含未允許之檔：$extra"
done
roots=()
while IFS= read -r r; do [ -e "$r" ] || fail "no_reference_roots 之 $r 不存在"; roots+=("$r"); done \
  < <(jq -er "$P.no_reference_roots[]" "$COMP") || fail "no_reference_roots 讀取失敗"
[ "${#roots[@]}" -gt 0 ] || fail "no_reference_roots 為空"
for a in $allowed; do
  hits=$(grep -rlF "$(basename "$a")" "${roots[@]}" 2>/dev/null)
  [ -z "$hits" ] || fail "$a 於 V-6 執行路徑被引用：$hits"
done
echo "OK: ${#metas[@]} 項；session／head／diff_digest／argv／env 皆等於收據所記；程式碼路徑差 ⊆ {$(echo $allowed)} 且無引用"
