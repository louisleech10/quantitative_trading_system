"""NOCAP Task 0.2b：寫碼當下擋新增之時間上限（PreToolUse Edit｜Write｜MultiEdit）。

使用者 2026-10-27：「時間上限的問題要根本解決……在這專案中不準再次發生」「你能確保在此專案每次都會用到嗎? 不然你可能
自己手動加上時間限制，或根本不用做好的共用監看?」。

只掃本次**新增**之行（Edit：new_string 中不在 old_string 之行；Write：新內容中不在現有檔之行；MultiEdit 逐筆）；
檔名副檔名屬 `scripts/timeout_patterns.json` 之 suffixes 才管轄。新增行命中任一樣式而不在 `scripts/timeout_registry.json`
白名單（同 path 且行含 contains 子字串）⇒ rc 2 擋下。登記檔之 class 只准 B／C／D；含 A 或未知類別 ⇒ 登記檔無效、
一律擋（fail-closed）。stdin 讀不到或非 JSON ⇒ 擋（寫入類 fail-closed）。

用法：`python3 scripts/timeout_write_guard.py`（stdin＝PreToolUse payload；rc 0 放行／2 擋）。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
PATTERNS = REPO / "scripts" / "timeout_patterns.json"
REGISTRY = REPO / "scripts" / "timeout_registry.json"
ALLOWED_CLASSES = {"B", "C", "D"}
#: contains＝""（整檔放行）只准守衛本身與其測試
WHOLE_FILE_OK = {"scripts/timeout_write_guard.py", "tests/governance/test_timeout_write_guard.py"}


def load_patterns(path: Path = PATTERNS) -> Tuple[Tuple[str, ...], List[Tuple[str, "re.Pattern[str]"]]]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    return tuple(spec["suffixes"]), [(p["id"], re.compile(p["regex"])) for p in spec["patterns"]]


def load_registry(path: Path = REGISTRY) -> List[Dict[str, str]]:
    """登記檔；任一列 class 不屬 B／C／D、或 contains＝"" 而非守衛自身 ⇒ ValueError（整份無效）。"""
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    for e in entries:
        if e.get("class") not in ALLOWED_CLASSES:
            raise ValueError(f"登記檔列 class={e.get('class')!r} 不允許（只准 B／C／D；長運算之時間上限＝A 類不可登記）：{e}")
        if not str(e.get("reason") or "").strip():
            raise ValueError(f"登記檔列缺理由：{e}")
        if e.get("contains", None) == "" and e.get("path") not in WHOLE_FILE_OK:
            raise ValueError(f"登記檔列 contains 為空（整檔放行）只准守衛本身與其測試：{e}")
        if not isinstance(e.get("contains"), str) or not e.get("path"):
            raise ValueError(f"登記檔列缺 path／contains：{e}")
    return entries


def rel_path(file_path: str) -> str:
    p = Path(file_path)
    try:
        return str(p.resolve().relative_to(REPO.resolve()))
    except (ValueError, OSError):
        return str(p)


def added_lines(old: str, new: str) -> List[str]:
    """`new` 中不在 `old` 之行（多重集合差，保序）。"""
    remaining: Dict[str, int] = {}
    for line in old.splitlines():
        remaining[line] = remaining.get(line, 0) + 1
    out = []
    for line in new.splitlines():
        if remaining.get(line, 0) > 0:
            remaining[line] -= 1
        else:
            out.append(line)
    return out


def edits_of(tool: str, tool_input: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """(path, old, new) 清單。"""
    path = str(tool_input.get("file_path") or "")
    if tool == "Edit":
        return [(path, str(tool_input.get("old_string") or ""), str(tool_input.get("new_string") or ""))]
    if tool == "MultiEdit":
        return [(path, str(e.get("old_string") or ""), str(e.get("new_string") or ""))
                for e in tool_input.get("edits") or []]
    if tool == "Write":
        existing = ""
        try:
            existing = Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).is_file() else ""
        except OSError:
            existing = ""
        return [(path, existing, str(tool_input.get("content") or ""))]
    return []


def violations(edits: Iterable[Tuple[str, str, str]], suffixes: Sequence[str],
               patterns: Sequence[Tuple[str, "re.Pattern[str]"]], registry: Sequence[Dict[str, str]]) -> List[str]:
    out = []
    for path, old, new in edits:
        if not path.endswith(tuple(suffixes)):
            continue
        rel = rel_path(path)
        allowed = [e["contains"] for e in registry if e["path"] == rel]
        for line in added_lines(old, new):
            hits = [pid for pid, rx in patterns if rx.search(line)]
            if hits and not any(c == "" or c in line for c in allowed):
                out.append(f"{rel}: [{','.join(hits)}] {line.strip()[:160]}")
    return out


def main(stdin: Optional[str] = None) -> int:
    raw = sys.stdin.read() if stdin is None else stdin
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print("timeout_write_guard: 讀不到 PreToolUse payload ⇒ 擋（寫入類 fail-closed）", file=sys.stderr)
        return 2
    tool = str(payload.get("tool_name") or "")
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0
    try:
        suffixes, patterns = load_patterns()
        registry = load_registry()
    except (OSError, ValueError, KeyError, re.error) as exc:
        print(f"timeout_write_guard: 樣式或登記檔無效 ⇒ 擋：{exc}", file=sys.stderr)
        return 2
    bad = violations(edits_of(tool, dict(payload.get("tool_input") or {})), suffixes, patterns, registry)
    if not bad:
        return 0
    print("🔴 timeout_write_guard（NOCAP）：新增之寫法會依時間停止或縮減運算，本專案禁止——", file=sys.stderr)
    for b in bad:
        print(f"  · {b}", file=sys.stderr)
    print("  長運算之卡死一律交共用監看（handoffs/run_receipts/numview_probes/_watchdog.py：無 log 亦無 CPU 進度才判卡死、"
          "終止前留現場）；不得自設時間上限。\n  若確屬等外部方（網路／API／委員 CLI／鎖）或短輔助命令之掛住保險，於 "
          "scripts/timeout_registry.json 登記 class B／C／D 並寫理由（A 類不可登記），同提交送審。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
