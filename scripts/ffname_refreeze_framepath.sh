#!/usr/bin/env bash
# FF-NAME Task 4.3：framepath K2（SPEC v22：改前碼與現行碼各跑 12 格、依名逐欄比對，符合重凍前提之格只換該格 fingerprint）。
# 可續跑：新／舊紀錄檔已存在且可解析即跳過；每步前查委員輪與磁碟。
#
# 用法：WT=<改前 worktree（c9737729）> OUT=<輸出目錄> bash scripts/ffname_refreeze_framepath.sh
# 選項：CELLS="C1,C2"（預設全 12 格）、DRY_RUN=1
# 預估：golden 內各格 memory.seconds 加總 1225.6 秒（約 20 分）／側；改前側另加紀錄器約 +10–20%（推論）⇒ 兩側合計約 45–50 分。
set -u
set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
WT="${WT:?須設 WT＝改前 worktree}"
OUT="${OUT:?須設 OUT＝輸出目錄}"
DRY_RUN="${DRY_RUN:-0}"
GOLDEN="tests/_golden/framepath/cgsa_fingerprint.json"
LOG="$OUT/runner.log"
mkdir -p "$OUT/records"
export PYTHONHASHSEED=0
[ -n "${CELLS:-}" ] && export FFNAME_CELLS="$CELLS"

EXPECTED="$("$PY" -c "import json; print(json.load(open('$ROOT/tests/_golden/ffname/contract.json'))['refreeze']['pre_change_commit'])")"
[ "$(git -C "$WT" rev-parse HEAD)" = "$EXPECTED" ] || { echo "WT 非契約 pre_change_commit $EXPECTED" >&2; exit 2; }

guard() {
  if pgrep -f committee_run >/dev/null 2>&1; then echo "委員輪進行中，停" >&2; exit 3; fi
  local free_gb
  free_gb=$(df -g / | awk 'NR==2 {print $4}')
  if [ "${free_gb:-0}" -lt 30 ]; then echo "磁碟剩 ${free_gb}GB < 30GB，停" >&2; exit 3; fi
}
valid() { [ -s "$1" ] && "$PY" -c "import json,sys; json.load(open(sys.argv[1]))" "$1" >/dev/null 2>&1; }

for side in old new; do
  out="$OUT/records/framepath.$side.json"
  if valid "$out"; then echo "[skip] framepath $side" | tee -a "$LOG"; continue; fi
  if [ "$DRY_RUN" = "1" ]; then echo "[dry] framepath $side → $out"; continue; fi
  guard
  t0=$(date +%s)
  if [ "$side" = "old" ]; then
    "$PY" "$ROOT/scripts/ffname_refreeze.py" record --recipe framepath --tree "$WT" --out "$out" > "$OUT/records/framepath.$side.log" 2>&1
  else
    "$PY" "$ROOT/scripts/ffname_refreeze.py" record --recipe framepath --no-instrument --out "$out" > "$OUT/records/framepath.$side.log" 2>&1
  fi
  rc=$?
  echo "[done] framepath $side rc=$rc $(( $(date +%s) - t0 ))s" | tee -a "$LOG"
  [ "$rc" -eq 0 ] || { rm -f "$out"; exit "$rc"; }
done
if [ "$DRY_RUN" != "1" ]; then
  "$PY" "$ROOT/scripts/ffname_refreeze.py" k2 --golden "$GOLDEN" --old "$OUT/records/framepath.old.json" \
    --new "$OUT/records/framepath.new.json" > "$OUT/records/framepath.k2.log" 2>&1
  rc=$?
  tail -14 "$OUT/records/framepath.k2.log" | tee -a "$LOG"
  [ "$rc" -eq 0 ] || { echo "[STOP] framepath k2 rc=$rc" | tee -a "$LOG"; exit "$rc"; }
  echo "framepath 12 格 k2 完成（逐格決策見 handoffs/run_receipts/ffname_refreeze_k2/framepath__cgsa_fingerprint.json）" | tee -a "$LOG"
fi
