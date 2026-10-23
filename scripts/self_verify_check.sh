#!/usr/bin/env bash
# self_verify_check.sh — 自我查證提問（使用者 2026-10-23：「你可以自己掛個hook，每次回答或產出要給使用者或委員時候，
# 掛一個問自己這些回答已經查證過了嗎？ 你自己做小功能，不用給委員審查這些流程」）。
#
# 兩種掛法（同一腳本）：
#   Stop（無參數）：最後一則 assistant 文字含數字或原因／比較／預估類說法 ⇒ exit 2，把自問題目回灌 Claude；
#     payload 之 stop_hook_active 為真（本則已因 Stop hook 續寫過）⇒ 放行（每則回覆只問一次，不循環）。
#   PostToolUse（參數 brief）：剛以 Edit／Write 寫入 handoffs/*BRIEF*.md 或 handoffs/reconcile/*/synth.md
#     （給委員之產出）⇒ exit 2，回灌同一自問（檔已寫入，不擋寫；Claude 依題目自查後必要時再改）。
# 誠實邊界：本腳本不判斷是否已查證（機器無從得知），只保證每次產出前被問到。
set -u

mode="${1:-stop}"
payload="$(python3 -c 'import signal,sys
signal.alarm(5)
sys.stdout.write(sys.stdin.read())' 2>/dev/null || true)"

python3 - "${mode}" "${payload}" <<'PY'
import json, re, sys

mode, raw = sys.argv[1], sys.argv[2]
try:
    d = json.loads(raw) if raw else {}
except Exception:
    raise SystemExit(0)

QUESTION = (
    "【自我查證】{target}送出前逐句自問：\n"
    "  ① 每個原因、診斷、比較（快／慢／較好）、預估（時間、規模、數量）、「已完成／已通過」之宣稱，"
    "本輪是否用工具實查過程式碼、資料、收據或實跑輸出？\n"
    "  ② 未查證者：立刻去查並更正，或改寫成「推測，未查證」，不得用肯定句。\n"
    "  ③ 引用之數字、檔:行、提交雜湊、測試計數是否與本輪實查輸出逐字相符？\n"
)

if mode == "brief":
    path = str(((d.get("tool_input") or {}).get("file_path")) or "")
    if re.search(r"handoffs/[^/]*BRIEF[^/]*\.md$", path) or re.search(r"handoffs/reconcile/[^/]+/synth\.md$", path):
        sys.stderr.write(QUESTION.format(target=f"給委員之產出 {path} ") +
                         "  ④ fact-verified 行與收斂檔之每條結論是否附同輪實跑或檔:行證據？查不到者標「推測，未查證」。\n")
        raise SystemExit(2)
    raise SystemExit(0)

if d.get("stop_hook_active"):
    raise SystemExit(0)
tp = d.get("transcript_path") or ""
if not tp:
    raise SystemExit(0)
last_text = None
try:
    with open(tp, encoding="utf-8") as fh:
        for line in fh:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msg = rec.get("message") or {}
            if rec.get("type") != "assistant" or not isinstance(msg.get("content"), list):
                continue
            texts = [b.get("text") or "" for b in msg["content"] if isinstance(b, dict) and b.get("type") == "text"]
            if texts:
                last_text = "\n".join(texts)
except OSError:
    raise SystemExit(0)
if not last_text or "（自查：已查證）" in last_text:
    raise SystemExit(0)
CLAIM = re.compile(r"\d|因為|原因|導致|所以|比較|較快|較慢|最快|最慢|更快|更好|預估|估計|大約|約 |應該|可能是|成立|已完成|已通過|通過|全綠")
if not CLAIM.search(last_text):
    raise SystemExit(0)
sys.stderr.write(QUESTION.format(target="本則回覆") +
                 "全部已查證 ⇒ 只補一行「（自查：已查證）」；有更正 ⇒ 直接寫更正內容（含該行）。\n")
raise SystemExit(2)
PY
