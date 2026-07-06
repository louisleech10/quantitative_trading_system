"""FeatureLibrary row_index attach 測試(第二刀首項 bug)。

驗證 `load` V2 路徑貼回持久化時間軸:
- helper 機制(attach / no-op / length-guard):快、可證偽、mutation-sensitive。
- 真實 12h run 端到端(G-1 值守恆 / G-2 時間軸 byte-equal):artifact 缺則 skip。

mutation 對照(見 SPEC §V):
- 移除 `df.index = row_index` → `test_attach_sets_datetime_index` FAIL。
- 移除長度檢查 → `test_attach_length_mismatch_raises` FAIL。
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "e53e22906c35363757f4cd49d27f973e"
MINI_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1] / "fixtures" / "ic_run_selector_mini_registry.json"
)


@pytest.fixture
def pinned_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    registry_copy = tmp_path / "registry.json"
    registry_copy.write_text(MINI_REGISTRY_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(registry_copy))
    return registry_copy


# ---------------------------------------------------------------------------
# helper 機制:小 df + 假 reader,不需真實巨量載入
# ---------------------------------------------------------------------------


def _small_df(n: int) -> pd.DataFrame:
    return pd.DataFrame({"f0": np.arange(n, dtype=float), "f1": np.arange(n, dtype=float) * 2})


def test_attach_sets_datetime_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """reader 回真時間軸 → index 變 DatetimeIndex(name=timestamp),值不變。"""
    lib = create_feature_library()
    df = _small_df(3)
    values_before = df.to_numpy(copy=True)
    axis = pd.DatetimeIndex(pd.to_datetime([0, 43200, 86400], unit="s"))
    monkeypatch.setattr(lib._reader, "load_row_index_v2", lambda *a, **k: axis)

    lib._attach_row_index(SYMBOL, TIMEFRAME, HASH_A, df)

    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.name == "timestamp"
    assert np.array_equal(df.index.view("int64") // 10**9, np.array([0, 43200, 86400]))
    # 值守恆:attach 只改 index,不重排/不動值
    assert np.array_equal(df.to_numpy(), values_before)


def test_attach_noop_when_row_index_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """舊 run(reader 回 None)→ index 維持原 RangeIndex,不 raise。"""
    lib = create_feature_library()
    df = _small_df(3)
    monkeypatch.setattr(lib._reader, "load_row_index_v2", lambda *a, **k: None)

    lib._attach_row_index(SYMBOL, TIMEFRAME, HASH_A, df)

    assert isinstance(df.index, pd.RangeIndex)


def test_attach_length_mismatch_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """sidecar 長度 != df → ValueError,不靜默貼錯位時間。"""
    lib = create_feature_library()
    df = _small_df(3)
    short_axis = pd.DatetimeIndex(pd.to_datetime([0, 43200], unit="s"))  # len 2 != 3
    monkeypatch.setattr(lib._reader, "load_row_index_v2", lambda *a, **k: short_axis)

    with pytest.raises(ValueError, match="row_index length mismatch"):
        lib._attach_row_index(SYMBOL, TIMEFRAME, HASH_A, df)


# ---------------------------------------------------------------------------
# 真實 12h run:端到端 G-1/G-2(artifact 缺則 skip)
# ---------------------------------------------------------------------------


def _require_materialized(lib) -> None:
    if lib._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")
    try:
        axis = lib._reader.load_row_index_v2(SYMBOL, TIMEFRAME, HASH_A, artifact_kind="raw")
    except Exception as exc:  # noqa: BLE001 - artifact 缺是 skip 條件非測試失敗
        pytest.skip(f"row_index artifact unreadable: {exc}")
    if axis is None:
        pytest.skip("run has no persisted row_index (old run)")


@pytest.mark.ic_run_selector
def test_load_real_run_attaches_persisted_axis(pinned_registry: Path) -> None:
    """G-2:load 回的 index 與持久化 timestamps.parquet byte-equal。"""
    lib = create_feature_library()
    _require_materialized(lib)
    df = lib.load(SYMBOL, TIMEFRAME, config_hash=HASH_A)
    axis = lib._reader.load_row_index_v2(SYMBOL, TIMEFRAME, HASH_A, artifact_kind="raw")

    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.name == "timestamp"
    assert len(df) == len(axis)
    assert np.array_equal(
        df.index.view("int64") // 10**9, axis.view("int64") // 10**9
    )


@pytest.mark.ic_run_selector
def test_load_real_run_value_conservation(pinned_registry: Path) -> None:
    """G-1:attach 不動特徵值——抽樣欄位與 reader 直讀 parquet 逐值相等。"""
    lib = create_feature_library()
    _require_materialized(lib)
    df = lib.load(SYMBOL, TIMEFRAME, config_hash=HASH_A)

    # 獨立 oracle:直接向 reader 取同批抽樣欄位(不經 attach 路徑)
    sample_cols = list(df.columns[:: max(1, len(df.columns) // 50)])[:50]
    raw = lib._reader.load_columns_v2(
        SYMBOL, TIMEFRAME, HASH_A, sample_cols, artifact_kind="raw", consumer="browse"
    )
    # reader 直讀為位置序;attach 只改 label 不改序 → 逐位置值須相等
    got = df[sample_cols].to_numpy()
    exp = raw[sample_cols].to_numpy()
    assert got.shape == exp.shape
    assert np.array_equal(got, exp, equal_nan=True)
