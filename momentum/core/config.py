"""Momentum configuration definitions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


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
