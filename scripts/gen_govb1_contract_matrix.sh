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

# fixture 補充項（Task 1.5；不在 §V-ASSERT fence 內）
_fixture_supplemental() {
  printf '%s\n' 'spec_assert_pending.md' 'spec_func_missing.md'
}

# 下界用 path 錨點導出 fence 內文——不依賴「fixture 清單」標題（失配時標題 pattern 與下界不可同崩）
_fixture_fence_items() {
  awk '
    /^```/ {
      if (in_f) { if (tgt) exit; in_f=0; tgt=0; seen=0; next }
      in_f=1; tgt=0; seen=0; next
    }
    in_f {
      if (!seen && $0 ~ /^[[:space:]]*$/) next
      if (!seen) {
        seen=1
        if ($0 ~ /^tests\/governance\/fixtures\/govb1\/?$/) { tgt=1; next }
        next
      }
      if (tgt) print
    }
  ' docs/GOVB1_INPUT_QUALITY_SPEC.md \
    | grep -oE '[a-z0-9_]+\.(md|json)|factkey_[a-z]+/' | LC_ALL=C sort -u
}

# 標題 pattern 抽取（與下界獨立；失配時只剩 supplemental，由下界守衛 fail-closed）
_fixture_heading_items() {
  awk 'BEGIN{c=0} /fixture 清單/{want=1} want && /^```$/{c++; next} c==1{print} c>=2{exit}' \
    docs/GOVB1_INPUT_QUALITY_SPEC.md \
    | grep -oE '[a-z0-9_]+\.(md|json)|factkey_[a-z]+/' | LC_ALL=C sort -u
}

# 現算下界 = fence 內項數 + supplemental 項數；fence 0 項 ⇒ 錨點失效，立即非零
_fixture_floor() {
  local fence_n supp_n
  fence_n="$( _fixture_fence_items | grep -c . || true )"
  if [ "${fence_n:-0}" -eq 0 ]; then
    echo "ERROR: SPEC fixture fence 現算 0 項，path 錨點已失效" >&2
    return 1
  fi
  supp_n="$( _fixture_supplemental | grep -c . || true )"
  echo $(( fence_n + supp_n ))
}

# fixture 清單由 SPEC §V-ASSERT 現讀 + supplemental；出口加現算下界（與 emit_behavior_rows 對稱）
_fixture_names() {
  local names n floor
  names="$(
    { _fixture_heading_items; _fixture_supplemental; } | LC_ALL=C sort -u
  )"
  floor="$(_fixture_floor)" || return 1
  n="$(printf '%s\n' "${names}" | grep -c . || true)"
  if [ "${n:-0}" -lt "${floor}" ]; then
    echo "ERROR: fixture 清單僅 ${n} 項，低於現算下界 ${floor}（heading pattern 可能已失效）" >&2
    return 1
  fi
  printf '%s\n' "${names}"
}

check_fixtures() {
  local base="tests/governance/fixtures/govb1" n rc=0 names
  names="$(_fixture_names)" || return 1
  while IFS= read -r n; do
    [ -n "${n}" ] || continue
    if [ ! -e "${base}/${n}" ]; then
      echo "ERROR: missing fixture ${base}/${n}" >&2
      rc=1
    fi
  done <<EOF
$(printf '%s\n' "${names}" | LC_ALL=C sort -u)
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
      # 禁經 pipe 取 rc：_fixture_names 下界失敗須直傳
      _lf_names="$(_fixture_names)" || return 1
      printf '%s\n' "${_lf_names}" | LC_ALL=C sort -u
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
