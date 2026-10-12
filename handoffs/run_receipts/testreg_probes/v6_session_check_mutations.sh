#!/bin/bash
# v6_session_check.sh 之 mutation 驗證（複本以 V6_META_DIR／V6_LEDGER_DIR 指入；不動真實 meta 與 ledger）：正常與原樣複本 rc 0，其餘 11 種破壞 rc 1
S=handoffs/run_receipts/testreg_probes/v6_session_check.sh
SRC=handoffs/run_receipts/testreg_probes/v6_run/junit
LSRC=$(jq -r '.ledger.dir' tests/registry/testreg_schema.json)
T=$(mktemp -d)
bash "$S" > /dev/null 2>&1; echo "normal rc=$?"
f=test_v6_asof_oracle_boundary_cases.meta.json
resetm() { rm -rf "$T/m"; mkdir -p "$T/m"; cp "$SRC"/*.meta.json "$T/m"/; }
run_m() { V6_META_DIR="$T/m" bash "$S" > /dev/null 2>"$T/err"; echo "$1 rc=$? $(tail -1 "$T/err")"; }
resetm; jq '.state_key |= (split("|")[0] + "|MUTATED_NODEID")' "$SRC/$f" > "$T/m/$f"; run_m nodeid_mutated
resetm; rm "$T/m/$f"; run_m missing_item
resetm; cp "$SRC/$f" "$T/m/extra.meta.json"; run_m extra_item
resetm; jq '.ledger_new = ["no-such-session.jsonl"]' "$SRC/$f" > "$T/m/$f"; run_m ledger_missing
# ledger 破壞：複製六項 session 到 $T/l，以 V6_LEDGER_DIR 指入
resetl() { rm -rf "$T/l"; mkdir -p "$T/l"; for m in "$SRC"/*.meta.json; do cp "$LSRC/$(jq -r '.ledger_new[0]' "$m")" "$T/l/"; done; }
run_l() { V6_LEDGER_DIR="$T/l" bash "$S" > /dev/null 2>"$T/err"; echo "$1 rc=$? $(tail -1 "$T/err")"; }
editfirst() { local p="$1" expr="$2"; { head -1 "$p" | jq -c "$expr"; tail -n +2 "$p"; } > "$p.tmp" && mv "$p.tmp" "$p"; }
resetl; run_l ledger_copy_unmodified
resetl; for p in "$T"/l/*.jsonl; do editfirst "$p" 'del(.env, .python)'; done; run_l all_env_python_deleted
one=$(ls "$T"/l/*.jsonl | head -1)
resetl; one=$(ls "$T"/l/*.jsonl | head -1); editfirst "$one" '.env.PYTEST_VERSION = "9.9.9"'; run_l one_pytest_version_changed
resetl; one=$(ls "$T"/l/*.jsonl | head -1); editfirst "$one" 'del(.argv_norm)'; run_l one_argv_deleted
resetl; one=$(ls "$T"/l/*.jsonl | head -1); editfirst "$one" '.kind = "test"'; run_l one_kind_changed
rm -rf "$T"
# 主委自查兩種：meta 之 ledger_new 為字串、ledger session 刪 head
resetm; jq '.ledger_new = "x"' "$SRC/$f" > "$T/m/$f"; run_m ledger_new_string
T=$(mktemp -d); resetl; one=$(ls "$T"/l/*.jsonl | head -1); editfirst "$one" 'del(.head)'; run_l one_head_deleted
rm -rf "$T"
