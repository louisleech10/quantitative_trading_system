"""L7 死特徵清理。

僅丟「真的無資訊」的欄位（常數 + 樣本不足），**絕不**依 NaN ratio。

詳見 docs/NAN_REDUCTION_STRATEGY.md §5.3。

判定條件（OR）：
    1. nunique(dropna=True) < 2          → 常數欄（含整欄 NaN 與整欄同值）
    2. count of non-NaN < min_valid_samples → 樣本不足（XGBoost 與 CV 都無法學）

安全 invariant（見 PLAN §2.6）：
    I-1 Per-column 粒度：回傳 frozenset[str]，絕非 group_id
    I-2 必須讀過實際資料才能判定 dead；空 df 直接回傳空 set
    I-3 Output ⊆ Input：drop_dead_columns 不新增、不重排欄位
    I-4 disable 時等同 no-op：enabled=False → 回傳空 dead_set
    I-5 範圍限縮 frame path（不處理 CGSA-streamed L3）
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class DeadFeatureDiagnostic:
    """死特徵診斷統計。"""
    constant_cols: tuple[str, ...] = field(default_factory=tuple)
    """nunique<2 的欄位（含整欄 NaN 與整欄同值）"""

    sparse_cols: tuple[str, ...] = field(default_factory=tuple)
    """valid_count<min_valid_samples 的欄位"""

    @property
    def total_dropped(self) -> int:
        """總共會 drop 的欄位數（兩集合可能重疊，回傳 union size）。"""
        return len(set(self.constant_cols) | set(self.sparse_cols))


def find_dead_columns(
    df: pd.DataFrame,
    min_valid_samples: int = 100,
    enabled: bool = True,
) -> tuple[frozenset[str], DeadFeatureDiagnostic]:
    """掃描 df 各欄，回傳 (dead_set, diagnostic)。純函式。

    判定條件（OR）：
        - nunique(dropna=True) < 2  → constant_cols
        - count of non-NaN < min_valid_samples → sparse_cols

    Invariants：
        I-2: 必須讀過實際資料才能判定 dead
            - df is None 或 empty → 回傳空集合
            - 無 columns → 回傳空集合
        I-4: enabled=False → 直接回傳空集合
        I-3: 回傳 dead_set 一定是 df.columns 的子集

    向量化實作（`df.nunique()` + `df.notna().sum()`），避免 per-column Python loop。

    Args:
        df: 待掃描的 DataFrame
        min_valid_samples: 有效樣本下限（含），低於此值的欄位列入 sparse_cols
        enabled: 是否啟用；False 等同 no-op

    Returns:
        (dead_set, diagnostic) — dead_set 為 frozenset[str]
    """
    if not enabled:
        return frozenset(), DeadFeatureDiagnostic()
    if df is None or df.empty or len(df.columns) == 0:
        return frozenset(), DeadFeatureDiagnostic()

    # 向量化：一次掃完所有欄位
    nunique_per_col = df.nunique(dropna=True)
    valid_count_per_col = df.notna().sum()

    constant_mask = nunique_per_col < 2
    sparse_mask = valid_count_per_col < min_valid_samples

    constant_cols = tuple(str(c) for c in nunique_per_col.index[constant_mask])
    sparse_cols = tuple(str(c) for c in valid_count_per_col.index[sparse_mask])

    dead_set = frozenset(constant_cols) | frozenset(sparse_cols)
    diagnostic = DeadFeatureDiagnostic(
        constant_cols=constant_cols,
        sparse_cols=sparse_cols,
    )
    return dead_set, diagnostic


def dead_column_mask(
    array: np.ndarray,
    min_valid_samples: int = 100,
) -> np.ndarray:
    """numpy-level dead 判定（CGSA streaming write 用，與 find_dead_columns 標準一致）。

    判定條件（OR）：
        - valid_count < min_valid_samples  → dead（樣本不足）
        - 全 NaN（valid_count == 0）         → dead（含於上條，明確標示）
        - 非全 NaN 但 nanmin == nanmax       → dead（常數欄，等價 nunique<2）

    Args:
        array: shape (rows, cols) 的數值陣列
        min_valid_samples: 有效樣本下限（含）；低於此值列為 dead

    Returns:
        shape (cols,) 的 bool mask；True = dead（應丟）

    Invariants（見 PLAN §2.6 / CGSA plan）：
        I-2: 對實際 array 計算，不依賴快取統計
        I-3: 與 find_dead_columns（DataFrame 版）標準一致
        空 array / 0 欄 → 回傳空 mask；不修改 input
    """
    if array.ndim != 2 or array.shape[1] == 0:
        n_cols = array.shape[1] if array.ndim == 2 else 0
        return np.zeros(n_cols, dtype=bool)

    finite_mask = ~np.isnan(array)
    valid_count = finite_mask.sum(axis=0)
    sparse = valid_count < min_valid_samples
    all_nan = valid_count == 0

    # 常數判定：對非全 NaN 欄，nanmin == nanmax（all-NaN 欄的 nanmin/max 為 NaN，
    # NaN == NaN 為 False，故用 all_nan 另行涵蓋）
    # 抑制 all-NaN slice 的 RuntimeWarning（全 dead group 在生產會頻繁觸發）
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        col_min = np.nanmin(array, axis=0)
        col_max = np.nanmax(array, axis=0)
    constant = (~all_nan) & (col_min == col_max)

    return sparse | constant | all_nan


def drop_dead_columns(
    df: pd.DataFrame,
    dead_set: Iterable[str],
) -> pd.DataFrame:
    """從 df 移除 dead_set 中的欄位。

    Invariants：
        I-3: 回傳 df 的欄位 ⊆ 輸入 df 的欄位；不新增、不重排
        idempotent；dead_set 含不存在欄位 → 安全忽略（不報錯）

    Args:
        df: 待清理的 DataFrame
        dead_set: 欄位名稱集合（任何 Iterable[str] 都接受）

    Returns:
        新 DataFrame，欄位順序保持 input 的相對順序
    """
    if df is None or df.empty or len(df.columns) == 0:
        return df
    dead_frozen = frozenset(str(c) for c in dead_set)
    if not dead_frozen:
        return df
    cols_to_drop = [c for c in df.columns if str(c) in dead_frozen]
    if not cols_to_drop:
        return df
    return df.drop(columns=cols_to_drop)
