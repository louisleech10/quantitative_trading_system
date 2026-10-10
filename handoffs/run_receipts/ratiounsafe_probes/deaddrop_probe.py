"""RATIOUNSAFE 預查（審查 r1 CODEX-R1-P1-02）：預設 L7 dead-drop 開時，pattern 欄經 L6.5 轉換與否對落盤欄集合與檔案大小之影響。
同一單週期設定（L1 只開 pattern＋精簡 trend EMA8／SMA13，L2–L6 預設，dead-drop 預設開）分別以前處理關／開各生成一次並落盤至暫存目錄，
比 raw 成品之欄名集合與 parquet 總 bytes。前處理關之 pattern 欄值＝修後「原值通過」之值；非 pattern 欄於兩臂不同屬預期（前處理本身）。
用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python <本檔> > <out.json>；環境 RATIOUNSAFE_TF（預設 12h）、RATIOUNSAFE_DAYS（預設 1000）。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
    from momentum.factories import create_feature_factory

    os.environ["FFACT_LAYER1_PARALLEL"] = "0"
    tf = os.environ.get("RATIOUNSAFE_TF", "12h")
    days = int(os.environ.get("RATIOUNSAFE_DAYS", "1000"))
    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f[f"/BTCUSDT/{tf}/data"]["timestamp"]).max()), unit="s", tz="UTC")
    start = (end - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    payload = {
        "timeframes": {"primary": tf, "training": [tf]},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "atomic_indicators": {
            "pattern": {"enabled": True},
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in ("momentum", "volatility", "volume", "cycle", "statistics",
                                               "microstructure", "entropy", "tail_risk")},
        },
    }
    tf_keys = set(TimeframeAligner._timeframe_seconds_keys())

    def _is_pattern(col: str) -> bool:  # 去第二段週期後第二段為 pattern（含 L4 lag 等衍生名）
        parts = [p for i, p in enumerate(str(col).split("_")) if not (i == 1 and p in tf_keys)]
        return len(parts) >= 3 and parts[1] == "pattern"

    def _gen(preprocessing: bool):
        cfg = dict(payload, preprocessing={"enabled": preprocessing})
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "cgsa")
            factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
            factory._storage = FeatureStorage(str(Path(tmp) / "features"))
            factory.generate_features("BTCUSDT", tf, config_override=cfg, force_regenerate=True,
                                      start_date=start, end_date=end.strftime("%Y-%m-%d"), persist=True)
            manifests = sorted(Path(tmp, "features").rglob("feature_manifest.json"))
            if not manifests:
                raise FileNotFoundError("暫存目錄無 feature_manifest.json")
            run_dir = manifests[0].parent
            reader = FeatureReader(str(Path(tmp, "features")))
            parts = [df for _, df in reader.stream_groups_v2("BTCUSDT", tf, run_dir.name, "raw", allow_partial=True)]
            frame = pd.concat(parts, axis=1) if parts else pd.DataFrame()
            nbytes = sum(p.stat().st_size for p in run_dir.rglob("*.parquet"))
            return list(frame.columns), nbytes

    cols_off, bytes_off = _gen(False)
    cols_on, bytes_on = _gen(True)
    s_off, s_on = set(cols_off), set(cols_on)
    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/ratiounsafe_probes/deaddrop_probe.py",
        "exit_code": 0, "tf": tf, "days": days, "l7_dead_feature_drop": "預設（開）",
        "n_cols_preprocessing_off": len(s_off), "n_cols_preprocessing_on": len(s_on),
        "n_pattern_off": sum(map(_is_pattern, s_off)), "n_pattern_on": sum(map(_is_pattern, s_on)),
        "pattern_only_in_off": sorted(c for c in s_off - s_on if _is_pattern(c)),
        "pattern_only_in_on": sorted(c for c in s_on - s_off if _is_pattern(c)),
        "nonpattern_set_equal": {c for c in s_off if not _is_pattern(c)} == {c for c in s_on if not _is_pattern(c)},
        "parquet_bytes_preprocessing_off": bytes_off, "parquet_bytes_preprocessing_on": bytes_on,
        "honest_bounds": "以前處理關之 pattern 欄近似修後原值通過；非 pattern 欄於兩臂之值不同（前處理本身），故 bytes 差含非 pattern 欄之編碼差，非純 pattern 增量；修後實際增量須於實作後以同設定實測",
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
