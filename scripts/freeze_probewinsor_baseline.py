#!/usr/bin/env python3
"""PROBEWINSOR Task 1.0（docs/PROBEWINSOR_SPEC.md §G）：於錨點碼態凍結 `tests/_golden/probewinsor/baseline.json`。

用法：
  venv/bin/python scripts/freeze_probewinsor_baseline.py
      寫入模式（一次性）：錨點＝HEAD（不由呼叫者指定）。拒絕條件：baseline 已存在；工作樹之 momentum/、api/
      之 .py 對 HEAD 有改動或有未追蹤（含被忽略者）之 .py；HEAD 已含 contract `anchor_absent_symbols` 所列之本票
      生產符號（＝HEAD 已非改前碼）。
  venv/bin/python scripts/freeze_probewinsor_baseline.py --check [--cells id1,id2]
      比對模式：重跑（全部或指定）格與真值表，逐鍵比對既有 baseline，不寫檔。
rc：0＝寫入成功或比對全同；1＝比對不符或 contract 之 anchor_expect 不符；2＝拒絕（來源不合、參數錯、生成例外）。
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

_PRODUCTION_PATHSPECS = (":(glob)momentum/**/*.py", ":(glob)api/**/*.py")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True)


def provenance_errors() -> List[str]:
    """寫入前之來源檢查（錨點＝HEAD）：工作樹生產 .py 對 HEAD 無改動、無未追蹤（含被忽略）之生產 .py、
    HEAD 不含本票生產符號（`probewinsor_helpers.absent_symbol_violations`）。任一 git 呼叫失敗即列為錯誤。"""
    errors: List[str] = []
    diff = _git("diff", "--quiet", "HEAD", "--", *_PRODUCTION_PATHSPECS)
    if diff.returncode == 1:
        errors.append("工作樹之 momentum/、api/ 之 .py 對 HEAD 有改動")
    elif diff.returncode != 0:
        errors.append(f"git diff 失敗：{diff.stderr.strip()}")
    others = _git("ls-files", "--others", "-z", "--", "momentum", "api")
    if others.returncode != 0:
        errors.append(f"git ls-files 失敗：{others.stderr.strip()}")
    else:
        stray = sorted(p for p in others.stdout.split("\0") if p.endswith(".py") and "__pycache__" not in p)
        if stray:
            errors.append(f"未追蹤（含被忽略）之生產 .py：{stray[:10]}")
    head = _git("rev-parse", "HEAD")
    if head.returncode != 0:
        errors.append(f"git rev-parse 失敗：{head.stderr.strip()}")
    else:
        errors.extend(ph.absent_symbol_violations(head.stdout.strip()))
    return errors


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
        if ph.BASELINE_PATH.exists():
            # 一次性寫入：baseline 一經凍結即只讀（否則可於生產碼改後以新錨點覆寫，「改前基準」即失效）
            print(f"ERROR: {ph.BASELINE_PATH.relative_to(REPO)} 已存在；凍結為一次性寫入，不得覆寫", file=sys.stderr)
            return 2
        refused = provenance_errors()
        if refused:
            for line in refused:
                print(f"ERROR: 來源不合（凍結只准於改前碼寫入）：{line}", file=sys.stderr)
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
        document = {"version": 1, "frozen_at_head": head, **produced}
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
