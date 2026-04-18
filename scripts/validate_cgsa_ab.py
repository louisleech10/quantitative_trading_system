from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.core.logging import get_logger  # noqa: E402


logger = get_logger(__name__)


LAYER_ATOL: Dict[str, float] = {
    "L1": 1e-7,
    "L2": 1e-6,
}

L3_AGGREGATOR_ATOL: Dict[str, float] = {
    "mean": 1e-6,
    "std": 1e-6,
    "min": 1e-6,
    "max": 1e-6,
    "range": 1e-6,
    "zscore": 1e-6,
    "rank": 1e-6,
    "slope": 1e-5,
    "skew": 1e-4,
    "kurt": 1e-4,
}

LAYER_ORDER = ["L1", "L2", "L3"]
DEFAULT_ATOL = 1e-4
NAN_RATIO_TOLERANCE = 1e-6


class FailureType(str, Enum):
    """Failure category for A/B validation flow."""

    IO_ERROR = "io_error"
    VALIDATION = "validation"
    CONFIG = "config"


class ValidationInputError(RuntimeError):
    """Input error with explicit failure type."""

    def __init__(self, message: str, failure_type: FailureType) -> None:
        super().__init__(message)
        self.failure_type = failure_type


@dataclass
class LayerComparisonResult:
    """Layer comparison output payload."""

    status: str
    layer: str
    compared_columns: int
    atol: float
    same_order: bool
    only_in_cgsa_count: int
    only_in_legacy_count: int
    nan_mask_equal: bool
    max_abs_diff: float
    failed_columns: list[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "layer": self.layer,
            "compared_columns": self.compared_columns,
            "atol": self.atol,
            "same_order": self.same_order,
            "only_in_cgsa_count": self.only_in_cgsa_count,
            "only_in_legacy_count": self.only_in_legacy_count,
            "nan_mask_equal": self.nan_mask_equal,
            "max_abs_diff": self.max_abs_diff,
            "failed_columns": self.failed_columns,
        }


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationInputError(f"JSON file not found: {path}", failure_type=FailureType.IO_ERROR) from exc
    except json.JSONDecodeError as exc:
        raise ValidationInputError(f"Invalid JSON file: {path} ({exc})", failure_type=FailureType.CONFIG) from exc

    if not isinstance(payload, dict):
        raise ValidationInputError(f"JSON payload must be object: {path}", failure_type=FailureType.CONFIG)
    return payload


def _resolve_layer_path(path_str: str, base_dir: Path) -> Path:
    candidate = Path(path_str)
    if not candidate.is_absolute():
        candidate = (base_dir / candidate).resolve()
    return candidate


def _load_layer_map(path: Path) -> Dict[str, Path]:
    payload = _load_json(path)
    layer_map: Dict[str, Path] = {}
    for layer, raw_path in payload.items():
        layer_name = str(layer).strip().upper()
        if not layer_name:
            continue
        if not isinstance(raw_path, str):
            raise ValidationInputError(
                f"Layer path must be string for {layer_name}",
                failure_type=FailureType.CONFIG,
            )
        resolved = _resolve_layer_path(raw_path, base_dir=path.parent)
        if not resolved.exists():
            raise ValidationInputError(
                f"Layer artifact not found for {layer_name}: {resolved}",
                failure_type=FailureType.IO_ERROR,
            )
        layer_map[layer_name] = resolved
    return layer_map


def _load_dataframe(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".pkl", ".pickle"}:
        return pd.read_pickle(path)

    raise ValidationInputError(
        f"Unsupported artifact format for {path}. Expected parquet/csv/pkl.",
        failure_type=FailureType.CONFIG,
    )


def _max_abs_diff(lhs: np.ndarray, rhs: np.ndarray) -> float:
    diff = np.abs(lhs - rhs)
    finite = diff[np.isfinite(diff)]
    if finite.size == 0:
        return 0.0
    return float(np.max(finite))


def _extract_l3_aggregator(column_name: str) -> str:
    tokens = [token.lower() for token in str(column_name).split("_")]
    for token in reversed(tokens):
        if token in L3_AGGREGATOR_ATOL:
            return token
    return "default"


def _compare_basic_layer(
    layer: str,
    cgsa_df: pd.DataFrame,
    legacy_df: pd.DataFrame,
    atol: float,
) -> LayerComparisonResult:
    cgsa_columns = [str(col) for col in cgsa_df.columns]
    legacy_columns = [str(col) for col in legacy_df.columns]
    cgsa_set = set(cgsa_columns)
    legacy_set = set(legacy_columns)

    only_in_cgsa = sorted(cgsa_set - legacy_set)
    only_in_legacy = sorted(legacy_set - cgsa_set)
    same_order = cgsa_columns == legacy_columns

    failed_columns: list[Dict[str, Any]] = []
    max_abs_diff = 0.0
    nan_mask_equal = True

    comparable_columns = [col for col in legacy_columns if col in cgsa_set]
    for column in comparable_columns:
        cgsa_arr = cgsa_df[column].to_numpy(dtype=np.float64, copy=False)
        legacy_arr = legacy_df[column].to_numpy(dtype=np.float64, copy=False)

        current_nan_equal = bool(np.array_equal(np.isnan(cgsa_arr), np.isnan(legacy_arr)))
        nan_mask_equal = nan_mask_equal and current_nan_equal

        if cgsa_arr.shape != legacy_arr.shape:
            failed_columns.append(
                {
                    "column": column,
                    "reason": "shape_mismatch",
                    "cgsa_shape": list(cgsa_arr.shape),
                    "legacy_shape": list(legacy_arr.shape),
                }
            )
            continue

        if not np.allclose(cgsa_arr, legacy_arr, atol=atol, rtol=0.0, equal_nan=True):
            column_diff = _max_abs_diff(cgsa_arr, legacy_arr)
            max_abs_diff = max(max_abs_diff, column_diff)
            failed_columns.append(
                {
                    "column": column,
                    "reason": "value_mismatch",
                    "max_abs_diff": column_diff,
                    "atol": atol,
                }
            )
            continue

        max_abs_diff = max(max_abs_diff, _max_abs_diff(cgsa_arr, legacy_arr))

    passed = (
        not only_in_cgsa
        and not only_in_legacy
        and same_order
        and nan_mask_equal
        and not failed_columns
    )

    return LayerComparisonResult(
        status="passed" if passed else "failed",
        layer=layer,
        compared_columns=len(comparable_columns),
        atol=atol,
        same_order=same_order,
        only_in_cgsa_count=len(only_in_cgsa),
        only_in_legacy_count=len(only_in_legacy),
        nan_mask_equal=nan_mask_equal,
        max_abs_diff=max_abs_diff,
        failed_columns=failed_columns,
    )


def _compare_l3_layer(layer: str, cgsa_df: pd.DataFrame, legacy_df: pd.DataFrame) -> LayerComparisonResult:
    cgsa_columns = [str(col) for col in cgsa_df.columns]
    legacy_columns = [str(col) for col in legacy_df.columns]
    cgsa_set = set(cgsa_columns)
    legacy_set = set(legacy_columns)

    only_in_cgsa = sorted(cgsa_set - legacy_set)
    only_in_legacy = sorted(legacy_set - cgsa_set)
    same_order = cgsa_columns == legacy_columns

    failed_columns: list[Dict[str, Any]] = []
    max_abs_diff = 0.0
    nan_mask_equal = True

    comparable_columns = [col for col in legacy_columns if col in cgsa_set]
    for column in comparable_columns:
        aggregator = _extract_l3_aggregator(column)
        atol = L3_AGGREGATOR_ATOL.get(aggregator, DEFAULT_ATOL)

        cgsa_arr = cgsa_df[column].to_numpy(dtype=np.float64, copy=False)
        legacy_arr = legacy_df[column].to_numpy(dtype=np.float64, copy=False)

        current_nan_equal = bool(np.array_equal(np.isnan(cgsa_arr), np.isnan(legacy_arr)))
        nan_mask_equal = nan_mask_equal and current_nan_equal

        if cgsa_arr.shape != legacy_arr.shape:
            failed_columns.append(
                {
                    "column": column,
                    "reason": "shape_mismatch",
                    "cgsa_shape": list(cgsa_arr.shape),
                    "legacy_shape": list(legacy_arr.shape),
                }
            )
            continue

        if not np.allclose(cgsa_arr, legacy_arr, atol=atol, rtol=0.0, equal_nan=True):
            column_diff = _max_abs_diff(cgsa_arr, legacy_arr)
            max_abs_diff = max(max_abs_diff, column_diff)
            failed_columns.append(
                {
                    "column": column,
                    "reason": "value_mismatch",
                    "aggregator": aggregator,
                    "max_abs_diff": column_diff,
                    "atol": atol,
                }
            )
            continue

        max_abs_diff = max(max_abs_diff, _max_abs_diff(cgsa_arr, legacy_arr))

    passed = (
        not only_in_cgsa
        and not only_in_legacy
        and same_order
        and nan_mask_equal
        and not failed_columns
    )

    return LayerComparisonResult(
        status="passed" if passed else "failed",
        layer=layer,
        compared_columns=len(comparable_columns),
        atol=DEFAULT_ATOL,
        same_order=same_order,
        only_in_cgsa_count=len(only_in_cgsa),
        only_in_legacy_count=len(only_in_legacy),
        nan_mask_equal=nan_mask_equal,
        max_abs_diff=max_abs_diff,
        failed_columns=failed_columns,
    )


def _combine_layer_columns(layer_frames: Mapping[str, pd.DataFrame]) -> tuple[list[str], float]:
    merged_columns: list[str] = []
    nan_ratio_sum = 0.0
    total_columns = 0

    for layer in LAYER_ORDER:
        layer_df = layer_frames.get(layer)
        if layer_df is None or layer_df.empty:
            continue

        merged_columns.extend([str(col) for col in layer_df.columns])
        layer_nan_ratio_sum = float(layer_df.isna().mean().sum())
        nan_ratio_sum += layer_nan_ratio_sum
        total_columns += int(layer_df.shape[1])

    if total_columns == 0:
        return merged_columns, 0.0

    mean_nan_ratio = float(nan_ratio_sum / total_columns)
    return merged_columns, mean_nan_ratio


def _parse_structural_baseline(path: Path) -> Dict[str, Any]:
    payload = _load_json(path)

    tier1 = payload.get("tier1_structural")
    if isinstance(tier1, dict) and tier1.get("available"):
        columns = [str(item) for item in tier1.get("columns", [])]
        feature_count = int(tier1.get("feature_count", len(columns)))
        nan_ratio = float((tier1.get("nan_ratio_summary") or {}).get("mean", 0.0))
        return {
            "columns": columns,
            "feature_count": feature_count,
            "nan_ratio_mean": nan_ratio,
            "source": "tier1_structural",
        }

    columns = [str(item) for item in payload.get("columns", [])]
    feature_count = int(payload.get("numeric_feature_count", len(columns)))
    nan_ratio = float((payload.get("numeric_nan_ratio_summary") or {}).get("mean", 0.0))
    return {
        "columns": columns,
        "feature_count": feature_count,
        "nan_ratio_mean": nan_ratio,
        "source": "numeric_structural",
    }


def _compare_structure(
    layer_frames: Mapping[str, pd.DataFrame],
    baseline_payload: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    if baseline_payload is None:
        return {
            "status": "skipped",
            "reason": "no_structural_baseline",
        }

    current_columns, current_nan_ratio = _combine_layer_columns(layer_frames)
    baseline_columns = [str(item) for item in baseline_payload.get("columns", [])]
    if not baseline_columns:
        return {
            "status": "skipped",
            "reason": "empty_structural_baseline_columns",
        }

    baseline_feature_count = int(baseline_payload.get("feature_count", len(baseline_columns)))
    baseline_nan_ratio = float(baseline_payload.get("nan_ratio_mean", 0.0))

    set_match = set(current_columns) == set(baseline_columns)
    order_match = current_columns == baseline_columns
    feature_count_match = len(current_columns) == baseline_feature_count
    nan_ratio_match = abs(current_nan_ratio - baseline_nan_ratio) <= NAN_RATIO_TOLERANCE

    passed = set_match and order_match and feature_count_match and nan_ratio_match

    return {
        "status": "passed" if passed else "failed",
        "baseline_source": baseline_payload.get("source"),
        "set_match": set_match,
        "order_match": order_match,
        "feature_count_match": feature_count_match,
        "nan_ratio_match": nan_ratio_match,
        "current_feature_count": len(current_columns),
        "baseline_feature_count": baseline_feature_count,
        "current_nan_ratio_mean": current_nan_ratio,
        "baseline_nan_ratio_mean": baseline_nan_ratio,
        "nan_ratio_tolerance": NAN_RATIO_TOLERANCE,
    }


def run_validation(
    cgsa_layers: Mapping[str, Path],
    legacy_layers: Mapping[str, Path],
    structural_baseline: Optional[Mapping[str, Any]] = None,
    strict_missing_layers: bool = False,
) -> Dict[str, Any]:
    cgsa_frames: Dict[str, pd.DataFrame] = {}
    legacy_frames: Dict[str, pd.DataFrame] = {}
    warnings: list[str] = []

    for layer in LAYER_ORDER:
        cgsa_path = cgsa_layers.get(layer)
        legacy_path = legacy_layers.get(layer)

        if cgsa_path is None or legacy_path is None:
            warning_message = f"Layer {layer} missing artifact: cgsa={cgsa_path}, legacy={legacy_path}"
            warnings.append(warning_message)
            logger.warning("[Task2.12] %s", warning_message)
            continue

        cgsa_frames[layer] = _load_dataframe(cgsa_path)
        legacy_frames[layer] = _load_dataframe(legacy_path)

    layer_results: Dict[str, Dict[str, Any]] = {}
    compared_layer_statuses: list[bool] = []

    for layer in LAYER_ORDER:
        cgsa_df = cgsa_frames.get(layer)
        legacy_df = legacy_frames.get(layer)

        if cgsa_df is None or legacy_df is None:
            if strict_missing_layers:
                layer_results[layer] = {
                    "status": "failed",
                    "reason": "missing_layer",
                }
                compared_layer_statuses.append(False)
            else:
                layer_results[layer] = {
                    "status": "skipped",
                    "reason": "missing_layer",
                }
            continue

        if layer == "L3":
            comparison = _compare_l3_layer(layer, cgsa_df, legacy_df)
        else:
            comparison = _compare_basic_layer(layer, cgsa_df, legacy_df, atol=LAYER_ATOL[layer])

        layer_results[layer] = comparison.to_dict()
        compared_layer_statuses.append(comparison.status == "passed")

    structure_result = _compare_structure(cgsa_frames, structural_baseline)
    if structure_result["status"] == "failed":
        compared_layer_statuses.append(False)

    if not compared_layer_statuses:
        overall_status = "failed"
        warnings.append("No layer compared. Provide at least one common layer artifact.")
    else:
        overall_status = "passed" if all(compared_layer_statuses) else "failed"

    report = {
        "task": "Task 2.12",
        "overall_status": overall_status,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "layers": layer_results,
        "structure": structure_result,
        "warnings": warnings,
    }
    return report


def _write_report(path: Path, report: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Task 2.12 - CGSA vs legacy per-layer A/B validation")
    parser.add_argument("--cgsa-layers", required=True, help="JSON path for CGSA layer artifacts")
    parser.add_argument("--legacy-layers", required=True, help="JSON path for legacy layer artifacts")
    parser.add_argument("--structural-baseline", default="", help="Optional structural baseline JSON path")
    parser.add_argument("--strict-missing-layers", action="store_true", help="Treat missing layers as failure")
    parser.add_argument(
        "--output",
        default="results/cgsa_ab/validate_cgsa_ab_report.json",
        help="Output JSON report path",
    )
    return parser


def main() -> int:
    parser = _build_arg_parser()
    args = parser.parse_args()

    cgsa_layer_path = Path(args.cgsa_layers)
    legacy_layer_path = Path(args.legacy_layers)
    output_path = Path(args.output)

    try:
        cgsa_layers = _load_layer_map(cgsa_layer_path)
        legacy_layers = _load_layer_map(legacy_layer_path)

        structural_payload: Optional[Dict[str, Any]] = None
        if args.structural_baseline:
            structural_payload = _parse_structural_baseline(Path(args.structural_baseline))

        report = run_validation(
            cgsa_layers=cgsa_layers,
            legacy_layers=legacy_layers,
            structural_baseline=structural_payload,
            strict_missing_layers=bool(args.strict_missing_layers),
        )
        _write_report(output_path, report)

        logger.info(
            "[Task2.12] Validation completed: status=%s report=%s",
            report["overall_status"],
            output_path,
        )

        return 0 if report["overall_status"] == "passed" else 1
    except ValidationInputError as exc:
        logger.error("[Task2.12] Validation input failed (%s): %s", exc.failure_type.value, exc)
        return 2
    except Exception as exc:
        logger.error("[Task2.12] Validation execution failed: %s", exc, exc_info=True)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
