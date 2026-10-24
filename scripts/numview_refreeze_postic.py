#!/usr/bin/env python3
"""NUMVIEW Task 3.4：IC-first processed 之 §G 凍結重凍（docs/NUMVIEW_SPEC.md Task 3.4「IC-first 之 §G 凍結於本 Task 同提交對
擇定核心重凍並登記審清單」、Task 3.1 v40 註）。

重凍項（只此三項；其餘凍結值不動）：
- `tests/_golden/numview/pre_change_fingerprints.json` 之 `cells.B_BTCUSDT_1h_4h.g3.processed`（§G G3）；
- `tests/_golden/preprov/pre_change_fingerprints.json` 之 `cells.ic_first.BTCUSDT.processed`、
  `cells.ic_first_default.BTCUSDT.processed`（PRE-PROV 沿用基準）。

證法：同一次改後之真實生成中，非 post-IC 之凍結值須不變——B 格 `g3.raw` 重算須逐位元＝凍結值（`numview_helpers.bitwise_diff`），
否則 rc=1、不寫；PRE-PROV 兩格（凍結基準無 raw）之 post-IC 輸入（raw 選欄，spy `transform_selected` 擷取值指紋）須逐位元＝
改前碼（HEAD 之 worktree 以 `--capture-inputs` 產出、`--baseline-inputs` 傳入）之擷取，否則 rc=1、不寫（審碼 b4 r1
CODEX-R1-P1-01）；processed 之欄集合須與凍結值相同（只改值與 dtype，不增減欄），否則 rc=1。G1（IC 頁改前臂份）不重凍——
其為 Task 3.4 ②之改前紀錄，§G 閘經決定紀錄 `changed_targets` 例外。
收據：`handoffs/run_receipts/<date>-numview-postic-refreeze.json`（每項 before／after 之 column_set_sha256、改值欄數、
dtype 分布）。`--check`：重算並報告，不寫凍結檔。

用法（真實資料重型跑，約 10 分；單行程、不與委員輪並行）：
  PYTHONPATH=. venv/bin/python scripts/numview_refreeze_postic.py [--check] [--work DIR]
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests.feature_engineering import numview_helpers as nh  # noqa: E402
from tests.feature_engineering import preprov_helpers as ph  # noqa: E402

B_CELL = "B_BTCUSDT_1h_4h"
PREPROV_CELLS = ("ic_first", "ic_first_default")
SYMBOL = "BTCUSDT"
RUN_KIND = "regen_b4"


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _changed(before: Mapping[str, Any], after: Mapping[str, Any]) -> List[str]:
    a, b = before.get("columns", {}), after.get("columns", {})
    return sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))


def _dtypes(fp: Mapping[str, Any]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for col in fp.get("columns", {}).values():
        out[str(col.get("dtype"))] = out.get(str(col.get("dtype")), 0) + 1
    return out


def _summary(before: Mapping[str, Any], after: Mapping[str, Any]) -> Dict[str, Any]:
    return {"column_set_equal": set(before.get("columns", {})) == set(after.get("columns", {})),
            "changed_columns": len(_changed(before, after)), "columns": len(after.get("columns", {})),
            "dtypes_before": _dtypes(before), "dtypes_after": _dtypes(after)}


def _generate_capturing_inputs(root: Path, cell: str) -> Any:
    """生成 PRE-PROV 格並擷取每次 post-IC `transform_selected` 之輸入（選欄於各群組之值指紋）；回 (handle, {群組: 指紋})。
    spy 以 *args 收參數，改前碼（arm 可選）與改後碼（arm 必填關鍵字）皆可用。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    captured: Dict[str, Any] = {}
    real = FeaturePreprocessor.transform_selected

    def spy(self: Any, selected: Any, groups: Any, *args: Any, **kwargs: Any) -> Any:
        names = [str(s) for s in selected]
        for gid, frame in (groups or {}).items():
            cols = [c for c in names if c in frame.columns]
            if cols:
                captured[str(gid)] = nh.frame_fingerprints(frame.loc[:, cols])
        return real(self, selected, groups, *args, **kwargs)

    FeaturePreprocessor.transform_selected = spy  # type: ignore[assignment]
    try:
        handle = ph.generate_short_run(root, cell, symbol=SYMBOL)
    finally:
        FeaturePreprocessor.transform_selected = real  # type: ignore[assignment]
    if not captured:
        raise SystemExit(f"REFUSE: {cell} 未擷取任何 post-IC 輸入")
    return handle, captured


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="重算並報告，不寫凍結檔")
    parser.add_argument("--work", default=None, help="生成暫存根（預設系統暫存）")
    parser.add_argument("--capture-inputs", default=None,
                        help="只生成 PRE-PROV 格並寫其 post-IC 輸入值指紋至此 JSON（於改前碼 worktree 執行以產基準）")
    parser.add_argument("--baseline-inputs", default=None,
                        help="改前碼之 post-IC 輸入值指紋 JSON（重凍必填；與本次擷取逐位元比對，不等即拒寫）")
    args = parser.parse_args(argv)
    work = Path(args.work) if args.work else Path(tempfile.mkdtemp(prefix="numview_refreeze_postic_"))
    if args.capture_inputs:
        out = {"head": _git("rev-parse", "HEAD").strip(),
               "cells": {cell: _generate_capturing_inputs(work / f"capture_{cell}", cell)[1] for cell in PREPROV_CELLS}}
        Path(args.capture_inputs).write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"[refreeze] captured post-IC inputs → {args.capture_inputs}")
        return 0
    if not args.baseline_inputs:
        print("REFUSE: 重凍須給 --baseline-inputs（改前碼之 post-IC 輸入值指紋；審碼 b4 r1 CODEX-R1-P1-01）", file=sys.stderr)
        return 2
    baseline_inputs = json.loads(Path(args.baseline_inputs).read_text(encoding="utf-8"))

    import importlib.util

    spec = importlib.util.spec_from_file_location("numview_freeze_baseline", REPO / "scripts" / "numview_freeze_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(freeze)

    numview_path, preprov_path = nh.PRE_CHANGE_FINGERPRINTS_PATH, ph.PRE_CHANGE_FINGERPRINTS_PATH
    numview = json.loads(numview_path.read_text(encoding="utf-8"))
    preprov = json.loads(preprov_path.read_text(encoding="utf-8"))
    items: Dict[str, Any] = {}

    record = numview["cells"][B_CELL]
    descriptor = {"id": B_CELL, "kind": record["kind"], "symbol": record["symbol"], "timeframes": list(record["timeframes"])}
    current = freeze.freeze_cell(descriptor, work / B_CELL, arms=[], run_kind=RUN_KIND)
    raw_diff = nh.bitwise_diff(record["g3"]["raw"], current["g3"]["raw"])
    if raw_diff:
        print(f"REFUSE: {B_CELL} g3.raw 與凍結值不等（非 post-IC 值改變，須歸因）：{raw_diff[:5]}", file=sys.stderr)
        return 1
    new_numview = copy.deepcopy(numview)
    new_numview["cells"][B_CELL]["g3"]["processed"] = current["g3"]["processed"]
    items[f"numview:{B_CELL}/g3/processed"] = dict(_summary(record["g3"]["processed"], current["g3"]["processed"]),
                                                   raw_bitwise_equal=True)

    new_preprov = copy.deepcopy(preprov)
    for cell in PREPROV_CELLS:
        handle, inputs = _generate_capturing_inputs(work / f"preprov_{cell}", cell)
        # 非 post-IC 值不變之證：本次 post-IC 輸入（raw 選欄）對改前碼之擷取逐位元相等（審碼 b4 r1 CODEX-R1-P1-01）
        base = (baseline_inputs.get("cells") or {}).get(cell) or {}
        if set(base) != set(inputs):
            print(f"REFUSE: {cell} post-IC 輸入群組 {sorted(inputs)} ≠ 改前 {sorted(base)}", file=sys.stderr)
            return 1
        input_diff = [d for gid in sorted(inputs) for d in nh.bitwise_diff(base[gid], inputs[gid])]
        if input_diff:
            print(f"REFUSE: {cell} post-IC 輸入與改前碼不等（非 post-IC 值改變，須歸因）：{input_diff[:5]}", file=sys.stderr)
            return 1
        after = ph.value_fingerprints(handle.run_dir, "processed")
        before = preprov["cells"][cell][SYMBOL]["processed"]
        new_preprov["cells"][cell][SYMBOL]["processed"] = after
        items[f"preprov:{cell}/{SYMBOL}/processed"] = dict(
            _summary(before, after), post_ic_input_bitwise_equal_to_pre_change=True,
            post_ic_input_groups=sorted(inputs),
            post_ic_input_columns=sum(len(fp.get("columns", {})) for fp in inputs.values()))

    bad = [k for k, v in items.items() if not v["column_set_equal"]]
    if bad:
        print(f"REFUSE: processed 欄集合改變：{bad}", file=sys.stderr)
        return 1

    before_sha = {str(p.relative_to(REPO)): _sha(p) for p in (numview_path, preprov_path)}
    if not args.check:
        # 格式同凍結腳本（scripts/numview_freeze_baseline.py:816，不排序鍵）與 PRE-PROV 凍結腳本（sort_keys）
        numview_path.write_text(json.dumps(new_numview, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        preprov_path.write_text(json.dumps(new_preprov, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    stamp = _dt.datetime.now(_dt.timezone.utc)
    receipt = {"schema_version": 1, "generated_at": stamp.isoformat(), "head": _git("rev-parse", "HEAD").strip(),
               "command": " ".join(["PYTHONPATH=. venv/bin/python", "scripts/numview_refreeze_postic.py", *(argv or sys.argv[1:])]),
               "criteria_sha256": _sha(Path(nh.current_criteria_path())),  # SPEC Task 0.3 ③
               "exit_code": 0, "check_only": bool(args.check), "run_kind": RUN_KIND, "files_before_sha256": before_sha,
               "files_after_sha256": {str(p.relative_to(REPO)): _sha(p) for p in (numview_path, preprov_path)},
               "baseline_inputs": {"path": str(args.baseline_inputs), "sha256": _sha(Path(args.baseline_inputs)),
                                   "head": baseline_inputs.get("head")},
               "items": items}
    out = REPO / "handoffs" / "run_receipts" / f"{stamp.strftime('%Y%m%d')}-numview-postic-refreeze.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[refreeze] {'checked' if args.check else 'wrote'}; receipt {out.relative_to(REPO)}")
    print(json.dumps(items, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
