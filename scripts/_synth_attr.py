#!/usr/bin/env python3
"""_synth_attr.py — 收斂檔（synth.md）群集歸戶之**共用**判定模組（VERDICTGATE Task 4.1；SPEC C-1）。

兩個呼叫端、同一實作（TODO v3 Task 4.1 要點 1／5）：
  · scripts/synth_attribution_hook.sh（PostToolUse 寫入當下；「寫入時子集」）
  · scripts/reconcile_cluster_attribution_check.sh（debt_clear 前置閘；全量）

判準（封閉、可證偽）：
  check_ids         附錄每個 `## <ID>` 必出現在群集段某一表列（`|…|`，含佔位列）。
  check_quote20     每個 finding：q = nfc_strip(斷言)[:20]（不足 20 字 ⇒ 全文），須 `q in nfc_strip(" ".join(row.cells))`
                    於某「含該 ID」之非佔位 row（hook 模式只看已完成列＝第 4 欄含處置 token）。
  check_disposition 每個 finding：含該 ID 之**已完成** row（第 4 欄含 disposition_values 之一）才算有處置；
                    `延後→X`：strict_defer=True（debt_clear）⇒ todo_text 非 None 且 X in todo_text，否則錯；
                    strict_defer=False（hook）⇒ 只驗 token 存在、不查目標。
  check_target      session 目錄名含 `-x-` 者必有 `**修訂標的**：<path>` 且檔案存在。
  check_placeholder 附錄已有 ID 而群集段仍含骨架「（待填）」⇒ 錯。
不做：不判定「決議內容是否處理了 finding」（SPEC §N 第三項）。
所有 check 回傳錯誤訊息列表（空＝通過）；比對前 NFC 正規化＋去所有空白，**不**寬容標點差異。

CLI（供 bash 包裝）：
  python3 scripts/_synth_attr.py <synth.md> --mode hook|gate [--todo <TODO.md>] [--values <governance_verdicts.json>] [--report]
  rc=0 通過；rc=1 有錯（逐條印 stderr）；rc=2 用法錯。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import List, Optional

ID_RE = re.compile(r"^## ([A-Z]+-R\d+-P[0-3]-\d{2,})\s*$", re.M)
TARGET_RE = re.compile(r"^\*\*修訂標的\*\*：(\S+)$", re.M)
ASSERT_RE = re.compile(r"\*\*斷言\*\*\s*[:：]\s*(.*)")
PLACEHOLDER = "（待填）"
QUOTE_N = 20


def nfc_strip(s: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", s or ""))


@dataclass
class Finding:
    id: str
    assertion: str


@dataclass
class Row:
    line_no: int
    cells: List[str]
    placeholder: bool


@dataclass
class SynthDoc:
    target: Optional[str]
    rows: List[Row]
    findings: List[Finding]
    session_dir: str
    rel_path: str = ""
    head: str = ""
    warnings: List[str] = field(default_factory=list)


def _id_in(text: str, fid: str) -> bool:
    # B4 R1 composer：尾隨字母（`…-01X`）亦不得誤中
    return re.search(r"(?<![A-Za-z0-9-])" + re.escape(fid) + r"(?![A-Za-z0-9])", text) is not None


# ── 處置 token／延後目標之封閉文法（B4 R1 CODEX-R1-P1-02／GROK-R1-P1-01：子字串比對 fail-open）──
#   token 須為「整詞」：前後不得緊接 CJK／字母／數字（`不採納`≠`採納`；`採納（紀錄）` 可）。
#   `延後→` 後只准**單一**目標，形狀 ∈ {`Task N.N`, 殘留 ID `E-n`／`SU-RESID-n` 等 `[A-Z][A-Z0-9]*(-[A-Z0-9]+)*-\d+`}；
#   目標之後只准空、或以 `（`／`(` 起之說明；`、，；` 接第二目標 ⇒ 錯。存在性＝整詞出現在 TODO 文字。
_CJK = r"一-鿿"
DEFER_TOKEN = "延後→"
DEFER_TARGET_RE = re.compile(r"^(Task \d+\.\d+|[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+)")


def _token_whole(cell: str, tok: str) -> bool:
    if tok == DEFER_TOKEN:
        return DEFER_TOKEN in cell
    return re.search(r"(?<![A-Za-z0-9" + _CJK + r"])" + re.escape(tok) + r"(?![A-Za-z0-9" + _CJK + r"])", cell) is not None


def _target_in_todo(tgt: str, todo_text: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9.\-])" + re.escape(tgt) + r"(?![A-Za-z0-9.])", todo_text) is not None


def parse_defer_targets(cell: str):
    """回傳 [(target|None, err|None), …]，每個 `延後→` 一項。"""
    out = []
    for m in re.finditer(re.escape(DEFER_TOKEN) + r"\s*([^|]*)", cell):
        rest = m.group(1)
        sm = DEFER_TARGET_RE.match(rest)
        if not sm:
            out.append((None, f"`延後→{rest.strip()[:20]}` 目標不合形狀（只准 `Task N.N` 或殘留 ID 如 `E-4`）"))
            continue
        tgt = sm.group(1)
        tail = rest[sm.end():].strip()
        if tail and not tail.startswith(("（", "(")):
            out.append((None, f"`延後→{tgt}` 之後接 `{tail[:10]}`——只准單一目標；說明須以（）括起"))
            continue
        out.append((tgt, None))
    return out


def parse_synth(text: str, rel_path: str) -> SynthDoc:
    head, _, app = text.partition("## 附錄")
    rows: List[Row] = []
    for i, line in enumerate(head.splitlines(), start=1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c or "") for c in cells):
            continue                                   # 表頭分隔列
        placeholder = (PLACEHOLDER in s) or (len(cells) < 4) or (cells[3] == "")
        rows.append(Row(line_no=i, cells=cells, placeholder=placeholder))
    findings: List[Finding] = []
    warnings: List[str] = []
    ids = [m.group(1) for m in ID_RE.finditer(app)]
    for idx, m in enumerate(ID_RE.finditer(app)):
        start = m.end()
        nxt = ID_RE.search(app, start)
        block = app[start: nxt.start() if nxt else len(app)]
        am = ASSERT_RE.search(block)
        assertion = am.group(1).strip() if am else ""
        if not am:
            warnings.append(f"{ids[idx]}: 附錄區塊無 `**斷言**:` 行（引用比對以空字串處理 ⇒ 必不合）")
        findings.append(Finding(id=ids[idx], assertion=assertion))
    tm = TARGET_RE.search(head)
    parts = rel_path.replace("\\", "/").split("/")
    session_dir = parts[2] if len(parts) >= 4 and parts[0] == "handoffs" and parts[1] == "reconcile" else (parts[-2] if len(parts) >= 2 else "")
    return SynthDoc(target=tm.group(1) if tm else None, rows=rows, findings=findings, session_dir=session_dir,
                    rel_path=rel_path, head=head, warnings=warnings)


def rows_for(doc: SynthDoc, fid: str) -> List[Row]:
    return [r for r in doc.rows if _id_in(" ".join(r.cells), fid)]


def check_ids(doc: SynthDoc) -> List[str]:
    miss = [f.id for f in doc.findings if not rows_for(doc, f.id)]
    return [f"① 附錄有 ID 未列入群集表：{', '.join(miss)}"] if miss else []


def _row_done(row: Row, values: List[str]) -> bool:
    if row.placeholder or len(row.cells) < 4:
        return False
    return any(_token_whole(row.cells[3], v) for v in values)


def check_quote20(doc: SynthDoc, *, values: Optional[List[str]] = None, completed_only: bool = False) -> List[str]:
    """completed_only=True（hook）：只對第 4 欄含處置 token 之列驗；無此列 ⇒ 視為草稿不擋。"""
    errs: List[str] = []
    for f in doc.findings:
        q = nfc_strip(f.assertion)[:QUOTE_N]
        cands = [r for r in rows_for(doc, f.id) if not r.placeholder]
        if completed_only:
            cands = [r for r in cands if _row_done(r, values or [])]
        if not cands:
            continue                                   # 無可驗之列：check_ids／check_disposition 另報
        if not any(q in nfc_strip(" ".join(r.cells)) for r in cands):
            errs.append(f"② {f.id} 之群集列未逐字引用斷言前 {QUOTE_N} 字「{q}」（列 {', '.join(str(r.line_no) for r in cands)}）")
    return errs


def check_disposition(doc: SynthDoc, values: List[str], todo_text: Optional[str], *, strict_defer: bool) -> List[str]:
    errs: List[str] = []
    for f in doc.findings:
        rows = rows_for(doc, f.id)
        if not rows:
            continue                                   # check_ids 另報
        done = [r for r in rows if _row_done(r, values)]
        if not done:
            errs.append(f"③ {f.id} 之群集列第 4 欄無處置 token（{' | '.join(values)}）（列 {', '.join(str(r.line_no) for r in rows)}）")
            continue
        for r in done:
            # 形狀與單一性兩模式皆驗（hook 也擋）；存在性只在 strict_defer（debt_clear）驗。
            for tgt, err in parse_defer_targets(r.cells[3]):
                if err:
                    errs.append(f"④ {f.id} 列 {r.line_no}：{err}")
                elif strict_defer:
                    if todo_text is None:
                        errs.append(f"④ {f.id} 列 {r.line_no}：`延後→{tgt}` 但未提供 --todo，無法驗目標存在")
                    elif not _target_in_todo(tgt, todo_text):
                        errs.append(f"④ {f.id} 列 {r.line_no}：`延後→{tgt}` 之目標不存在於 TODO 檔（整詞比對）")
    return errs


def check_target(doc: SynthDoc) -> List[str]:
    if "-x-" not in doc.session_dir:
        return []
    if not doc.target:
        return ["⑤ -x- 層 synth 未宣告修訂標的（**修訂標的**：docs/<檔>.md）"]
    if "<填" in doc.target or not os.path.isfile(doc.target):
        return [f"⑤ 修訂標的未填或不存在：{doc.target}"]
    return []


def check_placeholder(doc: SynthDoc) -> List[str]:
    if doc.findings and PLACEHOLDER in doc.head:
        return [f"⑥ 群集段仍是骨架佔位「{PLACEHOLDER}」"]
    return []


def load_values(path: str) -> List[str]:
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    vals = d.get("disposition_values")
    if not isinstance(vals, list) or not vals or not all(isinstance(v, str) and v for v in vals):
        raise ValueError(f"{path}: disposition_values 缺失或不合法")
    return vals


def run(doc: SynthDoc, mode: str, values: List[str], todo_text: Optional[str]) -> List[str]:
    errs = check_ids(doc) + check_target(doc)
    if mode == "hook":
        errs += check_disposition(doc, values, None, strict_defer=False)
        errs += check_quote20(doc, values=values, completed_only=True)
    elif mode == "gate":
        errs += check_disposition(doc, values, todo_text, strict_defer=True)
        errs += check_quote20(doc, values=values, completed_only=False)
    else:
        raise ValueError(mode)
    if not errs:
        errs += check_placeholder(doc)
    return errs


def report(doc: SynthDoc, out=sys.stdout) -> None:
    for f in doc.findings:
        rows = rows_for(doc, f.id)
        q = nfc_strip(f.assertion)[:QUOTE_N]
        print(f"── {f.id}", file=out)
        print(f"   斷言前{QUOTE_N}字: {q or '（找不到）'}", file=out)
        if rows:
            r = rows[0]
            print(f"   群集引用: {r.line_no}: {' | '.join(r.cells)[:60]}", file=out)
        else:
            print("   群集引用: ⚠️ 未被任何群集引用（掉項？）", file=out)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("synth")
    ap.add_argument("--mode", choices=("hook", "gate"), required=True)
    ap.add_argument("--todo")
    ap.add_argument("--values", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "governance_verdicts.json"))
    ap.add_argument("--report", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        return 2
    try:
        text = open(a.synth, encoding="utf-8").read()
        values = load_values(a.values)
    except (OSError, ValueError) as exc:
        print(f"[_synth_attr] ERROR: {exc}", file=sys.stderr)
        return 2
    todo_text = None
    if a.todo:
        try:
            todo_text = open(a.todo, encoding="utf-8").read()
        except OSError as exc:
            print(f"[_synth_attr] ERROR: --todo 讀取失敗: {exc}", file=sys.stderr)
            return 2
    rel = os.path.relpath(a.synth) if not a.synth.startswith("handoffs/") else a.synth
    doc = parse_synth(text, rel)
    if a.report:
        report(doc)
    errs = run(doc, a.mode, values, todo_text)
    for w in doc.warnings:
        print(f"[_synth_attr] ⚠ {w}", file=sys.stderr)
    if errs:
        print(f"[_synth_attr] 🔴 {rel}（mode={a.mode}）", file=sys.stderr)
        for e in errs:
            print("   " + e, file=sys.stderr)
        print(f"   findings={len(doc.findings)}；rows={len(doc.rows)}", file=sys.stderr)
        return 1
    print(f"[_synth_attr] ✓ {rel}（mode={a.mode}）findings={len(doc.findings)} 全在群集表、引用與處置合規")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
