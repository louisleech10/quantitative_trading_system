#!/usr/bin/env bash
# test_template_check.sh — TEMPLATE_GATE_FIX fixture 矩陣一鍵驗證。
# 用法：
#   bash scripts/test_template_check.sh              # 比對 EXPECTED.txt（修後應全綠）
#   bash scripts/test_template_check.sh --freeze     # 實測寫入 BASELINE_BEFORE.txt
#   bash scripts/test_template_check.sh --mutate A-1 # mutation 契約（B2 填實 sed 後驗收）
#
# 誠實邊界：EXPECTED 為 §G 先驗手填（Phase 2 目標矩陣），非跑後回填。
# 修前預設模式 exit 1（現行繞過探針仍 PASS）= Phase 2 可證偽起點。

set -u

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURE_DIR="${ROOT}/tests/gate_fixtures"
TEMPLATE_CHECK="${ROOT}/scripts/template_check.sh"
EXPECTED_FILE="${FIXTURE_DIR}/EXPECTED.txt"
BASELINE_FILE="${FIXTURE_DIR}/BASELINE_BEFORE.txt"
MUTATION_FILE="${FIXTURE_DIR}/MUTATION.txt"

usage() {
  echo "用法: test_template_check.sh [--freeze | --mutate <A-1|A-3|A-4|A-5>]"
  exit 1
}

fixture_kind() {
  local base="$1"
  case "${base}" in
    spec_*) echo spec ;;
    todo_*) echo todo ;;
    result_*) echo result ;;
    *) echo "" ;;
  esac
}

collect_fixtures() {
  FIXTURES=()
  local f base kind
  shopt -s nullglob
  for f in "${FIXTURE_DIR}"/*.md; do
    base="$(basename "${f}")"
    kind="$(fixture_kind "${base}")"
    if [ -z "${kind}" ]; then
      continue
    fi
    FIXTURES+=("${base}")
  done
  shopt -u nullglob
  if [ "${#FIXTURES[@]}" -eq 0 ]; then
    echo "ERROR: fixture 目錄無可跑探針（${FIXTURE_DIR}/*.md 為空或非 spec_/todo_/result_ 前綴）" >&2
    exit 2
  fi
  IFS=$'\n' FIXTURES=($(printf '%s\n' "${FIXTURES[@]}" | sort))
  unset IFS
}

run_matrix_to() {
  local out="$1"
  : > "${out}"
  local base kind path rc
  for base in "${FIXTURES[@]}"; do
    kind="$(fixture_kind "${base}")"
    path="${FIXTURE_DIR}/${base}"
    set +e
    bash "${TEMPLATE_CHECK}" "${kind}" "${path}" >/dev/null
    rc=$?
    set -e
    printf '%s,%s,%s\n' "${base}" "${kind}" "${rc}" >> "${out}"
  done
  sort -o "${out}" "${out}"
}

compare_matrix_files() {
  local actual="$1"
  local expected="$2"
  local label="$3"
  if [ ! -f "${expected}" ]; then
    echo "ERROR: 缺少 ${label}: ${expected}" >&2
    return 1
  fi
  if ! diff -u "${expected}" "${actual}"; then
    echo "MATRIX FAIL: 與 ${label} 不一致（見上方 diff）" >&2
    return 1
  fi
  return 0
}

validate_expected_coverage() {
  local missing=""
  local base
  for base in "${FIXTURES[@]}"; do
    if ! grep -qF "${base}," "${EXPECTED_FILE}"; then
      missing="${missing}  · EXPECTED 缺列: ${base}\n"
    fi
  done
  local exp_count
  exp_count="$(grep -c ',' "${EXPECTED_FILE}" || true)"
  if [ "${exp_count}" -ne "${#FIXTURES[@]}" ]; then
    echo "ERROR: EXPECTED 行數 ${exp_count} 與 fixture 數 ${#FIXTURES[@]} 不一致" >&2
    [ -n "${missing}" ] && printf '%b' "${missing}" >&2
    return 1
  fi
  if [ -n "${missing}" ]; then
    echo "ERROR: EXPECTED 與 fixture 清單不一致" >&2
    printf '%b' "${missing}" >&2
    return 1
  fi
  return 0
}

restore_template_check() {
  local backup="$1"
  cp "${backup}" "${TEMPLATE_CHECK}"
  rm -f "${TEMPLATE_CHECK}.bak"
}

run_mutate() {
  local mutate_id="$1"
  local line sed_cmd
  line="$(grep -E "^${mutate_id}\\|" "${MUTATION_FILE}" || true)"
  if [ -z "${line}" ]; then
    echo "ERROR: MUTATION.txt 無 id=${mutate_id}" >&2
    exit 1
  fi
  sed_cmd="${line#*|}"
  if [ -z "${sed_cmd}" ] || [ "${sed_cmd}" = "TBD" ]; then
    echo "ERROR: MUTATION ${mutate_id} 破壞命令尚未填實（B2）" >&2
    exit 1
  fi

  local tmp_actual tmp_broken tmp_restored backup
  tmp_actual="$(mktemp)"
  tmp_broken="$(mktemp)"
  tmp_restored="$(mktemp)"
  backup="$(mktemp)"
  trap 'rm -f "${tmp_actual}" "${tmp_broken}" "${tmp_restored}" "${backup}"' RETURN

  # 前置：矩陣須先全綠，否則拒跑（Task 1.2 ⑦ runtime defect 修正）
  run_matrix_to "${tmp_actual}"
  if ! compare_matrix_files "${tmp_actual}" "${EXPECTED_FILE}" "EXPECTED.txt（mutate 前須全綠）"; then
    echo "ERROR: --mutate 拒跑：矩陣未全綠（須先通過 test_template_check.sh 並 commit 實作）" >&2
    exit 2
  fi

  cp "${TEMPLATE_CHECK}" "${backup}"

  echo "MUTATE ${mutate_id}: 套用破壞 → ${sed_cmd}"
  (cd "${ROOT}" && eval "${sed_cmd}")

  run_matrix_to "${tmp_broken}"
  if compare_matrix_files "${tmp_broken}" "${EXPECTED_FILE}" "EXPECTED.txt（破壞後應轉紅）"; then
    echo "MUTATE FAIL: ${mutate_id} 破壞後矩陣仍與 EXPECTED 一致（未轉紅）" >&2
    restore_template_check "${backup}"
    exit 1
  fi

  restore_template_check "${backup}"

  run_matrix_to "${tmp_restored}"
  if ! compare_matrix_files "${tmp_restored}" "${tmp_actual}" "還原前快照（須與 EXPECTED 一致）"; then
    echo "MUTATE FAIL: ${mutate_id} 還原後矩陣與破壞前不一致" >&2
    exit 1
  fi

  if ! cmp -s "${backup}" "${TEMPLATE_CHECK}"; then
    echo "MUTATE FAIL: ${mutate_id} template_check.sh 未淨還原（cp 備份比對失敗）" >&2
    exit 1
  fi

  if ! git -C "${ROOT}" diff --exit-code scripts/template_check.sh >/dev/null; then
    echo "MUTATE FAIL: ${mutate_id} template_check.sh 工作區未淨（git diff 非空）" >&2
    git -C "${ROOT}" diff scripts/template_check.sh >&2 || true
    exit 1
  fi

  echo "MUTATE PASS: ${mutate_id}"
  exit 0
}

mode="compare"
mutate_id=""

while [ $# -gt 0 ]; do
  case "$1" in
    --freeze)
      mode="freeze"
      shift
      ;;
    --mutate)
      mode="mutate"
      mutate_id="${2:-}"
      [ -n "${mutate_id}" ] || usage
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage
      ;;
  esac
done

collect_fixtures

tmp_out="$(mktemp)"
trap 'rm -f "${tmp_out}"' EXIT

case "${mode}" in
  freeze)
    run_matrix_to "${BASELINE_FILE}"
    echo "BASELINE 已寫入 ${BASELINE_FILE}（${#FIXTURES[@]} 行）"
    exit 0
    ;;
  mutate)
    run_mutate "${mutate_id}"
    ;;
  compare)
    if [ ! -f "${EXPECTED_FILE}" ]; then
      echo "ERROR: 缺少 EXPECTED.txt: ${EXPECTED_FILE}" >&2
      exit 1
    fi
    validate_expected_coverage || exit 1
    run_matrix_to "${tmp_out}"
    if compare_matrix_files "${tmp_out}" "${EXPECTED_FILE}" "EXPECTED.txt"; then
      echo "MATRIX PASS: 全 ${#FIXTURES[@]} fixture 與 EXPECTED 一致"
      exit 0
    fi
    exit 1
    ;;
esac
