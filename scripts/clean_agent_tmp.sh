#!/usr/bin/env bash
# 清 `.claude/tmp/` 底下的 agent／治理隔離工作樹（派工收尾固定動作）。
#
# 為什麼存在（2026-08-28 實測）：`.claude/tmp` 長到 **20 GB**，其中單一目錄
# `cleanup-govenf-x-review-r1-grok-atk3-23208` 就佔 9.5 GB——它是委員自建的隔離樹，
# 複製時**沒有排除 `.claude/`**，於是把當時整包 `.claude/tmp`（裡面已有前幾輪的隔離樹）
# 一起複製進 `iso/.claude/`，一層套一層。該目錄真正的產出只有一個 19 KB 的 txt。
#
# 🔴 **根因不在 repo 內的任何腳本**：實查 `tests/governance/test_govflow_manifest.py::_iso_tree`
#    只複製 `scripts`／`tests/governance`／TODO／`handoffs`，其餘 copier 只 `copy2` 單一
#    `settings.json`——**沒有一支會複製 `.claude/` 整棵樹**。做出那 9.5 GB 的是委員 CLI 自己下的
#    ad-hoc 複製指令。⇒ 修不了「別人怎麼複製」，只能讓**殘留不累積**：把清理綁在
#    `agent_postflight.sh`（派工後本來就一定會跑的那一步），不靠紀律。
#
# 保留策略（刻意）：
#   - **只刪目錄**，散檔一律保留。`scripts/fact_keys.json` 把
#     `.claude/tmp/probe_b50.log` 與 `.claude/tmp/s04_export_delivered.sh` 引為治理票之
#     可重跑指令／實證，刪掉會讓那兩張票的證據失效；散檔總量僅數十 MB，不值得為它冒險。
#   - `.claude/gate/`（token／audit log／debt ledger）**不在本腳本範圍內**，一個字都不碰。
#
# 用法：
#   bash scripts/clean_agent_tmp.sh            # 實際刪除
#   bash scripts/clean_agent_tmp.sh --dry-run  # 只列出會刪什麼
set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "CLEAN_AGENT_TMP: 不在 git repo"; exit 2; }
cd "$ROOT" || exit 2

TMP_DIR=".claude/tmp"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

if [ ! -d "$TMP_DIR" ]; then
  echo "CLEAN_AGENT_TMP: ${TMP_DIR} 不存在，無事可做"
  exit 0
fi

# 🔴 rc 直接取，不經 pipe（`cmd | tail; echo rc=$?` 讀到的是 tail 的 rc——本專案踩過）
n_dirs="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
before_kb="$(du -sk "$TMP_DIR" | awk '{print $1}')"

if [ "$n_dirs" = "0" ]; then
  echo "CLEAN_AGENT_TMP ✅ ${TMP_DIR} 無隔離工作樹（現 $((before_kb / 1024)) MB，全為散檔）"
  exit 0
fi

if [ "$DRY" = "1" ]; then
  echo "CLEAN_AGENT_TMP [dry-run] 會刪除 ${n_dirs} 個目錄（${TMP_DIR} 現為 $((before_kb / 1024)) MB）："
  find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -exec du -sh {} + 2>/dev/null | sort -h | tail -10
  exit 0
fi

# `-exec … +` 而非 `-delete`：目錄非空時 `-delete` 會失敗；Finder 會在遍歷途中重建 `.DS_Store`
# 而讓單次 `rm -rf` 回報 "Directory not empty"，故跑兩輪（第二輪收尾）。
find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null
find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} + 2>/dev/null

left="$(find "$TMP_DIR" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
after_kb="$(du -sk "$TMP_DIR" | awk '{print $1}')"
freed_mb=$(((before_kb - after_kb) / 1024))

if [ "$left" != "0" ]; then
  echo "CLEAN_AGENT_TMP ⚠️ 仍有 ${left} 個目錄刪不掉（權限？檔案使用中？）——請人工查看"
  exit 1
fi
echo "CLEAN_AGENT_TMP ✅ 清掉 ${n_dirs} 個隔離工作樹，回收 ${freed_mb} MB（${TMP_DIR} 現為 $((after_kb / 1024)) MB，散檔保留）"
exit 0
