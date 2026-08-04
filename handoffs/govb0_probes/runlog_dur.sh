#!/usr/bin/env bash
# runlog_dur.sh — 主委獨立重算委員 runlog 時長分布（驗證 COMPOSER Q1 的數據）。
# 定義：時長 = mtime - birthtime（macOS stat -f）。唯讀。
set -u

out=".claude/tmp/dur.tsv"
: > "$out"
for f in handoffs/*.runlog; do
  [ -f "$f" ] || continue
  # 家族由檔名後綴推定
  case "$f" in
    *-codex.runlog) fam=codex ;;
    *-composer.runlog) fam=composer ;;
    *-grok.runlog) fam=grok ;;
    *) fam=other ;;
  esac
  b="$(stat -f %B "$f" 2>/dev/null)" || continue
  m="$(stat -f %m "$f" 2>/dev/null)" || continue
  d=$(( m - b ))
  [ "$d" -ge 0 ] || continue
  printf '%s\t%s\t%s\n' "$fam" "$d" "$f" >> "$out"
done

echo "TOTAL_RUNLOGS=$(wc -l < "$out" | tr -d ' ')"
echo
printf '%-10s %5s %8s %8s %8s %8s\n' family n p50 p95 p99 max
for fam in ALL codex composer grok; do
  if [ "$fam" = ALL ]; then
    vals="$(awk -F'\t' '{print $2}' "$out" | sort -n)"
  else
    vals="$(awk -F'\t' -v f="$fam" '$1==f{print $2}' "$out" | sort -n)"
  fi
  n=$(printf '%s\n' "$vals" | grep -c '[0-9]' || true)
  [ "$n" -gt 0 ] || continue
  pick() { # $1=percentile
    idx=$(( (n * $1 + 99) / 100 )); [ "$idx" -lt 1 ] && idx=1
    printf '%s\n' "$vals" | sed -n "${idx}p"
  }
  p50=$(pick 50); p95=$(pick 95); p99=$(pick 99); mx=$(printf '%s\n' "$vals" | tail -1)
  printf '%-10s %5s %7.1fm %7.1fm %7.1fm %7.1fm\n' "$fam" "$n" \
    "$(echo "$p50" | awk '{print $1/60}')" \
    "$(echo "$p95" | awk '{print $1/60}')" \
    "$(echo "$p99" | awk '{print $1/60}')" \
    "$(echo "$mx"  | awk '{print $1/60}')"
done

echo
echo "── 最長 5 筆（分鐘）──"
sort -t"$(printf '\t')" -k2 -n -r "$out" | head -5 | awk -F'\t' '{printf "  %7.1fm  %s\n", $2/60, $3}'

echo
echo "── 若採 composer 建議值，誤殺數（clean=排除 >90m）──"
for pair in "codex 3000" "grok 3900" "composer 4500"; do
  fam=${pair% *}; lim=${pair#* }
  k=$(awk -F'\t' -v f="$fam" -v L="$lim" '$1==f && $2>L && $2<=5400 {c++} END{print c+0}' "$out")
  tot=$(awk -F'\t' -v f="$fam" '$1==f && $2<=5400 {c++} END{print c+0}' "$out")
  printf '  %-9s limit=%sm  誤殺 %s/%s\n' "$fam" "$((lim/60))" "$k" "$tot"
done
