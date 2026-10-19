#!/usr/bin/env bash
# FF-NAME Task 4.3：failopen K2 全窗新舊碼對證（SPEC v22 §G K2＋重凍前提；使用者 2026-10-18 選「比完整的」）。
# 可續跑：每個（單元 × 新／舊）之紀錄檔已存在且可解析即跳過；每步前查委員輪與磁碟；逐步記牆鐘。
# 每單元 k2 之決策：refrozen（依名不符 0 且改前碼重現改前 golden ⇒ 合併入 golden）、pre_existing_drift（依名不符 0
# 但改前碼不重現 ⇒ golden 該單元不動、登記既有漂移）、fail（依名不符或 ⑥ 未驗 ⇒ rc 2，本腳本立即停）。
#
# 用法（主樹根目錄執行；須先備好改前 worktree）：
#   WT=<改前 worktree 路徑（c9737729）> OUT=<版控外輸出目錄> bash scripts/ffname_refreeze_failopen.sh
# 選項：UNITS="BTCUSDT/12h ETHUSDT/12h"（預設＝契約 failopen_units）、DRY_RUN=1（只印步驟與預估，不執行）
#
# 預估（golden 內 perf.generation_wall_seconds＋hash；改前碼另加紀錄器與逐欄 sidecar 約 +10–20%，推論）：
#   BTCUSDT/12h ≈ 2 分、ETHUSDT/12h ≈ 2 分、BTCUSDT/1h ≈ 7 分、ETHUSDT/1h ≈ 14 分、
#   BTCUSDT/multi ≈ 36 分、ETHUSDT/multi ≈ 40–82 分（golden 值為舊碼 81 分；BTC multi 曾由 81 分降至 36 分）
#   每側約 105–150 分，新舊兩側合計約 3.5–5 小時；全程串行，不與委員輪並行。
set -u
set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="$ROOT/venv/bin/python"
WT="${WT:?須設 WT＝改前 worktree（git worktree add --detach <path> c9737729）}"
OUT="${OUT:?須設 OUT＝版控外輸出目錄（sidecar 每份數十 MB）}"
# 預設＝契約 failopen_units（重凍對證之單元；failopen_units_k0 之單元不跑、golden 位元組保持改前）
UNITS="${UNITS:-$("$PY" -c "import json; print(' '.join(json.load(open('$ROOT/tests/_golden/ffname/contract.json'))['refreeze']['failopen_units']))")}"
DRY_RUN="${DRY_RUN:-0}"
GOLDEN="tests/_golden/failopen/baseline.json"
LOG="$OUT/runner.log"
mkdir -p "$OUT/records" "$OUT/sidecars"
export FFNAME_SIDECAR_DIR="$OUT/sidecars"
export PYTHONHASHSEED=0

EXPECTED="$("$PY" -c "import json; print(json.load(open('$ROOT/tests/_golden/ffname/contract.json'))['refreeze']['pre_change_commit'])")"
[ "$(git -C "$WT" rev-parse HEAD)" = "$EXPECTED" ] || { echo "WT 非契約 pre_change_commit $EXPECTED" >&2; exit 2; }
[ -e "$WT/data_cache/feature_klines" ] || { echo "WT 缺 data_cache/feature_klines（以 symlink 指向主樹，唯讀使用）" >&2; exit 2; }

guard() {
  if pgrep -f committee_run >/dev/null 2>&1; then echo "委員輪進行中，停（重型跑與派委員互斥）" >&2; exit 3; fi
  local free_gb
  free_gb=$(df -g / | awk 'NR==2 {print $4}')
  if [ "${free_gb:-0}" -lt 30 ]; then echo "磁碟剩 ${free_gb}GB < 30GB，停" >&2; exit 3; fi
}

valid() { [ -s "$1" ] && "$PY" -c "import json,sys; json.load(open(sys.argv[1]))" "$1" >/dev/null 2>&1; }

step() {  # step <unit> <side old|new>
  local unit="$1" side="$2" tag out t0 rc
  tag="$(echo "$unit" | tr '/' '-')"
  out="$OUT/records/failopen.$tag.$side.json"
  if valid "$out"; then echo "[skip] ${unit} ${side}（已存在）" | tee -a "$LOG"; return 0; fi
  if [ "$DRY_RUN" = "1" ]; then echo "[dry] $unit $side → $out"; return 0; fi
  guard
  t0=$(date +%s)
  if [ "$side" = "old" ]; then
    FFNAME_UNIT="$unit" "$PY" "$ROOT/scripts/ffname_refreeze.py" record --recipe failopen --tree "$WT" \
      --out "$out" > "$OUT/records/failopen.$tag.$side.log" 2>&1
  elif [ "$side" = "noprobe" ] || [ "$side" = "noprobe_control" ]; then  # 探針等價證明用：現行碼不掛探針
    FFNAME_NO_PROBE=1 FFNAME_UNIT="$unit" "$PY" "$ROOT/scripts/ffname_refreeze.py" record --recipe failopen \
      --no-instrument --out "$out" > "$OUT/records/failopen.$tag.$side.log" 2>&1
  else
    FFNAME_UNIT="$unit" "$PY" "$ROOT/scripts/ffname_refreeze.py" record --recipe failopen --no-instrument \
      --out "$out" > "$OUT/records/failopen.$tag.$side.log" 2>&1
  fi
  rc=$?
  echo "[done] $unit $side rc=$rc $(( $(date +%s) - t0 ))s" | tee -a "$LOG"
  [ "$rc" -eq 0 ] || { rm -f "$out"; exit "$rc"; }
}

for unit in $UNITS; do
  step "$unit" old
  step "$unit" new
  tag="$(echo "$unit" | tr '/' '-')"
  # 委員會 r3 (a)：multi 單元之 ⑥ 位移值來自串流寫出入口之唯讀探針 ⇒ 另跑兩份不掛探針之現行碼紀錄（noprobe 與
  # noprobe_control），先產「探針不改生產輸出」證明（k2 對 multi 單元要求此證明 equal，否則 fail）：掛 vs 不掛探針
  # 資料檔位元組全等、.json 中介檔遮罩逐次變動欄後全等；兩份不掛探針間之 .json 差證明該類差非探針所致。
  if [ "${unit##*/}" = "multi" ]; then
    step "$unit" noprobe
    step "$unit" noprobe_control
  fi
  if [ "$DRY_RUN" != "1" ] && [ "${unit##*/}" = "multi" ]; then
    "$PY" "$ROOT/scripts/ffname_refreeze.py" probe-equiv --with-probe "$OUT/records/failopen.$tag.new.json" \
      --without-probe "$OUT/records/failopen.${tag}.noprobe.json" \
      --control "$OUT/records/failopen.${tag}.noprobe_control.json" \
      > "$OUT/records/failopen.${tag}.probe_equiv.log" 2>&1
    rc=$?
    tail -2 "$OUT/records/failopen.${tag}.probe_equiv.log" | tee -a "$LOG"
    if [ "$rc" -ne 0 ]; then
      echo "[STOP] ${unit} 探針等價 rc=${rc}（詳 ${OUT}/records/failopen.${tag}.probe_equiv.log）" | tee -a "$LOG"
      exit "$rc"
    fi
  fi
  if [ "$DRY_RUN" != "1" ]; then
    "$PY" "$ROOT/scripts/ffname_refreeze.py" k2 --golden "$GOLDEN" \
      --old "$OUT/records/failopen.$tag.old.json" --new "$OUT/records/failopen.$tag.new.json" \
      > "$OUT/records/failopen.$tag.k2.log" 2>&1
    rc=$?
    tail -3 "$OUT/records/failopen.$tag.k2.log" | tee -a "$LOG"
    if [ "$rc" -ne 0 ]; then
      echo "[STOP] ${unit} k2 rc=${rc}（依名不符或 ⑥ 未驗；詳 ${OUT}/records/failopen.${tag}.k2.log）" | tee -a "$LOG"
      exit "$rc"
    fi
  fi
done
if [ "$DRY_RUN" != "1" ]; then
  echo "全部單元 k2 完成（每單元決策見 handoffs/run_receipts/ffname_refreeze_k2/failopen__baseline__*.json：refrozen 或 pre_existing_drift）" | tee -a "$LOG"
  echo "接著：venv/bin/python scripts/ffname_refreeze.py receipt --salt-proof handoffs/run_receipts/ffname_refreeze_maps/salt_proof.json --consumers handoffs/run_receipts/ffname_refreeze_consumers.json --full-reference <全量 reference JSON>" | tee -a "$LOG"
fi
