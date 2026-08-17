#!/usr/bin/env bash
# gap1_b1_mutation_probe.sh — B1／B2 之 mutation 自證（§V-5／8／9a／9b／10／13／15 ＋ §V-7／7b／7c／7d／7e）。
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
#
# 🔴 第三個缺陷（2026-08-18 由 codex 兩度 BLOCKED 抓到，本版修）：
#   本探針**就地 mutate 共用工作區**，故**不可並行**。B1 戳記輪 brief 叫三家都跑，
#   三個 agent 同時 mutate 同一批檔 ⇒ 彼此看到對方的 mutant，baseline 不穩定
#   （codex 實測：一次 98 passed/1 failed、一次 89 passed/10 failed，失敗集合不同）。
#   ⇒ 本版加**互斥鎖**（`mkdir` 為原子操作，macOS/Linux 皆可；不依賴 flock）：
#   已有人在跑就直接 exit 3 並印出鎖持有者，而不是產生無意義的紅。
#   鎖為 fail-closed：取不到鎖絕不繼續跑。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2

LOCK_DIR=".claude/gate/gap1_mutation_probe.lock"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "🔴 探針已有另一個執行實例（鎖: ${LOCK_DIR}）。" >&2
  echo "   本探針就地 mutate 共用工作區 ⇒ **不可並行**（並行會使 baseline 不穩定，" >&2
  echo "   委員曾因此看到彼此的 mutant 而誤判）。請等對方跑完，或讀既有 receipt：" >&2
  ls -t handoffs/run_receipts/*mutation*.log 2>/dev/null | head -3 >&2
  [ -f "${LOCK_DIR}/owner" ] && cat "${LOCK_DIR}/owner" >&2
  exit 3
fi
printf 'pid=%s started=%s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "${LOCK_DIR}/owner"
_release_lock() { rm -rf "${LOCK_DIR}"; }

PY=venv/bin/python
FREQ=momentum/core/frequency.py
SHARPE=momentum/Analysis/strategy_validation/sharpe.py
RC=momentum/Analysis/strategy_validation/returns_contract.py
LEDGER=momentum/Analysis/strategy_validation/ledger.py
TEST_FREQ=tests/momentum/Analysis/strategy_validation/test_frequency.py
TEST_SHARPE=tests/momentum/Analysis/strategy_validation/test_sharpe.py
TEST_RC=tests/momentum/Analysis/strategy_validation/test_returns_contract.py
TEST_LEDGER=tests/momentum/Analysis/strategy_validation/test_ledger.py
TEST_LEDGER_CONF=tests/momentum/Analysis/strategy_validation/test_ledger_conformance.py
TEST_LEDGER_PATH=tests/momentum/Analysis/strategy_validation/test_ledger_path.py
TEST_VB=tests/momentum/Strategy/test_vectorized_backtest.py
# baseline／post-restore 之測試集合（單一定義，兩處共用；A1-21 L10 起含 B2 三檔）
ALL_TESTS="${TEST_FREQ} ${TEST_SHARPE} ${TEST_RC} ${TEST_LEDGER} ${TEST_LEDGER_CONF} ${TEST_LEDGER_PATH} ${TEST_VB}"

TARGETS="${FREQ} ${SHARPE} ${RC} ${LEDGER} ${TEST_VB}"
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
cleanup() { restore_all; rm -rf "${BACKUP_DIR}"; _release_lock; }
trap cleanup EXIT

backup_all

FAILED_DESIGN=0

run_expect_red() {  # <label> <test-target>
  _label="$1"; _target="$2"
  "$PY" -m pytest ${_target} -q > /tmp/gap1_mut.log 2>&1  # 不加引號：允許多個測試目標（路徑無空白）
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

echo "[baseline] 未 mutate 時各檔應全綠（🔴 K2：baseline 紅即 fail-closed 退出，不得續跑）"
"$PY" -m pytest ${ALL_TESTS} -q > /tmp/gap1_mut.log 2>&1
_base_rc=$?          # 🔴 rc 直接取，禁經 pipe
echo "  baseline rc=${_base_rc} ($(tail -1 /tmp/gap1_mut.log))"
if [ "${_base_rc}" -ne 0 ]; then
  echo "  🔴 baseline 非綠 ⇒ mutation 之前提不成立（改壞才紅之判準失去意義）。中止。" >&2
  tail -20 /tmp/gap1_mut.log >&2
  exit 1
fi

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

echo "[§V-9a] returns_contract：bar_count 改回 status=ok（該語意膨脹 √(T-1)，必須非 ok）"
mutate "$RC" '            _REASON_T_SEMANTICS_INFLATES,
            status="not_applicable",' '            _REASON_T_SEMANTICS_INFLATES,
            status="ok",' || exit 1
run_expect_red "§V-9a" "$TEST_RC"

echo "[§V-9b] returns_contract：拿掉 source != resolved 之守衛（放行 default_730）"
mutate "$RC" '    if source != "resolved":' '    if False:  # source != "resolved"' || exit 1
run_expect_red "§V-9b" "$TEST_RC"

echo "[§V-7] read_trial_ledger 缺檔時回 n=1（而非 fail-closed n_unknown）"
mutate "$LEDGER" "    if not path.is_file():
        return _unavailable()" "    if not path.is_file():
        return _unavailable().__class__(**{**_unavailable().__dict__, 'n_candidates_considered': 1, 'n_for_dsr': 1, 'status': 'ok', 'reason': ''})" || exit 1
run_expect_red "§V-7" "$TEST_LEDGER"

echo "[§V-7b] _row_problems 拿掉 isfinite（NaN／inf 之 metric_value 放行）"
mutate "$LEDGER" '        if spec["type"] == "float" and not math.isfinite(value):' '        if False:  # MUTANT: isfinite removed' || exit 1
run_expect_red "§V-7b" "$TEST_LEDGER $TEST_LEDGER_CONF"

echo "[§V-7c] _snapshot_hash 改回裸 | 拼接（可碰撞之舊法）"
mutate "$LEDGER" '    payload = json.dumps(
        [sorted(artifact_hashes), dataset_key, research_session_id],
        separators=(",", ":"),
        ensure_ascii=False,
    )' '    payload = ",".join(sorted(artifact_hashes)) + "|" + dataset_key + "|" + research_session_id  # MUTANT' || exit 1
run_expect_red "§V-7c" "$TEST_LEDGER"

echo "[§V-7d] ledger_path 目錄字面改名（真實路徑推導須有回歸鎖）"
mutate "$LEDGER" '_LEDGER_DIRNAME = "strategy_validation"' '_LEDGER_DIRNAME = "strategy_validation_MUTANT"' || exit 1
run_expect_red "§V-7d" "$TEST_LEDGER_PATH"

echo "[§V-7e] 拿掉 flock（掃描＋寫入不再原子 ⇒ 同 id 可雙寫）"
mutate "$LEDGER" '        fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)' '        pass  # MUTANT: flock removed' || exit 1
run_expect_red "§V-7e" "$TEST_LEDGER_CONF"

echo "[verify] 還原後應無 mutant 殘留且全綠（🔴 K2：任一不成立即 exit 1）"
restore_all
if grep -rn "MUTANT" "$FREQ" "$SHARPE" "$RC" "$LEDGER" "$TEST_VB"; then
  echo "  🔴 有 mutant 殘留 ⇒ 還原機制失效（首版即因 git checkout 對未追蹤檔無效而發生）" >&2
  exit 1
fi
"$PY" -m pytest ${ALL_TESTS} -q > /tmp/gap1_mut.log 2>&1
_post_rc=$?          # 🔴 rc 直接取，禁經 pipe
echo "  post-restore rc=${_post_rc} ($(tail -1 /tmp/gap1_mut.log))"
if [ "${_post_rc}" -ne 0 ]; then
  echo "  🔴 還原後非綠 ⇒ 探針弄髒了工作區。中止。" >&2
  tail -20 /tmp/gap1_mut.log >&2
  exit 1
fi

if [ "$FAILED_DESIGN" -ne 0 ]; then
  echo "[gap1-b1-mutation] 🔴 有 mutation 未通過「可證偽」判準"
  exit 1
fi
echo "[gap1-b1-mutation] ✅ 全部 12 條 mutation 皆使測試轉紅（rc=1 斷言失敗）"
