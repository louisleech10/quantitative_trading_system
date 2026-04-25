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

# Multi-TF parallel workers: each worker spawns a full 6-layer pipeline process.
# RAM budget: ~2-3 GB per worker baseline; 1h L3 with 1611 cols can balloon to
# ~10-12 GB if held in memory. With Plan A streaming persist this drops to ~3 GB.
_MULTI_TF_MAX_WORKERS_BY_TIER: Dict[str, int] = {
    # OOM Fix: 8 GB cannot safely run 1 main + 1 worker concurrently when 1h L3
    # produces 156k cols. Force serialize (worker_count=1; non-primary TFs run
    # one at a time). Combined with L3 streaming this still fits in 8 GB.
    "8gb": 1,
    "16gb": 2,  # 16 GB: 1 main (~3 GB) + 2 workers (~3 GB each) ≈ 9 GB
    "24gb": 3,  # 24 GB: leaves ~6 GB headroom
    "32gb": 4,  # 32 GB: pipeline parallelism saturates at 4
}

# Layer 3 persist mode (Plan A: streaming persist callback).
# - "streaming": persist each chunk to CGSA registry as soon as it is computed,
#   freeing per-step buffers. Required for 8/16 GB to fit 1h CGSA L3.
# - "hybrid": buffer up to N cols before flushing (fewer .npy writes).
# - "in_memory": classic path; concat all step frames into one wide DataFrame.
_L3_PERSIST_MODE_BY_TIER: Dict[str, str] = {
    "8gb": "streaming",
    "16gb": "streaming",
    "24gb": "hybrid",
    "32gb": "in_memory",
}

# Streaming persist buffer (cols accumulated per step before flush).
# Smaller buffer = lower peak RAM but more .npy writes / smaller groups.
_L3_STREAMING_BUFFER_COLS_BY_TIER: Dict[str, int] = {
    "8gb": 2000,
    "16gb": 5000,
    "24gb": 10000,
    "32gb": 20000,  # only used if streaming/hybrid manually enabled
}

# L3 column chunk size for Numba rolling stats.
# Larger chunk = fewer Python for-loop iterations; constrained by L2/L3 cache.
# Multi-window path has a separate hard cap of 64 regardless of this value.
_LAYER3_CHUNK_SIZE_BY_TIER: Dict[str, int] = {
    "8gb": 256,   # ~107 MB per chunk (52K rows × 256 cols × float64)
    "16gb": 512,  # ~214 MB; reduces iterations by 2×
    "24gb": 512,  # same as 16 GB (cache sweet-spot, not purely RAM-limited)
    "32gb": 1024, # ~428 MB; near-zero Python overhead
}

# L6.5 large-group split threshold (P1.2):
# When a registry group exceeds this column count, it is split into balanced
# sub-tasks dispatched to the same ThreadPool. Reduces tail latency caused by
# imbalanced groups (e.g. L2_Momentum carrying ~16k cols while peers carry ~500).
# Set 0 / negative to disable splitting.
_L65_SPLIT_THRESHOLD_BY_TIER: Dict[str, int] = {
    "8gb": 4000,
    "16gb": 8000,
    "24gb": 12000,
    "32gb": 16000,
}

# L2 derived-feature category-level ThreadPool workers (P1.3):
# Allows Distance / Cross / Ratio / Momentum / BinarySignal / SignedStrength /
# WorldQuant categories to compute concurrently. 8GB MUST stay at 1 because
# Multi-TF spawns a sibling worker process; each L2 category peaks at ~1.5 GB
# intermediate before persist, and 2 × that × 2 processes ≈ OOM on M1 8GB.
_L2_CATEGORY_WORKERS_BY_TIER: Dict[str, int] = {
    "8gb": 1,
    "16gb": 4,
    "24gb": 6,
    "32gb": 7,
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
        "multi_tf_max_workers": _MULTI_TF_MAX_WORKERS_BY_TIER.get(tier, _MULTI_TF_MAX_WORKERS_BY_TIER["8gb"]),
        "layer3_chunk_size": _LAYER3_CHUNK_SIZE_BY_TIER.get(tier, _LAYER3_CHUNK_SIZE_BY_TIER["8gb"]),
        "l3_persist_mode": _L3_PERSIST_MODE_BY_TIER.get(tier, _L3_PERSIST_MODE_BY_TIER["8gb"]),
        "l3_streaming_buffer_cols": _L3_STREAMING_BUFFER_COLS_BY_TIER.get(tier, _L3_STREAMING_BUFFER_COLS_BY_TIER["8gb"]),
        "l65_split_threshold": _L65_SPLIT_THRESHOLD_BY_TIER.get(tier, _L65_SPLIT_THRESHOLD_BY_TIER["8gb"]),
        "l2_category_workers": _L2_CATEGORY_WORKERS_BY_TIER.get(tier, _L2_CATEGORY_WORKERS_BY_TIER["8gb"]),
    }


def get_l3_persist_mode() -> str:
    """Resolve L3 persist mode: env override > tier auto-detect.

    Returns one of: "streaming", "hybrid", "in_memory".
    """
    raw = os.getenv("FFACT_L3_PERSIST_MODE", "auto").strip().lower()
    if raw not in {"", "auto"}:
        if raw in {"streaming", "hybrid", "in_memory"}:
            return raw
    return get_tier_config(get_memory_tier())["l3_persist_mode"]


def get_l3_streaming_buffer_cols() -> int:
    """Resolve L3 streaming buffer size: env override > tier auto-detect."""
    raw = os.getenv("FFACT_L3_STREAMING_BUFFER_COLS", "auto").strip().lower()
    if raw not in {"", "auto"}:
        try:
            return max(100, int(raw))
        except ValueError:
            pass
    return get_tier_config(get_memory_tier())["l3_streaming_buffer_cols"]


def get_l65_split_threshold() -> int:
    """Resolve L6.5 large-group split threshold: env override > tier auto.

    Returns 0 to disable splitting; otherwise the column count above which a
    group will be partitioned into balanced sub-tasks.
    """
    raw = os.getenv("FFACT_L65_SPLIT_THRESHOLD", "auto").strip().lower()
    if raw not in {"", "auto"}:
        try:
            value = int(raw)
            return max(0, value)
        except ValueError:
            pass
    return get_tier_config(get_memory_tier())["l65_split_threshold"]


def get_l2_category_workers() -> int:
    """Resolve L2 derived-category ThreadPool workers: env override > tier auto."""
    raw = os.getenv("FFACT_L2_CATEGORY_WORKERS", "auto").strip().lower()
    if raw not in {"", "auto"}:
        try:
            value = int(raw)
            return max(1, value)
        except ValueError:
            pass
    return get_tier_config(get_memory_tier())["l2_category_workers"]