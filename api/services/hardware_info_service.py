"""組裝 Feature Factory 硬體資訊與 RAM tier 運維設定。"""

import os
import shutil
from pathlib import Path
from typing import Any, Dict

from momentum.FeatureEngineering.utils.hardware_utils import (
    TIER_THRESHOLDS,
    get_memory_tier,
    get_tier_config,
)

try:
    import psutil
except ImportError:
    psutil = None


def _build_cpu_info() -> Dict[str, Any]:
    """組裝 CPU 資訊，psutil 缺席或讀取失敗時安全降級。"""
    logical_cores = os.cpu_count() or 1
    physical_cores = logical_cores
    usage_pct = 0.0

    if psutil is None:
        return {
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "usage_pct": usage_pct,
        }

    try:
        physical_cores = psutil.cpu_count(logical=False) or logical_cores
        usage_pct = round(float(psutil.cpu_percent(interval=0.1)), 1)
    except OSError:
        physical_cores = logical_cores
        usage_pct = 0.0

    return {
        "logical_cores": logical_cores,
        "physical_cores": physical_cores,
        "usage_pct": usage_pct,
    }


def _build_memory_info() -> Dict[str, float]:
    """組裝記憶體資訊，psutil 缺席或讀取失敗時安全降級。"""
    if psutil is None:
        return {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "used_pct": 0.0,
        }

    try:
        virtual_memory = psutil.virtual_memory()
        return {
            "total_gb": round(virtual_memory.total / 1024 ** 3, 1),
            "available_gb": round(virtual_memory.available / 1024 ** 3, 1),
            "used_pct": round(float(virtual_memory.percent), 1),
        }
    except OSError:
        return {
            "total_gb": 0.0,
            "available_gb": 0.0,
            "used_pct": 0.0,
        }


def _build_disk_info(data_cache_path: Path) -> Dict[str, Any]:
    """組裝 data_cache 磁碟資訊，路徑缺席或讀取失敗時安全降級。"""
    resolved_path = data_cache_path.resolve()
    empty_disk_info = {
        "path": str(resolved_path),
        "free_gb": 0.0,
        "total_gb": 0.0,
        "used_pct": 0.0,
    }

    if not resolved_path.exists():
        return empty_disk_info

    try:
        disk_usage = shutil.disk_usage(resolved_path)
    except OSError:
        return empty_disk_info

    return {
        "path": str(resolved_path),
        "free_gb": round(disk_usage.free / 1024 ** 3, 1),
        "total_gb": round(disk_usage.total / 1024 ** 3, 1),
        "used_pct": round(disk_usage.used / disk_usage.total * 100, 1),
    }


def build_hardware_info(data_cache_path: Path) -> Dict[str, Any]:
    """組裝硬體資訊、建議設定、實際設定來源與完整 tier 表。"""
    memory_tier = get_memory_tier()
    tier_config = get_tier_config(memory_tier)

    # Build full tier table (all tiers × all params) so the frontend never
    # hardcodes values; if hardware_utils.py changes, the UI updates.
    all_tiers = ["8gb", "16gb", "24gb", "32gb"]
    tier_table = {tier: get_tier_config(tier) for tier in all_tiers}

    # Effective ("applied") settings — env var takes precedence over auto.
    # Each entry: { value, source: "auto"|"env", env_var }
    env_keys = {
        "l65_workers": "FFACT_L65_WORKERS",
        "cgsa_memory_buffer": "FFACT_CGSA_MEMORY_BUFFER",
        "l7_workers": "FFACT_L7_WORKERS",
        "multi_tf_max_workers": "FFACT_MULTI_TF_MAX_WORKERS",
        "layer3_chunk_size": "FFACT_LAYER3_CHUNK_SIZE",
        "l3_persist_mode": "FFACT_L3_PERSIST_MODE",
        "l3_streaming_buffer_cols": "FFACT_L3_STREAMING_BUFFER_COLS",
        "l65_split_threshold": "FFACT_L65_SPLIT_THRESHOLD",
        "l2_category_workers": "FFACT_L2_CATEGORY_WORKERS",
        "cgsa_shard_bytes": "FFACT_CGSA_SHARD_BYTES",
    }
    applied_settings: Dict[str, Dict[str, Any]] = {}
    for key, env_var in env_keys.items():
        env_raw = os.environ.get(env_var, "").strip()
        is_overridden = bool(env_raw) and env_raw.lower() != "auto"
        applied_settings[key] = {
            "value": tier_config.get(key),
            "source": "env" if is_overridden else "auto",
            "env_var": env_var,
            "env_raw": env_raw if is_overridden else None,
        }

    return {
        "memory_tier": memory_tier,
        "cpu": _build_cpu_info(),
        "memory": _build_memory_info(),
        "disk": _build_disk_info(data_cache_path),
        # Legacy keys preserved for backward compatibility.
        "recommended_settings": {
            "FFACT_L65_WORKERS": tier_config["l65_workers"],
            "FFACT_CGSA_MEMORY_BUFFER": tier_config["cgsa_memory_buffer"],
            "FFACT_L7_WORKERS": tier_config["l7_workers"],
            "FFACT_L7_COMPACTOR_ENABLED": 1,
            "FFACT_MULTI_TF_MAX_WORKERS": tier_config["multi_tf_max_workers"],
            "FFACT_LAYER3_CHUNK_SIZE": tier_config["layer3_chunk_size"],
        },
        # New fields (V8 final / v8fix13 optimization):
        "applied_settings": applied_settings,
        "tier_table": tier_table,
        "tier_thresholds_gb": [
            {"tier": tier, "min_total_gb": threshold}
            for threshold, tier in TIER_THRESHOLDS
        ],
    }
