"""PRE-RED 探針：重現 test_v7_cgsa_resume_matches_fresh 之種子 run（BTCUSDT 12h＋1h、14 天窗、persist），
印出其 L7 manifest 之 run_status／quality_status／failure_reasons 與 nan_ratio。

用法（cwd＝待測 worktree）：env PYTHONHASHSEED=0 venv/bin/python <本檔>
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    spec = importlib.util.spec_from_file_location("freeze_failopen_baseline", ROOT / "scripts/freeze_failopen_baseline.py")
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    for k, v in freeze.FIXED_ENV.items():
        os.environ[k] = v
    os.environ["FFACT_LAYER1_PARALLEL"] = "0"
    os.environ["FFACT_MULTI_TF_PARALLEL"] = "0"
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f["/BTCUSDT/12h/data"]["timestamp"]).max()), unit="s", tz="UTC")
    days = int(os.environ.get("PRERED_DAYS", "14"))
    lower = os.environ.get("PRERED_LOWER_TF", "1h")
    start = (end - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    print("probe_config days", days, "training", ["12h", lower])
    payload = {
        "timeframes": {"primary": "12h", "training": ["12h", lower], "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {"enabled": False},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }
    if os.environ.get("PRERED_REDUCED") == "1":
        # 精簡指標集（同 tests/feature_engineering/ff_artifact_compare_helpers.fast_config_payload 之 L1），L2–L4 維持預設
        payload["atomic_indicators"] = {
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in ("momentum", "volatility", "volume", "cycle", "pattern", "statistics",
                                               "microstructure", "entropy", "tail_risk")},
        }
        print("probe_config reduced L1")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "cgsa")
        factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
        factory._storage = FeatureStorage(str(Path(tmp) / "features"))
        res = factory.generate_features("BTCUSDT", "12h", config_override=payload, force_regenerate=True,
                                        start_date=start, end_date=end.strftime("%Y-%m-%d"), persist=True)
        from momentum.FeatureEngineering.feature_storage import resolve_run_status

        found = sorted(Path(tmp, "features").rglob("feature_manifest.json"))
        for p in found:
            m = json.loads(p.read_text(encoding="utf-8"))
            arts = m.get("artifacts", {})
            view = {name: {k: a.get(k) for k in ("quality_status", "run_status", "failure_reasons")}
                    for name, a in (arts.items() if isinstance(arts, dict) else [])}
            print("L7manifest", str(p.relative_to(tmp)), "resolved=", resolve_run_status(m),
                  json.dumps(view, ensure_ascii=False)[:900])
        print("result_status", res.metadata.get("run_status"), res.metadata.get("quality_status"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
