from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

import yaml

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.parameter_generator import ParameterGenerator
from momentum.FeatureEngineering.feature_config import (
    EntropyConfig,
    FactoryConfig,
    FeatureCountPreview,
    MicrostructureConfig,
    PreprocessingConfig,
    TailRiskConfig,
    ValidationResult,
)

logger = get_logger(__name__)

LEGACY_SOURCE_ALIASES = {
    "avg_price": "avg-price",
    "med_price": "med-price",
    "typ_price": "typ-price",
    "wcl_price": "wcl-price",
}

# Indicators that return more than one output column per parameter combination.
# All others default to 1.
_INDICATOR_OUTPUT_COUNTS: Dict[str, int] = {
    "MACD":     3,  # Line / Signal / Hist
    "MACDEXT":  3,
    "MACDFIX":  3,
    "BBANDS":   3,  # Upper / Middle / Lower
    "HT_PHASOR": 2,  # InPhase / Quadrature
    "HT_SINE":  2,  # Sine / LeadSine
    "MAMA":     2,  # MAMA / FAMA
    "STOCH":    2,  # slowk / slowd
    "STOCHF":   2,  # fastk / fastd
    "STOCHRSI": 2,  # fastk / fastd
    "AROON":    2,  # aroondown / aroonup
}

SPECIAL_CATEGORY_FEATURE_DEFAULTS = {
    "microstructure": [
        "amihud",
        "kyle_lambda",
        "roll_spread",
        "cs_spread",
        "ofi",
        "large_trade_ratio",
        "vpin",
    ],
    "entropy": [
        "shannon",
        "approximate",
        "sample",
        "hurst",
        "fractal",
        "permutation",
    ],
    "tail_risk": [
        "cvar",
        "realized_vol_up",
        "realized_vol_down",
        "rsj",
        "updown_vol_ratio",
        "gain_pain_ratio",
        "jarque_bera",
        "max_drawdown",
    ],
}


class ConfigManager:
    """Three-layer configuration manager: default < user < API override."""

    def __init__(
        self,
        default_config_path: str = "config/scan_config.yaml",
        user_config_path: str = "config/user_scan_config.yaml",
    ) -> None:
        self._default_config_path = default_config_path
        self._user_config_path = user_config_path

    def get_merged_config(self, api_override: Optional[Dict[str, Any]] = None) -> FactoryConfig:
        """Merge three layers and return a validated FactoryConfig."""
        base_config = self._load_yaml(self._default_config_path, required=True)
        user_config = self._load_yaml(self._user_config_path, required=False)
        merged = self.deep_merge(base_config, user_config)
        if api_override:
            merged = self.deep_merge(merged, api_override)
        merged = self.migrate_config(merged)
        merged = self._normalize_data_source_aliases(merged)
        try:
            return FactoryConfig.model_validate(merged)
        except Exception as exc:
            logger.error("Failed to validate merged config", exc_info=True)
            raise exc

    @staticmethod
    def migrate_config(raw_config: Dict[str, Any]) -> Dict[str, Any]:
        """將舊格式 config 自動轉為新格式（向後相容遷移）。

        Transformations:
        0. global_settings → global  (API/frontend 使用 field name；YAML 使用 alias)
        1. rolling_aggregation.aggregators: list[str] → dict[str, {enabled: True}]
        2. cross_sectional.features: list[str] → dict[str, {enabled: True}]
        3. microstructure.enabled_features: list → features dict
        4. entropy/tail_risk/microstructure 若缺少 features，補齊預設 features dict
        """
        config = raw_config  # in-place is fine; caller already deep-copied

        # 0. Normalize Pydantic field-name key "global_settings" → alias "global"
        #    FactoryConfig uses Field(alias="global"), so YAML stores it under "global".
        #    The frontend/API sends the TypeScript camelCase key "global_settings".
        #    After deep_merge both keys coexist; Pydantic would silently use the alias
        #    and ignore "global_settings", making slider changes ineffective.
        #    Fix: merge "global_settings" into "global" so user overrides take effect.
        if "global_settings" in config:
            override_gs = config.pop("global_settings")
            if isinstance(override_gs, dict):
                base_gs = config.get("global")
                if isinstance(base_gs, dict):
                    config["global"] = {**base_gs, **override_gs}
                else:
                    config["global"] = override_gs

        # 1. Rolling aggregation aggregators: list → dict
        rolling = config.get("rolling_aggregation")
        if isinstance(rolling, dict):
            agg = rolling.get("aggregators")
            if isinstance(agg, list):
                rolling["aggregators"] = {name: {"enabled": True} for name in agg}

        # 2. Cross-sectional features: list → dict
        cs = config.get("cross_sectional")
        if isinstance(cs, dict):
            feats = cs.get("features")
            if isinstance(feats, list):
                cs["features"] = {name: {"enabled": True} for name in feats}

        # 2.5 Timeframes alignment_mode backward compatibility
        timeframes = config.get("timeframes")
        if isinstance(timeframes, dict):
            alignment_mode = timeframes.get("alignment_mode")
            if alignment_mode is None:
                timeframes["alignment_mode"] = "open_minus"
            elif alignment_mode not in {"open_minus", "close_time"}:
                logger.warning(
                    "Unknown alignment_mode '%s', fallback to open_minus",
                    alignment_mode,
                )
                timeframes["alignment_mode"] = "open_minus"

        # 3. Microstructure enabled_features → features dict
        atomic = config.get("atomic_indicators")
        if isinstance(atomic, dict):
            ms = atomic.get("microstructure")
            if isinstance(ms, dict) and "features" not in ms:
                ef = ms.get("enabled_features")
                if isinstance(ef, list):
                    ms["features"] = {name: {"enabled": True} for name in ef}
                elif ef == "all":
                    ms["features"] = {
                        name: {"enabled": True}
                        for name in SPECIAL_CATEGORY_FEATURE_DEFAULTS["microstructure"]
                    }

            # 4. Entropy/TailRisk (and fallback for microstructure) ensure features dict is present
            for special_key, default_names in SPECIAL_CATEGORY_FEATURE_DEFAULTS.items():
                special_cfg = atomic.get(special_key)
                if not isinstance(special_cfg, dict):
                    continue
                features = special_cfg.get("features")
                if not isinstance(features, dict):
                    features = {}

                # Keep legacy microstructure allow-list semantics:
                # when enabled_features is a list AND features dict is not already
                # populated, build features from enabled_features. If both exist,
                # the explicit features dict takes priority (user intent wins over
                # legacy field). See test_edge_case_6_microstructure_features_dict_takes_priority.
                if special_key == "microstructure":
                    ef = special_cfg.get("enabled_features")
                    user_features = special_cfg.get("features")
                    if isinstance(user_features, dict) and user_features:
                        # User explicitly populated features → respect verbatim,
                        # do NOT fill defaults (only listed indicators run).
                        continue
                    if isinstance(ef, list):
                        special_cfg["features"] = {name: {"enabled": True} for name in ef}
                        continue

                # Default behavior: ensure the category has a complete features map for UI/schema.
                merged_features: Dict[str, Dict[str, Any]] = {
                    name: {"enabled": True} for name in default_names
                }
                for name, cfg in features.items():
                    if isinstance(cfg, dict):
                        merged_features[name] = {"enabled": cfg.get("enabled", True), **cfg}
                    else:
                        merged_features[name] = {"enabled": True}

                special_cfg["features"] = merged_features

        return config

    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate config keys, indicator names, and period ranges."""
        errors: List[str] = []
        warnings: List[str] = []

        base_config = self._load_yaml(self._default_config_path, required=True)
        merged = self.deep_merge(base_config, config or {})
        merged = self._normalize_data_source_aliases(merged)

        errors.extend(self._validate_json_schema(merged))

        allowed_sources = {
            "close",
            "open",
            "high",
            "low",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_volume",
            "taker_ratio",
            "avg-price",
            "med-price",
            "typ-price",
            "wcl-price",
            "funding_rate",
            "open_interest",
        }
        enabled_sources = (
            merged.get("data_sources", {}).get("enabled_sources", []) if isinstance(merged, dict) else []
        )
        for source in enabled_sources:
            if source not in allowed_sources:
                errors.append(f"Unknown data source: {source}")

        allowed_indicators = self._collect_allowed_indicators(base_config)
        atomic_config = merged.get("atomic_indicators", {}) if isinstance(merged, dict) else {}
        for category, category_config in atomic_config.items():
            if not isinstance(category_config, dict):
                continue
            indicators = category_config.get("indicators", [])
            for indicator in indicators:
                if not isinstance(indicator, dict):
                    continue
                name = indicator.get("name")
                if name and name not in allowed_indicators:
                    errors.append(f"Unknown indicator name: {name}")
                period_errors = self._validate_period_values(indicator)
                errors.extend(period_errors)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def _validate_json_schema(self, config: Dict[str, Any]) -> List[str]:
        try:
            schema = FactoryConfig.model_json_schema(by_alias=True)
            validator = Draft202012Validator(schema)
            return [self._format_schema_error(error) for error in validator.iter_errors(config)]
        except Exception as exc:
            logger.error("JSON Schema validation failed", exc_info=True)
            return [f"JSON Schema validation error: {exc}"]

    @staticmethod
    def _format_schema_error(error: Exception) -> str:
        path = getattr(error, "path", None)
        if path:
            location = ".".join(str(part) for part in path)
        else:
            location = "$"
        message = getattr(error, "message", str(error))
        return f"JSON Schema: {location}: {message}"

    def preview_feature_count(self, config: FactoryConfig) -> FeatureCountPreview:
        """Estimate feature counts, time, and memory usage."""
        config_dict = config.model_dump(by_alias=True)
        atomic_counts = self._estimate_atomic_counts(config_dict)
        atomic_total = sum(atomic_counts.values())

        operators_cfg = config_dict.get("operators", {})
        rolling_cfg = config_dict.get("rolling_aggregation", {})
        lag_cfg = config_dict.get("lag_features", {})
        meta_cfg = config_dict.get("meta_features", {})
        cross_cfg = config_dict.get("cross_sectional", {})
        labels_cfg = config_dict.get("labels", {})

        derived_count = self._estimate_derived_count(atomic_total, atomic_counts, operators_cfg)
        rolling_count = self._estimate_rolling_count(atomic_total, rolling_cfg)
        lag_count = self._estimate_lag_count(atomic_total, lag_cfg, config_dict)
        cross_count = self._estimate_cross_count(cross_cfg)
        meta_count = self._estimate_meta_count(meta_cfg)
        label_count = self._estimate_label_count(labels_cfg)

        microstructure_count = 0
        entropy_count = 0
        tail_risk_count = 0
        if config.atomic_indicators.microstructure.enabled:
            full_ms = self._estimate_microstructure_features(
                config.atomic_indicators.microstructure
            )
            microstructure_count = self._apply_feature_filter_ratio(
                full_ms, config.atomic_indicators.microstructure.features, 7
            )
        if config.atomic_indicators.entropy.enabled:
            full_ent = self._estimate_entropy_features(config.atomic_indicators.entropy)
            entropy_count = self._apply_feature_filter_ratio(
                full_ent, config.atomic_indicators.entropy.features, 6
            )
        if config.atomic_indicators.tail_risk.enabled:
            full_tr = self._estimate_tail_risk_features(config.atomic_indicators.tail_risk)
            tail_risk_count = self._apply_feature_filter_ratio(
                full_tr, config.atomic_indicators.tail_risk.features, 8
            )

        preprocessing_added = 0
        base_total_before_preprocessing = (
            atomic_total
            + microstructure_count
            + entropy_count
            + tail_risk_count
            + derived_count
            + rolling_count
            + lag_count
            + cross_count
            + meta_count
            # labels are target variables, NOT input features; excluded from preprocessing
        )
        if config.preprocessing.enabled:
            preprocess_multiplier = self._estimate_preprocessing_multiplier(config.preprocessing)
            preprocessing_added = max(0, int(base_total_before_preprocessing * (preprocess_multiplier - 1.0)))

        total_features = (
            atomic_total
            + microstructure_count
            + entropy_count
            + tail_risk_count
            + derived_count
            + rolling_count
            + lag_count
            + cross_count
            + meta_count
            # label_count intentionally excluded: labels are Y targets, not X features
            + preprocessing_added
        )

        estimated_time_seconds = max(0.5, total_features / 200.0)
        memory_mb = max(1.0, total_features * 0.02)

        breakdown = {
            "atomic": atomic_total,
            "derived": derived_count,
            "rolling": rolling_count,
            "lag": lag_count,
            "cross_sectional": cross_count,
            "meta": meta_count,
            "labels": label_count,
        }
        breakdown.update(atomic_counts)
        breakdown["microstructure"] = microstructure_count
        breakdown["entropy"] = entropy_count
        breakdown["tail_risk"] = tail_risk_count
        breakdown["preprocessing_added"] = preprocessing_added

        return FeatureCountPreview(
            total_features=total_features,
            estimated_time_seconds=estimated_time_seconds,
            memory_mb=memory_mb,
            breakdown=breakdown,
        )

    @staticmethod
    def _estimate_microstructure_features(config: MicrostructureConfig) -> int:
        count = 0
        count += len(config.windows)
        count += len(config.kyle_lambda_windows)
        count += len(config.kyle_lambda_windows)
        count += len(config.cs_spread_smooth)
        count += 1 + len(config.windows)
        count += len(config.kyle_lambda_windows)
        count += len(config.vpin_n_buckets) + len(config.vpin_zscore_windows)
        return count

    @staticmethod
    def _estimate_entropy_features(config: EntropyConfig) -> int:
        n_sources = len(config.apply_to)
        count = 0
        count += len(config.shannon_windows) * n_sources
        count += len(config.windows)
        count += len(config.windows)
        count += len(config.hurst_windows)
        count += len(config.windows)
        count += len(config.perm_windows)
        return count

    @staticmethod
    def _estimate_tail_risk_features(config: TailRiskConfig) -> int:
        count = 0
        count += len(config.cvar_alphas) * len(config.windows)
        count += 3 * len(config.rv_windows)
        count += len(config.rv_windows)
        count += len(config.windows)
        count += 2
        count += len(config.mdd_windows)
        return count

    @staticmethod
    def _estimate_preprocessing_multiplier(config: PreprocessingConfig) -> float:
        if config.mode == "replace":
            return 1.0

        multiplier = 1.0
        if config.rank_transform.enabled:
            multiplier += 1.0
        if config.gaussian_normalize.enabled:
            multiplier += 1.0
        if config.adaptive_zscore.enabled:
            multiplier += len(config.adaptive_zscore.windows)
        if config.adf_differencing.enabled or config.fractional_differencing.enabled:
            multiplier += 0.2
        return multiplier

    def apply_preset(self, preset_name: str) -> FactoryConfig:
        """Apply preset: minimal/standard/extended/full or Phase 3.1 level presets."""
        base_config = self._load_yaml(self._default_config_path, required=True)
        preset = preset_name.lower()

        if preset == "minimal":
            preset_config = self._apply_minimal_preset(base_config)
        elif preset == "standard":
            preset_config = self._apply_standard_preset(base_config)
        elif preset == "extended":
            preset_config = self._apply_extended_preset(base_config)
        elif preset == "full":
            preset_config = base_config
        elif preset == "basic_essential":
            preset_config = self._apply_basic_essential_preset(base_config)
        elif preset == "intermediate_research":
            preset_config = self._apply_intermediate_research_preset(base_config)
        elif preset == "professional_full":
            preset_config = self._apply_professional_full_preset(base_config)
        elif preset == "ml_optimized":
            preset_config = self._apply_ml_optimized_preset(base_config)
        elif preset == "trend_focused":
            preset_config = self._apply_trend_focused_preset(base_config)
        elif preset == "momentum_focused":
            preset_config = self._apply_momentum_focused_preset(base_config)
        elif preset == "microstructure_focused":
            preset_config = self._apply_microstructure_focused_preset(base_config)
        elif preset == "lightweight_ml":
            preset_config = self._apply_lightweight_ml_preset(base_config)
        elif preset == "custom":
            preset_config = base_config
        else:
            raise ValueError(f"Unknown preset: {preset_name}")

        return FactoryConfig.model_validate(preset_config)

    def deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge dictionaries; override values replace base values."""
        if not isinstance(base, dict) or not isinstance(override, dict):
            return copy.deepcopy(override)

        merged = copy.deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self.deep_merge(merged[key], value)
            else:
                merged[key] = copy.deepcopy(value)
        return merged

    def _normalize_data_source_aliases(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize legacy underscore synthetic source names to canonical hyphen format."""
        normalized = copy.deepcopy(config)

        data_sources = normalized.get("data_sources")
        if isinstance(data_sources, dict):
            enabled_sources = data_sources.get("enabled_sources")
            if isinstance(enabled_sources, list):
                data_sources["enabled_sources"] = [LEGACY_SOURCE_ALIASES.get(src, src) for src in enabled_sources]

            synthetic_sources = data_sources.get("synthetic_sources")
            if isinstance(synthetic_sources, list):
                data_sources["synthetic_sources"] = [
                    LEGACY_SOURCE_ALIASES.get(src, src) for src in synthetic_sources
                ]

        atomic = normalized.get("atomic_indicators")
        if isinstance(atomic, dict):
            for category_cfg in atomic.values():
                if not isinstance(category_cfg, dict):
                    continue
                for indicator in category_cfg.get("indicators", []) or []:
                    if not isinstance(indicator, dict):
                        continue
                    indicator_sources = indicator.get("data_sources")
                    if isinstance(indicator_sources, list):
                        indicator["data_sources"] = [
                            LEGACY_SOURCE_ALIASES.get(src, src) for src in indicator_sources
                        ]

        return normalized

    def _load_yaml(self, path: str, required: bool) -> Dict[str, Any]:
        if not os.path.exists(path):
            if required:
                raise FileNotFoundError(f"Config file not found: {path}")
            return {}

        with open(path, "r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Invalid config format in {path}; expected a mapping.")
        return data

    def _collect_allowed_indicators(self, base_config: Dict[str, Any]) -> set[str]:
        allowed = set()
        atomic = base_config.get("atomic_indicators", {}) if isinstance(base_config, dict) else {}
        for category_config in atomic.values():
            if not isinstance(category_config, dict):
                continue
            for indicator in category_config.get("indicators", []) or []:
                if isinstance(indicator, dict) and indicator.get("name"):
                    allowed.add(indicator["name"])
        return allowed

    def _validate_period_values(self, indicator: Dict[str, Any]) -> List[str]:
        errors: List[str] = []
        period_keys = ["periods", "period_range", "ema_periods"]

        for key in period_keys:
            value = indicator.get(key)
            if value is None:
                continue
            if key == "period_range" and isinstance(value, list) and value:
                if min(value) < 2:
                    errors.append(f"Invalid period_range in {indicator.get('name')}: {value}")
            elif isinstance(value, list):
                if any(period < 2 for period in value if isinstance(period, (int, float))):
                    errors.append(f"Invalid {key} in {indicator.get('name')}: {value}")

        combos = indicator.get("combos")
        if isinstance(combos, list):
            for combo in combos:
                if isinstance(combo, list):
                    if any(val < 2 for val in combo if isinstance(val, (int, float))):
                        errors.append(f"Invalid combo in {indicator.get('name')}: {combo}")

        return errors

    def _estimate_atomic_counts(self, config: Dict[str, Any]) -> Dict[str, int]:
        atomic = config.get("atomic_indicators", {})
        data_sources = config.get("data_sources", {}).get("enabled_sources", [])
        single_series_factor = max(1, min(len(data_sources), 2))

        multi_input = {
            "ADX",
            "ADXR",
            "DX",
            "PLUS_DI",
            "MINUS_DI",
            "PLUS_DM",
            "MINUS_DM",
            "CCI",
            "MFI",
            "STOCH",
            "STOCHF",
            "AROON",
            "AROONOSC",
            "BOP",
            "ULTOSC",
            "WILLR",
            "SAR",
            "SAREXT",
            "MIDPRICE",
            "TRANGE",
            "ATR",
            "NATR",
            "ADOSC",
            "OBV",
            "AD",
            "BETA",
            "CORREL",
        }

        breakdown: Dict[str, int] = {}
        for category, category_cfg in atomic.items():
            if not isinstance(category_cfg, dict) or not category_cfg.get("enabled", True):
                breakdown[category] = 0
                continue

            indicators = category_cfg.get("indicators", []) or []
            if category == "pattern" and not indicators:
                breakdown[category] = 61
                continue
            if category == "cycle" and not indicators:
                breakdown[category] = 5
                continue

            category_total = 0
            for indicator in indicators:
                if not isinstance(indicator, dict) or not indicator.get("name"):
                    continue
                if not indicator.get("enabled", True):
                    continue
                name = indicator["name"]
                count = self._estimate_indicator_params(indicator)
                if name not in multi_input:
                    count *= single_series_factor
                category_total += count

            breakdown[category] = category_total

        return breakdown

    def _estimate_indicator_params(self, indicator: Dict[str, Any]) -> int:
        """Return the exact number of feature columns for one indicator config entry.

        Handles all parameter axes:
        - combos (MACD-family, STOCH-family, ULTOSC, ADOSC, APO, PPO, …)
        - ema_periods + atr_multiplier (Keltner / Force_Index)
        - acceleration × maximum (SAR / SAREXT)
        - periods: str — resolved via ParameterGenerator including industry_standard
        - periods: list — merged with industry_standard
        - stddev (BBANDS), nbdev (STDDEV/VAR), vfactor (T3), matype (MA)

        Result is multiplied by the indicator's output_count for multi-column
        outputs such as MACD (3) and BBANDS (3).
        """
        name = indicator.get("name", "")
        output_count = _INDICATOR_OUTPUT_COUNTS.get(name, 1)

        # ── combos: each entry is one full parameter set ──────────────────────
        combos = indicator.get("combos")
        if isinstance(combos, list) and combos:
            return len(combos) * output_count

        # ── ema_periods (Keltner, Force_Index) ────────────────────────────────
        ema_periods = indicator.get("ema_periods")
        if isinstance(ema_periods, list) and ema_periods:
            param_count = len(ema_periods)
            atr_multiplier = indicator.get("atr_multiplier")
            if isinstance(atr_multiplier, list) and atr_multiplier:
                param_count *= len(atr_multiplier)
            return param_count * output_count

        # ── SAR / SAREXT: acceleration × maximum ──────────────────────────────
        acceleration = indicator.get("acceleration")
        maximum = indicator.get("maximum")
        if isinstance(acceleration, list) and isinstance(maximum, list):
            return max(1, len(acceleration)) * max(1, len(maximum)) * output_count

        # ── Period-based calculation ──────────────────────────────────────────
        periods = indicator.get("periods")
        period_range = indicator.get("period_range")
        industry_standard = indicator.get("industry_standard")

        if isinstance(periods, str):
            range_min = 5
            range_max = 233
            if isinstance(period_range, list) and len(period_range) >= 2:
                range_min = int(period_range[0])
                range_max = int(period_range[1])
            ind_std = industry_standard if isinstance(industry_standard, list) else None
            period_list = ParameterGenerator.generate(periods, range_min, range_max, ind_std)
            param_count = max(1, len(period_list))
        elif isinstance(periods, list):
            merged = {int(p) for p in periods}
            if isinstance(industry_standard, list):
                merged.update(int(p) for p in industry_standard)
            param_count = max(1, len(merged))
        else:
            # No explicit periods: fixed-param indicator
            # (e.g. OBV, TRANGE, BOP, HT_*, pattern CDLs, VWAP)
            param_count = 1

        # Additional expansion axes (applied in combination with periods)
        stddev  = indicator.get("stddev")   # BBANDS nbdevup/dn
        nbdev   = indicator.get("nbdev")    # STDDEV / VAR
        vfactor = indicator.get("vfactor")  # T3
        matype  = indicator.get("matype")   # MA (multiple MA types)

        if isinstance(stddev, list) and stddev:
            param_count *= len(stddev)
        if isinstance(nbdev, list) and nbdev:
            param_count *= len(nbdev)
        if isinstance(vfactor, list) and vfactor:
            param_count *= len(vfactor)
        if isinstance(matype, list) and matype:
            param_count *= len(matype)

        return max(1, param_count) * output_count

    def _estimate_label_count(self, labels_cfg: Dict[str, Any]) -> int:
        binary = labels_cfg.get("binary", {}) if isinstance(labels_cfg, dict) else {}
        regression = labels_cfg.get("regression", {}) if isinstance(labels_cfg, dict) else {}
        binary_count = len(binary.get("horizons", []) or [])
        regression_count = len(regression.get("horizons", []) or [])
        return binary_count + regression_count

    def _any_enabled(self, operators_cfg: Dict[str, Any]) -> bool:
        if not isinstance(operators_cfg, dict):
            return False
        for value in operators_cfg.values():
            if isinstance(value, dict) and value.get("enabled", True):
                return True
        return False

    @staticmethod
    def _apply_feature_filter_ratio(
        full_count: int,
        features_dict: Dict[str, Any],
        total_feature_types: int,
    ) -> int:
        """Scale full_count by the ratio of enabled features in an advanced config."""
        if not features_dict:
            return full_count
        enabled_count = sum(
            1 for v in features_dict.values()
            if (isinstance(v, dict) and v.get("enabled", True))
            or (hasattr(v, "enabled") and v.enabled)
        )
        ratio = enabled_count / max(1, total_feature_types)
        return max(0, int(full_count * ratio))

    def _estimate_derived_count(
        self,
        atomic_total: int,
        atomic_counts: Dict[str, int],
        operators_cfg: Dict[str, Any],
    ) -> int:
        """Estimate Layer 2 derived feature count based on enabled operators.

        Operator semantics (from derived_operators.py):
          distance  — 1 output per filtered feature (apply_to selects category subset)
          cross     — multiplier-based pairing [3x,5x,10x,20x,40x], only single-param
                      features qualify (~70% of atomic); each param gets at most 5 partners
                      but higher params find fewer valid partners; empirical ratio ≈ 1.8
          momentum  — len(lags) outputs per feature
          ratio     — same multiplier pairing as cross; ratio ≈ 1.8
          binary_signal — 1 output per enabled rule (exact)
          worldquant    — conservative estimate (intentionally small)
        """
        # Respect the top-level enabled=False flag (set when user disables Layer 2).
        if operators_cfg.get("enabled") is False:
            return 0
        if not self._any_enabled(operators_cfg):
            return 0
        count = 0

        # distance: 1:1 ratio, restricted to the category specified by apply_to
        dist = operators_cfg.get("distance", {})
        if isinstance(dist, dict) and dist.get("enabled", True):
            apply_to = dist.get("apply_to", "all")
            if apply_to == "all_trend":
                base = atomic_counts.get("trend", atomic_total)
            elif apply_to == "all_momentum":
                base = atomic_counts.get("momentum", atomic_total)
            elif apply_to == "all_volatility":
                base = atomic_counts.get("volatility", atomic_total)
            else:  # "all" or unrecognised
                base = atomic_total
            count += base

        # cross: multiplier-based pairing [3x,5x,10x,20x,40x]; each param produces on average
        # ~1-3 valid pairs (larger params find fewer partners at the high-multiplier targets).
        # Empirically ~1.8 pairs per single-param feature; ~70% of atomic have 1 param.
        cross = operators_cfg.get("cross", {})
        if isinstance(cross, dict) and cross.get("enabled", True):
            count += int(atomic_total * 1.8)

        # momentum: len(lags) new features per input feature (full atomic, apply_to defaulting to all)
        mom = operators_cfg.get("momentum", {})
        if isinstance(mom, dict) and mom.get("enabled", True):
            apply_to = mom.get("apply_to", "all")
            if apply_to == "all_trend":
                base = atomic_counts.get("trend", atomic_total)
            elif apply_to == "all_momentum":
                base = atomic_counts.get("momentum", atomic_total)
            else:
                base = atomic_total
            lags = mom.get("lags", [3, 5, 8])
            n_lags = len(lags) if isinstance(lags, list) else 3
            count += base * n_lags

        # ratio: same multiplier pairing structure as cross (~1.8)
        ratio_op = operators_cfg.get("ratio", {})
        if isinstance(ratio_op, dict) and ratio_op.get("enabled", True):
            count += int(atomic_total * 1.8)

        # binary_signal: exact count of enabled rules
        bs = operators_cfg.get("binary_signal", {})
        if isinstance(bs, dict) and bs.get("enabled", True):
            rules = bs.get("rules", [])
            if isinstance(rules, list):
                count += sum(1 for r in rules if isinstance(r, dict) and r.get("enabled", True))

        # worldquant: keep conservative estimate (complex formula, intentionally small)
        wq = operators_cfg.get("worldquant", {})
        if isinstance(wq, dict) and wq.get("enabled", True):
            wq_ops = wq.get("operators") or {}
            if isinstance(wq_ops, dict):
                wq_enabled = sum(
                    1 for v in wq_ops.values()
                    if isinstance(v, dict) and v.get("enabled", True)
                )
                count += int(atomic_total * 0.05 * max(1, wq_enabled))

        return count

    def _estimate_rolling_count(self, atomic_total: int, rolling_cfg: Dict[str, Any]) -> int:
        """Estimate Layer 3 rolling feature count based on enabled aggregators and windows."""
        if not rolling_cfg.get("enabled", True):
            return 0
        agg_dict = rolling_cfg.get("aggregators", {})
        if isinstance(agg_dict, dict):
            n_enabled_agg = sum(
                1 for v in agg_dict.values()
                if isinstance(v, dict) and v.get("enabled", True)
            )
        elif isinstance(agg_dict, list):
            n_enabled_agg = len(agg_dict)
        else:
            n_enabled_agg = 0
        n_windows = len(rolling_cfg.get("windows", [3, 5, 8, 13, 21, 34, 55, 89, 144, 233]))
        return atomic_total * n_enabled_agg * n_windows

    def _estimate_lag_count(
        self, atomic_total: int, lag_cfg: Dict[str, Any], config_dict: Dict[str, Any]
    ) -> int:
        """Estimate Layer 4 lag feature count using ParameterGenerator for exact lag sequence."""
        if not lag_cfg.get("enabled", True):
            return 0
        global_cfg = config_dict.get("global") or {}
        sequence_length = int(global_cfg.get("sequence_length", 100))
        max_lag_ratio = float(global_cfg.get("max_lag_ratio", 0.5))
        strategy = global_cfg.get("lag_strategy", "adaptive")
        custom_lags = global_cfg.get("custom_lags")
        lags = ParameterGenerator.generate_lag_sequence(
            sequence_length=sequence_length,
            max_lag_ratio=max_lag_ratio,
            strategy=strategy if isinstance(strategy, str) else "adaptive",
            custom_lags=custom_lags if isinstance(custom_lags, list) else None,
        )
        return atomic_total * len(lags)


    @staticmethod
    def _estimate_cross_count(cross_cfg: Dict[str, Any]) -> int:
        """Estimate Layer 5 cross-sectional feature count."""
        if not cross_cfg.get("enabled", False):
            return 0
        features = cross_cfg.get("features", {})
        if isinstance(features, dict):
            return sum(
                1 for v in features.values()
                if isinstance(v, dict) and v.get("enabled", True)
            )
        if isinstance(features, list):
            return len(features)
        return 0

    @staticmethod
    def _estimate_meta_count(meta_cfg: Dict[str, Any]) -> int:
        """Estimate Layer 6 meta feature count based on enabled sub-engines."""
        if not meta_cfg.get("enabled", True):
            return 0
        sub_keys = [
            "consensus", "interaction", "time_features", "trend_consensus",
            "momentum_divergence", "volume_price_divergence", "volatility_regime",
        ]
        n_enabled = sum(1 for k in sub_keys if meta_cfg.get(k, True))
        return n_enabled * 3

    def _apply_minimal_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        preset["data_sources"]["enabled_sources"] = ["close"]

        atomic = preset.get("atomic_indicators", {})
        for category in atomic.values():
            if isinstance(category, dict):
                category["enabled"] = False
                category["indicators"] = []

        atomic["trend"] = {
            "enabled": True,
            "indicators": [
                {"name": "EMA", "periods": [21, 55]},
                {"name": "SMA", "periods": [21, 55]},
            ],
        }
        atomic["momentum"] = {
            "enabled": True,
            "indicators": [
                {"name": "RSI", "periods": [14]},
                {"name": "MACD", "combos": [[12, 26, 9]]},
            ],
        }

        preset["operators"]["distance"]["enabled"] = False
        preset["operators"]["cross"]["enabled"] = False
        preset["operators"]["momentum"]["enabled"] = False
        preset["operators"]["ratio"]["enabled"] = False
        preset["operators"]["binary_signal"]["enabled"] = False
        preset["operators"]["worldquant"]["enabled"] = False

        preset["rolling_aggregation"]["enabled"] = False
        preset["lag_features"]["enabled"] = False

        return preset

    def _apply_standard_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        preset["data_sources"]["enabled_sources"] = [
            "close",
            "open",
            "high",
            "low",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_volume",
            "taker_ratio",
        ]

        atomic = preset.get("atomic_indicators", {})
        for category in atomic.values():
            if isinstance(category, dict):
                category["enabled"] = True

        for category in atomic.values():
            if not isinstance(category, dict):
                continue
            indicators = category.get("indicators", [])
            for indicator in indicators:
                if isinstance(indicator, dict) and indicator.get("periods") == "fibonacci":
                    indicator["periods"] = "fibonacci_short"

        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [5, 13, 21]
        preset["lag_features"]["enabled"] = True
        preset["lag_features"]["apply_to"] = "layer1_and_raw"

        return preset

    def _apply_extended_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        preset["data_sources"]["enabled_sources"] = [
            "close",
            "open",
            "high",
            "low",
            "volume",
            "quote_volume",
            "trades",
            "taker_buy_volume",
            "taker_ratio",
            "avg-price",
            "med-price",
            "typ-price",
            "wcl-price",
        ]
        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [5, 13, 21, 34]
        preset["lag_features"]["enabled"] = True
        preset["global"]["lag_strategy"] = "dense"
        return preset

    @staticmethod
    def _set_atomic_levels(
        preset: Dict[str, Any],
        enabled_keys: List[str],
    ) -> None:
        atomic = preset.get("atomic_indicators", {})
        for key, value in atomic.items():
            if isinstance(value, dict):
                value["enabled"] = key in enabled_keys

    @staticmethod
    def _ensure_preprocessing_shape(preset: Dict[str, Any]) -> Dict[str, Any]:
        preprocessing = preset.setdefault("preprocessing", {})
        if not isinstance(preprocessing, dict):
            preprocessing = {}
            preset["preprocessing"] = preprocessing

        preprocessing.setdefault("winsorization", {})
        preprocessing.setdefault("adf_differencing", {})
        preprocessing.setdefault("fractional_differencing", {})
        preprocessing.setdefault("rank_transform", {})
        preprocessing.setdefault("gaussian_normalize", {})
        preprocessing.setdefault("adaptive_zscore", {})
        return preprocessing

    def _apply_basic_essential_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(preset, ["trend", "momentum", "volatility", "volume"])

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "append"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = False
        preprocessing["gaussian_normalize"]["enabled"] = False
        preprocessing["adf_differencing"]["enabled"] = False
        preprocessing["fractional_differencing"]["enabled"] = False
        return preset

    def _apply_intermediate_research_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(
            preset,
            [
                "trend",
                "momentum",
                "volatility",
                "volume",
                "statistics",
                "cycle",
                "pattern",
                "tail_risk",
            ],
        )

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "append"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = True
        preprocessing["adaptive_zscore"]["windows"] = [20, 40, 60, 80, 100]
        preprocessing["gaussian_normalize"]["enabled"] = True
        preprocessing["adf_differencing"]["enabled"] = False
        preprocessing["fractional_differencing"]["enabled"] = False
        return preset

    def _apply_professional_full_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(
            preset,
            [
                "trend",
                "momentum",
                "volatility",
                "volume",
                "statistics",
                "cycle",
                "pattern",
                "tail_risk",
                "microstructure",
                "entropy",
            ],
        )

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "append"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = True
        preprocessing["adaptive_zscore"]["windows"] = [
            20,
            30,
            40,
            50,
            60,
            70,
            80,
            90,
            100,
            120,
            140,
            160,
            180,
            200,
            220,
            240,
            260,
            280,
            320,
            360,
        ]
        preprocessing["gaussian_normalize"]["enabled"] = True
        preprocessing["adf_differencing"]["enabled"] = True
        preprocessing["fractional_differencing"]["enabled"] = True
        return preset

    def _apply_ml_optimized_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(
            preset,
            [
                "trend",
                "momentum",
                "volatility",
                "volume",
                "statistics",
                "cycle",
                "pattern",
                "tail_risk",
            ],
        )

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "replace"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = True
        preprocessing["adaptive_zscore"]["windows"] = [20, 40, 60, 80, 100]
        preprocessing["gaussian_normalize"]["enabled"] = True
        preprocessing["adf_differencing"]["enabled"] = False
        preprocessing["fractional_differencing"]["enabled"] = True
        return preset

    def _apply_trend_focused_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """趨勢策略研究: Trend 全開 + Momentum 只 RSI/MACD/ADX + Volatility 全開"""
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(preset, ["trend", "momentum", "volatility"])

        # Momentum: disable all except RSI, MACD, ADX
        momentum_keep = {"RSI", "MACD", "ADX"}
        atomic = preset.get("atomic_indicators", {})
        mom = atomic.get("momentum", {})
        for ind in mom.get("indicators", []):
            if isinstance(ind, dict):
                ind["enabled"] = ind.get("name") in momentum_keep

        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [5, 13, 21]
        preset["lag_features"]["enabled"] = True
        return preset

    def _apply_momentum_focused_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """動量策略: Momentum 全開 + Volume 全開"""
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(preset, ["momentum", "volume"])

        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [5, 13, 21]
        preset["lag_features"]["enabled"] = True
        return preset

    def _apply_microstructure_focused_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """微觀結構研究: Microstructure 全開 + Volume + Entropy"""
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(preset, ["volume", "microstructure", "entropy"])

        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [5, 13, 21]
        preset["lag_features"]["enabled"] = False

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "append"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = False
        preprocessing["gaussian_normalize"]["enabled"] = False
        preprocessing["adf_differencing"]["enabled"] = False
        preprocessing["fractional_differencing"]["enabled"] = False
        return preset

    def _apply_lightweight_ml_preset(self, base_config: Dict[str, Any]) -> Dict[str, Any]:
        """輕量 ML: 精選 ~30 核心指標 + adaptive lag + rank preprocessing"""
        preset = copy.deepcopy(base_config)
        self._set_atomic_levels(preset, ["trend", "momentum", "volatility", "volume"])

        atomic = preset.get("atomic_indicators", {})
        # Trend: only EMA, SMA, BBANDS
        trend_keep = {"EMA", "SMA", "BBANDS"}
        for ind in atomic.get("trend", {}).get("indicators", []):
            if isinstance(ind, dict):
                ind["enabled"] = ind.get("name") in trend_keep

        # Momentum: only RSI, MACD, ADX, CCI, MFI, STOCH
        mom_keep = {"RSI", "MACD", "ADX", "CCI", "MFI", "STOCH"}
        for ind in atomic.get("momentum", {}).get("indicators", []):
            if isinstance(ind, dict):
                ind["enabled"] = ind.get("name") in mom_keep

        # Volatility: only ATR, NATR
        vol_keep = {"ATR", "NATR"}
        for ind in atomic.get("volatility", {}).get("indicators", []):
            if isinstance(ind, dict):
                ind["enabled"] = ind.get("name") in vol_keep

        # Volume: only OBV, VWAP
        vol_ind_keep = {"OBV", "VWAP"}
        for ind in atomic.get("volume", {}).get("indicators", []):
            if isinstance(ind, dict):
                ind["enabled"] = ind.get("name") in vol_ind_keep

        preset["rolling_aggregation"]["enabled"] = True
        preset["rolling_aggregation"]["windows"] = [13, 21]
        # Keep only mean, std, rank aggregators
        agg = preset.get("rolling_aggregation", {}).get("aggregators", {})
        if isinstance(agg, dict):
            for agg_name, agg_cfg in agg.items():
                if isinstance(agg_cfg, dict):
                    agg_cfg["enabled"] = agg_name in {"mean", "std", "rank"}
        elif isinstance(agg, list):
            preset["rolling_aggregation"]["aggregators"] = {
                name: {"enabled": name in {"mean", "std", "rank"}} for name in agg
            }

        preset["lag_features"]["enabled"] = True
        preset["global"]["lag_strategy"] = "adaptive"

        preprocessing = self._ensure_preprocessing_shape(preset)
        preprocessing["enabled"] = True
        preprocessing["mode"] = "replace"
        preprocessing["winsorization"]["enabled"] = True
        preprocessing["rank_transform"]["enabled"] = True
        preprocessing["adaptive_zscore"]["enabled"] = False
        preprocessing["gaussian_normalize"]["enabled"] = False
        preprocessing["adf_differencing"]["enabled"] = False
        preprocessing["fractional_differencing"]["enabled"] = False
        return preset
