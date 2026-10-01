"""ICPOSTLEAK §G 改前對照收據（資訊性，非通過條件）。

用法：
  venv/bin/python probe_change_report.py dump <程式碼根目錄> <輸出.npz>   # 於該根目錄之程式碼產各分支×七組合輸出
  venv/bin/python probe_change_report.py report <改前.npz> <改後.npz> <輸出.json>
dump 以 tests/feature_engineering/test_icpostleak.py 之 `_run_branch`（去 spy）與 §G 輸入集跑；直接執行須先 isolate。
"""
import json
import sys
import tempfile
from pathlib import Path

import numpy as np


def dump(root: Path, out: Path) -> None:
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ffstat_probes"))
    from _isolate import isolate

    isolate("probe_icpostleak_change_")
    import os

    import pytest

    os.chdir(root)
    from tests.feature_engineering import test_icpostleak as t

    frame = t._real_frame()
    arrays = {"__columns__": np.array([str(c) for c in frame.columns])}
    for branch in t.BRANCHES:
        for steps in t.COMBOS:
            spec = dict(t.BRANCHES[branch])
            spec.pop("spy", None)
            mp = pytest.MonkeyPatch()
            try:
                got = t._run_branch(mp, Path(tempfile.mkdtemp()), branch, steps, frame, spec_override=spec)
            finally:
                mp.undo()
            arrays[f"{branch}|{'+'.join(steps)}"] = got.to_numpy(dtype=np.float64)
    np.savez_compressed(out, **arrays)
    print(f"wrote {out} keys={len(arrays) - 1}")


def report(before_path: Path, after_path: Path, out: Path) -> None:
    before, after = np.load(before_path), np.load(after_path)
    columns = [str(c) for c in before["__columns__"]]
    rows = []
    for key in sorted(k for k in before.files if k != "__columns__"):
        a, b = before[key], after[key]

        def first(x, j):
            fin = np.flatnonzero(np.isfinite(x[:, j]))
            return int(fin[0]) if fin.size else None

        for j, col in enumerate(columns):
            fb, fa = first(a, j), first(b, j)
            start = fa if fa is not None else a.shape[0]
            seg_a, seg_b = a[start:, j], b[start:, j]
            both = np.isfinite(seg_a) & np.isfinite(seg_b)
            diff = ~((seg_a == seg_b) | (np.isnan(seg_a) & np.isnan(seg_b)))
            rows.append({
                "case": key, "column": col, "first_finite_before": fb, "first_finite_after": fa,
                "masked_rows_added": (fa - fb) if (fa is not None and fb is not None) else None,
                "suffix_diff_cells": int(diff.sum()),
                "suffix_max_abs_diff": float(np.max(np.abs(seg_a[both] - seg_b[both]))) if both.any() else 0.0,
            })
    summary = {
        "cases": len({r["case"] for r in rows}),
        "suffix_identical_cases": sorted({r["case"] for r in rows} - {r["case"] for r in rows if r["suffix_diff_cells"]}),
        "suffix_changed_cases": sorted({r["case"] for r in rows if r["suffix_diff_cells"]}),
    }
    out.write_text(json.dumps({"schema_version": 1, "command": "probe_change_report.py report", "exit_code": 0,
                               "spec": "docs/ICPOSTLEAK_SPEC.md §G 改前對照收據（資訊性）", "summary": summary,
                               "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


def branchdiff(after_path: Path, out: Path) -> None:
    """SPEC Task 1.1「數值基準」：改後各分支對同組合 legacy 之量級（最大絕對差、最大相對差、差異格數），作 §N 殘留觸發之輸入。
    不排除任何格、不加容差：NaN 位置不一致之格另計（nan_position_mismatch_cells）並計入 diff_cells；
    相對差分母＝|legacy|，legacy 恰為 0 之格無法定義相對差，其格數與該處最大絕對差另列（不併入相對差、不丟棄）。"""
    after = np.load(after_path)
    keys = sorted(k for k in after.files if k != "__columns__")
    combos = sorted({k.split("|", 1)[1] for k in keys})
    rows = []
    for combo in combos:
        ref_key = f"legacy|{combo}"
        ref = after[ref_key]
        for key in keys:
            branch, kc = key.split("|", 1)
            if kc != combo or branch == "legacy":
                continue
            got = after[key]
            if got.shape != ref.shape:
                rows.append({"branch": branch, "combo": combo, "shape_mismatch": [list(got.shape), list(ref.shape)]})
                continue
            fin_ref, fin_got = np.isfinite(ref), np.isfinite(got)
            both = fin_ref & fin_got
            nan_mismatch = fin_ref ^ fin_got
            absd = np.abs(got[both] - ref[both])
            denom = np.abs(ref[both])
            zero = denom == 0
            rel = absd[~zero] / denom[~zero]
            diff_cells = int((absd != 0).sum() + nan_mismatch.sum())
            rows.append({
                "branch": branch, "combo": combo, "cells": int(ref.size), "both_finite_cells": int(both.sum()),
                "nan_position_mismatch_cells": int(nan_mismatch.sum()), "diff_cells": diff_cells,
                "max_abs_diff": float(absd.max()) if absd.size else 0.0,
                "max_rel_diff": float(rel.max()) if rel.size else 0.0,
                "legacy_zero_cells": int(zero.sum()),
                "legacy_zero_max_abs_diff": float(absd[zero].max()) if zero.any() else 0.0,
            })
    measured = [r for r in rows if "max_rel_diff" in r]
    worst = max(measured, key=lambda r: r["max_rel_diff"]) if measured else None
    summary = {
        "pairs": len(rows),
        "shape_mismatch_pairs": sum(1 for r in rows if "shape_mismatch" in r),
        "nan_position_mismatch_pairs": sum(1 for r in measured if r["nan_position_mismatch_cells"]),
        "max_rel_diff_overall": worst["max_rel_diff"] if worst else 0.0,
        "max_rel_diff_at": f"{worst['branch']}|{worst['combo']}" if worst else None,
        "max_abs_diff_overall": max((r["max_abs_diff"] for r in measured), default=0.0),
        "residual_trigger_rel_gt_1e-3": bool(worst and worst["max_rel_diff"] > 1e-3),
    }
    out.write_text(json.dumps({"schema_version": 1, "command": "probe_change_report.py branchdiff", "exit_code": 0,
                               "spec": "docs/ICPOSTLEAK_SPEC.md Task 1.1 數值基準（各分支對 legacy 量級；§N 殘留觸發輸入）",
                               "summary": summary, "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    if sys.argv[1] == "dump":
        dump(Path(sys.argv[2]), Path(sys.argv[3]))
    elif sys.argv[1] == "branchdiff":
        branchdiff(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        report(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
