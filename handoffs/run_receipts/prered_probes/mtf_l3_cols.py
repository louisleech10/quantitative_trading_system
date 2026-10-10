"""直跑 L3（同 test_mtf_12h_l1_l3_direct 之設定）之欄集合與 L3 剔除原因。用法（cwd＝worktree）：venv/bin/python <本檔> <out.json>"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def main(out: str) -> None:
    spec = importlib.util.spec_from_file_location("ffb", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    os.environ["FFACT_CGSA_WORK_DIR"] = tempfile.mkdtemp()
    sys.path.insert(0, str(ROOT / "tests" / "feature_engineering"))
    tspec = importlib.util.spec_from_file_location("tfc", ROOT / "tests/feature_engineering/test_failopen_correctness.py")
    tfc = importlib.util.module_from_spec(tspec)
    tspec.loader.exec_module(tfc)
    from momentum.factories import create_feature_factory

    factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    payload = tfc._fast_config_payload(timeframes={"primary": "12h", "training": ["12h", "1h"], "alignment_mode": "open_minus"})
    config = factory._resolve_config(payload)
    s, e = freeze._window_dates()
    raw = factory._layer0_data_ingestion("BTCUSDT", "12h", config, start_date=s, end_date=e)
    l1 = factory._layer1_atomic_indicators(raw, config).data
    l2 = factory._layer2_derived_features(l1, raw, config).data
    l3 = factory._layer3_rolling_aggregation(l1, l2, config).data
    agg = getattr(factory, "_last_l3_aggregator", None)
    dead = dict(getattr(agg, "dead_reasons", {}) or {}) if agg is not None else {}
    lowcard = sorted(getattr(agg, "_low_cardinality_cols", []) or []) if agg is not None else []
    nunique = {str(c): int(l1[c].nunique(dropna=True)) for c in l1.columns}
    # 只出現在新版之 Skew_W3 三欄：存其值與上游值，供 C2 reference 驗算
    import numpy as np

    probe = {}
    for c in ("close_trend_MIDPOINT_233_Skew_W3", "hl_momentum_AROONOSC_233_Skew_W3", "hl_trend_MIDPRICE_233_Skew_W3"):
        if c in l3.columns:
            u = c[: -len("_Skew_W3")]
            probe[c] = {"value": np.asarray(l3[c], dtype=np.float64).tolist(), "upstream": np.asarray(l1[u], dtype=np.float64).tolist()}
    Path(out + ".probe.json").write_text(json.dumps(probe), encoding="utf-8")
    Path(out).write_text(json.dumps({"cols": list(map(str, l3.columns)), "dead_reasons": {str(k): str(v) for k, v in dead.items()},
                                     "l1_cols": list(map(str, l1.columns)), "l1_nunique": nunique}), encoding="utf-8")
    print("l3_cols", l3.shape[1], "dead", len(dead))


if __name__ == "__main__":
    main(sys.argv[1])
