"""TESTSEL I1b｜SPEC Task 1.7：K 線寫入路徑之 taker_ratio 決定性——provider 與舊快取匯入兩路徑逐位元相同，
且等於單一定義（float64 解析相除、一次捨入為 float32、clip [0,1]、volume≤0 ⇒ 0.5）。

錄製物：tests/fixtures/binance_raw/ETHUSDT_1h_1716235200000_500.json＝Binance GET /api/v3/klines 原始回應（數值欄為字串，
provider 轉型前擷取；runs/testsel_route/i1b/record_binance_raw.py）。I1b 實測：同源資料兩路徑 534／1,762 列差 1 ulp
（runs/testsel_route/i1b/i1b_facts.md ④）。實作前 accept／boundary 為紅（provider 仍 float32 先除；compute_taker_ratio 空殼）。
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.DataExtraction import taker_ratio as tr
from momentum.DataExtraction.kline_storage import KlineStorageManager
from momentum.DataExtraction.providers.binance_provider import BinanceProvider

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "binance_raw" / "ETHUSDT_1h_1716235200000_500.json"


def _raw() -> list:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["klines"]


def _definition(raw: list) -> np.ndarray:
    v = np.array([float(k[5]) for k in raw], dtype=np.float64)
    tb = np.array([float(k[9]) for k in raw], dtype=np.float64)
    with np.errstate(all="ignore"):
        out = np.where(v > 0, tb / v, 0.5)
    return np.clip(out, 0, 1).astype(np.float32)


def _provider_ratio(raw: list) -> np.ndarray:
    provider = BinanceProvider.__new__(BinanceProvider)
    return provider._convert_to_dataframe(raw)["taker_ratio"].to_numpy(dtype=np.float32)


def _legacy_ratio(raw: list, tmp_path: Path) -> np.ndarray:
    """以舊快取格式（DatetimeIndex、float64 欄、key='data'）寫入 tmp，經產品 `_import_from_legacy_cache` 匯入後讀回。"""
    idx = pd.to_datetime([k[0] for k in raw], unit="ms")
    legacy = pd.DataFrame({
        "open": [float(k[1]) for k in raw], "high": [float(k[2]) for k in raw], "low": [float(k[3]) for k in raw],
        "close": [float(k[4]) for k in raw], "volume": [float(k[5]) for k in raw], "close_time": [k[6] for k in raw],
        "quote_asset_volume": [float(k[7]) for k in raw], "number_of_trades": [int(k[8]) for k in raw],
        "taker_buy_base_asset_volume": [float(k[9]) for k in raw], "taker_buy_quote_asset_volume": [float(k[10]) for k in raw],
        "ignore": [k[11] for k in raw],
    }, index=idx)
    legacy_dir = tmp_path / "legacy"
    legacy_dir.mkdir()
    legacy.to_hdf(legacy_dir / "ETHUSDT_1h.h5", key="data")
    mgr = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    mgr.legacy_cache_dir = legacy_dir
    assert mgr._import_from_legacy_cache("ETHUSDT", "1h")
    df = mgr.read_klines("ETHUSDT", "1h", validate_continuity=False)
    return df["taker_ratio"].to_numpy(dtype=np.float32)


def test_accept_01_provider_equals_single_definition() -> None:
    """provider 路徑（錄製原始 JSON）逐位元等於單一定義，且與 decimal 精確商相差 ≤ 1 float32 ulp。"""
    raw = _raw()
    got = _provider_ratio(raw)
    assert got.tobytes() == _definition(raw).tobytes()
    exact = np.array([float(Decimal(k[9]) / Decimal(k[5])) if Decimal(k[5]) > 0 else 0.5 for k in raw])
    assert np.all(np.abs(got.astype(np.float64) - exact) <= np.abs(np.spacing(got)).astype(np.float64))


def test_accept_02_legacy_import_equals_provider(tmp_path: Path) -> None:
    """舊快取匯入路徑與 provider 路徑對同源資料之 taker_ratio 逐位元相同（現況 provider float32 先除而不同）。"""
    raw = _raw()
    assert _legacy_ratio(raw, tmp_path).tobytes() == _provider_ratio(raw).tobytes()


def test_accept_03_function_is_single_definition() -> None:
    """`compute_taker_ratio` 等於定義（兩路徑共用之單一函式）。"""
    raw = _raw()
    v = [float(k[5]) for k in raw]
    tb = [float(k[9]) for k in raw]
    assert np.asarray(tr.compute_taker_ratio(v, tb)).astype(np.float32).tobytes() == _definition(raw).tobytes()


def test_boundary_01_zero_volume_is_half_both_paths(tmp_path: Path) -> None:
    """邊界①：volume＝0 ⇒ 兩路徑皆 0.5。"""
    raw = [list(k) for k in _raw()[:20]]
    raw[3][5] = "0.00000000"; raw[3][9] = "0.00000000"
    assert _provider_ratio(raw)[3] == np.float32(0.5)
    assert _legacy_ratio(raw, tmp_path)[3] == np.float32(0.5)


def test_boundary_02_taker_above_volume_clipped_to_one_both_paths(tmp_path: Path) -> None:
    """邊界②：taker_buy_volume > volume（資料異常）⇒ clip 為 1.0，兩路徑相同。"""
    raw = [list(k) for k in _raw()[:20]]
    raw[5][9] = str(float(raw[5][5]) * 1.5)
    assert _provider_ratio(raw)[5] == np.float32(1.0)
    assert _legacy_ratio(raw, tmp_path)[5] == np.float32(1.0)


def test_boundary_03_existing_stored_data_not_rewritten(tmp_path: Path) -> None:
    """邊界③：既有庫內資料不重寫——讀取已存組不重算 taker_ratio（只修寫入路徑）。"""
    mgr = KlineStorageManager(cache_dir=str(tmp_path / "store"))
    df = BinanceProvider.__new__(BinanceProvider)._convert_to_dataframe(_raw()[:50])
    df.loc[0, "taker_ratio"] = np.float32(0.123456)  # 已存值（模擬舊算法結果）
    mgr.write_klines("ETHUSDT", "1h", df)
    back = mgr.read_klines("ETHUSDT", "1h", validate_continuity=False)
    assert back["taker_ratio"].to_numpy(dtype=np.float32)[0] == np.float32(0.123456)


def test_mutation_provider_float32_division_breaks_equality(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞對照：單一定義換成 float32 先除（provider 舊算法）⇒ 錄製資料上與定義不再逐位元相等。"""
    def _f32_first(volume, taker_buy_volume):
        v = np.asarray(volume, dtype=np.float32)
        tb = np.asarray(taker_buy_volume, dtype=np.float32)
        with np.errstate(all="ignore"):
            return np.clip(np.where(v > 0, tb / v, np.float32(0.5)), 0, 1).astype(np.float32)

    monkeypatch.setattr(tr, "compute_taker_ratio", _f32_first)
    raw = _raw()
    # 經 provider 路徑（審查 r1 P1-02：負對照須覆蓋「provider 改回」，provider 須經模組參照呼叫 taker_ratio.compute_taker_ratio）
    assert _provider_ratio(raw).tobytes() != _definition(raw).tobytes()
