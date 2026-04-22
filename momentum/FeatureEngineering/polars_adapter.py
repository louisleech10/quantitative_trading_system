"""Polars adapter for Feature Factory Phase 4 optimization.

Provides Polars-based implementations of L1/L2/L6.5 operations with
automatic fallback to pandas when FFACT_USE_POLARS=0 (default).

Risk mitigations:
- R5: Polars null vs NaN — handled by ensure_nan_semantics()
- R25: Version pinned to polars>=0.20,<0.21
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Optional, Tuple

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger

if TYPE_CHECKING:
    import polars as pl

logger = get_logger(__name__)

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
    """Check if Polars path is enabled via env var AND polars is installed."""
    raw = os.getenv("FFACT_USE_POLARS", "0").strip().lower()
    enabled = raw in {"1", "true", "yes", "on"}
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
        # Replace zero denominator with null (-> NaN in pandas)
        denom = pl.when(pl.col(col_b) == 0.0).then(None).otherwise(pl.col(col_b))
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
        # Replace zero denominator with null to produce NaN instead of inf
        safe_denom = pl.when(pl.col(indicator_col) != 0.0).then(pl.col(indicator_col)).otherwise(None)
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

    exprs = []
    for col_name, lag, output_name in specs:
        if col_name not in pl_df.columns:
            continue
        col = pl.col(col_name)
        shifted = col.shift(lag)
        denom = pl.when(shifted == 0.0).then(None).otherwise(shifted)
        exprs.append(((col - shifted) / denom).alias(output_name))

    if not exprs:
        return pl.DataFrame()

    result = pl_df.select(exprs)
    return ensure_nan_semantics(result)


def polars_l65_winsorization(
    pl_df: "pl.DataFrame",
    columns: List[str],
    method: str = "sigma",
    sigma_k: float = 3.0,
    quantile_range: Tuple[float, float] = (0.01, 0.99),
) -> "pl.DataFrame":
    """Apply winsorization using Polars expressions.

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame.
    columns : list of str
        Columns to winsorize.
    method : str
        'sigma' or 'quantile'.
    sigma_k : float
        Sigma multiplier for sigma method.
    quantile_range : tuple
        Lower and upper quantile for quantile method.

    Returns
    -------
    pl.DataFrame
        DataFrame with winsorized columns (same column names).
    """
    import polars as pl

    if not columns:
        return pl_df

    valid_columns = [c for c in columns if c in pl_df.columns]
    if not valid_columns:
        return pl_df

    if method == "sigma":
        exprs = []
        for col_name in valid_columns:
            col = pl.col(col_name)
            mean_val = col.mean()
            std_val = col.std()
            lower = mean_val - sigma_k * std_val
            upper = mean_val + sigma_k * std_val
            exprs.append(col.clip(lower, upper).alias(col_name))
        return pl_df.with_columns(exprs)
    elif method == "quantile":
        exprs = []
        for col_name in valid_columns:
            col = pl.col(col_name)
            lower = col.quantile(quantile_range[0])
            upper = col.quantile(quantile_range[1])
            exprs.append(col.clip(lower, upper).alias(col_name))
        return pl_df.with_columns(exprs)
    else:
        raise ValueError(f"Unsupported winsorization method: {method}")


def polars_l65_rank_transform(
    pl_df: "pl.DataFrame",
    columns: List[str],
    window: int = 252,
) -> "pl.DataFrame":
    """Apply rolling rank transform using Polars expressions.

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame.
    columns : list of str
        Columns to rank transform.
    window : int
        Rolling window size.

    Returns
    -------
    pl.DataFrame
        DataFrame with rank-transformed columns (same column names).
    """
    import polars as pl

    if not columns:
        return pl_df

    valid_columns = [c for c in columns if c in pl_df.columns]
    if not valid_columns:
        return pl_df

    # Polars rolling rank: use rolling_map with rank logic
    # For large datasets, we use a workaround: rank / count over rolling window
    exprs = []
    for col_name in valid_columns:
        col = pl.col(col_name)
        # Polars rolling rank (pct) — use rolling with min_periods=1
        ranked = col.rolling_rank(window_size=window, min_periods=1, method="average")
        count = col.rolling_count(window_size=window)
        # Percentage rank
        pct_rank = ranked / count
        # Handle constant windows: when all values same -> 0.5
        rolling_max = col.rolling_max(window_size=window, min_periods=1)
        rolling_min = col.rolling_min(window_size=window, min_periods=1)
        is_constant = rolling_max == rolling_min
        result_expr = pl.when(col.is_null()).then(None).when(is_constant).then(0.5).otherwise(pct_rank)
        exprs.append(result_expr.alias(col_name))

    return pl_df.with_columns(exprs)


def polars_l65_adaptive_zscore(
    pl_df: "pl.DataFrame",
    columns: List[str],
    window: int = 100,
    epsilon: float = 1e-8,
) -> "pl.DataFrame":
    """Apply adaptive z-score using Polars expressions.

    Parameters
    ----------
    pl_df : pl.DataFrame
        Input Polars DataFrame.
    columns : list of str
        Columns to z-score.
    window : int
        Rolling window size.
    epsilon : float
        Small value to prevent division by zero.

    Returns
    -------
    pl.DataFrame
        DataFrame with z-scored columns (same column names).
    """
    import polars as pl

    if not columns:
        return pl_df

    valid_columns = [c for c in columns if c in pl_df.columns]
    if not valid_columns:
        return pl_df

    exprs = []
    for col_name in valid_columns:
        col = pl.col(col_name)
        mean_val = col.rolling_mean(window_size=window, min_periods=1)
        std_val = col.rolling_std(window_size=window, min_periods=1)
        zscore = (col - mean_val) / (std_val + epsilon)
        # When std <= 0, output 0 (matching pandas behavior)
        result_expr = (
            pl.when(col.is_null())
            .then(None)
            .when(std_val <= 0.0)
            .then(0.0)
            .otherwise(zscore)
        )
        exprs.append(result_expr.alias(col_name))

    return pl_df.with_columns(exprs)
