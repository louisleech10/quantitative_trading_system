# -*- coding: utf-8 -*-
"""SPLITUNIFY `D-002-C5` register 之碼證錨點閘（可重跑、非一次性）。

**為什麼存在**（R32 `CODEX-R32-P1-01`）：register 每列所載的 `path:line` 是 `Task 9.3`
施工與 receipt 對證的唯一依據。歷來三道閘依序被打穿：

1. v15「行號 ≤ 該檔總行數」——`C5-19`／`C5-21`／`C5-26`／`C5-27` 四列全指註解卻照樣綠（R31 三家撞題）。
2. R31 委員修法「statement／AST overlap」——主委實跑量測，只殺掉四處中的**兩處**；
   指向「真實但錯誤的碼」的三處照樣綠。
3. 主委加的「行範圍 ＋ 單一 token 子字串」——R32 codex 實跑打穿：
   `split_projection.py:341`（錯誤訊息**字串**裡的 `feature_timeframe`）與
   `:566`（另一道重複閘）都能命中同一個 token。

⇒ 現行判準（逐字採 `CODEX-R32-P1-01` 修法）：

* 每個錨點是**單一精確行**，不是行範圍。
* `.py`：該行以 `tokenize` 取出 token 串後，register 所載之 **token 序列**須在其中
  **依序出現且恰好一次**；並以 AST 確認該行落在可執行 statement 上（純 docstring 不算）。
* `.tsx`／`.ts`：無 AST，改以**精確 literal** 在該行出現且恰好一次（具名誠實邊界）。
* **0 次或多次命中皆拒絕**。

🔴 本檔**不是**新的治理機制，是 SPLITUNIFY epic 之 `Task 9.3` 驗收器；
   由 `tests/momentum/Analysis/test_splitunify_register_anchors.py` 每次回歸跑一次，
   所以 register 行號日後再漂會**當場轉紅**，不再是「驗收當下跑一次」。
"""
from __future__ import annotations

import ast
import io
import re
import sys
import token as token_mod
import tokenize
from pathlib import Path
from typing import List, NamedTuple, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = REPO_ROOT / "docs" / "SPLITUNIFY_SPEC.D-002.md"

# register 列之機器可讀錨點子句。逐字格式（反引號為分隔符，勿加空白以外的字元）：
#   ANCHOR `<path>:<line>` TOKENS `<t1>` `<t2>` ...
_ANCHOR_RE = re.compile(
    r"ANCHOR\s+`([^`]+):(\d+)`\s+TOKENS((?:\s+`[^`]+`)+)"
)
_TOKEN_RE = re.compile(r"`([^`]+)`")
_ROW_ID_RE = re.compile(r"^\|\s*`(C5-\d+)`\s*\|")


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
        for m in _ANCHOR_RE.finditer(raw):
            toks = tuple(_TOKEN_RE.findall(m.group(3)))
            out.append(Anchor(row_id, m.group(1), int(m.group(2)), toks))
    return out


def _py_line_tokens(src: str, line: int) -> List[str]:
    """該行之 token 字面串（不含註解、換行、縮排等結構 token）。"""
    skip = {
        token_mod.COMMENT, token_mod.NL, token_mod.NEWLINE,
        token_mod.INDENT, token_mod.DEDENT, token_mod.ENCODING,
        token_mod.ENDMARKER,
    }
    vals: List[str] = []
    for tk in tokenize.generate_tokens(io.StringIO(src).readline):
        if tk.type in skip:
            continue
        if tk.start[0] <= line <= tk.end[0]:
            vals.append(tk.string)
    return vals


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
        if isinstance(n, ast.stmt):
            if n.lineno <= line <= getattr(n, "end_lineno", n.lineno):
                return True
    return False


def _ordered_subsequence_count(hay: Sequence[str], needle: Sequence[str]) -> int:
    """`needle` 以**依序（可不相鄰）**方式出現在 `hay` 的次數（貪婪不重疊計數）。"""
    if not needle:
        return 0
    count = 0
    i = 0
    while i < len(hay):
        j = 0
        k = i
        while k < len(hay) and j < len(needle):
            if hay[k] == needle[j]:
                j += 1
            k += 1
        if j == len(needle):
            count += 1
            i = k
        else:
            break
    return count


def check_anchor(anchor: Anchor) -> Tuple[bool, str]:
    p = REPO_ROOT / anchor.path
    if not p.is_file():
        return False, f"檔不存在：{anchor.path}"
    src = p.read_text(encoding="utf-8")
    lines = src.splitlines()
    if not (1 <= anchor.line <= len(lines)):
        return False, f"行號超出範圍：{anchor.line} > {len(lines)}"

    if p.suffix == ".py":
        if not _py_line_is_executable(src, anchor.line):
            return False, f"{anchor.line} 不在可執行 statement 上（註解／空行／docstring）"
        vals = _py_line_tokens(src, anchor.line)
        n = _ordered_subsequence_count(vals, anchor.tokens)
        if n == 0:
            return False, f"token 序列未在 {anchor.line} 出現：{list(anchor.tokens)}"
        if n > 1:
            return False, f"token 序列在 {anchor.line} 出現 {n} 次（多重命中即拒）"
        return True, f"{anchor.line} tokens={list(anchor.tokens)}"

    # .tsx／.ts：無 AST，精確 literal（具名誠實邊界，見模組 docstring）
    text = lines[anchor.line - 1]
    for t in anchor.tokens:
        c = text.count(t)
        if c == 0:
            return False, f"literal 未在 {anchor.line} 出現：{t!r}"
        if c > 1:
            return False, f"literal 在 {anchor.line} 出現 {c} 次（多重命中即拒）：{t!r}"
    return True, f"{anchor.line} literal={list(anchor.tokens)}"


def main(argv: List[str]) -> int:
    if len(argv) >= 4:
        # 單點模式（供 must-fail 回歸與人工複核）：<path> <line> <tok...>
        a = Anchor("(ad-hoc)", argv[1], int(argv[2]), tuple(argv[3:]))
        ok, why = check_anchor(a)
        print(f"{a.path}:{a.line} -> {'ANCHOR_OK' if ok else 'ANCHOR_FAIL'} {why}")
        return 0 if ok else 1

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
