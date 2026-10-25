#!/usr/bin/env bash
# self_verify_check.sh — 自我查證提問（使用者 2026-10-23：「你可以自己掛個hook，每次回答或產出要給使用者或委員時候，
# 掛一個問自己這些回答已經查證過了嗎？ 你自己做小功能，不用給委員審查這些流程」）。
#
# 兩種掛法（同一腳本）：
#   Stop（無參數）：最後一則 assistant 有文字 ⇒ 一律 exit 2，把自問題目回灌 Claude（使用者 2026-10-23 再定：
#     「是泛指所有產出和回答使用者跟委員」，不限含數字／原因／比較者）；payload 之 stop_hook_active 為真（本則已因
#     Stop hook 續寫過）或文字含「（自查：已查證）」⇒ 放行（每則回覆只問一次，不循環）。
#   PostToolUse（參數 brief）：剛以 Edit／Write 寫入給委員或使用者之產出——handoffs/*BRIEF*.md、
#     handoffs/reconcile/*/synth.md、白話說明/*.md、scripts/fact_keys.json（HANDOFF 來源）、handoffs/javis/to_javis/
#     ⇒ exit 2，回灌同一自問（檔已寫入，不擋寫；Claude 依題目自查後必要時再改）。
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
    "  ① 每一句陳述（事實、現況、紀錄、原因、診斷、比較、預估、引用、「已完成／已通過／已記錄」等宣稱，不限有無數字），"
    "本輪是否用工具實查過程式碼、資料、收據、紀錄或實跑輸出？憑記憶或先前印象者一律視為未查證。\n"
    "  ② 未查證者：立刻去查並更正，或改寫成「推測，未查證」，不得用肯定句。\n"
    "  ③ 引用之數字、檔:行、提交雜湊、測試計數是否與本輪實查輸出逐字相符？\n"
    # 使用者 2026-10-25：「我講的都是要這量化主線通用的，你能用hook提醒自己嗎？和要委員提醒你」
    "  【使用者原則】引用使用者只用「」放逐字原話並可指出處，自己的歸納標「我的判斷」；使用者之裁定與原則通用整條"
    "量化主線（非只限當時那票）；做法照主流軟體業界與量化金融之模式、不摳細節（使用者 2026-10-14），量化金融本即從嚴處"
    "（look-ahead／PIT、資料正確、回測與 IC 統計、真實資料驗證）照業界從嚴——本則有無違反？\n"
)

# 使用者 2026-10-25「你自己再記錄你跟委員會很多輪的原因是什麼，然後看能否修正Hook反問內容和跟委員的反問提醒來優化」：
# NUMVIEW 155 輪 321 條 P0／P1 之歸因（docs/SCAR_LEDGER.md 同日條）——主委自建驗證機制之破口、規格錯／殘留、
# 修一漏同類各占大宗，產品碼真缺陷約 5%；舊自問只對準「未查證」。下列三問對準其餘三類。
DESIGN = (
    "  【機制】本產出是否新增或擴充測試／治理機制（驗證器、快取、登記表、閘、豁免）？業界常規需要它嗎？不建會少驗哪條"
    "量化正確性路徑？答不出 ⇒ 不建，改用一般測試。\n"
    "  【修補】處置 finding 時是否已 grep 同類全部實例一次修完（範圍與結果寫入收斂檔），而非只修反例那一處？\n"
)
SPEC_Q = "  【規格】本段寫的是行為與驗收（該寫）還是測試實作細節（不寫）？改一處是否已全文 grep 舊敘述並同步？\n"

if mode == "brief":
    path = str(((d.get("tool_input") or {}).get("file_path")) or "")
    if (re.search(r"handoffs/[^/]*BRIEF[^/]*\.md$", path) or re.search(r"handoffs/reconcile/[^/]+/synth\.md$", path)
            or re.search(r"白話說明/[^/]+\.md$", path) or path.endswith("scripts/fact_keys.json")
            or re.search(r"handoffs/javis/to_javis/", path) or re.search(r"docs/[^/]*_SPEC\.md$", path)):
        sys.stderr.write(QUESTION.format(target=f"給委員之產出 {path} ") +
                         "  ④ fact-verified 行與收斂檔之每條結論是否附同輪實跑或檔:行證據？fact-verified 須逐字貼本輪命令與輸出"
                         "（不改寫、不摘要）；查不到者標「推測，未查證」。\n" + DESIGN +
                         (SPEC_Q if path.endswith("_SPEC.md") else ""))
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
if not last_text or not last_text.strip() or "（自查：已查證）" in last_text:
    raise SystemExit(0)
sys.stderr.write(QUESTION.format(target="本則回覆") +
                 "全部已查證 ⇒ 只補一行「（自查：已查證）」；有更正 ⇒ 直接寫更正內容（含該行）。\n")
raise SystemExit(2)
PY
