#!/bin/bash
# V-6 逐項實測狀態核對（伴隨收據 per_item_state.attested 之證據命令；fail-closed，任一不符或讀取錯誤 rc 1）。
# 以伴隨收據 per_item_state 為預期值，逐一機械核對 attested 所列每一事實：
#   ① junit/*.meta.json 之 nodeid 集合＝契約收據 durations_s 鍵集合＝per_item_state.items 鍵集合（不多不少）
#   ② 每項 meta 之 ledger_new 恰含一個字串，且等於 items[nodeid].session（＋".jsonl"）
#   ③ 該 session 檔存在、首行 kind=session；首行 head（40 位）與 diff_digest 等於 items[nodeid] 所記
#   ④ argv_norm.args 恰為 [nodeid]；去 args 後之 argv 之 sha256 等於 per_item_state.argv_rest_sha256
#   ⑤ env 為含 NUMBA_CACHE_DIR／PYTEST_VERSION／PYTHONPATH 非空字串之物件、python 為非空字串，
#      {env, python} 之 sha256 等於 per_item_state.env_python_sha256
#   ⑥ 每個出現之 head 至 BASE 之已提交差（整棵樹，只排除 DOC_EXCLUDE 之純文件路徑）⊆ CODE_DIFF_ALLOWED
#   ⑦ CODE_DIFF_ALLOWED 之每檔之主檔名（去副檔名）於 NO_REF_ROOTS（皆須存在）下皆無引用（grep -rlF）
# 範圍參數為本腳本之常數（不取自收據；審碼 b2 r6）：BASE＝契約收據首次加入之提交（git 導出）；收據之對應欄位須與常數相等。
# 覆寫（只供 mutation 驗證複本）：V6_META_DIR、V6_LEDGER_DIR、V6_COMPANION；有任一覆寫時結果標 MUTATION-MODE。
set -uo pipefail
DOC_EXCLUDE=(docs handoffs 白話說明 HANDOFF.md README.md 未來優化清單.md program.md AGENTS.md CLAUDE.md .cursorrules
  specs templates sessions frontend .github .vscode .vscode_settings.json ruff_output.txt git_push.sh uat_samples archived .claude)
CODE_DIFF_ALLOWED=(scripts/fact_keys.json)
NO_REF_ROOTS=(momentum conftest.py tests/conftest.py tests/fixtures tests/feature_engineering/conftest.py
  tests/feature_engineering/test_failopen_correctness.py scripts/freeze_failopen_baseline.py)
MODE=""; [ -n "${V6_META_DIR:-}${V6_LEDGER_DIR:-}${V6_COMPANION:-}" ] && MODE=" (MUTATION-MODE)"
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
BASE=$(git log --diff-filter=A --format=%H -- "$RCPT" | tail -1)
[[ "$BASE" =~ ^[0-9a-f]{40}$ ]] || fail "無法由 git 導出契約收據之首次加入提交"
canon() { printf "%s\n" "$@" | sort | jq -Rsc 'split("\n") | map(select(length > 0))'; }
[ "$(jq -er "$P.code_compare_to" "$COMP")" = "$BASE" ] || fail "收據 code_compare_to ≠ 契約收據首次加入之提交 $BASE"
[ "$(jq -c "$P.code_scope_exclude | sort" "$COMP")" = "$(canon "${DOC_EXCLUDE[@]}")" ] || fail "收據 code_scope_exclude ≠ 核對器常數"
[ "$(jq -c "$P.code_diff_allowed | sort" "$COMP")" = "$(canon "${CODE_DIFF_ALLOWED[@]}")" ] || fail "收據 code_diff_allowed ≠ 核對器常數"
[ "$(jq -c "$P.no_reference_roots | sort" "$COMP")" = "$(canon "${NO_REF_ROOTS[@]}")" ] || fail "收據 no_reference_roots ≠ 核對器常數"
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
excl=(); for e in "${DOC_EXCLUDE[@]}"; do excl+=(":(exclude,literal)$e"); done
allowed=$(printf "%s\n" "${CODE_DIFF_ALLOWED[@]}" | sort)
for h in $(printf "%s" "$heads" | sort -u); do
  d=$(git -c core.quotepath=off diff --name-only "$h" "$BASE" -- . "${excl[@]}") || fail "git diff $h $BASE 失敗"
  extra=$(comm -23 <(printf "%s\n" "$d" | sed '/^$/d' | sort) <(printf "%s\n" "$allowed"))
  [ -z "$extra" ] || fail "$h → $BASE 之已提交差（排除純文件路徑後）含未允許之檔：$extra"
done
for r in "${NO_REF_ROOTS[@]}"; do [ -e "$r" ] || fail "NO_REF_ROOTS 之 $r 不存在"; done
for a in "${CODE_DIFF_ALLOWED[@]}"; do
  stem=$(basename "$a"); stem=${stem%.*}
  hits=$(grep -rlF "$stem" "${NO_REF_ROOTS[@]}" 2>/dev/null)
  [ -z "$hits" ] || fail "$a（$stem）於 V-6 執行路徑被引用：$hits"
done
echo "OK${MODE}: ${#metas[@]} 項；session／head／diff_digest／argv／env 皆等於收據所記；各 head 至 ${BASE:0:8} 之已提交差（排除純文件路徑）⊆ {${CODE_DIFF_ALLOWED[*]}} 且其主檔名於 V-6 執行路徑無引用"
