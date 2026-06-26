"""IC SplitPlan 契約測試。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import h5py

from momentum.core.contracts import (
    CrossSymbolLeakageError,
    SplitPlan,
    SplitPairLeakageError,
    TimestampDiscontinuityError,
    validate_split_integrity,
    validate_split_pair_integrity,
)


KLINE_CACHE_PATH = "data_cache/feature_klines/kline_cache.h5"


def _load_kline_timestamps(symbol: str, limit: int = 80) -> np.ndarray:
    with h5py.File(KLINE_CACHE_PATH, "r") as handle:
        data = handle[symbol]["1h"]["data"][:limit]
    return np.asarray(data["timestamp"], dtype=np.int64)


def test_splitplan_fields() -> None:
    plan = SplitPlan(
        split_label="train",
        index_kind="timestamp",
        row_index=np.array([0, 1, 2]),
        time_bounds=("2024-01-01", "2024-01-03"),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    assert plan.split_label == "train"
    assert plan.index_kind == "timestamp"
    assert plan.purge_semantic == "rows"
    assert plan.expected_freq == "1h"
    assert plan.base_universe_hash == "hash-1"
    assert plan.symbol == "BTCUSDT"
    assert isinstance(plan.row_index, np.ndarray)


def test_splitplan_requires_base_universe_hash() -> None:
    with pytest.raises(ValueError, match="base_universe_hash"):
        SplitPlan(
            split_label="train",
            index_kind="timestamp",
            row_index=np.array([0, 1, 2]),
            time_bounds=("2024-01-01", "2024-01-03"),
            purge_gap=1,
            embargo=0,
            base_universe_hash="",
        )


def test_splitplan_allows_empty_row_index() -> None:
    plan = SplitPlan(
        split_label="test",
        index_kind="timestamp",
        row_index=np.array([], dtype=int),
        time_bounds=(None, None),
        purge_gap=0,
        embargo=0,
        base_universe_hash="hash-1",
    )

    assert len(plan.row_index) == 0


def test_splitplan_rejects_purge_gap_covering_segment() -> None:
    with pytest.raises(ValueError, match="purge_gap"):
        SplitPlan(
            split_label="val",
            index_kind="positional",
            row_index=np.array([10, 11]),
            time_bounds=(10, 11),
            purge_gap=2,
            embargo=0,
            base_universe_hash="hash-1",
        )


def test_splitplan_rejects_invalid_index_kind() -> None:
    with pytest.raises(ValueError, match="index_kind"):
        SplitPlan(
            split_label="train",
            index_kind="ordinal",  # type: ignore[arg-type]
            row_index=np.array([0, 1, 2]),
            time_bounds=(0, 2),
            purge_gap=0,
            embargo=0,
            base_universe_hash="hash-1",
        )


def test_cross_symbol_purge_blocked() -> None:
    btc_ts = _load_kline_timestamps("BTCUSDT", 30)
    eth_ts = _load_kline_timestamps("ETHUSDT", 30)
    ts = np.concatenate([btc_ts, eth_ts])
    symbols = np.asarray(["BTCUSDT"] * len(btc_ts) + ["ETHUSDT"] * len(eth_ts))
    plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(CrossSymbolLeakageError):
        validate_split_integrity(plan, ts, symbols)


def test_sorted_grouped_but_multi_symbol_blocked() -> None:
    btc_ts = _load_kline_timestamps("BTCUSDT", 25)
    eth_ts = _load_kline_timestamps("ETHUSDT", 25)
    ts = np.concatenate([btc_ts, eth_ts])
    symbols = np.asarray(["BTCUSDT"] * len(btc_ts) + ["ETHUSDT"] * len(eth_ts))
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(CrossSymbolLeakageError):
        validate_split_integrity(plan, ts, symbols)


def test_single_symbol_gap_blocked() -> None:
    ts = np.delete(_load_kline_timestamps("BTCUSDT", 40), np.s_[10:13])
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(TimestampDiscontinuityError):
        validate_split_integrity(plan, ts, symbols)


def test_unsorted_dup_ts_blocked() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 20)
    ts[8] = ts[7]
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(TimestampDiscontinuityError):
        validate_split_integrity(plan, ts, symbols)


def test_single_symbol_positive_symbol_purity_is_one() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 40)
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    validate_split_integrity(plan, ts, symbols)
    assert np.unique(symbols[plan.row_index]).tolist() == ["BTCUSDT"]


def test_l1_rows_purge_requires_expected_freq() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 20)
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.arange(len(ts)),
        time_bounds=(ts[0], ts[-1]),
        purge_gap=1,
        embargo=0,
        expected_freq=None,
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(TimestampDiscontinuityError, match="expected_freq"):
        validate_split_integrity(plan, ts, symbols)


def test_l2_pair_integrity_blocks_train_inside_test_embargo() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 40)
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    train_plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2, 14]),
        time_bounds=(ts[0], ts[14]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )
    test_plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.arange(10, 13),
        time_bounds=(ts[10], ts[12]),
        purge_gap=1,
        embargo=2,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(SplitPairLeakageError):
        validate_split_pair_integrity(train_plan, test_plan, ts, symbols)


def test_l2_interleaved_multisymbol_local_ordinal() -> None:
    base_ts = pd.date_range("2024-01-01", periods=20, freq="1h")
    ts = np.repeat(base_ts.astype("int64") // 1_000_000_000, 2)
    symbols = np.asarray(["BTCUSDT", "ETHUSDT"] * len(base_ts), dtype=object)
    train_plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([10, 12, 14, 16, 18]),
        time_bounds=(ts[10], ts[18]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )
    test_plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([20, 22]),
        time_bounds=(ts[20], ts[22]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(SplitPairLeakageError):
        validate_split_pair_integrity(train_plan, test_plan, ts, symbols)


def test_l2_interleaved_multisymbol_far_train_passes() -> None:
    base_ts = pd.date_range("2024-01-01", periods=20, freq="1h")
    ts = np.repeat(base_ts.astype("int64") // 1_000_000_000, 2)
    symbols = np.asarray(["BTCUSDT", "ETHUSDT"] * len(base_ts), dtype=object)
    train_plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([0, 2, 4, 6, 8]),
        time_bounds=(ts[0], ts[8]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )
    test_plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([20, 22]),
        time_bounds=(ts[20], ts[22]),
        purge_gap=1,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    validate_split_pair_integrity(train_plan, test_plan, ts, symbols)


def test_l3_empty_row_index_still_requires_symbol() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 10)
    symbols = np.asarray(["BTCUSDT"] * len(ts))
    plan = SplitPlan(
        split_label="train",
        index_kind="positional",
        row_index=np.asarray([], dtype=int),
        time_bounds=(None, None),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol=None,
    )

    with pytest.raises(CrossSymbolLeakageError, match="symbol"):
        validate_split_integrity(plan, ts, symbols)


def test_l4_nan_symbol_group_fails_closed() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 12)
    symbols = np.asarray(["BTCUSDT"] * len(ts), dtype=object)
    symbols[3] = pd.NA
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(CrossSymbolLeakageError, match="missing"):
        validate_split_integrity(plan, ts, symbols)


def test_l4_pandas_na_repr_fails_closed() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 12)
    symbols = np.asarray(["<NA>"] * len(ts), dtype=object)
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="<NA>",
    )

    with pytest.raises(CrossSymbolLeakageError, match="missing"):
        validate_split_integrity(plan, ts, symbols)


def test_l4_bytes_symbol_decodes_before_purity_check() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 12)
    symbols = np.asarray([b"BTCUSDT"] * len(ts), dtype=object)
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    validate_split_integrity(plan, ts, symbols)


@pytest.mark.parametrize("sentinel", ["nan", "NaN", "null", "None", "na", "n/a", "   "])
def test_l4_string_sentinel_symbols_fail_closed(sentinel: str) -> None:
    ts = _load_kline_timestamps("BTCUSDT", 12)
    symbols = np.asarray([sentinel] * len(ts), dtype=object)
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol=sentinel,
    )

    with pytest.raises(CrossSymbolLeakageError):
        validate_split_integrity(plan, ts, symbols)


def test_l4_normal_symbol_with_whitespace_normalizes() -> None:
    ts = _load_kline_timestamps("BTCUSDT", 12)
    symbols = np.asarray([" BTCUSDT "] * len(ts), dtype=object)
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    validate_split_integrity(plan, ts, symbols)


def test_l4_allowlist_rejects_unknown_symbol() -> None:
    btc_ts = _load_kline_timestamps("BTCUSDT", 12)
    eth_ts = _load_kline_timestamps("ETHUSDT", 12)
    ts = np.concatenate([btc_ts, eth_ts])
    symbols = np.asarray(["BTCUSDT"] * len(btc_ts) + ["ETHUSDT"] * len(eth_ts))
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    with pytest.raises(CrossSymbolLeakageError, match="allowed_symbols"):
        validate_split_integrity(plan, ts, symbols, allowed_symbols={"BTCUSDT"})


def test_l4_allowlist_accepts_known() -> None:
    btc_ts = _load_kline_timestamps("BTCUSDT", 12)
    eth_ts = _load_kline_timestamps("ETHUSDT", 12)
    ts = np.concatenate([btc_ts, eth_ts])
    symbols = np.asarray(["BTCUSDT"] * len(btc_ts) + ["ETHUSDT"] * len(eth_ts))
    plan = SplitPlan(
        split_label="test",
        index_kind="positional",
        row_index=np.asarray([0, 1, 2]),
        time_bounds=(ts[0], ts[2]),
        purge_gap=0,
        embargo=0,
        expected_freq="1h",
        base_universe_hash="hash-1",
        symbol="BTCUSDT",
    )

    validate_split_integrity(
        plan,
        ts,
        symbols,
        allowed_symbols={"BTCUSDT", "ETHUSDT"},
    )
