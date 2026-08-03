#!/usr/bin/env bash
# gen_govflow_manifest.sh — GOV_DISPATCH_FLOW_FIX Phase 0 攻擊面 manifest 生成器
#
# 預設：輸出四欄 manifest  path|phases|nodeid|status
#   phases  = 本 epic 於該 Phase「允許修改」的檔（非 SPEC §M「受影響 Phase」）
#   nodeid  = 對應 pytest 檔路徑；非測試檔／尚未存在 → -
#   status  ∈ {present, MISSING}
#
# 子命令：
#   --record-base <N>  append-only 寫入 handoffs/govflow_phase_base.tsv
#                      同一 <N> 已存在 ⇒ 非零離開；N ∉ {0,1,2,3,4} ⇒ 非零離開
#
# 真相源：docs/GOV_DISPATCH_FLOW_FIX_TODO.md Task 0.1（禁以 §M 手寫表為準）
#
# shellcheck 目標：bash 3.2（macOS /bin/bash）— 不用 associative array。

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

TODO_PATH="docs/GOV_DISPATCH_FLOW_FIX_TODO.md"
BASE_TSV="handoffs/govflow_phase_base.tsv"
A_PATTERN='completeness_check|result_state|committee_process_exempt|STAMP-MODE'

# ---------------------------------------------------------------------------
# --record-base <N>
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--record-base" ]; then
  N="${2:-}"
  if [ -z "${N}" ]; then
    echo "ERROR: --record-base 需要 <N> 引數（N ∈ {0,1,2,3,4}）" >&2
    exit 2
  fi
  case "${N}" in
    0|1|2|3|4) ;;
    *)
      echo "ERROR: --record-base <N> 的 N 必須 ∈ {0,1,2,3,4}，取得: ${N}" >&2
      exit 2
      ;;
  esac
  mkdir -p handoffs
  if [ -f "${BASE_TSV}" ]; then
    # 同一 N 已存在 ⇒ 非零（append-only）
    if awk -F'\t' -v n="${N}" '$1 == n { found=1; exit } END { exit !found }' "${BASE_TSV}"; then
      echo "ERROR: ${BASE_TSV} 已有 Phase ${N} 列（append-only，禁改寫基準）" >&2
      exit 1
    fi
  fi
  head_sha="$(git rev-parse HEAD)"
  # ISO8601 UTC
  ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
  printf '%s\t%s\t%s\n' "${N}" "${head_sha}" "${ts}" >> "${BASE_TSV}"
  echo "RECORDED phase-base N=${N} HEAD=${head_sha} ts=${ts} → ${BASE_TSV}"
  exit 0
fi

if [ "$#" -gt 0 ]; then
  echo "用法: bash scripts/gen_govflow_manifest.sh" >&2
  echo "      bash scripts/gen_govflow_manifest.sh --record-base <N>" >&2
  exit 2
fi

# ---------------------------------------------------------------------------
# PHASE_MAP lookup（path → phases；- ＝旁觀者；0 ＝ Phase 0）
# 語意＝本 epic 允許修改的檔，不是 SPEC §M 受影響 Phase。
# ---------------------------------------------------------------------------
phase_of() {
  case "$1" in
    scripts/gen_govflow_manifest.sh)                 echo "0" ;;
    scripts/completeness_check.sh)                   echo "1" ;;
    scripts/cx_run.sh)                               echo "2,3" ;;
    scripts/audit_events.json)                       echo "2" ;;
    docs/P16_COMMITTEE_DEBT_SPEC.md)                 echo "2" ;;
    scripts/committee_run.sh)                        echo "3" ;;
    scripts/gate.sh)                                 echo "-" ;;
    scripts/_role_gate.sh)                           echo "3" ;;
    scripts/verification_claim_check.py)             echo "4" ;;
    scripts/doc_format_precheck.sh)                  echo "2" ;;
    scripts/brief_conformance_check.sh)              echo "2" ;;
    scripts/verdict_filled_check.sh)                 echo "2" ;;
    scripts/gov_check.sh)                            echo "2" ;;
    tests/governance/test_govflow_manifest.py)       echo "0" ;;
    tests/governance/test_completeness_idlike_fp.py) echo "1" ;;
    tests/governance/test_result_state_format_failed.py) echo "2" ;;
    tests/governance/test_registry_v2_shape.py)      echo "2" ;;
    tests/governance/test_rolegate_predispatch.py)   echo "3" ;;
    tests/governance/test_claimcheck_verbatim_exempt.py) echo "4" ;;
    tests/governance/test_debt_emit.py)              echo "2" ;;
    tests/governance/test_stamp_taskid_inject.py)    echo "2" ;;
    scripts/git_hooks/pre-commit)                    echo "4" ;;
    *) echo "" ;;  # 空字串＝未映射
  esac
}

# PHASE_MAP 全部 key（含 phases=- 的旁觀者），供反向收斂掃描
# shellcheck disable=SC2046
PHASE_MAP_KEYS="
scripts/gen_govflow_manifest.sh
scripts/completeness_check.sh
scripts/cx_run.sh
scripts/audit_events.json
docs/P16_COMMITTEE_DEBT_SPEC.md
scripts/committee_run.sh
scripts/gate.sh
scripts/_role_gate.sh
scripts/verification_claim_check.py
scripts/doc_format_precheck.sh
scripts/brief_conformance_check.sh
scripts/verdict_filled_check.sh
scripts/gov_check.sh
tests/governance/test_govflow_manifest.py
tests/governance/test_completeness_idlike_fp.py
tests/governance/test_result_state_format_failed.py
tests/governance/test_registry_v2_shape.py
tests/governance/test_rolegate_predispatch.py
tests/governance/test_claimcheck_verbatim_exempt.py
tests/governance/test_debt_emit.py
tests/governance/test_stamp_taskid_inject.py
scripts/git_hooks/pre-commit
"

# ---------------------------------------------------------------------------
# 錨點完整性（邊界③）：count(### Task) == count(修改檔案) == count(不可做)
# ---------------------------------------------------------------------------
if [ ! -f "${TODO_PATH}" ]; then
  echo "ERROR: TODO 不存在: ${TODO_PATH}" >&2
  exit 1
fi

n_task="$(grep -cE '^### Task ' "${TODO_PATH}" || true)"
n_mod="$(grep -cE '^- \*\*修改檔案\*\*' "${TODO_PATH}" || true)"
n_forbid="$(grep -cE '^- \*\*不可做\*\*' "${TODO_PATH}" || true)"

if [ "${n_task}" != "${n_mod}" ] || [ "${n_mod}" != "${n_forbid}" ]; then
  echo "ERROR: 錨點完整性失敗: count(### Task)=${n_task} count(修改檔案)=${n_mod} count(不可做)=${n_forbid}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# A / B / C / D 聯集
# 命令用 grep -rlE（不用 rg，可攜性）
# ---------------------------------------------------------------------------
tmp_a="$(mktemp)"
tmp_b="$(mktemp)"
tmp_c="$(mktemp)"
tmp_d="$(mktemp)"
tmp_bcd="$(mktemp)"
tmp_union="$(mktemp)"
tmp_mapped="$(mktemp)"
cleanup() {
  rm -f "${tmp_a}" "${tmp_b}" "${tmp_c}" "${tmp_d}" "${tmp_bcd}" "${tmp_union}" "${tmp_mapped}"
}
trap cleanup EXIT

# A 類：廣域 grep
# shellcheck disable=SC2086
if ! grep -rlE "${A_PATTERN}" scripts tests/governance > "${tmp_a}" 2>/dev/null; then
  # grep 無命中時 rc=1 且可能空檔
  : > "${tmp_a}"
fi
# 正規化為相對 path（grep -rl 在部分平台給相對、部分含 ./）
if [ -s "${tmp_a}" ]; then
  sed 's|^\./||' "${tmp_a}" | sort -u > "${tmp_a}.n"
  mv "${tmp_a}.n" "${tmp_a}"
fi

if [ ! -s "${tmp_a}" ]; then
  echo "ERROR: A 類 pattern 命中 0 筆（pattern 寫錯，非「沒有 consumer」）" >&2
  exit 1
fi

# B 類：產出端 hook 固定表
cat > "${tmp_b}" <<'EOF'
scripts/doc_format_precheck.sh
scripts/brief_conformance_check.sh
scripts/verdict_filled_check.sh
scripts/gov_check.sh
EOF

# C 類：本 epic 新增元件
cat > "${tmp_c}" <<'EOF'
scripts/gen_govflow_manifest.sh
scripts/_role_gate.sh
tests/governance/test_govflow_manifest.py
tests/governance/test_completeness_idlike_fp.py
tests/governance/test_result_state_format_failed.py
tests/governance/test_rolegate_predispatch.py
tests/governance/test_claimcheck_verbatim_exempt.py
EOF

# D 類：機械抽取 TODO「修改檔案」…「不可做」區間內 path
awk '/^- \*\*修改檔案\*\*/,/^- \*\*不可做\*\*/' "${TODO_PATH}" \
  | grep -oE '(scripts|tests|docs)/[A-Za-z0-9_./-]+' \
  | sed 's/[:.]$//' \
  | sort -u > "${tmp_d}" || true

if [ ! -s "${tmp_d}" ]; then
  echo "ERROR: D 類機械抽取結果為空（TODO 錨點或 path 抽取 pattern 異常）" >&2
  exit 1
fi

sort -u "${tmp_b}" "${tmp_c}" "${tmp_d}" > "${tmp_bcd}"
sort -u "${tmp_a}" "${tmp_b}" "${tmp_c}" "${tmp_d}" > "${tmp_union}"

# ---------------------------------------------------------------------------
# fail-closed：B／C／D 任一 path 不在 PHASE_MAP ⇒ 非零
# （A 類未映射 → phases=-，不得因此非零）
# ---------------------------------------------------------------------------
unmapped_bcd=0
while IFS= read -r p || [ -n "${p}" ]; do
  [ -z "${p}" ] && continue
  ph="$(phase_of "${p}")"
  if [ -z "${ph}" ]; then
    echo "ERROR: B/C/D path 未映射 PHASE_MAP: ${p}" >&2
    unmapped_bcd=1
  fi
done < "${tmp_bcd}"
if [ "${unmapped_bcd}" -ne 0 ]; then
  exit 1
fi

# ---------------------------------------------------------------------------
# 邊界④ 反向收斂：{p : PHASE_MAP[p] != '-'} ⊆ (B ∪ C ∪ D)
# ---------------------------------------------------------------------------
reverse_fail=0
for p in ${PHASE_MAP_KEYS}; do
  [ -z "${p}" ] && continue
  ph="$(phase_of "${p}")"
  [ -z "${ph}" ] && continue
  if [ "${ph}" = "-" ]; then
    continue
  fi
  if ! grep -qxF "${p}" "${tmp_bcd}"; then
    echo "ERROR: PHASE_MAP 反向收斂失敗: ${p} → phases=${ph} 但不在 B∪C∪D（禁把旁觀者直接映射進 Phase）" >&2
    reverse_fail=1
  fi
done
if [ "${reverse_fail}" -ne 0 ]; then
  exit 1
fi

# ---------------------------------------------------------------------------
# 輸出四欄
# ---------------------------------------------------------------------------
nodeid_of() {
  # 測試檔且存在 → 以檔路徑為 nodeid；否則 -
  case "$1" in
    tests/*)
      case "$1" in
        *.py)
          if [ -e "$1" ]; then
            echo "$1"
          else
            echo "-"
          fi
          ;;
        *) echo "-" ;;
      esac
      ;;
    *)
      echo "-"
      ;;
  esac
}

status_of() {
  if [ -e "$1" ]; then
    echo "present"
  else
    echo "MISSING"
  fi
}

while IFS= read -r p || [ -n "${p}" ]; do
  [ -z "${p}" ] && continue
  ph="$(phase_of "${p}")"
  if [ -z "${ph}" ]; then
    # A 類未映射 → 旁觀者
    ph="-"
  fi
  nid="$(nodeid_of "${p}")"
  st="$(status_of "${p}")"
  # 應有 nodeid 而缺：present 的 tests/**/*.py 不得空字串
  if [ "${st}" = "present" ]; then
    case "${p}" in
      tests/*)
        case "${p}" in
          *.py)
            if [ -z "${nid}" ]; then
              echo "ERROR: 應有 nodeid 而缺: ${p}" >&2
              exit 1
            fi
            ;;
        esac
        ;;
    esac
  fi
  printf '%s|%s|%s|%s\n' "${p}" "${ph}" "${nid}" "${st}"
done < "${tmp_union}" | sort -t'|' -k1,1
