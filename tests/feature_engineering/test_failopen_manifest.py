"""Batch3 fail-open manifest completeness + status model tests."""

from __future__ import annotations

import json
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator

import numpy as np
import pandas as pd
import pytest

from momentum.core.contracts import LayerExecutionResult, LayerStatus
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import (
    COMPLETENESS_FIELD_NAMES,
    FeatureStorage,
    QUALITY_STATUS_PRECEDENCE,
    build_completeness_meta_from_layer_results,
    default_completeness_meta,
    merge_quality_status,
    resolve_run_status,
)

TEST_KLINE_CACHE_DIR = "data_cache/feature_klines"
BASELINE_SYMBOL = "BTCUSDT"
BASELINE_TIMEFRAME = "12h"


def _ok_layer(data: pd.DataFrame) -> LayerExecutionResult:
    return LayerExecutionResult(
        data=data,
        status=LayerStatus.ok,
        failed_engines=(),
        reason=None,
        configured_engines=1,
        present_engines=1,
        required_engines=0,
        dependency_error=False,
    )


def _failed_layer(data: pd.DataFrame, *, reason: str = "injected L3 failure") -> LayerExecutionResult:
    return LayerExecutionResult(
        data=data,
        status=LayerStatus.layer_failed,
        failed_engines=("rolling",),
        reason=reason,
        configured_engines=1,
        present_engines=0,
        required_engines=1,
        dependency_error=False,
    )


def _sample_groups(row_index: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    return {
        "pre_ic": pd.DataFrame(
            {"feat_a": np.array([1.0, 2.0, 3.0], dtype=np.float32)},
            index=row_index,
        )
    }


def _healthy_layer_results(index: pd.DatetimeIndex) -> dict[str, LayerExecutionResult]:
    frame = pd.DataFrame({"x": np.ones(len(index), dtype=np.float32)}, index=index)
    return {f"Layer {idx}": _ok_layer(frame) for idx in range(1, 7)}


def _complete_artifact_fields(
    row_index: pd.DatetimeIndex,
    *,
    schema_version: str = "raw_v2",
    quality_status: str = "complete",
) -> dict[str, object]:
    fields = build_completeness_meta_from_layer_results(
        _healthy_layer_results(row_index),
        timeframe="1h",
    )
    fields.update(
        {
            "complete": True,
            "schema_version": schema_version,
            "quality_status": quality_status,
            "path": "raw",
        }
    )
    return fields


def _write_disk_manifest(run_dir: Path, artifacts: dict[str, dict]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": "l7_v2",
        "complete": True,
        "symbol": "BTCUSDT",
        "tf": "1h",
        "config_hash": run_dir.name,
        "artifacts": artifacts,
    }
    (run_dir / FeatureStorage.L7_V2_MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def test_completeness_fields(tmp_path: Path) -> None:
    """注入層失敗 → failed_layers / partial / raw_v2；健康 run → complete。"""
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-01-01", periods=3, freq="h")
    groups = _sample_groups(row_index)
    tf = "1h"
    config_hash = "cfg_failopen_manifest"

    healthy_manifest_path = storage.feature_run_dir("BTCUSDT", tf, config_hash) / FeatureStorage.L7_V2_MANIFEST_NAME
    storage.write_raw(
        "BTCUSDT",
        tf,
        config_hash,
        groups,
        row_index=row_index,
        layer_results=_healthy_layer_results(row_index),
    )
    healthy = json.loads(healthy_manifest_path.read_text(encoding="utf-8"))
    assert healthy["schema_version"] == FeatureStorage.L7_RAW_SCHEMA_VERSION == "raw_v2"
    assert healthy["quality_status"] == "complete"
    assert healthy["failed_layers"] == []
    assert healthy["failed_timeframes"] == []
    assert healthy["present_timeframes"] == ["1h"]
    assert healthy["artifacts"]["raw"]["schema_version"] == "raw_v2"
    assert healthy["artifacts"]["raw"]["quality_status"] == "complete"

    partial_results = _healthy_layer_results(row_index)
    partial_results["Layer 3"] = _failed_layer(
        pd.DataFrame(index=row_index),
        reason="injected L3 failure",
    )
    partial_hash = "cfg_failopen_partial"
    storage.write_raw(
        "BTCUSDT",
        tf,
        partial_hash,
        groups,
        row_index=row_index,
        layer_results=partial_results,
    )
    partial_manifest = json.loads(
        (storage.feature_run_dir("BTCUSDT", tf, partial_hash) / FeatureStorage.L7_V2_MANIFEST_NAME).read_text(
            encoding="utf-8"
        )
    )
    assert "L3" in partial_manifest["failed_layers"]
    assert partial_manifest["quality_status"] == "partial"
    assert partial_manifest["schema_version"] == "raw_v2"
    assert any("L3:" in reason for reason in partial_manifest["failure_reasons"])

    meta_only = build_completeness_meta_from_layer_results(partial_results, timeframe=tf)
    assert meta_only["quality_status"] == "partial"
    assert "L3" in meta_only["failed_layers"]
    default_meta = default_completeness_meta(tf)
    assert default_meta["quality_status"] == "unknown"
    assert default_meta["present_layers"] == []


def test_persist_false_generate_features_metadata(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """FFACT_USE_CGSA=0 + persist=False 走非 CGSA generate_features，metadata 帶 completeness status。"""
    from tests.feature_engineering.test_failopen_contract import _apply_baseline_env, _freeze_baseline_module

    _apply_baseline_env(monkeypatch)
    monkeypatch.setenv("FFACT_USE_CGSA", "0")
    monkeypatch.setenv("FFACT_LAYER1_PARALLEL", "0")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))

    freeze = _freeze_baseline_module()
    start_date, end_date = freeze._window_dates()

    factory = create_feature_factory(
        cache_dir=TEST_KLINE_CACHE_DIR,
        validate_continuity=False,
    )
    result = factory.generate_features(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        # 本測試驗 metadata completeness 欄(L1-L6),非 L6.5 數值;非 CGSA 路徑
        # d* cache 不可用,開 preprocessing 會觸發全寬 ADF/d* 搜尋跑 30+ 分。
        config_override={"preprocessing": {"enabled": False}},
        force_regenerate=True,
        persist=False,
        start_date=start_date,
        end_date=end_date,
    )

    assert result.hdf5_path == ""
    assert result.metadata["quality_status"] == "complete"
    assert result.metadata["run_status"] == "complete"
    assert result.metadata["failed_layers"] == []
    assert factory.layer_results
    run_dir = factory._storage.feature_run_dir(
        BASELINE_SYMBOL,
        BASELINE_TIMEFRAME,
        str(result.metadata["config_hash"]),
    )
    assert not (run_dir / FeatureStorage.L7_V2_MANIFEST_NAME).exists()


def _run_concurrent_raw_processed_merge(
    storage: FeatureStorage,
    *,
    config_hash: str = "cfg_concurrent",
    lock_factory: Callable[[Path], Iterator[None]] | None = None,
    entry_barrier: threading.Barrier | None = None,
    lock_sleep_s: float = 0.0,
    load_interleave_barrier: threading.Barrier | None = None,
    load_interleave_sleep_s: float = 0.0,
    read_via_reader: bool = True,
) -> tuple[list[BaseException], dict[str, object]]:
    """並行 raw/processed writer；可注入 lock 行為與 barrier 放大交錯窗。"""
    row_index = pd.date_range("2026-01-01", periods=3, freq="h")
    groups = _sample_groups(row_index)
    processed_groups = {
        "selected": pd.DataFrame(
            {"feat_a_rank": np.array([0.1, 0.5, 0.9], dtype=np.float32)},
            index=row_index,
        )
    }
    symbol = "BTCUSDT"
    tf = "1h"
    layer_results = _healthy_layer_results(row_index)
    errors: list[BaseException] = []

    real_lock = FeatureStorage._manifest_v2_lock
    real_load = FeatureStorage._load_feature_manifest_v2_if_exists

    @classmethod
    def _interleaved_load(cls, run_dir: Path) -> dict[str, object]:
        loaded = real_load(run_dir)
        if load_interleave_barrier is not None:
            load_interleave_barrier.wait(timeout=30.0)
        if load_interleave_sleep_s > 0.0:
            time.sleep(load_interleave_sleep_s)
        return loaded

    @classmethod
    @contextmanager
    def _effective_lock(cls, run_dir: Path) -> Iterator[None]:
        if entry_barrier is not None:
            entry_barrier.wait(timeout=30.0)
        if lock_factory is not None:
            with lock_factory(run_dir):
                if lock_sleep_s > 0.0:
                    time.sleep(lock_sleep_s)
                yield
        else:
            with real_lock(run_dir):
                if lock_sleep_s > 0.0:
                    time.sleep(lock_sleep_s)
                yield

    def _write_raw() -> None:
        try:
            storage.write_raw(
                symbol,
                tf,
                config_hash,
                groups,
                row_index=row_index,
                layer_results=layer_results,
            )
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    def _write_processed() -> None:
        try:
            storage.write_processed(
                symbol,
                tf,
                config_hash,
                processed_groups,
                layer_results=layer_results,
            )
        except BaseException as exc:  # pragma: no cover - surfaced via errors list
            errors.append(exc)

    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(FeatureStorage, "_manifest_v2_lock", _effective_lock)
        if load_interleave_barrier is not None or load_interleave_sleep_s > 0.0:
            patcher.setattr(FeatureStorage, "_load_feature_manifest_v2_if_exists", _interleaved_load)
        threads = [threading.Thread(target=_write_raw), threading.Thread(target=_write_processed)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    reader = FeatureReader(str(storage.base_path))
    if read_via_reader:
        manifest = reader.load_manifest_v2(symbol, tf, config_hash, artifact_kind="raw")
    else:
        manifest_path = storage.feature_run_dir(symbol, tf, config_hash) / FeatureStorage.L7_V2_MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return errors, manifest


def test_manifest_concurrent_raw_processed_merge(tmp_path: Path) -> None:
    """並行 raw/processed writer（barrier + 鎖內 sleep）終態須同時保留兩個 artifact。"""
    storage = FeatureStorage(str(tmp_path / "features"))
    barrier = threading.Barrier(2)

    errors, manifest = _run_concurrent_raw_processed_merge(
        storage,
        entry_barrier=barrier,
        lock_sleep_s=0.05,
    )

    assert errors == []
    assert "raw" in manifest["artifacts"]
    assert "processed" in manifest["artifacts"]
    assert manifest["artifacts"]["raw"]["schema_version"] == "raw_v2"
    assert manifest["artifacts"]["processed"]["schema_version"] == "processed_v2"
    assert manifest["artifacts"]["raw"]["quality_status"] == "complete"
    assert manifest["artifacts"]["processed"]["quality_status"] == "complete"
    for field in COMPLETENESS_FIELD_NAMES:
        assert field in manifest["artifacts"]["raw"]
        assert field in manifest["artifacts"]["processed"]


def test_manifest_concurrent_merge_fails_without_lock(tmp_path: Path) -> None:
    """關閉 thread+flock 鎖時，同場景並行寫入須丟失 artifact（證偽力）。"""

    @contextmanager
    def _noop_lock(_run_dir: Path) -> Iterator[None]:
        yield

    storage = FeatureStorage(str(tmp_path / "features"))
    barrier = threading.Barrier(2)
    load_barrier = threading.Barrier(2)

    errors, manifest = _run_concurrent_raw_processed_merge(
        storage,
        config_hash="cfg_no_lock",
        lock_factory=_noop_lock,
        entry_barrier=barrier,
        lock_sleep_s=0.05,
        load_interleave_barrier=load_barrier,
        load_interleave_sleep_s=0.05,
        read_via_reader=False,
    )

    assert errors == []
    artifacts = manifest.get("artifacts", {})
    assert not (
        "raw" in artifacts and "processed" in artifacts
    ), "expected race without lock to drop one artifact"


def test_status_model() -> None:
    """merge 偏序 + 遷移偵測：legacy / V2-舊 unknown / empty_selection 贏 complete。"""
    row_index = pd.date_range("2026-01-01", periods=3, freq="h")
    complete_fields = _complete_artifact_fields(row_index)

    legacy_manifest = FeatureReader._adapt_legacy_manifest_v2(
        manifest={"groups": {}, "total_features": 0, "total_rows": 0},
        symbol="BTCUSDT",
        tf="1h",
        config_hash="legacy_cfg",
        artifact_kind="raw",
    )
    assert FeatureReader.resolve_run_status(legacy_manifest) == "legacy"
    assert legacy_manifest["quality_status"] == "legacy"

    v2_old_no_completeness = {
        "artifacts": {
            "raw": {
                "complete": True,
                "schema_version": "raw_v2",
                "quality_status": "complete",
            }
        }
    }
    assert resolve_run_status(v2_old_no_completeness) == "unknown"

    raw_complete = dict(complete_fields)
    raw_complete.update(
        {
            "complete": True,
            "schema_version": "raw_v2",
            "quality_status": "complete",
        }
    )
    processed_empty = dict(complete_fields)
    processed_empty.update(
        {
            "complete": True,
            "schema_version": "processed_v2",
            "quality_status": "empty_selection",
        }
    )
    dual_artifact = {"artifacts": {"raw": raw_complete, "processed": processed_empty}}
    assert merge_quality_status(dual_artifact["artifacts"]) == "empty_selection"
    assert resolve_run_status(dual_artifact) == "empty_selection"

    assert merge_quality_status(
        {
            "raw": raw_complete,
            "processed": {**processed_empty, "quality_status": "complete"},
        }
    ) == "complete"


def test_merge_quality_status_full_precedence() -> None:
    """偏序 failed>unknown>legacy>partial>empty_selection>complete 成對可證偽。"""
    row_index = pd.date_range("2026-01-01", periods=3, freq="h")

    def _artifact(status: str, *, schema_version: str = "raw_v2") -> dict[str, object]:
        if status == "legacy":
            return {
                "complete": True,
                "schema_version": "legacy_v7",
                "quality_status": "legacy",
                **{field: [] for field in COMPLETENESS_FIELD_NAMES if field.endswith("_layers")},
                "expected_timeframes": ["1h"],
                "present_timeframes": ["1h"],
                "failed_timeframes": [],
                "failure_reasons": [],
            }
        base = _complete_artifact_fields(row_index, schema_version=schema_version, quality_status=status)
        base["quality_status"] = status
        return base

    status_values = list(QUALITY_STATUS_PRECEDENCE)
    for higher_idx, higher in enumerate(status_values):
        for lower in status_values[higher_idx + 1 :]:
            merged = merge_quality_status(
                {
                    "a": _artifact(higher),
                    "b": _artifact(lower),
                }
            )
            assert merged == higher, f"expected {higher} > {lower}, got {merged}"


def test_v2_old_manifest_reader_returns_unknown(tmp_path: Path) -> None:
    """落盤 V2-舊 manifest → FeatureReader 真實讀取路徑 → run_status=unknown。"""
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))

    missing_completeness_dir = storage.feature_run_dir("BTCUSDT", "1h", "cfg_v2_old_no_completeness")
    _write_disk_manifest(
        missing_completeness_dir,
        {
            "raw": {
                "complete": True,
                "schema_version": "raw_v2",
                "quality_status": "complete",
                "path": "raw",
                "feature_schema_hash": "abc",
                "row_count": 3,
                "time_range": {"start": None, "end": None},
                "total_features": 1,
                "group_count": 1,
                "groups": {},
            }
        },
    )
    manifest = reader.load_manifest_v2(
        "BTCUSDT",
        "1h",
        "cfg_v2_old_no_completeness",
        artifact_kind="raw",
    )
    assert FeatureReader.resolve_run_status(manifest) == "unknown"

    missing_schema_dir = storage.feature_run_dir("BTCUSDT", "1h", "cfg_missing_schema_version")
    artifact = dict(_complete_artifact_fields(pd.date_range("2026-01-01", periods=3, freq="h")))
    artifact.pop("schema_version")
    _write_disk_manifest(missing_schema_dir, {"raw": artifact})
    manifest_missing_schema = reader.load_manifest_v2(
        "BTCUSDT",
        "1h",
        "cfg_missing_schema_version",
        artifact_kind="raw",
    )
    assert FeatureReader.resolve_run_status(manifest_missing_schema) == "unknown"
