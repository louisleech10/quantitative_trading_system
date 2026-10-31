#!/usr/bin/env python3
"""temp_output_guard — 要再用之檔不得落在系統暫存（PreToolUse：Bash／Edit／Write／MultiEdit）。

起因（2026-10-31）：macOS `com.apple.bsd.dirhelper` 每日 03:35 清除系統暫存中逾 3 日之檔
（`/System/Library/LaunchDaemons/com.apple.bsd.dirhelper.plist` `CLEAN_FILES_OLDER_THAN_DAYS`＝3），`/private/tmp` 開機清空；
ICPERF C 格交接 h5 與 FFPROD 6 次保留生成放 `$TMPDIR` 遭清除，凍結白跑兩次。規則：之後還會被讀之檔一律放 repo 內
（程式生成之資料放 `data_cache/`、重複使用之工具放 `scripts/`）；系統暫存只放同一次執行內用完即刪之檔。

Bash（命令列）：
  1. 輸出類參數（`OUTPUT_OPTS`，`--opt 值` 或 `--opt=值`）之值在系統暫存 ⇒ 擋。log（`--log`、`> 檔`）不在此列：log 遺失不需重跑。
  2. 以直譯器（python／bash／sh／zsh）執行位於系統暫存之腳本（.py／.sh）⇒ 擋（重複使用之工具須進 `scripts/`）。
Edit／Write／MultiEdit（repo 內 scripts/、momentum/、api/、tests/ 之 .py／.sh；只查新寫入之文字）：
  3. `.py`：`gettempdir(`、讀 `TMPDIR`（`environ.get("TMPDIR"`、`getenv("TMPDIR"`）、字串字面值 "/tmp"／"/private/tmp"／
     "/var/folders"、`mkdtemp(`／`mkstemp(` 而同行無 `dir=` ⇒ 擋。用完即刪之暫存改用 `tempfile.TemporaryDirectory`／
     `NamedTemporaryFile`（離開即刪）；要保留之輸出給 repo 內路徑。
  4. `.sh`：字面路徑 `/tmp/`、`/private/tmp`、`/var/folders` ⇒ 擋（`mktemp` 配 `trap ... rm` 不擋）。
用法：stdin＝PreToolUse payload；rc 0 放行／2 擋（訊息印 stderr）。stdin 非 JSON ⇒ 放行（非本檢查職責，交其他 hook）。
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Iterable, List, Optional

REPO = Path(__file__).resolve().parents[1]
TEMP_PREFIXES = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")
OUTPUT_OPTS = ("--out", "--out-dir", "--out-root", "--output", "--output-dir", "--work-root", "--work", "--work-dir",
               "--receipt", "--tmp-root", "--golden", "--capture-inputs", "--dest", "--target-dir")
INTERPRETERS = re.compile(r"(^|/)(python[0-9.]*|bash|sh|zsh)$")
CODE_DIRS = ("scripts", "momentum", "api", "tests")
#: 本檢查自身與其測試須寫出被禁樣式
EXEMPT = ("scripts/temp_output_guard.py", "tests/governance/test_temp_output_guard.py")
PY_RULES = (
    (re.compile(r"gettempdir\s*\("), "tempfile.gettempdir()"),
    (re.compile(r"""(environ\.get|getenv)\(\s*["']TMPDIR["']"""), "讀 TMPDIR"),
    (re.compile(r"""["'](/tmp|/private/tmp|/var/folders)(/|["'])"""), "寫死系統暫存路徑"),
)
MK_RE = re.compile(r"\bmk[ds]temp\s*\(")
SH_RE = re.compile(r"(?<![\w.])(/tmp/|/private/tmp|/var/folders)")


def _temp_roots() -> List[str]:
    roots = list(TEMP_PREFIXES)
    t = os.environ.get("TMPDIR")
    if t:
        roots.append(os.path.realpath(t).rstrip("/") + "/")
    return roots


def in_temp(value: str) -> bool:
    """`value`（展開 ~ 與 $TMPDIR 後）是否為系統暫存下之路徑。"""
    v = os.path.expandvars(os.path.expanduser(value.strip().strip("'\"")))
    if not v.startswith("/"):
        return False
    real = os.path.realpath(v)
    return any(x.startswith(r) or (x + "/") == r for x in (v, real) for r in _temp_roots())


def _tokens(command: str) -> List[str]:
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        return command.split()


def bash_problems(command: str) -> List[str]:
    toks = _tokens(command)
    out: List[str] = []
    for i, tok in enumerate(toks):
        opt, eq, val = tok.partition("=")
        if opt in OUTPUT_OPTS:
            value = val if eq else (toks[i + 1] if i + 1 < len(toks) else "")
            if value and in_temp(value):
                out.append(f"輸出參數 {opt} 指向系統暫存：{value}")
        if tok.endswith((".py", ".sh")) and in_temp(tok) and i > 0 and INTERPRETERS.search(toks[i - 1]):
            out.append(f"執行系統暫存中之腳本：{tok}（重複使用之工具須放 scripts/）")
    return out


def _new_texts(tool: str, ti: dict) -> Iterable[str]:
    if tool == "Write":
        yield str(ti.get("content") or "")
    elif tool == "Edit":
        yield str(ti.get("new_string") or "")
    elif tool == "MultiEdit":
        for e in ti.get("edits") or []:
            yield str((e or {}).get("new_string") or "")


def code_problems(path: str, texts: Iterable[str]) -> List[str]:
    try:
        rel = Path(os.path.realpath(path)).relative_to(REPO).as_posix()
    except ValueError:
        return []
    if rel in EXEMPT or rel.split("/", 1)[0] not in CODE_DIRS or not rel.endswith((".py", ".sh")):
        return []
    out: List[str] = []
    for text in texts:
        for n, line in enumerate(text.splitlines(), 1):
            if rel.endswith(".py"):
                out += [f"{rel}（新文字第 {n} 行）{name}：{line.strip()[:120]}" for rx, name in PY_RULES if rx.search(line)]
                if MK_RE.search(line) and "dir=" not in line:
                    out.append(f"{rel}（新文字第 {n} 行）mkdtemp／mkstemp 未給 dir=（不自刪）：{line.strip()[:120]}")
            elif SH_RE.search(line):
                out.append(f"{rel}（新文字第 {n} 行）寫死系統暫存路徑：{line.strip()[:120]}")
    return out


def check(payload: dict) -> List[str]:
    tool = str(payload.get("tool_name") or "")
    ti = payload.get("tool_input") or {}
    if tool == "Bash":
        return bash_problems(str(ti.get("command") or ""))
    if tool in ("Edit", "Write", "MultiEdit"):
        return code_problems(str(ti.get("file_path") or ""), _new_texts(tool, ti))
    return []


def main(stdin: Optional[str] = None) -> int:
    raw = sys.stdin.read() if stdin is None else stdin
    try:
        payload = json.loads(raw)
    except ValueError:
        return 0
    problems = check(payload if isinstance(payload, dict) else {})
    if not problems:
        return 0
    print("🔴 temp_output_guard：要再用之檔不得落在系統暫存（macOS 會清除；/private/tmp 開機清空）——\n"
          + "\n".join(f"  · {p}" for p in problems)
          + "\n  ⇒ 程式生成之資料放 data_cache/、重複使用之工具放 scripts/；用完即刪之暫存用 "
            "tempfile.TemporaryDirectory／NamedTemporaryFile。", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
