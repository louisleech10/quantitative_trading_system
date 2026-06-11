"""Batch1 fail-open contract：LayerExecutionResult + derive_status 真值表。"""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import LayerExecutionResult, LayerStatus, derive_status
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.core.column_group import LayerSource
from momentum.factories import create_feature_factory, create_kline_storage_manager


ROOT = Path(__file__).resolve().parents[2]
TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"
BASELINE_PATH = ROOT / "tests/_golden/failopen/baseline.json"
BASELINE_SYMBOL = "BTCUSDT"
BASELINE_TIMEFRAME = "12h"


@lru_cache(maxsize=1)
def _freeze_baseline_module():
    spec = importlib.util.spec_from_file_location(
        "freeze_failopen_baseline",
        ROOT / "scripts/freeze_failopen_baseline.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _apply_baseline_env(monkeypatch: pytest.MonkeyPatch) -> None:
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        monkeypatch.setenv(name, value)


def _compute_l1_canonical_sha256(monkeypatch: pytest.MonkeyPatch) -> str:
    """以 baseline 固定 config/窗 跑 L1，用 freeze 腳本同規則 hash registry L1 群組。"""
    if os.environ.get("PYTHONHASHSEED") != "0":
        pytest.skip("L1 baseline hash oracle requires PYTHONHASHSEED=0")

    freeze = _freeze_baseline_module()
    _apply_baseline_env(monkeypatch)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp) / "registry"
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))

        factory = create_feature_factory(
            cache_dir=TEST_KLINE_CACHE_DIR,
            validate_continuity=False,
        )
        payload = freeze._fixed_config_payload([BASELINE_TIMEFRAME], BASELINE_TIMEFRAME)
        config = factory._resolve_config(payload)
        start_date, end_date = freeze._window_dates()
        config_hash = factory._compute_config_hash(
            config,
            BASELINE_SYMBOL,
            BASELINE_TIMEFRAME,
            start_date=start_date,
            end_date=end_date,
        )
        factory._cgsa_force_fresh = True
        factory._current_symbol = BASELINE_SYMBOL
        factory._current_timeframe = BASELINE_TIMEFRAME
        factory._cgsa_registry = factory._prepare_cgsa_registry(
            BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash
        )
        raw = factory._layer0_data_ingestion(
            BASELINE_SYMBOL,
            BASELINE_TIMEFRAME,
            config,
            start_date=start_date,
            end_date=end_date,
        )
        layer1 = factory._execute_layer1_6(
            "Layer 1", factory._layer1_atomic_indicators, raw, config
        ).data
        assert isinstance(layer1, pd.DataFrame)
        assert not layer1.empty
        assert factory._cgsa_registry is not None

        l1_record = freeze._hash_registry_table(
            factory._cgsa_registry,
            factory._cgsa_registry.list_by_layer(LayerSource.L1),
            raw.index,
        )
        return l1_record["canonical_sha256"]


@lru_cache(maxsize=1)
def _resolve_test_target() -> tuple[str, str]:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    for symbol, timeframe in (("BTCUSDT", "12h"), ("ETHUSDT", "1h")):
        try:
            df = storage.read_klines(symbol, timeframe, validate_continuity=False)
        except Exception:
            continue
        if df is not None and len(df) >= 100:
            return symbol, timeframe
    pytest.skip("missing market data for fail-open contract tests")


def _load_ohlcv() -> pd.DataFrame:
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    return storage.read_klines(symbol, timeframe, validate_continuity=False)


# SPEC §P-4 真值表：每列一組 canonical 輸入，驗證唯一映射。
_TRUTH_TABLE_CASES = [
    (
        "empty_disabled_layer_off",
        dict(layer_enabled=False, configured_engines=3, present_engines=0, required_engines=1),
        LayerStatus.empty_disabled,
    ),
    (
        "empty_disabled_configured_zero",
        dict(layer_enabled=True, configured_engines=0, present_engines=0, required_engines=0),
        LayerStatus.empty_disabled,
    ),
    (
        "layer_failed",
        dict(
            layer_enabled=True,
            configured_engines=2,
            present_engines=0,
            required_engines=1,
            layer_exception=True,
        ),
        LayerStatus.layer_failed,
    ),
    (
        "dependency_failed",
        dict(
            layer_enabled=True,
            configured_engines=2,
            present_engines=0,
            required_engines=0,
            dependency_error=True,
        ),
        LayerStatus.dependency_failed,
    ),
    (
        "all_engines_failed",
        dict(
            layer_enabled=True,
            configured_engines=2,
            present_engines=0,
            required_engines=2,
        ),
        LayerStatus.all_engines_failed,
    ),
    (
        "all_engines_failed_all_optional",
        dict(
            layer_enabled=True,
            configured_engines=3,
            present_engines=0,
            required_engines=0,
            failed_engines=("optional_a", "optional_b"),
        ),
        LayerStatus.all_engines_failed,
    ),
    (
        "empty_short_data",
        dict(
            layer_enabled=True,
            configured_engines=2,
            present_engines=0,
            required_engines=0,
            short_data=True,
        ),
        LayerStatus.empty_short_data,
    ),
    (
        "offloaded_to_registry",
        dict(
            layer_enabled=True,
            configured_engines=2,
            present_engines=0,
            required_engines=0,
            offloaded=True,
        ),
        LayerStatus.offloaded_to_registry,
    ),
    (
        "empty_not_applicable",
        dict(
            layer_enabled=True,
            configured_engines=3,
            present_engines=0,
            required_engines=0,
        ),
        LayerStatus.empty_not_applicable,
    ),
    (
        "engine_partial",
        dict(
            layer_enabled=True,
            configured_engines=3,
            present_engines=2,
            required_engines=1,
            failed_engines=("optional_a",),
        ),
        LayerStatus.engine_partial,
    ),
    (
        "ok",
        dict(
            layer_enabled=True,
            configured_engines=3,
            present_engines=3,
            required_engines=1,
        ),
        LayerStatus.ok,
    ),
]


@pytest.mark.parametrize("case_name,kwargs,expected", _TRUTH_TABLE_CASES)
def test_derive_status_truth_table_unique_mapping(
    case_name: str, kwargs: dict, expected: LayerStatus
) -> None:
    del case_name
    assert derive_status(**kwargs) == expected


def test_derive_status_all_nine_statuses_reachable() -> None:
    statuses = {expected for _, _, expected in _TRUTH_TABLE_CASES}
    assert statuses == set(LayerStatus)


def test_failed_engines_tuple_is_immutable() -> None:
    result = LayerExecutionResult(
        data=pd.DataFrame(),
        status=LayerStatus.ok,
        failed_engines=["trend"],
        reason=None,
        configured_engines=1,
        present_engines=1,
        required_engines=1,
        dependency_error=False,
    )
    assert isinstance(result.failed_engines, tuple)
    with pytest.raises(AttributeError):
        result.failed_engines = ("other",)  # type: ignore[misc]
    with pytest.raises(AttributeError):
        result.failed_engines.append("other")  # type: ignore[attr-defined]


def test_required_fail_returns_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """required engine 例外 → layer_failed LayerExecutionResult，健康路徑數值不變。"""
    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:256].copy()

    healthy_once = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    assert isinstance(healthy_once, pd.DataFrame)
    assert not healthy_once.empty

    healthy_repeat = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    assert isinstance(healthy_repeat, pd.DataFrame)
    assert list(healthy_repeat.columns) == list(healthy_once.columns)
    np.testing.assert_array_equal(
        healthy_repeat.to_numpy(),
        healthy_once.to_numpy(),
        err_msg="healthy L1 path must be deterministic across invocations",
    )

    baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    expected_l1_hash = baseline["single_tf"][BASELINE_SYMBOL][BASELINE_TIMEFRAME]["layers"]["L1"][
        "canonical_sha256"
    ]
    actual_l1_hash = _compute_l1_canonical_sha256(monkeypatch)
    assert actual_l1_hash == expected_l1_hash, (
        "L1 healthy output must match frozen baseline canonical_sha256 "
        f"(got {actual_l1_hash}, expected {expected_l1_hash})"
    )

    def _boom(self, ohlcv):  # noqa: ANN001
        del self, ohlcv
        raise RuntimeError("injected required trend failure")

    monkeypatch.setattr(TrendIndicatorEngine, "compute_all", _boom)

    failed = factory._layer1_atomic_indicators(data, config)
    assert isinstance(failed, LayerExecutionResult)
    assert failed.status == LayerStatus.layer_failed
    assert failed.failed_engines == ("trend",)
    assert failed.reason is not None
    assert "injected required trend failure" in failed.reason

    executed = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    )
    assert isinstance(executed, LayerExecutionResult)
    assert executed.status == LayerStatus.layer_failed
    assert executed.data.empty
    assert list(executed.data.index) == list(data.index)
    assert "Layer 1" in factory.layer_results
    assert factory.layer_results["Layer 1"].status == LayerStatus.layer_failed
    assert factory.layer_results["Layer 1"].failed_engines == ("trend",)


def test_layer2_exception_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """L2 未分類例外 → layer_failed + 保留 index，不中斷 pipeline。"""
    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    assert isinstance(layer1, pd.DataFrame)
    assert not layer1.empty

    def _boom(self, layer1_df, ohlcv, cfg):  # noqa: ANN001
        del self, layer1_df, ohlcv, cfg
        raise RuntimeError("injected L2 failure")

    import types

    monkeypatch.setattr(
        factory,
        "_layer2_derived_features",
        types.MethodType(_boom, factory),
    )

    layer2 = factory._execute_layer1_6(
        "Layer 2", factory._layer2_derived_features, layer1, data, config
    )
    assert isinstance(layer2, LayerExecutionResult)
    assert layer2.status == LayerStatus.layer_failed
    assert layer2.data.empty
    assert len(layer2.data.index) == len(data.index)
    assert "Layer 2" in factory.layer_results


def test_layer3_exception_fail_open(monkeypatch: pytest.MonkeyPatch) -> None:
    """L3 未分類例外 → layer_failed + 保留 index，不中斷 pipeline。"""
    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    layer2 = factory._execute_layer1_6(
        "Layer 2", factory._layer2_derived_features, layer1, data, config
    ).data
    assert isinstance(layer1, pd.DataFrame)
    assert isinstance(layer2, pd.DataFrame)

    def _boom(self, l1, l2, cfg):  # noqa: ANN001
        del self, l1, l2, cfg
        raise RuntimeError("injected L3 failure")

    import types

    monkeypatch.setattr(
        factory,
        "_layer3_rolling_aggregation",
        types.MethodType(_boom, factory),
    )

    layer3 = factory._execute_layer1_6(
        "Layer 3", factory._layer3_rolling_aggregation, layer1, layer2, config
    )
    assert isinstance(layer3, LayerExecutionResult)
    assert layer3.status == LayerStatus.layer_failed
    assert layer3.data.empty
    assert len(layer3.data.index) == len(data.index)
    assert "Layer 3" in factory.layer_results
