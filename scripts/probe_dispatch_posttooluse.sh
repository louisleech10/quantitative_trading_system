#!/usr/bin/env bash
# probe_dispatch_posttooluse.sh — 票 B-7／B-32／B-50 之「能不能掛」實測探針（臨時）。
#
# 為何存在（使用者 2026-08-14T18:40+08:00）：
#   「沒有什麼可能、推理、想看看——你用推理都全錯。只有掛上和不掛兩種結果。」
#   這三張票的登記理由目前寫的是「觸發源為派工指令而非 Edit/Write ⇒ 該 hook 不觸發」
#   與「PostToolUse 取不到派工前那個快照」。前者只描述**現行 matcher**，
#   不等於 PostToolUse:Bash 掛不上；後者才是真正的判定限制。
#   ⇒ 唯一能分辨的方法：**真的掛一個 PostToolUse:Bash，看派工指令結束當下它看得到什麼。**
#
# 行為：只在 tool_input.command 含 committee_run／cx_run 時記錄一筆到
#   .claude/tmp/probe_b50.log，其餘一律 rc=0 立即返回（零干擾）。
#   永遠 rc=0——探針不得擋任何事。
#
# 🔴 **已於 2026-08-14 用畢並自 .claude/settings.json 拆除**〔`CODEX-R1-P1-02`：
#   臨時探針留在正式設定檔內屬部署完整性問題〕。本檔保留為**可重跑的量測工具**，
#   不掛任何自動路徑。要再測就手動加回 PostToolUse:Bash 一行，測完再拆。
#
# ── 實測結論（就是這一次跑出來的）──────────────────────────────────
#   · PostToolUse:Bash **確實會**在派工指令上觸發（原登記寫「該 hook 不觸發」是錯的）
#   · 但觸發當下 handoffs/ 下**只有 brief**，零個委員產出檔
#     ⇒ 委員派工依合約背景執行，hook 觸發於**啟動當下**而非完成當下
#   · 工作區 dirty 計數等於派工前之值 ⇒ B-50 要的「派工後快照」根本尚未發生
#   ⇒ 票 B-7／B-32／B-50 三張的 PostToolUse 掛載**確定不成立**，理由已寫進登記表。
set -u
REPO="$(cd "$(dirname "${0}")/.." && pwd)"
LOG="${REPO}/.claude/tmp/probe_b50.log"

[ -t 0 ] && exit 0

payload="$(cat 2>/dev/null || true)"
cmd="$(printf '%s' "${payload}" | python3 -c 'import json,sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
print((d.get("tool_input") or {}).get("command") or "")' 2>/dev/null || true)"

case "${cmd}" in
  *committee_run*|*cx_run*) : ;;
  *) exit 0 ;;
esac

{
  echo "=== PostToolUse:Bash 觸發於派工指令結束當下 ==="
  echo "cmd(前 160 字): $(printf '%s' "${cmd}" | cut -c1-160)"
  echo "--- 委員產出檔現況（這就是 PostToolUse 看得到的東西）---"
  ls -la "${REPO}"/handoffs/20260814-govmount* 2>&1 || echo "(無)"
  echo "--- 工作區 dirty 檔數 ---"
  cd "${REPO}" && git status --porcelain 2>/dev/null | wc -l
  echo ""
} >> "${LOG}" 2>&1

exit 0
