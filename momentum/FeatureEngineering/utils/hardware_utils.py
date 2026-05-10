"""Hardware tier helpers for Feature Factory optimization toggles."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from momentum.core.config import get_concurrent_symbols_override

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

# L6.5 preprocessing ThreadPool workers.
# OOM Fix (2026-04-25): 8 GB tier reduced from 4 → 2. With CGSA-parallel
# multi-TF + L6.5 large groups (e.g. WorldQuant ~16k cols), 4 concurrent
# workers on M1 8GB easily push RSS past 6 GB and trigger SIGKILL when a
# frontend dev server / browser is also resident. 2 workers keeps the peak
# inside ~3.5 GB while only adding ~30-40% to L6.5 wall time.
_WORKERS_BY_TIER: Dict[str, int] = {
    "8gb": 2,
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
# OOM Fix (2026-04-25): 8 GB lowered 4000 → 2000 so each sub-task buffers a
# smaller column slice (~half the previous peak). Combined with L65_WORKERS=2
# this caps L6.5 transient RSS at ~3.5 GB on M1 8GB.
_L65_SPLIT_THRESHOLD_BY_TIER: Dict[str, int] = {
    "8gb": 2000,
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

# CGSA shard target bytes per shard (Phase B Phase 1).
# Each L1-L6 group's float32 ndarray is sliced column-wise into shards of
# ~target_bytes so that L6.5/L7 raw-sink can stream per-shard parts and
# release source .npy bytes immediately. Smaller shard = lower in-flight peak
# but more files / manifest overhead. Floor 32 MiB / cap 512 MiB enforced.
_CGSA_SHARD_BYTES_BY_TIER: Dict[str, int] = {
    "8gb": 96 * 1024 * 1024,    # ~300 MiB transform peak (3x in-RAM)
    "16gb": 192 * 1024 * 1024,
    "24gb": 256 * 1024 * 1024,
    "32gb": 384 * 1024 * 1024,
}
_CGSA_SHARD_FLOOR_BYTES = 32 * 1024 * 1024
_CGSA_SHARD_CAP_BYTES = 512 * 1024 * 1024

_CONCURRENT_SYMBOLS_BY_TIER_GB: Dict[int, int] = {
    8: 1,
    16: 1,
    24: 2,
    32: 3,
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
    tier_gb = _parse_tier_gb(tier)
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
        "cgsa_shard_bytes": _CGSA_SHARD_BYTES_BY_TIER.get(tier, _CGSA_SHARD_BYTES_BY_TIER["8gb"]),
        "concurrent_symbols": get_tier_concurrent_symbols(tier_gb),
    }


def _parse_tier_gb(tier: str) -> int:
    """Parse a tier label such as '8gb' into an integer GB value."""

    try:
        return int(str(tier).strip().lower().replace("gb", ""))
    except ValueError:
        return 8


def get_current_tier_gb() -> int:
    """Return the current auto-detected memory tier as an integer GB value."""

    return _parse_tier_gb(get_memory_tier())


def get_tier_concurrent_symbols(tier_gb: int) -> int:
    """Return tier-aware safe concurrent-symbol count for heavy batch execution."""

    override = get_concurrent_symbols_override()
    if override is not None:
        return override
    return _CONCURRENT_SYMBOLS_BY_TIER_GB.get(int(tier_gb), 1)


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


def _parse_size_bytes(raw: str) -> Optional[int]:
    """Parse a size string like ``96MiB``/``128MB``/``100000000`` into bytes.

    Returns None for invalid input. Accepted units (case-insensitive):
    KiB/MiB/GiB (1024-base) and KB/MB/GB (1000-base). Bare digits = bytes.
    """
    text = raw.strip().lower()
    if not text:
        return None
    units = (
        ("gib", 1024 ** 3), ("mib", 1024 ** 2), ("kib", 1024),
        ("gb", 1000 ** 3), ("mb", 1000 ** 2), ("kb", 1000),
        ("b", 1),
    )
    for suffix, mult in units:
        if text.endswith(suffix):
            head = text[: -len(suffix)].strip()
            try:
                return int(float(head) * mult)
            except (ValueError, TypeError):
                return None
    try:
        return int(text)
    except ValueError:
        return None


def get_cgsa_shard_bytes() -> int:
    """Resolve CGSA per-shard target bytes: env override > tier auto-detect.

    Env: ``FFACT_CGSA_SHARD_BYTES`` (e.g. ``96MiB``, ``134217728``, ``auto``).
    Result is clamped to [floor, cap] to avoid pathological file count or
    memory peaks. Invalid env values fall back to tier default with a warning.
    """
    import logging
    raw = os.getenv("FFACT_CGSA_SHARD_BYTES", "auto").strip().lower()
    if raw not in {"", "auto"}:
        parsed = _parse_size_bytes(raw)
        if parsed is not None and parsed > 0:
            return max(_CGSA_SHARD_FLOOR_BYTES, min(_CGSA_SHARD_CAP_BYTES, parsed))
        logging.getLogger(__name__).warning(
            "[hardware] Invalid FFACT_CGSA_SHARD_BYTES=%r; falling back to tier default",
            raw,
        )
    tier_value = get_tier_config(get_memory_tier())["cgsa_shard_bytes"]
    return max(_CGSA_SHARD_FLOOR_BYTES, min(_CGSA_SHARD_CAP_BYTES, int(tier_value)))


def get_cgsa_per_layer_pipeline_enabled() -> bool:
    """Phase B Phase 2 master switch — default OFF.

    When ON, FeatureFactory will (in a future release) flush each L1-L6 layer
    output through the raw-sink before starting the next layer, capping
    cgsa_work peak bytes to ``max(single_layer_output)`` instead of
    ``sum(L1..L6 outputs)``. Requires:
      1. Cross-layer dependency audit (``Tier A`` — fully closed) at startup.
      2. Golden-output regression gate (Phase 2 vs Phase 1 per-cell allclose).
    Until both gates land, env=1 is accepted but the factory logs a warning
    and stays on Phase 1 behavior to preserve data correctness.
    """
    raw = os.getenv("FFACT_CGSA_PIPELINE_PER_LAYER", "0").strip().lower()
    return raw in {"1", "true", "on", "yes"}