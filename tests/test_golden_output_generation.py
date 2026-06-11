from types import SimpleNamespace
import logging
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from momentum.FeatureEngineering import feature_factory as feature_factory_module
from momentum.FeatureEngineering import memmap_utils


class _DummyDerivedOperatorEngine:
    OPERATOR_CATEGORIES = ("dummy",)

    def __init__(self, _config):
        self._config = _config

    def compute_all(self, layer1, _data, _indicator_specs):
        return pd.DataFrame({"derived": layer1.iloc[:, 0].astype(float)}, index=layer1.index)


class _DummyProcess:
    def memory_info(self):
        return SimpleNamespace(rss=512 * 1024 * 1024)


class _DummyPsutil:
    def Process(self):
        return _DummyProcess()


class _FakeFeatureFactory:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_features(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("No more fake responses configured")
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _load_generate_golden_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "generate_golden_output.py"
    spec = importlib.util.spec_from_file_location("generate_golden_output", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load generate_golden_output.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _make_result(features_df: pd.DataFrame):
    return SimpleNamespace(
        features_df=features_df,
        feature_count=int(features_df.shape[1]),
        layer_counts={"layer1": int(features_df.shape[1])},
    )


def test_l2_timing_log_emitted(monkeypatch, caplog):
    """測試 T0.1：L2 應輸出 Starting 與 Completed 計時日誌。"""
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    factory = feature_factory_module.FeatureFactory.__new__(feature_factory_module.FeatureFactory)
    factory._cgsa_registry = None
    monkeypatch.setattr(factory, "_filter_operators_config", lambda _operators: {})
    monkeypatch.setattr(factory, "_build_indicator_specs", lambda _layer1, _config: {})
    monkeypatch.setattr(feature_factory_module, "DerivedOperatorEngine", _DummyDerivedOperatorEngine)

    layer1 = pd.DataFrame({"f1": [1.0, 2.0, 3.0]})
    raw_data = pd.DataFrame({"close": [10.0, 11.0, 12.0]})
    config = SimpleNamespace(operators=SimpleNamespace(enabled=True))

    caplog.set_level(logging.INFO, logger=feature_factory_module.logger.name)
    result = factory._layer2_derived_features(layer1, raw_data, config).data

    assert "derived" in result.columns
    assert any("[L2] Starting derived features:" in rec.message for rec in caplog.records)
    assert any("[L2] Completed:" in rec.message for rec in caplog.records)

    # 邊界情況：L1 為空時不應崩潰。
    empty_layer1 = pd.DataFrame(index=layer1.index)
    empty_result = factory._layer2_derived_features(empty_layer1, raw_data, config).data
    assert empty_result.empty


def test_heartbeat_emitted_during_concat(monkeypatch, caplog):
    """測試 T0.2：concat 超過 30 秒時應輸出 heartbeat 與 RSS。"""
    perf_counter_ticks = iter([0.0, 31.0, 62.0, 93.0, 124.0, 155.0])

    monkeypatch.setattr(memmap_utils.time, "perf_counter", lambda: next(perf_counter_ticks))
    monkeypatch.setattr(memmap_utils, "_resolve_copy_block_rows", lambda: 1)
    monkeypatch.setattr(memmap_utils, "psutil", _DummyPsutil())

    caplog.set_level(logging.INFO, logger=memmap_utils.logger.name)
    left = pd.DataFrame({"a": [1.0, 2.0]})
    right = pd.DataFrame({"b": [3.0, 4.0]})

    result = memmap_utils.concat_with_memmap([left, right], threshold_bytes=1)

    assert list(result.columns) == ["a", "b"]
    heartbeat_messages = [
        rec.message for rec in caplog.records if "[concat_memmap] DF" in rec.message and "rows copied" in rec.message
    ]
    assert heartbeat_messages
    assert any("RSS=" in message for message in heartbeat_messages)


def test_golden_output_generated(monkeypatch, tmp_path):
    """測試 T0.3：應產出 golden.parquet 並符合欄位與無 inf 要求。"""
    module = _load_generate_golden_module()

    features_df = pd.DataFrame(
        {
            "close_1h_trend_EMA_5": [1.0, 2.0, 3.0],
            "close_1h_momentum_RSI_14": [50.0, np.nan, 58.0],
        }
    )
    fake_factory = _FakeFeatureFactory(
        responses=[
            MemoryError("simulated full-config oom"),
            _make_result(features_df),
        ]
    )

    monkeypatch.setattr(
        module,
        "create_feature_factory",
        lambda validate_continuity=True: fake_factory,
    )
    monkeypatch.setenv("GOLDEN_CONFIG_OVERRIDE", "")

    artifacts = module.generate_golden_output(
        symbol="ETHUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        output_dir=tmp_path,
        force_regenerate=True,
        attempt_tier1_full=True,
    )

    assert artifacts.parquet_path.exists()
    assert artifacts.feature_count > 0
    assert artifacts.baseline_tier == "tier2_reduced"

    saved_df = pd.read_parquet(artifacts.parquet_path)
    assert saved_df.shape[1] > 0
    assert not np.isinf(saved_df.to_numpy(dtype=np.float64, copy=False)).any()


def test_golden_columns_json_matches(monkeypatch, tmp_path):
    """測試 T0.4：columns.json 應與 golden.parquet 欄位完全一致。"""
    module = _load_generate_golden_module()

    features_df = pd.DataFrame(
        {
            "close_1h_trend_EMA_5": [1.0, 2.0],
            "close_1h_trend_EMA_8": [1.5, 2.5],
            "close_1h_momentum_RSI_14": [42.0, 47.0],
        }
    )
    fake_factory = _FakeFeatureFactory(responses=[_make_result(features_df)])

    monkeypatch.setattr(
        module,
        "create_feature_factory",
        lambda validate_continuity=True: fake_factory,
    )
    monkeypatch.setenv("GOLDEN_CONFIG_OVERRIDE", "")

    artifacts = module.generate_golden_output(
        symbol="ETHUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        output_dir=tmp_path,
        force_regenerate=True,
    )

    saved_df = pd.read_parquet(artifacts.parquet_path)
    columns_payload = json.loads(artifacts.columns_json_path.read_text(encoding="utf-8"))

    assert columns_payload == list(saved_df.columns)


def test_golden_default_skips_tier1_full(monkeypatch, tmp_path):
    """預設應跳過 Tier1 全量路徑，以降低 OOM 風險。"""
    module = _load_generate_golden_module()

    features_df = pd.DataFrame(
        {
            "close_1h_trend_EMA_5": [1.0, 2.0, 3.0],
            "close_1h_momentum_RSI_14": [44.0, 47.0, 51.0],
        }
    )
    fake_factory = _FakeFeatureFactory(responses=[_make_result(features_df)])
    factory_kwargs = {}

    def _fake_factory_builder(validate_continuity=True):
        factory_kwargs["validate_continuity"] = validate_continuity
        return fake_factory

    monkeypatch.setattr(module, "create_feature_factory", _fake_factory_builder)
    monkeypatch.setenv("GOLDEN_CONFIG_OVERRIDE", "")

    artifacts = module.generate_golden_output(
        symbol="ETHUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        output_dir=tmp_path,
        force_regenerate=True,
    )

    assert artifacts.baseline_tier == "tier2_reduced"
    assert len(fake_factory.calls) == 1
    assert factory_kwargs["validate_continuity"] is False
