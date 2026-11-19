"""TESTSEL I8 Task 2.3①（docs/TESTSEL_I8_SPEC.md）：L2 worldquant 運算元逐運算元截斷不變（無 look-ahead）。

業界寫法：對每個截斷點 t，以前綴 series[:t+1] 計算之第 0..t 列 == 全序列計算之第 0..t 列（逐位元，NaN 位置相同）。
被測經產品入口 `DerivedOperatorEngine.compute_all`（`momentum/FeatureEngineering/operators/derived_operators.py`
`_apply_worldquant`）：ts_argmax／ts_argmin（numba 快路徑 `operators/_worldquant_numba.py` 與 pandas 退路）、ts_rank、
decay_linear、ts_corr（corr_with＝volume），窗 5／13／21（預設最大 21），L1 欄帶 NaN 前綴。資料＝真實 kline
BTCUSDT 1h 末 1,500 根（`data_cache/feature_klines/kline_cache.h5`），禁合成 fixture。
改壞對照：ts_argmax 核心改為「窗含 t+1」⇒ 比對須抓到（偵測力證明，非空轉）。
"""
from __future__ import annotations

from typing import List

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_kline_storage_manager
from momentum.FeatureEngineering.operators import _worldquant_numba as wq
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine

KLINE_CACHE_DIR = "data_cache/feature_klines"

N_BARS = 1500
CUT_STEP = 37
WINDOWS = [5, 13, 21]
OPERATORS = ["ts_argmax", "ts_argmin", "ts_rank", "decay_linear", "ts_corr"]
_OFF = ("distance", "cross", "ratio", "momentum", "binary_signal", "signed_strength")


def _engine_config() -> dict:
    cfg = {k: {"enabled": False} for k in _OFF}
    cfg["worldquant"] = {"enabled": True, "apply_to": "all", "windows": WINDOWS, "operators": OPERATORS,
                         "transforms": [], "corr_with": "volume"}
    return cfg


@pytest.fixture(scope="module")
def inputs() -> tuple:
    df = create_kline_storage_manager(cache_dir=KLINE_CACHE_DIR).read_klines("BTCUSDT", "1h", validate_continuity=False)
    if df is None or len(df) < N_BARS:
        pytest.fail(f"真實 kline 不足：BTCUSDT/1h 需 ≥{N_BARS} 根")
    df = df.iloc[-N_BARS:]
    idx = pd.Index(np.arange(N_BARS), name="ts")
    close = pd.Series(df["close"].to_numpy(dtype=np.float64), index=idx)
    volume = pd.Series(df["volume"].to_numpy(dtype=np.float64), index=idx)
    ema8 = close.ewm(span=8, adjust=False).mean()
    ema8.iloc[:7] = np.nan  # NaN 前綴（L1 預熱）
    layer1 = pd.DataFrame({"close_trend_EMA_8": ema8,
                           "close_momentum_RSI_14": close.pct_change().rolling(14).mean()})
    raw = pd.DataFrame({"close": close, "volume": volume})
    return layer1, raw


def _mismatched_cuts(layer1: pd.DataFrame, raw: pd.DataFrame) -> List[int]:
    engine_cfg = _engine_config()
    full = DerivedOperatorEngine(engine_cfg).compute_all(layer1, raw)
    assert full.shape[1] == len(layer1.columns) * len(WINDOWS) * len(OPERATORS)
    bad: List[int] = []
    for t in list(range(25, N_BARS, CUT_STEP)) + [N_BARS - 1]:
        part = DerivedOperatorEngine(engine_cfg).compute_all(layer1.iloc[: t + 1], raw.iloc[: t + 1])
        a = full.iloc[: t + 1][part.columns].to_numpy()
        b = part.to_numpy()
        if not ((a == b) | (np.isnan(a) & np.isnan(b))).all():
            bad.append(t)
    return bad


def test_worldquant_truncation_invariant_numba_path(inputs: tuple) -> None:
    assert wq.HAS_NUMBA, "前提：numba 快路徑可用（產品預設路徑）"
    assert _mismatched_cuts(*inputs) == []


def test_worldquant_truncation_invariant_pandas_path(inputs: tuple, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wq, "HAS_NUMBA", False)
    assert _mismatched_cuts(*inputs) == []


def test_mutation_ts_argmax_window_includes_next_bar_is_caught(inputs: tuple,
                                                               monkeypatch: pytest.MonkeyPatch) -> None:
    orig = wq._ts_argmax_2d

    def leaky(arr: np.ndarray, window: int) -> np.ndarray:
        return orig(np.vstack([arr[1:], arr[-1:]]), window)

    monkeypatch.setattr(wq, "_ts_argmax_2d", leaky)
    assert _mismatched_cuts(*inputs), "窗含 t+1 之 mutant 未被抓到 ⇒ 比對無偵測力"
