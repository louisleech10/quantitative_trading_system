#!/usr/bin/env bash
# 群集歸戶自檢：把收斂檔群集表引用的每個 finding ID，對回附錄原文的斷言首句。
# 目的＝主委自行做「摘句比對」，不再花一輪委員替我抓 ID 錯位（本 session 已 9 次）。
#
# 🔴🔴 這裡沒有機械保護（票 B-36，使用者 2026-08-14T18:05+08:00 要求寫死）
#   本腳本**恆 rc=0**：它只印報告，沒有任何失敗條件。
#   ⇒ 掛到任何閘上都不會擋下任何東西，掛了也是白掛。
#   缺的不是掛載點，是**判定本身還沒寫出來**——要能擋，得先定義「什麼情況算掉項」。
#   已知障礙：唯一訊號「ID 未被任何群集引用」在收斂檔撰寫過程中恆為真
#   ⇒ 直接當失敗條件會高誤擋。
#   在那個判定寫出來之前，**群集掉項只靠人眼**，不得對外宣稱有機械防護。
set -u
cd "$(git rev-parse --show-toplevel)" || exit 2
SYNTH="${1:?用法: bash verify_cluster.sh <synth.md>}"

# 群集表所引用的所有 ID（只取 `## ` 附錄有定義的那些）
ids=$(grep -oE '[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}' "$SYNTH" | sort -u)

for id in $ids; do
  # 該 ID 在群集段（附錄之前）被引用的行
  cited=$(awk -v id="$id" '/^## 附錄/{exit} index($0,id){print NR": "substr($0,1,60)}' "$SYNTH" | head -2)
  # 該 ID 在附錄的斷言首句
  claim=$(awk -v h="## $id" 'index($0,h)==1{f=1;next} /^## /{if(f)exit} f && /斷言/{print;exit}' "$SYNTH" \
          | sed 's/.*斷言[*:： ]*//' | cut -c1-70)
  printf '── %s\n' "$id"
  printf '   附錄斷言: %s\n' "${claim:-（找不到）}"
  if [ -n "$cited" ]; then
    printf '   群集引用: %s\n' "$(printf '%s' "$cited" | head -1)"
  else
    printf '   群集引用: ⚠️ 未被任何群集引用（掉項？）\n'
  fi
done
