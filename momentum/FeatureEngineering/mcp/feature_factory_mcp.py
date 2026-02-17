from __future__ import annotations

from typing import Dict, List, Optional

from momentum.core.logging import get_logger
from momentum.FeatureEngineering.atomic.talib_wrapper import TALibWrapper
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_factory import FeatureFactory, FeatureGenerationResult
from momentum.FeatureEngineering.mcp.nl2config import NL2ConfigConverter

logger = get_logger(__name__)


class FeatureFactoryMCP:
    """MCP tools for Feature Factory operations."""

    def __init__(self, feature_factory: FeatureFactory, config_manager: ConfigManager):
        self._factory = feature_factory
        self._config_manager = config_manager
        self._nl2config = NL2ConfigConverter(self._get_schema())

    def generate_features(self, symbol: str, config: Optional[Dict] = None) -> Dict:
        """Generate features via FeatureFactory."""
        try:
            merged = self._config_manager.get_merged_config(config)
            timeframe = merged.timeframes.primary
            result = self._factory.generate_features(
                symbol,
                timeframe,
                config_override=config,
            )
            return self._summarize_result(result)
        except Exception as exc:
            logger.error("Feature generation failed for %s: %s", symbol, exc, exc_info=True)
            return {"error": str(exc)}

    def preview_feature_count(self, config: Optional[Dict] = None) -> Dict:
        """Preview feature counts and resource usage."""
        try:
            merged = self._config_manager.get_merged_config(config)
            preview = self._config_manager.preview_feature_count(merged)
            return preview.model_dump()
        except Exception as exc:
            logger.error("Preview failed: %s", exc, exc_info=True)
            return {"error": str(exc)}

    def update_config(self, partial_config: Dict) -> Dict:
        """Return merged config without persisting changes."""
        try:
            merged = self._config_manager.get_merged_config(partial_config)
            return merged.model_dump(by_alias=True)
        except Exception as exc:
            logger.error("Update config failed: %s", exc, exc_info=True)
            return {"error": str(exc)}

    def list_indicators(self, category: Optional[str] = None) -> List[Dict]:
        """List all available indicators."""
        specs = TALibWrapper.list_indicators(category)
        return [
            {
                "name": spec.name,
                "category": spec.category,
                "input_type": spec.input_type,
                "output_count": spec.output_count,
                "output_names": spec.output_names,
                "param_strategy": spec.param_strategy,
                "computed_in_adapter": spec.computed_in_adapter,
            }
            for spec in specs
        ]

    def list_data_sources(self) -> List[Dict]:
        """List enabled and synthetic data sources."""
        config = self._config_manager.get_merged_config()
        sources = []
        for name in config.data_sources.enabled_sources:
            sources.append({"name": name, "source_type": "raw"})
        for name in config.data_sources.synthetic_sources:
            sources.append({"name": name, "source_type": "synthetic"})
        return sources

    def get_presets(self) -> List[Dict]:
        """Return preset list with preview summaries."""
        presets = []
        preset_definitions = [
            {"name": "minimal", "description": "最小化 baseline", "level": "L1"},
            {"name": "standard", "description": "標準研究配置", "level": "L2"},
            {"name": "extended", "description": "擴展研究配置", "level": "L2"},
            {"name": "full", "description": "全量特徵配置", "level": "L3"},
            {"name": "basic_essential", "description": "🟢 基礎必用 — 業界標配", "level": "L1"},
            {"name": "intermediate_research", "description": "🟡 中階研究 — 進階策略開發", "level": "L2"},
            {"name": "professional_full", "description": "🔴 專業全量 — 量化研究全配", "level": "L3"},
            {"name": "ml_optimized", "description": "🤖 ML 友善 — 去冗餘、已正規化", "level": "ML"},
        ]

        for preset_info in preset_definitions:
            preset = preset_info["name"]
            try:
                config = self._config_manager.apply_preset(preset)
                preview = self._config_manager.preview_feature_count(config)
                presets.append(
                    {
                        "name": preset,
                        "description": preset_info["description"],
                        "level": preset_info["level"],
                        "preview": preview.model_dump(),
                        "config": config.model_dump(),
                    }
                )
            except Exception as exc:
                logger.error("Preset preview failed for %s: %s", preset, exc, exc_info=True)
        return presets

    def validate_config(self, config: Dict) -> Dict:
        """Validate config structure and indicator names."""
        result = self._config_manager.validate_config(config or {})
        return result.model_dump()

    def get_feature_metadata(self, feature_name: str) -> Dict:
        """Return indicator metadata when resolvable from the feature name."""
        TALibWrapper.initialize()
        indicator_name = self._find_indicator_name(feature_name)
        if not indicator_name:
            return {"feature_name": feature_name, "found": False, "metadata": {}}

        spec = TALibWrapper.get_indicator_spec(indicator_name)
        return {
            "feature_name": feature_name,
            "found": True,
            "indicator": {
                "name": spec.name,
                "category": spec.category,
                "input_type": spec.input_type,
                "output_count": spec.output_count,
                "output_names": spec.output_names,
                "param_strategy": spec.param_strategy,
                "computed_in_adapter": spec.computed_in_adapter,
            },
        }

    def nl2config(self, text: str) -> Dict:
        """Convert natural language into config patch and preview."""
        patch = self._nl2config.convert(text)
        description = "Rule-based config patch"
        preview = self._preview_from_patch(patch)
        return {"config_patch": patch, "description": description, "preview": preview}

    def _preview_from_patch(self, patch: Dict) -> Dict:
        try:
            if isinstance(patch, dict) and patch.get("preset"):
                config = self._config_manager.apply_preset(patch["preset"])
            else:
                config = self._config_manager.get_merged_config(patch)
            preview = self._config_manager.preview_feature_count(config)
            return preview.model_dump()
        except Exception as exc:
            logger.error("NL2Config preview failed: %s", exc, exc_info=True)
            return {"error": str(exc)}

    def _get_schema(self) -> Dict:
        try:
            config = self._config_manager.get_merged_config()
            return config.model_dump(by_alias=True)
        except Exception as exc:
            logger.error("Config schema load failed: %s", exc, exc_info=True)
            return {}

    @staticmethod
    def _summarize_result(result: FeatureGenerationResult) -> Dict:
        return {
            "feature_count": result.feature_count,
            "generation_time": result.generation_time,
            "layer_counts": result.layer_counts,
            "metadata": result.metadata,
            "hdf5_path": result.hdf5_path,
        }

    @staticmethod
    def _find_indicator_name(feature_name: str) -> Optional[str]:
        if feature_name in TALibWrapper.INDICATOR_REGISTRY:
            return feature_name

        padded = f"_{feature_name}_"
        for name in sorted(TALibWrapper.INDICATOR_REGISTRY.keys(), key=len, reverse=True):
            if f"_{name}_" in padded:
                return name

        return None
