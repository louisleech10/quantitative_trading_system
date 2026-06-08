"""Per-run cache for non-stationary column classification."""

from __future__ import annotations

import hashlib
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

NonStationaryKey = Tuple[str, float, int, str, bool, int, str, str, Tuple[int, ...], int, str, str, str]


class NonStationaryCache:
    """In-memory cache scoped to a single FeaturePreprocessor instance."""

    def __init__(self) -> None:
        self._cache: Dict[NonStationaryKey, bool] = {}

    def make_key(
        self,
        column: str,
        threshold: float,
        sample_size: int,
        nan_policy: str,
        series: pd.Series,
        *,
        causal_preprocessing: bool = True,
        calibration_bars: int = 0,
    ) -> NonStationaryKey:
        numeric = pd.to_numeric(series, errors="coerce")
        values = numeric.to_numpy(dtype=np.float64, copy=False)
        contiguous_values = np.ascontiguousarray(values)
        nan_mask = np.isnan(contiguous_values)
        digest_values = np.nan_to_num(
            contiguous_values,
            nan=0.0,
            posinf=np.finfo(np.float64).max,
            neginf=np.finfo(np.float64).min,
        )

        digest = hashlib.sha1()
        digest.update(np.ascontiguousarray(digest_values).view(np.uint8))
        digest.update(np.ascontiguousarray(nan_mask).view(np.uint8))
        value_digest = digest.hexdigest()[:16]

        first_valid = series.first_valid_index()
        last_valid = series.last_valid_index()

        return (
            str(column),
            round(float(threshold), 8),
            int(sample_size),
            str(nan_policy),
            bool(causal_preprocessing),
            int(calibration_bars),
            str(series.dtype),
            tuple(int(part) for part in series.shape),
            int(nan_mask.sum()),
            "" if first_valid is None else str(first_valid),
            "" if last_valid is None else str(last_valid),
            value_digest,
        )

    def get(self, key: NonStationaryKey) -> Optional[bool]:
        return self._cache.get(key)

    def set(self, key: NonStationaryKey, is_non_stationary: bool) -> None:
        self._cache[key] = bool(is_non_stationary)
