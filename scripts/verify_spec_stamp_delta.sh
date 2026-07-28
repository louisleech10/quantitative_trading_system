#!/usr/bin/env bash
# 一次性稽核：證明 SPEC 在三家戳記後的變更「恰為」M20 那一行 VERIFY-EXEMPT 註記
# 起因：GROK-R1-P1-05 抓到 TODO 檔頭寫的 SPEC sha 與磁碟實況不符
set -uo pipefail
SPEC=docs/P16_COMMITTEE_DEBT_SPEC.md
STAMPED=3578b4ae76590584fef7
TMP=$(mktemp)

# 把 M20 行還原成加註記之前的樣子
sed 's/（改法⑦的機械面）〔VERIFY-EXEMPT:doc-example:m20-mutation　本欄描述「改壞後應轉紅」的假設情境，非宣稱已實跑〕/（改法⑦的機械面）/' "$SPEC" > "$TMP"

now=$(shasum -a 256 "$SPEC" | cut -c1-20)
rev=$(shasum -a 256 "$TMP" | cut -c1-20)
echo "戳記時 sha : $STAMPED"
echo "還原後 sha : $rev"
echo "磁碟現況   : $now"
echo "--- 差異行數（還原 vs 現況）---"
diff "$TMP" "$SPEC" | grep -c '^[<>]'
rm -f "$TMP"

if [ "$rev" = "$STAMPED" ]; then
  echo "RESULT: 已證明 — 戳記後的變更恰為 M20 那一行註記，無其他改動"
  exit 0
else
  echo "RESULT: ⚠️ 還原後仍不等於戳記 sha — 尚有其他未交代的改動，須逐行比對"
  exit 1
fi
