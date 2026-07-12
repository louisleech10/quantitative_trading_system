"""IC API 測試共用的真實 kline fixture。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import AlignmentSpec, validate_alignment
from momentum.factories import create_kline_storage_manager


SYMBOL = "ETHUSDT"
TIMEFRAME = "12h"
CASE_ID = "ic_api_real_kline"
RETURN_TYPE = "simple"
N_ROWS = 512
MID_START = 200
HORIZON = 5
MAX_LOOKBACK = 20
MAX_FEATURE_LOOKBACK = 21
FEATURE_NAMES = [
    "log_return_1",
    "log_return_3",
    "rvol_20",
    "zscore_20",
    "hl_range",
    "oc_return",
    "close_sma_ratio_20",
]


def _write_h5(path: Path, key: str, values: np.ndarray, timestamps: np.ndarray, names: list[str]) -> None:
    """以 IC reader 使用的 flat data/ group schema 寫入。"""
    with h5py.File(path, "w") as handle:
        group = handle.create_group("data")
        group.create_dataset(key, data=values, compression="gzip")
        group.create_dataset("timestamps", data=timestamps, compression="gzip")
        name_key = "feature_names" if key == "features" else "label_names"
        dtype = h5py.string_dtype(encoding="utf-8")
        group.create_dataset(name_key, data=np.asarray(names, dtype=object), dtype=dtype)


def _feature_frame(kline: pd.DataFrame) -> pd.DataFrame:
    """只用 t 與過去資料計算特徵；rolling 右端為 t，shift 僅使用正值。"""
    close = pd.to_numeric(kline["close"], errors="coerce")
    high = pd.to_numeric(kline["high"], errors="coerce")
    low = pd.to_numeric(kline["low"], errors="coerce")
    open_ = pd.to_numeric(kline["open"], errors="coerce")
    log_close = np.log(close)
    log_return_1 = log_close - log_close.shift(1)
    close_std = close.rolling(MAX_LOOKBACK).std(ddof=0)
    return pd.DataFrame(
        {
            "log_return_1": log_return_1,
            "log_return_3": log_close - log_close.shift(3),
            "rvol_20": log_return_1.rolling(MAX_LOOKBACK).std(ddof=0),
            "zscore_20": (close - close.rolling(MAX_LOOKBACK).mean()) / close_std,
            "hl_range": (high - low) / close,
            "oc_return": close / open_ - 1.0,
            "close_sma_ratio_20": close / close.rolling(MAX_LOOKBACK).mean() - 1.0,
        },
        index=kline.index,
    )


def _validate_dataset(
    features: pd.DataFrame,
    labels: pd.Series,
    full_kline: pd.DataFrame,
) -> None:
    """驗證 finite、feature PIT oracle 與 simple forward label oracle。"""
    assert list(features.columns) == FEATURE_NAMES
    assert labels.name == "return_5"
    assert len(features) == len(labels) == N_ROWS
    assert np.isfinite(features.to_numpy(dtype=np.float64)).all()
    assert int(labels.tail(HORIZON).isna().sum()) == HORIZON
    assert labels.iloc[:-HORIZON].notna().all()

    expected_features = _feature_frame(full_kline).loc[features.index, FEATURE_NAMES]
    if not np.allclose(
        features.to_numpy(dtype=np.float64),
        expected_features.to_numpy(dtype=np.float64),
        atol=1e-12,
        rtol=1e-10,
        equal_nan=False,
    ):
        raise AssertionError("feature PIT oracle mismatch")

    close = pd.to_numeric(full_kline["close"], errors="coerce")
    spec = AlignmentSpec(
        feature_ts_col="timestamp",
        target_ts_col="timestamp",
        freq=TIMEFRAME,
        lag=HORIZON,
    )
    validate_alignment(
        features,
        labels,
        spec,
        close=close,
        sample_size=16,
        return_kind=RETURN_TYPE,
    )


def build_real_kline_frames(
    full_kline: pd.DataFrame,
    *,
    feature_shift: int = 0,
    backward_label: bool = False,
) -> tuple[pd.DataFrame, pd.Series]:
    """建立 512 軸資料；mutation 參數只供 PIT 測試證偽 self-test。"""
    full_kline = full_kline.copy()
    full_kline.index = pd.Index(
        pd.to_numeric(full_kline["timestamp"], errors="raise").astype(np.int64),
        name="timestamp",
    )
    required = MID_START + N_ROWS + HORIZON
    if len(full_kline) < required:
        pytest.fail(f"requires_kline: {SYMBOL}/{TIMEFRAME} has {len(full_kline)} rows, need >= {required}")
    calculation_start = MID_START - MAX_FEATURE_LOOKBACK
    calculation = full_kline.iloc[calculation_start:required].copy()
    computed = _feature_frame(calculation)
    if feature_shift:
        computed = computed.shift(feature_shift)
    target_index = full_kline.index[MID_START : MID_START + N_ROWS]
    features = computed.loc[target_index, FEATURE_NAMES].copy()
    close = pd.to_numeric(full_kline["close"], errors="coerce")
    if backward_label:
        labels = close / close.shift(HORIZON) - 1.0
    else:
        labels = close.shift(-HORIZON) / close - 1.0
    labels = labels.loc[target_index].rename("return_5").copy()
    labels.iloc[-HORIZON:] = np.nan
    _validate_dataset(features, labels, full_kline)
    return features, labels


@pytest.fixture(scope="session")
def ic_api_real_kline(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """讀真 ETHUSDT/12h，建立共用 IC API 輸入檔。"""
    cache = Path("data_cache/feature_klines/kline_cache.h5")
    if not cache.is_file():
        pytest.fail(f"requires_kline: missing kline cache file: {cache}")
    storage = create_kline_storage_manager(cache_dir=str(cache.parent))
    try:
        kline = storage.read_klines(SYMBOL, TIMEFRAME, validate_continuity=False)
    except Exception as exc:
        pytest.fail(f"requires_kline: failed reading {SYMBOL}/{TIMEFRAME}: {exc}")
    if kline is None or kline.empty:
        pytest.fail(f"requires_kline: no data for {SYMBOL}/{TIMEFRAME} in {cache}")

    features, labels = build_real_kline_frames(kline)
    timestamps = features.index.to_numpy(dtype=np.int64, copy=True)
    temp_dir = tmp_path_factory.mktemp(CASE_ID)
    features_path = temp_dir / "features.h5"
    labels_path = temp_dir / "labels.h5"
    meta_path = temp_dir / "meta.json"
    _write_h5(features_path, "features", features.to_numpy(dtype=np.float64), timestamps, FEATURE_NAMES)
    _write_h5(labels_path, "labels", labels.to_numpy(dtype=np.float64)[:, None], timestamps, ["return_5"])
    meta = {"symbol": SYMBOL, "timeframe": TIMEFRAME, "case_id": CASE_ID}
    meta.update(
        {
            name: {"name": name, "category": "price_derived", "layer": 1, "data_source": "kline"}
            for name in FEATURE_NAMES
        }
    )
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {
        "features_path": str(features_path),
        "labels_path": str(labels_path),
        "meta_path": str(meta_path),
        "feature_names": FEATURE_NAMES,
        "label_names": ["return_5"],
        "config_override": {"labels": {"return_type": RETURN_TYPE, "horizons": [HORIZON]}},
        "features": features,
        "labels": labels,
        "kline": kline,
    }
