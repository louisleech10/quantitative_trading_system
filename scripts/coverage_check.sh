#!/usr/bin/env bash
# coverage_check.sh — 機器驗證「研究/大綱的每個項目」都落進 SPEC/TODO（抓「掉項目」churn）。
#
# 根因：3000 行文件超過模型可靠指令預算(~150-200) → 每次重生成隨機掉一批不同項 → V1-V6 churn。
# 解法：把「完整性」從 prose 抽成扁平 manifest（小、在預算內、你看得懂），用機器逐 ID 比對，
#       而非靠 Opus 重讀整份或你逐字看。缺項機器列出 → Opus 只補缺項，不重生成整份。
#
# Manifest ID 慣例：每個必含項用方括號 ID，格式 [A-1] / [C-3] / [P2-4]（字母段-數字）。
#   manifest 範例行：  - [A-1] 風險分級與命中原則
#   SPEC/TODO 對應段任一處出現該 [A-1] 字樣即算覆蓋（建議標在小節標題或 Task 行）。
#
# 用法：bash scripts/coverage_check.sh <manifest_file> <target_doc>
# 退出：0=全覆蓋；1=有缺項(列出)/檔不存在。
# 誠實邊界：只驗 ID「出現」，不驗該 ID 段落內容扎實——後者交 template_check 反空殼 + adversarial。

set -u
manifest="${1:-}"; target="${2:-}"
[ -n "${manifest}" ] && [ -n "${target}" ] || { echo "用法: coverage_check.sh <manifest> <target_doc>"; exit 1; }
[ -f "${manifest}" ] || { echo "ERROR: manifest 不存在: ${manifest}"; exit 1; }
[ -f "${target}" ]   || { echo "ERROR: target 不存在: ${target}"; exit 1; }

# 從 manifest 抽出所有 [X-N] ID（去重、保序）
ids="$(grep -oE '\[[A-Za-z][A-Za-z0-9]*-[0-9]+\]' "${manifest}" | sed 's/^\[//; s/\]$//' | awk '!seen[$0]++')"
[ -n "${ids}" ] || { echo "ERROR: manifest 內找不到任何 [X-N] 格式 ID（慣例：- [A-1] 描述）"; exit 1; }

total=0; missing=""
while IFS= read -r id; do
  [ -z "${id}" ] && continue
  total=$((total+1))
  grep -qF "[${id}]" "${target}" || missing="${missing}  · [${id}]\n"
done <<EOF
${ids}
EOF

miss_n="$(printf "%b" "${missing}" | grep -c '·' || true)"
if [ -n "${missing}" ]; then
  echo "COVERAGE FAIL: ${target} 漏掉 manifest 的 ${miss_n}/${total} 項："
  printf "%b" "${missing}"
  echo "  → Opus 只補這幾項即可（不必重生成整份）。"
  exit 1
fi
echo "COVERAGE PASS: ${target} 涵蓋 manifest 全部 ${total} 項。"
