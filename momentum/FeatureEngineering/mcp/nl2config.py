from __future__ import annotations

from typing import Dict

from momentum.core.logging import get_logger

logger = get_logger(__name__)


class NL2ConfigConverter:
    """Rule-based natural language to config patch converter."""

    def __init__(self, config_schema: Dict):
        self._schema = config_schema

    def convert(self, natural_language: str) -> Dict:
        """Convert natural language into a partial config patch."""
        if not natural_language:
            return {}

        text = natural_language.lower()
        preset = self._extract_preset(text)
        if preset:
            return {"preset": preset}

        patch = self._extract_category_toggle(text)
        if patch:
            return patch

        return {}

    def get_schema_prompt(self) -> str:
        """Return a compact schema prompt for LLM usage."""
        if not isinstance(self._schema, dict) or not self._schema:
            return "Feature Factory config schema is not available."

        keys = ", ".join(sorted(self._schema.keys()))
        return (
            "Feature Factory config schema keys: "
            f"{keys}. Use these keys to build a partial config patch."
        )

    @staticmethod
    def _extract_preset(text: str) -> str | None:
        presets = ["minimal", "standard", "extended", "full"]
        for preset in presets:
            if preset in text:
                return preset
        return None

    @staticmethod
    def _extract_category_toggle(text: str) -> Dict:
        categories = [
            "trend",
            "momentum",
            "volatility",
            "volume",
            "cycle",
            "pattern",
            "statistics",
        ]
        for category in categories:
            if category not in text:
                continue
            if "disable" in text or "off" in text:
                return {"atomic_indicators": {category: {"enabled": False}}}
            if "enable" in text or "on" in text:
                return {"atomic_indicators": {category: {"enabled": True}}}
        return {}
