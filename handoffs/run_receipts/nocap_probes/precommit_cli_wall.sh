#!/usr/bin/env bash
# NOCAP Task 0.2b③ pre-commit 之 timeout_scan 段實測（b1 審碼 r3 CODEX-R3-P1-01）：於臨時 git repo 放入 N 個真實 .py
# （取自本 repo、含既有逾時呼叫者），提交為 HEAD 後各檔尾加一行並暫存，計時實際命令列
# `venv/bin/python scripts/timeout_scan.py --staged --repo <tmp>`（含 Python 啟動、git diff --cached、git show、掃描與比對）。
# 用法：bash handoffs/run_receipts/nocap_probes/precommit_cli_wall.sh <輸出收據>
set -u
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
OUT="${1:?收據路徑}"
TMP="$(mktemp -d)"
FILES="scripts/ffprod_measure.py scripts/framepath_affected_gate.py scripts/testreg.py api/services/ic_analysis_service.py api/services/model_enhancement_service.py momentum/Analysis/ic_filter_orchestrator.py momentum/Analysis/feature_quality_diagnostics.py handoffs/run_receipts/numview_probes/_watchdog.py handoffs/run_receipts/numview_probes/estimate.py scripts/heavy_run_guard.py"
git init -q "$TMP"
git -C "$TMP" config user.email t@t
git -C "$TMP" config user.name t
lines=0
for f in $FILES; do
  mkdir -p "$TMP/$(dirname "$f")"
  cp "$REPO/$f" "$TMP/$f"
  lines=$((lines + $(wc -l < "$REPO/$f")))
done
git -C "$TMP" add -A
git -C "$TMP" commit -q -m base --no-verify
for f in $FILES; do printf '\n# nocap probe\n' >> "$TMP/$f"; done
git -C "$TMP" add -A
start=$(python3 -c 'import time; print(time.time())')
"$REPO/venv/bin/python" "$REPO/scripts/timeout_scan.py" --staged --repo "$TMP" > "$TMP/out.log" 2>&1
rc=$?
end=$(python3 -c 'import time; print(time.time())')
secs=$(python3 -c "print(round($end - $start, 3))")
nfiles=$(echo $FILES | wc -w | tr -d ' ')
printf '{"files": %s, "lines": %s, "rc": %s, "seconds": %s, "budget_seconds": 2.0, "command": "venv/bin/python scripts/timeout_scan.py --staged --repo <tmp>"}\n' "$nfiles" "$lines" "$rc" "$secs" > "$OUT"
cat "$OUT"
rm -rf "$TMP"
