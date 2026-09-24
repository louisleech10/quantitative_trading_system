"""FF-STAT 驗收之共用 helper（docs/FFSTAT_SPEC.md §G、Task 1.1–4.1）。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）輕量設定：close 資料源、L1 trend、L2 只開 Ratio／Cross、
L3 rolling 5／13、L6.5 開 fracdiff（L1、L2）與 ADF 差分；輸出窗 `WINDOW` 之前留有足夠前史。
一切寫入經 `fftfmeta_golden_helpers.prepare_env` 隔離於 tmp。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.fftfmeta_golden_helpers import (
    HEALTHY,
    KLINE_DIR,
    PRIMARY_TF,
    SYMBOL,
    WINDOW,
    fast_payload,
    prepare_env,
)

CONTRACT = json.loads((Path(__file__).resolve().parents[1] / "_golden" / "ffstat" / "contract.json").read_text(encoding="utf-8"))
META = CONTRACT["metadata_keys"]
EVENTS = CONTRACT["events"]
BASELINE_PATH = Path(__file__).resolve().parents[1] / "_golden" / "ffstat" / "baseline.json"

__all__ = [
    "CONTRACT", "META", "EVENTS", "BASELINE_PATH", "PRIMARY_TF", "SYMBOL", "WINDOW",
    "prepare_env", "stat_payload", "run_stat", "decisions",
]


def prepare_stat_env(monkeypatch: Any, tmp_path: Path, **env: str) -> Path:
    """`prepare_env` ＋把 d* 快取目錄導向 tmp（現行 `_d_star_cache_dir` 固定指向專案 data_cache，不受環境變數影響）。
    回傳隔離之 d* 快取目錄（§G：兩次 run 皆以各自隔離之空 d* 快取執行）。"""
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor

    import tempfile

    prepare_env(monkeypatch, tmp_path, **env)
    target = tmp_path / "dstar_cache"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: target))
    # 本測試之系統暫存導向 <tmp>/sys_tmp（契約 test_tmp_isolation）：校準暫存殘留只查此處，不掃全系統 tmp
    sys_tmp = tmp_path / "sys_tmp"
    sys_tmp.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(tempfile, "tempdir", str(sys_tmp))
    return target


def sys_tmp(tmp_path: Path) -> Path:
    """`prepare_stat_env` 所設之本測試系統暫存目錄。"""
    return tmp_path / "sys_tmp"


def first_output_timestamp(root: Path):
    """落盤基礎欄之第一列時間（讀任一基礎欄 parquet 之 timestamp 欄或 index）。"""
    import pandas as pd
    import pyarrow.parquet as pq

    for p in sorted(root.rglob("*.parquet")):
        if p.name.endswith("_L65.parquet"):
            continue
        frame = pq.read_table(p).to_pandas()
        if "timestamp" in frame.columns:
            ts = frame["timestamp"].iloc[0]
            return pd.to_datetime(ts, unit="ms", utc=True) if isinstance(ts, (int, float)) else pd.Timestamp(ts)
        return pd.Timestamp(frame.index[0])
    raise AssertionError("無基礎欄 parquet")


def stat_payload(training_tfs: Optional[List[str]] = None, *, fracdiff: bool = True, adf: bool = True,
                 cross_sectional: bool = False, **overrides: Any) -> Dict[str, Any]:
    """開平穩化之輕量真實設定（§G）。"""
    payload = fast_payload(list(training_tfs or [PRIMARY_TF]), **HEALTHY)
    payload["operators"] = {
        "enabled": True,
        "distance": {"enabled": False},
        "cross": {"enabled": True},
        "momentum": {"enabled": False},
        "ratio": {"enabled": True},
        "binary_signal": {"enabled": False},
        "worldquant": {"enabled": False},
    }
    payload["lag_features"] = {"enabled": False}  # L4 延遲欄於本票驗收無用途，關閉以控時長
    pre = payload["preprocessing"]
    pre["fractional_differencing"] = {"enabled": fracdiff, "apply_to": "non_stationary"}
    pre["adf_differencing"] = {"enabled": adf, "apply_to": "non_stationary"}
    if cross_sectional:
        payload["cross_sectional"] = {"enabled": True}
    payload.update(overrides)
    return payload


def run_stat(tmp_path: Path, payload: Dict[str, Any], *, start_date: Optional[str] = WINDOW[0],
             end_date: str = WINDOW[1], primary_tf: str = PRIMARY_TF, persist: bool = True,
             force_regenerate: bool = True, kline_dir: str = KLINE_DIR) -> Tuple[Path, Any, Any]:
    """真實 kline 之 generate_features；回傳 (features_root, factory, result)。`start_date=None` 驗 Task 2.3；
    `kline_dir` 指向真實 kline 之 tmp 複本以驗洩漏證偽（改值只改複本）。"""
    root = tmp_path / "features"
    factory = create_feature_factory(cache_dir=kline_dir, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    result = factory.generate_features(
        SYMBOL, primary_tf, config_override=payload, force_regenerate=force_regenerate,
        start_date=start_date, end_date=end_date, persist=persist,
    )
    return root, factory, result


def decisions(result: Any) -> Dict[str, Dict[str, Any]]:
    """結果 metadata 之逐欄平穩化決策（契約 `metadata_keys.decisions`；Task 4.1 收據同源）。"""
    return dict(result.metadata[META["decisions"]])


def snapshot_tree(root: Path) -> Dict[str, str]:
    """目錄下每個檔之相對路徑 → sha256（零寫入斷言用）。"""
    import hashlib

    out: Dict[str, str] = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def kline_frame(symbol: str = SYMBOL, timeframe: str = PRIMARY_TF):
    """讀真實 `kline_cache.h5` 之 `<symbol>/<tf>/data` 為 DataFrame（UTC DatetimeIndex 升序；來源欄 float64）。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(Path(KLINE_DIR) / "kline_cache.h5", "r") as f:
        arr = f[symbol][timeframe]["data"][()]
    ts = arr["timestamp"].astype("int64")
    unit = "ms" if ts.max() > 10**12 else "s"
    idx = pd.to_datetime(ts, unit=unit, utc=True)
    cols = [n for n in arr.dtype.names if n != "timestamp"]
    frame = pd.DataFrame({c: arr[c].astype(np.float64) for c in cols}, index=idx)
    return frame.sort_index()


def kline_copy(tmp_path: Path) -> Path:
    """真實 kline 之 tmp 複本目錄（洩漏證偽：只改複本之值）。"""
    import shutil

    target = tmp_path / "klines"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(KLINE_DIR) / "kline_cache.h5", target / "kline_cache.h5")
    return target


def scale_kline_close(kline_dir: Path, start: str, end: str, factor: float, *, symbol: str = SYMBOL,
                      timeframe: str = PRIMARY_TF) -> int:
    """把複本中 `[start, end)` 之 close 乘以 `factor`（原地改複本）；回傳改動列數。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(kline_dir / "kline_cache.h5", "r+") as f:
        ds = f[symbol][timeframe]["data"]
        arr = ds[()]
        ts = arr["timestamp"].astype("int64")
        unit = "ms" if ts.max() > 10**12 else "s"
        idx = pd.to_datetime(ts, unit=unit, utc=True)
        mask = (idx >= pd.Timestamp(start, tz="UTC")) & (idx < pd.Timestamp(end, tz="UTC"))
        arr["close"][np.asarray(mask)] = arr["close"][np.asarray(mask)] * np.float32(factor)
        ds[...] = arr
        return int(mask.sum())
