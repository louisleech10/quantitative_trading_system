#!/usr/bin/env bash
# SessionStart：注入 HANDOFF.md，**並帶上它的時序資訊**（由 git 導出，非手寫）。
#
# 為何存在（2026-08-14，使用者定）：
#   使用者指出「交接打上日期時間，可以明確知道是不是最新的」，理由是
#   「不然你也常搞不清先後順序和最新狀態」——這在同日已實際發生三次：
#     ① 讀到 fact_keys.json 的中間狀態，據此宣稱「主線被改掉、委員違規」（實為委員實驗中）
#     ② 採信 backlog 的過期標記（B-49 標 OPEN，實際當日已退回）
#     ③ 搞不清哪些 commit 碰過哪些檔，G-7 因此紅
#
# 🔴 時間**不寫進 HANDOFF.md**：手寫的會漂——我會忘記更新，於是它顯示舊日期、
#   內容卻是新的，那比沒有更糟（使用者會相信它）。改由 git 導出，不可能漂。
set -u
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || { echo '{}'; exit 0; }
[ -f HANDOFF.md ] || { echo '{}'; exit 0; }

# 最後一次提交時間（ISO，含時區）；未提交過則標明
_ts="$(git log -1 --format=%cI -- HANDOFF.md 2>/dev/null)"
[ -n "${_ts}" ] || _ts="（尚未提交）"
# 工作區是否有未提交的改動 ⇒ 注入內容可能比 git 時間更新
if [ -n "$(git status --porcelain -- HANDOFF.md 2>/dev/null)" ]; then
  _dirty="；⚠️ 工作區有未提交改動，實際內容比上列時間更新"
else
  _dirty=""
fi
_head="$(git log -1 --format=%h 2>/dev/null || echo '-')"

LC_ALL=C jq -Rs --arg ts "${_ts}" --arg d "${_dirty}" --arg h "${_head}" \
  '{"systemMessage": ("=== HANDOFF.md (自動注入) ===\n" +
     "🕐 本檔最後提交：" + $ts + "｜當前 HEAD：" + $h + $d + "\n" +
     "（時間由 git 導出，非手寫；用於判斷本檔相對於其他資訊的新舊）\n\n" + .)}' \
  HANDOFF.md 2>/dev/null || echo '{}'
