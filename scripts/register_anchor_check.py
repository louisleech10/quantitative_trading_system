# -*- coding: utf-8 -*-
"""SPLITUNIFY `D-002-C5` register 之碼證錨點閘（可重跑、非一次性）。

**為什麼存在**：register 每列所載的 `path:line` 是 `Task 9.3` 施工與 receipt 對證的唯一依據。
這道閘**連續四代被打穿**，每一代都曾被當成已閉合，逐條寫明是因為下一代只會更隱蔽：

1. v15「行號 ≤ 該檔總行數」——四列全指註解卻照樣綠（R31 三家撞題）。
2. R31 委員修法「statement／AST overlap」——主委實跑量測，只殺掉四處中的**兩處**。
3. v26 主委的「行**範圍** ＋ 單一 token **子字串**」——R32 codex 實跑打穿：
   `split_projection.py:341`（`raise` 的**訊息字串**）與 `:566` 都命中同一 token。
4. v27 主委的「單一行 ＋ token **子序列**（可跳過）」——R33 codex 三條實跑打穿：
   ①子序列可跳 token ⇒ `columns = ["timeframe"]; emit("feature_timeframe")` 這種
   **語義替身**也會綠；②`_ordered_subsequence_count` 的貪婪不重疊計數漏算重疊命中
   （`hay=abab a`／`needle=aba` 應為 2 卻回 1）⇒「恰好一次」不對所有序列成立；
   ③`.tsx` 只在指定行數 literal、不驗檔內唯一性 ⇒ 同 literal 的 decoy 行可冒充。

⇒ **現行判準（v28；逐字採 `CODEX-R33-P1-01`／`P1-02`／`P1-03` 修法）**：

* 每個錨點是**單一精確行**。
* `.py`：該行之**正規化完整 token 序列**須與 register 所載序列**逐一相等**（不是子序列、
  不是子字串）；且該序列在**整個檔案**中須恰好出現在**一行**上；並以 AST 確認該行落在
  非純字串常數之 statement 上。
* `.tsx`／`.ts`：無 AST ⇒ 以**正規化完整行文字**相等，且該正規化行在
  **全 repo 之 `.ts`／`.tsx`** 中恰好一次（R34 起由單檔擴到全域；跳過建置產物目錄，見 `_TS_SKIP_DIRS`）。
* 任何「0 次或多於 1 次」皆拒絕。

🔴 本檔**不是**新的治理機制，是 SPLITUNIFY epic 之 `Task 9.3` 驗收器；
   由 `tests/momentum/Analysis/test_splitunify_contract.py` 每次回歸跑一次，
   所以 register 行號日後再漂、或本閘被放寬回任何一代舊形狀，都會**當場轉紅**。
"""
from __future__ import annotations

import ast
import hashlib
import io
import re
import sys
import token as token_mod
import tokenize
from pathlib import Path
from typing import List, NamedTuple, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "docs" / "SPLITUNIFY_SPEC.D-002.md"

# register 列之機器可讀錨點子句。逐字格式（反引號為分隔符）：
#   ANCHOR `<path>:<line>` TOKENS `<t1>` `<t2>` ...
# 🔴 TOKENS 須為該行之**完整**正規化 token 序列（`.tsx` 為完整正規化行文字，單一項）。
_ANCHOR_RE = re.compile(r"ANCHOR\s+`([^`]+):(\d+)`\s+TOKENS((?:\s+`[^`]+`)+)")
# 🔴 `.tsx` 的行本身含反引號（template literal），無法塞進反引號分隔的 TOKENS ⇒
#    改用正規化整行之 sha256。仍是「整行相等 ＋ 全 repo 之 .ts／.tsx 恰好一次」，不是子字串。
_ANCHOR_SHA_RE = re.compile(r"ANCHOR\s+`([^`]+):(\d+)`\s+LINESHA256\s+`([0-9a-f]{64})`")
_TOKEN_RE = re.compile(r"`([^`]+)`")
_ROW_ID_RE = re.compile(r"^\|\s*`(C5-\d+)`\s*\|")
_SHA_PREFIX = "sha256:"

_SKIP_TOK = {
    token_mod.COMMENT, token_mod.NL, token_mod.NEWLINE,
    token_mod.INDENT, token_mod.DEDENT, token_mod.ENCODING,
    token_mod.ENDMARKER,
}


class Anchor(NamedTuple):
    row_id: str
    path: str
    line: int
    tokens: Tuple[str, ...]


def parse_anchors(spec_text: str) -> List[Anchor]:
    """從 register 表逐列抽出 ANCHOR 子句（一列可有多個）。"""
    out: List[Anchor] = []
    for raw in spec_text.splitlines():
        m_id = _ROW_ID_RE.match(raw)
        if not m_id:
            continue
        row_id = m_id.group(1)
        for m in _ANCHOR_SHA_RE.finditer(raw):
            out.append(
                Anchor(row_id, m.group(1), int(m.group(2)), (_SHA_PREFIX + m.group(3),))
            )
        for m in _ANCHOR_RE.finditer(raw):
            toks = tuple(_TOKEN_RE.findall(m.group(3)))
            out.append(Anchor(row_id, m.group(1), int(m.group(2)), toks))
    return out


def py_line_spans_multiline_token(src: str, line: int) -> bool:
    """該行是否被某個**跨行 token**（多行字串等）覆蓋。

    🔴 R34 `CODEX-R34-P1-01`：舊版以 `start[0] <= line <= end[0]` 收 token，
    多行字串的**中間行**會拿到整個字串 token ⇒ 兩個相鄰行得到相同序列、
    或某行的序列含不屬於它的 token。跨行 token 覆蓋者一律 fail-closed。
    """
    for tk in tokenize.generate_tokens(io.StringIO(src).readline):
        if tk.type in _SKIP_TOK:
            continue
        if tk.start[0] != tk.end[0] and tk.start[0] <= line <= tk.end[0]:
            return True
    return False


def py_line_token_seq(src: str, line: int) -> Tuple[str, ...]:
    """該行之正規化完整 token 序列（只收**起訖都在該行**的 token）。"""
    vals: List[str] = []
    for tk in tokenize.generate_tokens(io.StringIO(src).readline):
        if tk.type in _SKIP_TOK:
            continue
        if tk.start[0] == tk.end[0] == line:
            vals.append(tk.string)
    return tuple(vals)


def _py_all_line_seqs(src: str) -> List[Tuple[str, ...]]:
    """逐行之正規化 token 序列（1-based；index 0 為佔位）。只收單行 token。"""
    n = len(src.splitlines())
    per_line: List[List[str]] = [[] for _ in range(n + 1)]
    for tk in tokenize.generate_tokens(io.StringIO(src).readline):
        if tk.type in _SKIP_TOK:
            continue
        if tk.start[0] == tk.end[0] and 1 <= tk.start[0] <= n:
            per_line[tk.start[0]].append(tk.string)
    return [tuple(x) for x in per_line]


def _py_line_is_executable(src: str, line: int) -> bool:
    """該行須落在**非純字串常數**之 statement 上（排除 docstring 與純註解行）。"""
    tree = ast.parse(src)
    doc_lines = set()
    for n in ast.walk(tree):
        if (
            isinstance(n, ast.Expr)
            and isinstance(getattr(n, "value", None), ast.Constant)
            and isinstance(n.value.value, str)
        ):
            doc_lines.update(range(n.lineno, getattr(n, "end_lineno", n.lineno) + 1))
    if line in doc_lines:
        return False
    for n in ast.walk(tree):
        if isinstance(n, ast.stmt) and n.lineno <= line <= getattr(n, "end_lineno", n.lineno):
            return True
    return False


_TS_SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", "coverage"}


def _repo_ts_files() -> List[Path]:
    """repo 內全部 `.ts`／`.tsx`（跳過建置產物目錄）。"""
    root = REPO_ROOT.resolve()
    out: List[Path] = []
    for suffix in ("*.ts", "*.tsx"):
        for f in root.rglob(suffix):
            if _TS_SKIP_DIRS & set(f.relative_to(root).parts):
                continue
            out.append(f)
    return out


def _normalize_text_line(s: str) -> str:
    """`.tsx`／`.ts` 用：壓掉前後與連續空白，其餘逐字保留。"""
    return re.sub(r"\s+", " ", s).strip()


def _resolve_in_repo(rel: str) -> Tuple[Path, str]:
    """把 register 所載路徑解析成 repo 內之實檔；越界一律 fail-closed。

    🔴 R34 `CODEX-R34-P1-02`：舊版直接 `REPO_ROOT / anchor.path`，而 `Path / 絕對路徑`
    會**丟掉前綴** ⇒ 錨點可指向 repo 外任何可讀檔。現行拒絕絕對路徑與 `..`，
    並以 `resolve()` 後確認仍在 `REPO_ROOT` 之下。
    """
    if rel.startswith("/") or Path(rel).is_absolute():
        return Path(rel), "路徑須為 repo 相對路徑（拒絕絕對路徑）"
    if ".." in Path(rel).parts:
        return Path(rel), "路徑不得含 `..`"
    root = REPO_ROOT.resolve()
    p = (root / rel).resolve()
    try:
        p.relative_to(root)
    except ValueError:
        return p, f"路徑解析後落在 repo 之外：{p}"
    return p, ""


def check_anchor(anchor: Anchor) -> Tuple[bool, str]:
    p, why = _resolve_in_repo(anchor.path)
    if why:
        return False, why
    if not p.is_file():
        return False, f"檔不存在：{anchor.path}"
    # 🔴 R35 `CODEX-R35-P2-01`：非 UTF-8／語法壞掉的標的檔，舊版會直接把例外往外丟
    #   （整支 checker crash），而不是回一則乾淨的 ANCHOR_FAIL。載入邊界統一捕捉。
    try:
        src = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"標的檔讀不進來（{type(exc).__name__}）：{exc}"
    lines = src.splitlines()
    if not (1 <= anchor.line <= len(lines)):
        return False, f"行號超出範圍：{anchor.line} > {len(lines)}"

    if p.suffix == ".py":
        try:
            spans = py_line_spans_multiline_token(src, anchor.line)
            executable = _py_line_is_executable(src, anchor.line)
            actual = py_line_token_seq(src, anchor.line)
            all_seqs = _py_all_line_seqs(src)
        except (SyntaxError, IndentationError, tokenize.TokenError, ValueError) as exc:
            return False, f"標的檔無法 tokenize／parse（{type(exc).__name__}）：{exc}"
        if spans:
            return False, f"{anchor.line} 落在**跨行 token**（多行字串等）之內——fail-closed"
        if not executable:
            return False, f"{anchor.line} 不在可執行 statement 上（註解／空行／docstring）"
        if actual != anchor.tokens:
            return False, (
                "token 序列不相等（須逐一相等，非子序列）\n"
                f"      register: {list(anchor.tokens)}\n"
                f"      實際:     {list(actual)}"
            )
        hits = [i for i, s in enumerate(all_seqs) if i >= 1 and s == actual]
        if len(hits) != 1:
            return False, f"該 token 序列在本檔出現 {len(hits)} 次（行 {hits}）——須恰好一次"
        return True, f"{anchor.line} n_tokens={len(actual)}"

    # .tsx／.ts：無 AST ⇒ 正規化**完整行**相等 ＋ 先驗同檔唯一、再驗**全 repo** 唯一（具名誠實邊界）
    if len(anchor.tokens) != 1:
        return False, "非 .py 之錨點須恰好一項（LINESHA256 或正規化完整行文字）"
    spec_item = anchor.tokens[0]
    got_norm = _normalize_text_line(lines[anchor.line - 1])
    if spec_item.startswith(_SHA_PREFIX):
        want_sha = spec_item[len(_SHA_PREFIX):]
        got_sha = hashlib.sha256(got_norm.encode("utf-8")).hexdigest()
        if got_sha != want_sha:
            return False, (
                "正規化整行之 sha256 不相等\n"
                f"      register: {want_sha}\n"
                f"      實際:     {got_sha}  ← 該行現為 {got_norm!r}"
            )
        hits = [
            i + 1 for i, ln in enumerate(lines)
            if hashlib.sha256(_normalize_text_line(ln).encode("utf-8")).hexdigest() == want_sha
        ]
    else:
        want = _normalize_text_line(spec_item)
        if got_norm != want:
            return False, f"正規化行文字不相等\n      register: {want!r}\n      實際:     {got_norm!r}"
        hits = [i + 1 for i, ln in enumerate(lines) if _normalize_text_line(ln) == want]
    if len(hits) != 1:
        return False, f"該正規化行在本檔出現 {len(hits)} 次（行 {hits}）——須恰好一次"
    # 🔴 R34 `CODEX-R34-P1-01`：只驗單檔唯一性 ⇒ 把整行搬到 `old.tsx`／`new.tsx` 兩個檔、
    #   register 指舊檔，本閘看不出來。⇒ 唯一性擴到**全 repo 之 .ts／.tsx**。
    want_sha = (
        spec_item[len(_SHA_PREFIX):] if spec_item.startswith(_SHA_PREFIX)
        else hashlib.sha256(_normalize_text_line(spec_item).encode("utf-8")).hexdigest()
    )
    global_hits: List[str] = []
    for other in sorted(_repo_ts_files()):
        try:
            other_lines = other.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for i, ln in enumerate(other_lines):
            if hashlib.sha256(_normalize_text_line(ln).encode("utf-8")).hexdigest() == want_sha:
                global_hits.append(f"{other.relative_to(REPO_ROOT.resolve())}:{i + 1}")
    if len(global_hits) != 1:
        return False, (
            f"該正規化行在全 repo 之 .ts／.tsx 出現 {len(global_hits)} 次"
            f"（{global_hits[:5]}）——須恰好一次"
        )
    return True, f"{anchor.line} whole-line（repo 內唯一）"


def main(argv: List[str]) -> int:
    if len(argv) >= 4:
        # 單點模式（供 must-fail 回歸與人工複核）：<path> <line> <tok...>
        a = Anchor("(ad-hoc)", argv[1], int(argv[2]), tuple(argv[3:]))
        ok, why = check_anchor(a)
        print(f"{a.path}:{a.line} -> {'ANCHOR_OK' if ok else 'ANCHOR_FAIL'} {why}")
        return 0 if ok else 1
    if len(argv) == 3 and argv[1] == "--emit":
        # 產生某行之 register 子句內容，供貼回 SPEC（避免手抄）
        path, line = argv[2].rsplit(":", 1)
        p = REPO_ROOT / path
        if p.suffix == ".py":
            seq = py_line_token_seq(p.read_text(encoding="utf-8"), int(line))
            print(" ".join("`%s`" % t for t in seq))
        else:
            norm = _normalize_text_line(p.read_text(encoding="utf-8").splitlines()[int(line) - 1])
            print(hashlib.sha256(norm.encode("utf-8")).hexdigest())
        return 0

    anchors = parse_anchors(SPEC_PATH.read_text(encoding="utf-8"))
    if not anchors:
        print("ANCHOR_FAIL: register 表未解析到任何 ANCHOR 子句", file=sys.stderr)
        return 1
    rc = 0
    for a in anchors:
        ok, why = check_anchor(a)
        print(f"{a.row_id:<7} {a.path}:{a.line} {'OK  ' if ok else 'FAIL'} {why}")
        if not ok:
            rc = 1
    print(f"— 共 {len(anchors)} 個錨點，{'全數通過' if rc == 0 else '有失敗'}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
