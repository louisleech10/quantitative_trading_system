#!/usr/bin/env bash
# gen_govb1_contract_matrix.sh — GOVB1 Task 0.1 契約矩陣生成器
# 輸出決定性、無副作用。分母一律現算，禁寫死份數／列數（G-2）。
#
# 用法：
#   bash scripts/gen_govb1_contract_matrix.sh              # stdout: 矩陣 + 行為表列
#   bash scripts/gen_govb1_contract_matrix.sh --check-fixtures
#   bash scripts/gen_govb1_contract_matrix.sh --behavior-only
set -u

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}" || exit 1

# 行為表逐列現讀——前導空白與粗體 rc 皆須納入（GROK-R7-P0-01）
_behavior_rows() {
  awk '/^[[:space:]]*\| `.*` \| (\*\*)?rc==/ { print }' docs/GOV_DISPATCH_FLOW_FIX_SPEC.md
}

emit_behavior_rows() {
  local rows n
  rows="$(_behavior_rows)"
  n="$(printf '%s\n' "${rows}" | grep -c . || true)"
  if [ "${n:-0}" -eq 0 ]; then
    echo "ERROR: 行為表現讀 0 行，pattern 已失效" >&2
    return 1
  fi
  printf '%s\n' "${rows}"
}

# docs 清單現跑導出（禁寫死份數）
_docs_list() {
  # shellcheck disable=SC2086
  grep -rln 'doc_format_precheck\|completeness_check\|cx_run' docs/*.md 2>/dev/null | LC_ALL=C sort || true
}

emit_matrix() {
  local f lines
  # 表頭（非 docs/ 前綴，不計入 T-0.1-C1）
  printf '%s\n' 'path|contract_lines|touched|evidence'
  while IFS= read -r f; do
    [ -n "${f}" ] || continue
    lines="$(grep -cE 'doc_format_precheck|completeness_check|cx_run' "${f}" || true)"
    # touched：契約矩陣本身只讀；本欄固定 0（後續 batch 可覆寫語意）
    printf '%s|%s|%s|%s\n' "${f}" "${lines}" "0" "keyword-hit"
  done <<EOF
$(_docs_list)
EOF
}

# fixture 清單由 SPEC §V-ASSERT 現讀（TODO 原 sed 在 opening fence 即截斷，改為取 fence 內文）
# 併入 Task 1.5 之 spec_assert_pending.md／spec_func_missing.md
_fixture_names() {
  awk 'BEGIN{c=0} /fixture 清單/{want=1} want && /^```$/{c++; next} c==1{print} c>=2{exit}' \
    docs/GOVB1_INPUT_QUALITY_SPEC.md \
    | grep -oE '[a-z0-9_]+\.(md|json)|factkey_[a-z]+/' | LC_ALL=C sort -u
  printf '%s\n' 'spec_assert_pending.md' 'spec_func_missing.md'
}

check_fixtures() {
  local base="tests/governance/fixtures/govb1" n rc=0
  while IFS= read -r n; do
    [ -n "${n}" ] || continue
    if [ ! -e "${base}/${n}" ]; then
      echo "ERROR: missing fixture ${base}/${n}" >&2
      rc=1
    fi
  done <<EOF
$(_fixture_names | LC_ALL=C sort -u)
EOF
  return "${rc}"
}

main() {
  case "${1:-}" in
    --check-fixtures)
      check_fixtures
      return $?
      ;;
    --behavior-only)
      emit_behavior_rows
      return $?
      ;;
    --list-fixtures)
      _fixture_names | LC_ALL=C sort -u
      return 0
      ;;
    "")
      emit_matrix
      emit_behavior_rows || return 1
      return 0
      ;;
    *)
      echo "ERROR: unknown arg: $1" >&2
      return 2
      ;;
  esac
}

main "$@"
