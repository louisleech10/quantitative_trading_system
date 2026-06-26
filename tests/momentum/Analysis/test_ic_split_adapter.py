"""ICSplitAdapter 真實 kline 契約測試。"""

from __future__ import annotations

import h5py
import numpy as np
import pandas as pd
import pytest
from types import SimpleNamespace

from momentum.Analysis.ic_split_adapter import EmbargoRelaxedError, ICSplitAdapter
from momentum.Analysis.model_validation.combinatorial_purged_cv import (
    CombinatorialPurgedCV,
)
from momentum.Analysis.model_validation.walk_forward_validator import (
    WalkForwardValidator,
)
from momentum.core.contracts import SplitPlan, validate_split_integrity
from momentum.factories import create_ic_split_adapter


KLINE_CACHE_PATH = "data_cache/feature_klines/kline_cache.h5"


def _load_kline_frame(symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT"), limit: int = 240) -> pd.DataFrame:
    frames = []
    with h5py.File(KLINE_CACHE_PATH, "r") as handle:
        for symbol in symbols:
            data = handle[symbol]["1h"]["data"][:limit]
            frames.append(
                pd.DataFrame(
                    {
                        "symbol": symbol,
                        "timestamp": np.asarray(data["timestamp"], dtype=np.int64),
                        "close": np.asarray(data["close"], dtype=np.float64),
                        "volume": np.asarray(data["volume"], dtype=np.float64),
                    }
                )
            )
    return pd.concat(frames, ignore_index=True)


def _positions_by_symbol(frame: pd.DataFrame, symbol: str) -> np.ndarray:
    local = frame.copy()
    local["_pos"] = np.arange(len(local), dtype=int)
    return (
        local[local["symbol"] == symbol]
        .sort_values("timestamp", kind="mergesort")["_pos"]
        .to_numpy(dtype=int)
    )


def _assert_valid_pair(pair: tuple[SplitPlan, SplitPlan], frame: pd.DataFrame) -> None:
    ts = frame["timestamp"].to_numpy()
    symbols = frame["symbol"].to_numpy()
    train_plan, test_plan = pair
    validate_split_integrity(train_plan, ts, symbols)
    validate_split_integrity(test_plan, ts, symbols)
    assert np.unique(symbols[train_plan.row_index]).size == 1
    assert np.unique(symbols[test_plan.row_index]).size == 1


def test_adapter_wraps_cpcv() -> None:
    frame = _load_kline_frame(limit=240)
    cpcv = CombinatorialPurgedCV(
        config={
            "n_groups": 4,
            "n_test_groups": 1,
            "purge_gap": 2,
            "embargo_pct": 0.0,
            "max_paths": 20,
        }
    )
    adapter = create_ic_split_adapter(expected_freq="1h")

    plans = adapter.split_cpcv(cpcv, frame, feature_cols=["close", "volume"])

    assert plans
    for pair in plans:
        _assert_valid_pair(pair, frame)

    btc_positions = _positions_by_symbol(frame, "BTCUSDT")
    btc_features = (
        frame[frame["symbol"] == "BTCUSDT"]
        .sort_values("timestamp", kind="mergesort")[["close", "volume"]]
        .reset_index(drop=True)
    )
    direct_train, direct_test = next(iter(cpcv.split(btc_features)))
    btc_train_plan, btc_test_plan = plans[0]
    assert np.array_equal(btc_train_plan.row_index, btc_positions[direct_train])
    assert np.array_equal(btc_test_plan.row_index, btc_positions[direct_test])


def test_adapter_wraps_wf() -> None:
    frame = _load_kline_frame(limit=220)
    wf = WalkForwardValidator(
        config={
            "mode": "rolling",
            "train_size": 80,
            "test_size": 30,
            "step_size": 40,
            "purge_gap": 5,
            "embargo_pct": 0.0,
        }
    )
    adapter = ICSplitAdapter(expected_freq="1h")

    plans = adapter.split_wf(wf, frame)

    assert plans
    for pair in plans:
        _assert_valid_pair(pair, frame)

    btc_positions = _positions_by_symbol(frame, "BTCUSDT")
    expected_ranges = wf._generate_rolling_splits(220, 80, 30, 40)
    for pair, (train_range, test_range) in zip(plans[: len(expected_ranges)], expected_ranges):
        train_plan, test_plan = pair
        assert np.array_equal(
            train_plan.row_index,
            btc_positions[np.arange(train_range[0], train_range[1])],
        )
        assert np.array_equal(
            test_plan.row_index,
            btc_positions[np.arange(test_range[0], test_range[1])],
        )


def test_l5_wf_cross_fold_embargo_violation_raises() -> None:
    frame = _load_kline_frame(symbols=("BTCUSDT",), limit=220)
    wf = WalkForwardValidator(
        config={
            "mode": "rolling",
            "train_size": 80,
            "test_size": 30,
            "step_size": 40,
            "purge_gap": 5,
            "embargo_pct": 0.02,
        }
    )
    adapter = ICSplitAdapter(expected_freq="1h")

    with pytest.raises(EmbargoRelaxedError, match="WF train contains"):
        adapter.split_wf(wf, frame)


def test_adapter_detects_embargo_relaxation() -> None:
    frame = _load_kline_frame(symbols=("BTCUSDT",), limit=60)
    cpcv = CombinatorialPurgedCV(
        config={
            "n_groups": 3,
            "n_test_groups": 2,
            "purge_gap": 15,
            "embargo_pct": 0.1,
            "max_paths": 20,
        }
    )
    adapter = ICSplitAdapter(expected_freq="1h")

    with pytest.raises(EmbargoRelaxedError):
        adapter.split_cpcv(cpcv, frame, feature_cols=["close", "volume"])


class _FakeShiftedCPCV:
    def __init__(self) -> None:
        self.config = SimpleNamespace(
            n_groups=3,
            n_test_groups=1,
            purge_gap=0,
            embargo_pct=0.0,
            max_paths=None,
        )

    def split(self, X: pd.DataFrame):
        n_samples = len(X)
        returned_test = np.arange(1, n_samples // 3 + 1, dtype=int)
        returned_train = np.setdiff1d(np.arange(n_samples, dtype=int), returned_test)
        yield returned_train, returned_test


def test_l6_cpcv_test_boundaries_rebuilt_independently() -> None:
    frame = _load_kline_frame(symbols=("BTCUSDT",), limit=120)
    adapter = ICSplitAdapter(expected_freq="1h")

    with pytest.raises(EmbargoRelaxedError, match="test boundaries"):
        adapter.split_cpcv(_FakeShiftedCPCV(), frame, feature_cols=["close", "volume"])
