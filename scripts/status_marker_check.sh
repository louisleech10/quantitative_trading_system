#!/usr/bin/env bash
# status_marker_check.sh — Stop hook：機械檢查回覆結尾的【進行中】/【停住】標記是否誠實。
#
# 病根（本 session 使用者糾正 3 次以上）：Claude 把【進行中】當結尾裝飾寫，
#   實際上該則回覆沒有任何動作 ⇒ 使用者無從判斷該不該回話。
#   歷次修法都是「我下次會注意」＝紀律，紀律必然失效——
#   使用者定死第 3 條：**工具必須自帶強制機制，不准靠紀律和記憶**。
#
# 判準（可機械驗證，無模糊空間）：
#   最後一則 assistant 訊息若含「【進行中】」，則該訊息必須滿足其一：
#     (a) 該訊息含 tool_use（真的在做事），或
#     (b) 文中出現可查的背景任務 handle（`b` + 8 位英數，如 b4cch08b4）
#   兩者皆無 → exit 2，訊息回灌 Claude context 要求改為【停住】。
#
# 誠實邊界：只驗「宣稱有動作時是否真有動作」，不驗「該不該停」。
#   寫【停住】一律放行（保守方向不擋）。
set -u

payload="$(cat)"
tp="$(printf '%s' "${payload}" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(""); raise SystemExit(0)
print(d.get("transcript_path") or "")
' 2>/dev/null || true)"

[ -n "${tp}" ] || exit 0
[ -f "${tp}" ] || exit 0

python3 - "${tp}" <<'PY'
import json, re, sys

path = sys.argv[1]
last_text, last_has_tool = None, False
try:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            msg = rec.get("message") or {}
            if rec.get("type") != "assistant" or msg.get("role") != "assistant":
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            texts, has_tool = [], False
            for blk in content:
                if not isinstance(blk, dict):
                    continue
                if blk.get("type") == "text":
                    texts.append(blk.get("text") or "")
                elif blk.get("type") == "tool_use":
                    has_tool = True
            if texts or has_tool:
                last_text, last_has_tool = "\n".join(texts), has_tool
except OSError:
    raise SystemExit(0)

if not last_text or "【進行中】" not in last_text:
    raise SystemExit(0)

# 可查的背景任務 handle（Bash run_in_background 產生的 ID 形狀）
if last_has_tool or re.search(r"\b[a-z][a-z0-9]{8}\b", last_text):
    raise SystemExit(0)

sys.stderr.write(
    "【狀態標記不誠實】本則回覆寫了「【進行中】」，但既沒有工具呼叫，"
    "也沒有給出可查的背景任務 handle。\n"
    "  規則（使用者定死，機械強制）：寫【進行中】必須同時滿足其一——\n"
    "    (a) 同一則回覆有實際工具呼叫；或 (b) 文中附上背景任務 ID 供使用者查核。\n"
    "  兩者皆無時一律寫【停住】。請立即改正這則回覆的結尾標記，"
    "或現在就發出你宣稱要做的那個動作。\n"
)
raise SystemExit(2)
PY
