"""NUMVIEW b2 諮詢 r2 證據探針（唯讀，秒級～分級）：真實 A_BTCUSDT_1h 輸入 (ii) 前 N 欄，IC 頁預設請求（rank 252＋zscore
[100,252]）下，polars 與 pandas_optimized 臂之輸出各對參考實作（`tests/feature_engineering/numview_reference.py`）算逐欄
Spearman IC（對 close 之 1 根前向報酬，IC-first 同一標籤 `pct_change().shift(-1)`），報告 |ΔIC|／SE(n_eff) 之分布、
正負號翻轉數、τ-b（`postic_branchdiff.ic_material`）。收據寫 `handoffs/run_receipts/<date>-numview-b2-ic-scale-probe.json`。

用法：`venv/bin/python handoffs/run_receipts/numview_probes/b2_ic_scale_probe.py [N]`（預設 200）。不生成特徵；讀凍結 run。
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
CELL_WORK = REPO / "data_cache/numview_freeze_runs/A_BTCUSDT_1h__default"
ARMS = {"polars": {"FFACT_USE_POLARS": "1"},
        "pandas_optimized": {"FFACT_USE_POLARS": "0", "FFACT_L65_CHUNK_SIZE": "0"}}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main(argv) -> int:
    n_cols = int(argv[0]) if argv else 200
    from api.models.ic_models import ApplyTransformsRequest
    from api.services.ic_analysis_service import _normalize_zscore_windows
    from momentum.factories import create_feature_preprocessor, create_post_ic_transform_config, ratio_unsafe_category
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from tests.feature_engineering import numview_helpers as nh
    from tests.feature_engineering import numview_reference as ref
    from tests.feature_engineering.ffname_helpers import register_canonical_run

    bd = _load("numview_postic_branchdiff", REPO / "handoffs/run_receipts/numview_probes/postic_branchdiff.py")
    side = json.loads((CELL_WORK / "numview_cell.json").read_text(encoding="utf-8"))
    run_dir = CELL_WORK / "features" / side["symbol"] / side["primary_tf"] / side["config_hash"]
    tmp = Path(tempfile.mkdtemp(prefix="b2icp_"))
    register_canonical_run(run_dir / "feature_manifest.json", tmp / "reg.json")
    root = CELL_WORK / "features"
    lib = FeatureLibrary(FeatureRegistry(tmp / "reg.json"), FeatureStorage(str(root)), feature_reader=FeatureReader(str(root)))
    df = lib.load_canonical_path(str(run_dir / "feature_manifest.json"))
    kept = [c for c in dict.fromkeys(side["ic_first_selected"]) if c in df.columns and ratio_unsafe_category(c) is None]
    cols = kept[:n_cols]
    frame = df[cols].copy()
    idx = pd.DatetimeIndex(frame.index)

    import h5py
    source = Path(side["source"])
    with h5py.File(str(source), "r") as h:
        data = h[side["symbol"]][side["primary_tf"]]["data"][()]
    kdf = pd.DataFrame({"timestamp": data["timestamp"], "close": data["close"].astype(np.float64)})
    unit = "ms" if int(kdf["timestamp"].iloc[-1]) > 10 ** 11 else "s"
    kdf.index = pd.to_datetime(kdf["timestamp"], unit=unit, utc=True)
    close = kdf["close"]
    label_full = close.pct_change().shift(-1)
    if idx.tz is None:
        idx_l = idx.tz_localize("UTC")
    else:
        idx_l = idx.tz_convert("UTC")
    label = label_full.reindex(idx_l).to_numpy(dtype=np.float64)

    req = ApplyTransformsRequest(selected_features=cols)
    windows = _normalize_zscore_windows(req.zscore_windows)
    cfg = create_post_ic_transform_config(rank=req.rank, rank_window=req.rank_window, zscore=req.zscore,
                                          zscore_windows=windows, gaussian=req.gaussian)
    t0 = time.perf_counter()
    reference = np.column_stack([ref.post_ic_chain(frame[c].to_numpy(dtype=np.float64), rank_window=req.rank_window,
                                                   gaussian_window=None, zscore_windows=windows) for c in cols])
    ref_seconds = time.perf_counter() - t0

    def spearman(x: np.ndarray, y: np.ndarray):
        m = np.isfinite(x) & np.isfinite(y)
        n = int(m.sum())
        if n < 3:
            return float("nan"), n
        rx = pd.Series(x[m]).rank().to_numpy()
        ry = pd.Series(y[m]).rank().to_numpy()
        return float(np.corrcoef(rx, ry)[0, 1]), n

    ic_ref, n_eff = zip(*[spearman(reference[:, j], label) for j in range(len(cols))])
    ic_ref = np.asarray(ic_ref)
    n_eff = np.asarray(n_eff)
    out = {"schema_version": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
           "head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO), capture_output=True, text=True).stdout.strip(),
           "command": f"venv/bin/python handoffs/run_receipts/numview_probes/b2_ic_scale_probe.py {n_cols}",
           "exit_code": 0,
           "criteria_sha256": hashlib.sha256(nh.current_criteria_path().read_bytes()).hexdigest(),
           "cell": "A_BTCUSDT_1h", "input": "ii", "columns": len(cols), "rows": int(len(frame)),
           "request": {"rank": req.rank, "rank_window": req.rank_window, "zscore": req.zscore, "zscore_windows": windows,
                       "gaussian": req.gaussian},
           "reference_seconds": round(ref_seconds, 3),
           "n_eff": {"min": int(n_eff.min()), "median": float(np.median(n_eff)), "max": int(n_eff.max())},
           "ic_ref_abs_over_2se": int(np.sum(np.abs(ic_ref) >= 2 / np.sqrt(np.maximum(n_eff, 1)))), "arms": {}}
    for arm, env in ARMS.items():
        for k in ("FFACT_USE_POLARS", "FFACT_L65_OPTIMIZATION_PROFILE", "FFACT_L65_CHUNK_SIZE"):
            os.environ.pop(k, None)
        os.environ.update(env)
        pre = create_feature_preprocessor(cfg.model_dump())
        t0 = time.perf_counter()
        res = pre.transform_selected(cols, {"ic_page": frame}, config=cfg)["ic_page"].loc[:, cols]
        secs = time.perf_counter() - t0
        actual = sorted({str(g.get("arm")) for g in pre.last_post_ic_execution()[1].values()})
        arr = res.to_numpy(dtype=np.float64)
        diff = bd.cell_diff(reference, arr)
        ic_arm = np.asarray([spearman(arr[:, j], label)[0] for j in range(len(cols))])
        se = 1 / np.sqrt(np.maximum(n_eff, 1))
        ratio = np.abs(ic_arm - ic_ref) / se
        fin = np.isfinite(ratio)
        mat = bd.ic_material(ic_ref.tolist(), ic_arm.tolist())
        out["arms"][arm] = {"actual_arm": actual, "seconds": round(secs, 3), "cell_diff": diff,
                            "abs_delta_ic": {"max": float(np.nanmax(np.abs(ic_arm - ic_ref))),
                                             "median": float(np.nanmedian(np.abs(ic_arm - ic_ref)))},
                            "delta_ic_over_se": {"max": float(ratio[fin].max()), "p99": float(np.percentile(ratio[fin], 99)),
                                                 "median": float(np.median(ratio[fin])),
                                                 "count_ge_0_01": int(np.sum(ratio[fin] >= 0.01)),
                                                 "count_ge_0_1": int(np.sum(ratio[fin] >= 0.1))},
                            "ic_material_v7": mat}
        print(arm, json.dumps(out["arms"][arm], ensure_ascii=False, default=str), flush=True)
    dest = REPO / "handoffs/run_receipts" / f"{datetime.now().strftime('%Y%m%d')}-numview-b2-ic-scale-probe.json"
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"[b2_ic_scale_probe] 收據 {dest.relative_to(REPO)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
