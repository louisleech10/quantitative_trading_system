"""NOCAP Task 0.2b：寫碼當下擋新增之時間上限（PreToolUse Edit｜Write｜MultiEdit｜Bash）。

使用者 2026-10-27：「時間上限的問題要根本解決……在這專案中不準再次發生」「你能確保在此專案每次都會用到嗎? 不然你可能
自己手動加上時間限制，或根本不用做好的共用監看?」。

- Edit／Write／MultiEdit：以寫入後之完整檔內容跑 `scripts/timeout_scan.py` 之同一掃描器（AST 取所在函式、被呼叫者、逾時
  字面值），只看**新增**之行（多重集合差）；命中而不在 `scripts/timeout_registry.json` 白名單（精確綁定：Python 呼叫型＝
  path＋function＋callee＋literal，其餘＝path＋整行；whole_file 只准守衛、掃描器本身與其測試）⇒ rc 2 擋下。
- Bash：以重導向（`>`／`>>`）、`tee`、`sed -i`、`perl -i` 寫入受管程式檔（`.py`／`.sh`）⇒ rc 2，要求改用 Edit（CLAUDE.md
  「改檔一律用 Edit」）；其餘寫檔方式（腳本自寫檔、git apply、他工具）由 pre-commit 之 `timeout_scan.py --staged` 攔下。
- 登記檔之 class 只准 B／C／D；含 A、未知類別、缺理由或缺綁定 ⇒ 登記檔無效、一律擋（fail-closed）。stdin 讀不到或非 JSON ⇒ 擋。

用法：`python3 scripts/timeout_write_guard.py`（stdin＝PreToolUse payload；rc 0 放行／2 擋）。
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[1]
PATTERNS = REPO / "scripts" / "timeout_patterns.json"
REGISTRY = REPO / "scripts" / "timeout_registry.json"
ALLOWED_CLASSES = {"B", "C", "D"}
#: whole_file（整檔放行）只准守衛、掃描器本身與其測試
WHOLE_FILE_OK = {"scripts/timeout_write_guard.py", "tests/governance/test_timeout_write_guard.py",
                 "scripts/timeout_scan.py"}
#: Bash 寫入受管程式檔之目標副檔名
CODE_SUFFIXES = (".py", ".sh")
_HEREDOC = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?")


def _scanner() -> Any:
    spec = importlib.util.spec_from_file_location("timeout_scan_for_guard", REPO / "scripts" / "timeout_scan.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def load_patterns(path: Path = PATTERNS) -> Tuple[Tuple[str, ...], List[Tuple[str, "re.Pattern[str]"]]]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    return tuple(spec["suffixes"]), [(p["id"], re.compile(p["regex"])) for p in spec["patterns"]]


def load_registry(path: Path = REGISTRY) -> List[Dict[str, Any]]:
    """登記檔；任一列 class 不屬 B／C／D、缺理由、缺綁定（whole_file／function＋callee＋literal／line 恰一種）、或
    whole_file 而非守衛／掃描器本身 ⇒ ValueError（整份無效）。"""
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    for e in entries:
        if e.get("class") not in ALLOWED_CLASSES:
            raise ValueError(f"登記檔列 class={e.get('class')!r} 不允許（只准 B／C／D；長運算之時間上限＝A 類不可登記）：{e}")
        if not str(e.get("reason") or "").strip() or not e.get("path"):
            raise ValueError(f"登記檔列缺 path 或理由：{e}")
        kinds = [bool(e.get("whole_file")), all(k in e for k in ("function", "callee", "literal")), "line" in e]
        if sum(kinds) != 1:
            raise ValueError(f"登記檔列須恰一種綁定（whole_file／function＋callee＋literal／line）：{e}")
        if e.get("whole_file") and e.get("path") not in WHOLE_FILE_OK:
            raise ValueError(f"登記檔列 whole_file（整檔放行）只准守衛、掃描器本身與其測試：{e}")
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


def _current(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace") if Path(path).is_file() else ""
    except OSError:
        return ""


def edits_of(tool: str, tool_input: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    """(path, 寫入前完整內容, 寫入後完整內容) 清單；Edit 之 old_string 找不到時以 new_string 片段代之（保守掃描）。"""
    path = str(tool_input.get("file_path") or "")
    before = _current(path)
    if tool == "Write":
        return [(path, before, str(tool_input.get("content") or ""))]
    if tool == "Edit":
        steps = [(str(tool_input.get("old_string") or ""), str(tool_input.get("new_string") or ""),
                  bool(tool_input.get("replace_all")))]
    elif tool == "MultiEdit":
        steps = [(str(e.get("old_string") or ""), str(e.get("new_string") or ""), bool(e.get("replace_all")))
                 for e in tool_input.get("edits") or []]
    else:
        return []
    after = before
    for old, new, every in steps:
        if old and old in after:
            after = after.replace(old, new) if every else after.replace(old, new, 1)
        elif not old:
            after = new + after
        else:
            return [(path, old, new)]  # 無從套用 ⇒ 只掃片段
    return [(path, before, after)]


def violations(edits: Iterable[Tuple[str, str, str]], registry: Sequence[Dict[str, Any]],
               scan: Optional[Any] = None) -> List[str]:
    scan = scan or _scanner()
    out = []
    for path, before, after in edits:
        rel = rel_path(path)
        added: Dict[str, int] = {}
        for line in added_lines(before, after):
            added[line] = added.get(line, 0) + 1
        if not added:
            continue
        for hit in scan.scan_text(rel, after):
            if added.get(hit.text, 0) <= 0:
                continue
            entry = scan.registered(hit, registry)
            if entry is None or entry.get("class") == "A":
                out.append(f"{rel}: [{hit.pattern_id}] {hit.text.strip()[:160]}")
    return out


def _strip_heredocs(command: str) -> str:
    """去掉 heredoc 內文（`<<EOF` 至分隔行）：內文是資料（提交訊息等），不是被執行之命令。"""
    out, pending = [], []
    for line in command.split("\n"):
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue
        out.append(line)
        pending += _HEREDOC.findall(line)
    return "\n".join(out)


def bash_code_writes(command: str) -> List[str]:
    """依 shell 語法找寫入 .py／.sh 之命令：重導向（`>`／`>>`／`&>`）之目標、`tee` 之檔名參數、`sed -i`／`perl -i` 之
    檔名參數。引號內字串與 heredoc 內文不算（只看真正之命令與重導向）。引號不成對 ⇒ 不判（由 pre-commit 掃描兜底）。"""
    import shlex

    lex = shlex.shlex(_strip_heredocs(command), posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        tokens = list(lex)
    except ValueError:
        return []
    found: List[str] = []
    argv: List[str] = []

    def flush() -> None:
        if not argv:
            return
        prog = Path(argv[0]).name
        files = [a for a in argv[1:] if a.endswith(CODE_SUFFIXES)]
        if prog == "tee" and files:
            found.append(f"tee {' '.join(files)}")
        elif prog == "sed" and files and any(a == "-i" or a.startswith("-i") or a == "--in-place" or
                                            (a.startswith("-") and not a.startswith("--") and "i" in a[1:])
                                            for a in argv[1:]):
            found.append(f"sed -i {' '.join(files)}")
        elif prog == "perl" and files and any(a.startswith("-") and not a.startswith("--") and "i" in a[1:]
                                             for a in argv[1:]):
            found.append(f"perl -i {' '.join(files)}")
        argv.clear()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok and set(tok) <= set(";&|()<>\n"):
            if ">" in tok and i + 1 < len(tokens):
                target = tokens[i + 1]
                if target.endswith(CODE_SUFFIXES):
                    found.append(f"{tok} {target}")
                i += 2
                continue
            if "<" in tok:
                i += 2
                continue
            flush()
            i += 1
            continue
        argv.append(tok)
        i += 1
    flush()
    return found


def main(stdin: Optional[str] = None) -> int:
    raw = sys.stdin.read() if stdin is None else stdin
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print("timeout_write_guard: 讀不到 PreToolUse payload ⇒ 擋（寫入類 fail-closed）", file=sys.stderr)
        return 2
    tool = str(payload.get("tool_name") or "")
    tool_input = dict(payload.get("tool_input") or {})
    if tool == "Bash":
        writes = bash_code_writes(str(tool_input.get("command") or ""))
        if not writes:
            return 0
        print("🔴 timeout_write_guard（NOCAP Task 0.2b）：Bash 寫入程式檔（.py／.sh）不經寫碼閘——改用 Edit／Write 工具"
              "（CLAUDE.md「改檔一律用 Edit」）：", file=sys.stderr)
        for w in writes:
            print(f"  · {w}", file=sys.stderr)
        return 2
    if tool not in ("Edit", "Write", "MultiEdit"):
        return 0
    try:
        registry = load_registry()
        bad = violations(edits_of(tool, tool_input), registry)
    except (OSError, ValueError, KeyError, re.error) as exc:
        print(f"timeout_write_guard: 樣式或登記檔無效 ⇒ 擋：{exc}", file=sys.stderr)
        return 2
    if not bad:
        return 0
    print("🔴 timeout_write_guard（NOCAP）：新增之寫法會依時間停止或縮減運算，本專案禁止——", file=sys.stderr)
    for b in bad:
        print(f"  · {b}", file=sys.stderr)
    print("  長運算之卡死一律交共用監看（handoffs/run_receipts/numview_probes/_watchdog.py：無 log 亦無 CPU 進度才判卡死、"
          "終止前留現場）；不得自設時間上限。\n  若確屬等外部方（網路／API／委員 CLI／鎖）或短輔助命令之掛住保險，於 "
          "scripts/timeout_registry.json 登記 class B／C／D 並寫理由（A 類不可登記；Python 呼叫綁 function＋callee＋literal、"
          "其餘綁整行），同提交送審。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
