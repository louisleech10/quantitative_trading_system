"""Verification tests for Feature Explorer 9-step optimization plan.

Covers:
    - Step 2 (P0-B): browse request coalescing via _coalesce_browse.
    - Step 8 (P2-A): opt-in ADF in browse_distribution.
    - Step 9 (P1-D): dq_v1 schema-metadata pack / fast-path read.
"""
from __future__ import annotations

import struct
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest

from api.services.feature_factory_service import FeatureFactoryService


def _make_service() -> FeatureFactoryService:
    service = FeatureFactoryService.__new__(FeatureFactoryService)
    service._browse_inflight = {}
    service._browse_inflight_lock = threading.Lock()
    service._active_browse_requests = 0
    service._active_browse_lock = threading.Lock()
    return service


# ---------------------------------------------------------------------------
# Step 2 — request coalescing
# ---------------------------------------------------------------------------

def test_coalesce_browse_dedup_identical_fingerprints():
    service = _make_service()
    call_counter = {"n": 0}
    barrier = threading.Barrier(5)

    def slow_compute() -> Dict[str, Any]:
        call_counter["n"] += 1
        time.sleep(0.05)
        return {"value": 42}

    results = [None] * 5

    def worker(i: int) -> None:
        barrier.wait()
        results[i] = service._coalesce_browse(("task", "browse_features"), slow_compute)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert call_counter["n"] == 1
    assert all(r == {"value": 42} for r in results)


def test_coalesce_browse_different_fingerprints_run_separately():
    service = _make_service()
    counter = {"n": 0}

    def compute() -> Dict[str, Any]:
        counter["n"] += 1
        return {"v": counter["n"]}

    a = service._coalesce_browse(("task", "a"), compute)
    b = service._coalesce_browse(("task", "b"), compute)
    assert counter["n"] == 2
    assert a != b


def test_coalesce_browse_propagates_exception_to_all_waiters():
    service = _make_service()
    barrier = threading.Barrier(3)

    def boom() -> Dict[str, Any]:
        time.sleep(0.03)
        raise RuntimeError("compute failed")

    captured: list = [None, None, None]

    def worker(i: int) -> None:
        barrier.wait()
        try:
            service._coalesce_browse(("task", "boom"), boom)
        except Exception as e:  # noqa: BLE001
            captured[i] = e

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert all(isinstance(c, RuntimeError) for c in captured)
    assert all("compute failed" in str(c) for c in captured)


def test_coalesce_browse_reentrant_skips_holder():
    """If a compute internally calls back into another browse, the inner call
    must execute directly (no deadlock) because the TLS marker is set."""
    service = _make_service()
    inner_called = {"n": 0}

    def inner() -> Dict[str, Any]:
        inner_called["n"] += 1
        return {"inner": True}

    def outer() -> Dict[str, Any]:
        return service._coalesce_browse(("task", "inner"), inner)

    res = service._coalesce_browse(("task", "outer"), outer)
    assert inner_called["n"] == 1
    assert res == {"inner": True}


# ---------------------------------------------------------------------------
# Step 8 — ADF opt-in
# ---------------------------------------------------------------------------

def test_browse_distribution_skips_adf_by_default(monkeypatch):
    """When compute_adf=False, adfuller must NOT be called and adf_pvalue
    must be None even if statsmodels is available."""
    service = _make_service()
    service._stats_cache = {}
    service._adf_cache = {}

    df = pd.DataFrame({"feature_a": np.linspace(0.0, 1.0, 100)})
    context = {"is_cgsa": False}
    monkeypatch.setattr(service, "_load_task_context", lambda _task: context)
    monkeypatch.setattr(service, "_load_task_features", lambda _task: (df, {}))

    called = {"adf": 0}

    def fake_adfuller(*_a, **_k):  # pragma: no cover - should not run
        called["adf"] += 1
        return (0.0, 0.01, 0, 0, {}, 0.0)

    monkeypatch.setattr(
        "api.services.feature_factory_service.adfuller",
        fake_adfuller,
        raising=False,
    )

    result = service._browse_distribution_impl(
        "task", "feature_a", n_bins=10, compute_adf=False,
    )
    assert called["adf"] == 0
    assert result["stats"]["adf_pvalue"] is None
    assert result["stats"]["is_stationary"] is False


# ---------------------------------------------------------------------------
# Step 9 — dq_v1 metadata pack / read roundtrip
# ---------------------------------------------------------------------------

def test_pack_dq_v1_metadata_roundtrip():
    from momentum.FeatureEngineering.feature_storage import _pack_dq_v1_metadata

    rows, cols = 20, 3
    arr = np.full((rows, cols), np.nan, dtype=np.float32)
    arr[5:18, 0] = 1.0          # col0: first_valid=5, last_valid=17, nan=7
    arr[:, 1] = 2.0              # col1: first_valid=0, last_valid=19, nan=0
    # col2: all NaN

    meta = _pack_dq_v1_metadata(arr, ["c0", "c1", "c2"])
    assert meta is not None
    blob = meta[b"dq_v1"]
    names = meta[b"dq_v1_cols"].split(b"\x00")
    assert int(meta[b"dq_v1_rows"]) == rows
    assert [n.decode() for n in names if n] == ["c0", "c1", "c2"]

    (n,) = struct.unpack_from("<I", blob, 0)
    assert n == 3
    entry = struct.calcsize("<iiI")
    fv0, lv0, nan0 = struct.unpack_from("<iiI", blob, 4)
    fv1, lv1, nan1 = struct.unpack_from("<iiI", blob, 4 + entry)
    fv2, lv2, nan2 = struct.unpack_from("<iiI", blob, 4 + 2 * entry)
    assert (fv0, lv0, nan0) == (5, 17, 7)
    assert (fv1, lv1, nan1) == (0, 19, 0)
    assert (fv2, lv2, nan2) == (rows, -1, rows)


def test_pack_dq_v1_metadata_rejects_non_float():
    from momentum.FeatureEngineering.feature_storage import _pack_dq_v1_metadata

    int_arr = np.zeros((10, 2), dtype=np.int32)
    assert _pack_dq_v1_metadata(int_arr, ["a", "b"]) is None


def test_pack_dq_v1_metadata_rejects_shape_mismatch():
    from momentum.FeatureEngineering.feature_storage import _pack_dq_v1_metadata

    arr = np.zeros((10, 3), dtype=np.float32)
    assert _pack_dq_v1_metadata(arr, ["only_one"]) is None


def test_try_load_dq_v1_roundtrip_writes_and_reads(tmp_path):
    """Write a parquet file with packed dq_v1 metadata via the storage helper,
    then verify _try_load_dq_v1 decodes the same first/last_valid/nan_count."""
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    from momentum.FeatureEngineering.feature_storage import (
        _pack_dq_v1_metadata,
        _write_parquet_with_codec,
    )

    rows, cols = 12, 2
    arr = np.full((rows, cols), np.nan, dtype=np.float32)
    arr[2:11, 0] = 0.5
    arr[:, 1] = 1.0

    table = pa.Table.from_arrays([pa.array(arr[:, i]) for i in range(cols)], names=["c0", "c1"])
    out = tmp_path / "part.parquet"
    _write_parquet_with_codec(
        table, out, float32_cols=["c0", "c1"],
        schema_metadata=_pack_dq_v1_metadata(arr, ["c0", "c1"]),
    )

    service = _make_service()
    hit, partials = service._try_load_dq_v1([out], total_rows=rows)
    assert hit is True
    assert len(partials) == 1
    col_map = {c: (n, fv, lv) for (c, n, fv, lv) in partials[0]["col_stats"]}
    assert col_map["c0"] == (3, 2, 10)
    assert col_map["c1"] == (0, 0, rows - 1)


def test_try_load_dq_v1_misses_when_metadata_absent(tmp_path):
    pa = pytest.importorskip("pyarrow")
    from momentum.FeatureEngineering.feature_storage import _write_parquet_with_codec

    arr = np.zeros((5, 1), dtype=np.float32)
    table = pa.Table.from_arrays([pa.array(arr[:, 0])], names=["c0"])
    out = tmp_path / "plain.parquet"
    _write_parquet_with_codec(table, out, float32_cols=["c0"], schema_metadata=None)

    service = _make_service()
    hit, partials = service._try_load_dq_v1([out], total_rows=5)
    assert hit is False
    assert partials == []


def test_try_load_dq_v1_misses_on_row_count_mismatch(tmp_path):
    pa = pytest.importorskip("pyarrow")
    from momentum.FeatureEngineering.feature_storage import (
        _pack_dq_v1_metadata,
        _write_parquet_with_codec,
    )

    arr = np.zeros((8, 1), dtype=np.float32)
    table = pa.Table.from_arrays([pa.array(arr[:, 0])], names=["c0"])
    out = tmp_path / "p.parquet"
    _write_parquet_with_codec(
        table, out, float32_cols=["c0"],
        schema_metadata=_pack_dq_v1_metadata(arr, ["c0"]),
    )

    service = _make_service()
    # Caller claims total_rows=99 → mismatch → safe fallback.
    hit, partials = service._try_load_dq_v1([out], total_rows=99)
    assert hit is False
