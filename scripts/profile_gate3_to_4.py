"""Gate 3→4 Re-Profile：量測真實 kline 上各層耗時，判定是否進入 Phase 4。"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("FFACT_USE_SEARCHSORTED", "1")
os.environ.setdefault("FFACT_USE_NUMBA_ROLLING", "1")
os.environ.setdefault("FFACT_L3_STREAMING", "1")

from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory


def main() -> None:
    process = psutil.Process()
    cfg = ConfigManager().get_merged_config()
    factory = create_feature_factory()

    # L0
    t0 = time.perf_counter()
    raw = factory._layer0_data_ingestion("ETHUSDT", "12h", cfg)
    l0_time = time.perf_counter() - t0
    print(f"[L0] data_ingestion: {l0_time:.3f}s, shape={raw.shape}")

    # L1
    t0 = time.perf_counter()
    layer1 = factory._layer1_atomic_indicators(raw, cfg)
    l1_time = time.perf_counter() - t0
    print(f"[L1] atomic_indicators: {l1_time:.3f}s, shape={layer1.shape}")

    # L2
    eng = DerivedOperatorEngine(cfg.operators.model_dump(by_alias=True))
    t0 = time.perf_counter()
    layer2 = eng.compute_all(layer1, raw)
    l2_time = time.perf_counter() - t0
    print(f"[L2] derived_features: {l2_time:.3f}s, shape={layer2.shape}")

    # L3
    r = RollingAggregator(cfg.rolling_aggregation.model_dump(by_alias=True))
    t0 = time.perf_counter()
    layer3 = r.compute_all(layer1)
    l3_time = time.perf_counter() - t0
    print(f"[L3] rolling_aggregation: {l3_time:.3f}s, shape={layer3.shape}")

    # L6.5 preprocessing
    preproc_cfg = cfg.preprocessing.model_dump(by_alias=True) if hasattr(cfg, 'preprocessing') else {"enabled": False}
    l65_time = 0.0
    if preproc_cfg.get("enabled", False):
        import pandas as pd
        combined = pd.concat([layer1, layer2, layer3], axis=1)
        preprocessor = FeaturePreprocessor(preproc_cfg)
        t0 = time.perf_counter()
        _ = preprocessor.preprocess(combined)
        l65_time = time.perf_counter() - t0
        print(f"[L6.5] preprocessing: {l65_time:.3f}s")
    else:
        print("[L6.5] preprocessing: DISABLED (0.0s)")

    pipeline_total = l0_time + l1_time + l2_time + l3_time + l65_time
    l2_l65_pct = (l2_time + l65_time) / pipeline_total * 100 if pipeline_total > 0 else 0

    rss_mb = process.memory_info().rss / (1024 * 1024)

    result = {
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "L0_seconds": round(l0_time, 3),
        "L1_seconds": round(l1_time, 3),
        "L2_seconds": round(l2_time, 3),
        "L3_seconds": round(l3_time, 3),
        "L6.5_seconds": round(l65_time, 3),
        "pipeline_total_seconds": round(pipeline_total, 3),
        "L2_plus_L65_pct": round(l2_l65_pct, 2),
        "RSS_MB": round(rss_mb, 1),
        "gate_condition": "L2+L6.5 > 30% total → Phase 4; else SKIP",
        "gate_result": "PROCEED to Phase 4" if l2_l65_pct >= 30 else "SKIP Phase 4",
        "no_phase4_condition": "pipeline_total < 420s (7 min) → SKIP Phase 4",
        "no_phase4_result": "SKIP Phase 4 (fast enough)" if pipeline_total < 420 else "PROCEED to Phase 4",
    }

    out_dir = Path("results/l56_golden_baseline")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "phase3_gate_compare_eth_1run.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Pipeline Total: {pipeline_total:.3f}s ({pipeline_total/60:.1f} min)")
    print(f"L2+L6.5: {l2_time + l65_time:.3f}s ({l2_l65_pct:.2f}%)")
    print(f"RSS: {rss_mb:.1f} MB")
    print(f"Gate 3→4: {result['gate_result']}")
    print(f"No-Phase-4: {result['no_phase4_result']}")
    print(f"Output: {out_path}")


if __name__ == "__main__":
    main()
