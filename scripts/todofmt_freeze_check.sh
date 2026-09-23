#!/usr/bin/env bash
# todofmt_freeze_check.sh — TODOFMT Task 3.3：收案聚合入口（檔名沿用 r3；語意為收案判定）。
#   規格：docs/TODOFMT_SPEC.md §P 收案判定表與「聚合入口規則」三句、Task 3.3。
#
# 用法：
#   bash scripts/todofmt_freeze_check.sh                                   # 收案判定（只用下方字面陣列；不讀 SPEC）
#   bash scripts/todofmt_freeze_check.sh --items-file <檔>                 # 測試用：以參數傳入執行陣列（一行一項）
#   bash scripts/todofmt_freeze_check.sh --compare <期望檔> <紀錄檔>       # 測試用：只跑「紀錄＝陣列」之比對
# rc：0＝全部通過且紀錄與陣列逐項相等／1＝有未通過或紀錄不等／2＝用法錯
#
# 規則（SPEC 三句）：
#   1. 執行清單與期望集合＝本檔同一字面陣列；每項為完整 argv（以空白分隔、不含 glob 字元、不含 gate.sh），預期 rc=0。
#   2. 每項只在其行程結束並取得 rc 之後才追加進執行紀錄；返回前比對紀錄與陣列（逐項、同序），不等即 rc 非 0。
#   3. pytest 項之摘要含 skipped／xfailed／xpassed 者計為未通過；任一未通過即聚合 rc 非 0。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# BEGIN TODOFMT FREEZE ITEMS（收案判定表之權威；本表為其唯一來源，SPEC 表為說明）
_ITEMS='
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_contract.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_template_check_todofmt.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_mutation_scope_extension.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_write_guard.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_gate_todo_routing.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_gate_impl_requires_manifest.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_template.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_constitution_sync.py
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_sample_self.py
bash scripts/template_check.sh todofmt docs/manifests/TODOFMT.json
venv/bin/python -m pytest -q -p no:cacheprovider tests/governance/test_todofmt_sample_fftfmeta.py
bash scripts/template_check.sh todofmt docs/manifests/FFTFMETA.json
'
# END TODOFMT FREEZE ITEMS

_nonblank() { printf '%s\n' "$1" | sed '/^[[:space:]]*$/d'; }

# 紀錄＝陣列：逐項、同序（多一項、少一項、順序不同皆不等）
_compare() {
  [ "$(_nonblank "$1")" = "$(_nonblank "$2")" ]
}

case "${1:-}" in
  --compare)
    [ $# -eq 3 ] && [ -f "$2" ] && [ -f "$3" ] || { echo "用法: --compare <期望檔> <紀錄檔>" >&2; exit 2; }
    _compare "$(cat "$2")" "$(cat "$3")" && exit 0 || exit 1 ;;
  --items-file)
    [ $# -eq 2 ] && [ -f "$2" ] || { echo "用法: --items-file <檔>" >&2; exit 2; }
    _ITEMS="$(cat "$2")" ;;
  "") : ;;
  *) echo "用法: todofmt_freeze_check.sh [--items-file <檔> | --compare <期望檔> <紀錄檔>]" >&2; exit 2 ;;
esac

cd "${REPO_ROOT}" || exit 2
_expected="$(_nonblank "${_ITEMS}")"
[ -n "${_expected}" ] || { echo "TODOFMT FREEZE FAIL：執行陣列為空" ; exit 1; }

_record=""
_failed=0
while IFS= read -r _item; do
  [ -n "${_item}" ] || continue
  set -f
  # shellcheck disable=SC2086
  set -- ${_item}
  set +f
  _out="$("$@" 2>&1 </dev/null)"
  _rc=$?
  _why=""
  if [ "${_rc}" -ne 0 ]; then
    _why="rc=${_rc}"
  elif printf '%s' "${_item}" | grep -q -- '-m pytest'; then
    # 只認 pytest 之結果摘要行（「N passed, M skipped in Xs」，可夾 = 框線），不論其在第幾行：
    #   b2 審碼 codex／grok：只看末三行時，摘要之後另有輸出即漏判；
    #   b3 主委實跑：全文掃描會把參數化測試名中之「− skipped」誤判為計數。
    #   找不到摘要行即 fail-closed（不當作通過）。
    _summary="$(printf '%s\n' "${_out}" | grep -E '^=*[[:space:]]*[0-9]+ [a-z]+(, [0-9]+ [a-z]+)* in [0-9.]+s' || true)"
    if [ -z "${_summary}" ]; then
      _why="找不到 pytest 結果摘要行"
    elif printf '%s\n' "${_summary}" | grep -Eq '[0-9]+ (skipped|xfailed|xpassed)'; then
      _why="含 skipped／xfailed／xpassed"
    fi
  fi
  # 規則 2：取得 rc 之後才追加紀錄
  _record="${_record}${_item}
"
  if [ -n "${_why}" ]; then
    _failed=1
    echo "FAIL（${_why}）：${_item}"
    printf '%s\n' "${_out}" | tail -n 5 | sed 's/^/    /'
  else
    echo "PASS：${_item}"
  fi
done <<EOF
${_expected}
EOF

if ! _compare "${_expected}" "${_record}"; then
  echo "TODOFMT FREEZE FAIL：執行紀錄與陣列不等（有項目未執行或多執行）"
  exit 1
fi
if [ "${_failed}" -ne 0 ]; then
  echo "TODOFMT FREEZE FAIL：有項目未通過"
  exit 1
fi
echo "TODOFMT FREEZE PASS：$(printf '%s\n' "${_expected}" | wc -l | tr -d ' ') 項皆通過"
exit 0
