#!/usr/bin/env bash
# mutation_scope_static.sh — TODOFMT Task 1.1：mutation 探針靜態檢查擴至量化三層之獨立入口。
#   規格：docs/TODOFMT_SPEC.md Task 1.1。
#
# 用法：bash scripts/mutation_scope_static.sh      （無參數；僅手動呼叫）
#   選檔：tests/momentum、tests/api、tests/feature_engineering 以 `grep -rl 'def test_mutation_'` 逐目錄選中
#         已宣告探針之檔（opt-in，C-3）；tests/governance 取 test_*.py 中已宣告探針者，扣除 gov_check 第 6 段
#         之既有排除三檔（由該段之 LEGACY_PROBE_DEBT 讀取，本檔不另列、不新增排除）。
#   執行：只呼叫 scripts/mutation_probe_static.py（C-5：不跑 pytest；不呼叫 mutation_probe_check.sh）。
#   rc＝靜態器之 rc；stdout＝靜態器之 fatal 名單。
# 🔴 不掛 hook、不入 pre-push、不入 gov_check、不入收案聚合器之執行陣列；rc 不接任何 fail-stop 鏈。
#   現行 rc 因既有之 fatal 名單而非 0，屬分類器另票（RESID-1），不是本入口之錯。
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
[ $# -eq 0 ] || { echo "用法: bash scripts/mutation_scope_static.sh（無參數）" >&2; exit 2; }
cd "${REPO_ROOT}" || exit 2

PY="${REPO_ROOT}/venv/bin/python"
[ -x "${PY}" ] || PY="$(command -v python3 || true)"
[ -n "${PY}" ] || { echo "mutation_scope_static: 找不到 python3 ⇒ fail-closed" >&2; exit 2; }

_legacy="$(sed -n 's/^[[:space:]]*LEGACY_PROBE_DEBT="\(.*\)"[[:space:]]*$/\1/p' scripts/gov_check.sh | head -1)"

# 選檔抽成函式：bash 3.2 於 $( ) 內解析 case 之右括號會出錯
_select_files() {
  for d in tests/momentum tests/api tests/feature_engineering; do
    [ -d "${d}" ] && grep -rl 'def test_mutation_' "${d}" 2>/dev/null
  done
  for f in tests/governance/test_*.py; do
    [ -f "${f}" ] || continue
    case " ${_legacy} " in
      *" ${f} "*) continue ;;
    esac
    grep -q 'def test_mutation_' "${f}" && printf '%s\n' "${f}"
  done
  return 0
}
_files="$(_select_files)"

set --
while IFS= read -r _f; do
  [ -n "${_f}" ] && set -- "$@" "${_f}"
done <<EOF
$(printf '%s\n' "${_files}" | LC_ALL=C sort -u)
EOF

"${PY}" scripts/mutation_probe_static.py "$@"
exit $?
