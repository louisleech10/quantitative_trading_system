"""FeatureLibrary config_hash 消歧與向後相容測試。

資料：session fixture `tmp_feature_runs`（tests/momentum/conftest.py）以真實 kline 於 tmp 物化之小型 run——
BTCUSDT 12h 兩個不同 config（A：L3 rolling 5／13；B：L3 rolling 5，最後生成⇒最新）＋ETHUSDT 12h（A）。
原釘選之真實 run（e53e2290…／f754aad4…）已依 2026-10-03 裁定刪除，舊寫法恆 skip、斷言從未執行。
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import FeatureNotFoundError
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"


@pytest.fixture
def runs(monkeypatch: pytest.MonkeyPatch, tmp_feature_runs: Dict[str, Any]) -> Dict[str, Any]:
    """指向 tmp registry 並 chdir 至 tmp root（`create_feature_library()` 之相對 data_cache/features 解析到 tmp）。

    前提不符以 raise 報 fixture 錯誤（fail-closed；不用 assert／pytest.fail，免混入各測試之斷言序號化）。"""
    if (tmp_feature_runs["symbol"], tmp_feature_runs["timeframe"]) != (SYMBOL, TIMEFRAME):
        raise RuntimeError("tmp_feature_runs 之 symbol/timeframe 與本檔常數不符")
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_feature_runs["registry"]))
    monkeypatch.chdir(tmp_feature_runs["root"])
    registry = create_feature_library()._registry
    for symbol, key in ((SYMBOL, "hash_a"), (SYMBOL, "hash_b"), ("ETHUSDT", "hash_eth")):
        if registry.get(symbol, TIMEFRAME, tmp_feature_runs[key]) is None:
            raise RuntimeError(f"tmp 物化之 run 未登記: {symbol}/{TIMEFRAME}/{tmp_feature_runs[key]}")
    return tmp_feature_runs


def _assert_frames_byte_equal(got: pd.DataFrame, exp: pd.DataFrame) -> None:
    """欄集合／欄序／dtype／index 相等，且逐欄值之原始位元組相等（含 NaN 位元型樣）。"""
    assert list(got.columns) == list(exp.columns)
    assert list(got.dtypes) == list(exp.dtypes)
    assert got.index.equals(exp.index)
    for col in got.columns:
        a = np.ascontiguousarray(got[col].to_numpy())
        b = np.ascontiguousarray(exp[col].to_numpy())
        assert a.tobytes() == b.tobytes(), f"欄 {col} 值位元組不等"


@pytest.mark.ic_run_selector
def test_load_with_config_hash_disambig(runs: Dict[str, Any]) -> None:
    library = create_feature_library()
    df_a = library.load(SYMBOL, TIMEFRAME, config_hash=runs["hash_a"])
    df_b = library.load(SYMBOL, TIMEFRAME, config_hash=runs["hash_b"])
    assert len(df_a) == len(df_b)
    assert df_a.shape[1] != df_b.shape[1]
    # 消歧須取到各自 run：B（rolling 5）之欄為 A（rolling 5／13）之真子集，A 獨有 13 窗欄
    assert set(df_b.columns) < set(df_a.columns)
    # 各自時間軸＝各自生成當下之主時間軸（epoch 秒；載入端獨立比對）
    gen_seconds_a, gen_seconds_b = runs["index_a"], runs["index_b"]
    assert isinstance(df_a.index, pd.DatetimeIndex) and isinstance(df_b.index, pd.DatetimeIndex)
    assert np.array_equal(df_a.index.view("int64") // 10**9, gen_seconds_a)
    assert np.array_equal(df_b.index.view("int64") // 10**9, gen_seconds_b)


@pytest.mark.ic_run_selector
@pytest.mark.backward_compat
def test_load_without_config_hash_matches_find_latest_materialized(runs: Dict[str, Any]) -> None:
    library = create_feature_library()
    latest = library._registry.find_latest_materialized(SYMBOL, TIMEFRAME)
    assert latest is not None
    df_default = library.load(SYMBOL, TIMEFRAME)
    df_latest = library.load(SYMBOL, TIMEFRAME, config_hash=str(latest["config_hash"]))
    assert df_default.shape == df_latest.shape
    assert list(df_default.columns) == list(df_latest.columns)
    _assert_frames_byte_equal(df_default, df_latest)
    # 兩個 run 並存時 latest 須為最後生成之 B（非任意一筆），且未給 config_hash 不得落到較舊之 A
    newest_hash, older_hash = runs["hash_b"], runs["hash_a"]
    assert str(latest["config_hash"]) == newest_hash
    df_older = library.load(SYMBOL, TIMEFRAME, config_hash=older_hash)
    assert list(df_default.columns) != list(df_older.columns)


@pytest.mark.ic_run_selector
def test_load_multi_without_config_hashes_byte_stable(runs: Dict[str, Any]) -> None:
    library = create_feature_library()
    symbols = ["BTCUSDT", "ETHUSDT"]
    loaded = library.load_multi(symbols, TIMEFRAME)
    assert set(loaded.keys()) == set(symbols)
    for frame in loaded.values():
        assert not frame.empty
    # byte 穩定：重載結果與首載逐位元相等；且各 symbol 等於以其最新 run 單獨載入之結果
    reloaded = create_feature_library().load_multi(symbols, TIMEFRAME)
    expected_hash = {"BTCUSDT": runs["hash_b"], "ETHUSDT": runs["hash_eth"]}
    for symbol in symbols:
        _assert_frames_byte_equal(reloaded[symbol], loaded[symbol])
        single_frame = library.load(symbol, TIMEFRAME, config_hash=expected_hash[symbol])
        _assert_frames_byte_equal(loaded[symbol], single_frame)
    # 跨 symbol 隔離：兩 symbol 同設定 A 之欄集合相同但值不同（未混用同一 run）
    eth_frame = loaded["ETHUSDT"]
    btc_frame_a = library.load("BTCUSDT", TIMEFRAME, config_hash=runs["hash_a"])
    assert list(eth_frame.columns) == list(btc_frame_a.columns)
    assert not np.array_equal(eth_frame.to_numpy(), btc_frame_a.to_numpy(), equal_nan=True)


@pytest.mark.ic_run_selector
def test_explicit_config_hash_missing_artifacts_fail_closed(runs: Dict[str, Any]) -> None:
    library = create_feature_library()
    bogus_hash = "deadbeefdeadbeefdeadbeefdeadbeef"
    with pytest.raises(FeatureNotFoundError, match="config_hash not found"):
        library.load(SYMBOL, TIMEFRAME, config_hash=bogus_hash)
