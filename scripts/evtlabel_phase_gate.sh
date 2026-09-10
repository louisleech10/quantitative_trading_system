#!/usr/bin/env bash
# evtlabel_phase_gate.sh — EVTLABEL 之 Phase Gate（機械可驗，非散文；沿 evtalign_phase_gate.sh）
#
# 三項任一失敗即 rc≠0：
#   ① 該 Phase 對應之測試檔仍有 skip（skip 不是綠）
#   ② golden glob 命中 0 個檔（空迴圈假綠；Phase≥2）
#   ③ mutation 腳本回報 UNCOVERED ≠ 0（SKIP 計入 UNCOVERED；Phase≥1）
#
# 用法：bash scripts/evtlabel_phase_gate.sh <0|1|2|3a|3b|3c>
# 憲法：rc 直接取禁經 pipe；bash 3.2；每道守衛 || fail。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
PY="venv/bin/python"

phase="${1:-}"
[ -n "${phase}" ] || { echo "用法: bash scripts/evtlabel_phase_gate.sh <0|1|2|3a|3b|3c>" >&2; exit 2; }

# Phase → 測試檔（TODO §B 之對照；新增 Phase 時在此加一行，不加即 rc=2）
case "${phase}" in
  0)  tests="" ;;
  1)  tests="tests/api/test_evtlabel_disclosure.py" ;;
  2)  tests="tests/momentum/event_samples/test_isolation_terms.py tests/momentum/Analysis/test_evtlabel_isolation_channel.py tests/momentum/core/test_holdout_test_row_index.py tests/api/test_isolation_disclosure.py" ;;
  3a) tests="tests/momentum/Analysis/test_event_label_mode_contract.py tests/api/test_evtlabel_staging.py" ;;
  3b) tests="tests/momentum/Analysis/test_evtlabel_stage3.py tests/momentum/Analysis/test_binary_discrimination.py tests/momentum/Analysis/test_evtlabel_stage5.py tests/momentum/Analysis/test_evtlabel_oracle.py" ;;
  3c) tests="tests/momentum/Analysis/test_evtlabel_e2e_realkline.py tests/momentum/Analysis/test_evtlabel_survivor_consumer.py" ;;
  *) echo "GATE FAIL: 未知 phase=${phase}（新 Phase 須先登記於本腳本）" >&2; exit 2 ;;
esac

# mutation phase 映射
# 🔴 2026-09-10 修正：原本 3a/3b/3c 一律映射成 "3"，意思是「B3 收案時要對 B4／B5 才會寫的
#    程式做自證」——那些檔案當下還不存在 ⇒ 全部 SKIP ⇒ UNCOVERED=999 ⇒ 關卡恆紅，
#    而且是**無法在該批解決**的紅。自證必須與批次同粒度，各批只證自己那一批的程式。
case "${phase}" in
  3a|3b|3c) mphase="${phase}" ;;
  *) mphase="${phase}" ;;
esac

fail=0

# ── 0：artifact 必須存在（Task 0.1）──────────────────────────────────
for p in scripts/evtlabel_phase_gate.sh handoffs/20260910-evtlabel-mutate.py \
         handoffs/20260910-probe-label-rule.py handoffs/20260910-probe-mw-bench.py \
         handoffs/20260910-probe-oracle-bench.py tests/golden/evtlabel; do
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

# ── ①b：真實規模 benchmark（Task 3.7 驗證 (a)/(b)；`COMPOSER-R1-P2-02` 要求持久 gate）──
#    🔴 一次性 receipt 擋不住「未來欄數膨脹時重犯」——本關卡讓它每批都跑一次。
#    探針自身在超過門檻時回 rc≠0（含 10% NaN 路徑，`GROK-R1-P1-03` 實測情境）。
case "${phase}" in
  3b|3c)
    if ! "${PY}" handoffs/20260910-probe-oracle-bench.py > /tmp/evtlabel_oracle_bench.out 2>&1; then
      echo "GATE FAIL: oracle benchmark 超出門檻（見 /tmp/evtlabel_oracle_bench.out）"
      grep -E '^\(a\)|^\(b\)|^\(c\)|OVER LIMIT' /tmp/evtlabel_oracle_bench.out || true
      fail=1
    fi
    ;;
esac

# ── ②：golden glob 非空（Phase≥2；G-2 事件切分 golden 沿 evtalign，G-6 survivor golden 於 B4 前凍結）──
case "${phase}" in
  2)
    ngold=0
    for g in tests/golden/evtalign/*.json; do [ -e "${g}" ] && ngold=$((ngold+1)); done
    if [ "${ngold}" -eq 0 ]; then echo "GATE FAIL: tests/golden/evtalign/*.json 命中 0 個（空迴圈假綠）"; fail=1; fi
    ;;
  3b|3c)
    ngold=0
    for g in tests/golden/evtlabel/*.json; do [ -e "${g}" ] && ngold=$((ngold+1)); done
    if [ "${ngold}" -eq 0 ]; then echo "GATE FAIL: tests/golden/evtlabel/*.json 命中 0 個（G-6 未凍結）"; fail=1; fi
    ;;
esac

# ── ③：mutation UNCOVERED 必須為 0（Phase≥1）──────────────────────────
if [ "${phase}" != "0" ]; then
  mout="$("${PY}" handoffs/20260910-evtlabel-mutate.py --phase "${mphase}" 2>&1)"
  mrc=$?
  unc="$(printf '%s\n' "${mout}" | sed -n 's/^UNCOVERED=\([0-9]*\).*/\1/p' | tail -1)"
  if [ "${mrc}" -ne 0 ]; then echo "GATE FAIL: mutation rc=${mrc}"; fail=1; fi
  if [ -z "${unc}" ] || [ "${unc}" -ne 0 ]; then echo "GATE FAIL: mutation UNCOVERED=${unc:-?}（SKIP 不計入通過）"; fail=1; fi
fi

if [ "${fail}" -eq 0 ]; then echo "GATE PASS: phase=${phase}"; exit 0; fi
echo "GATE FAIL: phase=${phase}"; exit 1
