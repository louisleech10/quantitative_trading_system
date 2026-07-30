#!/usr/bin/env bash
# B4 獨立驗收（主委端，不採信實作端自報）
#
# 群集 W 修法（2026-07-30 FIX3）：每一道守衛皆須有行為 oracle。
# 禁止僅以「檔案存在 / bash -n / grep -c def test_mutation_」當通過條件。
# product mutant（return 0 / sys.exit→continue / 拔 harness 綁定）必須使對應
# 具名 surface／mutation 測試轉紅，且訊號專屬（非聚合計數）。
#
# 承接：
#   - debt_ledger.sh / debt_clear.sh 存在且語法 OK（廉價前置）
#   - 未動 gate.sh（B5 標的）
#   - 反 bypass：DEBT_LEDGER_SOURCED 行為等同未設
#   - abandon_kind 無硬編 fallback（行為：空 enum → rc=2）
#   - 六道銷帳守衛：pytest mutation 三態 + surface reject 實跑
#   - ledger：malformed／sequence／duplicate／empty-enum／sourced／override-harness
#   - 1b 六項 rebuild 實跑
#   - mutation_probe_check 非空心
#   - 既有測試斷言未被刪
#
# 探針：一律 repo-local handoffs/（禁 /tmp）；本腳本不就地變異產品檔。
set -uo pipefail
fail=0
ok(){ printf '  ✅ %s\n' "$1"; }
bad(){ printf '  ❌ %s\n' "$1"; fail=1; }

# repo-local probe（禁 /tmp；sandbox 拒外部；收尾清除）
PROBE="handoffs/_b4_verify_probe_$$"
mkdir -p "${PROBE}"
cleanup() { rm -rf "${PROBE}"; }
trap cleanup EXIT

# 選 python：優先 venv
if [ -x "venv/bin/python" ]; then
  PY="venv/bin/python"
elif [ -x "venv/bin/python3" ]; then
  PY="venv/bin/python3"
else
  PY="python3"
fi

_run_pytest() {
  # $1 = nodeid 或 path；stdout/err → $2 log；把 rc 印到 stdout 供 $() 擷取
  # rc 直接取，禁經 pipe。不用 set -e，避免污染呼叫端 shell 狀態。
  local target="$1"
  local logf="$2"
  local rc
  env -u ROUND_ID "${PY}" -m pytest "${target}" -q --tb=line >"${logf}" 2>&1
  rc=$?
  printf '%s\n' "${rc}"
}

# 跑單一具名 surface／mutation；失敗時印專屬標籤（供「一道一訊號」）
# $1=標籤 $2=nodeid
_run_named() {
  local label="$1"
  local nodeid="$2"
  local logf="${PROBE}/named_$(echo "${label}" | tr '/: ' '___').log"
  local rc
  rc="$(_run_pytest "${nodeid}" "${logf}")"
  if [ "${rc}" -eq 0 ]; then
    ok "oracle ${label} PASS (${nodeid##*::})"
    return 0
  fi
  bad "oracle ${label} FAIL rc=${rc} nodeid=${nodeid##*::}"
  tail -8 "${logf}" | sed 's/^/    /'
  return 1
}

echo "=== 0. B4 檔案與語法（廉價前置，非單獨通過條件）==="
for f in scripts/debt_ledger.sh scripts/debt_clear.sh; do
  if [ -f "${f}" ]; then
    ok "$(basename "${f}") 存在"
    bash -n "${f}" && ok "$(basename "${f}") 語法 OK" || bad "$(basename "${f}") 語法錯"
  else
    bad "缺 ${f}"
  fi
done

echo "=== 1. 未動 gate.sh（B5）==="
git diff --name-only -- scripts/gate.sh | grep -q . && bad "動了 gate.sh（屬 B5）" || ok "未動 gate.sh"

echo "=== 2. 反 bypass：DEBT_LEDGER_SOURCED 不得改變行為（行為 oracle）==="
# 可執行碼不得引用該 env（註解禁令除外）
if grep -E '^[^#]*DEBT_LEDGER_SOURCED' scripts/debt_ledger.sh scripts/debt_clear.sh 2>/dev/null \
  | grep -vE '^\s*#' | grep -qE 'DEBT_LEDGER_SOURCED'; then
  bad "可執行碼仍引用 DEBT_LEDGER_SOURCED（須只靠 BASH_SOURCE）"
else
  ok "可執行碼未引用 DEBT_LEDGER_SOURCED"
fi
# 行為：audit 缺失時，設與不設 env 皆須 rc=2 + 相同缺失訊息
# rc 直接取（寫檔再 cat），禁經 pipe 吞 rc
_missing_audit="${PROBE}/missing-audit.log"
_out1="${PROBE}/sourced_on.out"
_out2="${PROBE}/sourced_off.out"
rm -f "${_missing_audit}" "${_out1}" "${_out2}"
GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="${_missing_audit}" \
  DEBT_LEDGER_SOURCED=1 bash scripts/debt_ledger.sh --has-open >"${_out1}" 2>&1
rc1=$?
GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="${_missing_audit}" \
  bash scripts/debt_ledger.sh --has-open >"${_out2}" 2>&1
rc2=$?
if [ "${rc1}" -eq 2 ] && [ "${rc2}" -eq 2 ] \
  && grep -q 'audit' "${_out1}" \
  && grep -q 'audit' "${_out2}"; then
  ok "DEBT_LEDGER_SOURCED=1 與未設 行為相同（audit 缺失 rc=2 + 訊息）"
else
  bad "DEBT_LEDGER_SOURCED bypass 仍活（sourced=1 rc=${rc1} / unset rc=${rc2}）"
fi

echo "=== 3. abandon_kind 無硬編 fallback（行為 oracle）==="
# 廉價前置：abandoned_count 路徑無 or ["no-findings 硬編
if awk '/mode == "abandoned_count"/,/sys.exit\(0\)/' scripts/debt_ledger.sh \
  | grep -qE 'or \[\s*"no-findings'; then
  bad "abandoned_count 仍有 or [...] 硬編 fallback"
else
  ok "abandoned_count 靜態無硬編 enum fallback"
fi
# 行為：空 enum registry → --abandoned-count 須 rc=2 + 專屬訊息
if ! _run_named "ledger/empty-enum" \
  "tests/governance/test_debt_ledger.py::test_abandoned_count_empty_enum_fail_closed"; then
  :
fi

echo "=== 4. 六道銷帳守衛 mutation 三態（行為 oracle，非 count）==="
# 廉價前置：至少 6 個 test_mutation_* 名稱（不得單獨通過）
n_mut=$(grep -cE '^def test_mutation_' tests/governance/test_debt_clear.py || true)
if [ "${n_mut}" -ge 6 ]; then
  ok "前置：test_debt_clear 有 ${n_mut} 個 test_mutation_* 名稱（≥6）"
else
  bad "前置：test_debt_clear 僅 ${n_mut} 個 mutation 探針名稱"
fi
# 行為：逐道實跑 baseline reject → mutant pass → restore reject
# 標籤 = 守衛名（專屬訊號）
_mut_fail=0
# shell 3.2：不用 mapfile／associative array
for pair in \
  "_assert_lock_mode_is_review|test_mutation_mode_review_guard" \
  "_assert_round_is_OPEN|test_mutation_open_guard" \
  "_run_completeness|test_mutation_completeness_guard" \
  "_assert_identity_binding|test_mutation_identity_binding_guard" \
  "_assert_roster_equals|test_mutation_roster_equals_guard" \
  "_assert_all_families_success_and_sha_match|test_mutation_family_sha_guard"
do
  guard="${pair%%|*}"
  t="${pair##*|}"
  if ! _run_named "clear-mut/${guard}" \
    "tests/governance/test_debt_clear.py::${t}"; then
    _mut_fail=1
  fi
done
[ "${_mut_fail}" -eq 0 ] && ok "六道 mutation 三態全綠（真實行為序列）" || true

echo "=== 4b. 六道守衛 surface reject（打真 product 路徑；product 閹割→對應道轉紅）==="
# 若 product 某守衛被 return 0 閹割，下列對應測會紅 → verify 轉紅
# 專屬訊號 = 該 surface 測試名（非聚合）
_surf_fail=0
for pair in \
  "_assert_lock_mode_is_review|test_clear_discovery_mode_rejected" \
  "_assert_round_is_OPEN|test_abandoned_then_clear_rejected" \
  "_run_completeness|test_clear_completeness_fail" \
  "_assert_identity_binding|test_clear_wrong_round_id_binding" \
  "_assert_roster_equals|test_clear_roster_mismatch" \
  "_assert_all_families_success_and_sha_match|test_clear_output_tampered_sha"
do
  guard="${pair%%|*}"
  t="${pair##*|}"
  if ! _run_named "clear-surf/${guard}" \
    "tests/governance/test_debt_clear.py::${t}"; then
    _surf_fail=1
  fi
done
[ "${_surf_fail}" -eq 0 ] && ok "六道 surface reject 全綠" || true

echo "=== 5. mutation_probe_check（非空心探針）==="
bash scripts/mutation_probe_check.sh tests/governance/test_debt_clear.py \
  >"${PROBE}/mpc.log" 2>&1
rc_mpc=$?
if [ "${rc_mpc}" -eq 0 ]; then
  ok "mutation_probe_check test_debt_clear.py rc=0"
else
  bad "mutation_probe_check rc=${rc_mpc}"
  tail -10 "${PROBE}/mpc.log" | sed 's/^/    /'
fi

echo "=== 6. 1b 六項 rebuild 實跑（非 count/grep）==="
_rb_fail=0
for t in \
  test_rebuild_1b_happy_path_harness_unset \
  test_rebuild_1b_without_flag_rejected \
  test_rebuild_1b_review_to_discovery_rejected \
  test_rebuild_1b_closed_round_rejected \
  test_rebuild_1b_audit_zero_rejected \
  test_rebuild_1b_audit_many_rejected
do
  if ! _run_named "rebuild/${t}" \
    "tests/governance/test_debt_clear.py::${t}"; then
    _rb_fail=1
  fi
done
[ "${_rb_fail}" -eq 0 ] && ok "1b 六項全綠" || true

echo "=== 7. ledger 關鍵守衛（每道具名 surface／mutation；補齊 malformed／sequence／override）==="
# CODEX-R3-P1-01：舊 verifier 漏跑 malformed／sequence → product 閹割仍 PASS
# unbound override：DEBT_*_OVERRIDE 必須綁 GOVERNANCE_TEST_HARNESS=1
_led_fail=0
for pair in \
  "ledger/malformed-json|test_malformed_json_line_fail_closed" \
  "ledger/sequence-gap|test_sequence_gap_fail_closed" \
  "ledger/sequence-dup|test_sequence_dup_fail_closed" \
  "ledger/duplicate-open|test_duplicate_open_same_round_fail_closed" \
  "ledger/round-exists-dup|test_round_exists_single_rejects_duplicate_open" \
  "ledger/sourced-env|test_debt_ledger_sourced_env_ignored_missing_audit" \
  "ledger/override-harness|test_cutoff_override_requires_harness" \
  "ledger/mut-malformed|test_mutation_malformed_json_guard"
do
  label="${pair%%|*}"
  t="${pair##*|}"
  if ! _run_named "${label}" \
    "tests/governance/test_debt_ledger.py::${t}"; then
    _led_fail=1
  fi
done
# FIX4：duplicate-open 改綁 build_rounds 路徑；round-exists-dup 另護 _round_exists_single（兩道獨立守衛）
[ "${_led_fail}" -eq 0 ] && ok "ledger 八道具名 oracle 全綠" || true

echo "=== 7b. ledger 隔離副本探針（禁就地變異產品；證 malformed 三態 + override harness）==="
# 探針副本：handoffs/_b4_verify_probe_$$/ledger_iso/；只改副本
_ISO="${PROBE}/ledger_iso"
mkdir -p "${_ISO}/scripts" "${_ISO}/audit"
cp scripts/debt_ledger.sh "${_ISO}/scripts/debt_ledger.sh"
cp scripts/audit_events.json "${_ISO}/scripts/audit_events.json" 2>/dev/null || true
chmod +x "${_ISO}/scripts/debt_ledger.sh"
_iso_src="${_ISO}/scripts/debt_ledger.sh"
_iso_orig="${_ISO}/debt_ledger.orig"
cp "${_iso_src}" "${_iso_orig}"
_iso_audit="${_ISO}/audit/bad.jsonl"
printf '%s\n' '{not-json' >"${_iso_audit}"

# baseline：壞 JSON → rc=2
GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="${_iso_audit}" \
  bash "${_iso_src}" --has-open >"${_ISO}/base.out" 2>&1
_iso_base_rc=$?
if [ "${_iso_base_rc}" -eq 2 ] && grep -qE 'JSON|解析' "${_ISO}/base.out"; then
  ok "iso-ledger baseline malformed → rc=2 + JSON/解析"
else
  bad "iso-ledger baseline malformed 未 fail-closed（rc=${_iso_base_rc}）"
  tail -5 "${_ISO}/base.out" | sed 's/^/    /'
fi

# mutant：sys.exit(2) → continue（只改副本）
# 錨點須與 test_mutation_malformed_json_guard 一致
if grep -q 'sys.exit(2)' "${_iso_src}"; then
  # 只替換 malformed JSON 那段（第一個「無法解析」後的 sys.exit(2)）
  awk '
    /JSON 無法解析\(fail-closed\)/ { hit=1 }
    hit && /sys\.exit\(2\)/ && !done {
      sub(/sys\.exit\(2\)/, "continue  # MUTANT-ISO")
      done=1
      hit=0
    }
    { print }
  ' "${_iso_orig}" >"${_iso_src}"
  chmod +x "${_iso_src}"
  GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="${_iso_audit}" \
    bash "${_iso_src}" --has-open >"${_ISO}/mut.out" 2>&1
  _iso_mut_rc=$?
  if [ "${_iso_mut_rc}" -eq 0 ]; then
    ok "iso-ledger mutant malformed swallow → rc=0（假綠可被觀測）"
  else
    bad "iso-ledger mutant 未呈現假綠（rc=${_iso_mut_rc}；錨點可能漂移）"
    tail -5 "${_ISO}/mut.out" | sed 's/^/    /'
  fi
  # restore 副本
  cp "${_iso_orig}" "${_iso_src}"
  chmod +x "${_iso_src}"
  GOVERNANCE_TEST_HARNESS=1 DEBT_AUDIT_OVERRIDE="${_iso_audit}" \
    bash "${_iso_src}" --has-open >"${_ISO}/rest.out" 2>&1
  _iso_rest_rc=$?
  if [ "${_iso_rest_rc}" -eq 2 ] && grep -qE 'JSON|解析' "${_ISO}/rest.out"; then
    ok "iso-ledger restored malformed → rc=2（還原後不殘紅／不殘綠）"
  else
    bad "iso-ledger restore 後異常 rc=${_iso_rest_rc}（須查明，不得留還原後更紅）"
    tail -5 "${_ISO}/rest.out" | sed 's/^/    /'
  fi
else
  bad "iso-ledger 找不到 sys.exit(2) 錨點"
fi

# override harness：未綁 GOVERNANCE_TEST_HARNESS 時設 DEBT_AUDIT_OVERRIDE → 必須 rc≠0
# 使用健康副本 + 不存在的 audit 路徑；有 harness 時 rc=2（檔缺失），無 harness 時亦須 rc≠0
_ov_audit="${_ISO}/audit/no-such-override.log"
_ov_out="${_ISO}/override.out"
# 故意不設 GOVERNANCE_TEST_HARNESS
env -u GOVERNANCE_TEST_HARNESS DEBT_AUDIT_OVERRIDE="${_ov_audit}" \
  bash "${_iso_src}" --has-open >"${_ov_out}" 2>&1
_ov_rc=$?
if [ "${_ov_rc}" -ne 0 ] && grep -qE 'GOVERNANCE_TEST_HARNESS|DEBT_AUDIT_OVERRIDE|須綁' "${_ov_out}"; then
  ok "iso-ledger unbound-override 拒（rc=${_ov_rc} + harness 訊息）"
else
  bad "iso-ledger unbound-override 未拒（rc=${_ov_rc}；override 可無 harness 生效）"
  tail -5 "${_ov_out}" | sed 's/^/    /'
fi

# 證：拔掉 harness 綁定後副本會假綠（仍不碰產品檔）
_unb="${_ISO}/scripts/debt_ledger_unbound.sh"
cp "${_iso_orig}" "${_unb}"
# 用 python 做精確替換（避免 bash 3.2 多行 sed；錨點與產品一致）
"${PY}" - "${_unb}" <<'PY'
import pathlib, sys
p = pathlib.Path(sys.argv[1])
text = p.read_text(encoding="utf-8")
old = """  if [ -n \"${DEBT_AUDIT_OVERRIDE:-}\" ]; then
    if [ \"${GOVERNANCE_TEST_HARNESS:-}\" != \"1\" ]; then
      echo \"ERROR: DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1\" >&2
      return 1
    fi
    printf '%s\\n' \"${DEBT_AUDIT_OVERRIDE}\"
    return 0
  fi"""
new = """  if [ -n \"${DEBT_AUDIT_OVERRIDE:-}\" ]; then
    # MUTANT-ISO: unbound override（不查 harness）
    printf '%s\\n' \"${DEBT_AUDIT_OVERRIDE}\"
    return 0
  fi"""
if old not in text:
    sys.stderr.write("ERROR: unbound-override anchor missing\n")
    sys.exit(2)
p.write_text(text.replace(old, new, 1), encoding="utf-8")
sys.exit(0)
PY
_py_rc=$?
if [ "${_py_rc}" -ne 0 ]; then
  bad "iso-ledger unbound mutant 無法套用錨點"
else
  chmod +x "${_unb}"
  # 無 harness + override 指向空檔 → 健康本體應 rc≠0；mutant 應可走到讀檔（空檔→rc=2 或 0）
  : >"${_ISO}/audit/empty.log"
  env -u GOVERNANCE_TEST_HARNESS DEBT_AUDIT_OVERRIDE="${_ISO}/audit/empty.log" \
    bash "${_unb}" --has-open >"${_ISO}/unb_mut.out" 2>&1
  _unb_mut_rc=$?
  # mutant 不得再印「須綁 GOVERNANCE_TEST_HARNESS」
  if grep -q '須綁 GOVERNANCE_TEST_HARNESS' "${_ISO}/unb_mut.out"; then
    bad "iso-ledger unbound mutant 仍擋 harness（錨點未生效）"
  else
    ok "iso-ledger unbound mutant 已跳過 harness（rc=${_unb_mut_rc}；可觀測假放行）"
  fi
  # 還原對照：健康副本在同樣 env 下必須拒絕
  env -u GOVERNANCE_TEST_HARNESS DEBT_AUDIT_OVERRIDE="${_ISO}/audit/empty.log" \
    bash "${_iso_orig}" --has-open >"${_ISO}/unb_base.out" 2>&1
  _unb_base_rc=$?
  if [ "${_unb_base_rc}" -ne 0 ] && grep -qE '須綁|GOVERNANCE_TEST_HARNESS' "${_ISO}/unb_base.out"; then
    ok "iso-ledger unbound baseline 健康本拒（rc=${_unb_base_rc}）"
  else
    bad "iso-ledger unbound baseline 未拒（rc=${_unb_base_rc}）"
    tail -5 "${_ISO}/unb_base.out" | sed 's/^/    /'
  fi
fi

# 產品檔內容必須仍等於開跑前備份（寫入 PROBE 時的副本）
if ! cmp -s scripts/debt_ledger.sh "${_iso_orig}"; then
  # 副本取自開跑當下產品；若產品在跑中被外力改動會紅——本腳本自身不改產品
  bad "debt_ledger.sh 與 iso 開跑快照不一致（可能被外力探針污染）"
else
  ok "debt_ledger.sh 產品檔未被本節探針改動"
fi

echo "=== 8. 防假綠：既有測試斷言未被刪 ==="
n=$(git diff -- tests/ | grep -cE "^-.*assert" || true)
[ "${n}" -eq 0 ] && ok "既有測試無 assert 被刪（${n}）" || bad "有 ${n} 行 assert 被刪"

echo "=== 9. 探針路徑約束：probe 必須 repo-local handoffs/ ==="
# 驗 runtime PROBE 前綴（不掃本檔字串——pattern/錯誤訊息會自撞）
case "${PROBE}" in
  handoffs/*)
    ok "verify_b4 PROBE 為 repo-local：${PROBE}"
    ;;
  *)
    bad "verify_b4 PROBE 不在 handoffs/：${PROBE}"
    ;;
esac
# §2 實際使用的 missing-audit 路徑亦須在 PROBE 下
case "${_missing_audit}" in
  handoffs/*)
    ok "missing-audit 路徑 repo-local：${_missing_audit}"
    ;;
  *)
    bad "missing-audit 不在 handoffs/：${_missing_audit}"
    ;;
esac
# §7b iso 路徑亦須在 PROBE 下
case "${_ISO}" in
  handoffs/*)
    ok "iso-ledger 路徑 repo-local：${_ISO}"
    ;;
  *)
    bad "iso-ledger 不在 handoffs/：${_ISO}"
    ;;
esac

echo
if [ "${fail}" -eq 0 ]; then
  echo "B4 INDEPENDENT VERIFY PASS"
else
  echo "B4 INDEPENDENT VERIFY FAIL"
fi
exit "${fail}"
