#!/usr/bin/env bash
# plain_docs_sync_check.sh — 白話說明/ 過期偵測（產出端強制，非靠紀律）
#
# 為何存在（2026-08-05 使用者三次指出，逐次逼出更正確的設計）：
#   ①「白話說明和日誌你忘記或沒做即時更新，就斷了」
#   ②「你也是只會記得更新 README，其他檔案也不一定會記得？
#      而且這個腳本也是要你記得用才會比對，忘記也是沒有？」
#   三個缺陷、三次修正：
#     (a) 只檢查 README   → 改為**逐檔**檢查（見 MANAGED）
#     (b) 腳本要記得跑     → 接進 `scripts/gov_check.sh`（pre-push 唯一委派點）⇒ 忘記也會跑
#     (c) 判準只驗「有沒有動過」→ **實測證偽**：文件先更新、實作後改，仍算動過而放行，
#         **順序完全沒驗**。改為**比新舊**（見下），且**不再需要人工維護 SYNCED-AT 標記**。
#   本專案第 3 條治理原則＝工具必須自帶強制機制，不准靠紀律和記憶。
#
# 判準（可機械算，無主觀，無需人工標記）：
#   對每個受管檔 f 與其 WATCHED 路徑集合 w：
#     last_w = 最後一個觸及 w 的 commit；last_f = 最後一個觸及 f 的 commit
#     若 last_w 存在，且 last_w **不是** last_f 的祖先（含相等）⇒ f 過期。
#   ⇒ 語意＝「實作動了之後，說明檔必須也動過」。同一 commit 內同時改亦視為同步。
#
# 誠實邊界（勿宣稱超出）：
#   1. 只驗**時序**，**不驗內容是否真的反映現況**——可只改一字換綠燈。
#   2. `git push --no-verify` 或 `GOVERNANCE_SKIP_PREPUSH=1` 可繞過。
#   ⇒ 屬「擋意外不防蓄意」，與本 repo 既有機檢同級。內容正確性仍靠審查。
#
# 憲法：bash 3.2；禁 declare -A（用 case 分派）；rc 直接取禁經 pipe；不新增狀態檔。
set -u

REPO="$(git rev-parse --show-toplevel 2>/dev/null)" || { echo "ERROR: 非 git repo（fail-closed）" >&2; exit 2; }
cd "${REPO}" || exit 2

DIR="白話說明"
[ -d "${DIR}" ] || { echo "[plain_docs_sync] 略過（無 ${DIR}/）"; exit 0; }

# 受管檔（不含 Archived/；已封存者不再要求同步）
MANAGED="README.md 第0批-施工清單.md 治理待辦總覽.md 第0批-在做什麼.md"

_watched_for() {
  # bash 3.2 無 declare -A ⇒ case 分派
  case "$1" in
    "README.md"|"第0批-施工清單.md") echo "scripts/ docs/GOVB0_ tests/governance/" ;;
    "治理待辦總覽.md")               echo "handoffs/20260801-GOV-AMEND-BACKLOG.md" ;;
    "第0批-在做什麼.md")             echo "docs/GOVB0_FRICTION_SPEC.md" ;;
    *)                                echo "" ;;
  esac
}

# ── --staged 模式（pre-commit 用）───────────────────────
# 判準：本次 staged 檔案若命中某受管檔的 WATCHED，該受管檔**必須也在同一次 staged**。
# 為何要有這層（2026-08-05 使用者要求「想辦法能確保自己更新」）：
#   只掛 pre-push 的話，要等到 push 才發現，那時 commit 訊息都寫完了 ⇒ 回饋太晚。
#   pre-commit 在**當下**擋住，且語意更嚴（要求同 commit，而非「之後補」）。
if [ "${1:-}" = "--staged" ]; then
  staged="$(git diff --cached --name-only --diff-filter=ACMR)"
  [ -n "${staged}" ] || { echo "[plain_docs_sync] (staged) 無 staged 檔，略過"; exit 0; }

  src=0
  for name in ${MANAGED}; do
    f="${DIR}/${name}"
    watched="$(_watched_for "${name}")"
    [ -n "${watched}" ] || continue

    hit=0
    for w in ${watched}; do
      case "${staged}" in
        *"${w}"*) hit=1; break ;;
      esac
    done
    [ "${hit}" -eq 1 ] || continue

    case "${staged}" in
      *"${f}"*) continue ;;
    esac

    src=1
    echo "[plain_docs_sync] ✗ (staged) ${f} 未一併更新" >&2
    echo "    本次 staged 命中其 WATCHED（${watched}），但該說明檔不在 staged 內。" >&2
  done

  if [ "${src}" -ne 0 ]; then
    echo "  ⇒ 現在更新該說明檔並 git add 最省事；否則 push 時會被硬擋。" >&2
    echo "  出處：使用者 2026-08-05「想辦法能確保自己更新白話說明的文檔」。" >&2
    echo "" >&2
    echo "  🔴 **本層是提醒，不擋 commit**（刻意設計）：若說明檔這次確實無需更動，" >&2
    echo "     硬擋會逼人養成用逃生口的習慣，反而使機制失效。" >&2
    echo "     真正的強制在 pre-push（gov_check 4/4）——**時序判準，繞不過去**：" >&2
    echo "     說明檔的最後更新不得早於其 WATCHED 的最後改動。" >&2
    exit 0
  fi
  echo "[plain_docs_sync] ✓ (staged) 白話說明 與本次改動同步"
  exit 0
fi

rc=0
stale_n=0
n_managed=0

for name in ${MANAGED}; do
  f="${DIR}/${name}"
  n_managed=$((n_managed + 1))

  if [ ! -f "${f}" ]; then
    echo "ERROR: 受管檔缺失: ${f}（fail-closed；若已封存請自 MANAGED 移除並註明）" >&2
    rc=2
    continue
  fi

  watched="$(_watched_for "${name}")"
  if [ -z "${watched}" ]; then
    echo "ERROR: ${name} 無 WATCHED 定義（fail-closed）" >&2
    rc=2
    continue
  fi

  # shellcheck disable=SC2086
  last_w="$(git log --format=%H -1 -- ${watched})"
  [ -n "${last_w}" ] || continue          # WATCHED 從未被改 ⇒ 無需同步

  last_f="$(git log --format=%H -1 -- "${f}")"
  if [ -z "${last_f}" ]; then
    echo "[plain_docs_sync] ✗ 過期: ${f}（尚未進版控，但其 WATCHED 已有改動）" >&2
    stale_n=$((stale_n + 1))
    rc=1
    continue
  fi

  # last_w 是 last_f 的祖先（或相等）⇒ 說明檔不早於實作 ⇒ 同步
  if git merge-base --is-ancestor "${last_w}" "${last_f}" 2>/dev/null; then
    continue
  fi

  stale_n=$((stale_n + 1))
  rc=1
  echo "[plain_docs_sync] ✗ 過期: ${f}" >&2
  echo "    其 WATCHED（${watched}）最後改動 ${last_w:0:8}，晚於本檔最後更新 ${last_f:0:8}" >&2
  echo "    WATCHED 的該次改動：" >&2
  git log --format='      %h %s' -1 "${last_w}" >&2
done

if [ "${rc}" -eq 0 ]; then
  echo "[plain_docs_sync] ✓ 白話說明 全數同步（受管 ${n_managed} 檔，判準＝說明檔不早於其 WATCHED）"
elif [ "${rc}" -eq 1 ]; then
  echo "  ⇒ ${stale_n} 個檔過期。修：更新該檔內容並與實作同 commit（或之後）提交。" >&2
  echo "  出處：使用者 2026-08-05「其他檔案也不一定會記得」「忘記也是沒有」。" >&2
fi
exit "${rc}"
