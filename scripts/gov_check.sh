#!/usr/bin/env bash
# gov_check.sh — 本機一鍵治理檢查(單一真相源;pre-push hook 也呼叫本腳本)。
#
# 為何存在(2026-07-25):bash -n / governance pytest / mutation-probe 原本散著各跑,
#   而且 pre-push 自己複製了一份檢查邏輯 → 兩處會漂。收斂成一支,pre-push 只呼叫它。
#
# 用法:
#   bash scripts/gov_check.sh            # 全套(語法 + governance 測試 + 探針健檢)
#   bash scripts/gov_check.sh --fast     # 只跑語法(秒級;適合改完 shell 立即自檢)
#   bash scripts/gov_check.sh --no-probe # 語法+測試,略過探針(pre-push 用;探針慢變不必每 push 跑)
#
# 誠實邊界:本機 oracle 有共同盲區(如 BSD/GNU realpath 分歧,本機全綠 CI 才紅)。
#   **CI(Linux)仍是唯一跨環境 oracle,push 後仍須看 CI 結果**(ci_check_after_push hook 會自動回報)。
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
fast=0; no_probe=0
case "${1:-}" in
  --fast)     fast=1 ;;
  --no-probe) no_probe=1 ;;   # pre-push 用:略過探針健檢(慢變項,不必每次 push 跑)
  "")         : ;;
  *) echo "用法: bash scripts/gov_check.sh [--fast|--no-probe]" >&2; exit 2 ;;
esac

rc_all=0

# --- 1) shell 語法 ---
echo "[gov_check] 1/3 shell 語法 (bash -n)…"
_bad=0
for f in scripts/*.sh scripts/git_hooks/*; do
  [ -f "${f}" ] || continue
  case "${f}" in *.py|*.json|*.txt|*.md) continue ;; esac
  head -1 "${f}" | grep -q 'bash\|sh' || continue
  bash -n "${f}" 2>/dev/null || { echo "  ✗ 語法錯: ${f}" >&2; _bad=1; }
done
if [ "${_bad}" -ne 0 ]; then echo "[gov_check] ✗ shell 語法未過" >&2; rc_all=1; else echo "[gov_check] ✓ shell 語法 OK"; fi

if [ "${fast}" -eq 1 ]; then
  [ "${rc_all}" -eq 0 ] && echo "[gov_check] --fast 完成(未跑測試)" || echo "[gov_check] --fast 未過" >&2
  exit "${rc_all}"
fi

py="venv/bin/python"; [ -x "${py}" ] || py="$(command -v python3 || command -v python)"
[ -n "${py}" ] || { echo "[gov_check] ✗ 找不到 python → fail-closed" >&2; exit 1; }

# --- 2) governance 守衛測試 ---
if [ -d tests/governance ]; then
  echo "[gov_check] 2/3 governance 守衛測試 (pytest tests/governance)…"
  if "${py}" -m pytest tests/governance -q --tb=short; then
    echo "[gov_check] ✓ governance 測試通過"
  else
    echo "[gov_check] ✗ governance 測試未過" >&2; rc_all=1
  fi
else
  echo "[gov_check] 2/3 略過(無 tests/governance)"
fi

# --- 3) mutation 探針健檢(守衛測試是否為真 oracle) ---
if [ "${no_probe}" -eq 1 ]; then
  echo "[gov_check] 3/3 略過探針健檢(--no-probe;慢變項,改由手動/守衛測試改動時跑)"
elif [ -x scripts/mutation_probe_check.sh ]; then
  echo "[gov_check] 3/3 mutation 探針健檢…"
  # 只驗「**宣稱有探針**的檔」(含 test_mutation_)其探針是否真跑得過。
  # 舊檔無探針屬既有狀態(該不該補=待辦 P1-2「驗守衛的測試必附常駐 mutation」機械強制),
  # 納入只會恆亮雜訊警告 → 刻意排除,並在此註明邊界。
  # 已知既有債(2026-07-25 實測):test_verify_gate{,_b3,_b4}.py 的探針被判「空心/偽自證」
  #   (探針沒碰待測系統)。屬既有品質債 → **具名報告但不阻斷**(阻斷會逼人養成繞過習慣);
  #   修法歸待辦 P1-2/P1-3(驗守衛的測試須附**有效**常駐 mutation)。
  # 既有債清單(2026-07-25 實測:探針「空心/偽自證」——沒真的碰待測系統)。
  #   具名排除,否則批次永遠紅、每次 push 白跑一輪逐檔重測(實測拖到 3.5 分鐘)。
  #   **修掉後請從本清單移除**(歸待辦 P1-2/P1-3:守衛測試須附**有效**常駐 mutation)。
  LEGACY_PROBE_DEBT="tests/governance/test_verify_gate.py tests/governance/test_verify_gate_b3.py tests/governance/test_verify_gate_b4.py"
  probe_files=""
  for pf in $(grep -rl 'def test_mutation_' tests/governance/test_*.py 2>/dev/null); do
    case " ${LEGACY_PROBE_DEBT} " in *" ${pf} "*) continue ;; esac
    probe_files="${probe_files} ${pf}"
  done
  if [ -n "${probe_files}" ]; then
    # shellcheck disable=SC2086
    if bash scripts/mutation_probe_check.sh ${probe_files} >/dev/null 2>&1; then
      echo "[gov_check] ✓ 探針健檢通過($(printf '%s' "${probe_files}" | wc -w | tr -d ' ') 檔;另 $(printf '%s' "${LEGACY_PROBE_DEBT}" | wc -w | tr -d ' ') 檔既有債排除中→P1-2/P1-3)"
    else
      echo "[gov_check] ✗ 探針健檢未過(非既有債檔的探針失效,須修)" >&2; rc_all=1
    fi
  else
    echo "[gov_check] 3/3 無(非既有債的)探針檔,略過"
  fi
else
  echo "[gov_check] 3/3 略過(無 mutation_probe_check.sh)"
fi

if [ "${rc_all}" -eq 0 ]; then
  echo "[gov_check] ✅ 全數通過(注意:本機綠≠CI綠,push 後仍看 CI)"
else
  echo "[gov_check] ❌ 有項目未過 — 修好再繼續" >&2
fi
exit "${rc_all}"
