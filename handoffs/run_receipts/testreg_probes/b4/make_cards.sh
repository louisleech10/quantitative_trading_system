#!/usr/bin/env bash
# TESTREG Task 4.2：依 p4_wave_eligible.tsv 為每檔產任務卡（目標、主委分類 note、approval_ref、委員交件檔）。
# 用法：bash handoffs/run_receipts/testreg_probes/b4/make_cards.sh
B=handoffs/run_receipts/testreg_probes/b4
mkdir -p "$B/cards"
while IFS=$'\t' read -r n path; do
  g=""
  for k in 5 6 7 8 9 10 11 12 13 14; do
    if grep -qx "$path" "$B/G$k.txt"; then g=$k; break; fi
  done
  [ -n "$g" ] || { echo "no group: $path" >&2; continue; }
  r=$((g + 4))
  slug=$(printf '%s' "$path" | tr '/' '_')
  {
    echo "# 任務卡：$path"
    echo
    echo "- 組：G${g}；approval_ref：handoffs/reconcile/20261010-testreg-x-consult-r$r/synth.md"
    echo "- 委員交件（可讀其對本檔之 note）：handoffs/20261010-testreg-x-consult-r$r-{codex,composer,grok}.md"
    echo "- rewrite 目標（皆於 HEAD 綠、R(t) 非空；機械前篩 p4_free_rt.tsv）："
    awk -F'\t' -v p="$path" '$1==p{print "  - " $2 "（R(t) 符號數 " $3 "）"}' "$B/p4_free_rt.tsv"
    echo "- 主委分類 note："
    awk -F'\t' -v p="$path" '$1==p{print "  " $9}' "$B/claude_G$g.md"
  } > "$B/cards/$slug.md"
done < "$B/p4_wave_eligible.tsv"
ls "$B/cards" | wc -l
