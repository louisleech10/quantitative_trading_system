#!/usr/bin/env bash
# evtalign_phase_gate.sh — EVTALIGN 之 Phase Gate（機械可驗，非散文）
#
# 為何存在（R1 `CODEX-R1-P1-05`／`COMPOSER-R1-P2-02`／`GROK-R1-P1-04` 三家獨立命中）：
#   Task 0.1 允許 placeholder 用 `pytest.skip`，而「skip 不算通過」若只靠人工讀 `-rs` 清單，
#   執行端跑前半 `pytest -q` 得 rc=0 即可假綠交件。⇒ 本腳本把三件事變成 rc。
#
# 三項任一失敗即 rc≠0：
#   ① 該 Phase 對應之測試檔仍有 skip
#   ② golden glob 命中 0 個檔（空迴圈假綠）
#   ③ mutation 腳本回報 uncovered ≠ 0（SKIP 不計入通過）
#
# 用法：bash scripts/evtalign_phase_gate.sh <0|1|2|3|4|5>
# 憲法：rc 直接取禁經 pipe；bash 3.2；每道守衛 || fail。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
PY="venv/bin/python"

phase="${1:-}"
[ -n "${phase}" ] || { echo "用法: bash scripts/evtalign_phase_gate.sh <phase>" >&2; exit 2; }

# Phase → 測試檔（TODO §B 之對照；新增 Phase 時在此加一行，不加即 rc=2）
case "${phase}" in
  0) tests="" ;;   # scaffold：本 Phase 之「通過」＝ artifact 存在，見下方 exists 檢查
  1) tests="tests/momentum/test_close_coterminalize.py tests/api/test_event_label_alignment.py" ;;
  2) tests="tests/momentum/test_validated_series_is_used_series.py" ;;
  3) tests="tests/api/test_period_auto_align.py" ;;
  4) tests="tests/api/test_stage_progress.py" ;;
  5) tests="tests/api/test_isolation_disclosure.py" ;;
  *) echo "GATE FAIL: 未知 phase=${phase}（新 Phase 須先登記於本腳本）" >&2; exit 2 ;;
esac

fail=0

# ── 0：五個 artifact 必須存在（Task 0.1）──────────────────────────────
for p in scripts/evtalign_phase_gate.sh handoffs/20260907-evtalign-mutate.py \
         handoffs/20260907-probe-split-baseline.py tests/golden/evtalign; do
  if [ ! -e "${p}" ]; then echo "GATE FAIL: 缺 artifact ${p}"; fail=1; fi
done

# ── ①：該 Phase 之測試不得有 skip ─────────────────────────────────────
if [ -n "${tests}" ]; then
  for t in ${tests}; do
    if [ ! -f "${t}" ]; then echo "GATE FAIL: 測試檔不存在 ${t}"; fail=1; continue; fi
    out="$("${PY}" -m pytest "${t}" -q -rs -p no:cacheprovider 2>&1)"
    rc=$?
    nskip="$(printf '%s\n' "${out}" | grep -c '^SKIPPED')"
    if [ "${rc}" -ne 0 ]; then echo "GATE FAIL: ${t} pytest rc=${rc}"; fail=1; fi
    if [ "${nskip}" -gt 0 ]; then echo "GATE FAIL: ${t} 仍有 ${nskip} 條 skip（skip 不是綠）"; fail=1; fi
  done
fi

# ── ②：golden glob 非空 ───────────────────────────────────────────────
ngold=0
for g in tests/golden/evtalign/*.json; do [ -e "${g}" ] && ngold=$((ngold+1)); done
if [ "${ngold}" -eq 0 ]; then echo "GATE FAIL: tests/golden/evtalign/*.json 命中 0 個（空迴圈假綠）"; fail=1; fi
# golden 自證（改前基線必須仍與碼一致；Phase≥1 時允許差異由測試對照，此處只驗檔案可讀）
"${PY}" handoffs/20260907-probe-split-baseline.py > /tmp/evtalign_gate_golden.log 2>&1
grc=$?
if [ "${phase}" = "0" ] && [ "${grc}" -ne 0 ]; then echo "GATE FAIL: golden 基線自證 rc=${grc}"; fail=1; fi

# ── ③：mutation uncovered 必須為 0（Phase≥1）──────────────────────────
if [ "${phase}" != "0" ]; then
  mout="$("${PY}" handoffs/20260907-evtalign-mutate.py --phase "${phase}" 2>&1)"
  mrc=$?
  unc="$(printf '%s\n' "${mout}" | sed -n 's/^UNCOVERED=\([0-9]*\).*/\1/p' | tail -1)"
  if [ "${mrc}" -ne 0 ]; then echo "GATE FAIL: mutation rc=${mrc}"; fail=1; fi
  if [ -z "${unc}" ] || [ "${unc}" -ne 0 ]; then echo "GATE FAIL: mutation UNCOVERED=${unc:-?}（SKIP 不計入通過）"; fail=1; fi
fi

if [ "${fail}" -eq 0 ]; then echo "GATE PASS: phase=${phase}"; exit 0; fi
echo "GATE FAIL: phase=${phase}"; exit 1
