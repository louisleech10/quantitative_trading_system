"""NOCAP Task 0.3：下指令當下擋——重型命令須背景執行且經共用監看（PreToolUse Bash）。

使用者 2026-10-27：「也不準跑完或沒動靜還要等我問你才去查」「你能確保在此專案每次都會用到嗎? 不然你可能自己手動加上
時間限制，或根本不用做好的共用監看?」。

判定（清單 `scripts/heavy_commands.json`）：命令依 shell 語法拆為簡單命令（`;`／`&&`／`||`／`|`／`&`／`(`／`)`／換行
分隔，去重導向、前置環境變數與 env／nohup／time 等前綴），只比對**執行位置**之命令——啟動器（python*／pytest／bash／sh／
zsh／source）及直接執行之 `.sh`；其所執行之 repo 內 `.sh` 檔內容（遞迴一層、參數代入）以同法拆解。`ls`／`grep`／`pgrep`／
`echo` 等之參數、腳本內註解與字串不算（2026-10-27 實測舊版逐字比對全文誤擋 `ls x.sh`、`pgrep 'pytest|…'`、
`bash scripts/template_check.sh`）。命中重型樣式 ⇒ 須 `tool_input.run_in_background` 為 true（行程結束必有完成通知）；
`wrapped` 類另須該命令經 `scripts/run_watched.py` 包裝；`self_watched` 類以原始碼機械對證其確實呼叫共用監看
`run_watched(`（否則視同未經監看）。引號不成對而無從拆解 ⇒ 退回全文比對（保守）。stdin 讀不到或非 JSON ⇒ 擋。

用法：`python3 scripts/heavy_run_guard.py`（stdin＝PreToolUse payload；rc 0 放行／2 擋）。
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
CATALOG = REPO / "scripts" / "heavy_commands.json"
WRAPPER = "scripts/run_watched.py"


_SEPARATORS = set(";&|()\n")
_SHELLS = {"bash", "sh", "zsh", "source", "."}
_PREFIXES = {"env", "nohup", "time", "exec", "command", "caffeinate", "nice"}
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
MAX_DEPTH = 5  # 執行之 .sh 遞迴展開之深度上限；逾限 ⇒ 擋（fail-closed，NOCAP Task 0.3 v3）
DEPTH_EXCEEDED = "<heavy_run_guard:depth-exceeded>"


def _simple_commands(text: str, comments: bool) -> Optional[List[List[str]]]:
    """依 shell 語法拆簡單命令（argv 串列）；重導向及其目標移除；`comments` 時以 `#` 起首之字詞至行尾為註解
    （不用 shlex 內建註解：其遇 `${x#y}` 會吞掉換行而把兩行併為一命令）；`case … in` 之分支樣式（`a|b)`）非命令。
    引號不成對 ⇒ None。"""
    lex = shlex.shlex(text, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    try:
        tokens = list(lex)
    except ValueError:
        return None
    commands: List[List[str]] = []
    cur: List[str] = []
    skip_next = False
    in_comment = False
    case_depth = 0
    in_pattern = False

    def flush(sep: str) -> None:
        nonlocal case_depth, in_pattern
        if cur and cur[0] == "case":
            case_depth += 1
            in_pattern = True
        elif cur and cur[0] == "esac":
            case_depth = max(0, case_depth - 1)
            in_pattern = False
        elif case_depth and in_pattern:
            if ")" in sep:
                in_pattern = False  # 樣式結束、其後為分支命令
        elif cur:
            commands.append(list(cur))
        if case_depth and ";;" in sep:
            in_pattern = True
        cur.clear()

    for tok in tokens:
        if in_comment:
            if "\n" not in tok:
                continue
            in_comment = False
        if skip_next:
            skip_next = False
            continue
        if comments and tok.startswith("#"):
            in_comment = True
            continue
        if tok and set(tok) <= _SEPARATORS | set("<>"):
            if "<" in tok or ">" in tok:
                skip_next = True  # 重導向之目標（檔名、`>&` 之 1）非命令
                continue
            flush(tok)
            continue
        cur.append(tok)
    flush("")
    return commands


def _strip_prefixes(argv: List[str]) -> List[str]:
    i = 0
    while i < len(argv) and _ASSIGN.match(argv[i]):
        i += 1
    while i < len(argv) and Path(argv[i]).name in _PREFIXES:
        i += 1
        while i < len(argv) and (argv[i].startswith("-") or _ASSIGN.match(argv[i])):
            i += 1
    return argv[i:]


def _script_body(tok: str, args: List[str]) -> Optional[str]:
    """repo 內 .sh 之內容，`"$@"`／`$@`／`$1`…`$9` 以實際參數代入；非 repo 內或讀不到 ⇒ None。"""
    path = Path(tok) if Path(tok).is_absolute() else REPO / tok
    try:
        if not (path.is_file() and REPO.resolve() in path.resolve().parents):
            return None
        body = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    joined = " ".join(shlex.quote(a) for a in args)
    body = body.replace('"$@"', joined).replace("$@", joined)
    for n in range(9, 0, -1):
        val = shlex.quote(args[n - 1]) if n <= len(args) else ""
        body = body.replace(f'"${n}"', val).replace(f"${{{n}}}", val).replace(f"${n}", val)
    return body


def executed(command: str, depth: int = 0, comments: bool = False) -> List[Tuple[str, bool]]:
    """執行位置之命令（以空白接回之 argv, 是否經共用監看包裝）。"""
    commands = _simple_commands(command, comments)
    if commands is None:
        return [(command, WRAPPER in command)]  # 無從拆解 ⇒ 全文比對（保守）
    out: List[Tuple[str, bool]] = []
    for raw in commands:
        out.extend(_analyze(_strip_prefixes(raw), depth, wrapped=False))
    return out


#: 動態啟動器之「帶值」選項（其後一個 token 為選項值、非內層命令）
_XARGS_VALUE_OPTS = {"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "-J", "-R", "-S"}
_PARALLEL_VALUE_OPTS = {"-j", "--jobs", "-S", "--sshlogin", "--joblog", "--results", "-I", "--colsep"}
_FIND_EXEC = {"-exec", "-execdir", "-ok", "-okdir"}


def _after_options(argv: List[str], value_opts: set) -> List[str]:
    i = 1
    while i < len(argv) and argv[i].startswith("-"):
        i += 2 if argv[i] in value_opts else 1
    return argv[i:]


#: 單次判定內已展開之腳本實體路徑——腳本互相呼叫時不重複展開（否則循環呼叫必觸深度上限）
_SEEN: set = set()


def _expand_script(script: str, args: List[str], depth: int, wrapped: bool) -> List[Tuple[str, bool]]:
    """執行之 repo 內 .sh：遞迴至不再出現新的 .sh；同一腳本＋參數只展開一次；逾深度上限 ⇒ 標記擋（fail-closed）。
    非 repo 內或讀不到之路徑（含未解析變數如 `${SCRIPT_DIR}/x.sh`）不計入深度。"""
    path = Path(script) if Path(script).is_absolute() else REPO / script
    try:
        if not (path.is_file() and REPO.resolve() in path.resolve().parents):
            return []
        key = str(path.resolve())  # 只依路徑：同一腳本以不同參數互相呼叫（gate.sh 等治理腳本鏈）亦只展開一次
    except OSError:
        return []
    if key in _SEEN:
        return []
    if depth >= MAX_DEPTH:
        return [(f"{DEPTH_EXCEEDED} {script}", wrapped)]
    _SEEN.add(key)
    body = _script_body(script, args)
    if body is None:
        return []
    return [(t, w or wrapped) for t, w in executed(body, depth + 1, comments=True)]


def _analyze(argv: List[str], depth: int, wrapped: bool) -> List[Tuple[str, bool]]:
    if not argv:
        return []
    prog = Path(argv[0]).name
    if argv[0].startswith("$") or "`" in argv[0]:  # 命令位置為未解析變數或命令替換 ⇒ argv 全文比對（保守）
        return [(" ".join(argv), wrapped)]
    if prog.startswith("python") and len(argv) > 1 and argv[1].endswith(WRAPPER):
        inner = argv[argv.index("--") + 1:] if "--" in argv else []
        return [(" ".join(argv), True)] + _analyze(_strip_prefixes(inner), depth, wrapped=True)
    if prog == "eval":  # eval 只看其組出之命令字串
        return executed(" ".join(argv[1:]), depth)
    if prog == "xargs":  # 內層命令遞迴判定（`ls | xargs grep x` 之內層為 grep ⇒ 放行）
        return _analyze(_strip_prefixes(_after_options(argv, _XARGS_VALUE_OPTS)), depth, wrapped)
    if prog == "parallel":
        inner = _after_options(argv, _PARALLEL_VALUE_OPTS)
        return _analyze(_strip_prefixes(inner[:inner.index(":::")] if ":::" in inner else inner), depth, wrapped)
    if prog == "find":
        out: List[Tuple[str, bool]] = []
        for i, tok in enumerate(argv):
            if tok in _FIND_EXEC:
                inner = []
                for t in argv[i + 1:]:
                    if t in (";", "+", "\\;"):
                        break
                    inner.append(t)
                out += _analyze(_strip_prefixes(inner), depth, wrapped)
        return out
    if prog in _SHELLS:
        rest = argv[1:]
        if "-c" in rest and rest.index("-c") + 1 < len(rest):  # 只分析內層字串（外層 argv 含其全文，比對會誤擋）
            return [(t, w or wrapped) for t, w in executed(rest[rest.index("-c") + 1], depth)]
        script = next((a for a in rest if not a.startswith("-")), None)
        out = [(" ".join(argv), wrapped)]
        if script and script.endswith(".sh"):
            out += _expand_script(script, rest[rest.index(script) + 1:], depth, wrapped)
        return out
    if prog.endswith(".sh"):
        return [(" ".join(argv), wrapped)] + _expand_script(argv[0], argv[1:], depth, wrapped)
    if prog.startswith("python") or prog in ("pytest", "py.test"):
        return [(" ".join(argv), wrapped)]
    return []  # 非啟動器（ls、grep、pgrep、echo、cat…）：其參數不是被執行之命令


def check(payload: Dict[str, Any], catalog: Dict[str, Any]) -> List[str]:
    tool_input = dict(payload.get("tool_input") or {})
    _SEEN.clear()
    runs = executed(str(tool_input.get("command") or ""))
    background = tool_input.get("run_in_background") is True
    problems: List[str] = []
    deep = sorted({text.split(" ", 1)[1] for text, w in runs
                   if text.startswith(DEPTH_EXCEEDED) and not (w and background)})
    if deep:
        problems.append(f"腳本間接執行逾 {MAX_DEPTH} 層（{', '.join(deep)}）⇒ 無從判定是否重型；"
                        f"改以 `venv/bin/python {WRAPPER} --log <路徑> -- <命令>` 背景執行")
    for kind in ("self_watched", "wrapped", "background_only"):
        for rule in catalog.get(kind) or []:
            hits = [w for text, w in runs if re.search(rule["regex"], text, re.M | re.S)]
            if not hits:
                continue
            if not background:
                problems.append(f"{rule['id']}：重型命令須以背景執行（run_in_background＝true），結束時才有完成通知")
            if kind == "wrapped" and not all(hits):
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
