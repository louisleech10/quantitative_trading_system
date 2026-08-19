#!/usr/bin/env bash
# gap2_mutation_probe.sh — GAP-2 §V mutation 自證（每批一組 case；B1 十條唯一對映）。
#
# 用法：bash scripts/gap2_mutation_probe.sh --batch B1|B2|B3|B4|B5
# rc：0＝全部 case「mutate 後轉紅（rc=1 且 ≥1 FAILED）＋還原後綠」；1＝有 case 未轉紅／還原後不綠／baseline 紅；
#     2＝mutation 目標行不存在（不留髒檔）或 batch 未定義／pytest collection error；3＝互斥鎖被持有。
# receipt：handoffs/run_receipts/<TS>-gap2-<batch>-probe.log（逐條 `MUTATION V-n: RED ✓ / RESTORED GREEN ✓`）。
#
# 沿用 scripts/gap1_b1_mutation_probe.sh 骨架（三個既往缺陷之修法一併沿用）：
#   ① 還原用 $BACKUP_DIR 複本 cp 回（非 git checkout：未追蹤新檔還原不了）；
#   ② rc=2（collection／語法錯）不算可證偽 ⇒ 判 mutation 設計錯；
#   ③ 就地 mutate 共用工作區 ⇒ 不可並行 ⇒ mkdir 互斥鎖 .claude/gate/gap2_mutation_probe.lock（持有 ⇒ rc=3）。
# 目標行先 grep -cF 存在檢查再替換（缺 ⇒ rc=2、不動檔）。
#
# case 表（V_ID|file|old|new|pytest_target）寫在本檔頂部之 case_* 陣列；後續批次只加列，每 V_ID 全票唯一：
#   B1：V-1／2／3／4／5／6／17a／18／21／22a（純函式）；V-22／V-24 只在 B4；V-7..9 B2；V-10..12／17b／19／20 B3。
#   A1-7 K5：V-3 對映改 test_marginal_uses_spearman_not_pearson（重尾 label 下 marginal 路徑 Spearman≠Pearson；O6 為輔測）。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2

BATCH=""
while [ $# -gt 0 ]; do
  case "$1" in
    --batch) BATCH="${2:-}"; shift 2 ;;
    *) echo "用法: bash scripts/gap2_mutation_probe.sh --batch B1|B2|B3|B4|B5" >&2; exit 2 ;;
  esac
done
[ -n "${BATCH}" ] || { echo "用法: bash scripts/gap2_mutation_probe.sh --batch B1|B2|B3|B4|B5" >&2; exit 2; }

PY=venv/bin/python
MIC=momentum/Analysis/marginal_ic.py
FC=momentum/Analysis/factor_combiner.py
TEST_FC=tests/momentum/Analysis/test_factor_combiner.py
SC=momentum/Analysis/survivor_contract.py
ORCH=momentum/Analysis/ic_filter_orchestrator.py
FREEZE=scripts/gap2_freeze_golden.py
TEST_WIRING=tests/momentum/Analysis/test_gap2_stage6b_wiring.py
TEST_PERSIST=tests/momentum/Analysis/test_gap2_survivor_persist.py
TEST_GOLDEN=tests/momentum/Analysis/test_gap2_golden.py
CONTRACT=momentum/Analysis/contracts/ic_survivor_contract.json
TEST_MIC=tests/momentum/Analysis/test_marginal_ic.py
TEST_SC=tests/momentum/Analysis/test_survivor_contract.py

# ---- case 表：V_ID | file | old | new | pytest_target（-k 名）----
declare -a CASES=()
case "${BATCH}" in
  B1)
    ALL_TESTS="${TEST_SC} ${TEST_MIC}"
    TARGETS="${MIC} ${FC}"
    CASES+=("V-1|${MIC}|proj = fit_projection(z_f_tr, Z_S_tr)|proj = fit_projection(z_f_te, Z_S_te)|test_o7_train_fit")
    CASES+=("V-2|${MIC}|    return stats.norm.ppf(r / (n + 1.0))|    return arr  # MUTANT: identity|test_o1a_residual_degenerate")
    CASES+=("V-3|${MIC}|    return float(stats.spearmanr(a, b)[0])|    return float(stats.pearsonr(a, b)[0])  # MUTANT|test_marginal_uses_spearman_not_pearson")
    CASES+=("V-4|${MIC}|            S = [s for s in survivors if s != f]|            S = list(survivors)  # MUTANT: 含自身|test_o2_orthogonal_new_info")
    CASES+=("V-5|${MIC}|    order_key_ic = train_ic |    order_key_ic = _rank_ic(test_rows_mask) |test_sequential_order_by_train_ic")
    CASES+=("V-6|${FC}|    rng = np.random.default_rng(seed)|    rng = np.random.default_rng()  # MUTANT: 忽略 seed|test_o9_bootstrap_seed_determinism")
    CASES+=("V-17a|${MIC}|            insample = _spearman(r_tr, y_tr)|            insample = _spearman(r_te, y_te)  # MUTANT|test_o7_train_insample_differs")
    CASES+=("V-18|${MIC}|            S = [s for s in survivors if s != f]|            S = [s for j, s in enumerate(survivors) if j != 0]  # MUTANT: 位置|test_shuffle_survivors_invariance")
    CASES+=("V-21|${MIC}|        if float(np.var(r_te)) <= thr:|        if False:  # MUTANT: 退化 gate 移除|test_o1a_residual_degenerate")
    CASES+=("V-22a|${MIC}|    if loo_budget_ok:|    if True:  # MUTANT: 超限仍輸出|test_budget_survivors_whole_not_computed")
    ;;
  B2)
    ALL_TESTS="${TEST_MIC} ${TEST_FC}"
    TARGETS="${FC}"
    CASES+=("V-7|${FC}|    sign_source_X, sign_source_y = X_tr, y_tr|    sign_source_X, sign_source_y = X_te, y_te  # MUTANT: 符號用 test|test_o8_sign_from_train_negative_case")
    CASES+=("V-8|${FC}|    weight_source_ic = train_ic|    weight_source_ic = test_ic_all  # MUTANT: 權重用 test|test_ic_weighted_uses_train_ic_reference")
    CASES+=("V-9|${FC}|    b = min(int(block_len), n)  |    b = 1  # MUTANT: 強制 iid; |test_delta_ci_uses_block_len_reference")
    ;;
  B3)
    ALL_TESTS="${TEST_SC}"
    TARGETS="${SC} ${CONTRACT}"
    CASES+=("V-10|${SC}|        \"sample_scope\": sample_scope,|        \"sample_scope_\": sample_scope,  # MUTANT: 移除 sample_scope|test_roundtrip_build_then_validate")
    CASES+=("V-11|${SC}|    if schema.get(\"additional_properties\") is False:|    if False:  # MUTANT: 放寬 additional_properties|test_unknown_key_raises")
    CASES+=("V-12|${CONTRACT}|  \"sample_scope_kind_values\": [|  \"sample_scope_kind_values\": [\"panel\",|test_load_sample_scope_kind_values_subset_of_row_mask_plan_source")
    CASES+=("V-17b|${SC}|    if payload[\"independent_oos_validation\"] not in c[\"independent_oos_validation_allowed\"]:|    if False:  # MUTANT: 不驗 independent_oos_validation|test_oos_four_field_consistency")
    CASES+=("V-19a|${SC}|        \"symbol\": str(symbol),|        \"symbol\": \"ETHUSDT\",  # MUTANT: 寫死|test_identity_three_fields")
    CASES+=("V-19b|${SC}|        \"timeframe\": str(timeframe),|        \"timeframe\": \"12h\",  # MUTANT: 寫死|test_identity_three_fields")
    CASES+=("V-19c|${SC}|        \"case_id\": str(case_id),|        \"case_id\": \"ic_gatekeeper\",  # MUTANT: 寫死|test_identity_three_fields")
    CASES+=("V-20|${SC}|    if payload[\"feature_set_hash\"] != feature_set_hash(names):|    if False:  # MUTANT: 略過 feature_set_hash 重算|test_feature_set_hash_and_survivor_sequence")
    ;;
  B4)
    ALL_TESTS="${TEST_WIRING} ${TEST_PERSIST} ${TEST_GOLDEN}"
    TARGETS="${ORCH} ${FREEZE} ${MIC}"
    CASES+=("V-13|${ORCH}|        section[\"oos_guarantees\"] = bool(oos_guarantees)|        section[\"oos_guarantees\"] = True  # MUTANT: fallback 仍標 True|test_event_fallback_holdout_present_but_root_degraded")
    CASES+=("V-14|${ORCH}|        if not cfg.enabled:\n            return self._marginal_status_object(\"disabled\", \"disabled_by_config\")|        if not cfg.enabled:\n            return {}  # MUTANT: 裸空|test_disabled_gives_status_object_only")
    CASES+=("V-15|${ORCH}|            filtered_features=list(filtered_df.columns) if filtered_df is not None else [],|            filtered_features=[str(r.get(\"feature_name\")) for r in (report.get(\"summary_table\") or [])],  # MUTANT: passed_features|test_file_exists_validates_names_and_sha")
    CASES+=("V-16|${ORCH}|            redundancy_log = {**redundancy_log, \"scope\": \"test\"}|            redundancy_log = {**redundancy_log, \"scope\": \"test\", \"method\": \"mutant\"}  # MUTANT: 動既有 stage6 鍵值|test_g1_golden_unchanged")
    CASES+=("V-22|${MIC}|        n_regressions += 1|        n_regressions += 2  # MUTANT: 計數與實際 fit 脫鉤|test_default_config_section_ok_and_root_oracle")
    CASES+=("V-23|${FREEZE}|_META_SCRUB = (\"filtered_features_path\", |_META_SCRUB = (|test_g1_golden_unchanged")
    CASES+=("V-24|${ORCH}|                \"path\": None,|                \"path_\": None,  # MUTANT: 失敗形狀省略 path 鍵|test_four_shapes_five_keys")
    ;;
  B5)
    echo "🔴 batch ${BATCH} 之 case 表尚未定義（該批 Task 落地時加列）。" >&2
    exit 2
    ;;
  *)
    echo "🔴 未知 batch: ${BATCH}" >&2; exit 2 ;;
esac

# ---- 互斥鎖（fail-closed）----
LOCK_DIR=".claude/gate/gap2_mutation_probe.lock"
if ! mkdir "${LOCK_DIR}" 2>/dev/null; then
  echo "🔴 探針已有另一個執行實例（鎖: ${LOCK_DIR}）；本探針就地 mutate 共用工作區 ⇒ 不可並行。" >&2
  [ -f "${LOCK_DIR}/owner" ] && cat "${LOCK_DIR}/owner" >&2
  ls -t handoffs/run_receipts/*gap2-*-probe.log 2>/dev/null | head -3 >&2
  exit 3
fi
printf 'pid=%s started=%s batch=%s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${BATCH}" > "${LOCK_DIR}/owner"
_release_lock() { rm -rf "${LOCK_DIR}"; }

TS="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p handoffs/run_receipts
RECEIPT="handoffs/run_receipts/${TS}-gap2-${BATCH}-probe.log"
BACKUP_DIR="$(mktemp -d)"
TMPLOG="$(mktemp)"

backup_all() {
  for f in ${TARGETS}; do
    mkdir -p "${BACKUP_DIR}/$(dirname "$f")"; cp "$f" "${BACKUP_DIR}/$f"
  done
}
restore_all() {
  for f in ${TARGETS}; do
    [ -f "${BACKUP_DIR}/$f" ] && cp "${BACKUP_DIR}/$f" "$f"
  done
}
cleanup() { restore_all; rm -rf "${BACKUP_DIR}" "${TMPLOG}"; _release_lock; }
trap cleanup EXIT

log() { echo "$*" | tee -a "${RECEIPT}"; }

# ---- 目標行存在檢查（全部 case 先查；缺任一 ⇒ rc=2、不動檔）----
for c in "${CASES[@]}"; do
  IFS='|' read -r vid file old new target <<<"$c"
  if ! "$PY" - "${file}" "${old}" <<'PYCHK'
import pathlib, sys
path, old = sys.argv[1], sys.argv[2].replace("\\n", "\n")
sys.exit(0 if old in pathlib.Path(path).read_text(encoding="utf-8") else 1)
PYCHK
  then
    echo "🔴 ${vid}: mutation 目標行不存在於 ${file}: ${old}" >&2
    exit 2
  fi
done

backup_all
log "[gap2_mutation_probe] batch=${BATCH} ts=${TS} cases=${#CASES[@]}"

# ---- baseline（fail-closed）----
"$PY" -m pytest ${ALL_TESTS} -q > "${TMPLOG}" 2>&1
_base_rc=$?
log "[baseline] rc=${_base_rc} ($(tail -1 "${TMPLOG}"))"
if [ "${_base_rc}" -ne 0 ]; then
  log "🔴 baseline 非綠 ⇒ mutation 前提不成立，中止。"
  tail -20 "${TMPLOG}" >&2
  exit 1
fi

FAIL=0
for c in "${CASES[@]}"; do
  IFS='|' read -r vid file old new target <<<"$c"
  # mutate（第一個命中；exact substring）
  "$PY" - "${file}" "${old}" "${new}" <<'PYEOF'
import pathlib, sys
path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
old = old.replace("\\n", "\n")  # case 表以字面 \n 表示換行（多行目標）
new = new.replace("\\n", "\n")
p = pathlib.Path(path)
s = p.read_text(encoding="utf-8")
if old not in s:
    sys.exit(f"MUTATION TARGET MISS: {path}: {old!r}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
PYEOF
  if [ $? -ne 0 ]; then log "🔴 ${vid}: mutate 失敗"; restore_all; exit 2; fi

  "$PY" -m pytest ${ALL_TESTS} -q -x -k "${target}" > "${TMPLOG}" 2>&1
  _rc=$?
  _nfail="$(grep -cE '^FAILED' "${TMPLOG}")"
  if [ "${_rc}" -eq 1 ] && [ "${_nfail}" -ge 1 ]; then
    log "MUTATION ${vid}: RED ✓ (${target} rc=1, FAILED=${_nfail})"
  elif [ "${_rc}" -eq 2 ]; then
    log "MUTATION ${vid}: 🔴 rc=2（collection／語法錯）⇒ mutation 設計錯，不算可證偽"
    FAIL=1
  else
    log "MUTATION ${vid}: 🔴 未轉紅（rc=${_rc}, FAILED=${_nfail}）⇒ 測試不可證偽"
    FAIL=1
  fi
  restore_all
  "$PY" -m pytest ${ALL_TESTS} -q -x -k "${target}" > "${TMPLOG}" 2>&1
  _rc2=$?
  if [ "${_rc2}" -eq 0 ]; then
    log "MUTATION ${vid}: RESTORED GREEN ✓"
  else
    log "MUTATION ${vid}: 🔴 還原後未綠（rc=${_rc2}）"
    FAIL=1
  fi
done

# ---- 還原後全套綠（雙保險）----
"$PY" -m pytest ${ALL_TESTS} -q > "${TMPLOG}" 2>&1
_post_rc=$?
log "[post-restore] rc=${_post_rc} ($(tail -1 "${TMPLOG}"))"
[ "${_post_rc}" -eq 0 ] || FAIL=1

if [ "${FAIL}" -eq 0 ]; then
  log "[gap2_mutation_probe] ✅ batch=${BATCH} 全部 ${#CASES[@]} 條 mutation 轉紅且還原綠 → receipt ${RECEIPT}"
  exit 0
fi
log "[gap2_mutation_probe] 🔴 batch=${BATCH} 有 case 未通過 → receipt ${RECEIPT}"
exit 1
