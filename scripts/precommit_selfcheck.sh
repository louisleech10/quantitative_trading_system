#!/usr/bin/env bash
# Commit 前自檢：把**秒級**檢查一次跑完，不要讓 14 分鐘的全套去發現 2 分鐘能發現的事。
#
# 為何存在（2026-08-14T09:20+08:00，使用者問「為何跑到第四次才能 commit」）：
#   同一批變更連跑四輪全套 gov_check（每輪約 14 分鐘），前三輪各紅一次：
#     ① G-7 缺 Governance-Scope trailer  → govb1_final_gate --only g7 幾秒可測
#     ② 生成內容含日期                    → 該條測試單獨跑 0.7 秒
#     ③ 白話說明時序過期                  → plain_docs_sync_check 幾秒
#   三者皆為秒級可測，卻由 14 分鐘的全套逐輪吐出 ⇒ 約 40 分鐘純等待。
#   🔴 主委早已把「不要讓 14 分鐘的全套去發現 2 分鐘能發現的事」寫進交接檔紀律，隨即自犯。
#
# 用法：
#   bash scripts/precommit_selfcheck.sh          # commit 前跑（不含 G-7）
#   bash scripts/precommit_selfcheck.sh --post   # commit 後跑（加驗 G-7，須有 commit 才準）
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2
mode="${1:-}"
rc=0
_run() {  # $1=標籤 $2...=指令
  local label="$1"; shift
  local out; out="$("$@" 2>&1)"; local r=$?
  if [ "${r}" -eq 0 ]; then printf '  ✓ %s\n' "${label}"
  else printf '  ✗ %s（rc=%d）\n' "${label}" "${r}"
       printf '%s\n' "${out}" | head -4 | sed 's/^/      /'
       rc=1
  fi
}

echo "── 秒級檢查 ─────────────────────────────"
_run "fact-key 投影一致"      bash scripts/gen_fact_key_blocks.sh --check
_run "機制一覽與實況一致"      bash scripts/list_active_mechanisms.sh --check
_run "白話說明時序"            bash scripts/plain_docs_sync_check.sh

echo "── 分鐘級：改動相關窄測試 ────────────────"
if [ -x venv/bin/python ]; then
  _run "factkey 四檔測試" venv/bin/python -m pytest \
      tests/governance/test_govb1_factkey_gen.py \
      tests/governance/test_govb1_factkey_hook.py \
      tests/governance/test_factkey_write_guard.py \
      tests/governance/test_gov_enforcement_registry.py -q
else
  echo "  ⚠ venv 不存在，略過窄測試"
fi

if [ "${mode}" = "--post" ]; then
  echo "── commit 後才準的檢查 ───────────────────"
  # 🔴 G-7 用 base..HEAD 之 endpoint 淨差，commit 前必為綠（檔還沒進範圍）⇒ 只能 commit 後驗
  _run "G-7 scope 淨差" bash scripts/govb1_final_gate.sh --only g7
fi

echo "─────────────────────────────────────────"
if [ "${rc}" -eq 0 ]; then
  echo "✅ 秒級與窄測試全綠。全套 gov_check 仍須在 push 前跑一次（十分鐘級）。"
else
  echo "🔴 上列已紅 ⇒ **先修再 commit**，不要丟給全套去發現。"
fi
exit "${rc}"
