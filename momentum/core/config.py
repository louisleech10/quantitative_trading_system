"""Momentum configuration definitions."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import FrozenSet, Iterator, Optional

import yaml

from momentum.core.logging import get_logger

logger = get_logger(__name__)

_OPTIMIZED_FRACDIFF_LAYERS = frozenset({"L1", "L2"})
_LEGACY_FRACDIFF_LAYERS = frozenset({"L1", "L2", "L3", "L4"})
_ALL_FRACDIFF_LAYERS = frozenset({"ALL"})
_SLOWPATH_NJOBS_BY_TIER_GB = {8: 2, 16: 4, 24: 6, 32: 8}


def get_l65_optimization_profile() -> str:
    raw = os.getenv("FFACT_L65_OPTIMIZATION_PROFILE", "optimized").strip().lower()
    if raw in {"", "optimized"}:
        return "optimized"
    if raw == "legacy":
        return "legacy"

    logger.warning(
        "Invalid FFACT_L65_OPTIMIZATION_PROFILE=%s, fallback to optimized",
        raw,
    )
    return "optimized"


def get_l7_codec_upgrade_enabled() -> bool:
    raw = os.getenv("FFACT_L7_CODEC_UPGRADE", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False

    logger.warning(
        "Invalid FFACT_L7_CODEC_UPGRADE=%s, fallback to disabled legacy codec",
        raw,
    )
    return False


def _parse_fracdiff_layers(raw: str) -> Optional[FrozenSet[str]]:
    tokens = [token.strip().upper() for token in raw.split(",") if token.strip()]
    if not tokens:
        return None
    if any(token == "ALL" for token in tokens):
        return _ALL_FRACDIFF_LAYERS

    layers = []
    invalid = []
    for token in tokens:
        if token.startswith("L") and token[1:].isdigit():
            layers.append(token)
        else:
            invalid.append(token)

    if invalid:
        logger.warning(
            "Invalid FFACT_FRACDIFF_APPLY_TO_LAYERS entries ignored: %s",
            invalid,
        )
    if not layers:
        return None
    return frozenset(layers)


def get_fracdiff_layers() -> FrozenSet[str]:
    raw = os.getenv("FFACT_FRACDIFF_APPLY_TO_LAYERS")
    if raw is not None:
        parsed = _parse_fracdiff_layers(raw)
        if parsed is not None:
            return parsed
        logger.warning(
            "Empty FFACT_FRACDIFF_APPLY_TO_LAYERS, fallback to optimized default L1,L2",
        )
        return _OPTIMIZED_FRACDIFF_LAYERS

    if get_l65_optimization_profile() == "legacy":
        return _LEGACY_FRACDIFF_LAYERS
    return _OPTIMIZED_FRACDIFF_LAYERS


def get_fracdiff_precision_override() -> Optional[float]:
    raw = os.getenv("FFACT_FRACDIFF_PRECISION_OVERRIDE")
    if raw is None or not raw.strip():
        return None

    try:
        precision = float(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid FFACT_FRACDIFF_PRECISION_OVERRIDE=%s, ignoring override",
            raw,
        )
        return None

    if precision <= 0.0:
        logger.warning(
            "FFACT_FRACDIFF_PRECISION_OVERRIDE must be positive, got %s; ignoring override",
            raw,
        )
        return None
    return precision


def get_fracdiff_precision(config_precision: float = 0.02) -> float:
    override = get_fracdiff_precision_override()
    if override is not None:
        return override

    try:
        precision = float(config_precision)
    except (TypeError, ValueError):
        logger.warning("Invalid fracdiff precision=%s, fallback to 0.02", config_precision)
        return 0.02

    if precision <= 0.0:
        logger.warning("Fracdiff precision must be positive, got %s; fallback to 0.02", config_precision)
        return 0.02
    return precision


def is_dstar_legacy_migration_enabled() -> bool:
    raw = os.getenv("FFACT_DSTAR_CACHE_MIGRATE_LEGACY", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_concurrent_symbols_override() -> Optional[int]:
    """Return the optional Feature Factory batch concurrent-symbol override."""

    raw = os.getenv("FFACT_CONCURRENT_SYMBOLS_OVERRIDE")
    if raw is None or not raw.strip():
        return None

    try:
        value = int(raw.strip())
    except ValueError:
        logger.warning(
            "Invalid FFACT_CONCURRENT_SYMBOLS_OVERRIDE=%s, ignoring override",
            raw,
        )
        return None

    if value <= 0:
        logger.warning(
            "FFACT_CONCURRENT_SYMBOLS_OVERRIDE must be positive, got %s; ignoring override",
            raw,
        )
        return None
    return value


def get_parallel_budget_enabled() -> bool:
    """Return whether batch parallel worker budget (C2) is enabled.

    預設 off：batch 子進程維持 n_jobs=1（與改動前行為一致）。
    """

    raw = os.getenv("FFACT_PARALLEL_BUDGET", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_batch_nested_enabled() -> bool:
    """Return whether ops forced batch safe mode (n_jobs=1 / 序列 symbol wave)."""

    raw = os.getenv("FFACT_BATCH_NESTED", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def get_batch_symbol_concurrency() -> int:
    """Return outer batch symbol concurrency injected by the parent wave."""

    raw = os.getenv("FFACT_BATCH_SYMBOL_CONCURRENCY")
    if raw is None or not str(raw).strip():
        return 1
    try:
        value = int(str(raw).strip())
    except ValueError:
        logger.warning(
            "Invalid FFACT_BATCH_SYMBOL_CONCURRENCY=%s, fallback to 1",
            raw,
        )
        return 1
    return max(1, value)


def get_slowpath_parallel_enabled() -> bool:
    """Return whether L6.5 joblib slow-path parallelism is enabled.

    Priority:
    1. If ``FFACT_L65_SLOWPATH_PARALLEL`` is explicitly set, honour it.
    2. Otherwise auto-detect from hardware tier:
       - Physical RAM ≥ 12 GB  (maps to ≥ 16 GB tier) → **ON**
       - Physical RAM <  12 GB (maps to   8 GB tier)   → **OFF**  ← OOM guard
       Mirrors ``TIER_THRESHOLDS`` in ``hardware_utils.py``.
    """
    raw = os.environ.get("FFACT_L65_SLOWPATH_PARALLEL")
    if raw is not None:
        raw = raw.strip().lower()
        if raw in {"1", "true", "yes", "on"}:
            return True
        if raw in {"", "0", "false", "no", "off"}:
            return False
        logger.warning(
            "Invalid FFACT_L65_SLOWPATH_PARALLEL=%s, falling back to auto-detect",
            raw,
        )

    # Auto-detect: query physical RAM via psutil (lazy import to avoid circular dep).
    # Threshold 12 GB matches TIER_THRESHOLDS: total ≥ 12 → "16gb", else "8gb".
    try:
        import psutil as _psutil_cfg  # noqa: PLC0415
        total_gb = _psutil_cfg.virtual_memory().total / 1024 ** 3
        if total_gb >= 12.0:
            logger.debug(
                "FFACT_L65_SLOWPATH_PARALLEL auto=ON  (%.1f GB physical RAM ≥ 12 GB tier threshold)",
                total_gb,
            )
            return True
        logger.debug(
            "FFACT_L65_SLOWPATH_PARALLEL auto=OFF (%.1f GB physical RAM < 12 GB, 8 GB tier OOM guard)",
            total_gb,
        )
        return False
    except Exception:
        # psutil unavailable or query failed → conservative default: OFF
        return False


def get_fast_adf_enabled() -> bool:
    """Return whether Phase 2 Fast ADF (Numba JIT) is enabled. Default ON.

    Disable with FFACT_USE_FAST_ADF=0 to force statsmodels ADF.
    """

    raw = os.getenv("FFACT_USE_FAST_ADF", "1").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"", "0", "false", "no", "off"}:
        return False
    logger.warning(
        "Invalid FFACT_USE_FAST_ADF=%s, fallback to enabled",
        raw,
    )
    return True


def get_slowpath_n_jobs(tier_gb: int, concurrent_symbols: int = 1) -> int:
    """Return safe L6.5 slow-path joblib worker count for the memory tier.

    ``concurrent_symbols`` 為 batch 外層同 wave 並行 symbol 數；預設 1 不影響單 symbol 路徑。
    """

    if get_batch_nested_enabled():
        logger.warning(
            "[L6.5] slow-path joblib forced safe mode (FFACT_BATCH_NESTED=1)"
        )
        return 1
    if not get_slowpath_parallel_enabled():
        return 1
    if sys.platform.startswith("win"):
        logger.warning("[L6.5] slow-path joblib disabled on Windows platform")
        return 1

    try:
        tier_value = int(tier_gb)
    except (TypeError, ValueError):
        tier_value = 8
    try:
        concurrent_value = int(concurrent_symbols)
    except (TypeError, ValueError):
        concurrent_value = 1
    concurrent_value = max(1, concurrent_value)
    tier_cap = _SLOWPATH_NJOBS_BY_TIER_GB.get(tier_value, 2)
    return max(1, tier_cap // concurrent_value)


@contextmanager
def batch_nested_environment(enabled: bool = True) -> Iterator[None]:
    """Temporarily mark child workers as batch execution context.

    ``FFACT_PARALLEL_BUDGET=off`` 時仍注入 ``FFACT_BATCH_NESTED=1``（維持現狀 n_jobs=1）。
    budget on 時不注入 nested，改由 ``FFACT_BATCH_SYMBOL_CONCURRENCY`` 傳遞外層並行度。
    """

    previous = os.environ.get("FFACT_BATCH_NESTED")
    if enabled and not get_parallel_budget_enabled():
        os.environ["FFACT_BATCH_NESTED"] = "1"
    elif not enabled:
        os.environ.pop("FFACT_BATCH_NESTED", None)

    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("FFACT_BATCH_NESTED", None)
        else:
            os.environ["FFACT_BATCH_NESTED"] = previous


def _default_project_root() -> Path:
    current = Path(__file__).resolve()
    # core/config.py -> core -> momentum -> project root
    # parents[0]=core, parents[1]=momentum, parents[2]=project_root
    if len(current.parents) >= 3:
        return current.parents[2]
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
