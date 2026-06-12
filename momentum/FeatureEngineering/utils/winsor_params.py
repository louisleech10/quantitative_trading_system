"""Winsorization rolling 參數解析。"""

from __future__ import annotations


def resolve_winsor_min_periods(window: int) -> int:
    """依 L6.5 既有公式解析 rolling min_periods。"""
    if window <= 0:
        raise ValueError(f"winsor window must be positive, got {window}")
    return min(window, max(20, window // 4))
