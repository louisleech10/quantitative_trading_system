"""
測試存儲路徑修復
驗證批次下載使用統一的存儲路徑，數據不會互相覆蓋

TESTREG b5 改寫：原版全函式無 assert（以 return True／False 表結果，失敗分支仍綠）、
真連 Binance 網路，且寫入真實 `settings.data_cache_path` 之 ETHUSDT 1h HDF5（非 hermetic、
會污染應用層 K 線快取）。現改為：
- 落盤根改 `tmp_path`（同一個 storage 物件同時供下載服務寫入與讀回＝統一路徑）；
- provider 以 `BinanceProvider` 子類**重播真實 Binance K 線**（唯讀取自
  `data_cache/feature_klines/kline_cache.h5` 之同時段 bars），不連網、不造假資料；
- 以 assert 驗兩段時間範圍皆在、總列數逐筆吻合、兩段之值與下載回傳逐值相等（append 合併不覆蓋）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.providers.binance_provider import BinanceProvider

_REAL_KLINE_DIR = Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines"
_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume", "taker_buy_volume", "taker_ratio"]


class _ReplayBinanceProvider(BinanceProvider):
    """重播真實 Binance K 線之 provider（不連網）：fetch_klines 回傳真實快取中同時段之 bars。"""

    def __init__(self, recorded: pd.DataFrame) -> None:
        super().__init__()
        self._recorded = recorded

    def ping(self) -> bool:  # 不打網路
        return True

    def fetch_klines(self, symbol, start_time, end_time, timeframe="1h"):
        start = int(start_time.replace(tzinfo=timezone.utc).timestamp())
        end = int(end_time.replace(tzinfo=timezone.utc).timestamp())
        ts = self._recorded["timestamp"]
        return self._recorded[(ts >= start) & (ts <= end)].reset_index(drop=True).copy()


def _recorded_eth_1h() -> pd.DataFrame:
    if not (_REAL_KLINE_DIR / "kline_cache.h5").exists():
        pytest.fail(f"真實 K 線快取缺席：{_REAL_KLINE_DIR / 'kline_cache.h5'}")
    reader = KlineStorageManager(cache_dir=str(_REAL_KLINE_DIR))
    data = reader.read_klines("ETHUSDT", "1h", validate_continuity=False)
    assert data is not None and not data.empty
    return data[_COLUMNS].copy()


def test_unified_storage_path(tmp_path: Path):
    """測試統一存儲路徑：兩段不重疊之下載依序 append 到同一 HDF5，後者不得覆蓋前者。"""
    storage = KlineStorageManager(cache_dir=str(tmp_path / "data_cache"))
    assert Path(storage.hdf5_path).resolve().is_relative_to(tmp_path.resolve())

    download_service = KlineDownloadService(storage_manager=storage)
    assert download_service.storage is storage, "下載服務須寫入同一個 storage（統一路徑）"
    download_service.registry.register("binance", _ReplayBinanceProvider(_recorded_eth_1h()))

    symbol = "ETHUSDT"
    timeframe = "1h"

    # 步驟1: 下載範圍1 (2024年5月 - 歷史數據)
    df1 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2024, 5, 20, 20, 0),
        end_time=datetime(2024, 5, 27, 12, 0),
        source="binance",
        save_to_storage=True,  # 會調用 append_klines
    )
    assert len(df1) > 0, "前提不成立：真實快取無範圍1之 bars"
    check1 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    assert check1 is not None and len(check1) == len(df1), "範圍1數據未落盤"

    # 步驟2: 下載範圍2 (2025年10月 - 近期數據)
    df2 = download_service.download_klines(
        symbol=symbol,
        timeframe=timeframe,
        start_time=datetime(2025, 10, 20, 20, 0),
        end_time=datetime(2025, 10, 27, 12, 0),
        source="binance",
        save_to_storage=True,  # 會調用 append_klines，應該合併而非覆蓋
    )
    assert len(df2) > 0, "前提不成立：真實快取無範圍2之 bars"
    assert df1["timestamp"].max() < df2["timestamp"].min(), "前提不成立：兩段範圍重疊"

    # 關鍵檢查：應該包含兩個範圍
    check2 = storage.read_klines(symbol, timeframe, validate_continuity=False)
    assert check2 is not None
    assert len(check2) == len(df1) + len(df2), (
        f"數據總量異常: 期望 {len(df1) + len(df2)}（{len(df1)} + {len(df2)}），實際 {len(check2)}"
    )
    assert check2["timestamp"].is_monotonic_increasing and check2["timestamp"].is_unique

    for label, expected in (("範圍1", df1), ("範圍2", df2)):
        got = check2[
            (check2["timestamp"] >= expected["timestamp"].min())
            & (check2["timestamp"] <= expected["timestamp"].max())
        ].reset_index(drop=True)
        assert len(got) == len(expected), f"{label}數據丟失（被覆蓋）"
        np.testing.assert_array_equal(
            got["timestamp"].to_numpy(dtype=np.int64),
            expected["timestamp"].to_numpy(dtype=np.int64),
        )
        for column in ("open", "high", "low", "close", "volume"):
            np.testing.assert_allclose(
                got[column].to_numpy(dtype=np.float64),
                expected[column].to_numpy(dtype=np.float64),
                rtol=0,
                atol=0,
                err_msg=f"{label} {column} 值被改寫",
            )
