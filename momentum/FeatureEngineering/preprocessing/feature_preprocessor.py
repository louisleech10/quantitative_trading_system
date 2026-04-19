from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


if TYPE_CHECKING:
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry


logger = get_logger(__name__)

try:
    from scipy.special import erfinv

    HAS_SCIPY = True
except Exception:
    HAS_SCIPY = False
    erfinv = None
    logger.warning("scipy not available, gaussian normalization disabled")

try:
    from statsmodels.tsa.stattools import adfuller

    HAS_STATSMODELS = True
except Exception:
    HAS_STATSMODELS = False
    adfuller = None
    logger.warning("statsmodels not available, ADF/Fractional Differencing disabled")


class FeaturePreprocessor:
    """Layer 6.5: 特徵前處理與正規化。"""

    def __init__(self, config: Dict):
        self._config = config or {}
        self.rank_config = self._config.get("rank_transform", {})
        self.gaussian_config = self._config.get("gaussian_normalize", {})
        self.adf_config = self._config.get("adf_differencing", {})
        self.zscore_config = self._config.get("adaptive_zscore", {})
        self.winsor_config = self._config.get("winsorization", {})
        self.fracdiff_config = self._config.get("fractional_differencing", {})
        # 預設 replace：確保跨標的欄位名稱一致
        self.mode = self._config.get("mode", "replace")

        self._fracdiff_processed_columns: set[str] = set()
        self._column_chunk_size = self._resolve_column_chunk_size()
        self._d_star_cache: Optional[Dict[str, float]] = None

    @staticmethod
    def _resolve_column_chunk_size() -> int:
        """Resolve L6.5 column chunk size from env var (0 = disabled)."""
        raw = os.getenv("FFACT_L65_CHUNK_SIZE", "2000").strip()
        try:
            size = int(raw)
        except ValueError:
            size = 2000
        return max(size, 0)

    def transform(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if features_df is None or features_df.empty:
            return pd.DataFrame(index=features_df.index if features_df is not None else None)

        num_cols = len(features_df.columns)
        chunk_size = self._column_chunk_size

        if chunk_size > 0 and num_cols > chunk_size:
            return self._transform_chunked(features_df, chunk_size)

        return self._transform_single(features_df)

    def transform_registry_groups(self, registry: "ColumnGroupRegistry") -> int:
        """Apply L6.5 transforms per group from registry and overwrite each group in place."""
        if registry is None:
            return 0

        # Determine which transforms are active (for the fast numpy path).
        do_winsorize = self.winsor_config.get("enabled", True)
        do_rank = self.rank_config.get("enabled", False)
        do_zscore = self.zscore_config.get("enabled", False)
        do_fracdiff = self.fracdiff_config.get("enabled", False)
        do_adf = self.adf_config.get("enabled", False)
        do_gaussian = self.gaussian_config.get("enabled", False)

        # Use the fast numpy/numba path when only winsorize+rank+zscore are active
        # (the common CGSA case), avoiding pandas overhead entirely.
        use_fast = (
            not do_fracdiff
            and not do_adf
            and not do_gaussian
            and self.mode == "replace"
        )

        if use_fast:
            from momentum.FeatureEngineering.preprocessing._numba_transforms import (
                transform_array_fast,
                warmup_numba,
            )
            # JIT warmup once (< 1s).
            warmup_numba()

            winsor_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            rank_window = int(self.rank_config.get("window", 252))
            zscore_windows = self.zscore_config.get("windows", [100, 252])
            zscore_primary = int(zscore_windows[0]) if zscore_windows else 100
            zscore_eps = float(self.zscore_config.get("epsilon", 1e-8))

        import time as _time
        from momentum.FeatureEngineering.core.column_group import ColumnGroup as _CG, LayerSource as _LS

        processed_count = 0
        all_groups = list(registry.iter_all())
        total_groups = len(all_groups)
        t0_all = _time.time()
        is_append = self.mode == "append"

        for idx, (group_id, group) in enumerate(all_groups, 1):
            if group.n_cols == 0:
                continue

            t0 = _time.time()
            group_array = np.asarray(registry.load_data(group_id), dtype=np.float32)

            if use_fast:
                processed_array = transform_array_fast(
                    group_array,
                    winsorize=do_winsorize,
                    winsor_lower_q=float(winsor_range[0]),
                    winsor_upper_q=float(winsor_range[1]),
                    rank=do_rank,
                    rank_window=rank_window,
                    zscore=do_zscore,
                    zscore_window=zscore_primary,
                    zscore_epsilon=zscore_eps,
                )
                registry.overwrite_data(group_id, processed_array)
            else:
                # Fallback: original pandas path for exotic transforms or append mode.
                group_df = pd.DataFrame(group_array, columns=list(group.columns), copy=False)
                processed_df = self._transform_single(group_df)

                if is_append and len(processed_df.columns) > group.n_cols:
                    # Split: overwrite originals, save appended cols as new group.
                    orig_cols = list(group.columns)
                    orig_array = processed_df[orig_cols].to_numpy(dtype=np.float32, copy=False)
                    registry.overwrite_data(group_id, orig_array)

                    new_cols = [c for c in processed_df.columns if c not in orig_cols]
                    if new_cols:
                        new_array = processed_df[new_cols].to_numpy(dtype=np.float32, copy=False)
                        new_gid = f"{group_id}_L65"
                        # Avoid collision
                        suffix = 1
                        while new_gid in registry._groups:
                            new_gid = f"{group_id}_L65_{suffix}"
                            suffix += 1
                        new_group = _CG(
                            group_id=new_gid,
                            layer=_LS.L65,
                            timeframe=group.timeframe,
                            data_source="preprocessed",
                            indicator=group.indicator,
                            columns=tuple(new_cols),
                            shape=(new_array.shape[0], new_array.shape[1]),
                            dtype="float32",
                        )
                        registry.save_data(new_group, new_array)
                else:
                    processed_array = processed_df.to_numpy(dtype=np.float32, copy=False)
                    registry.overwrite_data(group_id, processed_array)

            processed_count += 1

            elapsed = _time.time() - t0
            if elapsed > 5.0 or idx % 50 == 0 or idx == total_groups:
                logger.info(
                    "[L6.5][CGSA] Group %d/%d (%s) %d cols — %.1fs",
                    idx, total_groups, group_id, group.n_cols, elapsed,
                )

        total_elapsed = _time.time() - t0_all
        logger.info(
            "[L6.5][CGSA] Per-group preprocessing completed: %d groups in %.1fs (fast=%s)",
            processed_count, total_elapsed, use_fast,
        )
        return processed_count

    def _transform_single(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """Original transform logic applied to a full DataFrame."""
        transformed = features_df.copy()
        self._fracdiff_processed_columns = set()

        transformed = self._apply_winsorization(transformed)

        if self.fracdiff_config.get("enabled", False):
            transformed = self._apply_fractional_differencing(transformed)

        if self.adf_config.get("enabled", False):
            transformed = self._apply_adf_differencing(transformed)

        if self.rank_config.get("enabled", False):
            transformed = self._apply_rank_transform(transformed)

        if self.gaussian_config.get("enabled", False):
            transformed = self._apply_gaussian_normalize(transformed)

        if self.zscore_config.get("enabled", False):
            transformed = self._apply_adaptive_zscore(transformed)

        return transformed

    def _transform_chunked(self, features_df: pd.DataFrame, chunk_size: int) -> pd.DataFrame:
        """Process columns in chunks to limit peak memory on wide DataFrames.

        All L6.5 operations (winsorization, rank_transform, adaptive_zscore, etc.)
        are column-independent, so chunking does not affect correctness.
        """
        all_columns = list(features_df.columns)
        n_chunks = (len(all_columns) + chunk_size - 1) // chunk_size
        logger.info(
            "[L6.5] Column chunking activated: %d cols → %d chunks of ≤%d",
            len(all_columns),
            n_chunks,
            chunk_size,
        )

        result_chunks: List[pd.DataFrame] = []
        use_memmap = (len(features_df.index) * len(all_columns) * 4) >= 500_000_000

        use_shared_dstar_cache = bool(
            self.fracdiff_config.get("enabled", False)
            and self.fracdiff_config.get("cache_d_star", True)
        )
        if use_shared_dstar_cache:
            # Load once for the whole run (instead of once per chunk).
            self._d_star_cache = self._load_d_star_cache("default", "default")

        if use_memmap:
            from momentum.FeatureEngineering.memmap_utils import create_temp_memmap
            import numpy as _np

            out_arr = create_temp_memmap(
                (len(features_df.index), len(all_columns)), prefix="l65_"
            )
            col_offset = 0

        for i in range(0, len(all_columns), chunk_size):
            chunk_cols = all_columns[i : i + chunk_size]
            chunk_idx = i // chunk_size + 1
            logger.info("[L6.5] Processing chunk %d/%d (%d cols)", chunk_idx, n_chunks, len(chunk_cols))

            chunk_df = features_df[chunk_cols]
            processed_chunk = self._transform_single(chunk_df)

            if use_memmap:
                n = processed_chunk.shape[1]
                out_arr[:, col_offset : col_offset + n] = _np.asarray(
                    processed_chunk.values, dtype=_np.float32
                )
                col_offset += n
                del processed_chunk
            else:
                result_chunks.append(processed_chunk)

            # Release references to reduce peak memory
            del chunk_df

        if use_shared_dstar_cache and self._d_star_cache is not None:
            # Save once after all chunks complete.
            self._save_d_star_cache("default", "default", self._d_star_cache)
            self._d_star_cache = None

        if use_memmap:
            return pd.DataFrame(
                data=out_arr, index=features_df.index, columns=all_columns, copy=False,
            )

        if not result_chunks:
            return pd.DataFrame(index=features_df.index)

        return pd.concat(result_chunks, axis=1, copy=False)

    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.winsor_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        method = self.winsor_config.get("method", "sigma")

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        if method == "sigma":
            sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
            means = selected.mean(skipna=True)
            stds = selected.std(skipna=True)
            valid_std = (~stds.isna()) & (stds != 0.0)
            if not valid_std.any():
                return result

            valid_columns = valid_std[valid_std].index.tolist()
            lowers = means.loc[valid_columns] - sigma_k * stds.loc[valid_columns]
            uppers = means.loc[valid_columns] + sigma_k * stds.loc[valid_columns]
            clipped = selected.loc[:, valid_columns].clip(lower=lowers, upper=uppers, axis=1)
            clipped = clipped.astype(np.float32, copy=False)
            result.loc[:, valid_columns] = clipped
        elif method == "quantile":
            quantile_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
            lower_q = float(quantile_range[0])
            upper_q = float(quantile_range[1])
            lowers = selected.quantile(lower_q)
            uppers = selected.quantile(upper_q)
            clipped = selected.clip(lower=lowers, upper=uppers, axis=1)
            clipped = clipped.astype(np.float32, copy=False)
            result.loc[:, columns] = clipped.loc[:, columns]
        else:
            raise ValueError(f"Unsupported winsorization method: {method}")

        return result

    def _apply_fractional_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_STATSMODELS:
            logger.warning("Fractional differencing skipped: statsmodels unavailable")
            return df

        apply_to = self.fracdiff_config.get("apply_to", "non_stationary")
        columns = self._select_columns(df, apply_to)
        if not columns:
            return df

        result = df.copy()
        d_range = self.fracdiff_config.get("d_range", [0.0, 1.0])
        adf_threshold = float(self.fracdiff_config.get("adf_threshold", 0.05))
        weight_threshold = float(self.fracdiff_config.get("weight_threshold", 1e-5))
        precision = float(self.fracdiff_config.get("precision", 0.01))
        # 限制 weight 寬度：最多序列長度的 10%（上限 252），避免 d≈0.5 時產生大量 NaN
        max_lag = int(self.fracdiff_config.get("max_lag", 0))
        if max_lag <= 0:
            max_lag = min(max(2, len(df) // 10), 252)

        cache_enabled = bool(self.fracdiff_config.get("cache_d_star", True))
        if self._d_star_cache is not None:
            cache = self._d_star_cache
            shared_cache = True
        elif cache_enabled:
            cache = self._load_d_star_cache("default", "default")
            shared_cache = False
        else:
            cache = {}
            shared_cache = False

        # Precompute NaN rates once per chunk to avoid per-column scans.
        nan_rates = result.loc[:, columns].isna().mean()
        eligible_columns = [column for column in columns if float(nan_rates.get(column, 1.0)) <= 0.5]
        skipped_high_nan: List[str] = [column for column in columns if column not in eligible_columns]

        for column in eligible_columns:
            series = result[column].astype(float)

            try:
                if column in cache:
                    d_star = float(cache[column])
                else:
                    d_star = self._find_min_d(
                        series,
                        adf_threshold=adf_threshold,
                        d_range=(float(d_range[0]), float(d_range[1])),
                        precision=precision,
                        max_lag=max_lag,
                    )
                    cache[column] = d_star
            except Exception as exc:
                logger.warning("FracDiff d* search failed for %s: %s; fallback to d=1.0", column, exc)
                d_star = 1.0

            frac = self._frac_diff_ffd(series, d_star, threshold=weight_threshold, max_width=max_lag)

            if self.mode == "replace":
                result[column] = frac
            else:
                result[f"{column}_fracdiff"] = frac

            self._fracdiff_processed_columns.add(column)

        if skipped_high_nan:
            logger.warning(
                "FracDiff skipped for %d columns due to too many NaN. Sample: %s",
                len(skipped_high_nan),
                skipped_high_nan[:10],
            )

        if cache_enabled and not shared_cache:
            self._save_d_star_cache("default", "default", cache)

        return result

    def _apply_adf_differencing(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_STATSMODELS:
            logger.warning("ADF differencing skipped: statsmodels unavailable")
            return df

        apply_to = self.adf_config.get("apply_to", "non_stationary")
        columns = self._select_columns(df, apply_to)
        if not columns:
            return df

        result = df.copy()
        threshold = float(self.adf_config.get("adf_threshold", 0.05))
        max_diff = int(self.adf_config.get("max_diff", 2))
        sample_size = int(self.adf_config.get("sample_size", 500))
        candidate_columns = [
            column for column in columns if column not in self._fracdiff_processed_columns
        ]
        if not candidate_columns:
            return result

        nan_rates = result.loc[:, candidate_columns].isna().mean()
        eligible_columns = [
            column for column in candidate_columns if float(nan_rates.get(column, 1.0)) <= 0.5
        ]
        skipped_high_nan: List[str] = [
            column for column in candidate_columns if column not in eligible_columns
        ]

        for column in eligible_columns:
            series = result[column].astype(float)

            working = series.copy()
            chosen_diff = 0
            for diff_order in range(max_diff + 1):
                clean = working.dropna()
                if len(clean) < 20:
                    break
                sample = clean.tail(sample_size)
                try:
                    pvalue = adfuller(sample, autolag="AIC")[1]
                except Exception:
                    pvalue = 1.0

                if pvalue <= threshold:
                    chosen_diff = diff_order
                    break

                if diff_order < max_diff:
                    working = working.diff()

            if chosen_diff == 0:
                continue

            if self.mode == "replace":
                result[column] = working
            else:
                result[f"{column}_diff{chosen_diff}"] = working

        if skipped_high_nan:
            logger.warning(
                "ADF differencing skipped for %d columns due to too many NaN. Sample: %s",
                len(skipped_high_nan),
                skipped_high_nan[:10],
            )

        return result

    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.rank_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        window = int(self.rank_config.get("window", 252))

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)

        # Use pandas' vectorized rolling.rank fast path and patch constant windows
        # to keep legacy behavior exactly (constant window -> 0.5).
        rolling = selected.rolling(window, min_periods=1)
        ranked_df = rolling.rank(
            method="average",
            pct=True,
        )
        rolling_max = rolling.max()
        rolling_min = rolling.min()
        # all-NaN windows naturally produce False here (NaN == NaN is False).
        constant_mask = rolling_max == rolling_min
        ranked_df = ranked_df.mask(constant_mask, 0.5)
        ranked_df = ranked_df.where(~selected.isna(), np.nan)
        ranked_df = ranked_df.astype(np.float32, copy=False)

        if self.mode == "replace":
            result.loc[:, columns] = ranked_df
        else:
            ranked_df = ranked_df.rename(columns={column: f"{column}_rank" for column in columns})
            result = pd.concat([result, ranked_df], axis=1)

        return result

    def _rolling_last_rank_pct_for_preprocess(self, values: np.ndarray) -> float:
        """Rolling percentile rank for the last value, preserving legacy constant-window behavior."""
        last = values[-1]
        if np.isnan(last):
            return np.nan

        valid_mask = ~np.isnan(values)
        valid_count = int(valid_mask.sum())
        if valid_count == 0:
            return np.nan

        valid_values = values[valid_mask]
        # Keep legacy behavior: constant windows map to 0.5 exactly.
        if np.nanmax(valid_values) == np.nanmin(valid_values):
            return 0.5

        less_count = int(np.sum(valid_values < last))
        equal_count = int(np.sum(valid_values == last))
        average_rank = less_count + (equal_count + 1) / 2.0
        return average_rank / float(valid_count)

    def _apply_gaussian_normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        if not HAS_SCIPY:
            logger.warning("Gaussian normalization skipped: scipy unavailable")
            return df

        apply_to = self.gaussian_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        clip_range = self.gaussian_config.get("clip_range", [0.001, 0.999])
        lower = float(clip_range[0])
        upper = float(clip_range[1])

        if not columns:
            return df

        result = df.copy()
        new_columns: Dict[str, pd.Series] = {}
        for column in columns:
            series = result[column].astype(float)
            if series.nunique(dropna=True) <= 1:
                ranked = pd.Series(0.5, index=series.index)
            else:
                ranked = series.rank(pct=True)
            clipped = ranked.clip(lower=lower, upper=upper)
            gaussian = np.sqrt(2.0) * erfinv(2.0 * clipped - 1.0)
            gaussian_series = pd.Series(gaussian, index=series.index)
            if self.mode == "replace":
                result[column] = gaussian_series.astype(np.float32, copy=False)
            else:
                new_columns[f"{column}_gaussian"] = gaussian_series

        if self.mode != "replace" and new_columns:
            result = pd.concat([result, pd.DataFrame(new_columns, index=result.index)], axis=1)

        return result

    def _apply_adaptive_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.zscore_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        windows = self.zscore_config.get("windows", [100, 252])
        epsilon = float(self.zscore_config.get("epsilon", 1e-8))

        if not columns:
            return df

        result = df.copy()
        selected = result.loc[:, columns].astype(float)
        primary_window = int(windows[0]) if windows else 100

        if self.mode == "replace":
            mean = selected.rolling(primary_window, min_periods=1).mean()
            std = selected.rolling(primary_window, min_periods=1).std()
            zscore = (selected - mean) / (std + epsilon)
            zscore = zscore.where(std > 0.0, 0.0)
            zscore = zscore.where(~selected.isna(), np.nan)
            zscore = zscore.astype(np.float32, copy=False)
            result.loc[:, columns] = zscore
        else:
            append_frames: List[pd.DataFrame] = []
            for window in windows:
                window_int = int(window)
                mean = selected.rolling(window_int, min_periods=1).mean()
                std = selected.rolling(window_int, min_periods=1).std()
                zscore = (selected - mean) / (std + epsilon)
                zscore = zscore.where(std > 0.0, 0.0)
                zscore = zscore.where(~selected.isna(), np.nan)
                zscore = zscore.astype(np.float32, copy=False)
                zscore = zscore.rename(columns={column: f"{column}_zscore_{window_int}" for column in columns})
                append_frames.append(zscore)

            if append_frames:
                result = pd.concat([result] + append_frames, axis=1)

        return result

    def _select_columns(self, df: pd.DataFrame, apply_to: Union[str, List[str]]) -> List[str]:
        numeric_columns = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        if not numeric_columns:
            return []

        if isinstance(apply_to, list):
            return [col for col in apply_to if col in numeric_columns]

        if apply_to == "all":
            return numeric_columns

        if apply_to == "layer1_only":
            prefixes = ("close_", "open_", "high_", "low_", "volume_", "quote_volume_", "taker_", "ms_", "ent_", "tr_")
            return [col for col in numeric_columns if col.startswith(prefixes)]

        if apply_to == "non_stationary":
            return self._get_non_stationary_columns(df[numeric_columns])

        try:
            pattern = re.compile(str(apply_to))
            return [col for col in numeric_columns if pattern.search(col)]
        except re.error:
            logger.warning("Invalid regex apply_to=%s, fallback to all numeric columns", apply_to)
            return numeric_columns

    def _get_non_stationary_columns(self, df: pd.DataFrame) -> List[str]:
        if not HAS_STATSMODELS:
            return []

        threshold = float(self.adf_config.get("adf_threshold", self.fracdiff_config.get("adf_threshold", 0.05)))
        non_stationary: List[str] = []

        for column in df.columns:
            series = df[column].dropna()
            if len(series) < 20:
                non_stationary.append(column)
                continue

            try:
                pvalue = adfuller(series.tail(500), autolag="AIC")[1]
            except Exception:
                pvalue = 1.0

            if pvalue > threshold:
                non_stationary.append(column)

        return non_stationary

    @staticmethod
    def _get_weights_ffd(d: float, threshold: float = 1e-5, max_width: int = 0) -> np.ndarray:
        """計算 FFD 權重序列。

        max_width > 0 時強制截斷，防止 d ≈ 0.5 時產生幾百個權重（導致同等數量的 NaN）。
        """
        weights = [1.0]
        k = 1
        while True:
            w = -weights[-1] * (d - k + 1) / k
            if abs(w) < threshold:
                break
            if max_width > 0 and len(weights) >= max_width:
                break
            weights.append(w)
            k += 1
        return np.array(weights[::-1], dtype=np.float64)

    @staticmethod
    def _frac_diff_ffd(
        series: pd.Series,
        d: float,
        threshold: float = 1e-5,
        max_width: int = 0,
    ) -> pd.Series:
        """Fixed-Width Window Fractional Differencing。

        只對第一個有效值之後的區間做卷積，初始 NaN 區間（如 EMA warmup）
        保持 NaN，不做 bfill，避免常數區差分後出現假 0 值。
        """
        values = series.astype(float)
        weights = FeaturePreprocessor._get_weights_ffd(d, threshold, max_width=max_width)
        width = len(weights)

        out = np.full(len(values), np.nan, dtype=np.float64)

        # 找第一個有效位置，避免 bfill 把 EMA warmup NaN 填成常數
        arr = values.to_numpy(dtype=np.float64)
        valid_mask = ~np.isnan(arr)
        if valid_mask.sum() < width:
            return pd.Series(out, index=series.index)

        first_valid = int(np.argmax(valid_mask))
        # 只在有效區間內做 ffill（處理中途偶發 NaN）
        valid_slice = pd.Series(arr[first_valid:], dtype=float).ffill().to_numpy(dtype=np.float64)

        if len(valid_slice) < width:
            return pd.Series(out, index=series.index)

        conv = np.convolve(valid_slice, weights, mode="valid")
        # 結果起始位置：first_valid + width - 1
        out[first_valid + width - 1 : first_valid + len(valid_slice)] = conv
        return pd.Series(out, index=series.index)

    def _find_min_d(
        self,
        series: pd.Series,
        adf_threshold: float = 0.05,
        d_range: Tuple[float, float] = (0.0, 1.0),
        precision: float = 0.01,
        max_lag: int = 0,
    ) -> float:
        if not HAS_STATSMODELS:
            return 1.0

        clean = series.dropna()
        if len(clean) < 20:
            return 1.0

        left, right = float(d_range[0]), float(d_range[1])
        best = right

        def _is_stationary(d_value: float) -> bool:
            frac = self._frac_diff_ffd(
                clean,
                d_value,
                threshold=float(self.fracdiff_config.get("weight_threshold", 1e-5)),
                max_width=max_lag,
            )
            frac_clean = frac.dropna()
            if len(frac_clean) < 20:
                return False
            pvalue = adfuller(frac_clean.tail(500), autolag="AIC")[1]
            return bool(pvalue <= adf_threshold)

        while right - left > precision:
            mid = (left + right) / 2.0
            try:
                stationary = _is_stationary(mid)
            except Exception:
                stationary = False

            if stationary:
                best = mid
                right = mid
            else:
                left = mid

        return round(best, 4)

    @staticmethod
    def _cache_path(symbol: str, timeframe: str) -> Path:
        cache_dir = Path("data_cache") / "feature_preprocessing"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / f"d_star_{symbol}_{timeframe}.json"

    def _load_d_star_cache(self, symbol: str, timeframe: str) -> Dict[str, float]:
        path = self._cache_path(symbol, timeframe)
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {str(k): float(v) for k, v in data.items()}
            return {}
        except Exception as exc:
            logger.warning("Failed to load d* cache: %s", exc)
            return {}

    def _save_d_star_cache(self, symbol: str, timeframe: str, cache: Dict[str, float]) -> None:
        path = self._cache_path(symbol, timeframe)
        try:
            path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save d* cache: %s", exc)
