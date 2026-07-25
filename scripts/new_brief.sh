#!/usr/bin/env bash
# new_brief.sh — 產出**必過 P1-1 brief 合規閘**的 brief 骨架(免得手寫漏條款被自己的閘擋)。
#
# 為何存在(2026-07-25):cx_run.sh 的 P1-1 閘要求 findings 類 brief 須
#   ①宣告 brief-kind ②引用委員範本 ③含 ≥1 `fact-verified:` 與 ≥1 `assumed:`。
#   我手寫時被自己的閘擋過(把 assumed 寫成粗體 `**assumed**:` 讓 grep 抓不到 token)。
#   本腳本把 token 以**字面**寫死,格式一次到位;內容(判斷)仍由我填。
#
# 用法:
#   bash scripts/new_brief.sh <kind> <輸出路徑> ["標題"]
#   kind ∈ review|consult|closure|impl|stamp
set -u

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo .)" || exit 2

kind="${1:-}"; out="${2:-}"; title="${3:-}"
[ -n "${kind}" ] && [ -n "${out}" ] || {
  echo "用法: bash scripts/new_brief.sh <review|consult|closure|impl|stamp> <輸出路徑> [\"標題\"]" >&2; exit 2; }
case "${kind}" in review|consult|closure|impl|stamp) : ;;
  *) echo "ERROR: 未知 kind '${kind}'(允許 review|consult|closure|impl|stamp)" >&2; exit 2 ;; esac
[ -e "${out}" ] && { echo "ERROR: 檔已存在,拒覆寫: ${out}" >&2; exit 2; }
case "${out}" in handoffs/*) : ;; *) echo "ERROR: brief 建議放 handoffs/: ${out}" >&2; exit 2 ;; esac
[ -n "${title}" ] || title="（填標題）"

{
  echo "# ${title}"
  echo ""
  echo "brief-kind: ${kind}"
  echo ""
  if [ "${kind}" = "impl" ] || [ "${kind}" = "stamp" ]; then
    echo "## 任務"
    echo "（照 <TODO/規格路徑> 實作 …；逐 Task 照做）"
    echo ""
    echo "## 硬性要求"
    echo "1. 每個新測試須 mutation 自證（revert 修法→轉紅），提交前實跑貼 rc。"
    echo "2. 不放寬既有斷言換綠；\`pytest\` 全綠 + \`bash -n scripts/*.sh\` rc=0。"
    echo "3. **先不要 push**（Claude 驗 + 委員審後才 push）；可本地 commit。"
    echo ""
    echo "## 產出"
    echo "改了哪些檔/函式、新增/改的測試、實跑結果與 rc、遇到的問題。收尾清 /tmp workdir（保留 claude-501）。"
  else
    echo "## 範本"
    echo "照 \`templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md\` 全文執行（§0 挑戰前提／§1 必查／§2 獵空殼／canonical 四欄／Verdict）。"
    echo "findings 用 canonical ID：\`## <FAMILY>-R<輪次>-P<0-3>-<NN>\`（見 \`templates/COMMITTEE_FINDING_TEMPLATE.md\`）。"
    echo ""
    echo "## ⚠️ 前置說明（勿誤 block）"
    echo "- \`handoffs/reconcile/*/synth.md\` 等是**無戳記診斷/輸入檔**，非 gating 檔；勿 STAMP-BLOCK、勿對它們跑 \`reconcile_stamps_check.sh\`。"
    echo ""
    echo "## 審查標的"
    echo "- （標的檔／真實 diff 指令）"
    echo ""
    echo "## 本 brief 前提（逐條標；請優先攻 assumed）"
    echo "fact-verified: （已查證的事實） → （查證方式/實跑結果）"
    echo "assumed: （我的假設，可能是錯的） ← 請直接攻這條"
    echo ""
    echo "## 必答（逐條 verdict）"
    echo "1. （問題一）"
    echo "2. 可以進下一步嗎，還是有 BLOCKING 必須先修？"
    echo ""
    echo "## 產出"
    echo "canonical 四欄 findings + **Verdict**。**禁改碼**（只產 review 檔）。收尾清 /tmp workdir（保留 claude-501）。"
  fi
} > "${out}"

echo "[new_brief] 已產出 ${out}（kind=${kind}）"
echo "[new_brief] ⚠️ 骨架只保證**格式過閘**；內容(標的/前提/必答)仍須你填真實判斷,勿留佔位就派工。"
if [ "${kind}" != "impl" ] && [ "${kind}" != "stamp" ]; then
  echo "[new_brief] 提醒:fact-verified/assumed 各至少一條、且 token 須**字面**(勿寫成 **assumed**: 粗體會打斷 grep)。"
fi
