"""Batch2 fail-open layer catching + caller .data 遷移測試。"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
import types

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import LayerExecutionResult, LayerStatus
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.operators.derived_operators import DerivedOperatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
from momentum.factories import create_feature_factory, create_kline_storage_manager


ROOT = Path(__file__).resolve().parents[2]
TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"
BASELINE_PATH = ROOT / "tests/_golden/failopen/baseline.json"
BASELINE_SYMBOL = "BTCUSDT"
BASELINE_TIMEFRAME = "12h"
GATE_A_WORKER_ENV = "_FAILOPEN_GATE_A_WORKER"

pytestmark = pytest.mark.requires_kline


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
    pytest.fail("missing market data for fail-open layer tests")


def _load_ohlcv() -> pd.DataFrame:
    symbol, timeframe = _resolve_test_target()
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    return storage.read_klines(symbol, timeframe, validate_continuity=False)


def _make_factory(monkeypatch: pytest.MonkeyPatch):
    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    return create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )


def _enable_microstructure(config):
    """啟用 optional microstructure engine（預設 config 為關）。"""
    atomic = config.atomic_indicators.model_copy(
        update={
            "microstructure": config.atomic_indicators.microstructure.model_copy(
                update={"enabled": True}
            )
        }
    )
    return config.model_copy(update={"atomic_indicators": atomic})


def test_optional_engine_partial_keeps_other_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    """optional engine 例外 → engine_partial，其他 engine 欄仍在。"""
    factory = _make_factory(monkeypatch)
    config = _enable_microstructure(ConfigManager().get_merged_config())
    data = _load_ohlcv().iloc[:256].copy()

    def _boom(self, ohlcv):  # noqa: ANN001
        del self, ohlcv
        raise RuntimeError("injected optional microstructure failure")

    monkeypatch.setattr(MicrostructureIndicatorEngine, "compute_all", _boom)

    result = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    )
    assert result.status == LayerStatus.engine_partial
    assert "microstructure" in result.failed_engines
    assert not result.data.empty
    assert result.data.shape[1] > 0
    assert not any(col.startswith("microstructure_") for col in result.data.columns)


def test_required_engine_layer_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _make_factory(monkeypatch)
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:256].copy()

    def _boom(self, ohlcv):  # noqa: ANN001
        del self, ohlcv
        raise RuntimeError("injected required trend failure")

    monkeypatch.setattr(TrendIndicatorEngine, "compute_all", _boom)
    result = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    )
    assert result.status == LayerStatus.layer_failed
    assert result.failed_engines == ("trend",)
    assert result.data.empty
    assert list(result.data.index) == list(data.index)


def test_all_engines_failed_l2_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _make_factory(monkeypatch)
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", tmp)
        factory._cgsa_registry = factory._prepare_cgsa_registry("BTCUSDT", "1h", "l2fail")
        layer1 = factory._execute_layer1_6(
            "Layer 1", factory._layer1_atomic_indicators, data, config
        ).data
        assert not layer1.empty

        def _always_fail(self, layer1_df, ohlcv, specs, category):  # noqa: ANN001
            del self, layer1_df, ohlcv, specs, category
            raise RuntimeError("injected L2 category failure")

        monkeypatch.setattr(DerivedOperatorEngine, "compute_category", _always_fail)
        result = factory._execute_layer1_6(
            "Layer 2", factory._layer2_derived_features, layer1, data, config
        )

    assert result.status == LayerStatus.all_engines_failed
    assert len(result.failed_engines) == len(DerivedOperatorEngine.OPERATOR_CATEGORIES)
    assert result.data.empty
    assert len(result.data.index) == len(data.index)


def test_l2_parallel_category_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    """L2 parallel 路徑：單 category 失敗 → engine_partial。"""
    factory = _make_factory(monkeypatch)
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", tmp)
        factory._cgsa_registry = factory._prepare_cgsa_registry("BTCUSDT", "1h", "testhash")

        original = DerivedOperatorEngine.compute_category
        fail_categories = {"Cross"}

        def _selective_fail(self, layer1_df, ohlcv, specs, category):  # noqa: ANN001
            if category in fail_categories:
                raise RuntimeError(f"injected {category} failure")
            return original(self, layer1_df, ohlcv, specs, category)

        monkeypatch.setattr(
            "momentum.FeatureEngineering.utils.hardware_utils.get_l2_category_workers",
            lambda: 4,
        )
        monkeypatch.setattr(DerivedOperatorEngine, "compute_category", _selective_fail)
        result = factory._execute_layer1_6(
            "Layer 2", factory._layer2_derived_features, layer1, data, config
        )

    assert result.status == LayerStatus.engine_partial
    assert "Cross" in result.failed_engines
    assert not result.data.empty


def test_layer2_whole_layer_exception_layer_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    factory = _make_factory(monkeypatch)
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data

    def _boom(self, l1, ohlcv, cfg):  # noqa: ANN001
        del self, l1, ohlcv, cfg
        raise RuntimeError("injected L2 failure")

    monkeypatch.setattr(
        factory,
        "_layer2_derived_features",
        types.MethodType(_boom, factory),
    )
    result = factory._execute_layer1_6(
        "Layer 2", factory._layer2_derived_features, layer1, data, config
    )
    assert result.status == LayerStatus.layer_failed
    assert "Layer 2" in factory.layer_results
    assert len(result.data.index) == len(data.index)


def _assert_layer_golden_matches_baseline() -> None:
    """Gate-A：健康 run per-layer canonical hash == 凍結 baseline。"""
    freeze = _freeze_baseline_module()
    for name, value in freeze.FIXED_ENV.items():
        os.environ[name] = value

    with tempfile.TemporaryDirectory() as tmp:
        record = freeze._single_tf_record(BASELINE_SYMBOL, BASELINE_TIMEFRAME, Path(tmp))
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        expected_layers = baseline["single_tf"][BASELINE_SYMBOL][BASELINE_TIMEFRAME]["layers"]
        for layer_key in ("L1", "L2", "L3", "L4", "L5", "L6"):
            assert (
                record["layers"][layer_key]["canonical_sha256"]
                == expected_layers[layer_key]["canonical_sha256"]
            ), f"{layer_key} canonical hash drift"


def test_layer_golden_matches_baseline() -> None:
    """CI 預設路徑必跑 Gate-A：非 hash-seed=0 時 subprocess 帶 PYTHONHASHSEED=0 重入。"""
    if os.environ.get(GATE_A_WORKER_ENV) == "1":
        assert os.environ.get("PYTHONHASHSEED") == "0"
        _assert_layer_golden_matches_baseline()
        return

    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env[GATE_A_WORKER_ENV] = "1"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            f"{__file__}::test_layer_golden_matches_baseline",
            "-q",
            "--tb=short",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=1800,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_zero_copy_spill_preserves_memmap_sharing(monkeypatch: pytest.MonkeyPatch) -> None:
    """_execute_layer1_6 回傳 .data；spill 後底層 memmap 仍 zero-copy。"""
    factory = _make_factory(monkeypatch)
    rows, cols = 32_768, 2048
    rng = np.random.default_rng(42)
    original_df = pd.DataFrame(
        rng.standard_normal((rows, cols), dtype=np.float32),
        columns=[f"f{i}" for i in range(cols)],
    )
    wide_result = factory._build_layer_result(
        data=original_df,
        configured_engines=1,
        present_engines=1,
    )
    layer1 = pd.DataFrame({"close": np.ones(rows, dtype=np.float32)})
    config = ConfigManager().get_merged_config()

    result = factory._execute_layer1_6(
        "Layer 2",
        lambda *_args, **_kwargs: wide_result,
        layer1,
        layer1,
        config,
    )
    assert result.data is original_df

    memmap_holder: dict[str, np.memmap] = {}
    from momentum.FeatureEngineering import memmap_utils

    original_create = memmap_utils.create_temp_memmap

    def _capture_memmap(shape, dtype=np.float32, prefix: str = "ff_"):
        memmap_array = original_create(shape, dtype=dtype, prefix=prefix)
        memmap_holder["base"] = memmap_array
        return memmap_array

    monkeypatch.setattr(memmap_utils, "create_temp_memmap", _capture_memmap)

    spilled = factory._spill_to_memmap(result.data, "layer2_test")
    assert spilled is not result.data
    memmap_base = memmap_holder["base"]
    spilled_values = spilled.to_numpy(copy=False)
    assert np.shares_memory(spilled_values, memmap_base)


def test_l3_streaming_offload_status(monkeypatch: pytest.MonkeyPatch) -> None:
    """L3 CGSA streaming 成功但輸出已 offload → offloaded_to_registry。"""
    factory = _make_factory(monkeypatch)
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_L3_PERSIST_MODE", "streaming")
    config = ConfigManager().get_merged_config()
    data = _load_ohlcv().iloc[:128].copy()

    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv("FFACT_CGSA_WORK_DIR", tmp)
        factory._cgsa_registry = factory._prepare_cgsa_registry("BTCUSDT", "1h", "l3offload")
        layer1 = factory._execute_layer1_6(
            "Layer 1", factory._layer1_atomic_indicators, data, config
        ).data
        layer2 = pd.DataFrame(index=layer1.index)
        result = factory._execute_layer1_6(
            "Layer 3",
            factory._layer3_rolling_aggregation,
            layer1,
            layer2,
            config,
        )

    assert result.status == LayerStatus.offloaded_to_registry


def test_l5_reference_fetch_dependency_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    """L5 reference fetch 例外 → dependency_failed。"""
    factory = _make_factory(monkeypatch)
    base_config = ConfigManager().get_merged_config()
    cross_sectional = base_config.cross_sectional.model_copy(
        update={"enabled": True, "reference_symbol": "BTCUSDT"}
    )
    config = base_config.model_copy(update={"cross_sectional": cross_sectional})
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    layer2 = pd.DataFrame(index=layer1.index)

    _, timeframe = _resolve_test_target()
    factory._current_symbol = "ETHUSDT"
    factory._current_timeframe = timeframe
    factory._current_raw_data = data
    factory._reference_data_cache = {}

    def _fetch_fail(self, symbol, timeframe, cfg):  # noqa: ANN001
        del self, symbol, timeframe, cfg
        raise RuntimeError("injected reference fetch failure")

    monkeypatch.setattr(factory, "_layer0_data_ingestion", types.MethodType(_fetch_fail, factory))

    result = factory._execute_layer1_6(
        "Layer 5",
        factory._layer5_cross_sectional,
        layer1,
        layer2,
        config,
    )
    assert result.status == LayerStatus.dependency_failed


def test_l6_all_subengines_disabled_empty_not_applicable(monkeypatch: pytest.MonkeyPatch) -> None:
    """L6 layer 啟用但 sub-engine 全關 → empty_not_applicable（非 empty_disabled）。"""
    factory = _make_factory(monkeypatch)
    config = ConfigManager().get_merged_config()
    meta = config.meta_features.model_copy(
        update={
            "enabled": True,
            "trend_consensus": False,
            "momentum_divergence": False,
            "volume_price_divergence": False,
            "volatility_regime": False,
            "interaction": False,
            "time_features": False,
        }
    )
    config = config.model_copy(update={"meta_features": meta})
    data = _load_ohlcv().iloc[:128].copy()
    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, data, config
    ).data
    layer2 = pd.DataFrame(index=layer1.index)

    result = factory._execute_layer1_6(
        "Layer 6",
        factory._layer6_meta_features,
        layer1,
        layer2,
        data,
        config,
    )
    assert result.status == LayerStatus.empty_not_applicable
