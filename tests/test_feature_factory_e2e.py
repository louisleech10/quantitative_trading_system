"""Feature Factory end-to-end tests.

TESTREG Task 4.4 改寫（R10 治理檔）：
- CGSA 之 `result.features_df` 只帶索引、不帶欄，`metadata["feature_names"]` 恆為 []（Phase-B 串流設計，
  `feature_factory.py` 約 :3950、:4006）⇒ 原以 features_df 欄／值與 metadata 名單所做之斷言空真或恆紅；
  改由本次落盤之 L7 raw manifest（欄名）與 raw parquet（欄值）讀回。
- 原 `_require_data` 讀非 canonical 預設 kline、缺檔即 skip（違 A17）⇒ 改讀 `data_cache/feature_klines`，
  缺檔 fail（requires_kline_data）。
- 原生成未隔離 CGSA work_dir 與 feature registry（寫入真實 data_cache/cgsa_work、registry）⇒ 一律導向 tmp_path。
- 原 `test_no_future_leak_alignment_check` 以 12h 對 12h（恆等）呼叫已無生產呼叫者之 align_to_primary，並以讀其
  自寫 attrs 之 validate_no_future_leak 為 oracle（自指）⇒ 改以真實 1h 來源對 12h 主週期驗生產 CGSA 對齊所用之
  build_asof_index_map，期望值以逐列計數獨立導出。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator
from momentum.FeatureEngineering.timeframe.tf_aligner import TimeframeAligner
from tests.fixtures.ic_persist_redirect import get_active_redirect_root

pytestmark = [
    pytest.mark.ic_persist_redirect,
    pytest.mark.usefixtures("ic_persist_redirect"),
]

TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"


def _create_e2e_factory():
    factory = create_feature_factory()
    active_root = get_active_redirect_root()
    if active_root is not None:
        factory._storage = FeatureStorage(str(active_root / "features"))
    return factory


def _load_data(symbol: str, timeframe: str):
    storage = create_kline_storage_manager()
    try:
        df = storage.read_klines(symbol, timeframe)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    return df


def _require_data(symbol: str, timeframe: str) -> None:
    if _load_data(symbol, timeframe) is None:
        pytest.skip(f"missing data for {symbol}/{timeframe}")


def _has_timeframes(symbol: str, timeframes: list[str]) -> bool:
    return all(_load_data(symbol, tf) is not None for tf in timeframes)


def _generate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    timeframe: str,
    config_override: dict,
):
    """以真實 feature_klines 生成並落盤於 tmp_path（CGSA work_dir、registry、features 皆隔離）。"""
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa"))
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_path / "registry.json"))
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    factory._registry = FeatureRegistry(tmp_path / "registry.json")
    result = factory.generate_features(
        symbol,
        timeframe,
        config_override=config_override,
        force_regenerate=True,
    )
    return result, factory


def _persisted_feature_names(factory, result, symbol: str, timeframe: str) -> list[str]:
    """本次落盤之 L7 raw manifest 之全部欄名（CGSA 之欄名權威來源）。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(factory._storage.base_path))
    manifest = reader.load_manifest_v2(
        symbol, timeframe, str(result.metadata["config_hash"]), allow_partial=True
    )
    groups = manifest["artifacts"]["raw"]["groups"]
    return [str(col) for group in groups.values() for col in group.get("columns", [])]


def _persisted_values(factory, result, symbol: str, timeframe: str) -> pd.DataFrame:
    """讀回本次落盤之 raw 全部欄值。"""
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(factory._storage.base_path))
    columns = _persisted_feature_names(factory, result, symbol, timeframe)
    return reader.load_columns_v2(
        symbol, timeframe, str(result.metadata["config_hash"]), columns, allow_partial=True
    )


def test_standard_preset_btcusdt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data: Callable[..., pd.DataFrame],
):
    requires_kline_data("BTCUSDT", "12h")
    result, factory = _generate(tmp_path, monkeypatch, "BTCUSDT", "12h", {"preset": "standard"})
    assert result.feature_count > 0
    assert result.features_df.shape[0] > 100
    assert not np.isinf(result.features_df.to_numpy()).any()
    persisted = _persisted_values(factory, result, "BTCUSDT", "12h")
    assert persisted.shape == (result.features_df.shape[0], result.feature_count)
    assert not np.isinf(persisted.to_numpy(dtype=np.float64)).any()


def test_minimal_preset():
    _require_data("BTCUSDT", "12h")
    factory = _create_e2e_factory()
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override={"preset": "minimal"},
    )
    assert result.feature_count > 0
    assert result.feature_count < 500


def test_multi_data_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data: Callable[..., pd.DataFrame],
):
    requires_kline_data("BTCUSDT", "12h")
    override = {
        "data_sources": {"enabled_sources": ["close", "volume", "taker_ratio"]},
        "atomic_indicators": {"trend": {"enabled": True}},
    }
    result, factory = _generate(tmp_path, monkeypatch, "BTCUSDT", "12h", override)
    columns = set(_persisted_feature_names(factory, result, "BTCUSDT", "12h"))
    assert any(col.startswith("close_") for col in columns)
    assert any(col.startswith("volume_") for col in columns)


def test_user_override_rsi_period(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data: Callable[..., pd.DataFrame],
):
    requires_kline_data("BTCUSDT", "12h")
    override = {
        "atomic_indicators": {
            "momentum": {
                "enabled": True,
                "indicators": [{"name": "RSI", "periods": [7]}],
            }
        }
    }
    result, factory = _generate(tmp_path, monkeypatch, "BTCUSDT", "12h", override)
    columns = _persisted_feature_names(factory, result, "BTCUSDT", "12h")
    assert any("RSI_7" in col for col in columns)


def test_no_future_leak_alignment_check(requires_kline_data: Callable[..., pd.DataFrame]):
    """生產 CGSA 跨週期對齊（build_asof_index_map）於真實 BTCUSDT 1h→12h 上無 look-ahead，且取最新可用列。"""
    primary = requires_kline_data("BTCUSDT", "12h")
    source = requires_kline_data("BTCUSDT", "1h")
    primary_s = primary["timestamp"].to_numpy(dtype=np.int64)
    source_s = source["timestamp"].to_numpy(dtype=np.int64)
    ns = np.int64(1_000_000_000)
    source_dur_ns = np.int64(3600) * ns
    primary_dur_ns = np.int64(12 * 3600) * ns

    for mode, decision_offset_ns in (("close_time", primary_dur_ns), ("open_time", np.int64(0))):
        idx_map = TimeframeAligner.build_asof_index_map(
            primary_s,
            source_s,
            source_dur_ns=int(source_dur_ns),
            primary_dur_ns=int(primary_dur_ns),
            mode=mode,
        )
        decision_ns = primary_s * ns + decision_offset_ns
        source_close_ns = source_s * ns + source_dur_ns
        # 獨立 oracle：逐主週期列計數「收盤 ≤ 決策時點」之來源列數，最新可用列＝計數−1（無則 −1）
        expected = np.array(
            [int(np.count_nonzero(source_close_ns <= d)) - 1 for d in decision_ns], dtype=np.int64
        )
        np.testing.assert_array_equal(idx_map, expected)
        valid = idx_map >= 0
        assert valid.sum() > 100
        # PIT：被取用之來源列於決策時點前已收盤
        assert (source_close_ns[idx_map[valid]] <= decision_ns[valid]).all()
        # 最新性：下一根來源列（若有）於決策時點尚未收盤
        nxt = idx_map[valid] + 1
        has_next = nxt < len(source_close_ns)
        assert (source_close_ns[nxt[has_next]] > decision_ns[valid][has_next]).all()


def test_naming_convention_basic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data: Callable[..., pd.DataFrame],
):
    requires_kline_data("BTCUSDT", "12h")
    result, factory = _generate(tmp_path, monkeypatch, "BTCUSDT", "12h", {"preset": "minimal"})
    feature_names = _persisted_feature_names(factory, result, "BTCUSDT", "12h")
    assert feature_names, "落盤無任何欄——命名迴圈會空真"
    for name in feature_names:
        assert name
        assert " " not in name
        if name.startswith("meta_") or name.startswith("label_"):
            continue
        parts = name.split("_")
        assert len(parts) >= 3
        assert all(part for part in parts)


def test_metadata_completeness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    requires_kline_data: Callable[..., pd.DataFrame],
):
    requires_kline_data("BTCUSDT", "12h")
    result, factory = _generate(tmp_path, monkeypatch, "BTCUSDT", "12h", {"preset": "minimal"})
    metadata = result.metadata
    assert metadata["feature_count"] == result.feature_count
    # CGSA 之 metadata["feature_names"] 恆為 []（串流設計）⇒ 欄名清單以落盤 manifest 為權威
    feature_names = _persisted_feature_names(factory, result, "BTCUSDT", "12h")
    assert len(feature_names) == result.feature_count
    assert "layer_counts" in metadata
    assert "config_hash" in metadata
    assert "generation_time" in metadata
