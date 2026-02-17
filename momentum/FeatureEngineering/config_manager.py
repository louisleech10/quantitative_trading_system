from __future__ import annotations

import copy
import os
from typing import Any, Dict, List, Optional

from jsonschema import Draft202012Validator

import yaml

from momentum.core.logging import get_logger
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
        try:
            return FactoryConfig.model_validate(merged)
        except Exception as exc:
            logger.error("Failed to validate merged config", exc_info=True)
            raise exc

    def validate_config(self, config: Dict[str, Any]) -> ValidationResult:
        """Validate config keys, indicator names, and period ranges."""
        errors: List[str] = []
        warnings: List[str] = []

        base_config = self._load_yaml(self._default_config_path, required=True)
        merged = self.deep_merge(base_config, config or {})

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
            "avg_price",
            "med_price",
            "typ_price",
            "wcl_price",
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

        derived_count = int(atomic_total * 0.1) if self._any_enabled(operators_cfg) else 0
        rolling_count = int(atomic_total * 0.1) if rolling_cfg.get("enabled", True) else 0
        lag_count = int(atomic_total * 0.1) if lag_cfg.get("enabled", True) else 0
        cross_count = int(atomic_total * 0.05) if cross_cfg.get("enabled", False) else 0
        meta_count = 20 if meta_cfg.get("enabled", True) else 0
        label_count = self._estimate_label_count(labels_cfg)

        microstructure_count = 0
        entropy_count = 0
        tail_risk_count = 0
        if config.atomic_indicators.microstructure.enabled:
            microstructure_count = self._estimate_microstructure_features(
                config.atomic_indicators.microstructure
            )
        if config.atomic_indicators.entropy.enabled:
            entropy_count = self._estimate_entropy_features(config.atomic_indicators.entropy)
        if config.atomic_indicators.tail_risk.enabled:
            tail_risk_count = self._estimate_tail_risk_features(config.atomic_indicators.tail_risk)

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
            + label_count
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
            + label_count
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
                name = indicator["name"]
                count = self._estimate_indicator_params(indicator)
                if name not in multi_input:
                    count *= single_series_factor
                category_total += count

            breakdown[category] = category_total

        return breakdown

    def _estimate_indicator_params(self, indicator: Dict[str, Any]) -> int:
        count = 1
        periods = indicator.get("periods")
        if isinstance(periods, str):
            count *= {
                "fibonacci": 9,
                "fibonacci_short": 6,
                "fibonacci_full": 9,
                "log_scale": 7,
                "linear": 6,
            }.get(periods, 6)
        elif isinstance(periods, list):
            count *= max(1, len(periods))

        period_range = indicator.get("period_range")
        if isinstance(period_range, list) and period_range:
            count *= 9

        combos = indicator.get("combos")
        if isinstance(combos, list) and combos:
            count *= len(combos)

        stddev = indicator.get("stddev")
        if isinstance(stddev, list) and stddev:
            count *= len(stddev)

        atr_multiplier = indicator.get("atr_multiplier")
        if isinstance(atr_multiplier, list) and atr_multiplier:
            count *= len(atr_multiplier)

        acceleration = indicator.get("acceleration")
        maximum = indicator.get("maximum")
        if isinstance(acceleration, list) and isinstance(maximum, list):
            count *= max(1, len(acceleration)) * max(1, len(maximum))

        ema_periods = indicator.get("ema_periods")
        if isinstance(ema_periods, list) and ema_periods:
            count *= len(ema_periods)

        return count

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
            "avg_price",
            "med_price",
            "typ_price",
            "wcl_price",
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
