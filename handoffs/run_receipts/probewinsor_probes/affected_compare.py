"""PROBEWINSOR Task 1.3：比對受影響既有測試之錨點與修正後結果，寫收據 handoffs/run_receipts/probewinsor-affected.json。

用法：venv/bin/python handoffs/run_receipts/probewinsor_probes/affected_compare.py <out_dir> <anchor_label> <fixed_label>
      [--ratiounsafe <ratiounsafe_ppoff_compare.py 產物>] [--attribution <歸因 JSON>] [--receipt <路徑>]
讀 affected_run.sh 之逐檔 junit 與 .progress；nodeid＝<檔>::<類別>::<名稱>（類別取 junit classname 末段，若為模組名則省略）。
判定：錨點綠而修正後紅＝`anchor_green_fixed_red`（SPEC Task 1.3 驗證：須 == 0 或逐項歸因 §C）；錨點紅＝HEAD 既有紅（不歸本票）；
兩側 nodeid 集合不同、或任一檔未完成（rc 非 0／1、junit 缺）＝`incomplete`（收據 pass＝False）。
"""
from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Tuple

REPO = Path(__file__).resolve().parents[3]
LIST = Path(__file__).resolve().parent / "affected_list.txt"


def _files() -> List[str]:
    files = [line.strip() for line in LIST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(files) != 35:
        raise SystemExit(f"清單應 35 檔，實得 {len(files)}")
    return files


def _key(path: str) -> str:
    return path.replace("/", "_")


def _progress(out: Path, label: str) -> Dict[str, Any]:
    lines = (out / f"{label}.progress").read_text(encoding="utf-8").splitlines()
    head = dict(kv.split("=", 1) for kv in lines[0].split() if "=" in kv)
    per: Dict[str, Dict[str, Any]] = {}
    for line in lines[1:]:
        parts = line.split()
        if len(parts) >= 4 and "/" in parts[0] and parts[0][0].isdigit():
            per[parts[1]] = {"rc": int(parts[2].split("=", 1)[1]), "seconds": int(parts[3].split("=", 1)[1]),
                             "summary": " ".join(parts[4:])}
    return {"head": head.get("head"), "done": any(line.startswith("done") for line in lines), "per_file": per}


def _results(out: Path, label: str, path: str) -> Tuple[Dict[str, str], str]:
    xml = out / label / f"{_key(path)}.xml"
    if not xml.exists():
        return {}, "junit 缺"
    module = Path(path).stem
    results: Dict[str, str] = {}
    for case in ET.parse(xml).getroot().iter("testcase"):
        cls = (case.get("classname") or "").split(".")[-1]
        name = case.get("name") or ""
        nodeid = f"{path}::{cls}::{name}" if cls and cls != module else f"{path}::{name}"
        if case.find("failure") is not None or case.find("error") is not None:
            outcome = "failed"
        elif case.find("skipped") is not None:
            outcome = "skipped"
        else:
            outcome = "passed"
        if nodeid in results and results[nodeid] != outcome:
            outcome = "failed"  # setup／teardown 錯誤另列一筆 ⇒ 合併為失敗
        results[nodeid] = outcome
    return results, ""


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out_dir")
    parser.add_argument("anchor_label")
    parser.add_argument("fixed_label")
    parser.add_argument("--ratiounsafe", default=None)
    parser.add_argument("--attribution", default=None)
    parser.add_argument("--receipt", default=str(REPO / "handoffs/run_receipts/probewinsor-affected.json"))
    args = parser.parse_args(argv)
    out = Path(args.out_dir)
    progress = {label: _progress(out, label) for label in (args.anchor_label, args.fixed_label)}
    incomplete: List[str] = []
    for label, prog in progress.items():
        if not prog["done"]:
            incomplete.append(f"{label}：未跑完")
    per_file: Dict[str, Any] = {}
    anchor_green_fixed_red: List[str] = []
    anchor_red: List[str] = []
    fixed_fixed: List[str] = []
    for path in _files():
        entry: Dict[str, Any] = {}
        res = {}
        for label in (args.anchor_label, args.fixed_label):
            r, err = _results(out, label, path)
            rc = progress[label]["per_file"].get(path, {}).get("rc")
            if err or rc not in (0, 1):
                incomplete.append(f"{label} {path}：{err or f'rc={rc}'}")
            res[label] = r
            entry[label] = {"rc": rc, "seconds": progress[label]["per_file"].get(path, {}).get("seconds"),
                            "counts": {o: sum(1 for v in r.values() if v == o) for o in ("passed", "failed", "skipped")}}
        a, f = res[args.anchor_label], res[args.fixed_label]
        if set(a) != set(f):
            incomplete.append(f"{path}：兩側 nodeid 不同（僅錨點 {sorted(set(a) - set(f))[:5]}；僅修正後 "
                              f"{sorted(set(f) - set(a))[:5]}）")
        for nodeid in sorted(set(a) & set(f)):
            if a[nodeid] == "passed" and f[nodeid] == "failed":
                anchor_green_fixed_red.append(nodeid)
            elif a[nodeid] == "failed":
                anchor_red.append(nodeid)
                if f[nodeid] == "passed":
                    fixed_fixed.append(nodeid)
        per_file[path] = entry
    receipt: Dict[str, Any] = {
        "ticket": "PROBEWINSOR", "task": "1.3",
        "anchor_head": progress[args.anchor_label]["head"], "fixed_head": progress[args.fixed_label]["head"],
        "deselect": {"tests/feature_engineering/test_failopen_correctness.py": "not test_v6_"},
        "anchor_green_fixed_red": anchor_green_fixed_red,
        "anchor_red_head_existing": anchor_red,
        "anchor_red_fixed_green": fixed_fixed,
        "incomplete": incomplete,
        "per_file": per_file,
    }
    if args.ratiounsafe:  # ratiounsafe_ppoff_compare.py 之產物（前處理關臂重產 vs baseline.json）
        receipt["ratiounsafe"] = json.loads(Path(args.ratiounsafe).read_text(encoding="utf-8"))
    # 錨點綠而修正後紅者須逐項具名歸因（SPEC Task 1.3：經審碼核可後以 TODO 修訂處置；不得放寬斷言換綠）
    attribution = json.loads(Path(args.attribution).read_text(encoding="utf-8")) if args.attribution else {}
    receipt["attribution"] = attribution
    receipt["unattributed"] = [n for n in anchor_green_fixed_red if n not in attribution]
    receipt["pass"] = (not incomplete and not receipt["unattributed"]
                       and receipt.get("ratiounsafe", {}).get("equal", True))
    Path(args.receipt).write_text(json.dumps(receipt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"pass={receipt['pass']} anchor_green_fixed_red={len(anchor_green_fixed_red)} "
          f"anchor_red={len(anchor_red)} incomplete={len(incomplete)} → {args.receipt}")
    return 0 if receipt["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
