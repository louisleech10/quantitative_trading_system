#!/usr/bin/env bash
# mutation_probe_check.sh — 機械驗「聲稱正確性的測試是否真有牙齒」(章程 §B1.1/B1.2/B1.3)。
#
# 為何存在(2026-06-28,FF C1-2 假綠事故 + 機制 review 兩家攻破後硬化):
#   「pytest 全綠」+「git diff grep」抓不到自指 oracle / 空測 / 無效 mutation。
#   唯一可靠 = 每個正確性測試配「會跑、自證基線綠→變異紅」的 in-file `test_mutation_*` 探針,
#   驗收方親跑看真紅真綠(如拿火測煙霧偵測器會叫),非看燈亮。
#
# 用法：bash scripts/mutation_probe_check.sh <test_path> [<test_path>...]
#
# 規則(任一不過 → exit 1):
#   1) 每個含 `(async )?def test_` 的測試檔,須有 ≥1 `def test_mutation_*`,
#      或一行**行首** `# MUTATION-PROBE: n/a — <非空理由>`(不准 docstring 內嵌、不准空理由)。
#   2) 靜態(AST):每個 `test_mutation_*` 非空心/非偽自證(scripts/mutation_probe_static.py)。
#   3) 所有 `test_mutation_*` 探針真跑過(pytest -k test_mutation_ 綠;且 passed > 0)。
#
# 誠實邊界:擋空心/偽 raises/無探針/混批假 N/A;**不**證 oracle 真獨立(B1.2,WARN+adversarial 必審)。
set -u

[ $# -ge 1 ] || { echo "用法: mutation_probe_check.sh <test_path> [<test_path>...]"; exit 1; }

# repo root 鎖定(子目錄執行也對)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PY="${REPO_ROOT}/venv/bin/python"
[ -x "${VENV_PY}" ] || VENV_PY="python"

fail=""

# ---- 收集測試檔 ----
files=""
for p in "$@"; do
  if [ -d "${p}" ]; then
    files="${files}$(find "${p}" -name 'test_*.py' -type f 2>/dev/null)
"
  elif [ -f "${p}" ]; then
    files="${files}${p}
"
  else
    echo "ERROR: 路徑不存在: ${p}"; exit 1
  fi
done

# ---- 規則 1:每測試檔有探針或行首明示豁免(含理由) ----
probe_files=""
while IFS= read -r f; do
  [ -n "${f}" ] || continue
  grep -qE '^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_' "${f}" 2>/dev/null || continue
  if grep -qE '^[[:space:]]*(async[[:space:]]+)?def[[:space:]]+test_mutation_' "${f}" 2>/dev/null; then
    probe_files="${probe_files}${f}
"
    continue
  fi
  # N/A 須行首 + 帶非空理由(— / : / - 後須有非空白字)
  if grep -qE '^[[:space:]]*#[[:space:]]*MUTATION-PROBE:[[:space:]]*n/?a[[:space:]]*[-—:][[:space:]]*[^[:space:]]' "${f}" 2>/dev/null; then
    continue
  fi
  fail="${fail}  · 缺 mutation 探針: ${f}(須 def test_mutation_* 或行首 '# MUTATION-PROBE: n/a — 非空理由')\n"
done <<EOF
${files}
EOF

# ---- 規則 2:靜態 AST 擋空心/偽自證 ----
if [ -n "${probe_files}" ]; then
  static_out="$(printf '%s' "${probe_files}" | tr '\n' '\0' | xargs -0 "${VENV_PY}" "${SCRIPT_DIR}/mutation_probe_static.py" 2>&1)"
  static_rc=$?
  [ -n "${static_out}" ] && echo "${static_out}"
  if [ "${static_rc}" -ne 0 ]; then
    fail="${fail}  · 靜態檢查抓到空心/偽自證探針(見上 MUTATION-PROBE-STATIC FAIL)\n"
  fi
fi

# ---- 規則 3:探針真跑過(精準 -k test_mutation_,經 receipt 包裝) ----
echo "→ 跑 mutation 探針: pytest -k test_mutation_ $*"
# claim-id:單檔用 mutation-<stem>;多檔用 mutation-multi
CLAIM_ID="mutation-multi"
if [ $# -eq 1 ] && [ -f "$1" ]; then
  CLAIM_ID="mutation-$(basename "$1" .py)"
fi
RECEIPTS_DIR="${VERIFY_GATE_RECEIPTS_DIR:-${REPO_ROOT}/handoffs/run_receipts}"
GATE_AUDIT="${VERIFY_GATE_COMMITTEE_AUDIT_LOG:-${REPO_ROOT}/.claude/gate/audit.log}"
probe_out="$(${VENV_PY} "${SCRIPT_DIR}/run_with_receipt.py" --claim-id "${CLAIM_ID}" -- \
  "${VENV_PY}" -W ignore -m pytest -q -p no:cacheprovider -k "test_mutation_" "$@" 2>&1)"
probe_rc=$?
echo "${probe_out}" | tail -3
# receipt 副作用:append 路徑到 gate audit(失敗不影響原 exit code)
receipt_json="$(ls -t "${RECEIPTS_DIR}"/*-"${CLAIM_ID}".json 2>/dev/null | head -1 || true)"
if [ -n "${receipt_json}" ]; then
  mkdir -p "$(dirname "${GATE_AUDIT}")" 2>/dev/null || true
  echo "ts=$(date '+%Y-%m-%d %H:%M:%S') mutation_receipt=${receipt_json}" >> "${GATE_AUDIT}" 2>/dev/null || true
fi
# 取最終 summary 行的 passed 數(tail -1,避免多 'N passed' 取錯)
passed_count="$(echo "${probe_out}" | grep -oE '[0-9]+ passed' | tail -1 | grep -oE '[0-9]+' || echo 0)"
if [ "${probe_rc}" -ne 0 ]; then
  fail="${fail}  · mutation 探針未全綠(pytest rc=${probe_rc})——探針紅=底層測試抓不到注入的 bug,或探針自證注入沒生效\n"
elif [ "${passed_count:-0}" -eq 0 ]; then
  fail="${fail}  · 0 個 test_mutation_ 探針 passed——聲稱正確性卻無可執行探針(或全 skip/xfail)\n"
fi

if [ -n "${fail}" ]; then
  echo "MUTATION-PROBE FAIL:"
  printf "%b" "${fail}"
  echo "  → 章程 §B1.1/B1.2/B1.3:每正確性測試須附自證探針;驗收方親跑看真紅真綠,禁只看全綠 grep。"
  exit 1
fi
echo "MUTATION-PROBE PASS: 受審測試檔皆有探針(或行首 N/A+理由),靜態無空心/偽自證,且 ${passed_count} 個探針真跑過。"
