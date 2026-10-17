"""
K線數據整合服務（生產 `api.services.kline_data_service.KlineDataService`）快取決策測試

被測物是生產服務本身（storage_manager／download_service 以建構子注入）：
- 儲存層：真實 KlineStorageManager，落在 tmp_path 的獨立 HDF5。
- 上游（網路來源）：以 FakeProvider 取代 Binance，其資料來自真實 K 線
  `data_cache/feature_klines/kline_cache.h5` 的 ETHUSDT/1h 前 400 根（不打外網、不隨時間變）。
  FakeProvider 記錄每次 fetch 的區間，供斷言「是否呼叫上游／只補缺口」。

涵蓋：1 完全缺失(MISS)→下載並落快取；2 完全命中(HIT)→不呼叫上游；
3 部分命中→只補後段缺口並與快取合併無重複；4 資料完整性（欄位、時間連續、OHLC、taker_ratio）；
5 快取讀取 100 根之效能與正確性。
"""

from __future__ import annotations

import calendar
from datetime import datetime

import pandas as pd
import pytest

from api.services.kline_data_service import KlineDataService
from momentum.DataExtraction.kline_download_service import KlineDownloadService
from momentum.DataExtraction.kline_provider_base import KlineProviderBase
from momentum.factories import create_kline_storage_manager

SYMBOL = "ETHUSDT"
TF = "1h"
STEP = 3600
# 生產缺陷（見 xfail reason）僅在本機時區非 UTC 時現形；UTC 機器上該測試應直接通過
_LOCAL_TZ_NOT_UTC = datetime(2024, 1, 1).timestamp() != calendar.timegm(datetime(2024, 1, 1).timetuple())
_TZ_XFAIL = pytest.mark.xfail(
    _LOCAL_TZ_NOT_UTC,
    strict=True,
    reason="生產缺陷：KlineDataService 命中/部分命中路徑把 naive-UTC datetime 傳給 storage.read_klines，"
    "後者以 datetime.timestamp()（本機時區）解讀，非 UTC 機器讀到偏移視窗"
    "（kline_data_service.py:180、kline_storage.py:1100-1103）；見 白話說明/還沒做的事.md",
)
UPSTREAM_BARS = 400
REQUIRED_COLS = [
    "timestamp", "open", "high", "low", "close", "volume", "taker_buy_volume", "taker_ratio",
]


class FakeProvider(KlineProviderBase):
    """以真實 K 線切片充當上游；記錄 fetch 區間（timestamp 秒，含端點）。"""

    def __init__(self, upstream: pd.DataFrame):
        super().__init__(name="FakeBinance")
        self._upstream = upstream
        self.calls: list = []

    def fetch_klines(self, symbol, start_time, end_time, timeframe):
        s = calendar.timegm(start_time.timetuple())
        e = calendar.timegm(end_time.timetuple())
        self.calls.append((s, e))
        df = self._upstream[(self._upstream["timestamp"] >= s) & (self._upstream["timestamp"] <= e)]
        return df.reset_index(drop=True).copy()

    def get_rate_limit(self):
        return 1000

    def validate_symbol(self, symbol):
        return True

    def get_supported_timeframes(self):
        return [TF]

    def ping(self):
        return True


@pytest.fixture
def upstream(requires_kline_data) -> pd.DataFrame:
    df = requires_kline_data(SYMBOL, TF, min_rows=UPSTREAM_BARS)
    up = df.iloc[:UPSTREAM_BARS].reset_index(drop=True)
    assert (up["timestamp"].diff().dropna() == STEP).all(), "上游切片本身須時間連續"
    return up


@pytest.fixture
def env(tmp_path, upstream):
    storage = create_kline_storage_manager(cache_dir=str(tmp_path / "cache"))
    provider = FakeProvider(upstream)
    dl = KlineDownloadService(storage_manager=storage, failure_log_path=str(tmp_path / "fail.json"))
    dl.registry.register("binance", provider)
    svc = KlineDataService(storage_manager=storage, download_service=dl, default_source="binance")
    return svc, provider, storage, upstream


def _dt(ts: int) -> datetime:
    return datetime.utcfromtimestamp(int(ts))


def _expected(upstream: pd.DataFrame, s: int, e: int) -> pd.DataFrame:
    return upstream[(upstream["timestamp"] >= s) & (upstream["timestamp"] <= e)].reset_index(drop=True)


def _assert_same_bars(got: pd.DataFrame, exp: pd.DataFrame):
    got = got.sort_values("timestamp").reset_index(drop=True)
    assert len(got) == len(exp)
    assert got["timestamp"].tolist() == exp["timestamp"].tolist()
    for col in ["open", "high", "low", "close", "volume"]:
        pd.testing.assert_series_equal(
            got[col].astype("float64"), exp[col].astype("float64"), check_names=False
        )


def test_1_first_request_cache_miss(env):
    """完全缺失：呼叫上游一次、回傳與上游同值、並落入儲存層（metadata 涵蓋請求範圍）。"""
    svc, provider, storage, up = env
    t0 = int(up["timestamp"].iloc[10])
    t1 = t0 + 99 * STEP  # 100 根

    assert storage.get_metadata(SYMBOL, TF) is None
    df = svc.get_kline_data(SYMBOL, TF, _dt(t0), _dt(t1))

    assert len(provider.calls) == 1
    _assert_same_bars(df, _expected(up, t0, t1))
    assert len(df) == 100
    meta = storage.get_metadata(SYMBOL, TF)
    assert meta is not None
    assert meta["time_range_start"] <= t0 and meta["time_range_end"] >= t1


@_TZ_XFAIL
def test_2_second_request_cache_hit(env):
    """完全命中：子區間請求不得再呼叫上游，且值等於上游同區間。"""
    svc, provider, storage, up = env
    t0 = int(up["timestamp"].iloc[10])
    t1 = t0 + 99 * STEP
    svc.get_kline_data(SYMBOL, TF, _dt(t0), _dt(t1))
    assert len(provider.calls) == 1

    s2, e2 = t0 + 20 * STEP, t0 + 67 * STEP  # 48 根，在快取內
    df = svc.get_kline_data(SYMBOL, TF, _dt(s2), _dt(e2))

    assert len(provider.calls) == 1, "完全命中不應再呼叫上游"
    _assert_same_bars(df, _expected(up, s2, e2))
    assert len(df) == 48


@_TZ_XFAIL
def test_3_partial_cache_incremental_download(env):
    """部分命中：只向上游補快取之後的缺口（不重抓已快取段），合併結果連續、無重複，快取同步延伸。"""
    svc, provider, storage, up = env
    t0 = int(up["timestamp"].iloc[10])
    cache_end = t0 + 99 * STEP
    svc.get_kline_data(SYMBOL, TF, _dt(t0), _dt(cache_end))
    provider.calls.clear()

    s2 = cache_end - 50 * STEP
    e2 = cache_end + 10 * STEP
    df = svc.get_kline_data(SYMBOL, TF, _dt(s2), _dt(e2))

    assert len(provider.calls) == 1, "只應補後段缺口一次"
    gap_s, gap_e = provider.calls[0]
    assert gap_s == cache_end + STEP, "缺口應從快取末根的下一根開始（避免重抓）"
    assert gap_e == e2

    _assert_same_bars(df, _expected(up, s2, e2))
    assert df["timestamp"].is_unique
    assert len(df) == 61
    meta = storage.get_metadata(SYMBOL, TF)
    assert meta["time_range_end"] >= e2


def test_4_data_integrity_validation(env):
    """回傳資料完整性：必要欄位、時間嚴格等距遞增、OHLC 合理、taker_ratio∈[0,1]；非法區間 ValueError。"""
    svc, provider, storage, up = env
    t0 = int(up["timestamp"].iloc[5])
    t1 = t0 + 119 * STEP
    df = svc.get_kline_data(SYMBOL, TF, _dt(t0), _dt(t1), validate_integrity=True)

    assert [c for c in REQUIRED_COLS if c not in df.columns] == []
    assert (df["timestamp"].diff().dropna() == STEP).all()
    assert (df["high"] >= df["low"]).all()
    assert (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    assert (df["low"] <= df[["open", "close"]].min(axis=1)).all()
    assert df["taker_ratio"].between(0, 1).all()

    # start >= end 為參數錯誤
    with pytest.raises(ValueError):
        svc.get_kline_data(SYMBOL, TF, _dt(t1), _dt(t0))
    # 不支援之 timeframe 秒數換算
    with pytest.raises(ValueError):
        svc._get_timeframe_seconds("7x")
    assert svc._get_timeframe_seconds(TF) == STEP


@_TZ_XFAIL
def test_5_performance_benchmark(env):
    """快取讀取 100 根：不呼叫上游、筆數與值正確，且耗時 < 100ms（原驗收門檻，不放寬）。"""
    import time

    svc, provider, storage, up = env
    t0 = int(up["timestamp"].iloc[0])
    t1 = t0 + 199 * STEP
    svc.get_kline_data(SYMBOL, TF, _dt(t0), _dt(t1))
    provider.calls.clear()

    s2, e2 = t0 + 30 * STEP, t0 + 129 * STEP  # 100 根
    t_start = time.perf_counter()
    df = svc.get_kline_data(SYMBOL, TF, _dt(s2), _dt(e2))
    elapsed = time.perf_counter() - t_start

    assert provider.calls == []
    assert len(df) == 100
    _assert_same_bars(df, _expected(up, s2, e2))
    assert elapsed < 0.100
