#!/usr/bin/env python3
"""FF-NAME 欄名描述向量匯出腳本（docs/FFNAME_SPEC.md Task 1.2）。

用法：
  venv/bin/python scripts/export_feature_name_vectors.py --check            # 重產並與 tests/_golden/ffname/name_vectors.json 逐位元比對；rc 0＝相同
  venv/bin/python scripts/export_feature_name_vectors.py --out <path>       # 產生向量檔至 <path>（不覆寫正式檔）

產生規則（契約落點 `tests/_golden/ffname/contract.json` 之 `descriptor` 段）：
- 合法名：§G reference 全部新名（由 Task 0.1 baseline 之零件以新 formatter 推導）＋契約 `spec_valid_names`；
  每筆描述由 `feature_naming.feature_descriptor`（經 `parse_feature_name`）**重新計算**（不得讀回既有向量檔）。
- 拒收名：契約 `descriptor.rejection_cases` 之每一類至少一筆；描述之錯誤鍵＝`parse_feature_name` 實際拋出之例外類別名。
- 版面：`{version, valid: [{name, descriptor}], rejected: [{name, case, descriptor}]}`；輸出為 canonical JSON（鍵排序）。

不得手寫向量。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from momentum.FeatureEngineering import feature_naming  # noqa: E402

VECTORS_PATH = REPO / "tests" / "_golden" / "ffname" / "name_vectors.json"
CONTRACT_PATH = REPO / "tests" / "_golden" / "ffname" / "contract.json"
FREEZE_SCRIPT = REPO / "scripts" / "ffname_freeze_baseline.py"


def _load_freeze_module():
    spec = importlib.util.spec_from_file_location("ffname_freeze_baseline", FREEZE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"無法載入 {FREEZE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("ffname_freeze_baseline", module)
    spec.loader.exec_module(module)
    return module


def _baseline_new_names() -> List[str]:
    """§G reference 零件以新 formatter 推導之全部新名（baseline 缺即拋，不以空集合過關）。"""
    freeze = _load_freeze_module()
    data = json.loads(freeze.BASELINE_PATH.read_text(encoding="utf-8"))
    names = []
    for row in data["parts"]:
        part = freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                    "ops": tuple(row.get("ops") or ())})
        names.append(freeze.derive_new_name(part, row["tf"]))
    if not names:
        raise RuntimeError("baseline.json 無零件，無法產生 §G 向量")
    return names


def _describe(name: str) -> Dict[str, Any]:
    # 每次呼叫取模組屬性，確保描述反映當下之 parser（不快取、不讀回既有向量）
    return feature_naming.feature_descriptor(name)


def build_vectors() -> Dict[str, Any]:
    """依契約與 parser 重新計算向量（不讀既有向量檔）。"""
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    desc = contract["descriptor"]
    valid_names = sorted(set(_baseline_new_names()) | set(contract["spec_valid_names"].values()))
    valid = []
    for name in valid_names:
        descriptor = _describe(name)
        if desc["error_key"] in descriptor:
            raise RuntimeError(f"合法名 {name!r} 被 parser 拒收：{descriptor[desc['error_key']]}")
        valid.append({"name": name, "descriptor": descriptor})
    rejected = []
    for case, spec in sorted(desc["rejection_cases"].items()):
        name = contract["spec_reject_names"][spec["name_key"]]
        descriptor = _describe(name)
        if descriptor.get(desc["error_key"]) != spec["exception"]:
            raise RuntimeError(f"拒收案例 {case}（{name!r}）之例外 {descriptor.get(desc['error_key'])!r} ≠ 契約 {spec['exception']!r}")
        rejected.append({"name": name, "case": case, "descriptor": descriptor})
    return {"version": feature_naming.CURRENT_FEATURE_NAMING_VERSION, "valid": valid, "rejected": rejected}


def _sorted_keys(node: Any) -> Any:
    if isinstance(node, dict):
        return {k: _sorted_keys(node[k]) for k in sorted(node)}
    if isinstance(node, list):
        return [_sorted_keys(v) for v in node]
    return node


def _canonical_bytes(vectors: Dict[str, Any]) -> bytes:
    """頂層鍵依契約 `vectors_layout.top_keys` 之序，其下各層鍵排序。"""
    top_keys = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))["descriptor"]["vectors_layout"]["top_keys"]
    if sorted(top_keys) != sorted(vectors):
        raise RuntimeError(f"向量頂層鍵 {sorted(vectors)} ≠ 契約 {top_keys}")
    ordered = {k: _sorted_keys(vectors[k]) for k in top_keys}
    return (json.dumps(ordered, ensure_ascii=False, indent=1) + "\n").encode("utf-8")


def write_vectors(out_path: Path) -> int:
    """寫 canonical JSON 至 `out_path`；rc 0 成功。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_canonical_bytes(build_vectors()))
    return 0


def check(path: Path = VECTORS_PATH) -> int:
    """重產向量並與 `path` 逐位元比對；相同 rc 0，否則列差異 rc 1。"""
    fresh = _canonical_bytes(build_vectors())
    path = Path(path)
    if not path.is_file():
        print(f"缺向量檔 {path}")
        return 1
    committed = path.read_bytes()
    if committed == fresh:
        return 0
    old = {e["name"]: e for e in json.loads(committed.decode("utf-8")).get("valid", [])}
    new = {e["name"]: e for e in json.loads(fresh.decode("utf-8"))["valid"]}
    for name in sorted(set(old) ^ set(new)):
        print(f"{'多出' if name in old else '缺少'}：{name}")
    for name in sorted(set(old) & set(new)):
        if old[name] != new[name]:
            print(f"描述不符：{name}")
    print("向量檔與重產結果不一致（rc 1）")
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="重產並與正式向量檔比對")
    group.add_argument("--out", help="輸出路徑")
    args = parser.parse_args(argv)
    if args.check:
        return check()
    return write_vectors(Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
