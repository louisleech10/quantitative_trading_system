"""B5: batch start/end_date threading and strict-window regression tests."""

from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pandas as pd
import numpy as np
import pytest

import api.services.feature_factory_service as feature_service_module
from api.models.feature_factory_models import BatchGenerateRequest
from api.services.feature_factory_batch_service import FeatureFactoryBatchService
from momentum import factories as momentum_factories
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.factories import create_kline_storage_manager

TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"
DATE_WINDOW_DAYS = 167
ROW_COUNT_TOLERANCE = 8
PRODUCTION_FEATURES_ROOT = Path("data_cache/features")


def _snapshot_production_features() -> set[str]:
    """Record production feature cache paths for pollution checks."""
    if not PRODUCTION_FEATURES_ROOT.exists():
        return set()
    return {str(path) for path in PRODUCTION_FEATURES_ROOT.rglob("*") if path.is_file()}


def _isolate_feature_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Redirect feature writes to tmp_path while keeping real kline reads."""
    real_data_cache = Path(feature_service_module.settings.data_cache_path)
    klines_link = tmp_path / "feature_klines"
    if not klines_link.exists():
        klines_link.symlink_to(real_data_cache / "feature_klines", target_is_directory=True)

    monkeypatch.setattr(feature_service_module.settings, "data_cache_path", tmp_path)

    features_root = tmp_path / "features"
    features_root.mkdir(parents=True, exist_ok=True)
    original_create = momentum_factories.create_feature_factory

    def _create_with_tmp_features(
        cache_dir: Optional[str] = None,
        validate_continuity: bool = True,
    ):
        resolved_cache_dir = cache_dir or str(tmp_path / "feature_klines")
        factory = original_create(
            cache_dir=resolved_cache_dir,
            validate_continuity=validate_continuity,
        )
        factory._storage = FeatureStorage(str(features_root))
        return factory

    monkeypatch.setattr(momentum_factories, "create_feature_factory", _create_with_tmp_features)
    return features_root


@lru_cache(maxsize=1)
def _kline_available() -> bool:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    try:
        df = storage.read_klines("BTCUSDT", "12h", validate_continuity=False)
        return df is not None and len(df) >= 500
    except Exception:
        return False


def _require_kline() -> None:
    if not _kline_available():
        pytest.skip("missing kline cache for batch date integration tests")


def _minimal_batch_config(timeframe: str) -> Dict[str, Any]:
    return {
        "preset": "minimal",
        "timeframes": {
            "primary": timeframe,
            "training": [timeframe],
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {
            "enabled": True,
            "winsorization": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        },
    }


def _timestamp_series(df: pd.DataFrame) -> pd.Series:
    if "timestamp" in df.columns:
        return pd.to_datetime(df["timestamp"].to_numpy(dtype=np.int64), unit="s")
    return pd.to_datetime(df.index.to_numpy(dtype=np.int64), unit="s")


def _load_klines(symbol: str, timeframe: str) -> pd.DataFrame:
    storage = create_kline_storage_manager(cache_dir=TEST_KLINE_CACHE_DIR)
    df = storage.read_klines(symbol, timeframe, validate_continuity=False)
    if df is None or df.empty:
        pytest.skip(f"missing kline data for {symbol}/{timeframe}")
    return df.sort_index()


def _date_range_last_n_days(df: pd.DataFrame, days: int) -> tuple[str, str]:
    index_as_datetime = _timestamp_series(df)
    end_ts = index_as_datetime.max()
    start_ts = end_ts - pd.Timedelta(days=days)
    return start_ts.strftime("%Y-%m-%d"), end_ts.strftime("%Y-%m-%d")


def _strict_row_count(df: pd.DataFrame, start_date: str, end_date: str) -> int:
    index_as_datetime = _timestamp_series(df)
    mask = (index_as_datetime >= pd.Timestamp(start_date)) & (
        index_as_datetime <= pd.Timestamp(end_date)
    )
    return int(mask.sum())


def _manifest_row_count(manifest_path: str) -> int:
    payload = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    row_count = payload.get("row_count")
    if row_count is None:
        metadata = payload.get("metadata") or {}
        row_count = metadata.get("row_count")
    assert row_count is not None, f"manifest missing row_count: {manifest_path}"
    return int(row_count)


def _manifest_row_count_from_result(result: Any) -> int:
    metadata = getattr(result, "metadata", None) or {}
    row_count = metadata.get("row_count")
    if row_count is not None:
        return int(row_count)
    features_df = getattr(result, "features_df", None)
    if features_df is not None:
        return int(len(features_df.index))
    raise AssertionError("result missing row_count and features_df")


async def _wait_until_done(
    service: FeatureFactoryBatchService,
    task_id: str,
    timeout_sec: float = 180.0,
) -> Dict[str, Any]:
    started = time.time()
    while True:
        status = service.get_status(task_id)
        if status and status["status"] in {"completed", "partial", "failed"}:
            return status
        if time.time() - started > timeout_sec:
            raise TimeoutError(f"Task did not finish in {timeout_sec}s: {task_id}")
        await asyncio.sleep(0.05)


def test_batch_request_date_accepts_optional_dates() -> None:
    request = BatchGenerateRequest(
        symbols=["BTCUSDT"],
        timeframe="12h",
        start_date="2025-01-01",
        end_date="2025-06-21",
    )
    assert request.start_date == "2025-01-01"
    assert request.end_date == "2025-06-21"

    default_request = BatchGenerateRequest(symbols=["BTCUSDT"], timeframe="12h")
    assert default_request.start_date is None
    assert default_request.end_date is None


def test_batch_no_date_passes_none_to_generate_features(tmp_path) -> None:
    captured: List[Dict[str, Any]] = []

    def fake_generate(**kwargs: Any) -> MagicMock:
        captured.append(dict(kwargs))
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "BTCUSDT_1h.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        FeatureFactoryBatchService._compute_single(
            "BTCUSDT",
            "1h",
            None,
            True,
            str(tmp_path),
        )

    assert len(captured) == 1
    assert captured[0]["start_date"] is None
    assert captured[0]["end_date"] is None


def test_batch_date_threading_passes_dates_to_generate_features(tmp_path) -> None:
    captured: List[Dict[str, Any]] = []

    def fake_generate(**kwargs: Any) -> MagicMock:
        captured.append(dict(kwargs))
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "BTCUSDT_1h.h5")
        return result

    factory_mock = MagicMock()
    factory_mock.generate_features.side_effect = fake_generate

    with patch("momentum.factories.create_feature_factory", return_value=factory_mock):
        FeatureFactoryBatchService._compute_single(
            "BTCUSDT",
            "1h",
            None,
            True,
            str(tmp_path),
            "",
            "2025-01-01",
            "2025-06-21",
        )

    assert captured[0]["start_date"] == "2025-01-01"
    assert captured[0]["end_date"] == "2025-06-21"


@pytest.mark.asyncio
async def test_batch_date_threading_via_run_in_executor(
    monkeypatch,
    tmp_path,
    batch_service_factory,
) -> None:
    captured: List[tuple[Optional[str], Optional[str]]] = []

    def _compute_capture_dates(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
        _batch_id: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        captured.append((start_date, end_date))
        return f"/tmp/{symbol}_{timeframe}.h5"

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_capture_dates),
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=["BTCUSDT"],
        timeframe="12h",
        start_date="2025-01-01",
        end_date="2025-06-21",
    )
    task_id = await service.start_batch(request)
    await _wait_until_done(service, task_id)

    assert captured == [("2025-01-01", "2025-06-21")]


@pytest.mark.asyncio
async def test_batch_date_applied_row_count_primary_12h(
    monkeypatch,
    tmp_path,
    batch_service_factory,
    mock_browse_registrar,
) -> None:
    _require_kline()
    features_before = _snapshot_production_features()
    _isolate_feature_output(monkeypatch, tmp_path)
    symbol = "BTCUSDT"
    timeframe = "12h"
    klines = _load_klines(symbol, timeframe)
    start_date, end_date = _date_range_last_n_days(klines, DATE_WINDOW_DAYS)
    expected_rows = _strict_row_count(klines, start_date, end_date)

    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=[symbol],
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        config_override=_minimal_batch_config(timeframe),
        force_regenerate=True,
    )
    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id, timeout_sec=600.0)

    assert status["status"] == "completed"
    assert mock_browse_registrar.calls, "batch should register manifest"
    manifest_path = mock_browse_registrar.calls[0]["manifest_path"]
    actual_rows = _manifest_row_count(manifest_path)
    assert abs(actual_rows - expected_rows) <= ROW_COUNT_TOLERANCE
    assert actual_rows < len(klines) - 100, "date-selected batch must not run full history"
    assert _snapshot_production_features() == features_before


@pytest.mark.asyncio
async def test_batch_date_applied_row_count_primary_1h(
    monkeypatch,
    tmp_path,
    batch_service_factory,
    mock_browse_registrar,
) -> None:
    _require_kline()
    features_before = _snapshot_production_features()
    _isolate_feature_output(monkeypatch, tmp_path)
    symbol = "BTCUSDT"
    timeframe = "1h"
    klines = _load_klines(symbol, timeframe)
    start_date, end_date = _date_range_last_n_days(klines, DATE_WINDOW_DAYS)
    expected_rows = _strict_row_count(klines, start_date, end_date)

    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")
    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=[symbol],
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        config_override=_minimal_batch_config(timeframe),
        force_regenerate=True,
    )
    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id, timeout_sec=600.0)

    assert status["status"] == "completed"
    manifest_path = mock_browse_registrar.calls[0]["manifest_path"]
    actual_rows = _manifest_row_count(manifest_path)
    assert abs(actual_rows - expected_rows) <= ROW_COUNT_TOLERANCE
    assert actual_rows < len(klines) - 500, "date-selected 1h batch must not run full history"
    assert _snapshot_production_features() == features_before


@pytest.mark.asyncio
async def test_batch_vs_single_row_count_and_hash_consistency(
    monkeypatch,
    tmp_path,
    batch_service_factory,
    mock_browse_registrar,
) -> None:
    _require_kline()
    features_before = _snapshot_production_features()
    features_root = _isolate_feature_output(monkeypatch, tmp_path)
    symbol = "BTCUSDT"
    timeframe = "12h"
    klines = _load_klines(symbol, timeframe)
    start_date, end_date = _date_range_last_n_days(klines, DATE_WINDOW_DAYS)
    config_override = _minimal_batch_config(timeframe)

    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "0")

    factory = momentum_factories.create_feature_factory(cache_dir=TEST_KLINE_CACHE_DIR)
    single_result = factory.generate_features(
        symbol=symbol,
        timeframe=timeframe,
        config_override=config_override,
        force_regenerate=True,
        start_date=start_date,
        end_date=end_date,
    )
    single_row_count = _manifest_row_count_from_result(single_result)
    single_hash = str(single_result.metadata["config_hash"])

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=[symbol],
        timeframe=timeframe,
        start_date=start_date,
        end_date=end_date,
        config_override=config_override,
        force_regenerate=True,
    )
    task_id = await service.start_batch(request)
    status = await _wait_until_done(service, task_id, timeout_sec=300.0)
    assert status["status"] == "completed"

    batch_manifest_path = mock_browse_registrar.calls[-1]["manifest_path"]
    batch_manifest_payload = json.loads(Path(batch_manifest_path).read_text(encoding="utf-8"))
    batch_row_count = _manifest_row_count(batch_manifest_path)
    batch_hash = str(batch_manifest_payload.get("config_hash"))

    assert batch_row_count == single_row_count
    assert batch_hash == single_hash
    assert str(single_result.hdf5_path).startswith(str(features_root))
    assert str(batch_manifest_path).startswith(str(features_root))
    assert _snapshot_production_features() == features_before


@pytest.mark.asyncio
async def test_batch_date_resume_preserves_dates(
    monkeypatch,
    tmp_path,
    batch_service_factory,
) -> None:
    captured: List[tuple[Optional[str], Optional[str]]] = []

    def _compute_capture_dates(
        symbol: str,
        timeframe: str,
        _config_override,
        _force_regenerate: bool,
        _cache_dir: Optional[str] = None,
        _batch_id: str = "",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> str:
        captured.append((start_date, end_date))
        return f"/tmp/{symbol}_{timeframe}.h5"

    monkeypatch.setattr(
        "api.services.feature_factory_batch_service.ProcessPoolExecutor",
        ThreadPoolExecutor,
    )
    monkeypatch.setattr(
        FeatureFactoryBatchService,
        "_compute_single",
        staticmethod(_compute_capture_dates),
    )

    service = batch_service_factory(tmp_path)
    request = BatchGenerateRequest(
        symbols=["BTCUSDT", "ETHUSDT"],
        timeframe="12h",
        start_date="2025-01-01",
        end_date="2025-06-21",
    )
    checkpoint = service._build_initial_checkpoint("batch-date-resume", request)
    checkpoint["completed_items"] = [{
        "symbol": "BTCUSDT",
        "timeframe": "12h",
        "output_paths": ["/tmp/BTCUSDT_12h.h5"],
        "rss_peak_item_mb": 100,
        "rss_after_gc_mb": 80,
    }]
    checkpoint["queued_items"] = [{"symbol": "ETHUSDT", "timeframe": "12h"}]
    service._safe_persist_checkpoint(checkpoint)

    assert checkpoint["request_payload"]["start_date"] == "2025-01-01"
    assert checkpoint["request_payload"]["end_date"] == "2025-06-21"

    response = await service.resume_batch("batch-date-resume")
    assert response["status"] == "running"
    await _wait_until_done(service, "batch-date-resume")

    assert captured == [("2025-01-01", "2025-06-21")]


def test_legacy_checkpoint_without_date_defaults_none(batch_service_factory, tmp_path) -> None:
    service = batch_service_factory(tmp_path)
    legacy_payload = {
        "symbols": ["BTCUSDT"],
        "timeframe": "12h",
        "config_override": None,
        "force_regenerate": False,
        "max_workers": 4,
    }
    request = BatchGenerateRequest(**legacy_payload)
    assert request.start_date is None
    assert request.end_date is None

    checkpoint = service._build_initial_checkpoint("legacy-batch", request)
    checkpoint["request_payload"] = dict(legacy_payload)
    resumed = BatchGenerateRequest(**checkpoint["request_payload"])
    assert resumed.start_date is None
    assert resumed.end_date is None
