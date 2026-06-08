"""Context-aware d_star cache for Layer 6.5 fractional differencing."""

from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)

CACHE_VERSION = "v3"
ADF_ENGINE_VERSION = "statsmodels-v1"
STRONG_FINGERPRINT = "strong"
WEAK_FINGERPRINT = "weak_fingerprint"
MAX_CACHE_ENTRIES = 200_000
_GC_TRIM_FRACTION = 0.10


@dataclass(frozen=True)
class PreprocessingContext:
    """Run context used to isolate L6.5 preprocessing cache artifacts."""

    symbol: str = "unknown"
    timeframe: str = "unknown"
    config_hash: str = ""
    data_fingerprint: str = ""
    feature_schema_hash: str = ""
    time_range: Optional[Tuple[int, int]] = None
    row_count: int = 0
    source_data_version: str = ""
    data_fingerprint_status: str = STRONG_FINGERPRINT


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        number = float(value)
        if np.isnan(number) or np.isinf(number):
            return None
        return number
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return str(value)


def stable_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=_json_default,
    )


def _sha256_prefix(payload: Any, length: int = 32) -> str:
    digest = hashlib.sha256(stable_json(payload).encode("utf-8")).hexdigest()
    return digest[:length]


def compute_feature_schema_hash(columns: Iterable[str]) -> str:
    """Return a deterministic hash for the feature schema."""

    return _sha256_prefix([str(column) for column in columns], length=32)


def _metadata_complete(metadata: Dict[str, Any]) -> bool:
    required = (
        "symbol",
        "timeframe",
        "start_ts",
        "end_ts",
        "row_count",
        "source_data_version",
        "schema_hash",
        "last_updated",
    )
    return all(metadata.get(key) not in (None, "") for key in required)


def _row_sample_positions(row_count: int) -> List[int]:
    if row_count <= 0:
        return []
    fractions = (0.0, 0.25, 0.5, 0.75, 1.0)
    return sorted({min(row_count - 1, int(round(fraction * (row_count - 1)))) for fraction in fractions})


def _frame_value_digest(frame: pd.DataFrame) -> str:
    if frame.empty:
        return ""
    row_step = max(1, len(frame) // 1024)
    sample = frame.sort_index().iloc[::row_step].head(1024)
    hashed = pd.util.hash_pandas_object(sample, index=True).to_numpy(dtype=np.uint64, copy=False)
    return hashlib.sha256(np.ascontiguousarray(hashed).view(np.uint8)).hexdigest()[:32]


def _frame_sample_values(frame: pd.DataFrame) -> List[List[Any]]:
    positions = _row_sample_positions(len(frame))
    samples: List[List[Any]] = []
    for position in positions:
        row = frame.iloc[position]
        samples.append([_json_default(value) for value in row.tolist()])
    return samples


def _has_strong_index(frame: pd.DataFrame) -> bool:
    if frame.empty:
        return False
    index = frame.index
    if isinstance(index, pd.RangeIndex):
        return False
    first = index[0]
    last = index[-1]
    return first is not None and last is not None and str(first) != "" and str(last) != ""


def compute_data_fingerprint(
    frame: Optional[pd.DataFrame],
    hdf5_meta: Optional[Dict[str, Any]] = None,
) -> Tuple[str, bool]:
    """Compute a deterministic data fingerprint and whether it is weak."""

    metadata = hdf5_meta or {}
    if _metadata_complete(metadata):
        return _sha256_prefix(metadata, length=32), False

    if frame is None or not isinstance(frame, pd.DataFrame):
        return _sha256_prefix({"frame": "missing"}, length=32), True

    dtype_map = {str(column): str(dtype) for column, dtype in frame.dtypes.items()}
    nan_summary = {
        str(column): int(count)
        for column, count in frame.isna().sum(axis=0).items()
    }
    first_idx = "" if frame.empty else str(frame.index[0])
    last_idx = "" if frame.empty else str(frame.index[-1])
    summary = {
        "dtype": dtype_map,
        "shape": [int(frame.shape[0]), int(frame.shape[1])],
        "row_count": int(len(frame)),
        "col_count": int(len(frame.columns)),
        "nan_summary": nan_summary,
        "first_idx": first_idx,
        "last_idx": last_idx,
        "value_samples": _frame_sample_values(frame),
        "deterministic_sample_hash": _frame_value_digest(frame),
    }
    weak = not _has_strong_index(frame)
    return _sha256_prefix(summary, length=32), weak


def _safe_cache_token(value: str) -> str:
    token = str(value or "unknown")
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", token)


def _float_equal(left: Any, right: Any) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    try:
        return abs(float(left) - float(right)) <= 1e-12
    except (TypeError, ValueError):
        return False


def _int_equal(left: Any, right: Any) -> bool:
    try:
        return int(left) == int(right)
    except (TypeError, ValueError):
        return False


def _compute_fracdiff_hash(
    adf_threshold: Optional[float],
    precision: Optional[float],
    max_lag: Optional[int],
    weight_threshold: Optional[float],
    sample_size: Optional[int],
    nan_policy: str,
    adf_engine_version: str,
    causal_preprocessing: bool = True,
    calibration_bars: int = 0,
) -> str:
    """Deterministic MD5 of only the fracdiff algorithm parameters."""
    payload = {
        "adf_threshold": None if adf_threshold is None else round(float(adf_threshold), 15),
        "precision": None if precision is None else round(float(precision), 15),
        "max_lag": None if max_lag is None else int(max_lag),
        "weight_threshold": None if weight_threshold is None else round(float(weight_threshold), 15),
        "sample_size": None if sample_size is None else int(sample_size),
        "nan_policy": nan_policy,
        "adf_engine_version": adf_engine_version,
        "causal_preprocessing": bool(causal_preprocessing),
        "calibration_bars": int(calibration_bars),
    }
    return hashlib.md5(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _col_value_fingerprint(values: np.ndarray) -> str:
    """Fast per-column value fingerprint using strided 64-sample SHA-256 (µs-level)."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    n = len(arr)
    if n == 0:
        return "empty"
    step = max(1, n // 64)
    sample = arr[::step][:64]
    return hashlib.sha256(np.ascontiguousarray(sample).view(np.uint8)).hexdigest()[:16]


def _strong_col_value_fingerprint(values: np.ndarray) -> str:
    """Exact per-column value fingerprint for safe cross-column d-star aliasing."""
    arr = np.asarray(values, dtype=np.float64).ravel()
    n = len(arr)
    if n == 0:
        return "empty"
    canonical = np.ascontiguousarray(arr.copy())
    nan_mask = np.isnan(canonical)
    if nan_mask.any():
        canonical[nan_mask] = np.nan
    payload = np.ascontiguousarray(canonical.astype("<f8", copy=False)).view(np.uint8)
    digest = hashlib.sha256()
    digest.update(int(n).to_bytes(8, byteorder="little", signed=False))
    digest.update(payload)
    return digest.hexdigest()[:32]


class DStarCache:
    """Disk-backed d_star cache isolated by (symbol, timeframe, fracdiff_params).

    v3 changes vs v2:
    - Cache file key uses fracdiff-params hash (not config_hash), so adding new
      indicators or changing non-fracdiff UI settings does not invalidate the file.
    - Each per-column entry is validated by its own value fingerprint (value_fp)
      rather than a whole-file data fingerprint, enabling partial hits after
      kline updates that only affect some columns.
    - GC trims oldest _GC_TRIM_FRACTION of entries when file exceeds MAX_CACHE_ENTRIES.
    """

    def __init__(
        self,
        context: PreprocessingContext,
        cache_dir: Path,
        *,
        adf_threshold: Optional[float] = None,
        precision: Optional[float] = None,
        max_lag: Optional[int] = None,
        weight_threshold: Optional[float] = None,
        sample_size: Optional[int] = None,
        nan_policy: str = "dropna",
        adf_engine_version: str = ADF_ENGINE_VERSION,
        causal_preprocessing: bool = True,
        calibration_bars: int = 0,
    ) -> None:
        self._ctx = context
        self._dir = cache_dir
        self._metadata = {
            "adf_threshold": adf_threshold,
            "precision": precision,
            "max_lag": max_lag,
            "weight_threshold": weight_threshold,
            "sample_size": sample_size,
            "nan_policy": nan_policy,
            "adf_engine_version": adf_engine_version,
            "causal_preprocessing": bool(causal_preprocessing),
            "calibration_bars": int(calibration_bars),
        }
        self._fracdiff_hash = _compute_fracdiff_hash(
            adf_threshold, precision, max_lag, weight_threshold,
            sample_size, nan_policy, adf_engine_version,
            causal_preprocessing=causal_preprocessing,
            calibration_bars=calibration_bars,
        )
        self._path = self._build_path(cache_dir, context, self._fracdiff_hash)
        self._dirty = False
        self._hits = 0
        self._misses = 0
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._value_aliases: Dict[str, Dict[str, Any]] = {}

        if not self.is_enabled:
            logger.warning(
                "[d_star_cache] disabled: symbol=%s tf=%s reason=missing_context",
                context.symbol,
                context.timeframe,
            )
            return

        self._dir.mkdir(parents=True, exist_ok=True)
        self._entries = self._load_or_init()

    @staticmethod
    def _build_path(cache_dir: Path, context: PreprocessingContext, fracdiff_hash: str) -> Path:
        symbol = _safe_cache_token(context.symbol)
        timeframe = _safe_cache_token(context.timeframe)
        fhash = _safe_cache_token(fracdiff_hash[:12] or "nohash")
        return cache_dir / f"d_star_{symbol}_{timeframe}_{fhash}.json"

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_enabled(self) -> bool:
        return (
            self._ctx.symbol not in {"", "unknown"}
            and self._ctx.timeframe not in {"", "unknown"}
        )

    def _load_or_init(self) -> Dict[str, Dict[str, Any]]:
        if not self._path.exists():
            return {}

        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("[d_star_cache] failed to load cache=%s: %s", self._path, exc)
            return {}

        if not isinstance(payload, dict):
            logger.warning("[d_star_cache] invalid payload type cache=%s", self._path)
            return {}

        if not self._payload_matches(payload):
            return {}

        entries = payload.get("entries", {})
        if not isinstance(entries, dict):
            logger.warning("[d_star_cache] invalid entries cache=%s", self._path)
            return {}
        loaded_entries = {
            str(column): dict(entry)
            for column, entry in entries.items()
            if isinstance(entry, dict)
        }
        aliases = payload.get("value_aliases", {})
        if isinstance(aliases, dict):
            self._value_aliases = {
                str(value_fp): dict(alias)
                for value_fp, alias in aliases.items()
                if isinstance(alias, dict)
            }

        # Older v3 payloads do not have value_aliases. Rebuild aliases from
        # entries that already carry exact fingerprints; legacy weak-only
        # entries remain readable by direct column lookups.
        for column, entry in loaded_entries.items():
            strong_fp = entry.get("strong_value_fp")
            raw_value = entry.get("d_star")
            if strong_fp and raw_value is not None and strong_fp not in self._value_aliases:
                self._value_aliases[str(strong_fp)] = {
                    "d_star": raw_value,
                    "source_column": column,
                    "computed_at": entry.get("computed_at"),
                }
        return loaded_entries

    def _payload_matches(self, payload: Dict[str, Any]) -> bool:
        if payload.get("cache_version") != CACHE_VERSION:
            logger.info("[d_star_cache] cache_version mismatch, rebuild: %s", self._path)
            return False

        expected = self._base_payload_fields()

        if payload.get("fracdiff_hash") != expected["fracdiff_hash"]:
            logger.info("[d_star_cache] fracdiff_hash mismatch, rebuild: %s", self._path)
            return False

        exact_fields = (
            "symbol",
            "timeframe",
            "source_data_version",
            "nan_policy",
            "adf_engine_version",
            "causal_preprocessing",
        )
        for field_name in exact_fields:
            if payload.get(field_name) != expected.get(field_name):
                logger.warning(
                    "[d_star_cache] stale cache field=%s path=%s",
                    field_name,
                    self._path,
                )
                return False


        if int(payload.get("row_count", -1)) != int(expected.get("row_count", 0)):
            logger.warning("[d_star_cache] stale cache field=row_count path=%s", self._path)
            return False

        if payload.get("time_range", []) != expected.get("time_range", []):
            logger.warning("[d_star_cache] stale cache field=time_range path=%s", self._path)
            return False

        numeric_fields = ("adf_threshold", "precision", "weight_threshold")
        for field_name in numeric_fields:
            if not _float_equal(payload.get(field_name), expected.get(field_name)):
                logger.info(
                    "[d_star_cache] cache metadata mismatch field=%s path=%s",
                    field_name,
                    self._path,
                )
                return False

        integer_fields = ("max_lag", "sample_size", "calibration_bars")
        for field_name in integer_fields:
            if not _int_equal(payload.get(field_name), expected.get(field_name)):
                logger.info(
                    "[d_star_cache] cache metadata mismatch field=%s path=%s",
                    field_name,
                    self._path,
                )
                return False

        return True

    def _base_payload_fields(self) -> Dict[str, Any]:
        time_range = []
        if self._ctx.time_range is not None:
            time_range = [int(self._ctx.time_range[0]), int(self._ctx.time_range[1])]

        return {
            "cache_version": CACHE_VERSION,
            "symbol": self._ctx.symbol,
            "timeframe": self._ctx.timeframe,
            "fracdiff_hash": self._fracdiff_hash,
            "adf_threshold": self._metadata["adf_threshold"],
            "precision": self._metadata["precision"],
            "max_lag": self._metadata["max_lag"],
            "weight_threshold": self._metadata["weight_threshold"],
            "adf_engine_version": self._metadata["adf_engine_version"],
            "causal_preprocessing": self._metadata["causal_preprocessing"],
            "calibration_bars": self._metadata["calibration_bars"],
            "time_range": time_range,
            "row_count": int(self._ctx.row_count),
            "sample_size": self._metadata["sample_size"],
            "nan_policy": self._metadata["nan_policy"],
            "source_data_version": self._ctx.source_data_version,
        }

    def get(self, column: str, col_values: Optional[np.ndarray] = None) -> Optional[float]:
        if not self.is_enabled:
            return None

        entry = self._entries.get(str(column))

        if col_values is not None:
            # Per-column value fingerprint (v3 path): tolerates config/schema changes
            return self.get_by_value_fingerprint(
                column,
                weak_fp=_col_value_fingerprint(col_values),
                strong_fp=_strong_col_value_fingerprint(col_values),
            )

        if not entry:
            self._misses += 1
            return None

        if col_values is None:
            # Backward-compat path: whole-file data fingerprint check
            if entry.get("input_fingerprint") != self._ctx.data_fingerprint:
                self._misses += 1
                return None

        return self._entry_value(entry)

    def get_by_value_fingerprint(
        self,
        column: str,
        *,
        weak_fp: str,
        strong_fp: str,
    ) -> Optional[float]:
        """Return a d-star hit using precomputed value fingerprints."""
        if not self.is_enabled:
            return None

        entry = self._entries.get(str(column))
        if entry and (
            entry.get("strong_value_fp") == strong_fp
            or (
                entry.get("strong_value_fp") is None
                and entry.get("value_fp") == weak_fp
            )
        ):
            return self._entry_value(entry)

        alias = self._value_aliases.get(strong_fp)
        if alias:
            return self._entry_value(alias)

        self._misses += 1
        return None

    def _entry_value(self, entry: Dict[str, Any]) -> Optional[float]:
        raw_value = entry.get("d_star")
        if raw_value is None:
            self._misses += 1
            return None
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, column: str, d_star: float, col_values: Optional[np.ndarray] = None) -> None:
        if not self.is_enabled:
            return
        value = float(d_star)
        if not np.isfinite(value):
            return
        entry: Dict[str, Any] = {
            "d_star": value,
            "computed_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
        if col_values is not None:
            entry["value_fp"] = _col_value_fingerprint(col_values)
            strong_fp = _strong_col_value_fingerprint(col_values)
            entry["strong_value_fp"] = strong_fp
            self._value_aliases[strong_fp] = {
                "d_star": value,
                "source_column": str(column),
                "computed_at": entry["computed_at"],
            }
        else:
            entry["input_fingerprint"] = self._ctx.data_fingerprint
        self._entries[str(column)] = entry
        self._dirty = True

    def _maybe_gc(self) -> None:
        """Trim oldest entries when the cache exceeds MAX_CACHE_ENTRIES."""
        if len(self._entries) <= MAX_CACHE_ENTRIES:
            return
        trim_count = max(1, int(len(self._entries) * _GC_TRIM_FRACTION))
        sorted_keys = sorted(
            self._entries,
            key=lambda k: self._entries[k].get("computed_at", ""),
        )
        for key in sorted_keys[:trim_count]:
            del self._entries[key]
        remaining_strong = {
            str(entry.get("strong_value_fp"))
            for entry in self._entries.values()
            if entry.get("strong_value_fp")
        }
        self._value_aliases = {
            key: value
            for key, value in self._value_aliases.items()
            if key in remaining_strong
        }
        logger.info(
            "[d_star_cache] GC: removed %d oldest entries, remaining=%d path=%s",
            trim_count,
            len(self._entries),
            self._path,
        )

    def flush_atomic(self) -> None:
        if not self.is_enabled or not self._dirty:
            return
        self._maybe_gc()
        payload = self._base_payload_fields()
        payload["entries"] = self._entries
        payload["value_aliases"] = self._value_aliases

        tmp_path = self._path.with_name(
            f".{self._path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
        )
        try:
            tmp_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp_path, self._path)
            self._dirty = False
        except Exception as exc:
            logger.warning("[d_star_cache] atomic write failed path=%s: %s", self._path, exc)
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    def stats(self) -> Tuple[int, int]:
        return self._hits, self._misses
