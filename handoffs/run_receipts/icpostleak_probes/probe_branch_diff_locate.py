"""ICPOSTLEAK 審碼 r1 後：跨分支量級收據之最大差異格定位（資訊性）。

用法：venv/bin/python probe_branch_diff_locate.py <改後.npz> <輸出.json>
對每個 (分支, 組合) 之最大絕對差格，列：欄、列、legacy 值、分支值、該格 zscore 之輸入窗（以 legacy 對應前一步之輸出重建）
之 float64 精確 zscore（窗 = Z_WINDOWS 主窗，ddof 同 pandas rolling std＝1）、窗內 std 與 |mean|，判斷差異為
「近常數窗之病態放大」（std 相對 |mean| 極小）或「核心差異」。前一步輸出取同 npz 之 legacy 對應組合（去掉最後之 zscore）。
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


def main(npz_path: Path, out: Path) -> None:
    from tests.feature_engineering import test_icpostleak as t

    data = np.load(npz_path)
    columns = [str(c) for c in data["__columns__"]]
    window = int(sorted(t.Z_WINDOWS)[0]) if hasattr(t, "Z_WINDOWS") else None
    rows = []
    for key in sorted(k for k in data.files if k != "__columns__"):
        branch, combo = key.split("|", 1)
        if branch == "legacy":
            continue
        ref, got = data[f"legacy|{combo}"], data[key]
        both = np.isfinite(ref) & np.isfinite(got)
        if not both.any():
            continue
        absd = np.where(both, np.abs(got - ref), 0.0)
        r, c = np.unravel_index(int(np.argmax(absd)), absd.shape)
        if absd[r, c] == 0:
            continue
        row = {"branch": branch, "combo": combo, "column": columns[c], "row": int(r),
               "legacy": float(ref[r, c]), "branch_value": float(got[r, c]), "abs_diff": float(absd[r, c]),
               "diff_cells": int((absd > 0).sum()),
               "abs_diff_p50": float(np.median(absd[absd > 0])) if (absd > 0).any() else 0.0,
               "abs_diff_p99": float(np.quantile(absd[absd > 0], 0.99)) if (absd > 0).any() else 0.0}
        steps = combo.split("+")
        if steps[-1] == "zscore" and window:
            prev = "+".join(steps[:-1])
            if prev:
                x = data[f"legacy|{prev}"][:, c]
            else:
                x = t._real_frame().to_numpy(dtype=np.float64)[:, c]
            seg = x[max(0, r - window + 1): r + 1]
            seg = seg[np.isfinite(seg)]
            if seg.size >= 2:
                mu, sd = float(seg.mean()), float(seg.std(ddof=1))
                row.update({"window": window, "window_mean": mu, "window_std": sd,
                            "std_over_abs_mean": (sd / abs(mu)) if mu else None,
                            "exact_float64_z": (float((x[r] - mu) / sd) if sd > 0 else None)})
        rows.append(row)
    out.write_text(json.dumps({"schema_version": 1, "command": "probe_branch_diff_locate.py", "exit_code": 0,
                               "rows": rows}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for row in rows:
        print({k: (round(v, 6) if isinstance(v, float) else v) for k, v in row.items()})


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
