"""NaN 品質統計工具。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit


@njit(cache=True)
def _chunk_nan_state(mask: np.ndarray) -> tuple[int, int, int]:
    """回傳 NaN 數、首個 valid 位置、尾端 NaN run；掃描期不配置陣列。"""
    nan_count = 0
    first_valid = -1
    trailing_nan = 0
    for index in range(mask.size):
        if mask[index]:
            nan_count += 1
            trailing_nan += 1
        else:
            if first_valid < 0:
                first_valid = index
            trailing_nan = 0
    return nan_count, first_valid, trailing_nan


def abnormal_nan_count(values: np.ndarray) -> int:
    """計算各欄首尾有效值之間的 NaN；全 NaN 欄全部計入。"""
    array = np.asarray(values)
    if array.ndim != 2 or array.size == 0:
        return 0
    nan_mask = np.isnan(array)
    valid_mask = ~nan_mask
    has_valid = valid_mask.any(axis=0)
    total_nan = nan_mask.sum(axis=0, dtype=np.int64)
    first_valid = np.argmax(valid_mask, axis=0)
    last_valid = array.shape[0] - 1 - np.argmax(valid_mask[::-1], axis=0)
    leading = np.where(has_valid, first_valid, 0)
    trailing = np.where(has_valid, array.shape[0] - 1 - last_valid, 0)
    abnormal = np.where(has_valid, total_nan - leading - trailing, total_nan)
    return int(np.maximum(abnormal, 0).sum())


@dataclass
class ColumnNanAccumulator:
    """以 O(1) 狀態跨 chunk 累計單欄異常 NaN。"""

    total: int = 0
    nan_total: int = 0
    leading_nan: int = 0
    trailing_nan_run: int = 0
    seen_valid: bool = False

    def update(self, nan_mask_chunk: np.ndarray) -> None:
        """吸收單欄一維 NaN mask，保留跨 chunk 的首尾狀態。"""
        mask = np.asarray(nan_mask_chunk, dtype=bool)
        if mask.ndim != 1:
            raise ValueError(f"nan_mask_chunk must be 1D, got shape {mask.shape}")
        chunk_size = int(mask.size)
        if chunk_size == 0:
            return
        chunk_nan, first_valid, trailing_nan = _chunk_nan_state(mask)
        self.total += chunk_size
        self.nan_total += chunk_nan
        if first_valid < 0:
            if self.seen_valid:
                self.trailing_nan_run += chunk_size
            else:
                self.leading_nan += chunk_size
            return

        if not self.seen_valid:
            self.leading_nan += first_valid
        self.seen_valid = True
        self.trailing_nan_run = trailing_nan

    def abnormal(self) -> int:
        """回傳排除合法首尾 warmup 後的 NaN 數。"""
        if not self.seen_valid:
            return self.nan_total
        return max(0, self.nan_total - self.leading_nan - self.trailing_nan_run)
