from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from momentum.core.logging import get_logger


logger = get_logger(__name__)


@dataclass
class FeatureInfo:
    name: str
    source: str
    category: Optional[str]
    indicator: Optional[str]
    params: List[float]


class DerivedOperatorEngine:
    """Layer 2: derived feature generation.

    Operators:
      Distance, Cross, Momentum, Ratio, Binary Signal, Signed Strength

    WorldQuant-style time-series operators:
      ts_argmax, ts_argmin, ts_corr, ts_rank, decay_linear
      sign, log1p, abs, clip
    """

    def __init__(self, config: Dict | None) -> None:
        self._config = self._normalize_config(config)
        self._duplicate_series_warnings: set[str] = set()

    def compute_all(
        self,
        layer1_df: pd.DataFrame,
        raw_data: pd.DataFrame,
        indicator_specs: Optional[Dict[str, Dict]] = None,
    ) -> pd.DataFrame:
        if layer1_df.empty:
            return pd.DataFrame(index=layer1_df.index)

        feature_info = self._build_feature_info(layer1_df.columns, indicator_specs)
        frames: List[pd.DataFrame] = []

        distance_cfg = self._get_section("distance")
        if distance_cfg.get("enabled", False):
            frames.append(self._apply_distance(layer1_df, raw_data, feature_info, distance_cfg))

        cross_cfg = self._get_section("cross")
        if cross_cfg.get("enabled", False):
            frames.append(self._apply_pair_operator(layer1_df, feature_info, "Cross"))

        ratio_cfg = self._get_section("ratio")
        if ratio_cfg.get("enabled", False):
            frames.append(self._apply_pair_operator(layer1_df, feature_info, "Ratio"))

        momentum_cfg = self._get_section("momentum")
        if not momentum_cfg:
            momentum_cfg = self._get_section("momentum_change")
        if momentum_cfg.get("enabled", False):
            frames.append(self._apply_momentum(layer1_df, feature_info, momentum_cfg))

        binary_cfg = self._get_section("binary_signal")
        if binary_cfg.get("enabled", False):
            frames.append(self._apply_binary_signal(layer1_df, feature_info, binary_cfg))

        signed_cfg = self._get_section("signed_strength")
        if signed_cfg.get("enabled", False):
            frames.append(self._apply_signed_strength(layer1_df, feature_info, signed_cfg))

        worldquant_cfg = self._get_section("worldquant")
        if worldquant_cfg.get("enabled", False):
            frames.append(self._apply_worldquant(layer1_df, raw_data, feature_info, worldquant_cfg))

        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(index=layer1_df.index)

        return pd.concat(frames, axis=1)

    def compute_distance(self, price: pd.Series, indicator: pd.Series, name_prefix: str) -> pd.Series:
        """(Price - Indicator) / Indicator"""
        aligned_price, aligned_indicator = self._align_pair_series(
            left=price,
            right=indicator,
            left_name=f"{name_prefix}:price",
            right_name=f"{name_prefix}:indicator",
        )
        denom = aligned_indicator.replace(0, np.nan)
        return (aligned_price - aligned_indicator) / denom

    def compute_cross(self, fast: pd.Series, slow: pd.Series, name_prefix: str) -> pd.Series:
        """fast - slow"""
        return fast - slow

    def compute_momentum(self, series: pd.Series, lags: List[int], name_prefix: str) -> pd.DataFrame:
        """(Value[t] - Value[t-n]) / Value[t-n]"""
        frames: List[pd.Series] = []
        for lag in lags:
            shifted = series.shift(lag)
            denom = shifted.replace(0, np.nan)
            momentum = (series - shifted) / denom
            frames.append(momentum.rename(f"{name_prefix}_Momentum_L{lag}"))
        if not frames:
            return pd.DataFrame(index=series.index)
        return pd.concat(frames, axis=1)

    def compute_ratio(self, a: pd.Series, b: pd.Series, name_prefix: str) -> pd.Series:
        """A / B"""
        denom = b.replace(0, np.nan)
        return a / denom

    def compute_binary_signal(self, series: pd.Series, condition: str, name_prefix: str) -> pd.Series:
        """1 if condition else 0"""
        operator, threshold = self._parse_condition(condition)
        if operator == ">":
            mask = series > threshold
        elif operator == ">=":
            mask = series >= threshold
        elif operator == "<":
            mask = series < threshold
        elif operator == "<=":
            mask = series <= threshold
        elif operator == "==":
            mask = series == threshold
        else:
            mask = pd.Series(False, index=series.index)
        return mask.astype(int)

    def ts_argmax(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling window max position (0-based)."""
        return series.rolling(window).apply(lambda x: x.argmax(), raw=True)

    def ts_argmin(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling window min position (0-based)."""
        return series.rolling(window).apply(lambda x: x.argmin(), raw=True)

    def ts_corr(self, a: pd.Series, b: pd.Series, window: int) -> pd.Series:
        """Rolling correlation."""
        return a.rolling(window).corr(b)

    def ts_rank(self, series: pd.Series, window: int) -> pd.Series:
        """Rolling percentile rank (0-1)."""
        return series.rolling(window).apply(self._rolling_last_rank_pct, raw=True)

    def decay_linear(self, series: pd.Series, window: int) -> pd.Series:
        """Linearly decaying weighted average."""
        weights = np.arange(1, window + 1, dtype=float)
        weights /= weights.sum()
        return series.rolling(window).apply(lambda x: np.dot(x, weights), raw=True)

    def transform_sign(self, series: pd.Series) -> pd.Series:
        return np.sign(series)

    def transform_log1p(self, series: pd.Series) -> pd.Series:
        return np.log1p(np.abs(series)) * np.sign(series)

    def transform_abs(self, series: pd.Series) -> pd.Series:
        return np.abs(series)

    def transform_clip(self, series: pd.Series, lower: float = -3.0, upper: float = 3.0) -> pd.Series:
        return series.clip(lower, upper)

    def _apply_distance(
        self,
        layer1_df: pd.DataFrame,
        raw_data: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        config: Dict,
    ) -> pd.DataFrame:
        apply_to = config.get("apply_to", "all")
        frames: List[pd.Series] = []
        for col, info in feature_info.items():
            if not self._matches_apply_to(info, apply_to):
                continue
            if info.source not in raw_data.columns:
                continue
            series = self._select_feature_series(layer1_df, col)
            price = raw_data[info.source]
            distance = self.compute_distance(price, series, col)
            frames.append(distance.rename(f"{col}_Distance"))
        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

    def _apply_pair_operator(
        self,
        layer1_df: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        operator_name: str,
    ) -> pd.DataFrame:
        grouped: Dict[tuple, List[FeatureInfo]] = {}
        for info in feature_info.values():
            if not info.params or len(info.params) != 1:
                continue
            key = (info.source, info.category, info.indicator)
            grouped.setdefault(key, []).append(info)

        frames: List[pd.Series] = []
        for key, infos in grouped.items():
            infos_sorted = sorted(infos, key=lambda item: item.params[0])
            for fast, slow in zip(infos_sorted[:-1], infos_sorted[1:]):
                fast_series = self._select_feature_series(layer1_df, fast.name)
                slow_series = self._select_feature_series(layer1_df, slow.name)
                if operator_name == "Cross":
                    series = self.compute_cross(fast_series, slow_series, fast.name)
                else:
                    series = self.compute_ratio(fast_series, slow_series, fast.name)
                param_str = self._format_params([fast.params[0], slow.params[0]])
                col_name = f"{fast.source}_{fast.category}_{fast.indicator}_{param_str}_{operator_name}"
                frames.append(series.rename(col_name))

        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

    def _apply_momentum(
        self,
        layer1_df: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        config: Dict,
    ) -> pd.DataFrame:
        apply_to = config.get("apply_to", "all")
        lags = [int(lag) for lag in config.get("lags", [3, 5, 8])]
        selected_cols = [
            col for col, info in feature_info.items() if self._matches_apply_to(info, apply_to)
        ]
        if not selected_cols:
            return pd.DataFrame(index=layer1_df.index)

        selected = self._build_selected_frame(layer1_df, selected_cols)
        frames: List[pd.DataFrame] = []
        for lag in lags:
            shifted = selected.shift(lag)
            denom = shifted.replace(0, np.nan)
            momentum = (selected - shifted) / denom
            momentum.columns = [f"{col}_Momentum_L{lag}" for col in selected_cols]
            frames.append(momentum)
        result = pd.concat(frames, axis=1)
        expected_cols = [f"{col}_Momentum_L{lag}" for col in selected_cols for lag in lags]
        return result.loc[:, expected_cols]

    def _apply_binary_signal(
        self,
        layer1_df: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        config: Dict,
    ) -> pd.DataFrame:
        rules = config.get("rules", [])
        frames: List[pd.Series] = []
        for rule in rules:
            indicator = rule.get("indicator")
            condition = rule.get("condition")
            suffix = rule.get("name_suffix")
            if not indicator or not condition:
                continue
            for col, info in feature_info.items():
                if not info.indicator:
                    continue
                if info.indicator != indicator and not info.indicator.startswith(f"{indicator}_"):
                    continue
                feature_series = self._select_feature_series(layer1_df, col)
                series = self.compute_binary_signal(feature_series, condition, col)
                name_suffix = f"_{suffix}" if suffix else ""
                frames.append(series.rename(f"{col}_BinarySignal{name_suffix}"))

        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

    def _apply_signed_strength(
        self,
        layer1_df: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        config: Dict,
    ) -> pd.DataFrame:
        apply_to = config.get("apply_to", "all")
        frames: List[pd.Series] = []
        for col, info in feature_info.items():
            if not self._matches_apply_to(info, apply_to):
                continue
            feature_series = self._select_feature_series(layer1_df, col)
            series = self.transform_sign(feature_series) * self.transform_abs(feature_series)
            frames.append(series.rename(f"{col}_SignedStrength"))
        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

    def _apply_worldquant(
        self,
        layer1_df: pd.DataFrame,
        raw_data: pd.DataFrame,
        feature_info: Dict[str, FeatureInfo],
        config: Dict,
    ) -> pd.DataFrame:
        apply_to = config.get("apply_to", "all")
        windows = [int(window) for window in config.get("windows", [5, 13, 21])]
        transforms = config.get("transforms", ["sign", "log1p", "abs", "clip"])
        operators = config.get(
            "operators",
            ["ts_argmax", "ts_argmin", "ts_rank", "decay_linear"],
        )
        operator_set = set(operators)
        transform_set = set(transforms)
        corr_with = config.get("corr_with")
        clip_bounds = config.get("clip", {"lower": -3.0, "upper": 3.0})
        lower = float(clip_bounds.get("lower", -3.0))
        upper = float(clip_bounds.get("upper", 3.0))
        has_corr = "ts_corr" in operator_set and corr_with in raw_data.columns

        selected_cols = [
            col for col, info in feature_info.items() if self._matches_apply_to(info, apply_to)
        ]
        if not selected_cols:
            return pd.DataFrame(index=layer1_df.index)

        selected = self._build_selected_frame(layer1_df, selected_cols)

        frames: List[pd.DataFrame] = []
        for window in windows:
            rolling = selected.rolling(window)

            if "ts_argmax" in operator_set:
                argmax_df = rolling.apply(np.argmax, raw=True)
                argmax_df.columns = [f"{col}_TsArgmax_W{window}" for col in selected_cols]
                frames.append(argmax_df)

            if "ts_argmin" in operator_set:
                argmin_df = rolling.apply(np.argmin, raw=True)
                argmin_df.columns = [f"{col}_TsArgmin_W{window}" for col in selected_cols]
                frames.append(argmin_df)

            if "ts_rank" in operator_set:
                # rolling.rank keeps pandas rank(method='average', pct=True) semantics.
                rank_df = rolling.rank(method="average", pct=True)
                rank_df.columns = [f"{col}_TsRank_W{window}" for col in selected_cols]
                frames.append(rank_df)

            if "decay_linear" in operator_set:
                weights = np.arange(1, window + 1, dtype=float)
                weights /= weights.sum()

                def _decay_fn(arr: np.ndarray, _weights: np.ndarray = weights) -> float:
                    return float(np.dot(arr, _weights))

                decay_df = rolling.apply(_decay_fn, raw=True)
                decay_df.columns = [f"{col}_DecayLinear_W{window}" for col in selected_cols]
                frames.append(decay_df)

            if has_corr and corr_with is not None:
                corr_ref = raw_data[corr_with].reindex(selected.index)
                corr_df = rolling.corr(corr_ref)
                corr_df.columns = [f"{col}_TsCorr_{corr_with}_W{window}" for col in selected_cols]
                frames.append(corr_df)

        if "sign" in transform_set:
            sign_df = np.sign(selected)
            sign_df.columns = [f"{col}_Sign" for col in selected_cols]
            frames.append(sign_df)

        if "log1p" in transform_set:
            log1p_df = np.log1p(np.abs(selected)) * np.sign(selected)
            log1p_df.columns = [f"{col}_Log1p" for col in selected_cols]
            frames.append(log1p_df)

        if "abs" in transform_set:
            abs_df = np.abs(selected)
            abs_df.columns = [f"{col}_Abs" for col in selected_cols]
            frames.append(abs_df)

        if "clip" in transform_set:
            clip_df = selected.clip(lower=lower, upper=upper)
            clip_df.columns = [f"{col}_Clip" for col in selected_cols]
            frames.append(clip_df)

        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        result = pd.concat(frames, axis=1)

        expected_cols: List[str] = []
        for col in selected_cols:
            for window in windows:
                if "ts_argmax" in operator_set:
                    expected_cols.append(f"{col}_TsArgmax_W{window}")
                if "ts_argmin" in operator_set:
                    expected_cols.append(f"{col}_TsArgmin_W{window}")
                if "ts_rank" in operator_set:
                    expected_cols.append(f"{col}_TsRank_W{window}")
                if "decay_linear" in operator_set:
                    expected_cols.append(f"{col}_DecayLinear_W{window}")
                if has_corr and corr_with is not None:
                    expected_cols.append(f"{col}_TsCorr_{corr_with}_W{window}")

            if "sign" in transform_set:
                expected_cols.append(f"{col}_Sign")
            if "log1p" in transform_set:
                expected_cols.append(f"{col}_Log1p")
            if "abs" in transform_set:
                expected_cols.append(f"{col}_Abs")
            if "clip" in transform_set:
                expected_cols.append(f"{col}_Clip")

        return result.loc[:, expected_cols]

    def _build_selected_frame(self, frame: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        series_list = [self._select_feature_series(frame, col) for col in columns]
        selected = pd.concat(series_list, axis=1)
        selected.columns = columns
        return selected

    def _normalize_config(self, config: Dict | None) -> Dict:
        if config is None:
            return {}
        if hasattr(config, "model_dump"):
            return config.model_dump(by_alias=True)
        if isinstance(config, dict):
            return config
        return dict(config)

    def _get_section(self, key: str) -> Dict:
        section = self._config.get(key)
        if section is None and key == "momentum_change":
            section = self._config.get("momentum")
        if section is None:
            return {}
        if hasattr(section, "model_dump"):
            return section.model_dump(by_alias=True)
        if isinstance(section, dict):
            return section
        return dict(section)

    def _build_feature_info(
        self,
        columns: Iterable[str],
        indicator_specs: Optional[Dict[str, Dict]],
    ) -> Dict[str, FeatureInfo]:
        info_map: Dict[str, FeatureInfo] = {}
        for name in columns:
            if indicator_specs and name in indicator_specs:
                spec = indicator_specs[name]
                raw_params = spec.get("params")
                # indicator_specs passes params as a dict (e.g. {"timeperiod": 21});
                # _coerce_params needs numeric values, not key strings.
                if isinstance(raw_params, dict):
                    params = self._coerce_params(raw_params.values())
                else:
                    params = self._coerce_params(raw_params)
                info_map[name] = FeatureInfo(
                    name=name,
                    source=spec.get("source", ""),
                    category=spec.get("category"),
                    indicator=spec.get("indicator"),
                    params=params,
                )
                continue
            info_map[name] = self._parse_feature_name(name)
        return info_map

    def _parse_feature_name(self, name: str) -> FeatureInfo:
        parts = name.split("_")
        source = parts[0] if parts else name
        category = parts[1] if len(parts) > 1 else None
        remainder = parts[2:] if len(parts) > 2 else []

        param_tokens: List[float] = []
        while remainder and self._is_number(remainder[-1]):
            token = remainder.pop()
            value = float(token)
            if value.is_integer():
                value = int(value)
            param_tokens.insert(0, float(value))

        indicator = "_".join(remainder) if remainder else None
        return FeatureInfo(name=name, source=source, category=category, indicator=indicator, params=param_tokens)

    def _matches_apply_to(self, info: FeatureInfo, apply_to: str | List[str]) -> bool:
        if apply_to == "all" or apply_to is None:
            return True
        if isinstance(apply_to, list):
            return any(self._match_token(info, token) for token in apply_to)
        if isinstance(apply_to, str):
            if apply_to.startswith("all_"):
                return info.category == apply_to.replace("all_", "")
            if info.category and apply_to == info.category:
                return True
            try:
                return re.search(apply_to, info.name) is not None
            except re.error:
                return apply_to in info.name
        return False

    def _match_token(self, info: FeatureInfo, token: str) -> bool:
        if info.category and token == info.category:
            return True
        return token in info.name

    def _parse_condition(self, condition: str) -> tuple[str, float]:
        match = re.match(r"(>=|<=|==|>|<)\s*(-?\d+(?:\.\d+)?)", condition.strip())
        if not match:
            return "", 0.0
        return match.group(1), float(match.group(2))

    def _format_params(self, params: List[float]) -> str:
        parts = []
        for value in params:
            if isinstance(value, float) and value.is_integer():
                parts.append(str(int(value)))
            else:
                parts.append(str(value))
        return "_".join(parts)

    def _is_number(self, value: str) -> bool:
        return re.match(r"^-?\d+(?:\.\d+)?$", value) is not None

    def _coerce_params(self, params: Optional[Iterable]) -> List[float]:
        if not params:
            return []
        output: List[float] = []
        for item in params:
            try:
                value = float(item)
            except (TypeError, ValueError):
                continue
            output.append(value)
        return output

    def _rolling_last_rank_pct(self, values: np.ndarray) -> float:
        """Return pandas-equivalent percentile rank of the last value in the rolling window."""
        last = values[-1]
        if np.isnan(last):
            return np.nan

        valid_mask = ~np.isnan(values)
        valid_count = int(valid_mask.sum())
        if valid_count == 0:
            return np.nan

        valid_values = values[valid_mask]
        less_count = int(np.sum(valid_values < last))
        equal_count = int(np.sum(valid_values == last))

        # pandas rank(method='average', pct=True) for the last value.
        average_rank = less_count + (equal_count + 1) / 2.0
        return average_rank / float(valid_count)

    def _select_feature_series(self, frame: pd.DataFrame, column_name: str) -> pd.Series:
        """Return a single feature series even when duplicate column names exist."""
        selected = frame[column_name]
        if isinstance(selected, pd.Series):
            return selected

        if column_name not in self._duplicate_series_warnings:
            logger.warning(
                "Feature '%s' has duplicated columns (%d copies), using last column for derived operations",
                column_name,
                selected.shape[1],
            )
            self._duplicate_series_warnings.add(column_name)

        series = selected.iloc[:, -1]
        series.name = column_name
        return series

    def _align_pair_series(
        self,
        left: pd.Series,
        right: pd.Series,
        left_name: str,
        right_name: str,
    ) -> tuple[pd.Series, pd.Series]:
        """Deduplicate indexes and align left series to right series index."""
        left_normalized = self._deduplicate_index(left, left_name)
        right_normalized = self._deduplicate_index(right, right_name)

        if not left_normalized.index.equals(right_normalized.index):
            logger.warning(
                "Index mismatch between %s and %s, aligning %s to %s index",
                left_name,
                right_name,
                left_name,
                right_name,
            )
            left_normalized = left_normalized.reindex(right_normalized.index)

        return left_normalized, right_normalized

    def _deduplicate_index(self, series: pd.Series, series_name: str) -> pd.Series:
        """Drop duplicated index labels consistently using keep='last'."""
        if not series.index.has_duplicates:
            return series

        duplicate_count = int(series.index.duplicated(keep="last").sum())
        logger.warning(
            "%s contains duplicated index labels, dropping %d rows (keep='last')",
            series_name,
            duplicate_count,
        )
        return series[~series.index.duplicated(keep="last")]
