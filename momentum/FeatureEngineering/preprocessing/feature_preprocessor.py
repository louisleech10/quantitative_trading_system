from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Union

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


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
        self.mode = self._config.get("mode", "append")

        self._fracdiff_processed_columns: set[str] = set()

    def transform(self, features_df: pd.DataFrame) -> pd.DataFrame:
        if features_df is None or features_df.empty:
            return pd.DataFrame(index=features_df.index if features_df is not None else None)

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

    def _apply_winsorization(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.winsor_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        method = self.winsor_config.get("method", "sigma")

        if not columns:
            return df

        result = df.copy()
        for column in columns:
            series = result[column].astype(float)
            if method == "sigma":
                sigma_k = float(self.winsor_config.get("sigma_k", 3.0))
                mean = series.mean(skipna=True)
                std = series.std(skipna=True)
                if pd.isna(std) or std == 0.0:
                    continue
                lower = mean - sigma_k * std
                upper = mean + sigma_k * std
                result[column] = series.clip(lower=lower, upper=upper)
            elif method == "quantile":
                quantile_range = self.winsor_config.get("quantile_range", [0.01, 0.99])
                lower_q = float(quantile_range[0])
                upper_q = float(quantile_range[1])
                lower = series.quantile(lower_q)
                upper = series.quantile(upper_q)
                result[column] = series.clip(lower=lower, upper=upper)
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

        cache = {}
        if self.fracdiff_config.get("cache_d_star", True):
            cache = self._load_d_star_cache("default", "default")

        for column in columns:
            series = result[column].astype(float)
            if series.isna().mean() > 0.5:
                logger.warning("FracDiff skipped for %s due to too many NaN", column)
                continue

            try:
                if column in cache:
                    d_star = float(cache[column])
                else:
                    d_star = self._find_min_d(
                        series,
                        adf_threshold=adf_threshold,
                        d_range=(float(d_range[0]), float(d_range[1])),
                        precision=precision,
                    )
                    cache[column] = d_star
            except Exception as exc:
                logger.warning("FracDiff d* search failed for %s: %s; fallback to d=1.0", column, exc)
                d_star = 1.0

            frac = self._frac_diff_ffd(series, d_star, threshold=weight_threshold)

            if self.mode == "replace":
                result[column] = frac
            else:
                result[f"{column}_fracdiff"] = frac

            self._fracdiff_processed_columns.add(column)

        if self.fracdiff_config.get("cache_d_star", True):
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

        for column in columns:
            if column in self._fracdiff_processed_columns:
                continue

            series = result[column].astype(float)
            if series.isna().mean() > 0.5:
                logger.warning("ADF differencing skipped for %s due to too many NaN", column)
                continue

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

        return result

    def _apply_rank_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        apply_to = self.rank_config.get("apply_to", "all")
        columns = self._select_columns(df, apply_to)
        window = int(self.rank_config.get("window", 252))

        if not columns:
            return df

        result = df.copy()
        new_columns: Dict[str, pd.Series] = {}

        def _rank_last(values: pd.Series) -> float:
            if values.isna().all():
                return np.nan
            if values.nunique(dropna=True) <= 1:
                return 0.5
            return float(values.rank(pct=True).iloc[-1])

        for column in columns:
            ranked = result[column].astype(float).rolling(window, min_periods=1).apply(_rank_last, raw=False)
            if self.mode == "replace":
                result[column] = ranked
            else:
                new_columns[f"{column}_rank"] = ranked

        if self.mode != "replace" and new_columns:
            result = pd.concat([result, pd.DataFrame(new_columns, index=result.index)], axis=1)

        return result

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
                result[column] = gaussian_series
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
        new_columns: Dict[str, pd.Series] = {}
        primary_window = int(windows[0]) if windows else 100

        for column in columns:
            series = result[column].astype(float)
            if self.mode == "replace":
                mean = series.rolling(primary_window, min_periods=1).mean()
                std = series.rolling(primary_window, min_periods=1).std()
                zscore = (series - mean) / (std + epsilon)
                zscore = zscore.where(std > 0.0, 0.0)
                zscore = zscore.where(~series.isna(), np.nan)
                result[column] = zscore
            else:
                for window in windows:
                    window_int = int(window)
                    mean = series.rolling(window_int, min_periods=1).mean()
                    std = series.rolling(window_int, min_periods=1).std()
                    zscore = (series - mean) / (std + epsilon)
                    zscore = zscore.where(std > 0.0, 0.0)
                    zscore = zscore.where(~series.isna(), np.nan)
                    new_columns[f"{column}_zscore_{window_int}"] = zscore

        if self.mode != "replace" and new_columns:
            result = pd.concat([result, pd.DataFrame(new_columns, index=result.index)], axis=1)

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
    def _get_weights_ffd(d: float, threshold: float = 1e-5) -> np.ndarray:
        weights = [1.0]
        k = 1
        while True:
            w = -weights[-1] * (d - k + 1) / k
            if abs(w) < threshold:
                break
            weights.append(w)
            k += 1
        return np.array(weights[::-1], dtype=np.float64)

    @staticmethod
    def _frac_diff_ffd(series: pd.Series, d: float, threshold: float = 1e-5) -> pd.Series:
        values = series.astype(float)
        weights = FeaturePreprocessor._get_weights_ffd(d, threshold)
        width = len(weights)

        if len(values) < width:
            return pd.Series(np.nan, index=series.index)

        filled = values.ffill().bfill().to_numpy(dtype=np.float64)
        conv = np.convolve(filled, weights, mode="valid")
        out = np.full(len(filled), np.nan, dtype=np.float64)
        out[width - 1 :] = conv
        return pd.Series(out, index=series.index)

    def _find_min_d(
        self,
        series: pd.Series,
        adf_threshold: float = 0.05,
        d_range: Tuple[float, float] = (0.0, 1.0),
        precision: float = 0.01,
    ) -> float:
        if not HAS_STATSMODELS:
            return 1.0

        clean = series.dropna()
        if len(clean) < 20:
            return 1.0

        left, right = float(d_range[0]), float(d_range[1])
        best = right

        def _is_stationary(d_value: float) -> bool:
            frac = self._frac_diff_ffd(clean, d_value, threshold=float(self.fracdiff_config.get("weight_threshold", 1e-5)))
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
