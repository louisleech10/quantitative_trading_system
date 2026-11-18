#!/usr/bin/env python3
"""FRAMEPATH 凍結基準之結構重凍：逐欄紀錄契約 v2（d4d97d62，FFPROD b2）所致之 `manifest_sha256` 過期。

背景：`tests/_golden/framepath/cgsa_fingerprint.json` 最後一次結構重凍於 9891907f（2026-10-25，NUMVIEW Task 4.2）。
次日 d4d97d62（2026-10-26）把逐欄紀錄契約升 v2（紀錄表新增縮尾有效設定 7 欄；`momentum/FeatureEngineering/contracts/
run_provenance.json`）⇒ 每個落盤 run 之 manifest artifact 節點 `provenance.contract_version` 1→2、`provenance.sha256`
（紀錄檔位元組）改變 ⇒ 各格 `fingerprint.manifest_sha256` 不再等於凍結值，`test_framepath_invariance.py::
test_cell_matches_frozen_baseline` 於 d0249d55 與 main 9e1aadef 皆紅（2026-11-13 實跑）。

證法（兩樹各生成一次，逐格判定；任一格不成立 ⇒ rc=1、不寫任何檔）：
  `dump`：於 cwd 所在之 repo（worktree）行程內以凍結腳本之 `generate_cell` 跑全部格（`FRAMEPATH_CONFIG_HASH_PAIRS` 開，
          取篩後 manifest 細項），另記 run 目錄下每檔之 sha256（manifest 與 `provenance/` 紀錄檔除外＝值檔）。
  `apply --old <舊樹 dump> --new <現行樹 dump>`：每格須
    ① 舊樹之 `manifest_sha256` ＝ 凍結值（舊樹即凍結當時之碼態；證明比對對象正確）；
    ② 新舊篩後 manifest 逐鍵差異路徑 ⊆ {`…artifacts.<kind>.provenance.contract_version`, `…provenance.sha256`}，
       且 contract_version 之新值＝契約檔 `version`（其餘鍵逐位元相同）；
    ③ 新舊值檔集合相同且逐檔 sha256 相同（特徵值位元組不變）；
    ④ 現行樹 fingerprint 除 `manifest_sha256` 外各項以凍結腳本 `compare_cell` 對凍結值無差異；
  全部成立 ⇒ 只改寫各格 `fingerprint.manifest_sha256` 為現行值，並寫收據
  `tests/_golden/framepath/refreeze_provenance_v2_receipt.json`（逐格舊值、新值、差異路徑、值檔數）。無 manifest 之格
  （C9 拒絕格、C7 不落盤）其 manifest_sha256 須新舊相同且＝凍結值，原樣不動。

用法（真實資料重型跑；單行程串行；須經共用鎖）：
  cd <舊樹（9891907f）>  && venv/bin/python <本檔絕對路徑> dump <out.json> <work 目錄>
  cd <現行樹>             && venv/bin/python scripts/framepath_refreeze_provenance_v2.py dump <out.json> <work 目錄>
  venv/bin/python scripts/framepath_refreeze_provenance_v2.py apply --old <舊> --new <新> [--check]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping

BASELINE_REL = "tests/_golden/framepath/cgsa_fingerprint.json"
RECEIPT_REL = "tests/_golden/framepath/refreeze_provenance_v2_receipt.json"
CONTRACT_REL = "momentum/FeatureEngineering/contracts/run_provenance.json"
CHANGED_KEYS = ("contract_version", "sha256")
MANIFEST_BASENAMES = frozenset({"feature_manifest.json", "manifest.json"})
PROVENANCE_DIR = "provenance"


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def value_file_hashes(features_root: Path) -> Dict[str, str]:
    """run 樹下值檔（非 manifest、非 `provenance/` 紀錄檔、非暫存）之 {相對路徑: sha256}。"""
    out: Dict[str, str] = {}
    if not features_root.is_dir():
        return out
    for path in sorted(features_root.rglob("*")):
        rel = path.relative_to(features_root)
        if not path.is_file() or path.name in MANIFEST_BASENAMES or PROVENANCE_DIR in rel.parts:
            continue
        # registry.json 與其備份 registry.json.bak：特徵登記之中繼資料（含寫入時間戳），非值檔
        if path.name.startswith("registry.json") or path.suffix in (".tmp", ".lock"):
            continue
        out[str(rel)] = _sha_file(path)
    return out


def _path_first(p: str) -> None:
    """p 置於 sys.path 首位一次（先移除同字串舊項）：重複呼叫不使 sys.path 增長（TESTSELSLOW 2026-11-15）。"""
    while p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)


def dump(out_path: Path, work_root: Path) -> int:
    _path_first(os.getcwd())
    from scripts import freeze_framepath_baseline as fb

    os.environ[fb.CONFIG_HASH_PAIRS_ENV] = "1"
    cells: Dict[str, Any] = {}
    for cell in fb.CELLS:
        work = Path(work_root) / cell
        out = fb.generate_cell(cell, work)
        cells[cell] = {"fingerprint": out["fingerprint"],
                       "manifests": (out["receipt"].get("fingerprint_detail") or {}).get("manifests"),
                       "value_files": value_file_hashes(work / "features")}
        print(f"{cell} manifest_sha256={out['fingerprint'].get('manifest_sha256')}", flush=True)
    head = os.popen("git rev-parse HEAD").read().strip()
    out_path.write_text(json.dumps({"repo": os.getcwd(), "head": head, "cells": cells}, ensure_ascii=False,
                                   sort_keys=True, default=str), encoding="utf-8")
    return 0


def key_diffs(a: Any, b: Any, prefix: str = "") -> List[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        out: List[str] = []
        for key in sorted(set(a) | set(b), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            out += [path] if (key not in a or key not in b) else key_diffs(a[key], b[key], path)
        return out
    return [] if a == b else [prefix or "<root>"]


def manifest_diffs(old: Mapping[str, Any], new: Mapping[str, Any]) -> List[str]:
    """逐 manifest 檔（鍵＝run 內相對路徑，含 `.` 之檔名）之差異路徑 `<檔>#<鍵路徑>`；檔集合不同 ⇒ `<檔>#<root>`。"""
    out: List[str] = []
    for rel in sorted(set(old) | set(new)):
        if rel not in old or rel not in new:
            out.append(f"{rel}#<root>")
            continue
        out += [f"{rel}#{p}" for p in key_diffs(old[rel], new[rel])]
    return out


def allowed_path(path: str) -> bool:
    """`<檔>#artifacts.<kind>.provenance.<contract_version|sha256>`。"""
    segs = path.split("#", 1)[-1].split(".")
    return len(segs) == 4 and segs[0] == "artifacts" and segs[2] == "provenance" and segs[3] in CHANGED_KEYS


def _get(manifests: Mapping[str, Any], path: str) -> Any:
    rel, key_path = path.split("#", 1)
    node: Any = manifests.get(rel)
    for seg in key_path.split("."):
        node = node.get(seg) if isinstance(node, dict) else None
    return node


def _value_only(files: Any) -> Dict[str, str]:
    """dump 之值檔表再套一次排除規則（同 `value_file_hashes`；舊 dump 可能含 registry 備份）。"""
    return {k: v for k, v in dict(files or {}).items() if not Path(k).name.startswith("registry.json")}


def judge(cell: str, frozen: Mapping[str, Any], old: Mapping[str, Any], new: Mapping[str, Any],
          contract_version: int, compare_cell: Any) -> Dict[str, Any]:
    errors: List[str] = []
    frozen_fp = frozen["fingerprint"]
    want = frozen_fp.get("manifest_sha256")
    if old["fingerprint"].get("manifest_sha256") != want:
        errors.append(f"① 舊樹 manifest_sha256 {old['fingerprint'].get('manifest_sha256')} ≠ 凍結值 {want}")
    diffs = manifest_diffs(old.get("manifests") or {}, new.get("manifests") or {})
    bad = [p for p in diffs if not allowed_path(p)]
    errors += [f"② 差異路徑非 provenance 兩鍵：{p}" for p in bad]
    for p in diffs:
        if p.endswith(".contract_version") and _get(new.get("manifests") or {}, p) != contract_version:
            errors.append(f"② {p} 新值 ≠ 契約 version {contract_version}")
    old_v, new_v = _value_only(old.get("value_files")), _value_only(new.get("value_files"))
    if not new_v and any(str(k).endswith("feature_manifest.json") for k in (new.get("manifests") or {})):
        errors.append("③ 有落盤 run manifest 而無任何值檔（dump 未取到值檔）")  # C7 不落盤：只有 registry manifest
    if old_v != new_v:
        only = sorted(set(old_v) ^ set(new_v))
        changed = sorted(k for k in set(old_v) & set(new_v) if old_v[k] != new_v[k])
        errors.append(f"③ 值檔不同：單側 {only[:5]}、位元組異 {changed[:5]}")
    without = lambda fp: {k: v for k, v in fp.items() if k != "manifest_sha256"}  # noqa: E731
    errors += [f"④ {d}" for d in compare_cell(without(frozen_fp), without(new["fingerprint"]))]
    new_value = new["fingerprint"].get("manifest_sha256")
    if not diffs and new_value != want:
        errors.append("無 manifest 差異而 manifest_sha256 改變")
    return {"cell": cell, "frozen_before": want, "old_tree_value": old["fingerprint"].get("manifest_sha256"),
            "new_value": new_value, "changed": new_value != want, "diff_paths": diffs,
            "value_files": len(new_v), "errors": errors}


def apply(old_path: Path, new_path: Path, check: bool, baseline_override: str = "") -> int:
    repo = Path(__file__).resolve().parents[1]
    _path_first(str(repo))
    from scripts import freeze_framepath_baseline as fb

    old_doc = json.loads(old_path.read_text(encoding="utf-8"))
    new_doc = json.loads(new_path.read_text(encoding="utf-8"))
    if baseline_override and not check:
        raise SystemExit("--baseline 只限 --check（改壞對照用；寫入一律寫 repo 之凍結檔）")
    baseline_path = Path(baseline_override) if baseline_override else repo / BASELINE_REL
    baseline_text = baseline_path.read_text(encoding="utf-8")
    baseline = json.loads(baseline_text)
    contract_version = int(json.loads((repo / CONTRACT_REL).read_text(encoding="utf-8"))["version"])
    items = [judge(cell, baseline["cells"][cell], old_doc["cells"][cell], new_doc["cells"][cell], contract_version,
                   fb.compare_cell) for cell in fb.CELLS]
    for item in items:
        print(json.dumps({k: item[k] for k in ("cell", "changed", "errors")}, ensure_ascii=False))
    if any(item["errors"] for item in items):
        print("拒寫：至少一格不成立", file=sys.stderr)
        return 1
    if check:
        return 0
    # 只換值字面（不重排整檔）：舊值 → 新值之對照須一致；舊值於檔中之出現次數須＝持有該值之格數
    mapping: Dict[str, str] = {}
    holders: Dict[str, int] = {}
    for item in items:
        old_v, new_v = item["frozen_before"], item["new_value"]
        if old_v == new_v:
            continue
        if mapping.setdefault(old_v, new_v) != new_v:
            print(f"拒寫：同一舊值對到兩個新值（{old_v}）", file=sys.stderr)
            return 1
        holders[old_v] = holders.get(old_v, 0) + 1
    new_text = baseline_text
    for old_v, new_v in mapping.items():
        if baseline_text.count(f'"{old_v}"') != holders[old_v]:
            print(f"拒寫：舊值 {old_v} 於凍結檔出現次數 ≠ 持有格數", file=sys.stderr)
            return 1
        new_text = new_text.replace(f'"{old_v}"', f'"{new_v}"')
    for item in items:
        baseline["cells"][item["cell"]]["fingerprint"]["manifest_sha256"] = item["new_value"]
    if json.loads(new_text) != baseline:
        print("拒寫：字面替換結果 ≠ 逐格改寫之預期內容", file=sys.stderr)
        return 1
    receipt = {"schema": "framepath-refreeze-provenance-v2/1", "reason": "d4d97d62 逐欄紀錄契約 v2",
               "contract": CONTRACT_REL, "contract_version": contract_version,
               "old_tree": {"repo": old_doc.get("repo"), "head": old_doc.get("head")},
               "new_tree": {"repo": new_doc.get("repo"), "head": new_doc.get("head")},
               "baseline_sha256_before": hashlib.sha256(baseline_text.encode("utf-8")).hexdigest(),
               "baseline_sha256_after": hashlib.sha256(new_text.encode("utf-8")).hexdigest(),
               "items": items}
    baseline_path.write_text(new_text, encoding="utf-8")
    (repo / RECEIPT_REL).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written: {BASELINE_REL}、{RECEIPT_REL}")
    return 0


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("out")
    d.add_argument("work_root")
    a = sub.add_parser("apply")
    a.add_argument("--old", required=True)
    a.add_argument("--new", required=True)
    a.add_argument("--check", action="store_true")
    a.add_argument("--baseline", default="", help="改以此凍結檔比對（只限 --check）")
    args = ap.parse_args(argv)
    if args.cmd == "dump":
        return dump(Path(args.out), Path(args.work_root))
    return apply(Path(args.old), Path(args.new), args.check, args.baseline)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
