"""ICFIRSTALIGN 乙驗收之共用 helper（docs/ICFIRSTALIGN_SPEC.md v17 §G）。

真實 kline（`data_cache/feature_klines/kline_cache.h5`）；禁合成 fixture。一切寫入經 `prepare_env` 隔離於 tmp。
- S2：BTCUSDT 12h、精簡 L1（trend EMA8／SMA13）、L2 預設運算子、L3 rolling 5／13、L6.5 只縮尾、dead-drop 關。
- S2m：S2 之 training 改 [12h, 4h]。
- IC oracle：測試端獨立實作——自 raw sidecar 讀時間戳、以 kline 依時間戳算 h=1 forward return、
  依時間戳交集對齊後逐欄 Spearman（不呼叫引擎之對齊與 IC 函式）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, REPO, prepare_env

CONTRACT: Dict[str, Any] = json.loads(
    (REPO / "tests" / "_golden" / "icfirstalign" / "contract.json").read_text(encoding="utf-8")
)
SYMBOL = "BTCUSDT"
PRIMARY = "12h"
S2_WINDOW: Tuple[str, str] = ("2025-07-01", "2026-03-31")
_ATOMIC = ("trend", "momentum", "volatility", "volume", "cycle", "pattern", "statistics",
           "microstructure", "entropy", "tail_risk")


def s2_payload(training: Optional[List[str]] = None, **overrides: Any) -> Dict[str, Any]:
    """S2（training 預設 [12h]）；S2m 傳 ["12h", "4h"]。"""
    payload: Dict[str, Any] = {
        "timeframes": {"primary": PRIMARY, "training": list(training or [PRIMARY]), "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "atomic_indicators": {
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in _ATOMIC if c != "trend"},
        },
        "rolling_aggregation": {"enabled": True, "windows": [5, 13]},
        "cross_sectional": {"enabled": False},
        "preprocessing": {
            "enabled": True, "mode": "append", "causal_preprocessing": True,
            "winsorization": {"enabled": True},
            "rank_transform": {"enabled": False}, "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False}, "adf_differencing": {"enabled": False},
            "fractional_differencing": {"enabled": False},
        },
        "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        "max_nan_ratio": 1.0,
    }
    payload.update(overrides)
    return payload


def make_factory(root: Path) -> Any:
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(root))
    return factory


def generate_s2(root: Path, payload: Optional[Dict[str, Any]] = None, *, window: Tuple[str, str] = S2_WINDOW,
                **kwargs: Any) -> Tuple[Any, Any]:
    """正式生成（CGSA、persist=True）；回傳 (factory, result)。"""
    factory = make_factory(root)
    result = factory.generate_features(SYMBOL, PRIMARY, config_override=payload or s2_payload(),
                                       force_regenerate=True, start_date=window[0], end_date=window[1],
                                       persist=True, **kwargs)
    return factory, result


def run_dir(root: Path, config_hash: str, timeframe: str = PRIMARY) -> Path:
    return root / SYMBOL / timeframe / str(config_hash)


def kline_close(timeframe: str = PRIMARY) -> pd.Series:
    """真實 kline close，index＝UTC 之 tz-naive DatetimeIndex（同 sidecar 之表示）。"""
    import h5py

    with h5py.File(str(Path(KLINE_DIR) / "kline_cache.h5"), "r") as f:
        rec = f[f"/{SYMBOL}/{timeframe}/data"][:]
    idx = pd.DatetimeIndex(pd.to_datetime(rec["timestamp"], unit="s"))
    return pd.Series(np.asarray(rec["close"], dtype=np.float64), index=idx, name="close")


def forward_return_label(timeframe: str = PRIMARY) -> pd.Series:
    """h=1 forward return，依 kline 時間戳（label 預設語意）。"""
    close = kline_close(timeframe)
    return (close.shift(-1) / close - 1.0).rename("label")


def oracle_spearman(features: pd.DataFrame, label: pd.Series) -> Dict[str, float]:
    """測試端獨立 oracle：依時間戳交集對齊後逐欄 Spearman（rank → Pearson）。"""
    common = features.index.intersection(label.index)
    out: Dict[str, float] = {}
    y_full = label.loc[common].to_numpy(dtype=np.float64)
    for col in features.columns:
        x_full = features.loc[common, col].to_numpy(dtype=np.float64)
        mask = np.isfinite(x_full) & np.isfinite(y_full)
        if mask.sum() < 3:
            out[str(col)] = float("nan")
            continue
        xr = pd.Series(x_full[mask]).rank().to_numpy()
        yr = pd.Series(y_full[mask]).rank().to_numpy()
        out[str(col)] = float(np.corrcoef(xr, yr)[0, 1])
    return out


def isolated(monkeypatch: Any, tmp_path: Path, **env: str) -> Path:
    """prepare_env 隔離；回傳 features 根目錄。"""
    tmp_path.mkdir(parents=True, exist_ok=True)
    prepare_env(monkeypatch, tmp_path, **env)
    root = tmp_path / "features"
    root.mkdir(parents=True, exist_ok=True)
    return root


__all__ = [
    "CONTRACT", "SYMBOL", "PRIMARY", "S2_WINDOW", "s2_payload", "make_factory", "generate_s2", "run_dir",
    "kline_close", "forward_return_label", "oracle_spearman", "isolated", "REPO", "KLINE_DIR",
]
