from __future__ import annotations

import hashlib
import math
import struct
import threading
import time
from dataclasses import asdict
from pathlib import Path
from typing import Callable

import psutil
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import pytest

from momentum.Analysis import ic_artifact_writer
from momentum.Analysis.ic_artifact_writer import build_ic_artifact_rows, read, write
from momentum.core.contracts import EvaluationStatus, ICArtifactSchema, ICResult
from momentum.factories import create_ic_artifact_writer


def _ic_result(
    feature_name: str,
    ic_mean: float,
    *,
    eval_status: EvaluationStatus = EvaluationStatus.EVALUATED,
) -> ICResult:
    return ICResult(
        feature_name=feature_name,
        ic_mean=ic_mean,
        ic_std=ic_mean / 2.0,
        icir=ic_mean * 10.0,
        p_value=0.01 + abs(ic_mean),
        ic_hit_rate=0.55 + abs(ic_mean),
        eval_status=eval_status,
    )


def _sample_results() -> list[ICResult]:
    return [
        _ic_result("feat_regular", 0.12, eval_status=EvaluationStatus.EVALUATED),
        _ic_result("feat_nan", math.nan, eval_status=EvaluationStatus.NOT_EVALUATED),
        _ic_result("feat_pos_inf", math.inf, eval_status=EvaluationStatus.SKIPPED),
        _ic_result("feat_neg_inf", -math.inf, eval_status=EvaluationStatus.UNKNOWN_LEGACY),
    ]


def _row_hash(rows: list[dict]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        for key in ic_artifact_writer.ARTIFACT_COLUMNS:
            value = row[key]
            digest.update(key.encode("utf-8"))
            digest.update(b"\0")
            if isinstance(value, float):
                digest.update(struct.pack(">d", value))
            else:
                digest.update(str(value).encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _dict_rows(rows: list[ICArtifactSchema]) -> list[dict]:
    return [asdict(row) for row in rows]


def _many_rows(count: int) -> list[ICArtifactSchema]:
    results = [
        _ic_result(
            f"feature_{index:06d}",
            float(index % 17) / 100.0,
            eval_status=EvaluationStatus.EVALUATED,
        )
        for index in range(count)
    ]
    return build_ic_artifact_rows(
        results,
        default_horizon=5,
        selection_scope_id="scope-memory",
    )


def _rss_peak_for(call: Callable[[], list[dict]]) -> tuple[list[dict], int]:
    process = psutil.Process()
    peak = process.memory_info().rss
    done = threading.Event()

    def sample() -> None:
        nonlocal peak
        while not done.is_set():
            peak = max(peak, process.memory_info().rss)
            time.sleep(0.001)

    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    try:
        result = call()
        peak = max(peak, process.memory_info().rss)
        return result, peak
    finally:
        done.set()
        sampler.join(timeout=1.0)


def test_artifact_roundtrip(tmp_path: Path) -> None:
    rows = build_ic_artifact_rows(
        _sample_results(),
        default_horizon=3,
        selection_scope_id="scope-roundtrip",
    )
    artifact_path = tmp_path / "ic_artifact.parquet"

    write(rows, artifact_path)
    loaded = read(artifact_path)
    metadata = pq.read_metadata(artifact_path)

    assert len(loaded) == len(rows)
    assert metadata.metadata[b"schema_version"] == b"1"
    assert _row_hash(loaded) == _row_hash(_dict_rows(rows))
    assert [row["eval_status"] for row in loaded] == [
        "evaluated",
        "not_evaluated",
        "skipped",
        "unknown_legacy",
    ]
    assert math.isnan(loaded[1]["ic_mean"])
    assert loaded[2]["ic_mean"] == math.inf
    assert loaded[3]["ic_mean"] == -math.inf


def test_artifact_filter_no_full_load(tmp_path: Path) -> None:
    row_count = 20_000
    target_features = [f"feature_{index:06d}" for index in range(10, 20)]
    path_small = tmp_path / "small.parquet"
    path_large = tmp_path / "large.parquet"
    write(_many_rows(row_count), path_small)
    write(_many_rows(row_count * 2), path_large)

    filters = ds.field("feature_name").isin(target_features)
    small_rows, small_peak = _rss_peak_for(
        lambda: read(path_small, filters=filters, page=5_000)
    )
    large_rows, large_peak = _rss_peak_for(
        lambda: read(path_large, filters=filters, page=5_000)
    )

    assert len(small_rows) == len(target_features)
    assert len(large_rows) == len(target_features)
    assert {row["feature_name"] for row in small_rows} == set(target_features)
    assert {row["feature_name"] for row in large_rows} == set(target_features)
    assert small_peak < 2 * 1024**3
    assert large_peak < 2 * 1024**3
    assert large_peak <= small_peak + 128 * 1024**2


def test_artifact_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    artifact_path = tmp_path / "atomic.parquet"
    rows = build_ic_artifact_rows(
        [_ic_result("feat_atomic", 0.1)],
        default_horizon=1,
        selection_scope_id="scope-atomic",
    )

    def interrupted_write(*args, **kwargs) -> None:
        Path(args[1]).write_bytes(b"partial parquet bytes")
        raise RuntimeError("simulated interruption")

    monkeypatch.setattr(ic_artifact_writer.pq, "write_table", interrupted_write)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        write(rows, artifact_path)

    assert not artifact_path.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_build_rows_single_horizon() -> None:
    writer = create_ic_artifact_writer()
    rows = build_ic_artifact_rows(
        [_ic_result("feat_horizon", 0.07)],
        default_horizon=13,
        selection_scope_id="scope-horizon",
    )
    factory_rows = writer.build_ic_artifact_rows(
        [_ic_result("feat_factory", 0.08)],
        default_horizon=21,
        selection_scope_id="scope-factory",
    )

    assert len(rows) == 1
    assert rows[0].horizon == 13
    assert rows[0].feature_name == "feat_horizon"
    assert rows[0].selection_scope_id == "scope-horizon"
    assert rows[0].schema_version == ic_artifact_writer.SCHEMA_VERSION
    assert factory_rows[0].horizon == 21
