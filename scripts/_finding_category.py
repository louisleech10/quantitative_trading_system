#!/usr/bin/env python3
"""_finding_category.py — DOCROT2 Task 3.1（票 B-63）：finding 類別之值集、適用門檻與類別行解析之唯一實作。

呼叫端（不得另寫判定）：
  · scripts/completeness_check.sh --single  →  CLI `check-single`（是否須類別＋逐 finding 類別行判定）
  · scripts/_synth_attr.py::check_category   →  import（收斂檔主委欄與委員欄）
  · scripts/_docrot2_metrics.py              →  import（收案量測事件之類別計數、嚴格 audit 讀取）

判定（封閉、只讀 audit 序號，不讀日期與 mtime）：
  category_required(round_id)
    round_id 為 None                                ⇒ 須類別（fail-closed）
    audit 中該 round 之 committee_round_open 恰一筆且 sequence 為整數
       ⇒ sequence > category_required_after_audit_sequence 才須類別
    查無、多筆、sequence 非整數                      ⇒ 須類別（嚴側）
    audit 登記檔或 audit 不可讀、audit 含壞 JSON 列   ⇒ ConfigError（呼叫端 FAIL，不降級）
  值集與門檻只定義於 scripts/governance_verdicts.json；缺鍵或型別不符 ⇒ ConfigError（呼叫端 fail-closed）。
  類別行文法之唯一實作＝本檔 `_Scanner`（見其上方註解）。

CLI：
  python3 scripts/_finding_category.py required [--round-id <rid>] [--values <json>]   stdout 1｜0；rc 0，設定錯 rc 2
  python3 scripts/_finding_category.py values [--values <json>]                         stdout 每行一值；rc 0／2
  python3 scripts/_finding_category.py check-single <file> [--round-id <rid>]           completeness_check.sh --single 之類別閘；rc 0／1
"""
from __future__ import annotations

import json
import os
import re
import sys
from typing import List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VALUES = os.path.join(HERE, "governance_verdicts.json")
AUDIT_REGISTRY = os.path.join(HERE, "audit_events.json")
LABEL = "**類別**"
# 類別行值文法：標籤後接可選空白（只認半形空白與 tab）、可選半形／全形冒號、可選空白，值與標籤同行，
# 去頭尾半形空白與 tab 後須逐字等於封閉值之一（行尾 CR 由 _Scanner 先去除）
_LABEL_RE = re.compile(r"\*\*類別\*\*[ \t]*[:：]?[ \t]*(.*)$")
# 值形狀封閉：值為委員交件與群集表欄位之字面，不得含空白或表格分隔字元
_VALUE_SHAPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


class ConfigError(Exception):
    """governance_verdicts.json 或 audit 登記檔不可用。"""


def load_config(values_path: str = DEFAULT_VALUES) -> Tuple[List[str], int]:
    try:
        with open(values_path, encoding="utf-8") as fh:
            d = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{values_path} 讀取失敗：{exc}")
    vals = d.get("finding_category_values")
    thr = d.get("category_required_after_audit_sequence")
    if (not isinstance(vals, list) or not vals or not all(isinstance(v, str) and _VALUE_SHAPE.match(v) for v in vals)
            or len(set(vals)) != len(vals)):
        raise ConfigError(f"{values_path}: finding_category_values 缺失或不合法（須為非空、不重複、形如 [A-Za-z0-9_-] 之字串陣列）")
    if not isinstance(thr, int) or isinstance(thr, bool) or thr < 0:
        raise ConfigError(f"{values_path}: category_required_after_audit_sequence 缺失或非非負整數")
    return list(vals), thr


def resolve_audit_path() -> str:
    """與 audit_append.sh 同契約：DEBT_AUDIT_OVERRIDE 只在 GOVERNANCE_TEST_HARNESS=1 生效。"""
    ov = os.environ.get("DEBT_AUDIT_OVERRIDE")
    if ov:
        if os.environ.get("GOVERNANCE_TEST_HARNESS") != "1":
            raise ConfigError("DEBT_AUDIT_OVERRIDE 須綁 GOVERNANCE_TEST_HARNESS=1")
        return ov
    try:
        with open(AUDIT_REGISTRY, encoding="utf-8") as fh:
            rel = json.load(fh).get("audit_log_path")
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{AUDIT_REGISTRY} 讀取失敗：{exc}")
    if not isinstance(rel, str) or not rel:
        raise ConfigError(f"{AUDIT_REGISTRY} 缺 audit_log_path")
    return os.path.join(os.path.dirname(HERE), rel)


def iter_audit(audit_path: str):
    """嚴格讀取（review-r1 `CODEX-R1-P1-02`）：以 `{` 起首而無法解析或非物件之行 ⇒ ConfigError；讀不到 ⇒ ConfigError。
    與 audit_append.sh／debt_ledger 之 fail-closed 一致——前置壞列可藏住開債事件，不得略過。"""
    try:
        fh = open(audit_path, encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"audit 讀取失敗：{exc}")
    with fh:
        for n, raw in enumerate(fh, 1):
            s = raw.strip()
            if not s.startswith("{"):
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError as exc:
                raise ConfigError(f"audit 第 {n} 行 JSON 無法解析：{exc}")
            if not isinstance(rec, dict):
                raise ConfigError(f"audit 第 {n} 行非 JSON 物件")
            yield rec


def round_open_records(audit_path: str, round_id: str) -> List[dict]:
    return [r for r in iter_audit(audit_path)
            if r.get("event") == "committee_round_open" and r.get("round_id") == round_id]


def round_open_sequence(audit_path: str, round_id: str) -> Optional[int]:
    """恰一筆且 sequence 為整數 ⇒ 回序號；查無、多筆、序號非整數 ⇒ None（呼叫端視為須類別）。audit 不可讀 ⇒ ConfigError。"""
    recs = round_open_records(audit_path, round_id)
    if len(recs) != 1:
        return None
    seq = recs[0].get("sequence")
    if isinstance(seq, int) and not isinstance(seq, bool):
        return seq
    return None


def category_required(round_id: Optional[str], values_path: str = DEFAULT_VALUES,
                      audit_path: Optional[str] = None) -> bool:
    """未給 round id ⇒ True。給了 round id 而 audit 登記檔／audit 不可用 ⇒ ConfigError（呼叫端 FAIL，不降級為「須類別」）。"""
    _vals, thr = load_config(values_path)
    if not round_id:
        return True
    if audit_path is None:
        audit_path = resolve_audit_path()
    seq = round_open_sequence(audit_path, round_id)
    if seq is None:
        return True
    return seq > thr


# ── 類別行之單一文法（review-r1 `CODEX-R1-P1-01`／`COMPOSER-R1-P2-01`）────────────────────────────
#   completeness_check.sh --single（check-single）與收斂檔／量測（single_category）共用本段，不另寫第二份。
#   ① 行尾 CR 去除；② fence 標記＝行首 ASCII 空白（與 awk LC_ALL=C 之 [[:space:]] 同）後接 ``` 或 ~~~，
#     U+3000 等非 ASCII 空白不算；③ `<!-- … -->` 註解（可跨行，未閉合則至掃描尾）內之文字不算類別行；
#   ④ 標題行（finding 邊界）以原始行判定，與 completeness_check.sh 之 heading 規則同（註解與 fence 不影響邊界）。
_FENCE_RE = re.compile(r"^[ \t\v\f\r]*(```|~~~)")
_HEADING_RE = re.compile(r"^[ \t\v\f\r]*#{2,6}[ \t\v\f\r]")
_HEADING_PREFIX_RE = re.compile(r"^[ \t\v\f\r]*#{2,6}[ \t\v\f\r]+")
_CANON_RE = re.compile(r"^[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}$")


class _Scanner:
    def __init__(self) -> None:
        self.in_fence = False
        self.in_comment = False

    def strip_comments(self, ln: str) -> str:
        out, i = [], 0
        while i < len(ln):
            if self.in_comment:
                j = ln.find("-->", i)
                if j < 0:
                    return "".join(out)
                self.in_comment = False
                i = j + 3
            else:
                j = ln.find("<!--", i)
                if j < 0:
                    out.append(ln[i:])
                    break
                out.append(ln[i:j])
                self.in_comment = True
                i = j + 4
        return "".join(out)

    def category_value(self, raw: str) -> Optional[str]:
        """此行若為（fence 與註解外之）類別行 ⇒ 回其值（可能為空字串＝不合法）；否則 None。"""
        ln = self.strip_comments(raw.rstrip("\r"))
        if _FENCE_RE.match(ln):
            self.in_fence = not self.in_fence
            return None
        if self.in_fence or LABEL not in ln:
            return None
        if ln.count(LABEL) > 1:
            return ""
        m = _LABEL_RE.search(ln)
        return m.group(1).strip(" \t") if m else ""


def parse_category_lines(lines: List[str]) -> List[str]:
    """一段區塊內之全部類別行之值（單一文法見上）；同行重複標籤之行值記為空字串。"""
    sc = _Scanner()
    out: List[str] = []
    for ln in lines:
        v = sc.category_value(ln)
        if v is not None:
            out.append(v)
    return out


def _heading_token(raw: str) -> Optional[str]:
    if not _HEADING_RE.match(raw):
        return None
    body = _HEADING_PREFIX_RE.sub("", raw, count=1)
    parts = re.split(r"[ \t\v\f\r]+", body.strip(" \t\v\f\r"))
    tok = parts[0] if parts and parts[0] else ""
    return re.sub(r"[^A-Za-z0-9_-].*$", "", tok)


def finding_categories(text: str) -> List[Tuple[str, List[str]]]:
    """交件檔逐 finding 之類別值：finding 自 canonical 標題起、至下一個任意標題止；fence 與註解狀態全檔延續。"""
    sc = _Scanner()
    out: List[Tuple[str, List[str]]] = []
    cur: Optional[Tuple[str, List[str]]] = None
    for raw in text.split("\n"):
        tok = _heading_token(raw)
        if tok is not None:
            cur = (tok, []) if _CANON_RE.match(tok) else None
            if cur is not None:
                out.append(cur)
            continue
        v = sc.category_value(raw)
        if cur is not None and v is not None:
            cur[1].append(v)
    return out


def single_category(lines: List[str], values: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """回 (值, 錯誤)：恰一行 `**類別**` 且值 ∈ values 才有值。"""
    got = parse_category_lines(lines)
    if not got:
        return None, "缺 `**類別**: <值>` 行"
    if len(got) > 1:
        return None, f"`**類別**` 行出現 {len(got)} 次（須恰一次）"
    if got[0] not in values:
        return None, f"類別「{got[0]}」不在封閉值集 {values}"
    return got[0], None


def check_single(path: str, round_id: Optional[str], values_path: str = DEFAULT_VALUES) -> int:
    """completeness_check.sh --single 之類別閘：須類別時每條 finding（含 sentinel）恰一行合法類別。rc 0／1。
    訊息格式與 cx_run.sh 逐條可修補清單相容（`COMPLETENESS FAIL: <類型>: <ID> (file=…)`）。"""
    try:
        cats, _thr = load_config(values_path)
        required = category_required(round_id, values_path)
    except ConfigError as exc:
        print(f"COMPLETENESS FAIL: 類別判定設定不可用 ⇒ fail-closed：{exc} (file={path})", file=sys.stderr)
        return 1
    if not required:
        return 0
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            text = fh.read()
    except (OSError, UnicodeDecodeError) as exc:
        print(f"COMPLETENESS FAIL: 類別判定讀檔失敗：{exc} (file={path})", file=sys.stderr)
        return 1
    bad = 0
    for fid, got in finding_categories(text):
        if not got:
            print(f"COMPLETENESS FAIL: finding 缺類別（**類別**: <值>，值集見 governance_verdicts.json.finding_category_values）: {fid} (file={path})", file=sys.stderr)
            bad = 1
        elif len(got) > 1:
            print(f"COMPLETENESS FAIL: finding 類別行重複（須恰一行 **類別**）: {fid} (file={path})", file=sys.stderr)
            bad = 1
        elif got[0] not in cats:
            print(f"COMPLETENESS FAIL: finding 類別不在封閉值集（得「{got[0]}」）: {fid} (file={path})", file=sys.stderr)
            bad = 1
    return bad


def main(argv: List[str]) -> int:
    if not argv or argv[0] not in ("required", "values", "check-single"):
        print("用法: _finding_category.py required [--round-id <rid>] [--values <json>] | values [--values <json>]"
              " | check-single <file> [--round-id <rid>]", file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    target: Optional[str] = None
    if cmd == "check-single":
        if not rest or rest[0].startswith("--"):
            print("用法: _finding_category.py check-single <file> [--round-id <rid>]", file=sys.stderr)
            return 2
        target, rest = rest[0], rest[1:]
    rid: Optional[str] = None
    rid_set = False
    values_path = DEFAULT_VALUES
    i = 0
    while i < len(rest):
        if rest[i] == "--round-id" and i + 1 < len(rest) and cmd in ("required", "check-single") and not rid_set:
            rid, rid_set = rest[i + 1], True
            i += 2
        elif rest[i] == "--values" and i + 1 < len(rest) and cmd != "check-single":
            values_path = rest[i + 1]
            i += 2
        else:
            print(f"_finding_category: 未知或重複參數 {rest[i]}", file=sys.stderr)
            return 2
    if cmd == "check-single":
        return check_single(target, rid if rid_set else None)
    try:
        if cmd == "values":
            vals, _thr = load_config(values_path)
            print("\n".join(vals))
            return 0
        print("1" if category_required(rid if rid_set else None, values_path) else "0")
        return 0
    except ConfigError as exc:
        print(f"_finding_category: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
