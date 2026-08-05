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
from pathlib import Path

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

if last_has_tool:
    raise SystemExit(0)

# 可查的背景任務 handle。
# 2026-08-06 修：原正則 `\b[a-z][a-z0-9]{8}\b` 匹配**任何 9 字元小寫詞**，
#   與本檔開頭載明的「`b` + 8 位英數」不符 ⇒ 實作沒照自己的規格。
#   事故：回覆中的 `redesign2`（9 字元）被當成任務 ID，哨兵放行，
#   使用者等了 6 小時才發現主委其實停住了。
# 現行判準（兩層，皆機械可驗）：
#   ① 形狀須為 `b` + 8 位英數（照文件）
#   ② 該 ID 須**真的存在**於本 session 的 tasks 目錄（純形狀不夠——
#      任何以 b 開頭的 9 字元英文字仍可能誤命中）
# tasks 目錄無法定位時退回只驗 ①（仍嚴於舊版），並於 stderr 註明。
cands = re.findall(r"\bb[a-z0-9]{8}\b", last_text)

tasks_dir = None
try:
    p = Path(path)
    session_id = p.stem
    proj = p.parent.name
    for base in (Path("/private/tmp"), Path("/tmp")):
        for owner in base.glob("claude-*"):
            cand = owner / proj / session_id / "tasks"
            if cand.is_dir():
                tasks_dir = cand
                break
        if tasks_dir:
            break
except Exception:
    tasks_dir = None

if cands:
    if tasks_dir is None:
        sys.stderr.write(
            "[status_marker] 註：找不到 tasks 目錄，僅以 ID 形狀放行（未驗證任務是否真存在）\n"
        )
        raise SystemExit(0)
    for cid in cands:
        if (tasks_dir / f"{cid}.output").exists():
            raise SystemExit(0)
    sys.stderr.write(
        f"【狀態標記不誠實】文中的 {cands!r} 形狀像背景任務 ID，"
        f"但 {tasks_dir} 下找不到對應的 .output ⇒ 不是真的背景任務。\n"
    )
    raise SystemExit(2)

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
