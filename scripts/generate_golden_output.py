from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.core.logging import get_logger
from momentum.factories import create_feature_factory


logger = get_logger(__name__)


DEFAULT_OUTPUT_DIR = Path("data_cache/golden_output")
DEFAULT_SYMBOL = "ETHUSDT"
DEFAULT_PRIMARY_TF = "1h"
DEFAULT_TRAINING_TFS = ["1h", "12h"]


DEFAULT_REDUCED_CONFIG_OVERRIDE: Dict[str, Any] = {
    "timeframes": {
        "primary": DEFAULT_PRIMARY_TF,
        "training": DEFAULT_TRAINING_TFS,
        "alignment": "point_in_time",
        "alignment_mode": "open_minus",
    },
    "data_sources": {
        "enabled_sources": ["close"],
        "synthetic_sources": [],
    },
    "atomic_indicators": {
        "trend": {"enabled": True},
        "momentum": {"enabled": True},
        "volatility": {"enabled": False},
        "volume": {"enabled": False},
        "cycle": {"enabled": False},
        "pattern": {"enabled": False},
        "statistics": {"enabled": False},
        "microstructure": {"enabled": False},
        "entropy": {"enabled": False},
        "tail_risk": {"enabled": False},
    },
    "rolling_aggregation": {
        "enabled": True,
        "windows": [5, 21, 55],
        "aggregators": ["mean", "std", "rank"],
    },
    "preprocessing": {"enabled": False},
}


L1_ONLY_OVERRIDE: Dict[str, Any] = {
    "operators": {"enabled": False},
    "rolling_aggregation": {"enabled": False},
    "lag_features": {"enabled": False},
    "cross_sectional": {"enabled": False},
    "meta_features": {"enabled": False},
    "preprocessing": {"enabled": False},
}


class FailureType(Enum):
    IO_ERROR = "io_error"
    OOM = "oom"
    VALIDATION = "validation"
    CONFIG = "config"
    UNKNOWN = "unknown"


class GoldenOutputError(RuntimeError):
    def __init__(self, message: str, failure_type: FailureType):
        super().__init__(message)
        self.failure_type = failure_type


@dataclass
class GoldenArtifacts:
    parquet_path: Path
    columns_json_path: Path
    nan_mask_path: Path
    structural_path: Path
    baseline_tier: str
    feature_count: int


def _deep_merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def _classify_failure(error: Exception) -> FailureType:
    if isinstance(error, (OSError, IOError)):
        return FailureType.IO_ERROR
    if isinstance(error, MemoryError):
        return FailureType.OOM
    if isinstance(error, (ValueError, KeyError, json.JSONDecodeError)):
        return FailureType.CONFIG

    message = str(error).lower()
    if "memory" in message or "oom" in message:
        return FailureType.OOM
    if "validation" in message:
        return FailureType.VALIDATION
    return FailureType.UNKNOWN


def _load_env_reduced_override() -> Dict[str, Any]:
    raw = os.getenv("GOLDEN_CONFIG_OVERRIDE", "").strip()
    if not raw:
        return dict(DEFAULT_REDUCED_CONFIG_OVERRIDE)

    path = Path(raw)
    try:
        if path.exists() and path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = json.loads(raw)
    except Exception as error:
        raise GoldenOutputError(
            f"Invalid GOLDEN_CONFIG_OVERRIDE: {error}",
            failure_type=FailureType.CONFIG,
        ) from error

    if not isinstance(payload, dict):
        raise GoldenOutputError(
            "GOLDEN_CONFIG_OVERRIDE must be JSON object or path to JSON object file",
            failure_type=FailureType.CONFIG,
        )

    return _deep_merge_dict(dict(DEFAULT_REDUCED_CONFIG_OVERRIDE), payload)


def _timeframe_override(primary_tf: str, training_tfs: List[str]) -> Dict[str, Any]:
    return {
        "timeframes": {
            "primary": primary_tf,
            "training": training_tfs,
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        }
    }


def _build_structural_payload(
    symbol: str,
    primary_tf: str,
    training_tfs: List[str],
    numeric_result: Any,
    full_result: Optional[Any],
    baseline_tier: str,
    generated_at_utc: str,
    duration_seconds: float,
) -> Dict[str, Any]:
    numeric_features = numeric_result.features_df
    numeric_nan_ratio = {
        "mean": float(numeric_features.isna().mean().mean()) if not numeric_features.empty else 0.0,
        "max": float(numeric_features.isna().mean().max()) if not numeric_features.empty else 0.0,
        "min": float(numeric_features.isna().mean().min()) if not numeric_features.empty else 0.0,
    }

    structural: Dict[str, Any] = {
        "symbol": symbol,
        "primary_timeframe": primary_tf,
        "training_timeframes": training_tfs,
        "generated_at_utc": generated_at_utc,
        "duration_seconds": duration_seconds,
        "numeric_baseline_tier": baseline_tier,
        "numeric_feature_count": int(numeric_result.feature_count),
        "numeric_shape": [int(numeric_features.shape[0]), int(numeric_features.shape[1])],
        "numeric_nan_ratio_summary": numeric_nan_ratio,
        "numeric_layer_counts": dict(numeric_result.layer_counts),
        "tier1_structural": {
            "available": full_result is not None,
            "todo_marker": (
                "tier1_structural_baseline_pending_large_memory_env"
                if full_result is None
                else ""
            ),
        },
    }

    if full_result is not None:
        full_features = full_result.features_df
        structural["tier1_structural"].update(
            {
                "available": True,
                "feature_count": int(full_result.feature_count),
                "shape": [int(full_features.shape[0]), int(full_features.shape[1])],
                "nan_ratio_summary": {
                    "mean": float(full_features.isna().mean().mean()) if not full_features.empty else 0.0,
                    "max": float(full_features.isna().mean().max()) if not full_features.empty else 0.0,
                    "min": float(full_features.isna().mean().min()) if not full_features.empty else 0.0,
                },
                "layer_counts": dict(full_result.layer_counts),
                "columns": [str(col) for col in full_features.columns],
                "todo_marker": "",
            }
        )

    return structural


def _validate_numeric_output(features_df: pd.DataFrame) -> None:
    if features_df is None or features_df.empty:
        raise GoldenOutputError("Golden features dataframe is empty", failure_type=FailureType.VALIDATION)

    values = features_df.to_numpy(dtype=np.float64, copy=False)
    if np.isinf(values).any():
        raise GoldenOutputError(
            "Golden features contain non-finite values (inf/-inf)",
            failure_type=FailureType.VALIDATION,
        )


def _save_numeric_artifacts(
    output_dir: Path,
    symbol: str,
    primary_tf: str,
    training_tfs: List[str],
    features_df: pd.DataFrame,
) -> Dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    tf_token = "2tf" if len(training_tfs) >= 2 else f"{len(training_tfs)}tf"
    parquet_path = output_dir / f"{symbol}_{primary_tf}_{tf_token}_golden.parquet"
    columns_json_path = output_dir / "columns.json"
    nan_mask_path = output_dir / "nan_mask.npz"

    features_df.to_parquet(parquet_path)

    columns_payload = [str(col) for col in features_df.columns]
    columns_json_path.write_text(
        json.dumps(columns_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    nan_masks = {str(col): features_df[col].isna().to_numpy(dtype=bool) for col in features_df.columns}
    np.savez_compressed(nan_mask_path, **nan_masks)

    return {
        "parquet_path": parquet_path,
        "columns_json_path": columns_json_path,
        "nan_mask_path": nan_mask_path,
    }


def _run_pipeline(
    factory: Any,
    symbol: str,
    primary_tf: str,
    config_override: Dict[str, Any],
    force_regenerate: bool,
) -> Any:
    return factory.generate_features(
        symbol=symbol,
        timeframe=primary_tf,
        config_override=config_override,
        force_regenerate=force_regenerate,
        persist=False,
    )


def generate_golden_output(
    symbol: str = DEFAULT_SYMBOL,
    primary_tf: str = DEFAULT_PRIMARY_TF,
    training_tfs: Optional[List[str]] = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    force_regenerate: bool = True,
    attempt_tier1_full: bool = False,
    allow_data_gaps: bool = True,
) -> GoldenArtifacts:
    start_perf = time.perf_counter()
    timeframes = list(training_tfs or DEFAULT_TRAINING_TFS)
    tf_override = _timeframe_override(primary_tf=primary_tf, training_tfs=timeframes)

    logger.info("[golden] Starting golden output generation for %s (%s)", symbol, ",".join(timeframes))
    if allow_data_gaps:
        logger.warning("[golden] Continuity validation disabled for golden generation (allow_data_gaps=true)")
    factory = create_feature_factory(validate_continuity=not allow_data_gaps)

    full_result = None
    if attempt_tier1_full:
        try:
            full_result = _run_pipeline(
                factory=factory,
                symbol=symbol,
                primary_tf=primary_tf,
                config_override=tf_override,
                force_regenerate=force_regenerate,
            )
            logger.info("[golden] Tier 1 structural baseline captured with %d features", full_result.feature_count)
        except Exception as error:
            failure_type = _classify_failure(error)
            logger.warning("[golden] Tier 1 full-config run failed (%s): %s", failure_type.value, error)
    else:
        logger.info("[golden] Tier 1 full-config run skipped (attempt_tier1_full=false)")

    reduced_override = _deep_merge_dict(tf_override, _load_env_reduced_override())

    numeric_result = None
    baseline_tier = "tier2_reduced"
    try:
        numeric_result = _run_pipeline(
            factory=factory,
            symbol=symbol,
            primary_tf=primary_tf,
            config_override=reduced_override,
            force_regenerate=force_regenerate,
        )
        logger.info("[golden] Tier 2 reduced baseline generated with %d features", numeric_result.feature_count)
    except Exception as reduced_error:
        reduced_failure = _classify_failure(reduced_error)
        logger.warning(
            "[golden] Tier 2 reduced run failed (%s): %s. Fallback to Tier 3 L1-only",
            reduced_failure.value,
            reduced_error,
        )

        baseline_tier = "tier3_l1_only"
        l1_override = _deep_merge_dict(reduced_override, L1_ONLY_OVERRIDE)
        try:
            numeric_result = _run_pipeline(
                factory=factory,
                symbol=symbol,
                primary_tf=primary_tf,
                config_override=l1_override,
                force_regenerate=force_regenerate,
            )
            logger.info("[golden] Tier 3 L1-only baseline generated with %d features", numeric_result.feature_count)
        except Exception as l1_error:
            failure_type = _classify_failure(l1_error)
            raise GoldenOutputError(
                f"Failed to generate any golden baseline: {l1_error}",
                failure_type=failure_type,
            ) from l1_error

    _validate_numeric_output(numeric_result.features_df)
    artifact_paths = _save_numeric_artifacts(
        output_dir=output_dir,
        symbol=symbol,
        primary_tf=primary_tf,
        training_tfs=timeframes,
        features_df=numeric_result.features_df,
    )

    duration_seconds = time.perf_counter() - start_perf
    generated_at_utc = pd.Timestamp.utcnow().isoformat()
    structural_payload = _build_structural_payload(
        symbol=symbol,
        primary_tf=primary_tf,
        training_tfs=timeframes,
        numeric_result=numeric_result,
        full_result=full_result,
        baseline_tier=baseline_tier,
        generated_at_utc=generated_at_utc,
        duration_seconds=duration_seconds,
    )

    structural_path = output_dir / "golden_structural.json"
    structural_path.write_text(
        json.dumps(structural_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "[golden] Completed in %.2fs | tier=%s | features=%d | parquet=%s",
        duration_seconds,
        baseline_tier,
        numeric_result.feature_count,
        artifact_paths["parquet_path"],
    )

    return GoldenArtifacts(
        parquet_path=artifact_paths["parquet_path"],
        columns_json_path=artifact_paths["columns_json_path"],
        nan_mask_path=artifact_paths["nan_mask_path"],
        structural_path=structural_path,
        baseline_tier=baseline_tier,
        feature_count=int(numeric_result.feature_count),
    )


def _parse_training_tfs(raw: str) -> List[str]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        return list(DEFAULT_TRAINING_TFS)
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Feature Factory golden output artifacts")
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="Target symbol, default ETHUSDT")
    parser.add_argument("--primary-tf", default=DEFAULT_PRIMARY_TF, help="Primary timeframe, default 1h")
    parser.add_argument(
        "--training-tfs",
        default=",".join(DEFAULT_TRAINING_TFS),
        help="Comma separated training timeframes, default 1h,12h",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for golden artifacts",
    )
    parser.set_defaults(force_regenerate=True, attempt_tier1_full=False, allow_data_gaps=True)
    parser.add_argument(
        "--force-regenerate",
        dest="force_regenerate",
        action="store_true",
        help="Force recomputation and skip feature cache (default)",
    )
    parser.add_argument(
        "--no-force-regenerate",
        dest="force_regenerate",
        action="store_false",
        help="Allow cache usage when config hash matches",
    )
    parser.add_argument(
        "--attempt-tier1-full",
        dest="attempt_tier1_full",
        action="store_true",
        help="Attempt Tier 1 full-config structural run (can be memory heavy)",
    )
    parser.add_argument(
        "--skip-tier1-full",
        dest="attempt_tier1_full",
        action="store_false",
        help="Skip Tier 1 full-config run and use reduced baseline path (default)",
    )
    parser.add_argument(
        "--allow-data-gaps",
        dest="allow_data_gaps",
        action="store_true",
        help="Disable continuity validation for golden generation (default)",
    )
    parser.add_argument(
        "--strict-continuity",
        dest="allow_data_gaps",
        action="store_false",
        help="Enable strict continuity validation when reading klines",
    )
    args = parser.parse_args()

    try:
        artifacts = generate_golden_output(
            symbol=args.symbol,
            primary_tf=args.primary_tf,
            training_tfs=_parse_training_tfs(args.training_tfs),
            output_dir=Path(args.output_dir),
            force_regenerate=args.force_regenerate,
            attempt_tier1_full=args.attempt_tier1_full,
            allow_data_gaps=args.allow_data_gaps,
        )
    except GoldenOutputError as error:
        logger.error("[golden] Failed (%s): %s", error.failure_type.value, error)
        return 1
    except Exception as error:
        failure_type = _classify_failure(error)
        logger.error("[golden] Failed (%s): %s", failure_type.value, error, exc_info=True)
        return 1

    logger.info(
        "[golden] Artifacts ready: parquet=%s columns=%s nan_mask=%s structural=%s",
        artifacts.parquet_path,
        artifacts.columns_json_path,
        artifacts.nan_mask_path,
        artifacts.structural_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())