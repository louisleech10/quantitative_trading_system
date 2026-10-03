"""ICFIRSTALIGN 乙 F-2 量測（安全縮小版）：12h＋1h 多週期生成時，校準域計算與 memmap 合併之次數、列數、欄數、位元組數。

精簡 L1（EMA8、SMA13；L2–L6 預設）使單次合併遠小於整機記憶體；以實測之「欄數擴張比」與列數外推全欄設定。
攔截：FeatureFactory._compute_calibration_domain（呼叫者、週期、列數、輸出欄數、耗時）、memmap_utils.concat_with_memmap
（DataFrame 數、列×欄、估計 bytes、context）。真實 kline，落盤至暫存目錄，不寫 data_cache。
用法：env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python <本檔> > <out.json>
環境：ICF_DAYS（公開窗天數，預設 14）、ICF_LOWER_TF（預設 1h）、ICF_FULL_L1=1 時改用預設全 L1（危險，勿於 8 GB 機器使用）。
"""

from __future__ import annotations

import inspect
import json
import os
import tempfile
import time
import traceback
from pathlib import Path


def main() -> int:
    import h5py
    import numpy as np
    import pandas as pd

    from momentum.FeatureEngineering import feature_factory as ff_mod
    from momentum.FeatureEngineering import memmap_utils
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    os.environ.setdefault("FFACT_LAYER1_PARALLEL", "0")
    os.environ.setdefault("FFACT_MULTI_TF_PARALLEL", "0")
    days = int(os.environ.get("ICF_DAYS", "14"))
    lower = os.environ.get("ICF_LOWER_TF", "1h")
    with h5py.File("data_cache/feature_klines/kline_cache.h5", "r") as f:
        end = pd.Timestamp(int(np.asarray(f["/BTCUSDT/12h/data"]["timestamp"]).max()), unit="s", tz="UTC")
    start = (end - pd.Timedelta(days=days)).strftime("%Y-%m-%d")

    calls = []
    concats = []
    real_cal = ff_mod.FeatureFactory._compute_calibration_domain
    real_concat = memmap_utils.concat_with_memmap

    def _cal(self, symbol, timeframe, config, klines, *a, **k):
        caller = [s.function for s in inspect.stack()[1:5]]
        t0 = time.perf_counter()
        out = real_cal(self, symbol, timeframe, config, klines, *a, **k)
        calls.append({"caller": caller, "timeframe": str(timeframe), "rows_in": int(len(klines)),
                      "out_shape": list(getattr(out, "shape", (0, 0))), "seconds": round(time.perf_counter() - t0, 2)})
        return out

    def _concat(dfs, *a, **k):
        frames = [d for d in dfs if d is not None and not getattr(d, "empty", True)]
        rows = max((len(d) for d in frames), default=0)
        cols = sum(d.shape[1] for d in frames)
        caller = [s.function for s in inspect.stack()[1:4]]
        concats.append({"n_dfs": len(frames), "rows": rows, "cols": cols, "est_bytes": rows * cols * 4,
                        "callers": caller})
        return real_concat(dfs, *a, **k)

    ff_mod.FeatureFactory._compute_calibration_domain = _cal
    memmap_utils.concat_with_memmap = _concat
    if hasattr(ff_mod, "concat_with_memmap"):  # 模組層 from-import 之別名亦換掉
        ff_mod.concat_with_memmap = _concat

    payload = {
        "timeframes": {"primary": "12h", "training": ["12h", lower], "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
    }
    if os.environ.get("ICF_FULL_L1") != "1":
        payload["atomic_indicators"] = {
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in ("momentum", "volatility", "volume", "cycle", "pattern", "statistics",
                                               "microstructure", "entropy", "tail_risk")},
        }
    error = None
    raw_cols = None
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["FFACT_CGSA_WORK_DIR"] = str(Path(tmp) / "cgsa")
        factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
        factory._storage = FeatureStorage(str(Path(tmp) / "features"))
        try:
            factory.generate_features("BTCUSDT", "12h", config_override=payload, force_regenerate=True,
                                      start_date=start, end_date=end.strftime("%Y-%m-%d"), persist=True)
            manifests = sorted(Path(tmp, "features").rglob("feature_manifest.json"))
            if manifests:
                m = json.loads(manifests[0].read_text(encoding="utf-8"))
                raw_cols = (m.get("artifacts", {}).get("raw", {}) or {}).get("total_features")
        except Exception as exc:  # noqa: BLE001
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()[:500]
    out = {
        "schema_version": 1,
        "command": "env PYTHONPATH=. PYTHONHASHSEED=0 venv/bin/python handoffs/run_receipts/icfirstalign_probes/f2_calibration_domain_probe.py",
        "exit_code": 0 if error is None else 1,
        "config": {"days": days, "training": ["12h", lower], "full_l1": os.environ.get("ICF_FULL_L1") == "1"},
        "wall_seconds": round(time.perf_counter() - t0, 1),
        "error": error,
        "raw_total_features": raw_cols,
        "calibration_domain_calls": calls,
        "memmap_concats": concats,
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
