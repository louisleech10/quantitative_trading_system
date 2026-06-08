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
  map_batches() + scipy.stats.rankdata in polars_l65_rank_transform().
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, List, Optional, Tuple

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

    門檻 = `rel_eps × median(|nonzero values|)`（per-column robust scale，與 pandas
    `safe_denominator` 同邏輯）。擋 TA-Lib 振盪器邊界的 ~1e-14 浮點噪音、保留真實小值。
    """
    import polars as pl

    d = pl.col(denom_col)
    if rel_eps <= 0:
        return pl.when(d == 0.0).then(None).otherwise(d)

    abs_col = pl_df.get_column(denom_col).abs()
    nonzero = abs_col.filter(abs_col > 0)
    scale = float(nonzero.median()) if nonzero.len() > 0 and nonzero.median() is not None else 0.0
    threshold = scale * rel_eps
    return pl.when((d.abs() < threshold) | (d == 0.0)).then(None).otherwise(d)

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
    raw = os.getenv("FFACT_USE_POLARS", "1").strip().lower()
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

    # Near-zero threshold uses the column's own robust scale (shift preserves the
    # value distribution → same scale as the un-shifted column).
    exprs = []
    for col_name, lag, output_name in specs:
        if col_name not in pl_df.columns:
            continue
        col = pl.col(col_name)
        shifted = col.shift(lag)
        abs_col = pl_df.get_column(col_name).abs()
        nonzero = abs_col.filter(abs_col > 0)
        scale = float(nonzero.median()) if nonzero.len() > 0 and nonzero.median() is not None else 0.0
        threshold = scale * DEFAULT_DENOM_REL_EPS
        denom = pl.when((shifted.abs() < threshold) | (shifted == 0.0)).then(None).otherwise(shifted)
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
    causal_preprocessing: bool = True,
    window: int = 252,
    min_periods: int = 63,
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

    if causal_preprocessing:
        pdf = pl_df.to_pandas()
        arr = pdf.loc[:, valid_columns].to_numpy(dtype=np.float64, copy=True)
        if method == "sigma":
            mean, std = _rolling_mean_std(arr, int(window), min_periods=int(min_periods))
            lower = mean.astype(np.float64) - float(sigma_k) * std.astype(np.float64)
            upper = mean.astype(np.float64) + float(sigma_k) * std.astype(np.float64)
        elif method == "quantile":
            lower, upper = rolling_quantile_2d(
                arr,
                float(quantile_range[0]),
                float(quantile_range[1]),
                int(window),
                int(min_periods),
            )
        else:
            raise ValueError(f"Unsupported winsorization method: {method}")
        nan_mask = np.isnan(arr)
        valid_bounds = np.isfinite(lower) & np.isfinite(upper)
        clipped = np.clip(arr, lower, upper)
        arr[valid_bounds] = clipped[valid_bounds]
        arr[nan_mask] = np.nan
        pdf.loc[:, valid_columns] = arr.astype(np.float32, copy=False)
        return pl.from_pandas(pdf)

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


def _make_rolling_pct_rank_fn(window: int):
    """Create a rolling pct-rank closure for polars 1.x map_batches.

    Replaces polars 0.20.x rolling_rank() which was removed in polars 1.x.
    Semantics:
    - Null input → null output (NaN in pandas).
    - Constant window (max==min) → 0.5 exactly.
    - Otherwise: 1-indexed average rank / count of non-null values in window.
    Numerically equivalent to pandas rolling.rank(pct=True, method='average',
    min_periods=max(20, window//4)) within float32 precision (atol < 1e-5).
    """
    from scipy.stats import rankdata as _rankdata

    _w = max(1, int(window))
    _min_periods = min(_w, max(20, _w // 4))

    def _fn(s: "pl.Series") -> "pl.Series":
        import polars as pl

        # to_numpy(): null → np.nan for float series (both polars 0.20 and 1.x)
        arr = s.to_numpy()
        n = len(arr)
        out = np.full(n, np.nan, dtype=np.float32)

        for i in range(n):
            curr = arr[i]
            if np.isnan(curr):
                continue  # null input → null output

            start = max(0, i - _w + 1)
            w_data = arr[start : i + 1]
            valid = w_data[~np.isnan(w_data)]
            n_valid = len(valid)
            if n_valid < _min_periods:
                continue

            # Constant window → 0.5 (matches pandas constant_mask behaviour)
            if np.all(valid == valid[0]):
                out[i] = 0.5
                continue

            # valid[-1] == curr because curr is not NaN and is the last element
            # of w_data, so it is preserved at the tail of valid.
            ranks = _rankdata(valid, method="average")
            out[i] = np.float32(ranks[-1] / n_valid)

        # fill_nan(None): NaN → polars null so downstream rolling ops skip them
        return pl.Series(out).fill_nan(None)

    return _fn


def polars_l65_rank_transform(
    pl_df: "pl.DataFrame",
    columns: List[str],
    window: int = 252,
) -> "pl.DataFrame":
    """Apply rolling rank transform using map_batches (polars 1.x compatible).

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

    Notes
    -----
    polars 0.20.x rolling_rank() was removed in polars 1.x.
    Replaced with map_batches() + scipy.stats.rankdata.
    Results are numerically equivalent to the pandas path within float32
    precision (atol < 1e-5) as verified by T4.2 test suite.
    """
    import polars as pl

    if not columns:
        return pl_df

    valid_columns = [c for c in columns if c in pl_df.columns]
    if not valid_columns:
        return pl_df

    rank_fn = _make_rolling_pct_rank_fn(window)
    exprs = [
        pl.col(col_name).map_batches(rank_fn, return_dtype=pl.Float32).alias(col_name)
        for col_name in valid_columns
    ]
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
        mean_val = col.rolling_mean(window_size=window, min_samples=1)
        std_val = col.rolling_std(window_size=window, min_samples=1)
        zscore = (col - mean_val) / (std_val + epsilon)
        # When std is null (single-point window, ddof=1 undefined) or std <= 0,
        # output 0 to match pandas rolling_std(min_periods=1) + where(std>0, 0.0) logic.
        result_expr = (
            pl.when(col.is_null())
            .then(None)
            .when(std_val.is_null() | (std_val <= 0.0))
            .then(0.0)
            .otherwise(zscore)
        )
        exprs.append(result_expr.alias(col_name))

    return pl_df.with_columns(exprs)
