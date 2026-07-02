"""P1-FF-7 — wrapper path correctness and multi-engine path evidence."""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import pytest
import talib
import pyarrow.parquet as pq

from momentum.FeatureEngineering.atomic.talib_input_semantics import (
    C12_EXCLUDED_INDICATORS,
    C12_MAVP_ALLOWLIST,
    arrays_from_dataframe,
    build_talib_input_semantics,
)
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_storage import (
    L7_ENCODING_REGISTRY_METADATA_KEY,
    FeatureStorage,
)
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.factories import create_feature_factory


def _numeric_kline(requires_kline_data, *, rows: int = 180) -> pd.DataFrame:
    df = requires_kline_data("BTCUSDT", "12h", min_rows=max(rows, 200)).tail(rows).copy()
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _assert_common_numeric_equal(left: pd.DataFrame, right: pd.DataFrame, *, atol: float = 1e-6) -> None:
    common = [column for column in left.columns if column in right.columns]
    assert common, "no common numeric output columns"
    assert left.index.equals(right.index)
    for column in common:
        lvals = left[column].to_numpy(dtype=float)
        rvals = right[column].to_numpy(dtype=float)
        assert np.array_equal(np.isnan(lvals), np.isnan(rvals)), f"NaN mask differs: {column}"
        finite = np.isfinite(lvals) & np.isfinite(rvals)
        if finite.any():
            np.testing.assert_allclose(lvals[finite], rvals[finite], rtol=1e-5, atol=atol)


@pytest.mark.requires_kline
def test_v7_1_full_registry_prepare_inputs_match_semantics(requires_kline_data) -> None:
    """V7.1：全 registry 的 input semantics 與獨立語義表 byte-equal。"""
    data = _numeric_kline(requires_kline_data)
    semantics = build_talib_input_semantics([])
    TALibWrapper.initialize()

    for spec in TALibWrapper.list_indicators():
        if spec.computed_in_adapter or spec.name in C12_MAVP_ALLOWLIST:
            continue
        assert spec.name in semantics, f"missing semantics for {spec.name}"
        expected = arrays_from_dataframe(spec.name, data)
        params: dict[str, Any] = dict(spec.default_params)
        actual, _ = TALibWrapper._prepare_inputs(spec, data, "close", params)
        assert len(actual) == len(expected), spec.name
        for actual_array, expected_array in zip(actual, expected):
            np.testing.assert_array_equal(actual_array, expected_array, err_msg=spec.name)


@pytest.mark.requires_kline
@pytest.mark.parametrize(
    ("indicator", "params"),
    [
        ("PLUS_DI", {"timeperiod": 14}),
        ("MINUS_DM", {"timeperiod": 14}),
        ("AROON", {"timeperiod": 14}),
        ("MIDPRICE", {"timeperiod": 14}),
        ("MFI", {"timeperiod": 14}),
        ("SAREXT", {}),
        ("VAR", {"timeperiod": 5, "nbdev": 1}),
        ("TSF", {"timeperiod": 14}),
        ("CDLDOJI", {}),
    ],
)
def test_v7_1_wrapper_matches_talib_direct_for_representatives(
    requires_kline_data,
    indicator: str,
    params: dict[str, Any],
) -> None:
    """V7.1：代表性 wrapper output 與 talib direct-call 一致。"""
    data = _numeric_kline(requires_kline_data)
    if indicator in C12_EXCLUDED_INDICATORS:
        pytest.skip("price_transform tested separately")
    wrapper = TALibWrapper.compute(indicator, data, params).to_numpy(dtype=float)
    direct_inputs = arrays_from_dataframe(indicator, data)
    direct = getattr(talib, TALibWrapper.get_indicator_spec(indicator).talib_func)(
        *direct_inputs,
        **params,
    )
    if isinstance(direct, tuple):
        direct_array = np.column_stack([np.asarray(item, dtype=float) for item in direct])
    else:
        direct_array = np.asarray(direct, dtype=float).reshape(-1, 1)
    np.testing.assert_allclose(wrapper, direct_array, equal_nan=True, rtol=1e-10, atol=1e-10)


@pytest.mark.requires_kline
def test_v7_1_price_transform_policy_and_mavp_params(requires_kline_data) -> None:
    """V7.1：price_transform policy 與 MAVP periods 特例。"""
    data = _numeric_kline(requires_kline_data)
    expected_transforms = {
        "AVGPRICE": (
            (data["open"] + data["high"] + data["low"] + data["close"]) / 4.0,
            ("open", "high", "low", "close"),
        ),
        "MEDPRICE": ((data["high"] + data["low"]) / 2.0, ("high", "low")),
        "TYPPRICE": (
            (data["high"] + data["low"] + data["close"]) / 3.0,
            ("high", "low", "close"),
        ),
        "WCLPRICE": (
            (data["high"] + data["low"] + 2.0 * data["close"]) / 4.0,
            ("high", "low", "close"),
        ),
    }
    for name, (expected, columns) in expected_transforms.items():
        assert TALibWrapper.compute(name, data, {}).empty
        direct = getattr(talib, name)(*[data[col].to_numpy(dtype=float) for col in columns])
        np.testing.assert_allclose(expected.to_numpy(dtype=float), direct, rtol=1e-12, atol=1e-12)

    periods = np.full(len(data), 7.0)
    params = {"periods": periods.copy(), "minperiod": 2, "maxperiod": 30, "matype": 0}
    result = TALibWrapper.compute("MAVP", data, params)
    assert "periods" in params
    assert len(result) == len(data)
    assert result.shape[1] == 1


@pytest.mark.requires_kline
def test_v7_2_l2_polars_and_pandas_paths_match_with_sentinel(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """V7.2：L2 polars vs pandas 等值，且 polars path sentinel 有命中。"""
    pytest.importorskip("polars")
    import momentum.FeatureEngineering.polars_adapter as polars_adapter

    raw = _numeric_kline(requires_kline_data, rows=90)
    layer1 = pd.DataFrame(
        {
            "close_trend_EMA_8": raw["close"].ewm(span=8, adjust=False).mean(),
            "close_trend_EMA_21": raw["close"].ewm(span=21, adjust=False).mean(),
            "close_momentum_RSI_14": pd.Series(talib.RSI(raw["close"].to_numpy(dtype=float), timeperiod=14), index=raw.index),
        },
        index=raw.index,
    )
    factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    config = factory._resolve_config(
        {
            "operators": {
                "enabled": True,
                "ratio": {"enabled": True},
                "cross": {"enabled": True},
                "momentum": {"enabled": True, "lags": [1, 3]},
                "distance": {"enabled": True},
                "binary_signal": {"enabled": True},
                "signed_strength": {"enabled": True},
                "worldquant": {"enabled": False},
            },
            "nan_strategy": {"l7_dead_feature_drop": {"enabled": False}},
        }
    )

    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: False)
    pandas_result, _, _ = factory._layer2_derived_pandas(layer1, raw, config)

    calls = {"polars": 0}
    original = DerivedOperatorEngine.compute_all_polars

    def _counting_polars(self: DerivedOperatorEngine, *args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["polars"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(DerivedOperatorEngine, "compute_all_polars", _counting_polars)
    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: True)
    polars_result = factory._layer2_derived_features(layer1, raw, config).data

    assert calls["polars"] >= 1
    _assert_common_numeric_equal(pandas_result, polars_result, atol=1e-5)

    def _forbidden_pandas(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise AssertionError("pandas fallback should not run when polars is enabled")

    calls["polars"] = 0
    monkeypatch.setattr(DerivedOperatorEngine, "compute_all", _forbidden_pandas)
    _ = factory._layer2_derived_features(layer1, raw, config).data
    assert calls["polars"] >= 1


def test_v7_3_l3_numba_multi_single_and_pandas_paths_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V7.3：L3 numba multi/single 與 pandas fallback 等值，sentinel 命中。"""
    rows = 80
    idx = pd.RangeIndex(rows)
    frame = pd.DataFrame(
        {
            "close_trend_EMA_8": np.linspace(1.0, 2.0, rows),
            "close_momentum_RSI_14": np.sin(np.linspace(0.0, 6.0, rows)) + 3.0,
            "close_volatility_ATR_14": np.linspace(2.0, 1.0, rows) ** 2,
        },
        index=idx,
    )
    config = {
        "windows": [5, 13],
        "aggregators": ["mean", "std", "min", "max", "range", "zscore", "rank", "skew", "kurt"],
    }
    import momentum.FeatureEngineering.operators.numba_rolling as numba_rolling

    calls = {"multi": 0, "single": 0}
    original_multi = numba_rolling.fused_rolling_stats_multi_window
    original_single = numba_rolling.fused_rolling_stats

    def _counting_multi(values: np.ndarray, windows: np.ndarray) -> np.ndarray:
        calls["multi"] += 1
        return original_multi(values, windows)

    def _counting_single(values: np.ndarray, window: int) -> np.ndarray:
        calls["single"] += 1
        return original_single(values, window)

    monkeypatch.setattr(numba_rolling, "fused_rolling_stats_multi_window", _counting_multi)
    monkeypatch.setattr(numba_rolling, "fused_rolling_stats", _counting_single)

    monkeypatch.setenv("FFACT_L3_STREAMING", "1")
    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "1")
    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "1")
    multi = RollingAggregator(config).compute_all(frame)
    assert calls["multi"] >= 1

    monkeypatch.setenv("FFACT_L3_MULTI_WINDOW", "0")
    single = RollingAggregator(config).compute_all(frame)
    assert calls["single"] >= 1

    monkeypatch.setenv("FFACT_USE_NUMBA_ROLLING", "0")
    pandas_result = RollingAggregator(config).compute_all(frame)

    _assert_common_numeric_equal(pandas_result, multi, atol=1e-5)
    _assert_common_numeric_equal(pandas_result, single, atol=1e-5)


def _l65_frame() -> pd.DataFrame:
    rows = 96
    return pd.DataFrame(
        {
            "L1_close_trend_EMA_8": np.linspace(1.0, 3.0, rows),
            "L1_close_momentum_RSI_14": np.sin(np.linspace(0.0, 8.0, rows)) + 2.0,
        }
    )


def _l65_config(*, fracdiff: bool = False) -> dict[str, Any]:
    return {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {"enabled": True, "method": "sigma", "window": 8, "sigma_k": 3.0},
        "rank_transform": {"enabled": True, "window": 8},
        "adaptive_zscore": {"enabled": True, "windows": [8]},
        "gaussian_normalize": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": fracdiff, "cache_d_star": False},
    }


def test_v7_3_l65_polars_optimized_and_fracdiff_serial_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """V7.3：L6.5 polars/numba_fast/serial-fracdiff 互斥路徑有 sentinel。"""
    pytest.importorskip("polars")
    import momentum.FeatureEngineering.polars_adapter as polars_adapter

    frame = _l65_frame()
    calls = {"polars": 0, "optimized": 0, "fracdiff": 0}
    original_polars = FeaturePreprocessor._transform_single_polars
    original_optimized = FeaturePreprocessor._transform_single_optimized_df
    original_serial = FeaturePreprocessor._apply_fractional_differencing_serial

    def _counting_polars(self: FeaturePreprocessor, features_df: pd.DataFrame) -> pd.DataFrame:
        calls["polars"] += 1
        return original_polars(self, features_df)

    def _counting_optimized(self: FeaturePreprocessor, features_df: pd.DataFrame) -> pd.DataFrame:
        calls["optimized"] += 1
        return original_optimized(self, features_df)

    def _counting_serial(self: FeaturePreprocessor, *args: Any, **kwargs: Any) -> pd.DataFrame:
        calls["fracdiff"] += 1
        return original_serial(self, *args, **kwargs)

    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_polars", _counting_polars)
    monkeypatch.setattr(FeaturePreprocessor, "_transform_single_optimized_df", _counting_optimized)
    monkeypatch.setattr(FeaturePreprocessor, "_apply_fractional_differencing_serial", _counting_serial)
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: 1)

    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: True)
    polars_result = FeaturePreprocessor(_l65_config(fracdiff=False)).transform(frame)
    assert calls["polars"] >= 1
    assert calls["optimized"] == 0

    calls.update({"polars": 0, "optimized": 0, "fracdiff": 0})
    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: False)
    optimized_result = FeaturePreprocessor(_l65_config(fracdiff=False)).transform(frame)
    assert calls["optimized"] >= 1
    assert calls["polars"] == 0
    _assert_common_numeric_equal(optimized_result, polars_result, atol=1e-5)

    calls.update({"polars": 0, "optimized": 0, "fracdiff": 0})
    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: True)
    _ = FeaturePreprocessor(_l65_config(fracdiff=True)).transform(frame)
    assert calls["fracdiff"] >= 1
    assert calls["polars"] == 0


def test_v7_4_float16_error_bound_contract_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """V7.4：FeatureStorage 真實寫讀與 manifest codec registry 均明示誤差邊界。"""
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "1")
    source = pd.DataFrame(
        {
            "alpha_rank_4": np.array([0.25, 0.5, 1.0, np.nan], dtype=np.float32),
            "beta_zscore": np.array([-1.25, 0.0, 1.25, np.nan], dtype=np.float32),
            "plain_feature": np.array([0.1, 1.0, 10.0, -25.5], dtype=np.float32),
        }
    )
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(storage.base_path))
    processed_dir = storage.write_processed("SYNTHETIC", "1h", "cfg_p1ff57_codec", {"selected": source})

    schema = pq.read_schema(str(processed_dir / "selected.parquet"))
    registry = json.loads(schema.metadata[L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8")])
    assert registry["alpha_rank_4"]["encoding_type"] == "rank_uint16"
    assert registry["beta_zscore"]["encoding_type"] == "zscore_int16"
    assert "plain_feature" not in registry

    manifest = json.loads((processed_dir.parent / FeatureStorage.L7_V2_MANIFEST_NAME).read_text(encoding="utf-8"))
    assert manifest["artifacts"]["processed"]["groups"]["selected"]["encoded_column_count"] == len(registry)

    loaded = reader.load_columns_v2(
        "SYNTHETIC",
        "1h",
        "cfg_p1ff57_codec",
        list(source.columns),
        artifact_kind="processed",
    )
    diff = np.abs(
        loaded["plain_feature"].to_numpy(dtype=np.float32)
        - source["plain_feature"].to_numpy(dtype=np.float32)
    )
    rel_err = diff / np.maximum(np.abs(source["plain_feature"].to_numpy(dtype=np.float32)), 1e-12)
    assert float(rel_err.max()) <= FeatureStorage.FLOAT16_MAX_REL_ERROR
    np.testing.assert_allclose(
        loaded["alpha_rank_4"].to_numpy(dtype=np.float32),
        source["alpha_rank_4"].to_numpy(dtype=np.float32),
        rtol=0.0,
        atol=1.0 / (2 * 4),
        equal_nan=True,
    )


@pytest.mark.requires_kline
def test_mutation_m7_1_rsi_input_swap_fails_semantics(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """M7.1：RSI close 改餵 open 時，V7.1 semantics 會失敗。"""
    data = _numeric_kline(requires_kline_data)
    original_prepare = TALibWrapper._prepare_inputs.__func__

    def _poisoned_prepare(cls, spec, frame, data_source, params):
        if spec.name == "RSI":
            return [frame["open"].to_numpy(dtype=float)], "open"
        return original_prepare(cls, spec, frame, data_source, params)

    monkeypatch.setattr(TALibWrapper, "_prepare_inputs", classmethod(_poisoned_prepare))
    spec = TALibWrapper.get_indicator_spec("RSI")
    actual, _ = TALibWrapper._prepare_inputs(spec, data, "close", dict(spec.default_params))
    expected = arrays_from_dataframe("RSI", data)
    with pytest.raises(AssertionError):
        np.testing.assert_array_equal(actual[0], expected[0])


def test_mutation_m7_2_polars_claim_but_pandas_fallback_fails_sentinel(
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data,
) -> None:
    """M7.2：聲稱 polars 但未命中 polars sentinel 時，路徑證據會失敗。"""
    pytest.importorskip("polars")
    import momentum.FeatureEngineering.polars_adapter as polars_adapter

    raw = _numeric_kline(requires_kline_data, rows=80)
    layer1 = pd.DataFrame({"close_trend_EMA_8": raw["close"].ewm(span=8, adjust=False).mean()}, index=raw.index)
    factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
    config = factory._resolve_config({"operators": {"enabled": True, "momentum": {"enabled": True, "lags": [1]}}})
    calls = {"polars": 0}

    def _fake_polars(self: DerivedOperatorEngine, *args: Any, **kwargs: Any) -> pd.DataFrame:
        return DerivedOperatorEngine.compute_all(self, *args, **kwargs)

    monkeypatch.setattr(DerivedOperatorEngine, "compute_all_polars", _fake_polars)
    monkeypatch.setattr(polars_adapter, "polars_enabled", lambda: True)
    _ = factory._layer2_derived_features(layer1, raw, config).data
    with pytest.raises(AssertionError):
        assert calls["polars"] >= 1
