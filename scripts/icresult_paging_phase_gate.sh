#!/usr/bin/env bash
# icresult_paging_phase_gate.sh — ICRESULT_PAGING 之 Phase Gate（docs/ICRESULT_PAGING_SPEC.md §V／§G）
# phase 1：pytest tests/api/test_icresult_paging.py 無 skip ＋ golden --check ＋ mutation UNCOVERED=0 ＋ 探針 --size 三態
# phase 3：探針 --size 與 --latency 皆須 PASS
# 三態解析（SIZE_GATE／LATENCY_GATE 各自）：恰一行；FAIL ⇒ rc=1；BLOCKED ⇒ 轉印不改 rc（phase 3 例外：須 PASS）；PASS ⇒ 繼續；缺行／多行／未知 ⇒ rc=1
# 用法：bash scripts/icresult_paging_phase_gate.sh <1|3>；bash scripts/icresult_paging_phase_gate.sh --parse <TOKEN> <file> [--require-pass]
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
PY="venv/bin/python"

parse_token() {  # $1=TOKEN $2=file $3=require_pass(0/1) → 印狀態；rc 0/1
  local tok="$1" f="$2" req="${3:-0}" n val
  n="$(grep -c "^${tok}=" "${f}" 2>/dev/null)"
  if [ "${n}" != "1" ]; then echo "GATE FAIL: ${tok} 行數=${n}（須恰 1）"; return 1; fi
  val="$(sed -n "s/^${tok}=//p" "${f}" | head -1)"
  case "${val}" in
    PASS) echo "${tok}=PASS"; return 0 ;;
    FAIL) echo "GATE FAIL: ${tok}=FAIL"; return 1 ;;
    BLOCKED) echo "${tok}=BLOCKED"; if [ "${req}" = "1" ]; then echo "GATE FAIL: ${tok} 須 PASS"; return 1; fi; return 0 ;;
    *) echo "GATE FAIL: ${tok} 未知值 '${val}'"; return 1 ;;
  esac
}

if [ "${1:-}" = "--parse" ]; then
  req=0; [ "${4:-}" = "--require-pass" ] && req=1
  parse_token "${2:-}" "${3:-}" "${req}"; exit $?
fi

phase="${1:-}"
[ -n "${phase}" ] || { echo "用法: bash scripts/icresult_paging_phase_gate.sh <1|3>" >&2; exit 2; }
fail=0
case "${phase}" in
  1)
    t="tests/api/test_icresult_paging.py"
    if [ ! -f "${t}" ]; then echo "GATE FAIL: 測試檔不存在 ${t}"; fail=1
    else
      out="$("${PY}" -m pytest "${t}" -q -rs -p no:cacheprovider 2>&1)"; rc=$?
      nskip="$(printf '%s\n' "${out}" | grep -c '^SKIPPED')"
      [ "${rc}" -ne 0 ] && { echo "GATE FAIL: ${t} pytest rc=${rc}"; fail=1; }
      [ "${nskip}" -gt 0 ] && { echo "GATE FAIL: ${t} 仍有 ${nskip} 條 skip"; fail=1; }
    fi
    "${PY}" handoffs/20260909-probe-icresult-golden.py --check > .claude/gate/icresult_golden_check.out 2>&1; grc=$?
    [ "${grc}" -ne 0 ] && { echo "GATE FAIL: golden --check rc=${grc}"; tail -3 .claude/gate/icresult_golden_check.out; fail=1; }
    mout="$("${PY}" handoffs/20260909-icresult-paging-mutate.py --phase 1 2>&1)"; mrc=$?
    unc="$(printf '%s\n' "${mout}" | sed -n 's/^UNCOVERED=\([0-9]*\).*/\1/p' | tail -1)"
    [ "${mrc}" -ne 0 ] && { echo "GATE FAIL: mutation rc=${mrc}"; printf '%s\n' "${mout}" | grep -E '^(FAIL|SKIP|REFUSE)'; fail=1; }
    { [ -z "${unc}" ] || [ "${unc}" -ne 0 ]; } && { echo "GATE FAIL: mutation UNCOVERED=${unc:-?}"; fail=1; }
    "${PY}" handoffs/20260909-probe-icresult-size.py > .claude/gate/icresult_size.out 2>&1
    parse_token SIZE_GATE .claude/gate/icresult_size.out 0 || fail=1
    ;;
  3)
    "${PY}" handoffs/20260909-probe-icresult-size.py > .claude/gate/icresult_size.out 2>&1
    parse_token SIZE_GATE .claude/gate/icresult_size.out 1 || fail=1
    "${PY}" handoffs/20260909-probe-icresult-size.py --latency > .claude/gate/icresult_latency.out 2>&1
    parse_token LATENCY_GATE .claude/gate/icresult_latency.out 1 || fail=1
    ;;
  *) echo "GATE FAIL: 未知 phase=${phase}" >&2; exit 2 ;;
esac
if [ "${fail}" -eq 0 ]; then echo "GATE PASS: phase=${phase}"; exit 0; fi
echo "GATE FAIL: phase=${phase}"; exit 1
