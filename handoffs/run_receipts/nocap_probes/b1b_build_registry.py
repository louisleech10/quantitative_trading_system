"""NOCAP b1b：依 b1b_classification.json 把 scripts/timeout_scan.py 之未登記命中逐處分類，B／C／D 產生精確綁定登記列。

用法：venv/bin/python handoffs/run_receipts/nocap_probes/b1b_build_registry.py [--write]
- 不帶 --write：只印統計與檢查結果。
- --write：登記列併入 scripts/timeout_registry.json，A 類餘留清單寫 handoffs/run_receipts/20261027-nocap-b1b-class-a.json。
自我檢查（任一不過 ⇒ rc 1、不寫檔）：①每處未登記命中皆有規則 ②A 類命中不被任何新登記列蓋到 ③每條規則至少命中一處
④登記檔通過 validate_registry。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RULES = Path(__file__).with_name("b1b_classification.json")
REGISTRY = REPO / "scripts" / "timeout_registry.json"
CLASS_A_OUT = REPO / "handoffs" / "run_receipts" / "20261027-nocap-b1b-class-a.json"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("timeout_scan_b1b", REPO / "scripts" / "timeout_scan.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _rule_for(hit, rules):
    for i, r in enumerate(rules):
        if re.fullmatch(r["path"], hit.path) and ("lines" not in r or hit.line in r["lines"]) \
                and ("pattern_id" not in r or hit.pattern_id == r["pattern_id"]):
            return i, r
    return None, None


def _entry(hit, rule):
    base = {"path": hit.path}
    if hit.callee:
        base.update(function=hit.function, callee=hit.callee, literal=hit.literal)
    else:
        base["line"] = hit.text.strip()
    base.update({"class": rule["class"], "reason": rule["reason"]})
    return base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    scan = _load_scanner()
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    doc = json.loads(REGISTRY.read_text(encoding="utf-8"))
    existing = doc["entries"]
    hits = scan.scan_repo(REPO)
    todo = scan.unregistered(hits, existing)
    todo_keys = {id(h) for h in todo}
    problems, used, class_a, new = [], Counter(), [], []
    seen = {json.dumps({k: v for k, v in e.items() if k not in ("class", "reason")}, sort_keys=True) for e in existing}
    for h in hits:  # 規則套全庫命中：已登記者亦須有規則（驗既有登記無 A、規則無過期）
        prior = None if id(h) in todo_keys else scan.registered(h, existing)
        if prior is not None and prior.get("whole_file"):
            continue
        i, r = _rule_for(h, rules)
        if r is None:
            if prior is None:
                problems.append(f"無規則：{h.path}:{h.line} {h.text.strip()[:80]}")
            continue
        used[i] += 1
        if prior is not None:
            if r["class"] == "A":
                problems.append(f"規則判 A 而已登記（{prior.get('class')}）：{h.path}:{h.line} {h.text.strip()[:80]}")
            continue
        if r["class"] == "A":
            class_a.append({"path": h.path, "line": h.line, "pattern_id": h.pattern_id, "function": h.function,
                            "callee": h.callee, "literal": h.literal, "text": h.text.strip(), "reason": r["reason"]})
            continue
        e = _entry(h, r)
        key = json.dumps({k: v for k, v in e.items() if k not in ("class", "reason")}, sort_keys=True)
        if key not in seen:
            seen.add(key)
            new.append(e)
    for i, r in enumerate(rules):
        if used[i] == 0:
            problems.append(f"規則未命中任何一處（過期或寫錯）：#{i} {r['path']} {r.get('lines', '')}")
    merged = existing + new
    a_hits = [h for h in todo if (_rule_for(h, rules)[1] or {}).get("class") == "A"]
    for h in a_hits:
        hit_entry = scan.registered(h, merged)
        if hit_entry is not None:
            problems.append(f"A 類被登記列蓋到：{h.path}:{h.line} ← {hit_entry}")
    try:
        scan.validate_registry(merged)
    except ValueError as exc:
        problems.append(f"登記檔驗證失敗：{exc}")
    by_class = Counter(_rule_for(h, rules)[1]["class"] for h in todo if _rule_for(h, rules)[1])
    print(f"未登記命中 {len(todo)}；分類 {dict(sorted(by_class.items()))}；新登記列 {len(new)}（既有 {len(existing)}）")
    remaining = scan.unregistered(hits, merged)
    print(f"登記後未登記命中 {len(remaining)}（應全為 A 類 {len(class_a)}）")
    if len(remaining) != len(class_a):
        problems.append(f"登記後未登記數 {len(remaining)} ≠ A 類數 {len(class_a)}")
    for p in problems:
        print("✗", p)
    if problems:
        return 1
    if args.write:
        doc["entries"] = merged
        REGISTRY.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        CLASS_A_OUT.write_text(json.dumps({
            "_doc": "NOCAP b1b：A 類（依牆鐘停止／縮減運算或對長運算放棄等候）逐處清單，不登記，待 Phase 1–6 改碼移除；"
                    "分類規則 handoffs/run_receipts/nocap_probes/b1b_classification.json。",
            "count": len(class_a), "by_path": dict(sorted(Counter(a["path"] for a in class_a).items())),
            "hits": class_a}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已寫 {REGISTRY.relative_to(REPO)}（{len(merged)} 列）與 {CLASS_A_OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
