#!/usr/bin/env bash
# 派工狀態板——讓使用者從輸出直接看出「哪個 CLI 在跑、跑多久、在等什麼」。
#
# 為何存在(2026-07-29 使用者原話):
#   「很多時候你吐完字就沒了,我不知道你是在等各委員的回報還是什麼狀態,
#     我還無法知道各 CLI 是怎樣的狀態」
#   → 狀態必須是【查出來的資料】,不是 Claude 的描述。每則回覆結尾貼本腳本輸出。
#
# 用法:bash scripts/dispatch_status.sh
set -uo pipefail

echo "┌─ 派工狀態  $(date '+%H:%M:%S') ────────────────────────────"

# ── 1. 正在跑的委員 CLI ──────────────────────────────────────
found=0
while IFS= read -r line; do
  [ -z "$line" ] && continue
  pid=$(printf '%s' "$line" | awk '{print $1}')
  et=$(printf '%s'  "$line" | awk '{print $2}')
  # 從 cx_run 的參數抓 family 與 output
  fam=$(printf '%s' "$line" | grep -oE 'cx_run\.sh [a-z]+' | awk '{print $2}')
  out=$(printf '%s' "$line" | grep -oE 'handoffs/[A-Za-z0-9._/-]+\.md' | tail -1)
  [ -z "$fam" ] && continue
  printf '│ 🟢 %-9s 執行中  已跑 %-9s pid=%s\n' "$fam" "$et" "$pid"
  [ -n "$out" ] && printf '│      → 產出將寫入 %s\n' "$out"
  found=1
done < <(ps -eo pid,etime,args | grep 'cx_run\.sh' | grep -v grep)
[ "$found" -eq 0 ] && echo "│ ⚪ 目前沒有委員 CLI 在執行"

# ── 2. 我在等的背景監看 ──────────────────────────────────────
w=$(ps -eo pid,etime,args | grep 'wait_for_dispatch\.sh' | grep -v grep || true)
if [ -n "$w" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    et=$(printf '%s' "$line" | awk '{print $2}')
    tgt=$(printf '%s' "$line" | grep -oE 'handoffs/[A-Za-z0-9._/-]+\.md' | tr '\n' ' ')
    printf '│ ⏳ 死亡偵測器監看中(%s)  目標: %s\n' "$et" "$tgt"
  done < <(printf '%s\n' "$w")
else
  echo "│ ⚪ 無背景監看(若上方有 CLI 在跑卻無監看,代表我會漏接完成通知)"
end_marker=1
fi

# ── 3. 本 epic 戳記進度 ──────────────────────────────────────
SY=handoffs/reconcile/p16-b1-ruling/synth.md
if [ -f "$SY" ]; then
  n=$(grep -c '^RECONCILE-STAMP' "$SY" 2>/dev/null || echo 0)
  who=$(grep '^RECONCILE-STAMP' "$SY" 2>/dev/null | awk '{print $2}' | tr '\n' ' ')
  miss=""
  for f in codex composer grok; do
    printf '%s' "$who" | grep -q "$f" || miss="${miss}${f} "
  done
  printf '│ 🖋 戳記 %s/3  已簽: %s\n' "$n" "${who:-無}"
  [ -n "$miss" ] && printf '│      尚缺: %s\n' "$miss"
fi

echo "└──────────────────────────────────────────────────────────"
