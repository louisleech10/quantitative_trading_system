#!/usr/bin/env bash
# Multi-agent 派工「後」安全檢查（council review #5 的實體防線）
#
# 為什麼存在：cursor --force / agy --dangerously-skip-permissions / codex 非互動
# 把「不刪 data_cache、不改 git 歷史」推給模型自律（靠 prompt）。本腳本實體把關。
# 退出碼非 0 = 偵測到違規，Claude 必須停下調查，不得逕自驗收。
#
# ⚠️ data_cache/ 被 .gitignore 排除（git 看不到），故用檔案系統快照比對（需先跑
#    agent_preflight.sh）。限制：以「檔案數 + 總大小」抓刪除/縮減；靜默內容竄改
#    （大小不變）無法用此廉價法偵測，7GB+ 全量 checksum 太慢，屬已知取捨。
#
# 用法：bash scripts/agent_postflight.sh   （派工後跑）
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "POSTFLIGHT: 不在 git repo"; exit 2; }
cd "$ROOT" || exit 2
SNAP="${1:-/tmp/agent_dc_snapshot.txt}"
fail=0

# 紅線 1：data_cache/ 完整性（檔案系統層級）
if [ -d data_cache ]; then
  fc=$(find data_cache -type f | wc -l | tr -d ' ')
  kb=$(du -sk data_cache | awk '{print $1}')
else
  fc=0; kb=0
fi
if [ -f "$SNAP" ]; then
  read -r ofc okb < "$SNAP"
  if [ "$fc" -lt "$ofc" ] || [ "$kb" -lt "$okb" ]; then
    echo "POSTFLIGHT ❌ data_cache 縮減！before(檔$ofc/${okb}KB) → after(檔$fc/${kb}KB) — 疑似刪除/損毀，停下調查"
    fail=1
  else
    echo "POSTFLIGHT ✅ data_cache 完整（檔$fc/${kb}KB，未縮減）"
  fi
else
  echo "POSTFLIGHT ⚠️ 無 preflight 快照（$SNAP）→ 無法比對 data_cache，請先跑 scripts/agent_preflight.sh"
  fail=1
fi

# 紅線 2：git 追蹤範圍內的改動（force push/history 改寫無法事後從 worktree 完整測，
#         此處列出工作樹改動供 Claude 人工確認沒有越界）
porcelain="$(git status --porcelain)"
echo "--- 工作樹改動 (git status --porcelain) ---"
if [ -n "$porcelain" ]; then echo "$porcelain"; else echo "（無）"; fi

bash scripts/verify_hooks_health.sh || { echo "POSTFLIGHT ❌ verify hooks health failed"; fail=1; }

exit "$fail"
