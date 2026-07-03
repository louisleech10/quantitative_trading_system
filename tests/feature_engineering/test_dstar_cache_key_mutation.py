from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from momentum.FeatureEngineering.preprocessing._d_star_cache import DStarCache, PreprocessingContext


BASE_CONTEXT = PreprocessingContext(
    symbol="BTCUSDT",
    timeframe="1h",
    config_hash="c" * 32,
    data_fingerprint="fingerprint-v1",
    feature_schema_hash="schema-v1",
    time_range=(1, 600),
    row_count=600,
    source_data_version="unit",
)
VALUES_A = np.linspace(1.0, 2.0, 600, dtype=np.float64)
VALUES_B = np.linspace(2.0, 3.0, 600, dtype=np.float64)


def _cache(
    cache_dir: Path,
    context: PreprocessingContext = BASE_CONTEXT,
    *,
    max_lag: int = 50,
    calibration_bars: int = 500,
) -> DStarCache:
    return DStarCache(
        context,
        cache_dir,
        adf_threshold=0.1,
        precision=0.01,
        max_lag=max_lag,
        weight_threshold=1e-5,
        sample_size=500,
        calibration_bars=calibration_bars,
    )


def _seed_payload(
    cache_dir: Path,
    context: PreprocessingContext = BASE_CONTEXT,
    *,
    values: np.ndarray = VALUES_A,
    max_lag: int = 50,
    calibration_bars: int = 500,
) -> tuple[DStarCache, dict[str, Any]]:
    cache = _cache(
        cache_dir,
        context,
        max_lag=max_lag,
        calibration_bars=calibration_bars,
    )
    cache.set("feature_fracdiff", 0.375, values)
    cache.flush_atomic()
    return cache, json.loads(cache.path.read_text(encoding="utf-8"))


def _write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def _assert_no_stale_hit(cache: DStarCache, *, values: np.ndarray = VALUES_A, label: str) -> None:
    actual = cache.get("feature_fracdiff", values)
    assert actual == 0.375, f"{label} mutant admitted stale d_star hit: {actual!r}"


def test_mutation_path_symbol_collision_is_rejected_by_payload_symbol(tmp_path: Path) -> None:
    _, payload = _seed_payload(tmp_path, BASE_CONTEXT)
    other_symbol = _cache(tmp_path, replace(BASE_CONTEXT, symbol="ETHUSDT"))
    _write_payload(other_symbol.path, payload)

    assert isinstance(other_symbol, DStarCache)
    with pytest.raises(AssertionError, match="path_symbol"):
        _assert_no_stale_hit(other_symbol, label="path_symbol")


def test_mutation_path_timeframe_collision_is_rejected_by_payload_timeframe(tmp_path: Path) -> None:
    _, payload = _seed_payload(tmp_path, BASE_CONTEXT)
    other_timeframe = _cache(tmp_path, replace(BASE_CONTEXT, timeframe="4h"))
    _write_payload(other_timeframe.path, payload)

    assert isinstance(other_timeframe, DStarCache)
    with pytest.raises(AssertionError, match="path_timeframe"):
        _assert_no_stale_hit(other_timeframe, label="path_timeframe")


def test_mutation_fracdiff_hash_without_max_lag_is_rejected(tmp_path: Path) -> None:
    _, payload = _seed_payload(tmp_path, BASE_CONTEXT, max_lag=60, calibration_bars=500)
    target = _cache(tmp_path, BASE_CONTEXT, max_lag=50, calibration_bars=500)
    payload["max_lag"] = 50
    _write_payload(target.path, payload)

    assert isinstance(target, DStarCache)
    with pytest.raises(AssertionError, match="fracdiff_hash_max_lag"):
        _assert_no_stale_hit(target, label="fracdiff_hash_max_lag")


def test_mutation_fracdiff_hash_without_calibration_bars_is_rejected(tmp_path: Path) -> None:
    _, payload = _seed_payload(tmp_path, BASE_CONTEXT, max_lag=50, calibration_bars=800)
    target = _cache(tmp_path, BASE_CONTEXT, max_lag=50, calibration_bars=500)
    payload["calibration_bars"] = 500
    _write_payload(target.path, payload)

    assert isinstance(target, DStarCache)
    with pytest.raises(AssertionError, match="fracdiff_hash_calibration_bars"):
        _assert_no_stale_hit(target, label="fracdiff_hash_calibration_bars")


def test_mutation_payload_row_count_mismatch_is_rejected(tmp_path: Path) -> None:
    source_context = replace(BASE_CONTEXT, row_count=600, time_range=(1, 600))
    target_context = replace(BASE_CONTEXT, row_count=590, time_range=(1, 600))
    _seed_payload(tmp_path, source_context)
    target = _cache(tmp_path, target_context)

    assert isinstance(target, DStarCache)
    with pytest.raises(AssertionError, match="payload_row_count"):
        _assert_no_stale_hit(target, label="payload_row_count")


def test_mutation_payload_time_range_mismatch_is_rejected(tmp_path: Path) -> None:
    source_context = replace(BASE_CONTEXT, row_count=600, time_range=(1, 600))
    target_context = replace(BASE_CONTEXT, row_count=600, time_range=(1, 590))
    _seed_payload(tmp_path, source_context)
    target = _cache(tmp_path, target_context)

    assert isinstance(target, DStarCache)
    with pytest.raises(AssertionError, match="payload_time_range"):
        _assert_no_stale_hit(target, label="payload_time_range")


def test_mutation_strong_value_fingerprint_mismatch_is_rejected(tmp_path: Path) -> None:
    _seed_payload(tmp_path, BASE_CONTEXT, values=VALUES_A)
    target = _cache(tmp_path, BASE_CONTEXT)

    assert isinstance(target, DStarCache)
    with pytest.raises(AssertionError, match="strong_value_fp"):
        _assert_no_stale_hit(target, values=VALUES_B, label="strong_value_fp")
