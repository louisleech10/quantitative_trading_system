#!/bin/bash
# v6_session_check.sh 之 mutation 驗證：每案斷言預期 rc（正常與原樣複本 0、破壞 1），任一不符本腳本 rc 1。
# 破壞皆在 mktemp 複本，以 V6_META_DIR／V6_LEDGER_DIR／V6_COMPANION 指入；不動真實 meta、ledger 與收據。
set -uo pipefail
S=handoffs/run_receipts/testreg_probes/v6_session_check.sh
SRC=handoffs/run_receipts/testreg_probes/v6_run/junit
COMP=handoffs/run_receipts/testreg-v6-profile-run.json
LSRC=$(jq -er '.ledger.dir' tests/registry/testreg_schema.json) || { echo "schema 讀取失敗"; exit 1; }
T=$(mktemp -d) || exit 1
trap 'rm -rf "$T"' EXIT
bad=0; n=0
expect() {  # expect <名> <預期 rc> [env 指派…]
  local name="$1" want="$2"; shift 2
  env "$@" "$BASH" "$S" > /dev/null 2> "$T/err"; local got=$?
  n=$((n + 1))
  if [ "$got" = "$want" ]; then echo "PASS $name rc=$got $(tail -1 "$T/err")"; else echo "MISMATCH $name 預期 rc=$want 實得 rc=$got"; bad=$((bad + 1)); fi
}
f=test_v6_asof_oracle_boundary_cases.meta.json
g=test_v6_backend_output_matches_independent_oracle_False_.meta.json
resetm() { rm -rf "$T/m"; mkdir -p "$T/m"; cp "$SRC"/*.meta.json "$T/m"/; }
resetl() { rm -rf "$T/l"; mkdir -p "$T/l"; for m in "$SRC"/*.meta.json; do cp "$LSRC/$(jq -r '.ledger_new[0]' "$m")" "$T/l/"; done; }
resetc() { cp "$COMP" "$T/c.json"; }
editfirst() { local p="$1"; shift; { head -1 "$p" | jq -c "$@"; tail -n +2 "$p"; } > "$p.tmp" && mv "$p.tmp" "$p"; }
first_l() { ls "$T"/l/*.jsonl | head -1; }
ROOT=$(git rev-list --max-parents=0 HEAD | tail -1)

expect normal 0
resetm; expect meta_copy_unmodified 0 V6_META_DIR="$T/m"
resetl; expect ledger_copy_unmodified 0 V6_LEDGER_DIR="$T/l"
resetc; expect companion_copy_unmodified 0 V6_COMPANION="$T/c.json"
# meta 破壞
resetm; jq '.state_key |= (split("|")[0] + "|MUTATED_NODEID")' "$SRC/$f" > "$T/m/$f"; expect meta_nodeid_changed 1 V6_META_DIR="$T/m"
resetm; rm "$T/m/$f"; expect meta_item_missing 1 V6_META_DIR="$T/m"
resetm; cp "$SRC/$f" "$T/m/extra.meta.json"; expect meta_item_extra 1 V6_META_DIR="$T/m"
resetm; jq '.ledger_new = ["no-such-session.jsonl"]' "$SRC/$f" > "$T/m/$f"; expect meta_session_nonexistent 1 V6_META_DIR="$T/m"
resetm; jq '.ledger_new = "x"' "$SRC/$f" > "$T/m/$f"; expect meta_ledger_new_string 1 V6_META_DIR="$T/m"
resetm; jq --argjson s "$(jq '.ledger_new' "$SRC/$g")" '.ledger_new = $s' "$SRC/$f" > "$T/m/$f"; expect meta_session_swapped 1 V6_META_DIR="$T/m"
# ledger 破壞
resetl; for p in "$T"/l/*.jsonl; do editfirst "$p" 'del(.env, .python)'; done; expect ledger_all_env_python_deleted 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" '.env.PYTEST_VERSION = "9.9.9"'; expect ledger_one_pytest_version 1 V6_LEDGER_DIR="$T/l"
resetl; for p in "$T"/l/*.jsonl; do editfirst "$p" '.env.PYTEST_VERSION = "9.9.9"'; done; expect ledger_all_pytest_version_consistent 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" 'del(.argv_norm)'; expect ledger_one_argv_deleted 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" '.kind = "test"'; expect ledger_one_kind 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" 'del(.head)'; expect ledger_one_head_deleted 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" --arg h "$(git rev-parse 1b74dd46)" '.head = $h'; expect ledger_one_head_other_real_commit 1 V6_LEDGER_DIR="$T/l"
resetl; editfirst "$(first_l)" '.diff_digest = ("0" * 64)'; expect ledger_one_diff_digest 1 V6_LEDGER_DIR="$T/l"
# 伴隨收據（預期值）破壞
resetc; jq '.per_item_state.items |= del(.["test_v6_asof_oracle_boundary_cases"])' "$COMP" > "$T/c.json"; expect companion_item_missing 1 V6_COMPANION="$T/c.json"
resetc; jq --arg h "$ROOT" '.per_item_state.code_compare_to = $h' "$COMP" > "$T/c.json"; expect companion_compare_to_root_commit 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.code_compare_to = "1e3c0dfa233417eebb5820072d485934d611c972"' "$COMP" > "$T/c.json"; expect companion_compare_to_other_valid_head 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.code_scope_exclude += ["scripts"]' "$COMP" > "$T/c.json"; expect companion_scope_exclude_widened 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.code_diff_allowed = ["no/such/file"]' "$COMP" > "$T/c.json"; expect companion_allowed_changed 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.no_reference_roots = ["momentum"]' "$COMP" > "$T/c.json"; expect companion_roots_narrowed 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.no_reference_roots += ["tests/feature_engineering/test_framepath_disposition.py"]' "$COMP" > "$T/c.json"; expect companion_roots_changed 1 V6_COMPANION="$T/c.json"
resetc; jq '.per_item_state.env_python_sha256 = ("0" * 64)' "$COMP" > "$T/c.json"; expect companion_env_fp 1 V6_COMPANION="$T/c.json"
# 覆寫時結果須標 MUTATION-MODE（與正式核對區分）
resetm; V6_META_DIR="$T/m" "$BASH" "$S" 2>/dev/null | tail -1 | grep -q "MUTATION-MODE"; mm=$?
n=$((n + 1)); if [ "$mm" = "0" ]; then echo "PASS override_marked_mutation_mode"; else echo "MISMATCH override_marked_mutation_mode"; bad=$((bad + 1)); fi
"$BASH" "$S" 2>/dev/null | tail -1 | grep -q "MUTATION-MODE"; nm=$?
n=$((n + 1)); if [ "$nm" = "1" ]; then echo "PASS normal_not_marked_mutation_mode"; else echo "MISMATCH normal_not_marked_mutation_mode"; bad=$((bad + 1)); fi

echo "cases=$n mismatches=$bad"
[ "$bad" = "0" ]
