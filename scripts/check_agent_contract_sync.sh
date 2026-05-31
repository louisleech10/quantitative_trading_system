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

CONTRACT_FILES=("AGENTS.md" ".cursorrules")           # 執行端合約（9 點）兩份須一致
ALL_FILES=("AGENTS.md" ".cursorrules" "CLAUDE.md" "docs/MULTI_AGENT_ORCHESTRATION.md")

# 執行端合約兩份都該有的不變式 token
CONTRACT_TOKENS=("STATUS: BLOCKED" "handoffs/" "data_cache" "SMALL_INLINE" "ASSUMPTIONS_VERIFIED" "反提示注入")
# 全體都該提到的關鍵概念
GLOBAL_TOKENS=("preflight" "斷路器" "委員會")

fail=0
echo "=== 執行端合約一致性（AGENTS.md / .cursorrules）==="
for tok in "${CONTRACT_TOKENS[@]}"; do
  for f in "${CONTRACT_FILES[@]}"; do
    if ! grep -qF "$tok" "$f" 2>/dev/null; then
      echo "❌ 缺「$tok」於 $f"; fail=1
    fi
  done
done

echo "=== 全體關鍵概念存在性 ==="
for tok in "${GLOBAL_TOKENS[@]}"; do
  present=0
  for f in "${ALL_FILES[@]}"; do grep -qF "$tok" "$f" 2>/dev/null && present=1; done
  [ "$present" -eq 0 ] && { echo "❌ 「$tok」在 4 份檔皆未出現"; fail=1; }
done

if [ "$fail" -eq 0 ]; then
  echo "✅ 四源關鍵不變式一致（presence check）"
else
  echo "⚠️ 偵測到不同步 —— 改協作規則後請同步 4 處"
fi
exit "$fail"
