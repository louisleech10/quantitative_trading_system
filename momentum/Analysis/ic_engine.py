"""IC core engine for IC Gatekeeper."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd
from scipy import optimize, stats

from momentum.core.logging import get_logger


logger = get_logger(__name__)


class ICEngine:
    """Stage 4: IC core engine."""

    def __init__(self, config: dict):
        self._config = config or {}
        self._methods = self._config.get("methods", ["spearman"])
        self._rolling_windows = self._config.get("rolling_windows", [21, 63, 126])
        self._rolling_stride = self._config.get("rolling_stride", 1)
        self._ic_decay_horizons = self._config.get(
            "ic_decay_horizons", [1, 2, 3, 5, 8, 13, 21]
        )

        icir_config = self._config.get("icir", {})
        self._icir_window = icir_config.get("window", 63)
        self._reference_tf = icir_config.get("reference_tf", "12h")
        self._timeframe = self._config.get("timeframe")

        self._grouped_config = self._config.get("grouped_analysis", {})

    def compute_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        method: str = "spearman",
    ) -> dict[str, float]:
        """計算所有特徵對單一 Label 的 IC."""

        if features_df.empty:
            return {}

        if len(features_df) < 2 or len(label) < 2:
            return {feature: np.nan for feature in features_df.columns}

        if method in {"spearman", "pearson"} and not self._has_missing(
            features_df, label
        ):
            return self._compute_vectorized_ic(features_df, label, method)

        label_name = label.name or "label"
        label_series = label.rename(label_name)
        results: dict[str, float] = {}

        for feature in features_df.columns:
            series = features_df[feature]
            value = self._compute_pairwise_corr(series, label_series, method)
            results[feature] = value

        return results

    def compute_rolling_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        windows: list[int],
        stride: int = 1,
        method: str = "spearman",
    ) -> dict[str, dict]:
        """Rolling IC 時間序列."""

        label_name = label.name or "label"
        aligned = pd.concat(
            [features_df, label.rename(label_name)], axis=1
        ).dropna()
        if aligned.empty:
            return {name: {} for name in features_df.columns}

        adjusted_windows = self._adjust_rolling_windows(windows)
        results: dict[str, dict] = {name: {} for name in features_df.columns}

        if method == "spearman":
            ranked_features = aligned[features_df.columns].rank(axis=0, method="average")
            ranked_label = aligned[label_name].rank(method="average")
            x_values = ranked_features.to_numpy(dtype=float)
            y_values = ranked_label.to_numpy(dtype=float)
        else:
            x_values = aligned[features_df.columns].to_numpy(dtype=float)
            y_values = aligned[label_name].to_numpy(dtype=float)

        for window in adjusted_windows:
            window_key = f"window_{window}"
            corr_matrix = self._rolling_corr_matrix(x_values, y_values, window, stride)
            for idx, feature in enumerate(features_df.columns):
                results[feature][window_key] = corr_matrix[:, idx].tolist()
        return results

    def compute_icir(self, rolling_ic_results: dict) -> dict[str, dict]:
        """ICIR = IC Mean / IC Std."""

        icir_results: dict[str, dict] = {}
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size == 0:
                ic_mean = np.nan
                ic_std = np.nan
                icir = np.nan
                hit_rate = np.nan
            else:
                ic_mean = float(np.nanmean(values))
                ic_std = float(np.nanstd(values))
                icir = float(ic_mean / ic_std) if ic_std > 0 else np.nan
                hit_rate = float(np.mean(values > 0))

            icir_results[feature] = {
                "ic_mean": ic_mean,
                "ic_std": ic_std,
                "icir": icir,
                "ic_hit_rate": hit_rate,
            }

        return icir_results

    def compute_ic_decay(
        self,
        features_df: pd.DataFrame,
        close: pd.Series,
        horizons: list[int],
        method: str = "spearman",
        return_type: str = "simple",
    ) -> dict[str, dict]:
        """IC Decay analysis."""

        horizon_results: dict[int, dict[str, float]] = {}
        for horizon in horizons:
            label = self._compute_returns(close, horizon, return_type)
            horizon_results[horizon] = self.compute_ic(features_df, label, method)

        results: dict[str, dict] = {}
        for feature in features_df.columns:
            ic_values = [horizon_results[h][feature] for h in horizons]
            decay_fit = self._fit_exponential_decay(horizons, ic_values)
            peak_horizon = self._select_peak_horizon(horizons, ic_values)
            results[feature] = {
                "horizons": horizons,
                "ic_values": ic_values,
                "half_life": decay_fit.get("half_life"),
                "peak_horizon": peak_horizon,
                "decay_rate": decay_fit.get("decay_rate"),
                "decay_type": decay_fit.get("decay_type"),
                "fit_r2": decay_fit.get("r2"),
                "fit_warning": decay_fit.get("fit_warning"),
                "fit_warning_reason": decay_fit.get("fit_warning_reason"),
            }

        return results

    def compute_grouped_ic(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        metadata: dict,
        config: dict,
    ) -> dict[str, dict]:
        """分組 IC 分析."""

        grouped_results: dict[str, dict] = {}
        config = config or self._grouped_config
        method = config.get("method", self._methods[0])

        features_df, label, raw_data = self._align_with_raw_data(
            features_df, label, raw_data
        )

        if config.get("by_year"):
            by_year = {}
            for year, idx in self._iter_time_groups(raw_data, "year"):
                by_year[str(year)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_year"] = by_year

        if config.get("by_quarter"):
            by_quarter = {}
            for quarter, idx in self._iter_time_groups(raw_data, "quarter"):
                by_quarter[str(quarter)] = self.compute_ic(
                    features_df.loc[idx], label.loc[idx], method
                )
            grouped_results["by_quarter"] = by_quarter

        if config.get("by_regime"):
            grouped_results["by_regime"] = self._compute_regime_groups(
                features_df, label, raw_data, config
            )

        if config.get("by_category"):
            grouped_results["by_category"] = self._compute_metadata_groups(
                features_df, label, metadata, "category", method
            )

        if config.get("by_data_source"):
            grouped_results["by_data_source"] = self._compute_metadata_groups(
                features_df, label, metadata, "data_source", method
            )

        if config.get("by_layer"):
            grouped_results["by_layer"] = self._compute_metadata_groups(
                features_df, label, metadata, "layer", method
            )

        return grouped_results

    def compute_ic_autocorrelation(
        self, rolling_ic_results: dict, lag: int = 1
    ) -> dict[str, float]:
        """IC autocorrelation (Lag-1)."""

        results: dict[str, float] = {}
        persistent_count = 0
        for feature, windows in rolling_ic_results.items():
            series = self._select_icir_series(windows)
            values = np.array(series, dtype=float)
            if values.size <= lag:
                results[feature] = np.nan
                continue
            if np.nanstd(values) == 0:
                results[feature] = np.nan
                continue
            value = float(np.corrcoef(values[:-lag], values[lag:])[0, 1])
            if value > 0.3:
                persistent_count += 1
            results[feature] = value
        if persistent_count > 0:
            logger.info("IC autocorr persistent: count=%s", persistent_count)
        return results

    @staticmethod
    def _fit_exponential_decay(
        horizons: list[int], ic_values: list[float]
    ) -> dict:
        """Fit IC(h) = A * exp(-lambda * h) + C."""

        x = np.array(horizons, dtype=float)
        y = np.array(ic_values, dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]

        if x.size < 3:
            logger.warning(
                "Decay fit skipped: insufficient points (n=%d). Results may be unreliable.",
                x.size,
            )
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "insufficient_points",
            }

        if np.nanstd(y) < 1e-8:
            logger.warning(
                "Decay fit skipped: IC variance too small. Results may be unreliable."
            )
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "low_variance",
            }

        def model(h, a, lam, c):
            return a * np.exp(-lam * h) + c

        try:
            params, _ = optimize.curve_fit(model, x, y, maxfev=2000)
            a, lam, c = params
            fitted = model(x, a, lam, c)
            ss_res = float(np.sum((y - fitted) ** 2))
            ss_tot = float(np.sum((y - np.mean(y)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            decay_type = "exponential" if r2 >= 0.5 else "non_exponential"
            fit_warning = decay_type != "exponential"
            fit_warning_reason = "low_r2" if fit_warning else None
            if decay_type != "exponential":
                logger.warning(
                    "Decay fit quality low (R2=%.3f). Results may be unreliable.",
                    r2,
                )
            half_life = float(np.log(2) / lam) if lam > 0 else np.nan
            return {
                "decay_rate": float(lam),
                "half_life": half_life,
                "decay_type": decay_type,
                "r2": float(r2),
                "fit_warning": fit_warning,
                "fit_warning_reason": fit_warning_reason,
            }
        except Exception as exc:
            logger.warning("Decay fit failed: %s", exc)
            return {
                "decay_rate": np.nan,
                "half_life": np.nan,
                "decay_type": "fit_failed",
                "r2": np.nan,
                "fit_warning": True,
                "fit_warning_reason": "fit_exception",
            }

    def _compute_pairwise_corr(
        self, series: pd.Series, label: pd.Series, method: str
    ) -> float:
        aligned = pd.concat([series, label], axis=1).dropna()
        if aligned.empty:
            return np.nan

        x = aligned.iloc[:, 0]
        y = aligned.iloc[:, 1]
        if np.nanstd(x) == 0 or np.nanstd(y) == 0:
            return np.nan
        if method == "pearson":
            return float(stats.pearsonr(x, y)[0])
        if method == "kendall":
            return float(stats.kendalltau(x, y)[0])
        if method != "spearman":
            logger.warning("Unknown IC method=%s, fallback to spearman", method)
        return float(stats.spearmanr(x, y)[0])

    def _compute_returns(
        self, close: pd.Series, horizon: int, return_type: str
    ) -> pd.Series:
        if return_type == "log":
            return np.log(close.shift(-horizon) / close)
        if return_type not in {"simple", "log"}:
            logger.warning("Unsupported return_type=%s, fallback to simple", return_type)
        return close.shift(-horizon) / close - 1

    def _select_icir_series(self, windows: dict) -> list[float]:
        if not windows:
            return []
        key = f"window_{self._icir_window}"
        if key in windows:
            return windows[key]
        for values in windows.values():
            return values
        return []

    def _iter_time_groups(self, raw_data: pd.DataFrame, mode: str):
        time_index = self._get_time_index(raw_data)
        if time_index is None:
            return []
        if mode == "year":
            groups = time_index.to_series().groupby(time_index.year).groups
            return [(key, idx) for key, idx in groups.items()]
        groups = time_index.to_series().groupby(
            [time_index.year, time_index.quarter]
        ).groups
        return [(f"{key[0]}Q{key[1]}", idx) for key, idx in groups.items()]

    def _get_time_index(self, raw_data: pd.DataFrame) -> Optional[pd.DatetimeIndex]:
        if isinstance(raw_data.index, pd.DatetimeIndex):
            return raw_data.index
        for col in ("open_time", "close_time", "timestamp"):
            if col in raw_data.columns:
                values = raw_data[col]
                if np.issubdtype(values.dtype, np.number):
                    return pd.to_datetime(values, unit="ms")
                return pd.to_datetime(values)
        return None

    def _compute_regime_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
        config: dict,
    ) -> dict[str, dict]:
        close = raw_data.get("close")
        if close is None:
            return {}
        close = close.reindex(features_df.index)
        ema_55 = close.ewm(span=55, adjust=False).mean()
        vol = close.pct_change(fill_method=None).rolling(55).std()

        regime_defs = config.get("regime_definitions", {})
        high_pct = regime_defs.get("high_vol_percentile", 80)
        low_pct = regime_defs.get("low_vol_percentile", 20)
        vol_values = vol.dropna()
        if vol_values.empty:
            return {}
        high_thresh = np.nanpercentile(vol_values, high_pct)
        low_thresh = np.nanpercentile(vol_values, low_pct)

        masks = {
            "bull": close > ema_55,
            "bear": close < ema_55,
            "high_vol": vol >= high_thresh,
            "low_vol": vol <= low_thresh,
        }

        results: dict[str, dict] = {}
        method = config.get("method", self._methods[0])
        for name, mask in masks.items():
            idx = mask[mask].index
            if len(idx) == 0:
                results[name] = {}
                continue
            results[name] = self.compute_ic(
                features_df.loc[idx], label.loc[idx], method
            )
        return results

    def _compute_metadata_groups(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        metadata: dict,
        key: str,
        method: str,
    ) -> dict[str, dict]:
        if not metadata:
            return {}
        group_map: dict[str, list[str]] = {}
        for feature in features_df.columns:
            meta = metadata.get(feature, {})
            value = meta.get(key)
            if value is None:
                continue
            group_map.setdefault(str(value), []).append(feature)

        results: dict[str, dict] = {}
        for group, features in group_map.items():
            results[group] = self.compute_ic(
                features_df[features], label, method
            )
        return results

    def _align_with_raw_data(
        self,
        features_df: pd.DataFrame,
        label: pd.Series,
        raw_data: pd.DataFrame,
    ) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
        if raw_data is None or raw_data.empty:
            return features_df, label, raw_data

        if (
            features_df.index.equals(raw_data.index)
            and label.index.equals(raw_data.index)
        ):
            return features_df, label, raw_data

        if len(features_df) == len(raw_data):
            features_df = features_df.copy()
            label = label.copy()
            features_df.index = raw_data.index
            label.index = raw_data.index
        else:
            raw_data = raw_data.reindex(features_df.index)

        return features_df, label, raw_data

    def _compute_vectorized_ic(
        self, features_df: pd.DataFrame, label: pd.Series, method: str
    ) -> dict[str, float]:
        if features_df.shape[0] < 2:
            return {feature: np.nan for feature in features_df.columns}
        if features_df.shape[1] == 1:
            feature = features_df.columns[0]
            value = self._compute_pairwise_corr(
                features_df[feature], label, method
            )
            return {feature: value}
        values = np.column_stack([label.values, features_df.values])
        if method == "pearson":
            corr = np.corrcoef(values, rowvar=False)
        else:
            corr = stats.spearmanr(values, axis=0).correlation
        ic_values = corr[0, 1:]
        return dict(zip(features_df.columns, ic_values.astype(float)))

    def _has_missing(self, features_df: pd.DataFrame, label: pd.Series) -> bool:
        if label.isna().any():
            return True
        return features_df.isna().any().any()

    def _adjust_rolling_windows(self, windows: list[int]) -> list[int]:
        if not self._timeframe:
            return windows

        reference = self._parse_timeframe_hours(self._reference_tf)
        current = self._parse_timeframe_hours(self._timeframe)
        if reference is None or current is None or current == 0:
            logger.warning("Invalid timeframe for rolling windows: %s", self._timeframe)
            return windows

        factor = reference / current
        adjusted = [max(int(round(window * factor)), 1) for window in windows]
        return adjusted

    def _parse_timeframe_hours(self, timeframe: str) -> Optional[float]:
        if not timeframe:
            return None
        unit = timeframe[-1].lower()
        try:
            value = float(timeframe[:-1])
        except ValueError:
            return None
        if unit == "h":
            return value
        if unit == "d":
            return value * 24
        if unit == "w":
            return value * 168
        return None

    def _rolling_spearman(
        self,
        series: pd.Series,
        label: pd.Series,
        window: int,
        stride: int,
    ) -> list[float]:
        values = series.values
        target = label.values
        results: list[float] = []
        for end in range(window, len(values) + 1, stride):
            x = values[end - window : end]
            y = target[end - window : end]
            if np.isnan(x).any() or np.isnan(y).any():
                continue
            if np.std(x) == 0 or np.std(y) == 0:
                results.append(np.nan)
                continue
            results.append(float(stats.spearmanr(x, y)[0]))
        return results

    @staticmethod
    def _rolling_corr_matrix(
        x_values: np.ndarray,
        y_values: np.ndarray,
        window: int,
        stride: int,
    ) -> np.ndarray:
        if window <= 1:
            return np.empty((0, x_values.shape[1]))

        n_rows = x_values.shape[0]
        if n_rows < window:
            return np.empty((0, x_values.shape[1]))

        x = x_values.astype(float, copy=False)
        y = y_values.astype(float, copy=False)
        n_features = x.shape[1]

        csum_x = np.vstack([np.zeros((1, n_features)), np.cumsum(x, axis=0)])
        csum_x2 = np.vstack([np.zeros((1, n_features)), np.cumsum(x * x, axis=0)])
        csum_xy = np.vstack([np.zeros((1, n_features)), np.cumsum(x * y[:, None], axis=0)])
        csum_y = np.concatenate(([0.0], np.cumsum(y)))
        csum_y2 = np.concatenate(([0.0], np.cumsum(y * y)))

        starts = np.arange(0, n_rows - window + 1, stride)
        ends = starts + window

        sum_x = csum_x[ends] - csum_x[starts]
        sum_x2 = csum_x2[ends] - csum_x2[starts]
        sum_xy = csum_xy[ends] - csum_xy[starts]
        sum_y = csum_y[ends] - csum_y[starts]
        sum_y2 = csum_y2[ends] - csum_y2[starts]

        window_size = float(window)
        cov_num = sum_xy - (sum_x * sum_y[:, None]) / window_size
        var_x = sum_x2 - (sum_x * sum_x) / window_size
        var_y = sum_y2 - (sum_y * sum_y) / window_size
        denom = np.sqrt(var_x * var_y[:, None])
        with np.errstate(divide="ignore", invalid="ignore"):
            corr = cov_num / denom
        corr[~np.isfinite(corr)] = np.nan
        return corr

    def _select_peak_horizon(
        self, horizons: list[int], ic_values: list[float]
    ) -> int:
        values = np.array(ic_values, dtype=float)
        if np.isfinite(values).any():
            return horizons[int(np.nanargmax(np.abs(values)))]
        return horizons[0]
