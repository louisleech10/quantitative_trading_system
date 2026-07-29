#!/usr/bin/env bash
# Multi-agent 派工「前」快照（搭配 agent_postflight.sh）
#
# 為什麼用檔案系統而非 git：data_cache/ 被 .gitignore 排除（7GB+ 真實資料），
# git status 看不到它的刪除/縮減。必須在檔案系統層級記錄基準。
#
# 用法：bash scripts/agent_preflight.sh   （派工前跑一次）
set -u
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "PREFLIGHT: 不在 git repo"; exit 2; }
cd "$ROOT" || exit 2
SNAP="${1:-/tmp/agent_dc_snapshot.txt}"

if [ -d data_cache ]; then
  fc=$(find data_cache -type f | wc -l | tr -d ' ')
  kb=$(du -sk data_cache | awk '{print $1}')
else
  fc=0; kb=0
fi
# audit.log 行數基準（紅線 3）。事故 2026-07-29：執行端 grok 為「還原探針污染」跑了
#   `git checkout .claude/gate/audit.log`，把本 session 尚未 commit 的 gate 派工紀錄
#   一併還原掉（P16-B3 那筆 dispatch 紀錄 grep -c → 0）。audit 是 append-only 的
#   provenance 真相源，**行數只可增不可減**；git checkout 覆蓋掉的未 commit 內容無法救回。
#   合約早已明禁執行端 git checkout tracked 檔（AGENTS.md），但散文擋不住 → 做成偵測。
# ⚠️ 行數不足以證明 append-only（B3 review 兩家各自實跑打穿）：
#   codex：同長度整體內容替換 → 行數不變 → 舊版檢查 rc=0
#   composer：checkout 後 append 等量垃圾行補回行數 → 舊版檢查 rc=0
#   ⇒ 另記全檔 sha256；postflight 改驗「現檔前 al 行的 sha256 == 快照值」＝真 append-only。
if [ -f .claude/gate/audit.log ]; then
  al=$(wc -l < .claude/gate/audit.log | tr -d ' ')
  ah=$(shasum -a 256 < .claude/gate/audit.log | awk '{print $1}')
else
  al=0; ah="-"
fi
echo "$fc $kb $al $ah" > "$SNAP"
echo "PREFLIGHT 快照：data_cache 檔案數=$fc 大小=${kb}KB audit.log=${al} 行 sha=$(printf '%.8s' "$ah") → $SNAP"
bash scripts/verify_hooks_health.sh || { echo "PREFLIGHT ❌ verify hooks health failed"; exit 2; }
