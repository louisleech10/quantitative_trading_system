"""ICFIRSTALIGN 乙 SPEC v3 §A 收據：L2 兩計算臂（`compute_all_polars` 回傳表 vs 逐類別 `compute_category`）數值差異之量級。

正式 CGSA 生成時：後層（L5、L6）吃 `compute_all_polars` 回傳表；registry 落盤（＝公開 L2 特徵）為逐類別 `compute_category`。
現行校準域吃回傳表。真實 BTCUSDT 12h 尾 800 根；L1＝EMA8、SMA13（精簡）；設定取 ConfigManager 真值。
用法：env PYTHONPATH=. venv/bin/python <本檔>（峰值 < 500 MB，不跑工廠生成）。
"""

from __future__ import annotations

import json


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        rec = f["/BTCUSDT/12h/data"][-800:]
    raw = pd.DataFrame({n: np.asarray(rec[n], dtype=np.float64) for n in ("open", "high", "low", "close", "volume")})
    l1 = pd.DataFrame({"EMA_8": raw.close.ewm(span=8, adjust=False).mean(), "SMA_13": raw.close.rolling(13).mean()})
    cfg = ConfigManager().get_merged_config()
    engine = DerivedOperatorEngine(cfg.operators.model_dump())
    pl = engine.compute_all_polars(l1, raw)
    parts = [engine.compute_category(l1, raw, None, c) for c in engine.OPERATOR_CATEGORIES]
    pa = pd.concat([p for p in parts if p is not None and not p.empty], axis=1)
    common = sorted(set(pl.columns) & set(pa.columns))
    x64, y64 = pl[common].to_numpy(dtype=np.float64), pa[common].to_numpy(dtype=np.float64)
    x32, y32 = pl[common].to_numpy(dtype=np.float32), pa[common].to_numpy(dtype=np.float32)
    both = np.isfinite(x64) & np.isfinite(y64)
    absdiff = np.where(both, np.abs(x64 - y64), 0.0)
    scale = np.where(both, np.maximum(np.abs(x64), np.abs(y64)), 1.0)
    rel = np.where(both & (scale > 0), absdiff / np.where(scale > 0, scale, 1.0), 0.0)
    per_col = {c: int((both[:, i] & (x32[:, i] != y32[:, i])).sum()) for i, c in enumerate(common)}
    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. venv/bin/python handoffs/run_receipts/icfirstalign_probes/l2_arm_probe.py",
        "rows": len(raw), "cols_polars": int(pl.shape[1]), "cols_category": int(pa.shape[1]), "cols_common": len(common),
        "only_polars": sorted(set(pl.columns) - set(pa.columns)), "only_category": sorted(set(pa.columns) - set(pl.columns)),
        "nan_mask_diffs": int((np.isfinite(x64) != np.isfinite(y64)).sum()),
        "float64_finite_diffs": int((both & (x64 != y64)).sum()),
        "float32_finite_diffs": int((both & (x32 != y32)).sum()),
        "max_abs_diff": float(absdiff.max()), "max_rel_diff": float(rel.max()),
        "cols_with_float32_diffs": sum(1 for v in per_col.values() if v),
        "top_cols": sorted(per_col.items(), key=lambda kv: -kv[1])[:8],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
