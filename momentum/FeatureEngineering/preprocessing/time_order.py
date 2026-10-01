"""ICPOSTLEAK Task 1.2：依列序之 rolling 轉換入口之時間序檢查（docs/ICPOSTLEAK_SPEC.md §C「時間序」）。

本模組只放純函式：不讀檔、不記 log。
"""

from __future__ import annotations

from typing import Any


def assert_strictly_increasing_time_index(index: Any, *, where: str) -> None:
    """`index` 為 `pandas.DatetimeIndex` 時須嚴格遞增（無倒序、無重複、無亂序），否則拋 `ValueError`，
    訊息含 `where`、首個違規位置（整數位置）與該處前後兩個時間戳。非 DatetimeIndex（如 RangeIndex）與長度 0／1 不檢。
    不靜默排序。"""
    raise NotImplementedError("ICPOSTLEAK Task 1.2")
