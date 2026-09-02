"""Feature Factory 頁之 K 線下載鏈（`-k feature_kline_download_chain`）。

出生事故（2026-09-02 使用者提問）：使用者忘了 `data_cache/feature_klines/kline_cache.h5`
是從哪個頁面下載的、兩邊格式是否相同。查證發現 FF／IC／事件分析**全數只讀這一份**，
而產生它的那條鏈（`FeatureKlineService` → provider → `KlineDownloadService` →
`KlineStorageManager`）**沒有任何自動化測試**——今天能用是靠一份手跑收據
（`handoffs/run_receipts/20260902T012246Z-ff-kline-download-e2e.json`），
下次有人動 `kline_storage.py` 或 provider，沒有東西會喊。

🔴 **本檔只換掉 HTTP，不換掉任何轉換／寫入邏輯**：stub provider 是 `BinanceProvider`
的子類，`fetch_klines` 餵合成的幣安原始列給**真的** `_convert_to_dataframe()`，
之後走**真的** `KlineDownloadService.download_klines` 與 `KlineStorageManager`。
所以 dtype／欄位順序／`taker_ratio` 規則／HDF5 版面都是產品碼算出來的，不是測試自己寫的。

🔴 **不打網路**（PR smoke 可跑）；與真實檔之對證另以 `requires_kline` 標記（缺檔 FAIL 非 skip）。
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import List

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.providers.binance_provider import BinanceProvider

import api.services.feature_kline_service as fks_mod

SYMBOL, TF = "TESTUSDT", "12h"
TF_SEC = 12 * 3600
T0 = int(datetime(2025, 12, 1, tzinfo=timezone.utc).timestamp())

#: 契約的 on-disk compound dtype（欄名**與順序**；順序由 provider 之 `_convert_to_dataframe` 決定）。
CANONICAL_DTYPE = np.dtype([
    ("timestamp", "<i8"), ("open", "<f4"), ("high", "<f4"), ("low", "<f4"), ("close", "<f4"),
    ("volume", "<f4"), ("taker_buy_volume", "<f4"), ("taker_ratio", "<f4"),
    ("quote_volume", "<f4"), ("number_of_trades", "<i4"),
])
CANONICAL_ATTRS = {
    "data_checksum", "data_source", "is_complete", "last_updated",
    "time_range_end", "time_range_start", "timeframe", "total_bars",
}


def _raw_binance_rows(n: int, t0: int = T0) -> List[list]:
    """合成幣安 `/api/v3/klines` 原始列（12 欄），值刻意不整齊以暴露精度／順序問題。"""
    rows = []
    for i in range(n):
        ts_ms = (t0 + i * TF_SEC) * 1000
        o = 3000.0 + i * 1.37
        vol = 17000.0 + i * 13.1
        tb = vol * (0.45 + 0.01 * (i % 7))
        rows.append([
            ts_ms, f"{o:.2f}", f"{o + 5.5:.2f}", f"{o - 4.25:.2f}", f"{o + 1.11:.2f}",
            f"{vol:.3f}", ts_ms + TF_SEC * 1000 - 1, f"{vol * o:.2f}", 1200 + i,
            f"{tb:.3f}", f"{tb * o:.2f}", "0",
        ])
    return rows


class _OfflineBinance(BinanceProvider):
    """只替換 HTTP：`fetch_klines` 餵合成原始列給**真的**轉換器。"""

    def __init__(self, n_bars: int = 20) -> None:
        super().__init__()
        self.n_bars = n_bars
        self.calls: List[dict] = []

    def ping(self) -> bool:  # 不打網路
        return True

    def validate_symbol(self, symbol: str) -> bool:  # 不打網路
        return True

    def fetch_klines(self, symbol, start_time, end_time, timeframe):
        self.calls.append({"symbol": symbol, "start": start_time, "end": end_time, "tf": timeframe})
        return self._convert_to_dataframe(_raw_binance_rows(self.n_bars))


class _BrokenBinance(_OfflineBinance):
    """over 向：轉換後**少一個必要欄**，鏈必須 fail-closed、不得落檔。"""

    def fetch_klines(self, symbol, start_time, end_time, timeframe):
        df = super().fetch_klines(symbol, start_time, end_time, timeframe)
        return df.drop(columns=["taker_ratio"])


@pytest.fixture
def svc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """`FeatureKlineService` 指向暫存目錄、provider 換成離線版；其餘與產品碼逐字相同。"""
    provider = _OfflineBinance()
    monkeypatch.setattr(fks_mod, "settings", SimpleNamespace(data_cache_path=tmp_path))
    monkeypatch.setattr(fks_mod, "create_binance_provider", lambda: provider)
    service = fks_mod.FeatureKlineService()
    return service, provider, tmp_path / "feature_klines" / "kline_cache.h5"


def _run(service, symbols, timeframes, start="2025-12-01", end=None):
    task_id = service.create_download_task(symbols, timeframes, start, end)
    service.execute_download(task_id, symbols, timeframes, start, end)
    return service.get_task_status(task_id)


def test_feature_kline_download_chain_writes_canonical_hdf5(svc):
    """主條：FF 頁那條鏈跑完 ⇒ 檔在 `feature_klines/`、dtype 與 attrs 逐字等於契約形狀。"""
    service, provider, h5 = svc
    status = _run(service, [SYMBOL], [TF])
    assert status["completed_jobs"] == 1 and status["failed_jobs"] == 0, status
    assert provider.calls and provider.calls[0]["tf"] == TF
    assert h5.is_file(), f"應寫到 {h5}"
    with h5py.File(h5, "r") as f:
        ds = f[f"{SYMBOL}/{TF}/data"]
        assert ds.dtype == CANONICAL_DTYPE, ds.dtype          # 欄名、型別、**順序**三者皆比
        assert ds.shape == (provider.n_bars,)
        assert set(f[f"{SYMBOL}/{TF}"].attrs.keys()) == CANONICAL_ATTRS
        assert int(f[f"{SYMBOL}/{TF}"].attrs["total_bars"]) == provider.n_bars


def test_feature_kline_download_chain_values_survive_roundtrip(svc):
    """值層：`read_klines` 讀回 ＝ provider 產出（同 dtype），且 `taker_ratio` 遵守 provider 規則。"""
    service, provider, _ = svc
    _run(service, [SYMBOL], [TF])
    storage = KlineStorageManager(cache_dir=str(service._storage.cache_dir))
    df = storage.read_klines(SYMBOL, TF, validate_continuity=False)
    assert df is not None and len(df) == provider.n_bars
    assert list(df.columns) == list(CANONICAL_DTYPE.names)
    assert {c: str(t) for c, t in df.dtypes.items()} == KlineStorageManager.COLUMN_DTYPES
    # provider 規則：先轉 float32 再相除（見 binance_provider._convert_to_dataframe）
    expected = (df["taker_buy_volume"].astype("float32") / df["volume"].astype("float32")).astype("float32").clip(0, 1)
    assert np.array_equal(df["taker_ratio"].to_numpy(), expected.to_numpy())
    # 連續、無重複、升冪
    ts = df["timestamp"].to_numpy()
    assert np.all(np.diff(ts) == TF_SEC)


def test_feature_kline_download_chain_trims_beyond_end_date(svc):
    """本 service 獨有的邏輯：`append_klines` 只合併不截斷 ⇒ service 須主動裁掉超過 end_date 的 bar。"""
    service, provider, h5 = svc
    end = "2025-12-05"                                       # provider 會回 20 根（到 12-10），須裁到 12-05 23:59:59
    _run(service, [SYMBOL], [TF], end=end)
    end_sec = int(datetime(2025, 12, 5, 23, 59, 59, tzinfo=timezone.utc).timestamp())
    with h5py.File(h5, "r") as f:
        ts = f[f"{SYMBOL}/{TF}/data"]["timestamp"]
        assert ts.max() <= end_sec, (ts.max(), end_sec)
        assert len(ts) == 10                                 # 12-01 00:00 … 12-05 12:00 共 10 根


def test_feature_kline_download_chain_fail_closed_on_bad_provider_frame(tmp_path, monkeypatch):
    """over 向：provider 少一個必要欄 ⇒ 任務記 failed、**不得**寫出任何 dataset。"""
    monkeypatch.setattr(fks_mod, "settings", SimpleNamespace(data_cache_path=tmp_path))
    monkeypatch.setattr(fks_mod, "create_binance_provider", lambda: _BrokenBinance())
    service = fks_mod.FeatureKlineService()
    status = _run(service, [SYMBOL], [TF])
    assert status["failed_jobs"] == 1 and status["completed_jobs"] == 0, status
    h5 = tmp_path / "feature_klines" / "kline_cache.h5"
    if h5.is_file():
        with h5py.File(h5, "r") as f:
            assert f"{SYMBOL}/{TF}/data" not in f, "壞資料不得落檔"


def test_feature_kline_download_chain_listing_sees_new_symbol(svc):
    """FF 頁的「已下載清單」端點讀的就是這份檔 ⇒ 下載完必須列得出來，且筆數對。"""
    service, provider, _ = svc
    _run(service, [SYMBOL], [TF])
    rows = [r for r in service.list_downloaded() if r["symbol"] == SYMBOL and r["timeframe"] == TF]
    assert len(rows) == 1, service.list_downloaded()
    assert int(rows[0]["row_count"]) == provider.n_bars


@pytest.mark.requires_kline
def test_feature_kline_download_chain_matches_real_feature_klines_file(svc):
    """與使用者**真實**的 `feature_klines/kline_cache.h5` 對證：本鏈產出的 on-disk 形狀與它逐字相同。

    這條把「FF 頁下載的東西 ＝ FF／IC 正在讀的東西」釘死；缺檔 FAIL 非 skip（pytest.ini 之約定）。
    """
    from tests.conftest import FEATURE_KLINE_H5_PATH
    if not Path(FEATURE_KLINE_H5_PATH).is_file():
        pytest.fail(f"requires_kline: missing kline cache file: {FEATURE_KLINE_H5_PATH}")
    service, _, h5 = svc
    _run(service, [SYMBOL], [TF])
    with h5py.File(h5, "r") as new, h5py.File(FEATURE_KLINE_H5_PATH, "r") as real:
        real_ds = next(
            real[f"{s}/{t}/data"] for s in real if not s.startswith("_") for t in real[s] if "data" in real[s][t]
        )
        assert new[f"{SYMBOL}/{TF}/data"].dtype == real_ds.dtype, (new[f"{SYMBOL}/{TF}/data"].dtype, real_ds.dtype)
        assert new[f"{SYMBOL}/{TF}/data"].compression == real_ds.compression
        real_grp = real_ds.parent
        assert set(new[f"{SYMBOL}/{TF}"].attrs.keys()) == set(real_grp.attrs.keys())
