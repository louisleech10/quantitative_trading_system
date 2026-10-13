#!/bin/bash
# TESTREG v42：test_testreg_gate_wiring.py 之字面對映修正收據產生器（契約 receipts.literal_fix）。
# 前提：目標倉（$1，預設 repo 根）之工作樹已含 Task 2.3 實作與改名後之測試檔，且未提交；HEAD＝收據 head。
# 步驟：patch＝工作樹相對 HEAD 之（scripts/testreg.py、scripts/framepath_affected_gate.py、該測試檔）改動 →
#       於 HEAD 乾淨 worktree 套 patch、以記錄器實跑該測試檔 → session 檔複製回目標倉 ledger → 寫收據與 patch。
# 用法：bash handoffs/run_receipts/testreg_probes/literal_fix_receipt.sh [目標倉根]
set -u
REPO_MAIN=$(cd "$(dirname "$0")/../../.." && pwd)
TGT=$(cd "${1:-$REPO_MAIN}" && pwd)
REL=tests/registry/test_testreg_gate_wiring.py
DIR=handoffs/run_receipts/testreg-literal-fix
SLUG=tests__registry__test_testreg_gate_wiring.py
APPROVAL=handoffs/reconcile/20261010-testreg-x-consult-r2/synth.md
PY=$REPO_MAIN/venv/bin/python
HEAD_SHA=$(git -C "$TGT" rev-parse HEAD)
mkdir -p "$TGT/$DIR"
git -C "$TGT" diff HEAD --binary -- scripts/testreg.py scripts/framepath_affected_gate.py "$REL" > "$TGT/$DIR/$SLUG.patch"
WT=$(mktemp -d)/wt
# 修訂審查 r41 CODEX-R41-P2-02：任一步失敗（patch 套用、pytest 非 0、未產生 session）皆清理暫存 worktree 並以非 0 結束，
# 不複製 session、不寫收據
trap 'git -C "$TGT" worktree remove --force "$WT" >/dev/null 2>&1' EXIT
git -C "$TGT" worktree add -q --detach "$WT" "$HEAD_SHA" || exit 1
git -C "$WT" apply "$TGT/$DIR/$SLUG.patch" || { echo "patch 套用失敗"; exit 1; }
before=$(ls "$WT/.testreg/ledger" 2>/dev/null | sort)
( cd "$WT" && env -u TESTREG_PARENT_SESSION PYTHONPATH="$WT" "$PY" -m pytest -q -p no:cacheprovider -o log_cli=false \
    --log-level=WARNING "$REL" > "$WT/../run.log" 2>&1 ); rc=$?
tail -1 "$WT/../run.log"
if [ "$rc" -ne 0 ]; then echo "pytest rc=${rc}：改名後未全過，不產收據"; exit "${rc}"; fi
after=$(ls "$WT/.testreg/ledger" 2>/dev/null | sort)
SID_FILE=$(comm -13 <(echo "$before") <(echo "$after") | head -1)
[ -n "$SID_FILE" ] || { echo "未產生 session"; exit 1; }
# 修訂審查 r42 CODEX-R42-P2-01：複製 session 與寫收據任一失敗 ⇒ 非 0 結束（不留半成品收據）
mkdir -p "$TGT/.testreg/ledger" || { echo "建 ledger 目錄失敗"; exit 1; }
cp "$WT/.testreg/ledger/$SID_FILE" "$TGT/.testreg/ledger/" || { echo "複製 session 失敗"; exit 1; }
SID=${SID_FILE%.jsonl}
printf '{\n "approval_ref": "%s",\n "head": "%s",\n "map": {"tests.t": "tests.test_qt", "tests/t.py": "tests/test_qt.py"},\n "patch_path": "%s",\n "path": "%s",\n "session_id": "%s"\n}\n' \
  "$APPROVAL" "$HEAD_SHA" "$DIR/$SLUG.patch" "$REL" "$SID" > "$TGT/$DIR/$SLUG.json" \
  || { rm -f "$TGT/$DIR/$SLUG.json"; echo "寫收據失敗"; exit 1; }
echo "pytest_rc=$rc session=$SID receipt=$DIR/$SLUG.json"
