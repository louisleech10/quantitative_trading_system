"""P1-FF-5 — cross-symbol value isolation tests."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache
from momentum.FeatureEngineering.run_paths import cgsa_work_dir, features_run_dir
from tests.feature_engineering.ff_artifact_compare_helpers import (
    BASELINE_SYMBOL,
    BASELINE_TIMEFRAME,
    OTHER_SYMBOL,
    assert_dstar_symbol_isolated,
    assert_dstar_payloads_equal,
    assert_full_chain_runtime,
    assert_manifest_semantics_equal,
    assert_path_excludes_symbol,
    assert_sampled_values_equal,
    assert_slow_full_chain_config,
    canonical_frame_digest,
    cross_sectional_config_payload,
    dstar_context,
    feature_manifest_path,
    fast_config_payload,
    kline_full_window_dates,
    kline_window_dates,
    make_factory,
    representative_columns,
    run_symbol_frame,
    run_symbol_result,
    runtime_output_manifest,
    slow_full_chain_config_payload,
)


def test_v5_4_run_and_cgsa_paths_are_symbol_scoped(tmp_path: Path) -> None:
    """V5.4：feature run dir 與 CGSA work dir 均含 symbol leaf。"""
    config_hash = "cfg_p1ff57"
    a_run = features_run_dir(tmp_path, BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash)
    b_run = features_run_dir(tmp_path, OTHER_SYMBOL, BASELINE_TIMEFRAME, config_hash)
    a_cgsa = cgsa_work_dir(tmp_path, BASELINE_SYMBOL, BASELINE_TIMEFRAME, config_hash)
    b_cgsa = cgsa_work_dir(tmp_path, OTHER_SYMBOL, BASELINE_TIMEFRAME, config_hash)

    assert a_run != b_run
    assert a_cgsa != b_cgsa
    assert BASELINE_SYMBOL in str(a_run)
    assert OTHER_SYMBOL not in str(a_run)
    assert BASELINE_SYMBOL in str(a_cgsa)
    assert OTHER_SYMBOL not in str(a_cgsa)


def test_v5_2_dstar_path_payload_and_alias_are_symbol_isolated(tmp_path: Path) -> None:
    """V5.2/V5.2b：d-star path 與 payload 語義 map 不能跨 symbol 命中。"""
    assert_dstar_symbol_isolated(tmp_path / "dstar")


def test_v5_2_shared_dstar_cache_is_reset_after_chunked_transform(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """污染面：L6.5 shared d* cache 狀態不得跨 context 殘留。"""
    rows = 32
    frame = pd.DataFrame(
        {
            "L1_close_trend_EMA_8": np.linspace(1.0, 4.0, rows),
            "L1_close_trend_SMA_13": np.linspace(2.0, 5.0, rows) ** 1.05,
        }
    )
    config = {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {"enabled": False},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
        "adf_differencing": {"enabled": False},
        "fractional_differencing": {"enabled": True, "cache_d_star": True, "max_lag": 2},
    }
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: tmp_path / "dstar"))
    monkeypatch.setattr(FeaturePreprocessor, "_resolve_slowpath_n_jobs", lambda self: 1)
    preprocessor = FeaturePreprocessor(config)
    preprocessor._preprocessing_context = dstar_context(BASELINE_SYMBOL)
    preprocessor._d_star_cache_shared = True
    preprocessor._apply_fractional_differencing(frame)

    assert preprocessor._d_star_cache_shared is True
    assert preprocessor._d_star_cache is not None
    preprocessor._d_star_cache.flush_atomic()
    assert BASELINE_SYMBOL in preprocessor._d_star_cache.path.name
    assert OTHER_SYMBOL not in preprocessor._d_star_cache.path.name


@pytest.mark.requires_kline
def test_v5_1_fast_order_permutation_keeps_hash_and_sampled_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.1/V5.3/V5.8：三序 [A]/[A,B]/[B,A] 的 A 值與 manifest 不變。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = fast_config_payload()
    solo_factory = make_factory(tmp_path / "solo")
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    a_then_b_factory = make_factory(tmp_path / "a_then_b")
    run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    run_symbol_frame(
        a_then_b_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    a_after_b_result = run_symbol_result(
        a_then_b_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    b_then_a_factory = make_factory(tmp_path / "b_then_a")
    run_symbol_frame(
        b_then_a_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    b_then_a_result = run_symbol_result(
        b_then_a_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )

    only_a = solo_result.features_df
    a_then_b = a_after_b_result.features_df
    b_then_a = b_then_a_result.features_df
    sampled = representative_columns(only_a, limit=20)
    assert sampled, "fast isolation test needs at least one numeric feature column"
    assert canonical_frame_digest(only_a) == canonical_frame_digest(a_then_b)
    assert canonical_frame_digest(only_a) == canonical_frame_digest(b_then_a)
    assert_sampled_values_equal(only_a, a_then_b, columns=sampled)
    assert_sampled_values_equal(only_a, b_then_a, columns=sampled)
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(a_after_b_result),
    )
    assert_manifest_semantics_equal(
        runtime_output_manifest(solo_result),
        runtime_output_manifest(b_then_a_result),
    )


@pytest.mark.requires_kline
def test_v5_5_l5_reference_cache_uses_reference_symbol_timeframe_key(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.5 medium：L5 reference cache key 保留 reference symbol + timeframe。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    factory = make_factory(tmp_path)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    first = run_symbol_frame(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    run_symbol_frame(
        factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )
    second = run_symbol_frame(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    expected_key = (OTHER_SYMBOL, BASELINE_TIMEFRAME)
    assert expected_key in factory._reference_data_cache
    assert all(len(key) == 2 for key in factory._reference_data_cache)
    sampled = representative_columns(first, limit=20)
    assert_sampled_values_equal(first, second, columns=sampled)


def test_v5_reference_cache_source_uses_tuple_key_and_effective_ref_symbol() -> None:
    """污染面靜態 guard：run_multi_symbol IPC 與 L5 cache lookup 使用一致 key。"""
    source = inspect.getsource(FeatureFactory.run_multi_symbol)
    lookup_source = inspect.getsource(FeatureFactory._load_reference_if_available)

    assert "effective_ref_symbol = config.cross_sectional.reference_symbol or ref_symbol" in source
    assert "write_reference_data_ipc(ref_data, work_dir, effective_ref_symbol)" in source
    assert "self._reference_data_cache.get((ref_symbol, tf))" in lookup_source


def test_mutation_m5_1_shared_dstar_path_fails_isolation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """M5.1：去掉 symbol 的 d-star path 會被 V5.2 偵測。"""
    monkeypatch.setattr(
        DStarCache,
        "_build_path",
        staticmethod(lambda cache_dir, _context, _frac_hash: cache_dir / "d_star_shared.json"),
    )

    with pytest.raises(AssertionError):
        assert_dstar_symbol_isolated(tmp_path / "dstar")


def test_mutation_m5_2_reference_cache_static_key_drop_is_detected() -> None:
    """M5.2 靜態輔助：reference cache 若退化成 timeframe-only key，guard 會失敗。"""
    source = inspect.getsource(FeatureFactory._load_reference_if_available)
    with pytest.raises(AssertionError):
        assert "self._reference_data_cache.get(tf)" in source


@pytest.mark.requires_kline
def test_mutation_m5_2_reference_cache_poisoning_fails_runtime_values(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """M5.2：A 的 L5 reference cache 若被 runtime 毒化，V5.5 值斷言會紅。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=14)
    config = cross_sectional_config_payload(reference_symbol=OTHER_SYMBOL)

    clean_factory = make_factory(tmp_path / "clean")
    clean = run_symbol_frame(
        clean_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    poisoned_factory = make_factory(tmp_path / "poisoned")
    original_ingestion = poisoned_factory._layer0_data_ingestion

    def _poisoned_reference_ingestion(symbol: str, timeframe: str, cfg, *args, **kwargs):
        if symbol == OTHER_SYMBOL and timeframe == BASELINE_TIMEFRAME:
            return original_ingestion(BASELINE_SYMBOL, timeframe, cfg, *args, **kwargs)
        return original_ingestion(symbol, timeframe, cfg, *args, **kwargs)

    monkeypatch.setattr(poisoned_factory, "_layer0_data_ingestion", _poisoned_reference_ingestion)
    poisoned = run_symbol_frame(
        poisoned_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
    )

    relative_price_columns = [column for column in clean.columns if "relative_price" in str(column)]
    assert relative_price_columns
    with pytest.raises(AssertionError):
        assert_sampled_values_equal(clean, poisoned, columns=relative_price_columns)


def test_mutation_m5_3_dstar_payload_wrong_symbol_fails_alias_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """M5.3：d-star value_alias source_column 注入外部 symbol 會被 V5.2b 偵測。"""
    original_set = DStarCache.set

    def _poisoned_set(self: DStarCache, column: str, d_star: float, col_values=None) -> None:
        original_set(self, f"{OTHER_SYMBOL}_{column}", d_star, col_values=col_values)

    monkeypatch.setattr(DStarCache, "set", _poisoned_set)
    with pytest.raises(AssertionError):
        assert_dstar_symbol_isolated(tmp_path / "dstar")


@pytest.mark.requires_kline
def test_v5_4_runtime_cgsa_paths_are_symbol_scoped(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """V5.4：真實 generate_features 的 CGSA runtime path/manifest 隔離 symbol。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa"))
    kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=120)
    start, end = kline_window_dates(kline, days=7)
    config = fast_config_payload()
    factory = make_factory(tmp_path / "features")

    run_symbol_frame(
        factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    result = run_symbol_result(
        factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    manifest_path = Path(str(result.metadata["manifest_path"]))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    registry_manifest = Path(str(manifest["generation_metadata"]["source_registry_manifest"]))

    assert manifest_path == feature_manifest_path(factory, BASELINE_SYMBOL, str(result.metadata["config_hash"]))
    assert manifest_path.is_file()
    assert registry_manifest.is_file()
    assert_path_excludes_symbol(manifest_path, OTHER_SYMBOL)
    assert_path_excludes_symbol(registry_manifest, OTHER_SYMBOL)
    assert manifest["symbol"] == BASELINE_SYMBOL
    assert manifest["tf"] == BASELINE_TIMEFRAME
    assert manifest["artifacts"]["raw"]["metadata"]["source_registry_manifest"] == str(registry_manifest)


@pytest.mark.slow
@pytest.mark.requires_kline
def test_v5_slow_solo_a_equals_batch_b_then_a_artifacts(
    requires_kline_data,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Slow tier：solo(A) vs same-factory batch-like B→A 的全鏈 A artifact 一致。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    baseline_kline = requires_kline_data(BASELINE_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    other_kline = requires_kline_data(OTHER_SYMBOL, BASELINE_TIMEFRAME, min_rows=1600)
    assert len(baseline_kline) == len(other_kline)
    start, end = kline_full_window_dates(baseline_kline, other_kline)
    config = slow_full_chain_config_payload(reference_symbol=OTHER_SYMBOL)

    solo_dstar_dir = tmp_path / "dstar" / "solo"
    batch_dstar_dir = tmp_path / "dstar" / "batch"
    solo_factory = make_factory(tmp_path / "solo")
    assert_slow_full_chain_config(solo_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: solo_dstar_dir))
    solo_result = run_symbol_result(
        solo_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    solo_manifest = runtime_output_manifest(
        solo_result,
        factory=solo_factory,
        symbol=BASELINE_SYMBOL,
    )
    assert_full_chain_runtime(solo_factory, solo_result, manifest=solo_manifest)

    batch_factory = make_factory(tmp_path / "batch")
    assert_slow_full_chain_config(batch_factory, config)
    monkeypatch.setattr(FeaturePreprocessor, "_d_star_cache_dir", staticmethod(lambda: batch_dstar_dir))
    run_symbol_frame(
        batch_factory,
        symbol=OTHER_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_result = run_symbol_result(
        batch_factory,
        symbol=BASELINE_SYMBOL,
        start_date=start,
        end_date=end,
        config_payload=config,
        persist=True,
    )
    batch_a_manifest = runtime_output_manifest(
        batch_a_result,
        factory=batch_factory,
        symbol=BASELINE_SYMBOL,
    )
    assert_full_chain_runtime(batch_factory, batch_a_result, manifest=batch_a_manifest)

    solo = solo_result.features_df
    batch_a = batch_a_result.features_df
    sampled = representative_columns(solo, limit=20)
    assert sampled
    assert canonical_frame_digest(solo) == canonical_frame_digest(batch_a)
    assert_sampled_values_equal(solo, batch_a, columns=sampled)
    assert_manifest_semantics_equal(
        solo_manifest,
        batch_a_manifest,
    )
    assert_dstar_payloads_equal(solo_dstar_dir, batch_dstar_dir, BASELINE_SYMBOL)

    dstar_files = list(batch_dstar_dir.glob("*.json"))
    assert dstar_files, "slow tier must materialize d* artifacts"
    for path in dstar_files:
        if BASELINE_SYMBOL in path.name:
            assert OTHER_SYMBOL not in path.name
