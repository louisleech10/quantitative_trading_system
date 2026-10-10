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
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)

    start, end = _date_window(120)
    cfg = _minimal_config()

    def _persisted(root: Path, result: Any) -> pd.DataFrame:
        # FRAMEPATH：CGSA 之 features_df 只帶索引不帶欄 ⇒ 欄值改由本次落盤之 raw 讀回（同一輸出窗）
        reader = FeatureReader(str(root))
        config_hash = str(result.metadata["config_hash"])
        manifest = reader.load_manifest_v2("BTCUSDT", "12h", config_hash, allow_partial=True)
        columns = [c for group in manifest["artifacts"]["raw"]["groups"].values() for c in group.get("columns", [])]
        return reader.load_columns_v2("BTCUSDT", "12h", config_hash, columns, allow_partial=True)

    monkeypatch.setenv("FFACT_WARMUP_TRIM", "0")
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
    off_df = _persisted(features_root / "off", res_off)
    on_df = _persisted(features_root / "on", res_on)

    window = factory_on._current_output_window
    assert window is not None and window.warmup_enabled
    cols = _position_independent_columns(list(on_df.columns))
    # CGSA 落盤保留全 NaN 死欄（frame 之 L7 死欄刪除不在 CGSA 落盤路徑；主委 2026-10-08 探針：本設定 25 欄中
    # meta_12h_Momentum_Divergence、meta_12h_Volatility_Regime 全 NaN、stable_start 為 None）⇒ 只量有有效值之欄
    cols = [c for c in cols if on_df[c].notna().any()]
    assert cols, "no position-independent columns to measure"
    k = min(50, max(1, window.max_warmup_bars // 4))
    off_sub = off_df[cols].iloc[:k]
    on_sub = on_df[cols].iloc[:k]
    valid_off = float(off_sub.notna().mean().mean())
    valid_on = float(on_sub.notna().mean().mean())
    # FFSTAT v32（使用者 2026-09-27 R1「預熱恆開」、刪 FFACT_WARMUP_TRIM）：環境變數不再能關預熱 ⇒ 兩次輸出開頭 k 列
    # 之有效率相同，且位置無關欄於輸出開頭即全數有效（改前斷言「開啟比關閉多 5%」之前提已不存在）
    assert valid_off == valid_on, f"FFACT_WARMUP_TRIM 仍影響結果：on={valid_on:.3f} off={valid_off:.3f}"
    if "warmup_insufficient" not in (res_on.metadata or {}):
        assert valid_on >= 0.999, f"預熱恆開後輸出開頭仍有空值：on={valid_on:.3f}"
    _assert_data_cache_unchanged(before)


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

        # ICFIRSTALIGN Task 2.4：run_ic_first 經正式 CGSA 生成，以本次起訖自行定窗（無自帶 raw_data／layers）
        reader = FeatureReader(str(features_root))
        result = factory.run_ic_first(
            symbol,
            timeframe,
            config,
            start_date=start,
            end_date=end,
            ic_engine=ICEngine({"methods": ["spearman"]}),
            feature_reader=reader,
            ic_threshold=0.0,
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
        env={"FFACT_WARMUP_TRIM": "1"},  # ICFIRSTALIGN Task 2.4：IC-first 只經 CGSA
        config_override=_minimal_config(),
        ic_first=True,
    )


@pytest.mark.requires_kline
def test_warmup_trim_ic_first_public_window_init(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """public generate_features 初始化 B6 window；run_ic_first 以本次起訖自行定窗（ICFIRSTALIGN Task 2.0）仍 trim，
    且結束後 factory 之窗還原為呼叫前同一物件。（Task 2.4：IC-first 只經 CGSA。）"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    _require_kline()
    before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path / "ic_first_public")
    monkeypatch.setenv("FFACT_WARMUP_TRIM", "1")

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
        start_date=start,
        end_date=end,
        ic_engine=ICEngine({"methods": ["spearman"]}),
        feature_reader=FeatureReader(str(features_root)),
        ic_threshold=0.0,
    )
    assert factory._current_output_window is window
    assert ic_result.metadata["output_window"]["output_start"] == str(window.output_start)
    assert len(ic_result.features_df) == expected_rows
    _assert_trimmed_first_row_is_start(ic_result.features_df.index, start, window)
    _assert_data_cache_unchanged(before)
