"""ICFIRSTALIGN 乙之具名錯誤（docs/ICFIRSTALIGN_SPEC.md v17；契約 tests/_golden/icfirstalign/contract.json 之 errors）。

跨域共用（momentum.Analysis 與 momentum.FeatureEngineering 皆拋／捕），故置於 momentum.core。
"""

from __future__ import annotations


class RowIndexArtifactMissingError(ValueError):
    """成品之時間軸 sidecar 缺（Task 1.1 邊界①、Task 1.2 邊界②、Task 1.3：processed 讀回不得退回根軸）。"""


class RowIndexLengthMismatchError(ValueError):
    """時間軸 sidecar 列數與資料列數不符（Task 1.1、Task 1.3 邊界②）。"""


class ICCacheRawUnavailableError(RuntimeError):
    """IC cache 計算身分不符而 raw 成品不存在，無法重算（Task 1.4）。"""


class CloseCarrierInvalidError(ValueError):
    """close carrier 對齊後全 NaN 或長度 0（Task 3.1）。"""


class L3PersistConflictError(RuntimeError):
    """L3 串流分支同時收到 callback 欄與非空回傳表（Task 4.0 邊界②：不得雙寫）。"""


__all__ = [
    "RowIndexArtifactMissingError",
    "RowIndexLengthMismatchError",
    "ICCacheRawUnavailableError",
    "CloseCarrierInvalidError",
    "L3PersistConflictError",
]
