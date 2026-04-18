import json
import os
from pathlib import Path
import numpy as np
import pandas as pd

try:
    from momentum.FeatureEngineering.config_manager import ConfigManager
    from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
    from momentum.factories import create_feature_factory

    cfg = ConfigManager().get_merged_config()
    factory = create_feature_factory()
    raw = factory._layer0_data_ingestion("ETHUSDT", "12h", cfg)
    layer1 = factory._layer1_atomic_indicators(raw, cfg)
    subset = layer1.iloc[:, :64]

    roll_cfg = cfg.rolling_aggregation.model_dump(by_alias=True)
    os.environ["FFACT_L3_STREAMING"] = "1"

    os.environ["FFACT_USE_NUMBA_ROLLING"] = "0"
    pandas_out = RollingAggregator(roll_cfg).compute_all(subset)
    os.environ["FFACT_USE_NUMBA_ROLLING"] = "1"
    numba_out = RollingAggregator(roll_cfg).compute_all(subset)

    same_columns = list(pandas_out.columns) == list(numba_out.columns)

    max_abs_diff = 0.0
    by_tol = {
        "1e-6": {"cols": 0, "max_diff": 0.0, "pass": True},
        "1e-5": {"cols": 0, "max_diff": 0.0, "pass": True},
        "1e-4": {"cols": 0, "max_diff": 0.0, "pass": True},
    }

    for col in pandas_out.columns:
        p = pandas_out[col].to_numpy(dtype=np.float64)
        n = numba_out[col].to_numpy(dtype=np.float64)
        mask = ~(np.isnan(p) | np.isnan(n))
        diff = np.max(np.abs(p[mask] - n[mask])) if mask.any() else 0.0
        
        max_abs_diff = max(max_abs_diff, float(diff))

        if "_Skew_" in col or "_Kurt_" in col:
            bucket = "1e-4"
            atol = 1e-4
        elif "_Slope_" in col:
            bucket = "1e-5"
            atol = 1e-5
        else:
            bucket = "1e-6"
            atol = 1e-6

        ok = np.allclose(n, p, atol=atol, equal_nan=True)
        by_tol[bucket]["cols"] += 1
        by_tol[bucket]["max_diff"] = max(by_tol[bucket]["max_diff"], float(diff))
        if not ok:
            by_tol[bucket]["pass"] = False

    all_pass = same_columns and all(item["pass"] for item in by_tol.values())

    report = {
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "rows": int(subset.shape[0]),
        "input_cols": int(subset.shape[1]),
        "output_cols": int(pandas_out.shape[1]),
        "same_columns": same_columns,
        "max_abs_diff": max_abs_diff,
        "by_tolerance": by_tol,
        "all_pass": all_pass,
    }

    out = Path("results/l56_golden_baseline/t3_12_real_h5_subset_compare.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nREPORT_START")
    print(json.dumps(report, ensure_ascii=False))
    print("REPORT_END")
except Exception as e:
    import traceback
    print(traceback.format_exc())
