#!/usr/bin/env bash
# evtwarmup_phase_gate.sh — EVTWARMUP／TFWINDOW 之 Phase Gate（同 evtalign_phase_gate.sh 型）
# ① 該 Phase 測試檔無 skip ② golden 非空且自證 ③ mutation UNCOVERED=0
# 用法：bash scripts/evtwarmup_phase_gate.sh <1|3>；rc 直接取禁經 pipe。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
PY="venv/bin/python"
phase="${1:-}"
[ -n "${phase}" ] || { echo "用法: bash scripts/evtwarmup_phase_gate.sh <phase>" >&2; exit 2; }
case "${phase}" in
  1) tests="tests/api/test_evtwarmup.py" ;;
  3) tests="tests/api/test_tfwindow.py" ;;
  *) echo "GATE FAIL: 未知 phase=${phase}" >&2; exit 2 ;;
esac
fail=0
for t in ${tests}; do
  if [ ! -f "${t}" ]; then echo "GATE FAIL: 測試檔不存在 ${t}"; fail=1; continue; fi
  out="$("${PY}" -m pytest "${t}" -q -rs -p no:cacheprovider 2>&1)"; rc=$?
  nskip="$(printf '%s\n' "${out}" | grep -c '^SKIPPED')"
  if [ "${rc}" -ne 0 ]; then echo "GATE FAIL: ${t} pytest rc=${rc}"; fail=1; fi
  if [ "${nskip}" -gt 0 ]; then echo "GATE FAIL: ${t} 仍有 ${nskip} 條 skip"; fail=1; fi
done
ngold=0; for g in tests/golden/evtwarmup/*.json; do [ -e "${g}" ] && ngold=$((ngold+1)); done
if [ "${ngold}" -eq 0 ]; then echo "GATE FAIL: tests/golden/evtwarmup/*.json 命中 0 個"; fail=1; fi
mout="$("${PY}" handoffs/20260908-evtwarmup-mutate.py --phase "${phase}" 2>&1)"; mrc=$?
unc="$(printf '%s\n' "${mout}" | sed -n 's/^UNCOVERED=\([0-9]*\).*/\1/p' | tail -1)"
if [ "${mrc}" -ne 0 ]; then echo "GATE FAIL: mutation rc=${mrc}"; printf '%s\n' "${mout}" | grep -E '^(FAIL|SKIP|REFUSE)'; fail=1; fi
if [ -z "${unc}" ] || [ "${unc}" -ne 0 ]; then echo "GATE FAIL: mutation UNCOVERED=${unc:-?}"; fail=1; fi
if [ "${fail}" -eq 0 ]; then echo "GATE PASS: phase=${phase}"; exit 0; fi
echo "GATE FAIL: phase=${phase}"; exit 1
