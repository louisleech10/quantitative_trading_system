#!/usr/bin/env python3
"""PROBEWINSOR Task 1.0（docs/PROBEWINSOR_SPEC.md §G）：於錨點碼態凍結 `tests/_golden/probewinsor/baseline.json`。

用法：
  venv/bin/python scripts/freeze_probewinsor_baseline.py --anchor <commit>
      寫入模式：生產碼（momentum/ 之 .py）須與錨點逐位元相同（工作樹對錨點之 git diff 為空），否則拒絕。
  venv/bin/python scripts/freeze_probewinsor_baseline.py --anchor <commit> --check [--cells id1,id2]
      比對模式：重跑（全部或指定）格與真值表，逐鍵比對既有 baseline，不寫檔。
rc：0＝寫入成功或比對全同；1＝比對不符或 contract 之 anchor_expect 不符；2＝拒絕（生產碼已改、參數錯、生成例外）。
設定格唯一定義＝`tests/_golden/probewinsor/contract.json`；單格生成與記錄＝`tests/feature_engineering/probewinsor_helpers.py`。
單組串行；每格之寫入隔離於暫存目錄、完成即刪。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests.feature_engineering import probewinsor_helpers as ph  # noqa: E402

_PRODUCTION_PATHSPEC = ":(glob)momentum/**/*.py"


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)


def production_matches_anchor(anchor: str) -> bool:
    """工作樹之 momentum/**/*.py 對錨點無差異（含已提交與未提交之改動）。"""
    proc = _git("diff", "--quiet", anchor, "--", _PRODUCTION_PATHSPEC)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"git diff 失敗：{proc.stderr.strip()}")
    untracked = _git("ls-files", "--others", "--exclude-standard", "--", _PRODUCTION_PATHSPEC).stdout.strip()
    return proc.returncode == 0 and not untracked


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_all(cell_ids: List[str]) -> Dict[str, Any]:
    spec = ph.contract()
    cells: Dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="probewinsor-freeze-") as tmp:
        for cell_id in cell_ids:
            record = ph.run_cell(ph.cell_by_id(cell_id), Path(tmp))
            cells[cell_id] = record
            print(f"[freeze] {cell_id} rounds={record['rounds']} quality={record['quality_status']} "
                  f"cols={len(record['columns'])} {record['elapsed_seconds']}s", flush=True)
    return {
        "contract_sha256": _sha256_file(ph.CONTRACT_PATH),
        "kline_sha256": _sha256_file(REPO / spec["kline_dir"] / "kline_cache.h5"),
        "cells": cells,
        "truth_table": ph.truth_table(),
    }


def anchor_expect_errors(cells: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for cell_id, expect in ph.contract().get("anchor_expect", {}).items():
        if cell_id not in cells:
            continue
        for key, value in expect.items():
            if cells[cell_id].get(key) != value:
                errors.append(f"anchor_expect {cell_id}.{key}: {cells[cell_id].get(key)!r} != {value!r}")
    return errors


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--cells", default="")
    args = parser.parse_args(argv)
    all_ids = [c["id"] for c in ph.contract()["cells"]]
    wanted = [c for c in args.cells.split(",") if c] or all_ids
    unknown = sorted(set(wanted) - set(all_ids))
    if unknown:
        print(f"ERROR: contract 無此格：{unknown}", file=sys.stderr)
        return 2
    if not args.check:
        if args.cells:
            print("ERROR: 寫入模式不接受 --cells（baseline 須含全部格）", file=sys.stderr)
            return 2
        if not production_matches_anchor(args.anchor):
            print(f"ERROR: momentum/ 之 .py 與錨點 {args.anchor} 不同；凍結只准於生產碼未改時寫入", file=sys.stderr)
            return 2
    try:
        produced = run_all(wanted)
    except Exception as exc:  # 任一格失敗 ⇒ 整次失敗、不寫部分 baseline
        print(f"ERROR: 生成失敗：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    errors = anchor_expect_errors(produced["cells"])
    if args.check:
        frozen = ph.baseline()
        for cell_id in wanted:
            for line in ph.diff(produced["cells"][cell_id], frozen["cells"].get(cell_id, {}), ph.keys("all")):
                errors.append(f"{cell_id}: {line}")
        if produced["truth_table"] != frozen.get("truth_table"):
            errors.append("truth_table 不同")
        if produced["contract_sha256"] != frozen.get("contract_sha256"):
            errors.append("contract_sha256 不同")
        if produced["kline_sha256"] != frozen.get("kline_sha256"):
            errors.append("kline_sha256 不同")
    for line in errors:
        print(f"FAIL: {line}", file=sys.stderr)
    if errors:
        return 1
    if not args.check:
        head = _git("rev-parse", "HEAD").stdout.strip()
        document = {"version": 1, "anchor": args.anchor, "frozen_at_head": head, **produced}
        ph.BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = ph.BASELINE_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(document, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        tmp_path.replace(ph.BASELINE_PATH)
        print(f"[freeze] 已寫入 {ph.BASELINE_PATH.relative_to(REPO)}（{len(produced['cells'])} 格）")
    else:
        print(f"[freeze] --check 全同（{len(wanted)} 格）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
