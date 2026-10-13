#!/usr/bin/env bash
# TESTREG b3 Task 3.1 輔助：Phase 3 範圍內輕量檔（非真實 K 線、無 slow／timeout 標記）逐檔實跑，找出未登記之既有紅。
# 記錄器開（結果進 .testreg/ledger 與 summary，供 Task 3.2 估時）；每檔一次 pytest、單組串行；單檔逾 MAX 秒即終止並記 timeout。
# 用法：bash light_sweep.sh <檔清單> <輸出 tsv> [MAX 秒，預設 300]
# 輸出欄：path、rc、seconds、summary（pytest 最後摘要行）、failed_nodeids（逗號分隔）
set -u
LIST="$1"; OUT="$2"; MAX="${3:-300}"
LOGDIR="$(dirname "$OUT")/light_sweep_logs"
mkdir -p "$LOGDIR"
printf 'path\trc\tseconds\tsummary\tfailed_nodeids\n' > "$OUT"
while IFS= read -r f; do
  [ -n "$f" ] || continue
  log="$LOGDIR/$(printf '%s' "$f" | tr '/' '_').log"
  start=$(date +%s)
  venv/bin/python -m pytest -q -p no:cacheprovider -rfE "$f" > "$log" 2>&1 &
  pid=$!
  rc=""
  while kill -0 "$pid" 2>/dev/null; do
    if [ $(( $(date +%s) - start )) -ge "$MAX" ]; then
      kill "$pid" 2>/dev/null; sleep 2; kill -9 "$pid" 2>/dev/null; rc="timeout"; break
    fi
    sleep 1
  done
  wait "$pid" 2>/dev/null; prc=$?
  [ -n "$rc" ] || rc="$prc"
  secs=$(( $(date +%s) - start ))
  summ=$(grep -E '(passed|failed|error|skipped|no tests ran)' "$log" | tail -1 | tr '\t' ' ')
  fails=$(grep -E '^(FAILED|ERROR) ' "$log" | awk '{print $2}' | paste -sd, -)
  printf '%s\t%s\t%s\t%s\t%s\n' "$f" "$rc" "$secs" "${summ:--}" "${fails:--}" >> "$OUT"
done < "$LIST"
bash scripts/restore_golden_inventory.sh > /dev/null 2>&1
echo "DONE $(awk -F'\t' 'NR>1' "$OUT" | wc -l | tr -d ' ') files → $OUT"
