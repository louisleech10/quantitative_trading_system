"""B6 warmup-then-trim backend tests (B6a+B6b)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np
import pandas as pd
import pytest

from momentum import factories as momentum_factories
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.warmup_window import (
    OutputWindow,
    compute_row_bounds,
    compute_warmup_insufficient,
    estimate_max_warmup_bars,
    is_warmup_trim_enabled,
    max_ingest_index_before_output_start,
    output_row_count,
    resolve_output_window,
    trim_dataframe_to_output_window,
)
from momentum.factories import create_feature_factory, create_kline_storage_manager

TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"
PRODUCTION_FEATURES_ROOT = Path("data_cache/features")
POSITION_INDEPENDENT_EXCLUDE = re.compile(
    r"(OBV|AD|ADOSC|VWAP|fracdiff_|adf_|label_|post_ic_)",
    re.IGNORECASE,
)


def _snapshot_production_features() -> Set[str]:
    if not PRODUCTION_FEATURES_ROOT.exists():
        return set()
    return {str(p) for p in PRODUCTION_FEATURES_ROOT.rglob("*") if p.is_file()}


def _assert_data_cache_unchanged(before: Set[str]) -> None:
    after = _snapshot_production_features()
    new_files = after - before
    assert not new_files, f"data_cache pollution: {sorted(new_files)[:5]}"


def _isolate_feature_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    cgsa_root = tmp_path / "cgsa_work"
    cgsa_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(cgsa_root))

    features_root = tmp_path / "features"
    features_root.mkdir(parents=True, exist_ok=True)
    original_create = momentum_factories.create_feature_factory

    def _create_with_tmp_features(
        cache_dir: Optional[str] = None,
        validate_continuity: bool = True,
    ):
        resolved_cache_dir = cache_dir or TEST_KLINE_CACHE_DIR
        factory = original_create(
            cache_dir=resolved_cache_dir,
            validate_continuity=validate_continuity,
        )
        factory._storage = FeatureStorage(str(features_root))
        return factory

    monkeypatch.setattr(momentum_factories, "create_feature_factory", _create_with_tmp_features)
    return features_root


def _kline_available() -> bool:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    try:
        df = storage.read_klines("BTCUSDT", "12h", validate_continuity=False)
        return df is not None and len(df) >= 500
    except Exception:
        return False


def _require_kline() -> None:
    if not _kline_available():
        pytest.fail("missing kline cache for B6 warmup tests")


def _minimal_config(timeframe: str = "12h") -> Dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": timeframe,
            "training": [timeframe],
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close", "volume"], "synthetic_sources": []},
        "cross_sectional": {"enabled": False},
        "preprocessing": {
            "enabled": True,
            "winsorization": {"enabled": True, "window": 100},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        },
        "nan_strategy": {
            "l7_dead_feature_drop": {"enabled": False},
        },
    }


def _timestamp_series(df: pd.DataFrame) -> pd.Series:
    if "timestamp" in df.columns:
        return pd.to_datetime(df["timestamp"].to_numpy(dtype=np.int64), unit="s")
    idx = df.index.to_numpy(dtype=np.int64)
    unit = "ms" if abs(int(idx[0])) >= 1_000_000_000_000 else "s"
    return pd.to_datetime(idx, unit=unit)


def _date_window(days: int = 120) -> tuple[str, str]:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    df = storage.read_klines("BTCUSDT", "12h", validate_continuity=False)
    ts = _timestamp_series(df)
    end_ts = ts.max()
    start_ts = end_ts - pd.Timedelta(days=days)
    return start_ts.strftime("%Y-%m-%d"), end_ts.strftime("%Y-%m-%d")


def _multi_tf_config(timeframe: str = "12h") -> Dict[str, Any]:
    cfg = _minimal_config(timeframe)
    cfg["timeframes"] = {
        "primary": "12h",
        "training": ["1h", "12h"],
        "alignment": "point_in_time",
        "alignment_mode": "open_minus",
    }
    return cfg


def _expected_output_row_count_from_ingest(
    factory: Any,
    symbol: str,
    timeframe: str,
    config: Any,
    start: str,
    end: str,
    window: OutputWindow,
) -> int:
    """從 ingest/raw 軸計算預期公開列數（非 trim 後結果）。"""
    ingest_start = window.ingest_start if window.warmup_enabled else start
    raw = factory._layer0_data_ingestion(
        symbol,
        timeframe,
        config,
        start_date=ingest_start,
        end_date=end,
    )
    return output_row_count(raw.index, window)


def _assert_trimmed_first_row_is_start(
    index: pd.Index,
    start: str,
    window: OutputWindow,
) -> None:
    ts = _timestamp_series(pd.DataFrame(index=index))
    assert ts.min() >= pd.Timestamp(start)
    if window.warmup_enabled:
        start_idx, _ = compute_row_bounds(index, window)
        assert start_idx == 0, "trimmed output must begin at output_start (index position 0)"


def _read_manifest_row_count(manifest_path: Path) -> int:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if "row_count" in payload:
        return int(payload["row_count"])
    artifacts = payload.get("artifacts") or {}
    for kind in ("raw", "processed", "validated"):
        entry = artifacts.get(kind) or {}
        if "row_count" in entry:
            return int(entry["row_count"])
    raise AssertionError(f"manifest missing row_count: {manifest_path}")


def _resolve_manifest_path(result: Any, features_root: Path) -> Optional[Path]:
    meta = result.metadata or {}
    manifest_raw = meta.get("manifest_path")
    if manifest_raw:
        path = Path(str(manifest_raw))
        if path.name == FeatureStorage.L7_V2_MANIFEST_NAME and path.exists():
            return path
    config_hash = str(meta.get("config_hash", ""))
    timeframe = str(meta.get("timeframe", "12h"))
    symbol = str(meta.get("symbol", "BTCUSDT"))
    candidate = (
        features_root / symbol / timeframe / config_hash / FeatureStorage.L7_V2_MANIFEST_NAME
    )
    if candidate.exists():
        return candidate
    return None


def _position_independent_columns(columns: List[str]) -> List[str]:
    return [c for c in columns if not POSITION_INDEPENDENT_EXCLUDE.search(c)]


# ── B6a: warmup_bars_estimate ─────────────────────────────────────────────


def test_warmup_bars_estimate_includes_l1_l3_l65() -> None:
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    config = factory._resolve_config(_minimal_config())
    max_w = estimate_max_warmup_bars(config, "12h", ["12h"])
    assert max_w >= 100
    assert max_w >= config.preprocessing.winsorization.window


def test_warmup_bars_estimate_l5_beta_when_enabled() -> None:
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    cfg = _minimal_config()
    cfg["cross_sectional"] = {"enabled": True, "features": {"beta": {"enabled": True}}}
    config = factory._resolve_config(cfg)
    off = estimate_max_warmup_bars(
        factory._resolve_config(_minimal_config()), "12h", ["12h"]
    )
    on = estimate_max_warmup_bars(config, "12h", ["12h"])
    assert on >= 60
    assert on >= off


def test_resolve_output_window_flag_off_is_strict() -> None:
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    config = factory._resolve_config(_minimal_config())
    window = resolve_output_window(config, "12h", "2024-06-01", "2024-12-01")
    assert window.warmup_enabled is False
    assert window.ingest_start == "2024-06-01"
    monkeypatch.undo()


# ── B6b: ingest / trim / insufficient ─────────────────────────────────────


@pytest.mark.requires_kline
def test_warmup_ingest_range_multitf_primary_ingest_before_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    _isolate_feature_output(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    start, end = _date_window(90)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    config = factory._resolve_config(_minimal_config())
    window = resolve_output_window(config, "12h", start, end)
    raw = factory._layer0_data_ingestion(
        "BTCUSDT",
        "12h",
        config,
        start_date=window.ingest_start,
        end_date=end,
    )
    max_ingest = max_ingest_index_before_output_start(raw, window)
    assert max_ingest is not None
    assert max_ingest < pd.Timestamp(start)
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_trim_no_leak_row_count_matches_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    start, end = _date_window(90)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(_minimal_config())
    window = resolve_output_window(config, "12h", start, end)
    expected_rows = _expected_output_row_count_from_ingest(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override=_minimal_config(),
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )
    assert len(result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(result.features_df.index, start, window)
    ts = _timestamp_series(result.features_df)
    assert ts.min() >= pd.Timestamp(start)
    if end:
        assert ts.max() <= pd.Timestamp(end) + pd.Timedelta(hours=12)
    manifest_path = _resolve_manifest_path(result, features_root)
    if manifest_path is not None:
        assert _read_manifest_row_count(manifest_path) == expected_rows
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_insufficient_report_near_dataset_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    _isolate_feature_output(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    df = storage.read_klines("BTCUSDT", "12h", validate_continuity=False)
    ts = _timestamp_series(df)
    start = ts.min().strftime("%Y-%m-%d")
    end = (ts.min() + pd.Timedelta(days=30)).strftime("%Y-%m-%d")

    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override=_minimal_config(),
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )
    meta = result.metadata or {}
    if "warmup_insufficient" in meta:
        wi = meta["warmup_insufficient"]
        assert wi["needed"] > wi["available"]
        assert wi["affected_bars"] == wi["needed"] - wi["available"]
    assert meta.get("label_tail_nan_bars") == 21
    assert "cumulative_anchor" in meta
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_quality_gain_position_independent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)

    start, end = _date_window(120)
    cfg = _minimal_config()

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    factory_off = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_off._storage = FeatureStorage(str(features_root / "off"))
    res_off = factory_off.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    factory_on = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory_on._storage = FeatureStorage(str(features_root / "on"))
    res_on = factory_on.generate_features(
        "BTCUSDT",
        "12h",
        config_override=cfg,
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )

    window = factory_on._current_output_window
    assert window is not None and window.warmup_enabled
    cols = _position_independent_columns(list(res_on.features_df.columns))
    assert cols, "no position-independent columns to measure"
    k = min(50, max(1, window.max_warmup_bars // 4))
    off_sub = res_off.features_df[cols].iloc[:k]
    on_sub = res_on.features_df[cols].iloc[:k]
    valid_off = float(off_sub.notna().mean().mean())
    valid_on = float(on_sub.notna().mean().mean())
    if "warmup_insufficient" not in (res_on.metadata or {}):
        assert valid_on >= valid_off + 0.05, f"on={valid_on:.3f} off={valid_off:.3f}"
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_flag_off_golden_baseline_check() -> None:
    if not _kline_available():
        pytest.fail("missing kline cache")
    env = os.environ.copy()
    env.pop("FFACT_WARMUP_TRIM", None)
    env["FFACT_WARMUP_TRIM"] = "0"
    proc = subprocess.run(
        ["python", "scripts/build_l65_golden_baseline.py", "--check"],
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_trim_dataframe_preserves_values() -> None:
    idx = pd.date_range("2024-01-01", periods=10, freq="12h")
    df = pd.DataFrame({"a": np.arange(10, dtype=float)}, index=idx)
    window = OutputWindow(
        ingest_start="2023-12-20",
        output_start="2024-01-04",
        output_end="2024-01-05",
        max_warmup_bars=5,
        warmup_enabled=True,
    )
    trimmed = trim_dataframe_to_output_window(df, window)
    assert len(trimmed) == 3
    np.testing.assert_array_equal(trimmed["a"].to_numpy(), np.array([6.0, 7.0, 8.0]))


def test_warmup_flag_off_preserves_config_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    """flag 關時 config_hash 與 B6 strict 一致；flag 開才分裂 cache key。"""
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    config = factory._resolve_config(_minimal_config())
    start, end = _date_window(60)

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    hash_strict_a = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    hash_strict_b = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    assert hash_strict_a == hash_strict_b

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    hash_warmup = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    assert hash_warmup != hash_strict_a

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
    hash_strict_c = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    assert hash_strict_c == hash_strict_a


def _run_cgsa_l1_l6_into_registry(
    factory: Any,
    symbol: str,
    timeframe: str,
    config: Any,
    start: str,
    end: str,
    window: OutputWindow,
) -> pd.DataFrame:
    """執行與 generate_features 一致的 CGSA L1-L6，將非空 groups 寫入 registry。"""
    factory._current_symbol = symbol
    factory._current_timeframe = timeframe
    factory._current_output_window = window

    config_hash = factory._compute_config_hash(
        config, symbol, timeframe, start_date=start, end_date=end,
    )
    factory._current_config_hash = config_hash
    factory._cgsa_registry = factory._prepare_cgsa_registry(symbol, timeframe, config_hash)

    raw_data = factory._layer0_data_ingestion(
        symbol,
        timeframe,
        config,
        start_date=factory._layer0_ingest_start_date_for_tf(
            timeframe, config.timeframes.primary,
        ),
        end_date=end,
    )
    factory._current_raw_data = raw_data

    layer1 = factory._execute_layer1_6(
        "Layer 1", factory._layer1_atomic_indicators, raw_data, config,
    ).data
    layer2 = factory._spill_to_memmap(
        factory._execute_layer1_6(
            "Layer 2", factory._layer2_derived_features, layer1, raw_data, config,
        ).data,
        "layer2",
    )
    layer3 = factory._execute_layer1_6(
        "Layer 3", factory._layer3_rolling_aggregation, layer1, layer2, config,
    ).data
    layer4 = factory._execute_layer1_6(
        "Layer 4", factory._layer4_lag_features, layer1, layer2, layer3, raw_data, config,
    ).data
    layer5 = factory._execute_layer1_6(
        "Layer 5", factory._layer5_cross_sectional, layer1, layer2, config,
    ).data
    layer6 = factory._execute_layer1_6(
        "Layer 6", factory._layer6_meta_features, layer1, layer2, raw_data, config,
    ).data
    factory._persist_single_tf_l3_l6_to_cgsa(layer3, layer4, layer5, layer6)
    return raw_data


def _assert_warmup_trim_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    path_name: str,
    env: Dict[str, str],
    config_override: Dict[str, Any],
    timeframe: str = "12h",
    symbol: str = "BTCUSDT",
    days: int = 90,
    ic_first: bool = False,
) -> None:
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path / path_name)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    start, end = _date_window(days)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(config_override)
    window = resolve_output_window(config, timeframe, start, end)
    expected_rows = _expected_output_row_count_from_ingest(
        factory, symbol, timeframe, config, start, end, window,
    )

    if ic_first:
        from momentum.Analysis.ic_engine import ICEngine
        from momentum.FeatureEngineering.feature_reader import FeatureReader

        factory._current_output_window = window
        raw_data = factory._layer0_data_ingestion(
            symbol,
            timeframe,
            config,
            start_date=window.ingest_start if window.warmup_enabled else start,
            end_date=end,
        )
        _, layers = factory._run_l1_l6_for_ic_first(symbol, timeframe, config)
        reader = FeatureReader(str(features_root))
        result = factory.run_ic_first(
            symbol,
            timeframe,
            config,
            raw_data=raw_data,
            layers=layers,
            config_hash=factory._compute_config_hash(
                config, symbol, timeframe, start_date=start, end_date=end,
            ),
            ic_engine=ICEngine({"methods": ["spearman"]}),
            feature_reader=reader,
            storage=factory._storage,
            ic_threshold=0.0,
            persist=True,
        )
    else:
        result = factory.generate_features(
            symbol,
            timeframe,
            config_override=config_override,
            force_regenerate=True,
            start_date=start,
            end_date=end,
        )

    assert len(result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(result.features_df.index, start, window)
    manifest_path = _resolve_manifest_path(result, features_root)
    if manifest_path is not None:
        assert _read_manifest_row_count(manifest_path) == expected_rows
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_trim_non_cgsa_l7_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _assert_warmup_trim_artifact(
        monkeypatch,
        tmp_path,
        path_name="non_cgsa",
        env={"FFACT_WARMUP_TRIM": "1", "FFACT_USE_CGSA": "0"},
        config_override=_minimal_config(),
    )


@pytest.mark.requires_kline
def test_warmup_trim_cgsa_raw(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _assert_warmup_trim_artifact(
        monkeypatch,
        tmp_path,
        path_name="cgsa_raw",
        env={"FFACT_WARMUP_TRIM": "1", "FFACT_USE_CGSA": "1"},
        config_override=_minimal_config(),
    )


@pytest.mark.requires_kline
def test_warmup_trim_cgsa_validate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """CGSA validate/V7：非空 registry groups + row_slice trim + manifest row_count。"""
    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "1")

    start, end = _date_window(90)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(_minimal_config())
    window = resolve_output_window(config, "12h", start, end)

    raw_data = _run_cgsa_l1_l6_into_registry(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    registry = factory._cgsa_registry
    assert registry is not None
    group_count = len(list(registry.iter_all()))
    total_features = int(registry.total_columns())
    assert group_count > 0, "CGSA validate test requires non-empty registry groups"
    assert total_features > 0, "CGSA validate test requires non-empty feature columns"

    config_hash = factory._compute_config_hash(
        config, "BTCUSDT", "12h", start_date=start, end_date=end,
    )
    result = factory._layer7_validate_and_persist(
        symbol="BTCUSDT",
        timeframe="12h",
        raw_data=raw_data,
        layers=[],
        config=config,
        elapsed=1.0,
        config_hash=config_hash,
        persist=True,
    )
    expected_rows = _expected_output_row_count_from_ingest(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    assert result.feature_count == total_features
    assert len(result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(result.features_df.index, start, window)
    manifest_path = _resolve_manifest_path(result, features_root)
    if manifest_path is not None:
        assert _read_manifest_row_count(manifest_path) == expected_rows
    _assert_data_cache_unchanged(before)


@pytest.mark.requires_kline
def test_warmup_trim_multi_tf(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _assert_warmup_trim_artifact(
        monkeypatch,
        tmp_path,
        path_name="multi_tf",
        env={
            "FFACT_WARMUP_TRIM": "1",
            "FFACT_USE_CGSA": "0",
            "FFACT_MULTI_TF_PARALLEL": "0",
        },
        config_override=_multi_tf_config(),
        timeframe="12h",
    )


@pytest.mark.requires_kline
def test_warmup_trim_ic_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    _assert_warmup_trim_artifact(
        monkeypatch,
        tmp_path,
        path_name="ic_first",
        env={"FFACT_WARMUP_TRIM": "1", "FFACT_USE_CGSA": "0"},
        config_override=_minimal_config(),
        ic_first=True,
    )


@pytest.mark.requires_kline
def test_warmup_trim_ic_first_public_window_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """public generate_features 初始化 B6 window；run_ic_first 不手設 window 仍 trim。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path / "ic_first_public")
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")
    monkeypatch.setenv("FFACT_USE_CGSA", "0")

    start, end = _date_window(90)
    factory = create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR, validate_continuity=False)
    factory._storage = FeatureStorage(str(features_root))
    config = factory._resolve_config(_minimal_config())

    gen_result = factory.generate_features(
        "BTCUSDT",
        "12h",
        config_override=_minimal_config(),
        force_regenerate=True,
        start_date=start,
        end_date=end,
    )
    window = factory._current_output_window
    assert window is not None and window.warmup_enabled
    expected_rows = _expected_output_row_count_from_ingest(
        factory, "BTCUSDT", "12h", config, start, end, window,
    )
    assert len(gen_result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(gen_result.features_df.index, start, window)

    ic_result = factory.run_ic_first(
        "BTCUSDT",
        "12h",
        config,
        ic_engine=ICEngine({"methods": ["spearman"]}),
        feature_reader=FeatureReader(str(features_root)),
        storage=factory._storage,
        ic_threshold=0.0,
        persist=True,
    )
    assert factory._current_output_window is window
    assert len(ic_result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(ic_result.features_df.index, start, window)
    _assert_data_cache_unchanged(before)
