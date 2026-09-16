#!/usr/bin/env python3
"""_finding_category.py — DOCROT2 Task 3.1（票 B-63）：finding 類別之值集、適用門檻與類別行解析之唯一實作。

呼叫端（不得另寫判定）：
  · scripts/completeness_check.sh --single  →  CLI `required`／`values`（決定是否須類別、取封閉值集）
  · scripts/_synth_attr.py::check_category   →  import（收斂檔主委欄與委員欄）
  · scripts/_docrot2_metrics.py              →  import（收案量測事件之類別計數）

判定（封閉、只讀 audit 序號，不讀日期與 mtime）：
  category_required(round_id)
    round_id 為 None                                ⇒ 須類別（fail-closed）
    audit 中該 round 之 committee_round_open 恰一筆且 sequence 為整數
       ⇒ sequence > category_required_after_audit_sequence 才須類別
    查無、多筆、sequence 非整數、audit 讀不到        ⇒ 須類別（fail-closed：嚴側）
  值集與門檻只定義於 scripts/governance_verdicts.json；缺鍵或型別不符 ⇒ ConfigError（呼叫端 fail-closed）。

CLI：
  python3 scripts/_finding_category.py required [--round-id <rid>] [--values <json>]   stdout 1｜0；rc 0，設定錯 rc 2
  python3 scripts/_finding_category.py values [--values <json>]                         stdout 每行一值；rc 0／2
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
# 與 completeness_check.sh::_validate_finding_body 之 category_value 同文法：標籤後接可選空白（只認半形空白與 tab）、
# 可選半形／全形冒號、可選空白，值與標籤同行，去頭尾半形空白與 tab 後須逐字等於封閉值之一
_LABEL_RE = re.compile(r"\*\*類別\*\*[ \t]*[:：]?[ \t]*(.*)$")
# 值形狀封閉：completeness_check.sh 以 `|` 串接值集傳入 awk，值內不得含分隔字元或空白
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
    with open(audit_path, encoding="utf-8") as fh:
        for raw in fh:
            s = raw.strip()
            if not s.startswith("{"):
                continue
            try:
                rec = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                yield rec


def round_open_records(audit_path: str, round_id: str) -> List[dict]:
    return [r for r in iter_audit(audit_path)
            if r.get("event") == "committee_round_open" and r.get("round_id") == round_id]


def round_open_sequence(audit_path: str, round_id: str) -> Optional[int]:
    """恰一筆且 sequence 為整數 ⇒ 回序號；其餘一律 None（呼叫端視為須類別）。"""
    try:
        recs = round_open_records(audit_path, round_id)
    except OSError:
        return None
    if len(recs) != 1:
        return None
    seq = recs[0].get("sequence")
    if isinstance(seq, int) and not isinstance(seq, bool):
        return seq
    return None


def category_required(round_id: Optional[str], values_path: str = DEFAULT_VALUES,
                      audit_path: Optional[str] = None) -> bool:
    _vals, thr = load_config(values_path)
    if not round_id:
        return True
    if audit_path is None:
        try:
            audit_path = resolve_audit_path()
        except ConfigError:
            return True
    seq = round_open_sequence(audit_path, round_id)
    if seq is None:
        return True
    return seq > thr


def parse_category_lines(lines: List[str]) -> List[str]:
    """一段 finding 區塊（fence 外）之全部 `**類別**` 行之值（去頭尾空白）；同行重複標籤之行值記為空字串。"""
    out: List[str] = []
    in_fence = False
    for ln in lines:
        if re.match(r"^\s*(```|~~~)", ln):
            in_fence = not in_fence
            continue
        if in_fence or LABEL not in ln:
            continue
        if ln.count(LABEL) > 1:
            out.append("")
            continue
        m = _LABEL_RE.search(ln)
        out.append(m.group(1).strip(" \t") if m else "")
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


def main(argv: List[str]) -> int:
    if not argv or argv[0] not in ("required", "values"):
        print("用法: _finding_category.py required [--round-id <rid>] [--values <json>] | values [--values <json>]",
              file=sys.stderr)
        return 2
    cmd, rest = argv[0], argv[1:]
    rid: Optional[str] = None
    rid_set = False
    values_path = DEFAULT_VALUES
    i = 0
    while i < len(rest):
        if rest[i] == "--round-id" and i + 1 < len(rest) and cmd == "required":
            rid, rid_set = rest[i + 1], True
            i += 2
        elif rest[i] == "--values" and i + 1 < len(rest):
            values_path = rest[i + 1]
            i += 2
        else:
            print(f"_finding_category: 未知參數 {rest[i]}", file=sys.stderr)
            return 2
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
