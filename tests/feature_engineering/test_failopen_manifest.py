"""Batch3 fail-open manifest completeness + status model tests."""

from __future__ import annotations

import json
import sys
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


# ---------------------------------------------------------------------------
# FF-TFMETA（docs/FFTFMETA_SPEC.md）Task 1.1／1.2／2.1／2.3 驗收
# ---------------------------------------------------------------------------

from momentum.FeatureEngineering import feature_storage as fs_module  # noqa: E402
from momentum.FeatureEngineering.feature_storage import (  # noqa: E402
    apply_quality_degradation,
    build_timeframe_completeness,
    resolve_completeness_meta,
)

_ALL_LAYERS = ["L1", "L2", "L3", "L4", "L5", "L6"]
_MULTI = ["1h", "12h"]
_IDX3 = pd.date_range("2026-01-01", periods=3, freq="h")


def _expected_meta(
    *,
    expected_tfs: list[str],
    present_tfs: list[str],
    failed_tfs: list[str],
    failed_layers: list[str],
    present_layers: list[str],
    quality_status: str,
    failure_reasons: list[str],
    expected_layers: list[str] = _ALL_LAYERS,
) -> dict[str, object]:
    return {
        "expected_layers": list(expected_layers),
        "present_layers": list(present_layers),
        "failed_layers": list(failed_layers),
        "expected_timeframes": list(expected_tfs),
        "present_timeframes": list(present_tfs),
        "failed_timeframes": list(failed_tfs),
        "quality_status": quality_status,
        "failure_reasons": list(failure_reasons),
    }


# --- Task 1.1 ---------------------------------------------------------------

def test_timeframe_completeness_expected_is_ordered_training_tfs() -> None:
    out = build_timeframe_completeness(["12h", "1h", "4h"], [])
    assert out["expected_timeframes"] == ["12h", "1h", "4h"]


def test_timeframe_completeness_present_is_expected_minus_failed() -> None:
    out = build_timeframe_completeness(["1h", "4h", "12h"], ["4h"])
    assert out["present_timeframes"] == ["1h", "12h"]


def test_timeframe_completeness_failed_subset_of_expected() -> None:
    out = build_timeframe_completeness(["1h", "4h", "12h"], ["12h", "1h"])
    assert set(out["failed_timeframes"]) <= set(out["expected_timeframes"])
    assert out["failed_timeframes"] == ["1h", "12h"]


def test_timeframe_completeness_expected_is_present_union_failed() -> None:
    out = build_timeframe_completeness(["1h", "4h", "12h"], ["4h"])
    assert set(out["expected_timeframes"]) == set(out["present_timeframes"]) | set(out["failed_timeframes"])
    assert out["present_timeframes"] == [tf for tf in out["expected_timeframes"] if tf not in out["failed_timeframes"]]


def test_timeframe_completeness_no_failed_present_equals_expected() -> None:
    out = build_timeframe_completeness(_MULTI, [])
    assert out == {"expected_timeframes": _MULTI, "present_timeframes": _MULTI, "failed_timeframes": []}


def test_timeframe_completeness_empty_expected_raises() -> None:
    with pytest.raises(ValueError):
        build_timeframe_completeness([], [])


def test_boundary_01_timeframe_completeness_unknown_failed_raises() -> None:
    with pytest.raises(ValueError):
        build_timeframe_completeness(_MULTI, ["4h"])


def test_boundary_02_timeframe_completeness_dedup_first_occurrence() -> None:
    out = build_timeframe_completeness(["1h", "12h", "1h"], [])
    assert out["expected_timeframes"] == ["1h", "12h"]
    assert out["present_timeframes"] == ["1h", "12h"]


def test_boundary_03_timeframe_completeness_all_failed_present_empty() -> None:
    out = build_timeframe_completeness(_MULTI, ["12h", "1h"])
    assert out == {"expected_timeframes": _MULTI, "present_timeframes": [], "failed_timeframes": _MULTI}


def test_boundary_04_timeframe_completeness_failed_reordered_by_expected() -> None:
    out = build_timeframe_completeness(["1h", "4h", "12h"], ["12h", "4h", "12h"])
    assert out["failed_timeframes"] == ["4h", "12h"]


# --- Task 1.2 ---------------------------------------------------------------

def test_resolve_completeness_single_tf_unchanged() -> None:
    healthy = _healthy_layer_results(_IDX3)
    partial = _healthy_layer_results(_IDX3)
    partial["Layer 3"] = _failed_layer(pd.DataFrame(index=_IDX3), reason="boom")
    for layer_results in (healthy, partial):
        assert resolve_completeness_meta(layer_results, "1h") == build_completeness_meta_from_layer_results(
            layer_results, timeframe="1h"
        )
    assert resolve_completeness_meta({}, "1h") == default_completeness_meta("1h")
    assert resolve_completeness_meta(None, "1h") == default_completeness_meta("1h")


def test_resolve_completeness_healthy_multi_tf() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
    )
    assert meta == _expected_meta(
        expected_tfs=_MULTI, present_tfs=_MULTI, failed_tfs=[],
        failed_layers=[], present_layers=_ALL_LAYERS, quality_status="complete", failure_reasons=[],
    )


def test_resolve_completeness_skipped_tf() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
    )
    assert meta == _expected_meta(
        expected_tfs=_MULTI, present_tfs=["1h"], failed_tfs=["12h"],
        failed_layers=[], present_layers=_ALL_LAYERS, quality_status="partial",
        failure_reasons=["timeframe:12h"],
    )


def test_resolve_completeness_failed_tf_with_layer_failure() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
        cross_tf_layer_failures=("L2:1h:injected L2 failure",),
    )
    assert meta == _expected_meta(
        expected_tfs=_MULTI, present_tfs=["1h"], failed_tfs=["12h"],
        failed_layers=["L2:1h"], present_layers=["L1", "L3", "L4", "L5", "L6"], quality_status="partial",
        failure_reasons=["timeframe:12h", "L2:1h:injected L2 failure"],
    )


def test_resolve_completeness_single_tf_via_canonical_equals_legacy() -> None:
    healthy = _healthy_layer_results(_IDX3)
    meta = resolve_completeness_meta(
        healthy, "1h", timeframe_completeness=build_timeframe_completeness(["1h"], [])
    )
    assert meta == build_completeness_meta_from_layer_results(healthy, timeframe="1h")


def _assert_non_primary_status_case(status_value: str) -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        cross_tf_layer_failures=(f"L3:12h:{status_value}",),
    )
    assert meta == _expected_meta(
        expected_tfs=_MULTI, present_tfs=_MULTI, failed_tfs=[],
        failed_layers=["L3:12h"], present_layers=["L1", "L2", "L4", "L5", "L6"], quality_status="partial",
        failure_reasons=[f"L3:12h:{status_value}"],
    )


def test_resolve_completeness_layer_failed_on_non_primary() -> None:
    _assert_non_primary_status_case(LayerStatus.layer_failed.value)


def test_resolve_completeness_all_engines_failed_on_non_primary() -> None:
    _assert_non_primary_status_case(LayerStatus.all_engines_failed.value)


def test_resolve_completeness_dependency_failed_on_non_primary() -> None:
    _assert_non_primary_status_case(LayerStatus.dependency_failed.value)


def test_resolve_completeness_cross_tf_failures_are_authoritative() -> None:
    """layer_results 為最後處理之週期（可被覆寫），層失敗以 cross_tf_layer_failures 為準。"""
    stale = _healthy_layer_results(_IDX3)
    stale["Layer 3"] = _failed_layer(pd.DataFrame(index=_IDX3), reason="stale")
    meta = resolve_completeness_meta(
        stale,
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        cross_tf_layer_failures=("L3:1h:injected",),
    )
    assert meta["failed_layers"] == ["L3:1h"]
    assert meta["failure_reasons"] == ["L3:1h:injected"]


def _statuses(**overrides: tuple) -> dict:
    base = {f"L{i}": ("ok", "") for i in range(1, 7)}
    base.update(overrides)
    return base


def test_resolve_completeness_layer_status_evidence_expected_layers() -> None:
    """v6（r5 codex P2-02）：有 `layer_status_by_tf` 時層證據以之為準、layer_results 不參與；
    expected_layers＝各 present 週期非 empty_disabled 之 L<n> 聯集（L1–L6 序）。"""
    stale = _healthy_layer_results(_IDX3)
    stale["Layer 3"] = _failed_layer(pd.DataFrame(index=_IDX3), reason="stale")
    meta = resolve_completeness_meta(
        stale, "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        layer_status_by_tf={"1h": _statuses(L2=("empty_disabled", ""), L5=("empty_disabled", "")),
                            "12h": _statuses(L5=("empty_disabled", ""))},
    )
    assert meta["expected_layers"] == ["L1", "L2", "L3", "L4", "L6"]
    assert meta["present_layers"] == ["L1", "L2", "L3", "L4", "L6"]
    assert meta["failed_layers"] == [] and meta["quality_status"] == "complete"


def test_resolve_completeness_layer_status_missing_or_partial_entry_is_unknown() -> None:
    """v6：任一 present 週期無條目、或條目未含 L1–L6 全部六鍵 ⇒ unknown（不得解為無失敗）。"""
    tc = build_timeframe_completeness(_MULTI, [])
    missing = resolve_completeness_meta({}, "1h", timeframe_completeness=tc, layer_status_by_tf={"1h": _statuses()})
    partial = resolve_completeness_meta({}, "1h", timeframe_completeness=tc,
                                        layer_status_by_tf={"1h": _statuses(), "12h": {"L1": ("ok", "")}})
    assert missing["quality_status"] == "unknown"
    assert partial["quality_status"] == "unknown"


def test_resolve_completeness_layer_status_failures_come_from_cross_tf() -> None:
    """v6：層失敗之唯一權威仍為 cross_tf_layer_failures；skipped 週期不需條目。"""
    meta = resolve_completeness_meta(
        {}, "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
        cross_tf_layer_failures=("L2:1h:dependency_failed",),
        layer_status_by_tf={"1h": _statuses(L2=("dependency_failed", ""))},
    )
    assert meta["failed_layers"] == ["L2:1h"]
    assert meta["present_layers"] == ["L1", "L3", "L4", "L5", "L6"]
    assert meta["failure_reasons"] == ["timeframe:12h", "L2:1h:dependency_failed"]
    assert meta["quality_status"] == "partial"


def test_boundary_05_resolve_completeness_empty_selection_override_wins() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        override_quality_status="empty_selection",
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
    )
    assert meta["quality_status"] == "empty_selection"
    assert meta["failed_timeframes"] == ["12h"]


def test_boundary_06_resolve_completeness_no_layer_evidence_unknown() -> None:
    meta = resolve_completeness_meta(
        {}, "1h", timeframe_completeness=build_timeframe_completeness(_MULTI, [])
    )
    assert meta == _expected_meta(
        expected_tfs=_MULTI, present_tfs=_MULTI, failed_tfs=[], expected_layers=[],
        failed_layers=[], present_layers=[], quality_status="unknown", failure_reasons=[],
    )


def test_boundary_07_resolve_completeness_same_layer_two_tfs() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3),
        "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        cross_tf_layer_failures=("L3:1h:a", "L3:12h:b"),
    )
    assert meta["failed_layers"] == ["L3:1h", "L3:12h"]
    assert meta["present_layers"] == ["L1", "L2", "L4", "L5", "L6"]
    assert meta["failure_reasons"] == ["L3:1h:a", "L3:12h:b"]
    assert meta["quality_status"] == "partial"


def test_mutation_resolve_completeness_ignoring_cross_tf_failures_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ③：忽略 cross_tf_layer_failures ⇒ 非 primary 層失敗之案例必紅。"""
    real = fs_module.resolve_completeness_meta

    def _mutant(layer_results, timeframe, **kwargs):
        kwargs["cross_tf_layer_failures"] = ()
        return real(layer_results, timeframe, **kwargs)

    monkeypatch.setattr(sys.modules[__name__], "resolve_completeness_meta", _mutant)
    with pytest.raises(AssertionError):
        _assert_non_primary_status_case(LayerStatus.dependency_failed.value)


def test_mutation_storage_single_tf_timeframes_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """§V mutant ②：storage 改回 [timeframe] ⇒ 健康多週期之週期欄必紅。"""
    real = fs_module.resolve_completeness_meta

    def _mutant(layer_results, timeframe, **kwargs):
        meta = dict(real(layer_results, timeframe, **kwargs))
        meta.update({"expected_timeframes": [timeframe], "present_timeframes": [timeframe], "failed_timeframes": []})
        return meta

    monkeypatch.setattr(sys.modules[__name__], "resolve_completeness_meta", _mutant)
    with pytest.raises(AssertionError):
        test_resolve_completeness_healthy_multi_tf()


# --- Task 2.1 ---------------------------------------------------------------

_ROOT_PRESERVED_KEYS = COMPLETENESS_FIELD_NAMES + ("failure_reasons", "quality_status", "run_status")
_TC_FAILURE = ("L2:12h:dependency_failed",)


def _write_multi_raw(storage: FeatureStorage, config_hash: str) -> dict:
    storage.write_raw(
        "BTCUSDT", "1h", config_hash, _sample_groups(_IDX3),
        row_index=_IDX3,
        layer_results=_healthy_layer_results(_IDX3),
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        cross_tf_layer_failures=_TC_FAILURE,
    )
    path = storage.feature_run_dir("BTCUSDT", "1h", config_hash) / FeatureStorage.L7_V2_MANIFEST_NAME
    return json.loads(path.read_text(encoding="utf-8"))


def test_writer_timeframe_completeness_passes_canonical(tmp_path: Path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    manifest = _write_multi_raw(storage, "cfg_tfmeta_writer")
    canonical = resolve_completeness_meta(
        _healthy_layer_results(_IDX3), "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
        cross_tf_layer_failures=_TC_FAILURE,
    )
    for key in COMPLETENESS_FIELD_NAMES + ("quality_status", "failure_reasons"):
        assert manifest[key] == canonical[key], key
        assert manifest["artifacts"]["raw"][key] == canonical[key], key
    assert manifest["present_timeframes"] == _MULTI
    assert manifest["quality_status"] == "partial"


def test_writer_timeframe_completeness_ic_first_rewrite_preserves_root(tmp_path: Path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    before = _write_multi_raw(storage, "cfg_tfmeta_icfirst")
    storage.write_raw(
        "BTCUSDT", "1h", "cfg_tfmeta_icfirst", _sample_groups(_IDX3),
        row_index=_IDX3, layer_results=_healthy_layer_results(_IDX3),
    )
    storage.write_processed(
        "BTCUSDT", "1h", "cfg_tfmeta_icfirst", _sample_groups(_IDX3),
        layer_results=_healthy_layer_results(_IDX3),
    )
    path = storage.feature_run_dir("BTCUSDT", "1h", "cfg_tfmeta_icfirst") / FeatureStorage.L7_V2_MANIFEST_NAME
    after = json.loads(path.read_text(encoding="utf-8"))
    for key in _ROOT_PRESERVED_KEYS:
        assert after[key] == before[key], key
    assert "processed" in after["artifacts"]


def test_writer_timeframe_completeness_fresh_single_tf_unchanged(tmp_path: Path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    storage.write_raw(
        "BTCUSDT", "1h", "cfg_tfmeta_single", _sample_groups(_IDX3),
        row_index=_IDX3, layer_results=_healthy_layer_results(_IDX3),
    )
    path = storage.feature_run_dir("BTCUSDT", "1h", "cfg_tfmeta_single") / FeatureStorage.L7_V2_MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    legacy = build_completeness_meta_from_layer_results(_healthy_layer_results(_IDX3), timeframe="1h")
    for key in COMPLETENESS_FIELD_NAMES + ("quality_status", "failure_reasons"):
        assert manifest[key] == legacy[key], key
    assert manifest["run_status"] == "complete"


def test_boundary_11_writer_timeframe_completeness_overwrite_takes_new(tmp_path: Path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    _write_multi_raw(storage, "cfg_tfmeta_overwrite")
    storage.write_raw(
        "BTCUSDT", "1h", "cfg_tfmeta_overwrite", _sample_groups(_IDX3),
        row_index=_IDX3, layer_results=_healthy_layer_results(_IDX3),
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
    )
    path = storage.feature_run_dir("BTCUSDT", "1h", "cfg_tfmeta_overwrite") / FeatureStorage.L7_V2_MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["failed_timeframes"] == ["12h"]
    assert manifest["failed_layers"] == []
    assert manifest["failure_reasons"] == ["timeframe:12h"]


def test_boundary_12_writer_timeframe_completeness_empty_selection_keeps_canonical(tmp_path: Path) -> None:
    storage = FeatureStorage(str(tmp_path / "features"))
    storage.write_processed(
        "BTCUSDT", "1h", "cfg_tfmeta_empty", {},
        layer_results=_healthy_layer_results(_IDX3),
        timeframe_completeness=build_timeframe_completeness(_MULTI, []),
    )
    path = storage.feature_run_dir("BTCUSDT", "1h", "cfg_tfmeta_empty") / FeatureStorage.L7_V2_MANIFEST_NAME
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["artifacts"]["processed"]["quality_status"] == "empty_selection"
    assert manifest["present_timeframes"] == _MULTI
    assert manifest["expected_timeframes"] == _MULTI


def test_mutation_writer_timeframe_completeness_root_overwrite_is_caught(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """IC-first 二次寫入若把根週期欄改回 [tf]，保留測試必紅。"""
    real_build = FeatureStorage._build_feature_manifest_v2

    def _mutant(self, **kwargs):
        manifest = real_build(self, **kwargs)
        manifest["present_timeframes"] = [kwargs["tf"]]
        return manifest

    monkeypatch.setattr(FeatureStorage, "_build_feature_manifest_v2", _mutant)
    with pytest.raises(AssertionError):
        test_writer_timeframe_completeness_ic_first_rewrite_preserves_root(tmp_path)


# --- Task 2.3（純函式；整合驗收見 test_degradation_in_manifest_*） ---------------

def _complete_meta() -> dict[str, object]:
    return build_completeness_meta_from_layer_results(_healthy_layer_results(_IDX3), timeframe="1h")


def test_degradation_pure_nan_threshold() -> None:
    out = apply_quality_degradation(
        _complete_meta(), inf_ratio=0.0, nan_ratio=0.3, max_inf_ratio=0.0, max_nan_ratio=0.1,
        preprocessing_applied=None,
    )
    assert out["quality_status"] == "partial"
    assert out["run_status"] == "partial"
    assert out["failure_reasons"] == ["nan_ratio=0.3>max_nan_ratio=0.1"]
    assert out["quality_thresholds"] == {
        "max_inf_ratio": 0.0, "max_nan_ratio": 0.1, "observed_inf_ratio": 0.0, "observed_nan_ratio": 0.3,
    }


def test_degradation_pure_healthy_unchanged() -> None:
    meta = _complete_meta()
    out = apply_quality_degradation(
        meta, inf_ratio=0.0, nan_ratio=0.05, max_inf_ratio=0.0, max_nan_ratio=0.1, preprocessing_applied=True,
    )
    assert out == meta


def test_degradation_pure_l65_failure() -> None:
    out = apply_quality_degradation(
        _complete_meta(), inf_ratio=0.0, nan_ratio=0.0, max_inf_ratio=0.0, max_nan_ratio=0.1,
        preprocessing_applied=False,
    )
    assert out["quality_status"] == "partial"
    assert out["failure_reasons"] == ["L6.5:preprocessing_failed"]
    assert out["preprocessing_applied"] is False


def test_boundary_16_degradation_in_manifest_reason_order_timeframe_layer_quality() -> None:
    meta = resolve_completeness_meta(
        _healthy_layer_results(_IDX3), "1h",
        timeframe_completeness=build_timeframe_completeness(_MULTI, ["12h"]),
        cross_tf_layer_failures=("L2:1h:x",),
    )
    out = apply_quality_degradation(
        meta, inf_ratio=0.01, nan_ratio=0.3, max_inf_ratio=0.0, max_nan_ratio=0.1, preprocessing_applied=False,
    )
    assert out["failure_reasons"] == [
        "timeframe:12h",
        "L2:1h:x",
        "L6.5:preprocessing_failed",
        "inf_ratio=0.01>max_inf_ratio=0",
        "nan_ratio=0.3>max_nan_ratio=0.1",
    ]


@pytest.mark.requires_kline
def test_degradation_in_manifest_cgsa_nan_threshold(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Task 2.3 驗證：NaN 比例超門檻（真實 run、max_nan_ratio=0.0）⇒ manifest 與 result.metadata 之 quality_status
    皆 partial 且 failure_reasons 相等。"""
    from tests.feature_engineering import fftfmeta_golden_helpers as fg

    fg.prepare_env(monkeypatch, tmp_path)
    root, _factory, result = fg.generate(tmp_path, fg.degraded_single_tf_payload())
    manifest = fg.l7_manifest(root, "1h", result)
    assert manifest["quality_status"] == result.metadata["quality_status"] == "partial"
    assert manifest["artifacts"]["raw"]["quality_status"] == "partial"
    assert manifest["failure_reasons"] == result.metadata["failure_reasons"]
    assert any(r.startswith("nan_ratio=") for r in manifest["failure_reasons"])


@pytest.mark.requires_kline
def test_writer_timeframe_completeness_ic_first_rewrite_preserves_quality_degradation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Task 2.1 驗證（r5 codex P1-02）：先寫含 Task 2.3 品質降級之 run（真實 kline、max_nan_ratio=0.0），
    再以 IC-first 形（不帶週期參數）各寫一次 raw 與 processed ⇒ 根與 raw 之 quality_status、run_status、
    failure_reasons（含 nan_ratio= 原因）逐鍵等於首寫。"""
    from tests.feature_engineering import fftfmeta_golden_helpers as fg

    fg.prepare_env(monkeypatch, tmp_path)
    root, factory, result = fg.generate(tmp_path, fg.degraded_single_tf_payload())
    before = fg.l7_manifest(root, "1h", result)
    assert any(r.startswith("nan_ratio=") for r in before["failure_reasons"])
    config_hash = str(result.metadata["config_hash"])
    storage = factory._storage
    storage.write_raw("BTCUSDT", "1h", config_hash, _sample_groups(_IDX3), row_index=_IDX3,
                      layer_results=_healthy_layer_results(_IDX3))
    storage.write_processed("BTCUSDT", "1h", config_hash, _sample_groups(_IDX3),
                            layer_results=_healthy_layer_results(_IDX3))
    after = fg.l7_manifest(root, "1h", result)
    for key in ("quality_status", "run_status", "failure_reasons") + COMPLETENESS_FIELD_NAMES:
        assert after[key] == before[key], key
    assert after["quality_status"] == "partial"


@pytest.mark.requires_kline
def test_degradation_in_manifest_frame_l65_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Task 2.3 驗證：frame 路徑 L6.5 失敗 ⇒ meta.json 與 result.metadata 皆含 L6.5:preprocessing_failed。"""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from tests.feature_engineering import fftfmeta_golden_helpers as fg

    def _boom(self, *_args, **_kwargs):
        raise RuntimeError("injected preprocessing failure")

    fg.prepare_env(monkeypatch, tmp_path, FFACT_USE_CGSA="0")
    monkeypatch.setattr(FeatureFactory, "_layer6_5_pre_ic", _boom)
    root, _factory, result = fg.generate(tmp_path, fg.fast_payload(["1h"], **fg.HEALTHY))
    meta = fg.meta_json(root, "1h")
    for source in (meta, result.metadata):
        assert "L6.5:preprocessing_failed" in source["failure_reasons"]
        assert source["quality_status"] == "partial"
    assert meta["failure_reasons"] == result.metadata["failure_reasons"]


def test_boundary_15_degradation_in_manifest_none_threshold_matches_old_verdict() -> None:
    """Task 2.3 邊界①：門檻 None 由 factory 政策層解析為實值後，純函式判定與改前 factory 事後判定相同（同輸入比對）。"""
    factory = create_feature_factory(validate_continuity=False)
    config = factory._resolve_config({})
    resolved_nan = factory._default_max_nan_ratio("BTCUSDT", "12h")
    for nan_ratio, inf_ratio in ((0.001, 0.0), (0.5, 0.0), (0.0, 0.01), (0.5, 0.01)):
        old = dict(_complete_meta())
        old["run_status"] = "complete"
        factory._apply_runtime_quality_gate(old, config, "BTCUSDT", "12h", nan_ratio=nan_ratio, inf_ratio=inf_ratio)
        new = apply_quality_degradation(
            {**_complete_meta(), "run_status": "complete"}, inf_ratio=inf_ratio, nan_ratio=nan_ratio,
            max_inf_ratio=0.0, max_nan_ratio=resolved_nan, preprocessing_applied=None,
        )
        for key in ("quality_status", "run_status", "failure_reasons", "quality_thresholds"):
            assert new.get(key) == old.get(key), (nan_ratio, inf_ratio, key)


@pytest.mark.requires_kline
def test_mutation_degradation_in_manifest_writer_skips_gate_is_caught(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """§V mutant ⑤：writer 不做降級（恢復事後只改 metadata）⇒ manifest 仍 complete ⇒ 驗收必紅。"""
    monkeypatch.setattr(fs_module, "apply_quality_degradation", lambda meta, **_kwargs: dict(meta))
    with pytest.raises(AssertionError):
        test_degradation_in_manifest_cgsa_nan_threshold(monkeypatch, tmp_path)


def test_mutation_degradation_skipping_nan_gate_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：NaN 門檻判定被略過 ⇒ 純函式驗收必紅。"""
    real = fs_module.apply_quality_degradation

    def _mutant(meta, **kwargs):
        kwargs["nan_ratio"] = 0.0
        return real(meta, **kwargs)

    monkeypatch.setattr(sys.modules[__name__], "apply_quality_degradation", _mutant)
    with pytest.raises(AssertionError):
        test_degradation_pure_nan_threshold()
