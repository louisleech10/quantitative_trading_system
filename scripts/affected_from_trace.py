"""依讀檔追蹤（`scripts/readtrace_plugin.py` 之 JSONL）與本批改動檔，算受影響 nodeid（TEST_SELECTION §5 過渡期）。

判定（任一成立 ⇒ 受影響，附理由）：
- `test-file:<檔>`：該 nodeid 所在之測試檔本身即改動檔；
- `read:<檔>`：該 nodeid 執行期間讀取之 repo 檔含改動檔；
- `cached-read:<檔>←<讀者>`／`cached-<子行程理由>←<讀者>`：該 nodeid 執行期間呼叫到之「讀者」（曾讀檔／啟動子行程之
  專案函式，含 lru_cache 命中；紀錄之 `calls`）讀過改動檔或其子行程命中——快取使後續呼叫者自身無讀檔；讀者表＝各紀錄
  `reader_*` 與收集期讀者表行（`{"readers": ...}`）之聯集；
- 紀錄有 `executed_files`（本測試實際執行到之 repo .py，外掛 profile 所記）且有模組 import 期讀檔表（`{"mod_own"}` 行）
  者，import 期依賴改用執行判定：
  - `executed:<檔>`：執行到之 .py 即改動檔；
  - `import-read:<檔>`／`import-proc-*`：測試模組、所屬 conftest／`__init__.py` 本身 import 期（及收集期 hook）之讀檔
    或子行程（`import_direct_*`）；
  - 起點＝執行到之模組 ∪ 本測試（任一執行緒）存取其屬性之模組（`accessed_modules`，外掛之模組類別動態記錄，涵蓋
    `from M import X`、`getattr`、`import *`、區域別名），沿模組 import 期存取邊（`{"mod_access"}` 行：匯入端 →
    被存取其資料／類別之模組，追再匯出鏈）求閉包；閉包內模組原始碼即改動檔 ⇒ `accessed:<檔>`；閉包內模組本身 import
    期讀檔或子行程命中 ⇒ `import-read-exec:<檔>←<模組>`／`import-exec-<理由>←<模組>`；
  executed／accessed／import-*-exec 之紀錄不分階段 ⇒ 以 setup 命中保守擴散。
- 紀錄無 `executed_files`（舊紀錄、呼叫記錄關閉）或只在收集檔者，退回 import 閉包（保守）：
  - `import-read:<檔>`：收集期（測試模組 import、所屬 conftest／`__init__.py` 載入與其收集期 hook）讀取之 repo 檔含
    改動檔，含 import 閉包內各模組 import 期間之讀檔（追蹤紀錄或收集檔之 `import_files`，兩者取聯集）；
  - `import-module:<檔>`：測試模組或其所用 fixture 實際引用之模組之 import 閉包含改動之模組原始碼（`import_modules`）；
- `proc-arg:<檔>`：其子行程命令列含改動檔路徑；
- `proc-dir:<目錄>→<檔>`：其子行程命令列含 repo 內目錄參數（grep -r、rg、find 等掃描整棵樹），改動檔在其下；
- `proc-script:<腳本>`：其子行程命令列含某 repo 腳本，而該腳本（或其遞迴引用之 repo 腳本）原始碼提及改動檔
  （提及＝可執行內容〔去 `#` 註解與 Python docstring〕含相對路徑；或含檔名且該檔名於 repo 版控檔中唯一）——子行程內
  讀檔追不到，以此保守補判。
  執行期子行程（`procs`）與收集期子行程（`import_procs`）同此三種判法，後者理由加前綴 `import-`
  （如 `import-proc-arg:<檔>`）。
- `shared-fixture:<命中者>`／`same-file-fixture:<命中者>`：命中發生於 setup 階段（module／session 等 fixture 建立；
  舊紀錄無階段資訊者一律視為可能），則與命中者共用任一非 function 範圍之專案 fixture 之測試亦受影響（pytest 內建
  session fixture 不算共用依據）。命中者之 shared 已知（紀錄所帶，或舊紀錄缺而以 `--collect` 收集檔補）且去掉內建
  後為空 ⇒ 不擴散（其 setup 依賴只能來自每測試重建之 function 範圍 fixture，各測試自身紀錄已含）；命中者 shared
  未知（舊紀錄且收集檔亦無）⇒ 保守以同檔計；他測試 shared 未知而與命中者同檔 ⇒ 亦以同檔計。
- `untraced`：收集檔（`readtrace_plugin` 只收集輸出）有、追蹤紀錄無，且未因上列理由選入 ⇒ 執行期依賴未知 ⇒ 必跑
  （TEST_SELECTION §1）；`--exclude-untraced` 只供量測。此類 nodeid 亦照判 test-file、import-*、fixture 擴散。
同一 nodeid 多筆紀錄（重跑）取最後一筆。摘要另列 `affected_excl_untraced=`。

用法：`venv/bin/python scripts/affected_from_trace.py <trace.jsonl>... --changed <改動檔清單> --out <輸出.tsv>
[--collect <只收集.jsonl>...] [--exclude-untraced]`
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shlex
import subprocess
import tokenize
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

REPO = Path(__file__).resolve().parents[1]
_SCRIPT_SUFFIX = (".sh", ".py")


def _builtin_session() -> frozenset:
    """pytest／pytest-asyncio 內建 session fixture 名（唯一來源 `scripts/ledger_durations.py:_BUILTIN_SESSION`）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("affected_from_trace_ld", Path(__file__).resolve().parent
                                                  / "ledger_durations.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod._BUILTIN_SESSION


_BUILTIN_SESSION = _builtin_session()


def _project_shared(ids: Iterable[str]) -> Set[str]:
    """共用 fixture id 去掉 pytest 內建者（`<scope>:` 空 baseid `::<內建名>`）：內建 fixture 定義於 repo 外、不讀 repo 檔，
    且幾乎每條測試皆用——經其擴散＝全選（ICPERF L1c 補跑實測 6,891 條中 3,855 條僅經內建 fixture 擴散）。"""
    out = set()
    for x in ids:
        head, _, name = str(x).rpartition("::")
        if name in _BUILTIN_SESSION and head.split(":", 1)[-1] == "":
            continue
        out.add(str(x))
    return out


def latest_records(paths: Iterable[Path]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec.get("nodeid"), str):
                out[rec["nodeid"]] = rec
    return out


def _tracked(root: Path) -> List[str]:
    res = subprocess.run(["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True)
    return [ln for ln in res.stdout.splitlines() if ln]


def mention_patterns(changed: Iterable[str], tracked: List[str]) -> Dict[str, re.Pattern]:
    """改動檔 → 其被提及之樣式（相對路徑；檔名於版控檔唯一者另含檔名）。"""
    counts = Counter(Path(t).name for t in tracked)
    out = {}
    for c in changed:
        alts = [re.escape(c)]
        if counts[Path(c).name] <= 1:
            alts.append(r"(?<![\w.-])" + re.escape(Path(c).name) + r"(?![\w-])")
        out[c] = re.compile("|".join(alts))
    return out


#: 讀取 docstring 作資料之寫法（`__doc__`、`inspect.getdoc`、`help(`）：出現即不去 docstring（保守；審碼 r13 CODEX-R13-P1-01）
_DOC_CONSUMERS = ("__doc__", "getdoc", "help")


def _strip_py(src: str) -> str:
    """去 Python 之 `#` 註解與語句層級字串（docstring）；程式中之字串常值保留（以路徑讀檔者在此）。程式碼含
    `_DOC_CONSUMERS` 任一名稱 ⇒ docstring 可能被當資料讀 ⇒ 只去註解。無法斷詞 ⇒ 原文（保守）。"""
    try:
        toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return src
    # 原文任何位置（含字串，如 globals()['__doc__']、getattr(m, "__doc__")）出現即保留——寧多選不漏選（審碼 r14）
    keep_docs = any(name in src for name in _DOC_CONSUMERS)
    out: List[str] = []
    prev = tokenize.NEWLINE
    for tok in toks:
        if tok.type in (tokenize.COMMENT, tokenize.NL):
            continue
        if not keep_docs and tok.type == tokenize.STRING and prev in (tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT):
            prev = tokenize.NEWLINE  # docstring 後之 NEWLINE 仍屬語句起點
            continue
        prev = tok.type
        out.append(tok.string)
    return " ".join(out)


#: heredoc 終止字＝任一字詞（含數字開頭如 <<'0'；審碼 r14）；誤判（如算術 $((x<<2))）只使其後內容原樣保留＝寧多選不漏選
_HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([^\s'\"<>;&|()]+)\2")


def _strip_sh(src: str) -> str:
    """去 shell 註解：`#` 位於字詞開頭（行首或空白、`;&|(` 後）且不在引號內才是註解（`$#`、`${#x}`、引號內或反斜線跳脫之
    `#` 不算）；引號狀態跨行延續；heredoc 內容原樣保留（審碼 r13 CODEX-R13-P1-02）；首行 shebang 保留。"""
    out: List[str] = []
    quote = ""
    pending: List[Tuple[str, bool]] = []  # 本行登記、下一行起生效之 heredoc（終止字、是否 <<- 允許前導 tab）
    in_doc: Optional[Tuple[str, bool]] = None
    for n, ln in enumerate(src.splitlines()):
        if in_doc is not None:
            out.append(ln)
            delim, tabs = in_doc
            if (ln.lstrip("\t") if tabs else ln) == delim:
                in_doc = pending.pop(0) if pending else None
            continue
        cut = len(ln)
        i = 0
        while i < len(ln):
            ch = ln[i]
            if quote == "'":
                if ch == "'":
                    quote = ""
            elif quote == '"':
                if ch == "\\":
                    i += 1
                elif ch == '"':
                    quote = ""
            elif ch == "\\":
                i += 1
            elif ch in ("'", '"'):
                quote = ch
            elif ch == "#" and (i == 0 or ln[i - 1] in " \t;&|(") and not (n == 0 and i == 0 and ln.startswith("#!")):
                cut = i
                break
            elif ln.startswith("<<", i) and not ln.startswith("<<<", i):
                m = _HEREDOC.match(ln, i)
                if m:
                    pending.append((m.group(3), m.group(1) == "-"))
                    i = m.end()
                    continue
            i += 1
        out.append(ln[:cut])
        if pending and not quote:
            in_doc = pending.pop(0)
    return "\n".join(out)


def _code_text(path: str, src: str) -> str:
    """腳本之可執行內容（去註解與說明文字）：提及改動檔只在註解／docstring 者不算依賴（2026-11-12 實測：
    `scripts/run_receipt_identity.py` 之 docstring 提及 `docs/NOCAP_SPEC.md`，經腳本互相引用傳染，選入約 1,750 條不相干之治理測試）。"""
    if path.endswith(".py"):
        return _strip_py(src)
    if path.endswith(".sh"):
        return _strip_sh(src)
    return src


def tainted_scripts(root: Path, tracked: List[str], patterns: Dict[str, re.Pattern]) -> Dict[str, str]:
    """repo 腳本 → 其（遞迴）提及之改動檔；遞迴：腳本可執行內容（去註解與說明文字）提及已污染腳本之相對路徑或唯一檔名。"""
    scripts = [t for t in tracked if t.endswith(_SCRIPT_SUFFIX) and not t.startswith("tests/")]
    text = {}
    for s in scripts:
        try:
            text[s] = _code_text(s, (root / s).read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
    taint: Dict[str, str] = {}
    for s, body in text.items():
        for c, pat in patterns.items():
            if s != c and pat.search(body):
                taint[s] = c
                break
    counts = Counter(Path(t).name for t in tracked)
    changed = True
    while changed:
        changed = False
        for s, body in text.items():
            if s in taint:
                continue
            for t in list(taint):
                alts = [re.escape(t)] + ([re.escape(Path(t).name)] if counts[Path(t).name] <= 1 else [])
                if re.search("|".join(alts), body):
                    taint[s] = f"{taint[t]}（經 {t}）"
                    changed = True
                    break
    return taint


#: 相對目錄無法還原（舊紀錄無子行程 cwd 且參數以 `..` 起首）⇒ 保守視為可能掃到改動檔
UNRESOLVED = "?"


def _dir_tokens(cmd: str, root: Path, cwd: Optional[str] = None, depth: int = 0) -> List[str]:
    """命令列中指向 repo 內目錄之參數（repo 相對；`.`＝repo 根）：目錄掃描（grep -r、rg、find、git grep 等）會讀其下全部檔。
    相對參數以子行程 cwd（紀錄之 `proc_cwds`）解析；無 cwd 之舊紀錄以 repo 根解析，惟 `..` 起首者無法還原 ⇒ UNRESOLVED。"""
    try:  # 控制運算子（; && || | &）另成 token：`true;cd x;grep` 之 cd 才辨識得到
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        toks = list(lex)
    except ValueError:
        toks = cmd.split()
    out = []
    base = Path(cwd) if cwd else root
    # shell 內層命令中切換目錄（cd／pushd，經 && ; 換行等串接）不經稽核事件 ⇒ 其後之相對目錄皆不可知 ⇒ 保守
    if depth > 0 and any(t.rstrip(";&|") in ("cd", "pushd") for t in toks):
        return [UNRESOLVED]
    for tok in toks[1:]:
        # `bash -c "grep -r x momentum"` 之內層命令：只依 shlex 會切開之 ASCII 空白遞迴（全形空白等不切，否則無窮遞迴）
        if depth < 3 and any(ch in " \t\r\n" for ch in tok):
            out += _dir_tokens("_ " + tok, root, cwd, depth + 1)
            continue
        if not tok or tok.startswith("-") or "=" in tok or set(tok) <= set(";&|"):
            continue
        # `..` 起首而 cwd 不可知：舊紀錄無 cwd，或位於 shell 內層命令（其中之 `cd` 不經稽核事件）⇒ 保守
        if tok.startswith("..") and (cwd is None or depth > 0):
            out.append(UNRESOLVED)
            continue
        p = Path(tok)
        try:
            rel = (p if p.is_absolute() else base / p).resolve().relative_to(root.resolve())
        except (ValueError, OSError):
            continue
        if not (root / rel).is_dir():
            continue
        out.append(str(rel))
    return out


def _proc_reason(cmd: str, changed: Set[str], script_pat: Dict[str, re.Pattern], taint: Dict[str, str],
                 root: Path, cwd: Optional[str] = None) -> str:
    arg = next((c for c in sorted(changed) if c in cmd), None)
    if arg:
        return f"proc-arg:{arg}"
    for d in _dir_tokens(cmd, root, cwd):
        if d == UNRESOLVED:
            return "proc-dir-unresolved:無子行程 cwd 之 .. 相對目錄"
        under = next((c for c in sorted(changed) if d == "." or c.startswith(d.rstrip("/") + "/")), None)
        if under:
            return f"proc-dir:{d}→{under}"
    scr = next((s for s, p in script_pat.items() if p.search(cmd)), None)
    if scr:
        return f"proc-script:{scr}→{taint[scr]}"
    return ""


def _pairs(cmds: Optional[list], cwds: Optional[list]) -> List[tuple]:
    """子行程命令與其 cwd 配對（舊紀錄無 cwd ⇒ None）。"""
    cmds = cmds or []
    cwds = cwds if cwds is not None and len(cwds) == len(cmds) else [None] * len(cmds)
    return list(zip(cmds, cwds))


def affected(records: Dict[str, dict], changed: Set[str], root: Path = REPO,
             collected: Optional[Dict[str, dict]] = None, readers: Optional[Dict[str, dict]] = None,
             include_untraced: bool = True, mod_tables: Optional[Dict[str, dict]] = None) -> Dict[str, str]:
    """受影響 nodeid → 理由。`collected`＝只收集輸出（nodeid → {shared, import_files, import_procs,
    import_proc_cwds, import_modules}）：補紀錄缺之 shared、併入 import 期依賴；只在收集檔之 nodeid 亦判定，未因任何
    理由選入者以 `untraced` 選入（include_untraced=False 只供量測）。`readers`＝收集期讀者表（`reader_tables`）。"""
    collected = collected or {}
    tracked = _tracked(root)
    patterns = mention_patterns(changed, tracked)
    taint = tainted_scripts(root, tracked, patterns)
    script_pat = {s: re.compile(re.escape(s) + r"|(?<![\w.-])" + re.escape(Path(s).name) + r"(?![\w-])")
                  for s in taint}

    def shared_of(node: str) -> Optional[list]:
        """非 function 範圍 fixture：紀錄所帶者優先，缺則取收集檔；兩者皆無 ⇒ None（未知）。"""
        rec = records.get(node)
        if rec is not None and "shared" in rec:
            return rec.get("shared") or []
        if node in collected and "shared" in collected[node]:
            return collected[node].get("shared") or []
        return None

    # 讀者表：外部（收集期讀者表行）＋各紀錄之 reader_*（執行期，第一個呼叫者所記）之聯集
    table: Dict[str, dict] = {}

    def _merge(rid: str, files: Iterable[str], procs: List[tuple]) -> None:
        cur = table.setdefault(rid, {"files": set(), "procs": []})
        cur["files"] |= set(files)
        cur["procs"] += [p for p in procs if p not in cur["procs"]]

    for rid, ent in (readers or {}).items():
        _merge(rid, ent.get("files") or [], _pairs(ent.get("procs"), ent.get("proc_cwds")))
    for rec in records.values():
        rprocs, rcwds = rec.get("reader_procs") or {}, rec.get("reader_proc_cwds") or {}
        for rid in set(rec.get("reader_files") or {}) | set(rprocs):
            _merge(rid, (rec.get("reader_files") or {}).get(rid) or [], _pairs(rprocs.get(rid), rcwds.get(rid)))
    # 模組本身 import 期讀檔表（{"mod_own"} 行之聯集）
    mod_own: Dict[str, dict] = {}
    mod_access: Dict[str, Set[str]] = {}
    for mod, ent in (mod_tables or {}).items():
        if mod == "__mod_access__":
            continue
        cur = mod_own.setdefault(mod, {"files": set(), "procs": []})
        cur["files"] |= set(ent.get("files") or [])
        cur["procs"] += [p for p in _pairs(ent.get("procs"), ent.get("proc_cwds")) if p not in cur["procs"]]
    for mod, targets in ((mod_tables or {}).get("__mod_access__") or {}).items():
        mod_access.setdefault(mod, set()).update(targets)

    access_memo: Dict[frozenset, List[str]] = {}

    def access_closure(start: Iterable[str]) -> List[str]:
        """起點模組沿 import 期存取邊（mod_access：匯入端 → 被存取其資料／類別之模組）遞迴之閉包（含起點）。"""
        key = frozenset(start)
        if key not in access_memo:
            seen, stack = set(), list(key)
            while stack:
                m = stack.pop()
                if m in seen:
                    continue
                seen.add(m)
                stack.extend(mod_access.get(m, ()))
            access_memo[key] = sorted(seen)
        return access_memo[key]

    def exec_import_reason(rec: dict, col: dict, executed: List[str]) -> str:
        """有 executed_files 之紀錄：(1) 測試模組／conftest 本身 import 期讀檔或子行程（import_direct_*）⇒
        `import-direct-` 前綴之 import-read／import-proc-*；(2) 起點＝執行到之模組 ∪ 本測試存取其屬性之模組
        （accessed_modules），沿 mod_access 邊之閉包內：模組原始碼即改動檔 ⇒ `accessed:<檔>`；模組 M 本身 import 期
        讀檔命中 ⇒ `import-read-exec:<檔>←<M>`，子行程 ⇒ `import-exec-<理由>←<M>`。"""
        src = rec if "import_direct_files" in rec else col
        dhit = sorted(set(src.get("import_direct_files") or []) & changed)
        if dhit:
            return f"import-direct-import-read:{dhit[0]}"
        for cmd, cwd in _pairs(src.get("import_direct_procs"), src.get("import_direct_proc_cwds")):
            r = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
            if r:
                return f"import-direct-import-{r}"
        mods = access_closure(set(executed) | set(rec.get("accessed_modules") or []))
        src_hit = sorted(set(mods) & changed)
        if src_hit:
            return f"accessed:{src_hit[0]}"
        for mod in mods:
            ent = mod_own.get(mod)
            if not ent:
                continue
            hit = sorted(ent["files"] & changed)
            if hit:
                return f"import-read-exec:{hit[0]}←{mod}"
            for cmd, cwd in ent["procs"]:
                r = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
                if r:
                    return f"import-exec-{r}←{mod}"
        return ""

    memo: Dict[str, str] = {}

    def reader_reason(rids: Iterable[str]) -> str:
        """呼叫到之讀者中，讀過改動檔或其子行程命中者 ⇒ `cached-read:<檔>←<讀者>`／`cached-<子行程理由>←<讀者>`。"""
        for rid in sorted(rids):
            if rid not in memo:
                ent = table.get(rid)
                hit = sorted(ent["files"] & changed) if ent else []
                why = f"cached-read:{hit[0]}←{rid}" if hit else ""
                for cmd, cwd in ([] if why or not ent else ent["procs"]):
                    r = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
                    if r:
                        why = f"cached-{r}←{rid}"
                        break
                memo[rid] = why
            if memo[rid]:
                return memo[rid]
        return ""

    out: Dict[str, str] = {}
    setup_hit: Set[str] = set()  # 依賴可能來自共用 fixture（setup 階段命中，或舊紀錄無階段資訊）
    nodes = list(records) + [n for n in collected if n not in records]
    for node in nodes:
        rec = records.get(node) or {}
        col = collected.get(node) or {}
        own = node.split("::", 1)[0]
        if own in changed:  # 測試檔本身改動（pytest 以 import 載入測試模組，讀檔追蹤看不到）
            out[node] = f"test-file:{own}"
            continue
        # 執行期（setup＋call）：讀檔、子行程
        hit = sorted(set(rec.get("files") or []) & changed)
        reason = f"read:{hit[0]}" if hit else ""
        for cmd, cwd in ([] if reason else _pairs(rec.get("procs"), rec.get("proc_cwds"))):
            reason = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
            if reason:
                break
        if not reason:  # 執行期呼叫到之讀者（快取命中者自身無讀檔）⇒ 繼承讀者讀過之檔與子行程
            reason = reader_reason(rec.get("calls") or [])
        executed = rec.get("executed_files")
        exec_mode = executed is not None and bool(mod_own or mod_access)
        if not reason and exec_mode:  # 本測試實際執行到之改動 .py
            ehit = sorted(set(executed) & changed)
            reason = f"executed:{ehit[0]}" if ehit else ""
        if not reason and exec_mode:
            # 有執行紀錄：模組 import 期讀檔只歸「執行到該模組（或讀其模組層資料）」之測試；直接讀檔另判
            reason = exec_import_reason(rec, col, executed)
            if reason.startswith("import-direct-"):
                out[node] = reason[len("import-direct-"):]
                continue  # 測試模組／conftest 本身 import 期所做：已直接歸屬同模組／目錄全部 item ⇒ 不經 fixture 擴散
        if not reason and not exec_mode:  # 收集期（import／conftest 載入）：已直接歸屬同模組／目錄全部 item ⇒ 不經 fixture 擴散
            ihit = sorted((set(rec.get("import_files") or []) | set(col.get("import_files") or [])) & changed)
            reason = f"import-read:{ihit[0]}" if ihit else ""
            if not reason:
                mhit = sorted((set(rec.get("import_modules") or []) | set(col.get("import_modules") or [])) & changed)
                reason = f"import-module:{mhit[0]}" if mhit else ""
            for cmd, cwd in ([] if reason else (_pairs(rec.get("import_procs"), rec.get("import_proc_cwds"))
                                                + _pairs(col.get("import_procs"), col.get("import_proc_cwds")))):
                reason = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
                if reason:
                    reason = f"import-{reason}"
                    break
            if reason:
                out[node] = reason
            continue
        if not reason:
            continue
        out[node] = reason
        setup_procs = rec.get("setup_procs") or []
        setup_cwds = rec.get("setup_proc_cwds")
        if "setup_files" not in rec:
            setup_hit.add(node)
        elif reason.startswith(("executed:", "accessed:", "import-read-exec:", "import-exec-")):
            setup_hit.add(node)  # 執行紀錄不分階段：可能為 module／session fixture 之建立（只第一個使用者執行）⇒ 保守擴散
        elif set(rec.get("setup_files") or []) & changed:
            setup_hit.add(node)
        elif setup_procs and setup_cwds is None and not reason.startswith(("read:", "test-file:")):
            setup_hit.add(node)  # setup 子行程無 cwd 紀錄而命中來自子行程 ⇒ 無法排除 setup 命中，保守擴散
        elif any(_proc_reason(c, changed, script_pat, taint, root, w)
                 for c, w in zip(setup_procs, setup_cwds or [None] * len(setup_procs))):
            setup_hit.add(node)
        elif reader_reason(rec.get("setup_calls") or []):
            setup_hit.add(node)  # setup 階段（fixture 建立）呼叫到之讀者命中 ⇒ 共用該 fixture 者亦依賴
    # 共用 fixture 擴散：module／session 等 fixture 只在第一個使用者之 setup 讀檔，後續使用者之紀錄不含該依賴 ⇒
    # 與命中者共用任一非 function 範圍之專案 fixture 之測試皆受影響（pytest 內建者除外，見 `_project_shared`）；
    # 命中者 shared 已知而無專案共用 fixture ⇒ 不擴散；命中者 shared 未知、或他測試 shared 未知 ⇒ 保守以同檔計
    for node in sorted(setup_hit):
        known = shared_of(node)
        if known is not None and not _project_shared(known):
            continue
        shared = _project_shared(known or [])
        own = node.split("::", 1)[0]
        for other in nodes:
            if other in out:
                continue
            other_shared = shared_of(other)
            if shared and other_shared is not None and set(other_shared) & shared:
                out[other] = f"shared-fixture:{node}"
            elif (known is None or other_shared is None) and other.split("::", 1)[0] == own:
                out[other] = f"same-file-fixture:{node}"
    # 未追蹤：收集檔有、追蹤紀錄無 ⇒ 執行期依賴未知 ⇒ 必跑（TEST_SELECTION §1）；量測用可關
    if include_untraced:
        for node in collected:
            if node not in records and node not in out:
                out[node] = "untraced"
    return out


def mod_tables(paths: Iterable[Path]) -> Dict[str, dict]:
    """追蹤／收集檔中之模組本身 import 期讀檔表行（`{"mod_own": {模組: {files, procs, proc_cwds}}}`）之聯集；模組 import
    期存取邊表行（`{"mod_access": {匯入端: [被存取模組...]}}`）之聯集置於鍵 `__mod_access__`。"""
    out: Dict[str, dict] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if '"mod_access"' in line:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if isinstance(rec.get("mod_access"), dict) and "nodeid" not in rec:
                    acc = out.setdefault("__mod_access__", {})
                    for mod, targets in rec["mod_access"].items():
                        acc[mod] = sorted(set(acc.get(mod, [])) | set(targets or []))
                continue
            if '"mod_own"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec.get("mod_own"), dict) and "nodeid" not in rec:
                for mod, ent in rec["mod_own"].items():
                    cur = out.setdefault(mod, {"files": [], "procs": [], "proc_cwds": []})
                    cur["files"] = sorted(set(cur["files"]) | set(ent.get("files") or []))
                    cur["procs"] += ent.get("procs") or []
                    cur["proc_cwds"] += ent.get("proc_cwds") or [None] * len(ent.get("procs") or [])
    return out


def reader_tables(paths: Iterable[Path]) -> Dict[str, dict]:
    """追蹤／收集檔中之收集期讀者表行（`{"readers": {id: {files, procs, proc_cwds}}}`）之聯集。"""
    out: Dict[str, dict] = {}
    for path in paths:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if '"readers"' not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if isinstance(rec.get("readers"), dict) and "nodeid" not in rec:
                for rid, ent in rec["readers"].items():
                    cur = out.setdefault(rid, {"files": [], "procs": [], "proc_cwds": []})
                    cur["files"] = sorted(set(cur["files"]) | set(ent.get("files") or []))
                    cur["procs"] += ent.get("procs") or []
                    cur["proc_cwds"] += ent.get("proc_cwds") or [None] * len(ent.get("procs") or [])
    return out


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--changed", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--collect", action="extend", nargs="+", default=[],
                    help="readtrace_plugin 只收集輸出（READTRACE_COLLECT_OUT）；可多個，後者覆蓋前者同 nodeid")
    ap.add_argument("--exclude-untraced", action="store_true",
                    help="只供量測：不把未追蹤（收集檔有、追蹤紀錄無）且無其他理由者列入（正式選取不得用）")
    args = ap.parse_args(argv)
    changed = {ln.strip() for ln in Path(args.changed).read_text(encoding="utf-8").splitlines() if ln.strip()}
    recs = latest_records(Path(t) for t in args.traces)
    coll = latest_records(Path(c) for c in args.collect)
    paths = [Path(t) for t in args.traces] + [Path(c) for c in args.collect]
    res = affected(recs, changed, collected=coll, readers=reader_tables(paths), include_untraced=not args.exclude_untraced,
                   mod_tables=mod_tables(paths))
    Path(args.out).write_text("".join(f"{n}\t{r}\n" for n, r in sorted(res.items())), encoding="utf-8")
    kinds = Counter(r.split(":", 1)[0] for r in res.values())
    untraced = sum(1 for n in coll if n not in recs)
    print(f"records={len(recs)} collected={len(coll)} untraced={untraced} affected={len(res)} "
          f"affected_excl_untraced={len(res) - kinds.get('untraced', 0)} "
          + " ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
