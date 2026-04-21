"""Hardware tier helpers for Feature Factory optimization toggles."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil as _psutil
except ImportError:
    _psutil = None


TIER_THRESHOLDS: List[Tuple[int, str]] = [
    (28, "32gb"),
    (20, "24gb"),
    (12, "16gb"),
    (0, "8gb"),
]

_WORKERS_BY_TIER: Dict[str, int] = {
    "8gb": 4,
    "16gb": 6,
    "24gb": 8,
    "32gb": 8,
}
_CGSA_BUFFER_BY_TIER: Dict[str, int] = {
    "8gb": 0,
    "16gb": 0,
    "24gb": 32,
    "32gb": 64,
}
_L7_WORKERS_BY_TIER: Dict[str, int] = {
    "8gb": 4,
    "16gb": 6,
    "24gb": 8,
    "32gb": 8,
}
_CHUNK_BARS_BY_TIER: Dict[str, Optional[int]] = {
    "8gb": 50_000,
    "16gb": 100_000,
    "24gb": 250_000,
    "32gb": None,
}


def get_memory_tier() -> str:
    """Return the current memory tier using env override or psutil auto-detection."""
    override = os.getenv("FFACT_MEMORY_TIER", "auto").strip().lower()
    if override and override != "auto":
        return override

    if _psutil is None:
        return "8gb"

    try:
        total_gb = _psutil.virtual_memory().total / 1024 ** 3
    except (AttributeError, OSError):
        return "8gb"

    for threshold, tier in TIER_THRESHOLDS:
        if total_gb >= threshold:
            return tier
    return "8gb"


def get_tier_config(tier: str) -> Dict[str, Any]:
    """Return conservative tier settings with 8GB defaults for unknown tiers."""
    return {
        "l65_workers": _WORKERS_BY_TIER.get(tier, _WORKERS_BY_TIER["8gb"]),
        "cgsa_memory_buffer": _CGSA_BUFFER_BY_TIER.get(tier, _CGSA_BUFFER_BY_TIER["8gb"]),
        "l7_workers": _L7_WORKERS_BY_TIER.get(tier, _L7_WORKERS_BY_TIER["8gb"]),
        "chunk_bars": _CHUNK_BARS_BY_TIER.get(tier, _CHUNK_BARS_BY_TIER["8gb"]),
    }