"""IC Phase 1 G3 真實 kline split/leakage golden。"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import (
    CrossSymbolLeakageError,
    SplitPlan,
    TimestampDiscontinuityError,
    split_per_symbol,
    validate_split_integrity,
)


KLINE_CACHE_PATH = Path("data_cache/feature_klines/kline_cache.h5")
SYMBOLS = ("BTCUSDT", "ETHUSDT")


def _load_symbol_frame(symbol: str, limit: int = 40) -> pd.DataFrame:
    with h5py.File(KLINE_CACHE_PATH, "r") as handle:
        data = handle[symbol]["1h"]["data"][:limit]
    return pd.DataFrame(
        {
            "symbol": symbol,
            "timestamp": np.asarray(data["timestamp"], dtype=np.int64),
            "close": np.asarray(data["close"], dtype=np.float64),
        }
    )


def _multi_symbol_frame(limit: int = 40) -> pd.DataFrame:
    return pd.concat(
        [_load_symbol_frame(symbol, limit=limit) for symbol in SYMBOLS],
        ignore_index=True,
    )


def _make_plan(
    *,
    symbol: str,
    row_index: np.ndarray,
    ts: np.ndarray,
    split_label: str = "train",
) -> SplitPlan:
    return SplitPlan(
        split_label=split_label,
        index_kind="positional",
        row_index=row_index,
        time_bounds=(ts[row_index[0]], ts[row_index[-1]]) if row_index.size else (None, None),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="g3-real-kline-btc-eth-1h",
        symbol=symbol,
    )


def test_split_leakage_golden() -> None:
    """真實 BTC+ETH kline 的 split 洩漏 golden，反例必 fail-closed。"""
    frame = _multi_symbol_frame(limit=32)
    ts = frame["timestamp"].to_numpy()
    symbols = frame["symbol"].to_numpy()

    positive_rows = frame.index[frame["symbol"] == "BTCUSDT"].to_numpy()[:12]
    positive_plan = _make_plan(symbol="BTCUSDT", row_index=positive_rows, ts=ts)

    validate_split_integrity(
        positive_plan,
        ts,
        symbols,
        allowed_symbols=set(SYMBOLS),
    )
    assert (symbols[positive_plan.row_index] == "BTCUSDT").mean() == 1.0
    assert np.array_equal(positive_plan.row_index, np.arange(12))

    sorted_but_multi_symbol = (
        _multi_symbol_frame(limit=16)
        .sort_values(["timestamp", "symbol"], kind="mergesort")
        .reset_index(drop=True)
    )
    with pytest.raises(CrossSymbolLeakageError):
        validate_split_integrity(
            _make_plan(
                symbol="BTCUSDT",
                row_index=np.arange(len(sorted_but_multi_symbol)),
                ts=sorted_but_multi_symbol["timestamp"].to_numpy(),
            ),
            sorted_but_multi_symbol["timestamp"].to_numpy(),
            sorted_but_multi_symbol["symbol"].to_numpy(),
            allowed_symbols=set(SYMBOLS),
        )

    gapped = _load_symbol_frame("BTCUSDT", limit=28).drop(index=[10, 11, 12]).reset_index(drop=True)
    with pytest.raises(TimestampDiscontinuityError):
        validate_split_integrity(
            _make_plan(
                symbol="BTCUSDT",
                row_index=np.arange(len(gapped)),
                ts=gapped["timestamp"].to_numpy(),
            ),
            gapped["timestamp"].to_numpy(),
            gapped["symbol"].to_numpy(),
            allowed_symbols=set(SYMBOLS),
        )

    unsorted = _load_symbol_frame("BTCUSDT", limit=18)
    unsorted = pd.concat([unsorted.iloc[:8], unsorted.iloc[[10, 9]], unsorted.iloc[11:]])
    unsorted = unsorted.reset_index(drop=True)
    with pytest.raises(TimestampDiscontinuityError):
        validate_split_integrity(
            _make_plan(
                symbol="BTCUSDT",
                row_index=np.arange(len(unsorted)),
                ts=unsorted["timestamp"].to_numpy(),
            ),
            unsorted["timestamp"].to_numpy(),
            unsorted["symbol"].to_numpy(),
            allowed_symbols=set(SYMBOLS),
        )

    duplicated = _load_symbol_frame("BTCUSDT", limit=18)
    duplicated.loc[9, "timestamp"] = duplicated.loc[8, "timestamp"]
    with pytest.raises(TimestampDiscontinuityError):
        validate_split_integrity(
            _make_plan(
                symbol="BTCUSDT",
                row_index=np.arange(len(duplicated)),
                ts=duplicated["timestamp"].to_numpy(),
            ),
            duplicated["timestamp"].to_numpy(),
            duplicated["symbol"].to_numpy(),
            allowed_symbols=set(SYMBOLS),
        )


def test_split_per_symbol_golden() -> None:
    """split_per_symbol 對真實多 symbol kline 不跨界、不誤殺連續資料。"""
    frame = _multi_symbol_frame(limit=24)

    def splitter(group: pd.DataFrame) -> Iterable[tuple[np.ndarray, np.ndarray]]:
        assert group["symbol"].nunique() == 1
        yield np.arange(0, 10), np.arange(12, 16)

    plans = split_per_symbol(
        frame,
        splitter,
        "symbol",
        "timestamp",
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="g3-real-kline-btc-eth-1h",
        allowed_symbols=set(SYMBOLS),
    )

    assert len(plans) == len(SYMBOLS)
    expected_train_sets = {
        "BTCUSDT": np.arange(0, 10),
        "ETHUSDT": np.arange(24, 34),
    }
    ts = frame["timestamp"].to_numpy()
    symbols = frame["symbol"].to_numpy()
    for train_plan, test_plan in plans:
        validate_split_integrity(train_plan, ts, symbols, allowed_symbols=set(SYMBOLS))
        validate_split_integrity(test_plan, ts, symbols, allowed_symbols=set(SYMBOLS))
        assert (symbols[train_plan.row_index] == train_plan.symbol).mean() == 1.0
        assert (symbols[test_plan.row_index] == test_plan.symbol).mean() == 1.0
        assert np.array_equal(train_plan.row_index, expected_train_sets[train_plan.symbol])
        train_local_max = int(np.searchsorted(np.flatnonzero(symbols == train_plan.symbol), train_plan.row_index).max())
        test_local_min = int(np.searchsorted(np.flatnonzero(symbols == test_plan.symbol), test_plan.row_index).min())
        assert train_local_max < test_local_min - test_plan.purge_gap
