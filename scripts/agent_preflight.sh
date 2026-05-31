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
echo "$fc $kb" > "$SNAP"
echo "PREFLIGHT 快照：data_cache 檔案數=$fc 大小=${kb}KB → $SNAP"
