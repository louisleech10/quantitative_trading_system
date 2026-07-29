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
  # 用 Bash run_in_background:true 直接跑 cx_run.sh 時,harness 本身即追蹤該程序,
  # 完成/死亡都會通知,**不需要**額外監看。只有舊的 nohup+& 孤兒式啟動才需要。
  # (2026-07-29:nohup 已被 settings.json deny 封死,故正常情況這裡不需要監看)
  echo "│ ℹ️ 無額外監看 — 若上方 CLI 是用 run_in_background 啟動,harness 會自動通知(正常)"
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

# ── 衛生：呆滯程序 + repo 內 probe 殘留（使用者 2026-07-29 要求維持乾淨）──
_stale=0
while IFS= read -r l; do
  [ -z "$l" ] && continue
  et=$(printf '%s' "$l" | awk '{print $2}')
  s=$(printf '%s' "$et" | awk -F'[-:]' '{if(NF==4)print ($1*86400)+($2*3600)+($3*60)+$4; else if(NF==3)print ($1*3600)+($2*60)+$3; else print ($1*60)+$2}')
  [ "$s" -gt 1800 ] && _stale=$((_stale+1))
done < <(ps -eo pid,etime,args | grep -iE 'cx_run\.sh|committee_run\.sh|cursor-agent|/grok |codex exec' | grep -v grep)
_probes=$(ls -d handoffs/_probe_* handoffs/_narrowprobe_* 2>/dev/null | grep -c . || true)
if [ "${_stale}" -gt 0 ] || [ "${_probes:-0}" -gt 0 ]; then
  printf '│ 🧹 衛生：呆滯程序 %s 個、probe 殘留 %s 個 → bash scripts/cleanup_stale_dispatch.sh --kill\n' \
         "${_stale}" "${_probes:-0}"
fi

echo "└──────────────────────────────────────────────────────────"
