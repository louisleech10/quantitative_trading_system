"""特徵欄名之單一真相源：週期標記之加與剝、ratio-unsafe 類別判定（docs/RATIOUNSAFE_SPEC.md Task 1.1）。

純函式、無狀態。週期鍵一律取自 `TimeframeAligner._timeframe_seconds_keys()`（不寫死週期清單或正則）。
標記規則＝生產落盤之群組週期身分規則（`feature_storage` CGSA L7 寫檔）推廣至全部週期鍵：
`label_` 開頭、少於 2 段、或 `parts[1] == timeframe` ⇒ 原樣；否則插於第一段後。
加剝互逆之定義域：非 `label_`、至少 2 段、`parts[1]` 不屬週期鍵之名。
"""

from __future__ import annotations

from typing import FrozenSet, Optional

# Task 1.1：ratio-unsafe 類別之單一常數（`derived_operators`、`rolling_aggregator`、`feature_preprocessor` re-export 同一物件）
RATIO_UNSAFE_CATEGORIES: FrozenSet[str] = frozenset({"pattern"})


def timeframe_keys() -> FrozenSet[str]:
    """全部合法週期鍵（取自 `TimeframeAligner._timeframe_seconds_keys()`）。RATIOUNSAFE Task 1.1。"""
    raise NotImplementedError("RATIOUNSAFE Task 1.1")


def tag_timeframe(column: str, timeframe: str) -> str:
    """欄名加週期標記（群組週期身分規則）；`timeframe` 不屬週期鍵 ⇒ ValueError。RATIOUNSAFE Task 1.1。"""
    raise NotImplementedError("RATIOUNSAFE Task 1.1")


def strip_timeframe_tag(column: str) -> str:
    """去除第二段之週期標記（非 `label_`、至少 3 段且 `parts[1]` 屬週期鍵）；否則原樣。RATIOUNSAFE Task 1.1。"""
    raise NotImplementedError("RATIOUNSAFE Task 1.1")


def ratio_unsafe_category(column: str) -> Optional[str]:
    """共同核心：去標記後 `split("_", 2)[1]` 屬 `RATIO_UNSAFE_CATEGORIES` 則回之，否則 None。RATIOUNSAFE Task 1.1。"""
    raise NotImplementedError("RATIOUNSAFE Task 1.1")


def is_ratio_unsafe_column(column: str) -> bool:
    """＝ `ratio_unsafe_category(column) is not None`。RATIOUNSAFE Task 1.1。"""
    raise NotImplementedError("RATIOUNSAFE Task 1.1")
