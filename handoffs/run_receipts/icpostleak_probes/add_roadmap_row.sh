#!/bin/zsh
# 於 fact_keys.json 之 roadmap-status 插入 RM-ICPOSTLEAK 列（序 331，緊接 RM-ICFIRSTALIGN 之後）；已存在則不重複
cd /Users/louis/Desktop/quantitative_trading_system || exit 1
F=scripts/fact_keys.json
if jq -e '."roadmap-status".rows[] | select(.[1]=="RM-ICPOSTLEAK")' $F > /dev/null; then echo "已存在"; exit 0; fi
T=$(mktemp)
jq '."roadmap-status".rows |= (
  (map(.[1]) | index("RM-ICFIRSTALIGN")) as $i
  | .[0:($i+1)] + [[
      "331", "RM-ICPOSTLEAK",
      "ICPOSTLEAK：IC 頁「套用後處理」之未來洩漏與 rank／zscore／gaussian 窗未滿即出值（ICFIRSTALIGN 之甲部分）",
      "進行中", "docs/ICPOSTLEAK_SPEC.md",
      "2026-10-01 使用者裁定 FF-STAT 後先修；SPEC v4 凍結（審查 r1–r4）；TODO manifest docs/manifests/ICPOSTLEAK.json 審查中。殘留二條（各分支 zscore 數值核心統一＝needs-research；ICFIRSTALIGN 乙部分＝user-ruling 交全票細項排序諮詢）見 SPEC §N"
    ]] + .[($i+1):]
)' $F > $T && mv $T $F
jq -c '."roadmap-status".rows[] | select(.[1]=="RM-ICPOSTLEAK") | .[0:4]' $F
