#!/usr/bin/env python3
"""_live_doc_write_guard.py — DOCROT2 Task 2.1–2.4（票 B-63）：活文件寫入判定之唯一實作。

呼叫端（薄包裝，不得另寫判定）：scripts/live_doc_write_guard.sh
  （無參數）                   PreToolUse hook：stdin＝payload；Edit／Write 以「寫入後全文」判定。exit 0 放行／2 擋。
  --staged                     pre-commit：暫存之登記活文件，HEAD 版為舊檔、index 版為寫入後全文。rc 0／1。
  --tree <commit> --path <p>   以該 commit 之檔為寫入後全文，只執行交接檔全文判定（Task 2.4）。rc 0／1。
rc 2＝用法或環境錯誤（hook 模式之環境錯誤亦以 exit 2 擋）。

判定（依 scripts/live_doc_registry.json 之類別旗標；字面集合、指標文法、交接檔文法皆只定義於該檔）：
  ① new_line_status_check（Task 2.1）：新增行＝舊檔與寫入後全文之行級 diff（insert／replace 之寫入後側），
     去除豁免區（本檔為其 target 之生成區塊、HISTORY-BEGIN..END、fenced code block）後，
     交 `gen_fact_key_blocks.sh --status-hits`（與全檔模式共用同一段判定碼）。不設引號或樣本句豁免。
  ② archaeology_check（Task 2.2）：歷史專區外之新增行（生成區塊與結構標記行除外）含 `~~`、考古字面、
     canonical finding ID ⇒ 違規；歷史專區內之新增非空行須全行符合指標文法——主詞 v<N> 或登記之狀態識別碼，
     目標為工作樹存在之反引號 repo 相對路徑或 `git cat-file -e <sha>^{commit}` 成立之 commit。刪除行不判。
  ③ handoff_grammar（Task 2.4）：H1 恰一行、H2 封閉集合各恰一次、現況／待辦只含對應投影生成區塊且列之
     「下一步」非空、進行中紀錄區只含 HISTORY 區塊且首個非空行為條目標記、標記識別碼須登記；
     --staged／--tree 另判條目識別碼（標記與指標主詞）之狀態不得屬 enforcement_completed_statuses。
"""
from __future__ import annotations

import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _live_doc_registry as ldr  # noqa: E402

GEN_REL = os.path.join("scripts", "gen_fact_key_blocks.sh")
BEGIN_GEN_RE = re.compile(r"^<!-- BEGIN GENERATED: (.+) -->$")
END_GEN_RE = re.compile(r"^<!-- END GENERATED: (.+) -->$")
HIST_BEGIN = "<!-- HISTORY-BEGIN -->"
HIST_END = "<!-- HISTORY-END -->"
FENCE_RE = re.compile(r"^\s*```")
# 形狀同 scripts/_synth_attr.py 之 ID_RE，去除行首 `## ` 與行尾之錨定
FINDING_ID_RE = re.compile(r"[A-Z]+-R\d+-P[0-3]-\d{2,}")
SUBJECT_VERSION_RE = re.compile(r"^v[0-9]+$")


class GuardError(Exception):
    """環境或 payload 錯誤（fail-closed）。"""


# ────────────────────────────────────────────────────────────── 資料來源

def _git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", root, "-c", "core.quotePath=false", *args], capture_output=True)


def _git_show(root: str, spec: str) -> Optional[bytes]:
    r = _git(root, "show", spec)
    return r.stdout if r.returncode == 0 else None


class Context:
    """一次判定所需之登記資料（登記檔讀工作樹；fact_keys 依模式讀工作樹／index／commit）。"""

    def __init__(self, root: str, fact_keys_text: Optional[str] = None):
        self.root = root
        errs, self.norm = ldr._load(root)
        if errs or not self.norm:
            raise GuardError("活文件登記檔不合規：" + "；".join(errs))
        self.registry = ldr.load_json(os.path.join(root, ldr.REGISTRY_REL))
        if fact_keys_text is None:
            try:
                with open(os.path.join(root, ldr.FACT_KEYS_REL), encoding="utf-8") as fh:
                    fact_keys_text = fh.read()
            except OSError as exc:
                raise GuardError(f"讀不到 fact_keys.json：{exc}")
        try:
            self.fact_keys = json.loads(fact_keys_text)
        except json.JSONDecodeError as exc:
            raise GuardError(f"fact_keys.json 非合法 JSON：{exc}")
        schema = self.fact_keys.get("_schema") or {}
        self.completed = set(schema.get("enforcement_completed_statuses") or [])
        if not self.completed:
            raise GuardError("fact_keys.json 缺 `_schema.enforcement_completed_statuses`")
        self.status_of: Dict[str, str] = {}
        for key in list(schema.get("status_keys") or []) + list(schema.get("docrot2_status_keys") or []):
            spec = self.fact_keys.get(key)
            if not isinstance(spec, dict):
                continue
            cols = spec.get("columns") or []
            si = cols.index("狀態") if "狀態" in cols else None
            for row in spec.get("rows") or []:
                if isinstance(row, list) and len(row) > 1:
                    self.status_of[row[1]] = row[si] if si is not None and si < len(row) else ""

    def cls_flags(self, rel: str) -> Tuple[Optional[str], dict]:
        if not ldr.in_scope(rel, self.norm["scope_roots"]):
            return None, {}
        cls = ldr.classify(rel, self.norm)
        if cls is None:
            return None, {}
        return cls, dict((self.registry.get("class_flags") or {}).get(cls) or {})

    def legal_keys(self, rel: str) -> Set[str]:
        out: Set[str] = set()
        for key, spec in self.fact_keys.items():
            if key == "_schema" or not isinstance(spec, dict):
                continue
            tgt = spec.get("target")
            targets = [tgt] if isinstance(tgt, str) else (tgt if isinstance(tgt, list) else [])
            if rel in targets:
                out.add(key)
        return out


# ────────────────────────────────────────────────────────────── 區段與新增行

def split_lines(text: str) -> List[str]:
    return text.split("\n")


def regions(lines: Sequence[str], legal: Set[str]) -> Dict[str, List[bool]]:
    """標出生成區塊、歷史專區、fenced code block 與結構標記行（未閉合之區塊不給豁免）。"""
    n = len(lines)
    gen, hist, fence, marker = [False] * n, [False] * n, [False] * n, [False] * n
    in_gen: Optional[Tuple[str, int]] = None
    in_hist = False
    in_fence: Optional[int] = None
    for i, ln in enumerate(lines):
        if in_gen is not None:
            gen[i] = True
            m = END_GEN_RE.match(ln)
            if m and m.group(1) == in_gen[0]:
                marker[i] = True
                in_gen = None
            continue
        if in_fence is not None:
            fence[i] = True
            if FENCE_RE.match(ln):
                in_fence = None
            continue
        m = BEGIN_GEN_RE.match(ln)
        if m and m.group(1) in legal and not in_hist:
            gen[i] = marker[i] = True
            in_gen = (m.group(1), i)
            continue
        if ln == HIST_BEGIN and not in_hist:
            marker[i] = True
            in_hist = True
            continue
        if ln == HIST_END and in_hist:
            marker[i] = True
            in_hist = False
            continue
        if in_hist:
            hist[i] = True
            continue
        if FENCE_RE.match(ln):
            fence[i] = True
            in_fence = i
    if in_gen is not None:                      # 未閉合生成區塊：撤銷豁免
        for j in range(in_gen[1], n):
            gen[j] = marker[j] = False
    if in_fence is not None:                    # 未閉合 fence：撤銷豁免
        for j in range(in_fence, n):
            fence[j] = False
    return {"gen": gen, "hist": hist, "fence": fence, "marker": marker}


def added_indices(old_lines: Sequence[str], new_lines: Sequence[str]) -> List[int]:
    sm = difflib.SequenceMatcher(None, list(old_lines), list(new_lines), autojunk=False)
    out: List[int] = []
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        if tag in ("insert", "replace"):
            out.extend(range(j1, j2))
    return out


# ────────────────────────────────────────────────────────────── ① 手寫狀態（Task 2.1）

def status_hits(ctx: Context, lines: Sequence[str], idxs: Sequence[int]) -> List[str]:
    if not idxs:
        return []
    gen = os.path.join(ctx.root, GEN_REL)
    if not os.path.isfile(gen):
        raise GuardError(f"缺 {GEN_REL}（判定碼唯一來源）")
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".lines") as fh:
        for i in idxs:
            fh.write(f"{i + 1}\t{lines[i]}\n")
        tmp = fh.name
    try:
        r = subprocess.run(["bash", gen, "--status-hits", tmp], cwd=ctx.root, capture_output=True)
    finally:
        os.unlink(tmp)
    if r.returncode != 0:
        raise GuardError("--status-hits 執行失敗：" + r.stderr.decode("utf-8", "replace").strip())
    out: List[str] = []
    for row in r.stdout.decode("utf-8").splitlines():
        parts = row.split("\t")
        if len(parts) == 3:
            out.append(f"L{parts[0]}：新增行含識別碼「{parts[1]}」與狀態「{parts[2]}」（狀態只准寫在 fact_keys.json 並以生成區塊呈現）")
    return out


# ────────────────────────────────────────────────────────────── ② 舊版字面與歷史指標（Task 2.2）

def _pointer_violation(ctx: Context, line: str) -> Optional[str]:
    pat = ctx.registry.get("history_pointer_regex")
    if not isinstance(pat, str):
        raise GuardError("live_doc_registry.json 缺 history_pointer_regex")
    m = re.match(pat, line)
    if not m:
        return "不符指標文法（- <YYYY-MM-DD>：<主詞> → <目標>）"
    subject, target = m.group(1), m.group(2)
    if not (SUBJECT_VERSION_RE.match(subject) or subject in ctx.status_of):
        return f"主詞「{subject}」須為 v<N> 或登記之狀態識別碼"
    if target.startswith("commit `"):
        sha = target[len("commit `"):-1]
        if _git(ctx.root, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
            return f"目標 commit {sha} 不存在"
        return None
    path = target.strip("`")
    parts = path.split("/")
    if path.startswith("/") or ".." in parts or "" in parts:
        return f"目標路徑「{path}」須為 repo 相對路徑"
    if not os.path.lexists(os.path.join(ctx.root, path)):
        return f"目標路徑「{path}」於工作樹不存在"
    return None


def archaeology(ctx: Context, lines: Sequence[str], idxs: Sequence[int], reg: Dict[str, List[bool]],
                handoff: bool) -> List[str]:
    literals = [s for s in (ctx.registry.get("archaeology_literals") or []) if isinstance(s, str) and s]
    entry_re = re.compile((ctx.registry.get("handoff") or {}).get("entry_marker_regex") or r"(?!)")
    out: List[str] = []
    for i in idxs:
        if reg["gen"][i] or reg["marker"][i]:
            continue
        ln = lines[i]
        if reg["hist"][i]:
            if not ln.strip() or (handoff and entry_re.match(ln)):
                continue
            why = _pointer_violation(ctx, ln)
            if why:
                out.append(f"L{i + 1}：歷史專區新增行{why}")
            continue
        if "~~" in ln:
            out.append(f"L{i + 1}：歷史專區外新增刪除線 `~~`（舊版字面不留在活文件；修訂史以指標指向不可變紀錄）")
        for lit in literals:
            if lit in ln:
                out.append(f"L{i + 1}：歷史專區外新增考古字面「{lit}」")
        m = FINDING_ID_RE.search(ln)
        if m:
            out.append(f"L{i + 1}：歷史專區外新增 finding ID「{m.group(0)}」（出處留在收斂檔，活文件只寫現行條文）")
    return out


# ────────────────────────────────────────────────────────────── ③ 交接檔文法（Task 2.4）

def _spans(lines: Sequence[str], starts: List[Tuple[int, str]]) -> Dict[str, Tuple[int, int]]:
    out: Dict[str, Tuple[int, int]] = {}
    for k, (i, name) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        out.setdefault(name, (i + 1, end))
    return out


def handoff_grammar(ctx: Context, lines: Sequence[str], reg: Dict[str, List[bool]], lifecycle: bool) -> List[str]:
    spec = ctx.registry.get("handoff") or {}
    h2_set = list(spec.get("h2_sections") or [])
    gen_only = list(spec.get("generated_only_sections") or [])
    sec_keys = dict(spec.get("section_projection_keys") or {})
    hist_sec = spec.get("history_section")
    entry_re = re.compile(spec.get("entry_marker_regex") or r"(?!)")
    if not h2_set or not hist_sec or set(gen_only) - set(sec_keys):
        raise GuardError("live_doc_registry.json 之 handoff 文法定義不完整")
    out: List[str] = []
    h1 = [i for i, ln in enumerate(lines) if ln.startswith("# ")]
    if len(h1) != 1:
        out.append(f"H1 須恰一行（實得 {len(h1)}）")
    elif any(ln.strip() for ln in lines[:h1[0]]):
        out.append("H1 之前不得有內容")
    starts = [(i, ln.rstrip()) for i, ln in enumerate(lines) if ln.startswith("## ")]
    names = [nm for _, nm in starts]
    for nm in names:
        if nm not in h2_set:
            out.append(f"H2「{nm}」不屬封閉集合 {h2_set}")
    for nm in h2_set:
        if names.count(nm) != 1:
            out.append(f"H2「{nm}」須恰一次（實得 {names.count(nm)}）")
    first = starts[0][0] if starts else len(lines)
    for i in range((h1[0] + 1) if h1 else 0, first):
        if lines[i].strip():
            out.append(f"L{i + 1}：H1 與首個 H2 之間不得有內容")
    spans = _spans(lines, starts)
    for sec in gen_only:
        if sec not in spans:
            continue
        key = sec_keys[sec]
        a, b = spans[sec]
        blocks = [i for i in range(a, b) if BEGIN_GEN_RE.match(lines[i])]
        mine = [i for i in blocks if BEGIN_GEN_RE.match(lines[i]).group(1) == key and reg["gen"][i]]
        if len(mine) != 1 or len(blocks) != 1:
            out.append(f"{sec} 須恰含一個 `{key}` 生成區塊（實得 {len(mine)} 個、區塊共 {len(blocks)} 個）")
        for i in range(a, b):
            if lines[i].strip() and not reg["gen"][i]:
                out.append(f"L{i + 1}：{sec} 只准生成區塊，不得手寫")
        header: Optional[List[str]] = None
        for i in range(a, b):
            if not (reg["gen"][i] and lines[i].startswith("|")):
                continue
            cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            if header is None:
                header = cells
                continue
            if all(set(c) <= {"-"} for c in cells):
                continue
            if "下一步" not in header:
                out.append(f"{sec} 投影缺「下一步」欄")
                break
            ni = header.index("下一步")
            if ni >= len(cells) or not cells[ni]:
                out.append(f"L{i + 1}：{sec} 投影列「下一步」為空")
    if hist_sec in spans:
        a, b = spans[hist_sec]
        begins = [i for i in range(a, b) if lines[i] == HIST_BEGIN]
        if len(begins) != 1:
            out.append(f"{hist_sec} 須恰含一個 HISTORY-BEGIN..END（實得 {len(begins)}）")
        for i in range(a, b):
            if lines[i].strip() and not (reg["hist"][i] or reg["marker"][i]):
                out.append(f"L{i + 1}：{hist_sec} 只准歷史專區內容")
        entries: List[Tuple[int, List[str], List[int]]] = []
        seen_first = False
        for i in range(a, b):
            if not reg["hist"][i] or not lines[i].strip():
                continue
            m = entry_re.match(lines[i])
            if m:
                ids = m.group(1).split(",")
                for x in ids:
                    if x not in ctx.status_of:
                        out.append(f"L{i + 1}：條目標記含未登記識別碼「{x}」")
                entries.append((i, ids, []))
                seen_first = True
                continue
            if not seen_first:
                out.append(f"L{i + 1}：{hist_sec} 首個條目標記前不得有內容")
                continue
            entries[-1][2].append(i)
        if lifecycle:
            pat = ctx.registry.get("history_pointer_regex") or r"(?!)"
            for i, ids, body in entries:
                subjects = list(ids)
                for j in body:
                    pm = re.match(pat, lines[j])
                    if pm and not SUBJECT_VERSION_RE.match(pm.group(1)):
                        subjects.append(pm.group(1))
                done = sorted({x for x in subjects if ctx.status_of.get(x) in ctx.completed})
                if done:
                    out.append(f"L{i + 1}：進行中紀錄之條目含已完成識別碼 {done}（整則移至 {spec.get('archive_path')}）")
    return out


# ────────────────────────────────────────────────────────────── 組合

def evaluate(ctx: Context, rel: str, old_text: str, new_text: str, *, lifecycle: bool,
             new_lines_only: bool = True) -> List[str]:
    cls, flags = ctx.cls_flags(rel)
    if cls is None:
        return []
    new_lines = split_lines(new_text)
    reg = regions(new_lines, ctx.legal_keys(rel))
    out: List[str] = []
    if new_lines_only:
        idxs = added_indices(split_lines(old_text), new_lines) if old_text != new_text else []
        if flags.get("new_line_status_check"):
            cand = [i for i in idxs if not (reg["gen"][i] or reg["hist"][i] or reg["fence"][i] or reg["marker"][i])]
            out += status_hits(ctx, new_lines, cand)
        if flags.get("archaeology_check"):
            out += archaeology(ctx, new_lines, idxs, reg, bool(flags.get("handoff_grammar")))
    if flags.get("handoff_grammar"):
        out += handoff_grammar(ctx, new_lines, reg, lifecycle)
    return out


def _report(rel: str, viols: Sequence[str]) -> None:
    print(f"live_doc_write_guard: 🔴 {rel}", file=sys.stderr)
    for v in viols:
        print(f"  · {v}", file=sys.stderr)


def hook_mode(raw: str) -> int:
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print("live_doc_write_guard: payload 不可解析 ⇒ fail-closed", file=sys.stderr)
        return 2
    if not isinstance(payload, dict):
        print("live_doc_write_guard: payload 非物件 ⇒ fail-closed", file=sys.stderr)
        return 2
    tool = payload.get("tool_name")
    if tool not in ("Edit", "Write"):
        return 0
    ti = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else None
    fp = ti.get("file_path") if ti else None
    if not isinstance(fp, str) or not fp:
        print("live_doc_write_guard: payload 缺 tool_input.file_path ⇒ fail-closed", file=sys.stderr)
        return 2
    root = ldr.repo_root()
    rel = os.path.relpath(os.path.abspath(fp), root)
    if rel.startswith("..") or os.path.isabs(rel):
        return 0
    try:
        ctx = Context(root)
        cls, _ = ctx.cls_flags(rel)
        if cls is None:
            return 0
        full = os.path.join(root, rel)
        old: Optional[str] = None
        if os.path.isfile(full):
            with open(full, encoding="utf-8") as fh:
                old = fh.read()
        if tool == "Write":
            new = ti.get("content")
            if not isinstance(new, str):
                raise GuardError("Write 之 content 非字串")
        else:
            o, n, ra = ti.get("old_string"), ti.get("new_string"), ti.get("replace_all", False)
            if not (isinstance(o, str) and o and isinstance(n, str) and isinstance(ra, bool)):
                raise GuardError("Edit 之 old_string／new_string／replace_all 型別不符")
            if old is None:
                raise GuardError("Edit 目標檔不存在")
            cnt = old.count(o)
            if ra:
                if cnt == 0:
                    raise GuardError("replace_all 為 true 但 old_string 於舊檔出現 0 次")
                new = old.replace(o, n)
            else:
                if cnt != 1:
                    raise GuardError(f"old_string 於舊檔須恰出現一次（實得 {cnt} 次）")
                new = old.replace(o, n, 1)
        old_text = old or ""
        if new == old_text:
            return 0
        viols = evaluate(ctx, rel, old_text, new, lifecycle=False)
    except (GuardError, ValueError, UnicodeDecodeError) as exc:
        print(f"live_doc_write_guard: {rel}：{exc} ⇒ fail-closed", file=sys.stderr)
        return 2
    if viols:
        _report(rel, viols)
        return 2
    return 0


def _decode(blob: Optional[bytes]) -> Optional[str]:
    if blob is None:
        return None
    if b"\0" in blob:
        return None
    try:
        return blob.decode("utf-8")
    except UnicodeDecodeError:
        return None


def staged_mode() -> int:
    root = ldr.repo_root()
    r = _git(root, "diff", "--cached", "--name-status", "-z", "-M", "--diff-filter=ACMR")
    if r.returncode != 0:
        print("live_doc_write_guard: git diff --cached 失敗 ⇒ fail-closed", file=sys.stderr)
        return 2
    fk = _decode(_git_show(root, ":" + ldr.FACT_KEYS_REL.replace(os.sep, "/")))
    try:
        ctx = Context(root, fk)
    except (GuardError, ValueError) as exc:
        print(f"live_doc_write_guard: {exc} ⇒ fail-closed", file=sys.stderr)
        return 2
    tokens = r.stdout.decode("utf-8").split("\0")
    items: List[Tuple[str, str]] = []
    i = 0
    while i < len(tokens) and tokens[i]:
        st = tokens[i]
        if st.startswith("R") or st.startswith("C"):
            items.append((tokens[i + 1], tokens[i + 2]))
            i += 3
        else:
            items.append((tokens[i + 1], tokens[i + 1]))
            i += 2
    rc = 0
    for old_path, path in items:
        new_text = _decode(_git_show(root, ":" + path))
        if new_text is None:
            continue
        old_text = _decode(_git_show(root, "HEAD:" + old_path)) or ""
        try:
            viols = evaluate(ctx, path, old_text, new_text, lifecycle=True)
        except GuardError as exc:
            print(f"live_doc_write_guard: {path}：{exc} ⇒ fail-closed", file=sys.stderr)
            return 2
        if viols:
            _report(path + "（暫存）", viols)
            rc = 1
    return rc


def tree_mode(commit: str, path: str) -> int:
    root = ldr.repo_root()
    new_text = _decode(_git_show(root, f"{commit}:{path}"))
    if new_text is None:
        print(f"live_doc_write_guard: {commit}:{path} 不存在或非文字 ⇒ fail-closed", file=sys.stderr)
        return 2
    fk = _decode(_git_show(root, f"{commit}:" + ldr.FACT_KEYS_REL.replace(os.sep, "/")))
    try:
        ctx = Context(root, fk)
        viols = evaluate(ctx, path, new_text, new_text, lifecycle=True, new_lines_only=False)
    except (GuardError, ValueError) as exc:
        print(f"live_doc_write_guard: {exc} ⇒ fail-closed", file=sys.stderr)
        return 2
    if viols:
        _report(f"{commit}:{path}", viols)
        return 1
    return 0


def main(argv: List[str]) -> int:
    if not argv:
        return hook_mode(sys.stdin.read())
    if argv == ["--staged"]:
        return staged_mode()
    if len(argv) == 4 and argv[0] == "--tree" and argv[2] == "--path":
        return tree_mode(argv[1], argv[3])
    print("用法: live_doc_write_guard.sh [--staged | --tree <commit> --path <p>]（無參數＝PreToolUse hook）", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
