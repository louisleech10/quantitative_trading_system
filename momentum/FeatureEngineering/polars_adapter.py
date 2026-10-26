"""Polars adapter for Feature Factory Phase 4 optimization.

Provides Polars-based implementations of L2/L6.5 operations.
Default is ON (FFACT_USE_POLARS=1); disable with FFACT_USE_POLARS=0
to fall back to pandas path.

Phase 4 status: COMPLETED & ACTIVE (default-on as of V7 baseline)

Risk mitigations (both risks resolved):
- R5: Polars null vs NaN — fully handled via ensure_nan_semantics(),
  fill_null(float('nan')) at all pandas←→polars conversion points.
  In polars 1.x (null/NaN are distinct types), map_batches output uses
  fill_nan(None) so downstream rolling ops skip missing values.
- R25: Version upgraded to polars>=1.0,<2.0 (was >=0.20,<0.21).
  Only breaking changes were rolling_rank() (removed in 1.x) and
  rolling_count() (renamed to rolling_len()). Both replaced with
  map_batches() + scipy.stats.rankdata（該 L6.5 rank 轉換已於 FFPROD Task 1.1 刪除：生產不可達）.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.preprocessing._numba_transforms import (
    _rolling_mean_std,
    rolling_quantile_2d,
)
from momentum.FeatureEngineering.utils.numeric_guards import DEFAULT_DENOM_REL_EPS

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)


def _safe_denom_expr(
    pl_df: "pl.DataFrame",
    denom_col: str,
    rel_eps: float = DEFAULT_DENOM_REL_EPS,
) -> "pl.Expr":
    """Polars 版近零分母守衛：回傳 denom 的 expr，將 exact-0 與相對近零設為 null。

    門檻 = `rel_eps × 因果尺度`（第 t 列之前固定窗之非零絕對值中位數，窗未滿 fail-closed；FFSTAT v53，
    與 pandas `safe_denominator` 同一 `causal_near_zero_mask`）。擋 TA-Lib 振盪器邊界的 ~1e-14 浮點噪音、保留真實小值。
    """
    import polars as pl

    d = pl.col(denom_col)
    if rel_eps <= 0:
        return pl.when(d == 0.0).then(None).otherwise(d)

    # FFSTAT v53：與 pandas `safe_denominator` 同一因果尺度（改前全欄中位數＝未來洩漏）
    from momentum.FeatureEngineering.utils.numeric_guards import causal_near_zero_mask

    values = pl_df.get_column(denom_col).cast(pl.Float64).to_numpy()  # Float64 之 null 轉 numpy 即 NaN
    mask = pl.Series(causal_near_zero_mask(values, rel_eps))
    return pl.when(pl.lit(mask)).then(None).otherwise(d)

# Lazy import to avoid import error when polars not installed
_polars_available: Optional[bool] = None


def _check_polars_available() -> bool:
    """Check if polars is importable (cached)."""
    global _polars_available
    if _polars_available is None:
        try:
            import polars as pl  # noqa: F401

            _polars_available = True
        except ImportError:
            _polars_available = False
            logger.warning("polars not available; Phase 4 Polars path disabled")
    return _polars_available


def polars_enabled() -> bool:
    """Check if Polars path is enabled via env var AND polars is installed.

    Default is ON ("1"). Phase 4 is completed and active as of V7 baseline.
    Use FFACT_USE_POLARS=0 to force fallback to pandas path.
    """
    from momentum.FeatureEngineering import memory_budget as _memory_budget  # ICFIRSTALIGN Task 4.2：選擇子唯一入口

    enabled = _memory_budget.selector_flag("FFACT_USE_POLARS")
    if enabled and not _check_polars_available():
        return False
    return enabled


def pandas_to_polars(df: pd.DataFrame, *, use_float64: bool = False) -> "pl.DataFrame":
    """Convert pandas DataFrame to Polars DataFrame (zero-copy where possible).

    Uses pl.from_numpy for float arrays (zero-copy), handles NaN preservation.

    Parameters
    ----------
    df : pd.DataFrame
        Input pandas DataFrame with numeric columns.
    use_float64 : bool
        If True, preserve float64 precision (for large-magnitude values like prices).
        Default False uses float32 for memory efficiency.

    Returns
    -------
    pl.DataFrame
        Polars DataFrame with same column names and shape.
    """
    import polars as pl

    dtype = np.float64 if use_float64 else np.float32
    pl_dtype = pl.Float64 if use_float64 else pl.Float32

    if df.empty:
        return pl.DataFrame(schema={col: pl_dtype for col in df.columns})

    # Convert to numpy first for zero-copy path
    arr = df.to_numpy(dtype=dtype, na_value=np.nan, copy=False)
    columns = list(df.columns)
    pl_df = pl.from_numpy(arr, schema=columns)

    # R5 mitigation: Convert NaN to null so Polars rolling/aggregation ops
    # skip missing values (matching pandas NaN behavior in rolling).
    pl_df = pl_df.with_columns([pl.col(c).fill_nan(None) for c in pl_df.columns])
    return pl_df


def polars_to_pandas(
    pl_df: "pl.DataFrame",
    index: Optional[pd.Index] = None,
) -> pd.DataFrame:
    """Convert Polars DataFrame back to pandas, ensuring NaN semantics (C6).

    Polars uses null for missing values; this function ensures they become
    NaN in the output numpy/pandas representation.

    Parameters
    ----------
    pl_df : pl.DataFrame
        Polars DataFrame to convert.
    index : pd.Index, optional
        Index to assign to the resulting pandas DataFrame.

    Returns
    -------
    pd.DataFrame
        Pandas DataFrame with NaN where Polars had null.
    """
    if pl_df.is_empty():
        cols = pl_df.columns
        pd_df = pd.DataFrame(columns=cols, dtype=np.float32)
        if index is not None:
            pd_df.index = index
        return pd_df

    # fill_null(NaN) ensures null -> NaN conversion
    filled = pl_df.fill_null(float("nan"))
    numpy_arr = filled.to_numpy()

    pd_df = pd.DataFrame(
        data=numpy_arr.astype(np.float32, copy=False),
        columns=pl_df.columns,
        copy=False,
    )
    if index is not None:
        pd_df.index = index
    return pd_df


def ensure_nan_semantics(pl_df: "pl.DataFrame") -> "pl.DataFrame":
    """Ensure Polars null values are compatible with NaN semantics (R5/C6).

    In Polars, division by zero produces inf (not NaN). This function
    normalizes inf/-inf to null (which becomes NaN in pandas).

    Parameters
    ----------
    pl_df : pl.DataFrame
        Polars DataFrame that may contain inf values.

    Returns
    -------
    pl.DataFrame
        Polars DataFrame with inf replaced by null.
    """
    import polars as pl

    # Replace inf/-inf with null to match pandas NaN behavior
    exprs = []
    for col_name in pl_df.columns:
        col = pl.col(col_name)
        exprs.append(
            pl.when(col.is_infinite())
            .then(None)
            .otherwise(col)
            .alias(col_name)
        )
    return pl_df.with_columns(exprs)


def polars_l2_derived_ratio(
    pl_df: "pl.DataFrame",
    pairs: List[Tuple[str, str, str]],
) -> "pl.DataFrame":
    """Compute ratio features using Polars expressions (A / B).

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame containing source columns.
    pairs : list of (col_a, col_b, output_name)
        Pairs of columns to compute ratio for.

    Returns
    -------
    pl.DataFrame
        DataFrame with only the new ratio columns.
    """
    import polars as pl

    if not pairs:
        return pl.DataFrame()

    exprs = []
    for col_a, col_b, output_name in pairs:
        if col_a not in pl_df.columns or col_b not in pl_df.columns:
            continue
        # Replace zero / near-zero (float-noise) denominator with null (-> NaN)
        denom = _safe_denom_expr(pl_df, col_b)
        exprs.append((pl.col(col_a) / denom).alias(output_name))

    if not exprs:
        return pl.DataFrame()

    result = pl_df.select(exprs)
    return ensure_nan_semantics(result)


def polars_l2_derived_diff(
    pl_df: "pl.DataFrame",
    pairs: List[Tuple[str, str, str]],
) -> "pl.DataFrame":
    """Compute difference features using Polars expressions (A - B).

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame containing source columns.
    pairs : list of (col_a, col_b, output_name)
        Pairs of columns to compute difference for.

    Returns
    -------
    pl.DataFrame
        DataFrame with only the new diff columns.
    """
    import polars as pl

    if not pairs:
        return pl.DataFrame()

    exprs = []
    for col_a, col_b, output_name in pairs:
        if col_a not in pl_df.columns or col_b not in pl_df.columns:
            continue
        exprs.append((pl.col(col_a) - pl.col(col_b)).alias(output_name))

    if not exprs:
        return pl.DataFrame()

    return pl_df.select(exprs)


def polars_l2_derived_distance(
    pl_df: "pl.DataFrame",
    pairs: List[Tuple[str, str, str]],
) -> "pl.DataFrame":
    """Compute distance features: (price - indicator) / indicator.

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame containing source (price) and indicator columns.
    pairs : list of (price_col, indicator_col, output_name)
        Triples specifying (numerator, denominator/base, output column name).

    Returns
    -------
    pl.DataFrame
        DataFrame with only the new distance columns.
    """
    import polars as pl

    if not pairs:
        return pl.DataFrame()

    exprs = []
    for price_col, indicator_col, output_name in pairs:
        if price_col not in pl_df.columns or indicator_col not in pl_df.columns:
            continue
        # Distance = (price - indicator) / indicator
        # Replace zero / near-zero (float-noise) denominator with null → NaN not inf
        safe_denom = _safe_denom_expr(pl_df, indicator_col)
        expr = ((pl.col(price_col) - pl.col(indicator_col)) / safe_denom).alias(output_name)
        exprs.append(expr)

    if not exprs:
        return pl.DataFrame()

    result = pl_df.select(exprs)
    return ensure_nan_semantics(result)


def polars_l2_derived_momentum(
    pl_df: "pl.DataFrame",
    specs: List[Tuple[str, int, str]],
) -> "pl.DataFrame":
    """Compute momentum features: (value[t] - value[t-n]) / value[t-n].

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame.
    specs : list of (col_name, lag, output_name)
        Column name, lag period, and output name for each momentum feature.

    Returns
    -------
    pl.DataFrame
        DataFrame with only the new momentum columns.
    """
    import polars as pl

    if not specs:
        return pl.DataFrame()

    # FFSTAT v53：分母＝col[t−lag]，其近零遮罩＝col 之因果遮罩（`causal_near_zero_mask`，尺度只看 t−lag 之前之
    # 固定窗）平移 lag 列；改前以全欄中位數為尺度＝未來洩漏
    from momentum.FeatureEngineering.utils.numeric_guards import causal_near_zero_mask

    exprs = []
    masks: Dict[str, np.ndarray] = {}
    for col_name, lag, output_name in specs:
        if col_name not in pl_df.columns:
            continue
        col = pl.col(col_name)
        shifted = col.shift(lag)
        if col_name not in masks:
            values = pl_df.get_column(col_name).cast(pl.Float64).to_numpy()  # Float64 之 null 轉 numpy 即 NaN
            masks[col_name] = causal_near_zero_mask(values, DEFAULT_DENOM_REL_EPS)
        base = masks[col_name]
        lag_i = int(lag)
        shifted_mask = np.concatenate([np.ones(min(lag_i, len(base)), dtype=bool), base[: max(len(base) - lag_i, 0)]])
        denom = pl.when(pl.lit(pl.Series(shifted_mask))).then(None).otherwise(shifted)
        exprs.append(((col - shifted) / denom).alias(output_name))

    if not exprs:
        return pl.DataFrame()

    result = pl_df.select(exprs)
    return ensure_nan_semantics(result)
