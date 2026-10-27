"""NOCAP Task 0.3：下指令當下擋——重型命令須背景執行且經共用監看（PreToolUse Bash）。

使用者 2026-10-27：「也不準跑完或沒動靜還要等我問你才去查」「你能確保在此專案每次都會用到嗎? 不然你可能自己手動加上
時間限制，或根本不用做好的共用監看?」。

判定（清單 `scripts/heavy_commands.json`）：命令字串＋其所呼叫之 repo 內 `.sh` 檔內容（遞迴一層）命中重型樣式 ⇒
須 `tool_input.run_in_background` 為 true（行程結束必有完成通知）；`wrapped` 類另須經 `scripts/run_watched.py`；
`self_watched` 類以原始碼機械對證其確實呼叫共用監看 `run_watched(`（否則視同未經監看）。stdin 讀不到或非 JSON ⇒ 擋。

用法：`python3 scripts/heavy_run_guard.py`（stdin＝PreToolUse payload；rc 0 放行／2 擋）。
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "scripts" / "heavy_commands.json"
WRAPPER = "scripts/run_watched.py"


def expand(command: str) -> str:
    """命令字串＋其中引用之 repo 內 .sh 檔內容（遞迴一層）；檔內 `"$@"`／`$@`／`$1`…`$9` 以實際傳入之參數代入
    （否則經輔助腳本轉呼叫之重型命令無從比對）。"""
    parts = [command]
    try:
        tokens = shlex.split(command, comments=False, posix=True)
    except ValueError:
        tokens = command.split()
    for i, tok in enumerate(tokens):
        if not tok.endswith(".sh"):
            continue
        path = Path(tok) if Path(tok).is_absolute() else REPO / tok
        try:
            if not (path.is_file() and REPO.resolve() in path.resolve().parents):
                continue
            body = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        args = []
        for a in tokens[i + 1:]:
            if a in (";", "&&", "||", "|", ">", "2>&1"):
                break
            args.append(a)
        joined = " ".join(args)
        body = body.replace('"$@"', joined).replace("$@", joined)
        for n in range(9, 0, -1):
            val = args[n - 1] if n <= len(args) else ""
            body = body.replace(f'"${n}"', val).replace(f"${{{n}}}", val).replace(f"${n}", val)
        parts.append(body)
    return "\n".join(parts)


def check(payload: Dict[str, Any], catalog: Dict[str, Any]) -> List[str]:
    tool_input = dict(payload.get("tool_input") or {})
    text = expand(str(tool_input.get("command") or ""))
    background = tool_input.get("run_in_background") is True
    problems: List[str] = []
    for kind in ("self_watched", "wrapped", "background_only"):
        for rule in catalog.get(kind) or []:
            if not re.search(rule["regex"], text, re.M | re.S):
                continue
            if not background:
                problems.append(f"{rule['id']}：重型命令須以背景執行（run_in_background＝true），結束時才有完成通知")
            if kind == "wrapped" and WRAPPER not in text:
                problems.append(f"{rule['id']}：須經共用監看包裝 `venv/bin/python {WRAPPER} --log <路徑> -- <命令>`")
            if kind == "self_watched" and not calls_run_watched(REPO / rule["source"]):
                problems.append(f"{rule['id']}：{rule['source']} 未呼叫共用監看 run_watched( ⇒ 改經 {WRAPPER} 包裝")
    return problems


def calls_run_watched(path: Path) -> bool:
    """原始碼確有 `<任意>.run_watched(...)` 或 `run_watched(...)` 之呼叫（AST；字串、註解中出現不算）。"""
    import ast

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if (isinstance(f, ast.Attribute) and f.attr == "run_watched") or (isinstance(f, ast.Name) and f.id == "run_watched"):
                return True
    return False


def main(stdin: Optional[str] = None) -> int:
    raw = sys.stdin.read() if stdin is None else stdin
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print("heavy_run_guard: 讀不到 PreToolUse payload ⇒ 擋（重型樣式無從判定）", file=sys.stderr)
        return 2
    if str(payload.get("tool_name") or "") != "Bash":
        return 0
    try:
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"heavy_run_guard: 重型命令清單無效 ⇒ 擋：{exc}", file=sys.stderr)
        return 2
    problems = check(payload, catalog)
    if not problems:
        return 0
    print("🔴 heavy_run_guard（NOCAP）：重型命令須經共用監看並背景執行——", file=sys.stderr)
    for p in problems:
        print(f"  · {p}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
