"""FeatureLibrary row_index attach 測試(第二刀首項 bug)。

驗證 `load` V2 路徑貼回持久化時間軸:
- helper 機制(attach / no-op / length-guard):快、可證偽、mutation-sensitive。
- 真實 12h run 端到端(G-1 值守恆 / G-2 時間軸 byte-equal):session fixture `tmp_feature_runs`
  (tests/momentum/conftest.py)以真實 kline 於 tmp 物化之小型 BTCUSDT 12h run;registry 條目／
  row_index artifact 缺則 fail-closed(不 skip;原釘選之 e53e2290… artifact 已依 2026-10-03 裁定刪除,
  舊寫法恆 skip、斷言從未執行)。

mutation 對照(見 SPEC §V):
- 移除 `df.index = row_index` → `test_attach_sets_datetime_index` FAIL。
- 移除長度檢查 → `test_attach_length_mismatch_raises` FAIL。
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
# helper 機制測試之 config_hash 引數(假 reader,不讀資料,hash 值無關)。
HASH_A = "e53e22906c35363757f4cd49d27f973e"


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch, tmp_feature_runs: Dict[str, Any]) -> Dict[str, Any]:
    """指向 tmp registry 並 chdir 至 tmp root(`create_feature_library()` 之相對 data_cache/features 解析到 tmp)。"""
    if (tmp_feature_runs["symbol"], tmp_feature_runs["timeframe"]) != (SYMBOL, TIMEFRAME):
        raise RuntimeError("tmp_feature_runs 之 symbol/timeframe 與本檔常數不符")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_feature_runs["registry"]))
    monkeypatch.chdir(tmp_feature_runs["root"])
    return tmp_feature_runs


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
# 真實 12h run(tmp 物化):端到端 G-1/G-2(資料缺則 fail-closed)
# ---------------------------------------------------------------------------


def _require_materialized(lib, config_hash: str) -> None:
    """物化 run 須已登記且帶持久化 row_index;缺則 fail-closed(不 skip)。"""
    if lib._registry.get(SYMBOL, TIMEFRAME, config_hash) is None:
        pytest.fail("missing registry run(tmp 物化資料缺失 ⇒ fail-closed)")
    try:
        persisted = lib._reader.load_row_index_v2(SYMBOL, TIMEFRAME, config_hash, artifact_kind="raw")
    except Exception as exc:  # noqa: BLE001 - artifact 缺＝物化資料缺失 ⇒ fail-closed
        pytest.fail(f"row_index artifact unreadable: {exc}")
    if persisted is None:
        pytest.fail("materialized run has no persisted row_index")


@pytest.mark.ic_run_selector
def test_load_real_run_attaches_persisted_axis(runs: Dict[str, Any]) -> None:
    """G-2:load 回的 index 與持久化 timestamps.parquet byte-equal。"""
    lib = create_feature_library()
    _require_materialized(lib, runs["hash_a"])
    df = lib.load(SYMBOL, TIMEFRAME, config_hash=runs["hash_a"])
    axis = lib._reader.load_row_index_v2(SYMBOL, TIMEFRAME, runs["hash_a"], artifact_kind="raw")

    assert isinstance(df.index, pd.DatetimeIndex)
    assert df.index.name == "timestamp"
    assert len(df) == len(axis)
    assert np.array_equal(
        df.index.view("int64") // 10**9, axis.view("int64") // 10**9
    )
    # 獨立 oracle:持久化時間軸＝生成當下之主時間軸(epoch 秒;非由 load 路徑導出)
    gen_seconds = runs["index_a"]
    assert np.array_equal(df.index.view("int64") // 10**9, gen_seconds)


@pytest.mark.ic_run_selector
def test_load_real_run_value_conservation(runs: Dict[str, Any]) -> None:
    """G-1:attach 不動特徵值——全部欄位與 reader 直讀 parquet 逐值相等。"""
    lib = create_feature_library()
    _require_materialized(lib, runs["hash_a"])
    df = lib.load(SYMBOL, TIMEFRAME, config_hash=runs["hash_a"])

    # 獨立 oracle:直接向 reader 取同批欄位(不經 attach 路徑);小型 tmp run ⇒ 全欄比對(原抽樣 ≤50 欄)
    sample_cols = list(df.columns)
    raw = lib._reader.load_columns_v2(
        SYMBOL, TIMEFRAME, runs["hash_a"], sample_cols, artifact_kind="raw", consumer="browse"
    )
    # reader 直讀為位置序;attach 只改 label 不改序 → 逐位置值須相等
    got = df[sample_cols].to_numpy()
    exp = raw[sample_cols].to_numpy()
    assert got.shape == exp.shape
    assert np.array_equal(got, exp, equal_nan=True)
    # 逐欄 dtype 不變(attach 不得轉型)
    got_dtypes, exp_dtypes = list(df[sample_cols].dtypes), list(raw[sample_cols].dtypes)
    assert got_dtypes == exp_dtypes
