"""Batch 2b tests for Task 2.3~2.6."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd

from momentum.FeatureEngineering.core.column_group import LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import (
    MAX_L2_ESTIMATED_COLS,
    FeatureFactory,
)
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator


class _DummyOperators:
    def __init__(self, payload: dict) -> None:
        self.enabled = True
        self._payload = payload

    def model_dump(self, by_alias: bool = True) -> dict:
        return self._payload


class _DummyConfig:
    def __init__(self, operators_payload: dict, lag_apply_to: str = "all") -> None:
        self.operators = _DummyOperators(operators_payload)
        self.lag_features = SimpleNamespace(apply_to=lag_apply_to)


def _make_factory() -> FeatureFactory:
    """建立最小可用 FeatureFactory 測試實例。"""
    return FeatureFactory(config_manager=Mock(), adapter_registry=Mock())


def _operators_payload(cross_enabled: bool = False, ratio_enabled: bool = False) -> dict:
    return {
        "distance": {"enabled": False},
        "cross": {"enabled": cross_enabled},
        "ratio": {"enabled": ratio_enabled},
        "momentum": {"enabled": False, "lags": [3, 5, 8]},
        "binary_signal": {"enabled": False, "rules": []},
        "signed_strength": {"enabled": False},
        "worldquant": {
            "enabled": False,
            "windows": [5, 13, 21],
            "operators": ["ts_argmax", "ts_argmin", "ts_rank", "decay_linear"],
            "transforms": ["sign", "log1p", "abs", "clip"],
        },
    }


def test_task23_l1_per_indicator_groups_saved(tmp_path):
    """Task 2.3: L1 每個 indicator 應儲存成獨立 ColumnGroup。"""
    factory = _make_factory()
    factory._current_timeframe = "1h"
    factory._cgsa_registry = ColumnGroupRegistry(work_dir=tmp_path)

    frame = pd.DataFrame(
        {
            "close_trend_EMA_5": [1.0, 2.0, 3.0],
            "close_trend_EMA_21": [4.0, 5.0, 6.0],
            "close_momentum_RSI_14": [7.0, 8.0, 9.0],
            "volume_momentum_RSI_14": [10.0, 11.0, 12.0],
        }
    )

    factory._persist_layer1_indicator_groups(frame, category_hint="trend")

    groups = factory._cgsa_registry.list_by_layer(LayerSource.L1)
    group_ids = [group.group_id for group in groups]
    assert group_ids == ["1h_L1_momentum_RSI", "1h_L1_trend_EMA"]

    loaded_rsi = np.asarray(factory._cgsa_registry.load_data("1h_L1_momentum_RSI"))
    expected_rsi = frame[["close_momentum_RSI_14", "volume_momentum_RSI_14"]].to_numpy(dtype=np.float32)
    np.testing.assert_allclose(loaded_rsi, expected_rsi, equal_nan=True)


def test_task24_l2_per_category_emit_and_registry_save(tmp_path, monkeypatch):
    """Task 2.4: L2 在 CGSA 模式應按 category 計算並寫入 Registry。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    factory = _make_factory()
    factory._current_timeframe = "1h"
    factory._cgsa_registry = ColumnGroupRegistry(work_dir=tmp_path)

    layer1 = pd.DataFrame(
        {
            "close_trend_EMA_5": [10.0, 12.0, 14.0, 16.0],
            "close_trend_EMA_21": [11.0, 12.0, 13.0, 14.0],
        }
    )
    raw_data = pd.DataFrame({"close": [10.0, 12.0, 14.0, 16.0]})

    indicator_specs = {
        "close_trend_EMA_5": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [5],
        },
        "close_trend_EMA_21": {
            "source": "close",
            "category": "trend",
            "indicator": "EMA",
            "params": [21],
        },
    }
    monkeypatch.setattr(factory, "_build_indicator_specs", lambda _layer1, _config: indicator_specs)

    config = _DummyConfig(_operators_payload(cross_enabled=True))
    result = factory._layer2_derived_features(layer1, raw_data, config).data

    assert list(result.columns) == ["close_trend_EMA_5_21_Cross"]

    saved = np.asarray(factory._cgsa_registry.load_data("1h_L2_Cross"))
    expected = result.to_numpy(dtype=np.float32)
    np.testing.assert_allclose(saved, expected, equal_nan=True)


def test_task24_l2_estimate_cols_respects_breaker_threshold():
    """Task 2.4: 斷路器估算在 Cross+Ratio 開啟時應可超過閾值。"""
    estimated = FeatureFactory._estimate_l2_output_cols(
        l1_col_count=500,
        operators_config=_operators_payload(cross_enabled=True, ratio_enabled=True),
    )

    assert estimated > MAX_L2_ESTIMATED_COLS


def test_task25_feature_factory_combine_layers_cgsa_noop(monkeypatch):
    """Task 2.5: FeatureFactory._combine_layers 在 CGSA 模式下為 no-op。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    layer = pd.DataFrame({"f1": [1.0, 2.0]})
    combined = FeatureFactory._combine_layers([layer], context="layer7_final")

    assert combined.empty


def test_task25_layer4_forces_layer1_and_raw_in_cgsa(monkeypatch):
    """Task 2.5: CGSA 模式下 L4 應強制使用 layer1_and_raw 快速路徑。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    factory = _make_factory()
    captured: dict[str, int] = {}

    def _fake_combine(layers, context="unknown"):
        captured["layer_count"] = len(layers)
        return pd.concat(layers, axis=1)

    class _DummyLagProcessor:
        def __init__(self, _config) -> None:
            pass

        def compute_all(self, features_df: pd.DataFrame) -> pd.DataFrame:
            return pd.DataFrame(index=features_df.index)

    monkeypatch.setattr(factory, "_combine_layers", _fake_combine)
    monkeypatch.setattr(
        "momentum.FeatureEngineering.feature_factory.LagProcessor",
        _DummyLagProcessor,
    )

    config = _DummyConfig(_operators_payload(), lag_apply_to="all")
    raw = pd.DataFrame({"open": [1.0, 2.0]})
    layer1 = pd.DataFrame({"l1": [1.0, 2.0]})
    layer2 = pd.DataFrame({"l2": [3.0, 4.0]})
    layer3 = pd.DataFrame({"l3": [5.0, 6.0]})

    _ = factory._layer4_lag_features(layer1, layer2, layer3, raw, config)

    assert captured["layer_count"] == 2


def test_task25_multitf_combine_layers_cgsa_noop(monkeypatch):
    """Task 2.5: MultiTFGenerator._combine_layers 在 CGSA 模式下為 no-op。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    layer = pd.DataFrame({"f1": [1.0, 2.0]})
    combined = MultiTFGenerator._combine_layers([layer])

    assert combined.empty


def test_task26_multitf_tagging_skips_when_registry_present(monkeypatch):
    """Task 2.6: CGSA + registry 存在時，Multi-TF tagging 應跳過 rename。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    features_df = pd.DataFrame({"close_trend_EMA_5": [1.0, 2.0]})
    tagged = MultiTFGenerator._apply_timeframe_tag(features_df, "1h", registry=object())

    assert tagged.columns.tolist() == ["close_trend_EMA_5"]


def test_task26_multitf_tagging_fallback_when_registry_absent(monkeypatch):
    """Task 2.6: 非 CGSA 或無 registry 時，Multi-TF tagging 應維持舊 rename 路徑。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    features_df = pd.DataFrame({"close_trend_EMA_5": [1.0, 2.0]})
    tagged = MultiTFGenerator._apply_timeframe_tag(features_df, "1h", registry=None)

    assert tagged.columns.tolist() == ["close_1h_trend_EMA_5"]
