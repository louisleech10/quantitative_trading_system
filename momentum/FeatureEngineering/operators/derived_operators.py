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
        denom = indicator.replace(0, np.nan)
        return (price - indicator) / denom

    def compute_cross(self, fast: pd.Series, slow: pd.Series, name_prefix: str) -> pd.Series:
        """fast - slow"""
        return fast - slow

    def compute_momentum(self, series: pd.Series, lags: List[int], name_prefix: str) -> pd.DataFrame:
        """(Value[t] - Value[t-n]) / Value[t-n]"""
        frames: List[pd.Series] = []
        for lag in lags:
            denom = series.shift(lag).replace(0, np.nan)
            momentum = (series - series.shift(lag)) / denom
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
        return series.rolling(window).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)

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
            series = layer1_df[col]
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
                if operator_name == "Cross":
                    series = self.compute_cross(layer1_df[fast.name], layer1_df[slow.name], fast.name)
                else:
                    series = self.compute_ratio(layer1_df[fast.name], layer1_df[slow.name], fast.name)
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
        frames: List[pd.DataFrame] = []
        for col, info in feature_info.items():
            if not self._matches_apply_to(info, apply_to):
                continue
            frames.append(self.compute_momentum(layer1_df[col], lags, col))
        frames = [frame for frame in frames if not frame.empty]
        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

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
                series = self.compute_binary_signal(layer1_df[col], condition, col)
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
            series = self.transform_sign(layer1_df[col]) * self.transform_abs(layer1_df[col])
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
        corr_with = config.get("corr_with")
        clip_bounds = config.get("clip", {"lower": -3.0, "upper": 3.0})

        frames: List[pd.Series] = []
        for col, info in feature_info.items():
            if not self._matches_apply_to(info, apply_to):
                continue
            series = layer1_df[col]
            for window in windows:
                if "ts_argmax" in operators:
                    frames.append(self.ts_argmax(series, window).rename(f"{col}_TsArgmax_W{window}"))
                if "ts_argmin" in operators:
                    frames.append(self.ts_argmin(series, window).rename(f"{col}_TsArgmin_W{window}"))
                if "ts_rank" in operators:
                    frames.append(self.ts_rank(series, window).rename(f"{col}_TsRank_W{window}"))
                if "decay_linear" in operators:
                    frames.append(self.decay_linear(series, window).rename(f"{col}_DecayLinear_W{window}"))
                if "ts_corr" in operators and corr_with in raw_data.columns:
                    corr_series = self.ts_corr(series, raw_data[corr_with], window)
                    frames.append(corr_series.rename(f"{col}_TsCorr_{corr_with}_W{window}"))

            if "sign" in transforms:
                frames.append(self.transform_sign(series).rename(f"{col}_Sign"))
            if "log1p" in transforms:
                frames.append(self.transform_log1p(series).rename(f"{col}_Log1p"))
            if "abs" in transforms:
                frames.append(self.transform_abs(series).rename(f"{col}_Abs"))
            if "clip" in transforms:
                lower = float(clip_bounds.get("lower", -3.0))
                upper = float(clip_bounds.get("upper", 3.0))
                frames.append(self.transform_clip(series, lower, upper).rename(f"{col}_Clip"))

        if not frames:
            return pd.DataFrame(index=layer1_df.index)
        return pd.concat(frames, axis=1)

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
                params = self._coerce_params(spec.get("params"))
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
