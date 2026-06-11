"""Fail-open consumer gate helpers (IC / training / browse / cache)."""

from __future__ import annotations

from typing import Dict, Iterable, Literal, Mapping, Optional, Sequence

from momentum.FeatureEngineering.feature_storage import (
    COMPLETENESS_FIELD_NAMES,
    resolve_run_status,
)

ConsumerPolicy = Literal["strict", "browse"]


class TrainingReadError(RuntimeError):
    """Raised when training cannot safely consume feature artifacts."""


def effective_run_status(manifest: Optional[Mapping[str, object]] = None) -> str:
    """Resolve run_status from manifest, falling back to quality_status / unknown."""
    if not manifest:
        return "unknown"
    explicit = manifest.get("run_status") or manifest.get("quality_status")
    if explicit is not None:
        resolved = str(explicit)
        if resolved:
            return resolved
    return resolve_run_status(dict(manifest))


def metadata_has_completeness_evidence(metadata: Mapping[str, object]) -> bool:
    """Legacy HDF5 metadata without completeness fields must not count as complete."""
    return any(
        metadata.get(field) not in (None, "", [], {})
        for field in COMPLETENESS_FIELD_NAMES
    )


def effective_run_status_from_metadata(metadata: Optional[Mapping[str, object]]) -> str:
    """Resolve run_status from factory HDF5 metadata payload."""
    if not metadata:
        return "unknown"
    for key in ("run_status", "quality_status"):
        value = metadata.get(key)
        if value is not None and str(value):
            status = str(value)
            if status == "complete" and not metadata_has_completeness_evidence(metadata):
                return "unknown"
            return status
    return "unknown"


def is_source_run_status_reusable(
    run_status: Optional[str],
    *,
    allow_partial: bool = False,
) -> bool:
    """IC/training cache reuse gate: missing status is unknown and must fail closed."""
    if not run_status or run_status == "unknown":
        return False
    if run_status == "complete":
        return True
    return bool(allow_partial and run_status == "partial")


def is_run_status_cacheable(run_status: str) -> bool:
    """Only complete artifacts may hit factory / CGSA resume cache."""
    return run_status == "complete"


def assert_consumer_run_status(
    manifest: Mapping[str, object],
    *,
    consumer: ConsumerPolicy,
    allow_partial: bool = False,
    error_type: type[RuntimeError] = TrainingReadError,
) -> str:
    """Enforce consumer-specific run_status policy; browse never raises."""
    run_status = effective_run_status(manifest)
    if consumer == "browse":
        return run_status
    if run_status == "complete":
        return run_status
    if allow_partial and run_status == "partial":
        return run_status
    raise error_type(
        f"run_status={run_status!r} is not consumable for strict consumer "
        f"(allow_partial={allow_partial})"
    )


def assert_required_columns_present(
    frames: Mapping[str, object],
    required_columns: Sequence[str],
    *,
    error_type: type[RuntimeError] = TrainingReadError,
) -> None:
    """交集前驗證：任一 symbol 缺欄即拒絕，不得靜默縮小交集掩蓋。"""
    missing_by_symbol: Dict[str, list[str]] = {}
    for symbol, frame in frames.items():
        columns = getattr(frame, "columns", None)
        if columns is None:
            missing_by_symbol[str(symbol)] = list(required_columns)
            continue
        missing = [name for name in required_columns if name not in columns]
        if missing:
            missing_by_symbol[str(symbol)] = missing
    if missing_by_symbol:
        raise error_type(
            "required feature columns missing before intersection: "
            + ", ".join(f"{sym}={cols}" for sym, cols in missing_by_symbol.items())
        )


def intersect_columns_without_masking(
    column_sets: Iterable[Sequence[str]],
    *,
    error_type: type[RuntimeError] = TrainingReadError,
) -> list[str]:
    """Compute column intersection; empty intersection is an error (no silent mask)."""
    sets = [set(columns) for columns in column_sets]
    if not sets:
        return []
    shared = set.intersection(*sets)
    if not shared:
        raise error_type("multi-symbol intersection is empty; refusing to mask missing columns")
    return sorted(shared)
