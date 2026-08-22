"""ICHC B4 診斷（臨時）：timestamps 構造 vs filter_base index 對齊檢查。"""
import sys
from pathlib import Path

import h5py
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.momentum.helpers.ichc_run import fixture_paths  # noqa: E402

h5, _ = fixture_paths()
with h5py.File(h5, "r") as handle:
    ts = handle["ETHUSDT/12h/timestamps"][:5]
print("raw int64 head:", ts.tolist())
print("as unit=s:", pd.to_datetime(ts, unit="s")[:3].tolist())
print("as unit=ms:", pd.to_datetime(ts, unit="ms")[:3].tolist())

from momentum.factories import create_kline_storage_manager  # noqa: E402

kr = create_kline_storage_manager(cache_dir="data_cache/feature_klines")
raw = kr.read_klines("ETHUSDT", "12h")
print("raw kline shape:", raw.shape)
print("raw kline cols:", list(raw.columns)[:10])
print("raw index head:", raw.index[:2].tolist(), raw.index.dtype)
if "timestamp" in raw.columns:
    print("timestamp col head:", raw["timestamp"].head(2).tolist(), raw["timestamp"].dtype)
