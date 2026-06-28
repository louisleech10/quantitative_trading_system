#!/usr/bin/env bash
# mutation_probe_check.sh — 機械驗「聲稱正確性的測試是否真有牙齒」(章程 §B1.1/B1.2/B1.3)。
#
# 為何存在(2026-06-28,FF C1-2 假綠事故後):
#   「pytest 全綠」+「git diff grep 沒放寬斷言」抓不到自指 oracle / 空測 / 無效 mutation。
#   唯一可靠 = 每個正確性測試配「會跑、自證基線綠→變異紅」的 in-file `test_mutation_*` 探針,
#   驗收方親自跑探針看真紅真綠(如拿火測煙霧偵測器會叫),非看燈亮。
#
# 用法：bash scripts/mutation_probe_check.sh <test_path> [<test_path>...]
#   <test_path> = 受審的正確性測試檔或目錄。
#
# 規則(任一不過 → exit 1):
#   1) 每個含 `def test_` 的測試檔,須有 ≥1 `def test_mutation_*`,
#      或明示一行 `# MUTATION-PROBE: n/a — <理由>`(非 correctness/純邊界 smoke;不准靜默)。
#   2) 路徑下所有 `test_mutation_*` 探針須真跑過(pytest -k mutation 綠;且收集數 > 0)。
#      探針綠 = 它內部已自證「注入壞改後底層斷言 pytest.raises 真紅」。
#
# 誠實邊界:本閘保證「探針存在且會跑且綠」,以及「沒探針的檔有明示豁免」。
#   它不替你判斷探針內的 oracle 是否獨立(B1.2)——那仍須 adversarial 標準必問。
set -u

[ $# -ge 1 ] || { echo "用法: mutation_probe_check.sh <test_path> [<test_path>...]"; exit 1; }

VENV_PY="venv/bin/python"
[ -x "${VENV_PY}" ] || VENV_PY="python"

fail=""

# ---- 規則 1:每個測試檔有探針或明示豁免 ----
files=""
for p in "$@"; do
  if [ -d "${p}" ]; then
    found="$(find "${p}" -name 'test_*.py' -type f 2>/dev/null)"
    files="${files}${found}
"
  elif [ -f "${p}" ]; then
    files="${files}${p}
"
  else
    echo "ERROR: 路徑不存在: ${p}"; exit 1
  fi
done

while IFS= read -r f; do
  [ -n "${f}" ] || continue
  grep -qE '^[[:space:]]*def test_' "${f}" 2>/dev/null || continue   # 無測試的檔跳過
  if grep -qE '^[[:space:]]*def test_mutation_' "${f}" 2>/dev/null; then
    continue
  fi
  if grep -qE '#[[:space:]]*MUTATION-PROBE:[[:space:]]*n/?a' "${f}" 2>/dev/null; then
    continue   # 明示豁免(理由須在同行,供稽核)
  fi
  fail="${fail}  · 缺 mutation 探針: ${f}(須 def test_mutation_* 或 '# MUTATION-PROBE: n/a — 理由')\n"
done <<EOF
${files}
EOF

# ---- 規則 2:所有 mutation 探針真跑過 ----
echo "→ 跑 mutation 探針: pytest -k mutation $*"
probe_out="$(${VENV_PY} -W ignore -m pytest -q -p no:cacheprovider -k "mutation" "$@" 2>&1)"
probe_rc=$?
echo "${probe_out}" | tail -3
collected="$(echo "${probe_out}" | grep -oE '[0-9]+ passed' | head -1 | grep -oE '[0-9]+' || echo 0)"
if [ "${probe_rc}" -ne 0 ]; then
  fail="${fail}  · mutation 探針未全綠(pytest rc=${probe_rc})——探針紅=底層測試抓不到注入的 bug,或探針自證注入沒生效\n"
elif [ "${collected:-0}" -eq 0 ]; then
  fail="${fail}  · 路徑下收集到 0 個 mutation 探針——聲稱正確性卻無可執行探針\n"
fi

if [ -n "${fail}" ]; then
  echo "MUTATION-PROBE FAIL:"
  printf "%b" "${fail}"
  echo "  → 章程 §B1.1/B1.2/B1.3:每正確性測試須附自證探針;驗收方親跑看真紅真綠,禁只看全綠 grep。"
  exit 1
fi
echo "MUTATION-PROBE PASS: 所有受審測試檔有探針(或明示豁免),且 ${collected} 個探針真跑過。"
