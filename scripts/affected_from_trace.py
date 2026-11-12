"""依讀檔追蹤（`scripts/readtrace_plugin.py` 之 JSONL）與本批改動檔，算受影響 nodeid（TEST_SELECTION §5 過渡期）。

判定（任一成立 ⇒ 受影響，附理由）：
- `test-file:<檔>`：該 nodeid 所在之測試檔本身即改動檔；
- `read:<檔>`：該 nodeid 執行期間讀取之 repo 檔含改動檔；
- `proc-arg:<檔>`：其子行程命令列含改動檔路徑；
- `proc-dir:<目錄>→<檔>`：其子行程命令列含 repo 內目錄參數（grep -r、rg、find 等掃描整棵樹），改動檔在其下；
- `proc-script:<腳本>`：其子行程命令列含某 repo 腳本，而該腳本（或其遞迴引用之 repo 腳本）原始碼提及改動檔
  （提及＝可執行內容〔去 `#` 註解與 Python docstring〕含相對路徑；或含檔名且該檔名於 repo 版控檔中唯一）——子行程內
  讀檔追不到，以此保守補判。
- `shared-fixture:<命中者>`／`same-file-fixture:<命中者>`：命中發生於 setup 階段（module／session 等 fixture 建立；
  舊紀錄無階段資訊者一律視為可能），則與命中者共用任一非 function 範圍之專案 fixture 之測試亦受影響（pytest 內建
  session fixture 不算共用依據；舊紀錄或命中者只用內建 fixture 者以同檔計）。
同一 nodeid 多筆紀錄（重跑）取最後一筆。不涵蓋：import 時執行之改動（由直接執行改動函式之測試覆蓋，另列）。

用法：`venv/bin/python scripts/affected_from_trace.py <trace.jsonl>... --changed <改動檔清單> --out <輸出.tsv>`
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
    keep_docs = any(t.type == tokenize.NAME and t.string in _DOC_CONSUMERS for t in toks)
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


_HEREDOC = re.compile(r"<<(-?)\s*(['\"]?)([A-Za-z_]\w*)\2")


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


def affected(records: Dict[str, dict], changed: Set[str], root: Path = REPO) -> Dict[str, str]:
    tracked = _tracked(root)
    patterns = mention_patterns(changed, tracked)
    taint = tainted_scripts(root, tracked, patterns)
    script_pat = {s: re.compile(re.escape(s) + r"|(?<![\w.-])" + re.escape(Path(s).name) + r"(?![\w-])")
                  for s in taint}
    out: Dict[str, str] = {}
    setup_hit: Set[str] = set()  # 依賴可能來自共用 fixture（setup 階段命中，或舊紀錄無階段資訊）
    for node, rec in records.items():
        own = node.split("::", 1)[0]
        if own in changed:  # 測試檔本身改動（pytest 以 import 載入測試模組，讀檔追蹤看不到）
            out[node] = f"test-file:{own}"
            continue
        hit = sorted(set(rec.get("files") or []) & changed)
        reason = f"read:{hit[0]}" if hit else ""
        procs = [] if reason else (rec.get("procs") or [])
        cwds = rec.get("proc_cwds") or [None] * len(procs)
        for cmd, cwd in zip(procs, cwds):
            reason = _proc_reason(cmd, changed, script_pat, taint, root, cwd)
            if reason:
                break
        if not reason:
            continue
        out[node] = reason
        setup_procs = rec.get("setup_procs") or []
        setup_cwds = rec.get("setup_proc_cwds")
        if "setup_files" not in rec:
            setup_hit.add(node)
        elif set(rec.get("setup_files") or []) & changed:
            setup_hit.add(node)
        elif setup_procs and setup_cwds is None and not reason.startswith(("read:", "test-file:")):
            setup_hit.add(node)  # setup 子行程無 cwd 紀錄而命中來自子行程 ⇒ 無法排除 setup 命中，保守擴散
        elif any(_proc_reason(c, changed, script_pat, taint, root, w)
                 for c, w in zip(setup_procs, setup_cwds or [None] * len(setup_procs))):
            setup_hit.add(node)
    # 共用 fixture 擴散：module／session 等 fixture 只在第一個使用者之 setup 讀檔，後續使用者之紀錄不含該依賴 ⇒
    # 與命中者共用任一非 function 範圍之專案 fixture 之測試皆受影響（pytest 內建者除外，見 `_project_shared`）；
    # 舊紀錄（無 shared）或命中者只用內建 fixture ⇒ 保守以同檔計
    for node in sorted(setup_hit):
        shared = _project_shared(records[node].get("shared") or [])
        own = node.split("::", 1)[0]
        for other, rec in records.items():
            if other in out:
                continue
            if shared and set(rec.get("shared") or []) & shared:
                out[other] = f"shared-fixture:{node}"
            elif (not shared or "shared" not in rec) and other.split("::", 1)[0] == own:
                out[other] = f"same-file-fixture:{node}"
    return out


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("traces", nargs="+")
    ap.add_argument("--changed", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    changed = {ln.strip() for ln in Path(args.changed).read_text(encoding="utf-8").splitlines() if ln.strip()}
    recs = latest_records(Path(t) for t in args.traces)
    res = affected(recs, changed)
    Path(args.out).write_text("".join(f"{n}\t{r}\n" for n, r in sorted(res.items())), encoding="utf-8")
    kinds = Counter(r.split(":", 1)[0] for r in res.values())
    print(f"records={len(recs)} affected={len(res)} " + " ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
