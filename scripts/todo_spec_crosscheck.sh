#!/usr/bin/env bash
# TODO ↔ SPEC 逐 Task 改法編號對照 smoke check
#
# 為何存在（2026-07-28，TODO v1.0 R1 三家 27 findings）：
#   27 條裡 21 條是同一個病——起草者寫 TODO 時**沒有回讀 SPEC 對應段落**，
#   造成「SPEC 有、TODO 沒有或寫反」：探針策略寫成與 SPEC 相反、漏 cutoff、
#   漏 14 檔 DEBT_AUDIT_OVERRIDE、漏 committee_round_open 必填欄位、
#   第六項銷帳條件寫成別的東西。
#   這不是深度不足，是根本沒對照。對照是機械動作，故做成工具。
#
# ⚠️ 誠實邊界（與 spec_fourway_check.sh 同級，**不是保證**）：
#   本腳本只數「SPEC 某 Task 有幾個帶圈改法編號」vs「TODO 該 Task 提到幾個」，
#   **不判斷內容是否正確、不判斷語意是否相反**。
#   G1 那種「TODO 寫了但寫成相反」它抓不到——只有人讀或委員能抓。
#   → 定位＝**漏項 smoke check**（抓「完全沒提」），不是正確性檢查。
#   → 不接入 gov_check.sh，不作為任何 gate 的前置。
#
# 用法：bash scripts/todo_spec_crosscheck.sh [SPEC] [TODO]
set -uo pipefail
SPEC="${1:-docs/P16_COMMITTEE_DEBT_SPEC.md}"
TODO="${2:-docs/P16_COMMITTEE_DEBT_TODO.md}"

echo "=== TODO↔SPEC 改法編號對照（漏項 smoke check）==="
echo "SPEC: $SPEC"
echo "TODO: $TODO"
echo

# 取出 SPEC 裡所有 Task 標題行號
awk '/^\*\*Task [0-9]+\.[0-9]+ /{print NR"\t"$0}' "$SPEC" > /tmp/_spec_tasks.txt

fail=0
while IFS=$'\t' read -r start line; do
  task=$(printf '%s' "$line" | sed -E 's/^\*\*Task ([0-9]+\.[0-9]+).*/\1/')
  # 該 Task 區段 = 從本行到下一個 Task 標題（或檔尾）
  end=$(awk -v s="$start" 'NR>s && /^\*\*Task [0-9]+\.[0-9]+ /{print NR; exit}' "$SPEC")
  [ -z "$end" ] && end=$(wc -l < "$SPEC")

  # SPEC 該 Task 的帶圈改法編號（①-⑨）去重
  spec_marks=$(sed -n "${start},${end}p" "$SPEC" | grep -o '[①②③④⑤⑥⑦⑧⑨]' | sort -u | tr -d '\n')
  n_spec=${#spec_marks}
  [ "$n_spec" -eq 0 ] && continue
  n_spec=$(printf '%s' "$spec_marks" | wc -m | tr -d ' ')

  # TODO 對應 Task 區段
  t_start=$(grep -n "^### Task ${task} " "$TODO" | head -1 | cut -d: -f1)
  if [ -z "$t_start" ]; then
    printf '  ❌ Task %-5s SPEC 有 %s 個改法，TODO **完全沒有這個 Task**\n' "$task" "$n_spec"
    fail=1; continue
  fi
  t_end=$(awk -v s="$t_start" 'NR>s && /^### Task /{print NR; exit}' "$TODO")
  [ -z "$t_end" ] && t_end=$(wc -l < "$TODO")
  t_len=$((t_end - t_start))

  printf '  ·  Task %-5s SPEC 改法 %s 個(%s)　TODO 段落 %s 行\n' \
         "$task" "$n_spec" "$spec_marks" "$t_len"
done < /tmp/_spec_tasks.txt
rm -f /tmp/_spec_tasks.txt

echo
echo "⚠️ 本表**只列數量供人工逐條對照**，不自動判定內容正確。"
echo "   起草者義務：逐個改法編號打開 SPEC 原文，確認 TODO 有對應落點且**語意方向一致**。"
[ "$fail" = 0 ] && echo "CROSSCHECK SMOKE PASS（無 Task 完全缺漏）" || echo "CROSSCHECK SMOKE FAIL（有 Task 完全缺漏）"
exit "$fail"
