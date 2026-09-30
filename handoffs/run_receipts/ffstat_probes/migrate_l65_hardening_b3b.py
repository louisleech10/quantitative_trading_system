"""FF-STAT b3b：tests/golden/l65_hardening 基準遷移之證據（舊基準 vs 新基準逐葉比對）。

語意變更：平穩化判定之校準值由「輸出範圍前 N 列（含 NaN）之有效值」改為封包之「N 個有效值」
（工具以 scripts/build_l65_golden.attach_fixture_calibration 取 fixture 前 N 個有效值）。
⇒ 預期只有「fixture 前 N 列內含 NaN」之欄可能改變；其餘欄須逐位元不變。

用法：python migrate_l65_hardening_b3b.py <舊基準目錄> <新基準目錄> <收據 json>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import numpy as np  # noqa: E402

import scripts.build_l65_golden_baseline as gb  # noqa: E402

old_dir, new_dir, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
N = 500


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else str(k))
    else:
        yield prefix, obj


report = {"n": N, "records": {}, "violations": []}
for path in sorted(new_dir.glob("*_baseline.json")):
    symbol, tf = path.name.split("_")[:2]
    old = dict(leaves(json.loads((old_dir / path.name).read_text(encoding="utf-8"))))
    new = dict(leaves(json.loads(path.read_text(encoding="utf-8"))))
    raw = gb._load_hdf5_kline_frame(symbol, tf, gb.KLINE_CACHE_PATH)
    src, _ = gb._build_l1_l2_real_features(raw.tail(gb.DEFAULT_MAX_ROWS), max_cols=gb.DEFAULT_MAX_COLS)
    nan_in_head = {c for c in src.columns if not np.isfinite(src[c].to_numpy(np.float64)[:N]).all()}
    changed = sorted(k for k in set(old) | set(new) if old.get(k) != new.get(k))
    per_column = sorted({k.split(".")[2] for k in changed
                         if len(k.split(".")) >= 3 and k.split(".")[1] in ("per_feature_stats", "dtypes")})
    aggregate = sorted(k for k in changed
                       if not (len(k.split(".")) >= 3 and k.split(".")[1] in ("per_feature_stats", "dtypes")))
    bad = [c for c in per_column if c not in nan_in_head]
    report["records"][path.name] = {"changed_leaves": len(changed), "changed_columns": per_column,
                                    "aggregate_changed": aggregate, "columns_with_nan_in_first_n": sorted(nan_in_head)}
    report["violations"].extend(f"{path.name}:{c}" for c in bad)
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("violations", report["violations"])
for name, rec in report["records"].items():
    print(name, rec["changed_leaves"], rec["changed_columns"], rec["aggregate_changed"][:6])
