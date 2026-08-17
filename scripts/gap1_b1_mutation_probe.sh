#!/usr/bin/env bash
# gap1_b1_mutation_probe.sh — B1 之 mutation 自證（§V-5／8／10／13／15）。
#
# 每條：就地 mutate 一行 → 跑對應測試 → 斷言**轉紅且為斷言失敗（非 collection error）** → 還原。
# 產出 receipt 供 code review 對證（TODO §0「新測試須 mutation 自證（實跑貼 rc）」）。
#
# 🔴 首版兩個真缺陷（2026-08-17 實跑抓到，已修；留紀錄以免重犯）：
#   ① 用 `git checkout --` 還原 ⇒ **未追蹤新檔還原不了**，且一個 pathspec 不存在會使
#      整條命令失敗、連追蹤檔也沒還原 ⇒ mutant 留在工作區（首次實跑真的發生）。
#      改法：mutate 前把每個目標檔複製到 $BACKUP_DIR，還原時 `cp` 回來（與版控狀態無關）。
#   ② §V-10 之 mutant 把註解插進括號運算式中 ⇒ SyntaxError ⇒ pytest rc=2（collection error）。
#      「因語法壞掉而紅」**不算**測試可證偽 ⇒ 本版對每條 mutation 斷言
#      `FAILED` 條數 >= 1（rc=1），rc=2 一律判為 mutation 設計錯。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2

PY=venv/bin/python
FREQ=momentum/core/frequency.py
SHARPE=momentum/Analysis/strategy_validation/sharpe.py
TEST_FREQ=tests/momentum/Analysis/strategy_validation/test_frequency.py
TEST_SHARPE=tests/momentum/Analysis/strategy_validation/test_sharpe.py
TEST_VB=tests/momentum/Strategy/test_vectorized_backtest.py

TARGETS="${FREQ} ${SHARPE} ${TEST_VB}"
BACKUP_DIR="$(mktemp -d)"

backup_all() {
  for f in ${TARGETS}; do
    mkdir -p "${BACKUP_DIR}/$(dirname "$f")"
    cp "$f" "${BACKUP_DIR}/$f"
  done
}
restore_all() {
  for f in ${TARGETS}; do
    [ -f "${BACKUP_DIR}/$f" ] && cp "${BACKUP_DIR}/$f" "$f"
  done
}
cleanup() { restore_all; rm -rf "${BACKUP_DIR}"; }
trap cleanup EXIT

backup_all

FAILED_DESIGN=0

run_expect_red() {  # <label> <test-target>
  _label="$1"; _target="$2"
  "$PY" -m pytest "$_target" -q > /tmp/gap1_mut.log 2>&1
  _rc=$?
  _nfail="$(grep -cE '^FAILED' /tmp/gap1_mut.log)"
  if [ "$_rc" -eq 1 ] && [ "$_nfail" -ge 1 ]; then
    echo "  ✅ ${_label}: 轉紅 rc=1（${_nfail} 條 FAILED＝斷言失敗）"
  elif [ "$_rc" -eq 2 ]; then
    echo "  🔴 ${_label}: rc=2（collection/語法錯）⇒ **mutation 設計錯**，不算可證偽"
    FAILED_DESIGN=1
  else
    echo "  🔴 ${_label}: rc=${_rc}、FAILED=${_nfail} ⇒ **未轉紅**，測試不可證偽"
    FAILED_DESIGN=1
  fi
  restore_all
}

mutate() {  # <file> <old> <new>
  "$PY" - "$1" "$2" "$3" <<'PY'
import pathlib, sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
p = pathlib.Path(path)
s = p.read_text(encoding="utf-8")
if old not in s:
    sys.exit(f"MUTATION TARGET MISS: {path}: {old!r}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
PY
}

echo "[baseline] 未 mutate 時三檔應全綠"
"$PY" -m pytest "$TEST_FREQ" "$TEST_SHARPE" "$TEST_VB" -q > /tmp/gap1_mut.log 2>&1
echo "  baseline rc=$? ($(tail -1 /tmp/gap1_mut.log))"

echo "[§V-8] resolve_periods_per_year 未知 timeframe 回 730（而非 raise）"
mutate "$FREQ" '        raise UnknownTimeframeError(f"unknown timeframe: {timeframe!r}")' '        return 730' || exit 1
run_expect_red "§V-8" "$TEST_FREQ"

echo "[§V-15] available_years 回 n_bars（把 bar 數當年數）"
mutate "$FREQ" "    return n_bars / resolve_periods_per_year(timeframe)" "    return float(n_bars)" || exit 1
run_expect_red "§V-15" "$TEST_FREQ"

echo "[§V-5] compute_sharpe 退化情形回 0.0（而非 NaN＋status）"
mutate "$SHARPE" '    nan = float("nan")' "    nan = 0.0" || exit 1
run_expect_red "§V-5" "$TEST_SHARPE"

echo "[§V-10] Mertens (γ4-1)/4 改成 γ4/4（語法合法之數值 mutant）"
mutate "$SHARPE" "(kurtosis - 1.0) / 4.0 * sr_pp**2" "kurtosis / 4.0 * sr_pp**2" || exit 1
run_expect_red "§V-10" "$TEST_SHARPE"

echo "[§V-13] Task 1.3 斷言③ 之 fixture 改用 risk_free_rate=0.02"
mutate "$TEST_VB" '        prices, proba, atr, _default_params(), timeframe="1h", risk_free_rate=0.0
    )
    default = vb.run_backtest(prices, proba, atr, _default_params(), risk_free_rate=0.0)' \
'        prices, proba, atr, _default_params(), timeframe="1h", risk_free_rate=0.02
    )
    default = vb.run_backtest(prices, proba, atr, _default_params(), risk_free_rate=0.02)' || exit 1
run_expect_red "§V-13" "${TEST_VB}::test_sharpe_ratio_diverges_by_sqrt_ratio_with_zero_rf"

echo "[verify] 還原後應無 mutant 殘留且全綠"
restore_all
grep -rn "MUTANT" "$FREQ" "$SHARPE" "$TEST_VB" && { echo "  🔴 有 mutant 殘留"; exit 1; }
"$PY" -m pytest "$TEST_FREQ" "$TEST_SHARPE" "$TEST_VB" -q > /tmp/gap1_mut.log 2>&1
echo "  post-restore rc=$? ($(tail -1 /tmp/gap1_mut.log))"

if [ "$FAILED_DESIGN" -ne 0 ]; then
  echo "[gap1-b1-mutation] 🔴 有 mutation 未通過「可證偽」判準"
  exit 1
fi
echo "[gap1-b1-mutation] ✅ 全部 mutation 皆使測試轉紅（rc=1 斷言失敗）"
