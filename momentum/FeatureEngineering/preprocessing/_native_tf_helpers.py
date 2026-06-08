"""Helpers for native-resolution L6.5 preprocessing on compact-aligned groups.

Background
----------
Compact-aligned groups (e.g. 12h features stored at native 1696 rows when the
primary timeframe is 1h with 20352 rows) used to be expanded via ``idx_map``
*before* L6.5 preprocessing. That step-function replication caused several
quant-finance correctness issues:

* Fractional differencing's ADF-based d_star search became biased — every
  primary row inside a 12h bucket holds an identical value, which inflates
  autocorrelation and yields a different d_star than computing on native rows.
* Distribution-based transforms (rank, gaussian, winsorization, zscore)
  over-weighted plateaus relative to the true source distribution.
* Rolling windows defined in primary-timeframe units (e.g. ``window=252``)
  no longer represented the intended look-back when applied to a step series.

This module provides the building blocks for an alternative path that
computes L6.5 transforms on native source rows and forward-fills the result
to primary rows via the existing alignment ``idx_map`` afterwards.

Decoupling note: this module imports only from numpy + ``momentum.core``,
never from ``api.*`` (Rule 1).
"""

from __future__ import annotations

import copy
import os
from typing import Any, Dict, Optional, Tuple

import numpy as np

from momentum.core.constants import TIMEFRAME_SECONDS
from momentum.core.logging import get_logger


logger = get_logger(__name__)


_ROW_BLOCK = 1024  # Matches tf_aligner._searchsorted_align block size for cache-friendly copy.


# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------
def native_tf_enabled() -> bool:
    """Return True iff native-resolution L6.5 path is enabled.

    Controlled by env var ``FFACT_L65_NATIVE_TF`` (default ``1``). Set to
    ``0`` to fall back to the legacy expand-then-transform behavior.
    """
    raw = os.getenv("FFACT_L65_NATIVE_TF", "1").strip().lower()
    return raw not in ("0", "false", "off", "no", "")


# ---------------------------------------------------------------------------
# Window scaling
# ---------------------------------------------------------------------------
def scale_window_for_native(
    window: int,
    source_timeframe: str,
    primary_timeframe: str,
) -> int:
    """Convert a primary-timeframe window into the equivalent source-rows window.

    Preserves the time-equivalent look-back: a primary window of 252 1h bars
    becomes ``round(252 * 3600 / 43200) = 21`` 12h bars. Always clamped to
    >= 1 so a single source observation is at least considered.

    Raises:
        ValueError: if either timeframe is not in TIMEFRAME_SECONDS.
    """
    if window <= 0:
        return 0
    if source_timeframe == primary_timeframe:
        return int(window)
    try:
        src_sec = TIMEFRAME_SECONDS[source_timeframe]
        primary_sec = TIMEFRAME_SECONDS[primary_timeframe]
    except KeyError as exc:
        raise ValueError(
            f"Unknown timeframe in TIMEFRAME_SECONDS mapping: {exc}"
        ) from exc
    if primary_sec <= 0 or src_sec <= 0:
        raise ValueError(
            f"Invalid timeframe seconds: {src_sec}, {primary_sec}"
        )
    scaled = int(round(int(window) * primary_sec / src_sec))
    return max(1, scaled)


# ---------------------------------------------------------------------------
# Config rewriting
# ---------------------------------------------------------------------------
_WINDOW_KEYS = ("window",)
_WINDOWS_LIST_KEYS = ("windows",)
_SAMPLE_SIZE_KEYS = ("sample_size", "max_lag")


def scale_preprocessing_config_for_native(
    config: Dict[str, Any],
    source_timeframe: str,
    primary_timeframe: str,
) -> Dict[str, Any]:
    """Return a deep-copied L6.5 config with all rolling windows scaled.

    Scaled keys (when present at any nesting level inside the standard L6.5
    section dicts):

    * ``rank_transform.window`` -> primary->source rows
    * ``winsorization.window`` -> primary->source rows
    * ``adaptive_zscore.windows`` -> list of primary->source rows
    * ``adaptive_zscore.window`` (legacy)
    * top-level ``calibration_bars`` -> primary->source rows
    * ``fractional_differencing.sample_size`` -> kept (sample size is
      observation count for ADF, not a time window). NOT scaled.
    * ``fractional_differencing.max_lag`` -> kept (lag in observations).
    * ``adf_differencing.sample_size`` -> kept.

    Window-like fields below other keys are left untouched.
    """
    if source_timeframe == primary_timeframe:
        return copy.deepcopy(config)

    scaled = copy.deepcopy(config)

    def _scale_window(value: Any) -> Any:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return scale_window_for_native(value, source_timeframe, primary_timeframe)
        return value

    # rank_transform
    rank_cfg = scaled.get("rank_transform")
    if isinstance(rank_cfg, dict):
        for key in _WINDOW_KEYS:
            if key in rank_cfg:
                rank_cfg[key] = _scale_window(rank_cfg[key])

    # winsorization
    winsor_cfg = scaled.get("winsorization")
    if isinstance(winsor_cfg, dict):
        winsor_cfg["window"] = _scale_window(winsor_cfg.get("window", 252))

    # adaptive_zscore
    zscore_cfg = scaled.get("adaptive_zscore")
    if isinstance(zscore_cfg, dict):
        for key in _WINDOW_KEYS:
            if key in zscore_cfg:
                zscore_cfg[key] = _scale_window(zscore_cfg[key])
        for key in _WINDOWS_LIST_KEYS:
            if key in zscore_cfg and isinstance(zscore_cfg[key], (list, tuple)):
                zscore_cfg[key] = [_scale_window(w) for w in zscore_cfg[key]]

    scaled["calibration_bars"] = _scale_window(scaled.get("calibration_bars", 500))

    return scaled


# ---------------------------------------------------------------------------
# Native -> primary alignment (forward-fill via idx_map)
# ---------------------------------------------------------------------------
def apply_idx_map_to_array(
    native_arr: np.ndarray,
    idx_map: np.ndarray,
    primary_n_rows: int,
) -> np.ndarray:
    """Expand a native-resolution array to primary rows via idx_map.

    Equivalent to forward-filling each native value across all primary rows
    pointing at it. ``idx_map[i] == -1`` produces NaN (no source row yet).

    Args:
        native_arr: shape (source_n_rows, n_cols), dtype float32.
        idx_map: shape (primary_n_rows,), dtype int (signed). Values in
            ``[-1, source_n_rows)``.
        primary_n_rows: expected primary row count (must match
            ``idx_map.shape[0]``).

    Returns:
        np.ndarray of shape (primary_n_rows, n_cols), float32, with NaN
        rows where idx_map == -1.
    """
    native = np.asarray(native_arr, dtype=np.float32)
    if native.ndim != 2:
        raise ValueError(
            f"native_arr must be 2D, got shape={native.shape}"
        )
    idx = np.asarray(idx_map)
    if idx.ndim != 1:
        raise ValueError(f"idx_map must be 1D, got shape={idx.shape}")
    if int(idx.shape[0]) != int(primary_n_rows):
        raise ValueError(
            f"idx_map length {idx.shape[0]} != primary_n_rows {primary_n_rows}"
        )

    src_rows, n_cols = native.shape
    if src_rows > 0:
        bad = (idx >= src_rows)
        if bool(np.any(bad)):
            raise ValueError(
                f"idx_map references source row beyond native rows: "
                f"max={int(idx.max())}, source_n_rows={src_rows}"
            )

    out = np.full((int(primary_n_rows), n_cols), np.nan, dtype=np.float32)
    if n_cols == 0 or primary_n_rows == 0:
        return out

    valid = idx >= 0
    if not bool(np.any(valid)):
        return out

    # Block-copy to bound peak working set on wide arrays. Each block writes
    # at most _ROW_BLOCK x n_cols float32 = 4 KB * n_cols.
    valid_idx_int64 = idx.astype(np.int64, copy=False)
    for start in range(0, int(primary_n_rows), _ROW_BLOCK):
        end = min(start + _ROW_BLOCK, int(primary_n_rows))
        block_valid = valid[start:end]
        if not bool(np.any(block_valid)):
            continue
        block_idx = valid_idx_int64[start:end]
        # Build a destination slice; rows where block_valid is False stay NaN.
        # np.where would broadcast a NaN row; cheaper to mask-assign.
        # source rows for the valid positions:
        out_block = out[start:end]
        out_block[block_valid] = native[block_idx[block_valid]]
    return out


# ---------------------------------------------------------------------------
# Dispatch decision
# ---------------------------------------------------------------------------
_MIN_NATIVE_ROWS = 50  # Avoid tiny groups where overhead dominates.
_MIN_SCALED_WINDOW = 5  # Below this the scaled rolling window is not meaningful.


def should_use_native_path(
    *,
    is_compact_aligned: bool,
    source_timeframe: Optional[str],
    primary_timeframe: Optional[str],
    source_n_rows: int,
    scaled_config: Dict[str, Any],
    flag_enabled: Optional[bool] = None,
) -> Tuple[bool, str]:
    """Decide whether to take the native-resolution L6.5 path for one group.

    Returns ``(use_native, reason)``. ``reason`` is a short tag suitable
    for logging.

    Fallback conditions (use legacy expand-then-transform):

    * Feature flag disabled.
    * Group is not compact-aligned (no idx_map to apply).
    * source_timeframe == primary_timeframe (nothing to gain).
    * Native row count too small (< _MIN_NATIVE_ROWS).
    * All scaled rolling windows collapsed below _MIN_SCALED_WINDOW.
    """
    enabled = native_tf_enabled() if flag_enabled is None else bool(flag_enabled)
    if not enabled:
        return False, "flag_off"
    if not is_compact_aligned:
        return False, "not_compact"
    if source_timeframe is None or primary_timeframe is None:
        return False, "missing_tf"
    if source_timeframe == primary_timeframe:
        return False, "same_tf"
    if source_n_rows < _MIN_NATIVE_ROWS:
        return False, f"native_rows<{_MIN_NATIVE_ROWS}"

    # Look at scaled windows. If any enabled rolling step has a scaled
    # window < threshold, we still proceed if at least one window remains
    # meaningful — but if every enabled rolling window collapsed, fall back.
    rolling_windows: list[int] = []
    rank_cfg = scaled_config.get("rank_transform")
    if isinstance(rank_cfg, dict) and rank_cfg.get("enabled"):
        w = rank_cfg.get("window")
        if isinstance(w, int):
            rolling_windows.append(w)
    zscore_cfg = scaled_config.get("adaptive_zscore")
    if isinstance(zscore_cfg, dict) and zscore_cfg.get("enabled"):
        for key in ("window",):
            w = zscore_cfg.get(key)
            if isinstance(w, int):
                rolling_windows.append(w)
        windows = zscore_cfg.get("windows")
        if isinstance(windows, (list, tuple)):
            rolling_windows.extend(int(w) for w in windows if isinstance(w, int))

    if rolling_windows and max(rolling_windows) < _MIN_SCALED_WINDOW:
        return False, f"scaled_window<{_MIN_SCALED_WINDOW}"

    return True, "ok"


__all__ = [
    "apply_idx_map_to_array",
    "native_tf_enabled",
    "scale_preprocessing_config_for_native",
    "scale_window_for_native",
    "should_use_native_path",
]
