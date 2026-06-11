"""Batch5 fail-open consumer gate + cache/resume tests."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.ic_engine import ICEngine, ICReadError
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.consumer_gate import TrainingReadError, is_run_status_cacheable
from momentum.FeatureEngineering.feature_config import FactoryConfig
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import (
    COMPLETENESS_FIELD_NAMES,
    FeatureStorage,
    build_completeness_meta_from_layer_results,
)
from momentum.factories import create_feature_factory
from tests.feature_engineering.test_failopen_manifest import (
    _complete_artifact_fields,
    _healthy_layer_results,
    _write_disk_manifest,
)


def _partial_manifest(tmp_path: Path, *, run_status: str = "partial") -> tuple[FeatureStorage, str, str]:
    storage = FeatureStorage(str(tmp_path / "features"))
    row_index = pd.date_range("2026-01-01", periods=3, freq="h")
    layer_results = _healthy_layer_results(row_index)
    completeness = build_completeness_meta_from_layer_results(layer_results, timeframe="1h")
    completeness["quality_status"] = run_status
    completeness["failed_layers"] = ["L3"] if run_status == "partial" else []
    artifact = _complete_artifact_fields(row_index, quality_status=run_status)
    artifact.update(completeness)
    artifact["groups"] = {
        "g1": {
            "path": "raw/g1.parquet",
            "columns": ["feat_a"],
            "nan_ratio": 0.0,
            "row_count": 3,
        }
    }
    artifact["total_features"] = 1
    config_hash = f"cfg_{run_status}"
    run_dir = storage.feature_run_dir("BTCUSDT", "1h", config_hash)
    run_dir.mkdir(parents=True, exist_ok=True)
    group_dir = run_dir / "raw"
    group_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"feat_a": [1.0, 2.0, 3.0]}, index=row_index).to_parquet(group_dir / "g1.parquet")
    _write_disk_manifest(run_dir, {"raw": artifact})
    manifest_path = run_dir / FeatureStorage.L7_V2_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["run_status"] = run_status
    manifest["quality_status"] = run_status
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return storage, config_hash, run_status


def test_ic_rejects_partial_and_unknown(tmp_path: Path) -> None:
    storage, config_hash, _ = _partial_manifest(tmp_path, run_status="partial")
    reader = FeatureReader(str(storage.base_path))
    engine = ICEngine({})
    manifest = reader.load_manifest_v2("BTCUSDT", "1h", config_hash, artifact_kind="raw")

    with pytest.raises(ICReadError, match="partial"):
        engine._validate_l7_raw_manifest(
            manifest,
            symbol="BTCUSDT",
            tf="1h",
            config_hash=config_hash,
            allow_partial_ic=False,
        )

    _, unknown_hash, _ = _partial_manifest(tmp_path / "unknown", run_status="unknown")
    reader_unknown = FeatureReader(str((tmp_path / "unknown" / "features")))
    unknown_manifest = reader_unknown.load_manifest_v2(
        "BTCUSDT", "1h", unknown_hash, artifact_kind="raw"
    )
    with pytest.raises(ICReadError, match="unknown"):
        engine._validate_l7_raw_manifest(
            unknown_manifest,
            symbol="BTCUSDT",
            tf="1h",
            config_hash=unknown_hash,
            allow_partial_ic=False,
        )


def test_ic_allow_partial_flag(tmp_path: Path) -> None:
    storage, config_hash, _ = _partial_manifest(tmp_path, run_status="partial")
    reader = FeatureReader(str(storage.base_path))
    engine = ICEngine({})
    manifest = reader.load_manifest_v2("BTCUSDT", "1h", config_hash, artifact_kind="raw")
    assert manifest["run_status"] == "partial"
    raw_artifact = engine._validate_l7_raw_manifest(
        manifest,
        symbol="BTCUSDT",
        tf="1h",
        config_hash=config_hash,
        allow_partial_ic=True,
    )
    assert raw_artifact["total_features"] == 1


def test_training_rejects_partial(tmp_path: Path) -> None:
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    storage, config_hash, _ = _partial_manifest(tmp_path, run_status="partial")
    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add(
        {
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "config_hash": config_hash,
            "feature_count": 1,
            "row_count": 3,
            "hdf5_relative_path": "",
        }
    )
    library = FeatureLibrary(registry, storage, FeatureReader(str(storage.base_path)))
    with pytest.raises(TrainingReadError, match="partial"):
        library.load_for_training("BTCUSDT", "1h", allow_partial_training=False)


def test_browser_reads_partial_with_status(tmp_path: Path) -> None:
    storage, config_hash, _ = _partial_manifest(tmp_path, run_status="partial")
    reader = FeatureReader(str(storage.base_path))
    manifest = reader.load_manifest_v2(
        "BTCUSDT",
        "1h",
        config_hash,
        artifact_kind="raw",
        consumer="browse",
    )
    assert manifest["run_status"] == "partial"
    frame = reader.load_columns_v2(
        "BTCUSDT",
        "1h",
        config_hash,
        ["feat_a"],
        artifact_kind="raw",
        consumer="browse",
    )
    assert not frame.empty


def test_cache_gate_partial_unknown_miss_complete_hit(tmp_path: Path) -> None:
    factory = create_feature_factory(validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))

    for status in ("partial", "unknown", "complete"):
        storage, config_hash, _ = _partial_manifest(tmp_path / status, run_status=status)
        if status != "complete":
            factory._storage = storage
        else:
            factory._storage = storage

        metadata = {"config_hash": config_hash, "run_status": status, "quality_status": status}
        if status == "complete":
            metadata.update(
                {
                    "expected_layers": ["L1", "L2"],
                    "present_layers": ["L1", "L2"],
                    "failed_layers": [],
                    "expected_timeframes": ["1h"],
                    "present_timeframes": ["1h"],
                    "failed_timeframes": [],
                }
            )
        cached = SimpleNamespace(metadata=metadata, features_df=pd.DataFrame({"x": [1.0]}))
        factory._storage.load_factory_output = MagicMock(return_value=cached)  # type: ignore[method-assign]

        result = factory._try_load_cache("BTCUSDT", "1h", config_hash)
        if status == "complete":
            assert result is not None
        else:
            assert result is None


def test_failopen_flags_in_factory_config_api_ts() -> None:
    config = ConfigManager().get_merged_config()
    for field in (
        "allow_partial_layers",
        "allow_partial_timeframes",
        "allow_partial_ic",
        "allow_partial_training",
        "max_inf_ratio",
        "max_nan_ratio",
    ):
        assert field in FactoryConfig.model_fields

    from api.models.feature_factory_models import FailOpenGateFlags

    flags = FailOpenGateFlags()
    assert flags.allow_partial_ic is False
    assert flags.max_inf_ratio == 0.0

    import pathlib

    ts_source = pathlib.Path("frontend/src/lib/types.ts").read_text(encoding="utf-8")
    for token in (
        "allow_partial_layers",
        "allow_partial_ic",
        "allow_partial_training",
        "max_inf_ratio",
        "max_nan_ratio",
    ):
        assert token in ts_source


def test_is_run_status_cacheable_matrix() -> None:
    assert is_run_status_cacheable("complete") is True
    for status in ("partial", "unknown", "legacy", "failed", "empty_selection"):
        assert is_run_status_cacheable(status) is False


def _legacy_reader_fixture(tmp_path: Path) -> tuple[FeatureReader, str]:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": [1.0, 2.0, 3.0]})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return FeatureReader(str(base_dir)), config_hash


def test_legacy_reader_strict_rejects_ic_and_training(tmp_path: Path) -> None:
    from momentum.FeatureEngineering.feature_library import FeatureLibrary
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    reader, config_hash = _legacy_reader_fixture(tmp_path)
    engine = ICEngine({})

    with pytest.raises(TrainingReadError, match="legacy"):
        reader.load_manifest_v2(
            "LEGACY",
            "1h",
            config_hash,
            artifact_kind="raw",
            consumer="strict",
        )

    with pytest.raises(ICReadError, match="legacy"):
        engine._validate_l7_raw_manifest(
            reader.load_manifest_v2(
                "LEGACY",
                "1h",
                config_hash,
                artifact_kind="raw",
                consumer="browse",
            ),
            symbol="LEGACY",
            tf="1h",
            config_hash=config_hash,
        )

    registry = FeatureRegistry(tmp_path / "registry.json")
    registry.add(
        {
            "symbol": "LEGACY",
            "timeframe": "1h",
            "config_hash": config_hash,
            "feature_count": 1,
            "row_count": 3,
            "hdf5_relative_path": "",
        }
    )
    library = FeatureLibrary(registry, FeatureStorage(str(tmp_path / "features")), reader)
    with pytest.raises(TrainingReadError, match="legacy"):
        library.load_for_training("LEGACY", "1h")


def test_ic_cache_rejects_missing_source_run_status(tmp_path: Path) -> None:
    engine = ICEngine({})
    selected_path = tmp_path / "ic_selected_features_BTCUSDT_1h.json"
    label = pd.Series([0.1, 0.2, 0.3])
    cached_payload = {
        "ic_scores": {"feat_a": 0.5},
        "quality_status": "complete",
        "data_fingerprint": {
            "symbol": "BTCUSDT",
            "tf": "1h",
            "config_hash": "cfg_x",
            "row_count": 3,
        },
    }
    selected_path.write_text(json.dumps(cached_payload), encoding="utf-8")

    assert (
        engine._try_reuse_cached_ic_scores(
            selected_path=selected_path,
            symbol="BTCUSDT",
            tf="1h",
            config_hash="cfg_x",
            label=label,
            merged_ic_params={"label_horizon": "1", "selection_window": {"start": "a"}},
            resolved_threshold=0.02,
            allow_partial_ic=False,
        )
        is None
    )


def test_metadata_complete_without_completeness_is_unknown() -> None:
    from momentum.FeatureEngineering.consumer_gate import effective_run_status_from_metadata

    status = effective_run_status_from_metadata(
        {"quality_status": "complete", "config_hash": "abc"}
    )
    assert status == "unknown"


def test_try_load_cache_rejects_legacy_complete_without_completeness(tmp_path: Path) -> None:
    factory = create_feature_factory(validate_continuity=False)
    storage = FeatureStorage(str(tmp_path / "features"))
    factory._storage = storage
    config_hash = "cfg_legacy_complete"
    metadata = {"config_hash": config_hash, "quality_status": "complete", "run_status": "complete"}
    cached = SimpleNamespace(metadata=metadata, features_df=pd.DataFrame({"x": [1.0]}))
    factory._storage.load_factory_output = MagicMock(return_value=cached)  # type: ignore[method-assign]

    assert factory._try_load_cache("BTCUSDT", "1h", config_hash) is None


def test_cgsa_skips_resume_when_l7_manifest_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import patch

    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    work_dir = tmp_path / "cgsa_work"
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))
    work_dir.mkdir(parents=True)
    (work_dir / "manifest.json").write_text(
        json.dumps({"groups": {"g1": {"status": "complete"}}}),
        encoding="utf-8",
    )

    factory = create_feature_factory(validate_continuity=False)
    factory._storage = FeatureStorage(str(tmp_path / "features"))

    with patch(
        "momentum.FeatureEngineering.feature_factory.ColumnGroupRegistry.resume_from_manifest"
    ) as resume_mock:
        registry = factory._prepare_cgsa_registry("BTCUSDT", "1h", config_hash="cfg12345678")
        resume_mock.assert_not_called()
    assert registry is not None
