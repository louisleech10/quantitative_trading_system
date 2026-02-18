"""Momentum configuration definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from momentum.core.logging import get_logger

logger = get_logger(__name__)


def _default_project_root() -> Path:
    current = Path(__file__).resolve()
    # core/config.py -> core -> momentum -> project root
    if len(current.parents) >= 4:
        return current.parents[3]
    return Path.cwd()


@dataclass(frozen=True)
class MomentumConfig:
    """Configuration for momentum core modules."""

    project_root: Path
    data_cache_path: Path
    results_path: Path

    @classmethod
    def from_project_root(cls, project_root: Optional[Path] = None) -> "MomentumConfig":
        root = project_root or _default_project_root()
        return cls(
            project_root=root,
            data_cache_path=root / "data_cache",
            results_path=root / "results",
        )

    @staticmethod
    def load_optimization_config() -> dict:
        config_path = Path(__file__).parent.parent.parent / "config" / "optimization_config.yaml"
        if not config_path.exists():
            raise FileNotFoundError(f"Optimization config not found: {config_path}")
        try:
            with open(config_path, "r", encoding="utf-8") as file:
                config = yaml.safe_load(file)
            if not isinstance(config, dict):
                raise ValueError("optimization_config.yaml must be a dictionary at root")
            return config
        except yaml.YAMLError as exc:
            logger.error("Failed to parse optimization config YAML", exc_info=True)
            raise ValueError(f"Invalid optimization_config.yaml format: {exc}") from exc
