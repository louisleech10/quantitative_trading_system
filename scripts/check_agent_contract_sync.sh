#!/usr/bin/env bash
# 四源規則同步檢查（council Round 2 #Composer7 / #7）
#
# 為什麼存在：執行合約/協作規則散在 4 個檔（AGENTS.md / .cursorrules / CLAUDE.md /
# docs/MULTI_AGENT_ORCHESTRATION.md），改一處忘了同步其他 → 執行端讀到不一致合約。
# 本腳本檢查關鍵不變式 token 是否在「應該出現的檔」都存在（presence checklist，非語意 diff）。
#
# 用法：bash scripts/check_agent_contract_sync.sh   （改完協作規則後跑）
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "不在 git repo"; exit 2; }
cd "$ROOT" || exit 2

CONTRACT_FILES=("AGENTS.md" ".cursorrules")
PLANNER_FILES=("CLAUDE.md" "docs/MULTI_AGENT_ORCHESTRATION.md")
ORCH_FILE="docs/MULTI_AGENT_ORCHESTRATION.md"
EXECUTOR_HARDEN_FILES=("CLAUDE.md" "AGENTS.md" ".cursorrules")

# CONTRACT_REQUIRED：執行端合約兩份皆須含
CONTRACT_TOKENS=("STATUS: BLOCKED" "handoffs/" "data_cache" "SMALL_INLINE" "ASSUMPTIONS_VERIFIED" "反提示注入" "register-output" "RECONCILE-STAMP" "VERIFY")
# 兩輪斷路器：接受「≤ 2 輪」或「兩輪」任一命中
CIRCUIT_BREAKER_PATTERNS=("≤ 2 輪" "兩輪")
# PLANNER_REQUIRED：規劃層至少一處須含（CLAUDE.md 或 ORCH）
PLANNER_TOKENS=("preflight" "斷路器" "委員會")

fail=0

# 四檔存在性
for f in "${CONTRACT_FILES[@]}" "${PLANNER_FILES[@]}"; do
  if [ ! -f "$f" ]; then
    echo "❌ 檔案不存在: $f"; fail=1
  fi
done

echo "=== 執行端合約一致性（AGENTS.md / .cursorrules）==="
for tok in "${CONTRACT_TOKENS[@]}"; do
  for f in "${CONTRACT_FILES[@]}"; do
    if ! grep -qF "$tok" "$f" 2>/dev/null; then
      echo "❌ 缺 '${tok}' 於 $f"; fail=1
    fi
  done
done

# 兩輪斷路器字樣（兩份合約皆須含 ≤ 2 輪 或 兩輪 其一）
for f in "${CONTRACT_FILES[@]}"; do
  cb_ok=0
  for pat in "${CIRCUIT_BREAKER_PATTERNS[@]}"; do
    grep -qF "$pat" "$f" 2>/dev/null && cb_ok=1
  done
  if [ "$cb_ok" -eq 0 ]; then
    echo "❌ 缺兩輪斷路器字樣（≤ 2 輪 或 兩輪）於 $f"; fail=1
  fi
done

echo "=== 規劃層關鍵概念存在性（CLAUDE.md / ORCH 至少一處）==="
for tok in "${PLANNER_TOKENS[@]}"; do
  present=0
  for f in "${PLANNER_FILES[@]}"; do
    grep -qF "$tok" "$f" 2>/dev/null && present=1
  done
  [ "$present" -eq 0 ] && { echo "❌ '${tok}' 在 CLAUDE.md / ORCH 皆未出現"; fail=1; }
done

echo "=== 選層單一來源反向檢查 ==="
if [ -f "$ORCH_FILE" ]; then
  anchor_count="$(grep -cE '^\*\*現行分工|^- \*\*現行分工|現行分工[（(]' "$ORCH_FILE" 2>/dev/null || echo 0)"
  if [ "$anchor_count" -ne 1 ]; then
    echo "❌ ORCH 權威錨點行計數須 == 1（現為 ${anchor_count}）: $ORCH_FILE"; fail=1
  fi
fi

for f in "${EXECUTOR_HARDEN_FILES[@]}"; do
  if [ -f "$f" ]; then
    hardcoded="$(grep -nE 'Codex.*實作|Composer.*實作|GPT-5.5.*實作' "$f" 2>/dev/null || true)"
    if [ -n "$hardcoded" ]; then
      echo "❌ $f 寫死執行端分工（須改為 ORCH 錨點 pointer）:"
      echo "$hardcoded"
      fail=1
    fi
  fi
done

if [ "$fail" -eq 0 ]; then
  echo "✅ 四源關鍵不變式一致（presence check）"
else
  echo "⚠️ 偵測到不同步 —— 改協作規則後請同步 4 處"
fi
exit "$fail"
