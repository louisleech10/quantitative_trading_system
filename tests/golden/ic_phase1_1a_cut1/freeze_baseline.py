"""Freeze the IC Phase 1 1a cut1 G-OLD (flag-off) baseline — reuses 1-contract BTC/1h reference inputs/config_hash; flag-off == current behavior."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

import h5py


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.ic_persist_redirect_manual import run_with_manual_redirect  # noqa: E402
from api.models.ic_models import FeatureFilterConfig, ICAnalyzeRequest  # noqa: E402
from api.services.ic_analysis_service import ICAnalysisService  # noqa: E402
from momentum.factories import create_feature_reader  # noqa: E402


SYMBOL = "BTCUSDT"
TIMEFRAME = "1h"
MODE = "longitudinal"
CONFIG_HASH = "a384e6d22ca15fc639757cb3162e7cb3"
REGISTRY_FEATURE_COUNT = 90857
REGISTRY_ROW_COUNT = 20352
OUTPUT_DIR = Path(__file__).resolve().parent
BASELINE_PATH = OUTPUT_DIR / "baseline_old_btc_1h_a384e6d2.json"
META_PATH = OUTPUT_DIR / "baseline_meta.json"
INPUT_DIR = OUTPUT_DIR / "inputs"


def _canonical_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_reusable_inputs(
    h5_path: Path,
    meta_path: Path,
    max_features: int,
) -> list[str]:
    """以 pinned digest 與 H5 schema 驗證 committed canonical input。"""
    baseline_meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    manifest = baseline_meta.get("input_manifest")
    if not isinstance(manifest, dict):
        raise RuntimeError("missing pinned input_manifest in baseline metadata")
    if _sha256(h5_path) != manifest.get("h5_sha256"):
        raise RuntimeError("canonical H5 SHA256 differs from pinned manifest")
    if _sha256(meta_path) != manifest.get("meta_sha256"):
        raise RuntimeError("canonical meta SHA256 differs from pinned manifest")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    subset = meta.get("baseline_subset", {})
    selected = subset.get("selected_features")
    if (
        meta.get("symbol") != SYMBOL
        or meta.get("timeframe") != TIMEFRAME
        or meta.get("config_hash") != CONFIG_HASH
        or subset.get("max_features") != max_features
        or not isinstance(selected, list)
    ):
        raise RuntimeError("canonical meta identity/subset does not match freeze request")

    group_key = f"{SYMBOL}/{TIMEFRAME}"
    with h5py.File(h5_path, "r") as handle:
        if list(handle.keys()) != [SYMBOL] or group_key not in handle:
            raise RuntimeError("canonical H5 symbol/timeframe group mismatch")
        group = handle[group_key]
        if set(group.keys()) != {"features", "timestamps", "feature_names"}:
            raise RuntimeError("canonical H5 schema mismatch")
        features = group["features"]
        timestamps = group["timestamps"][:]
        raw_names = group["feature_names"][:]
        feature_order = [x.decode("utf-8") if isinstance(x, bytes) else str(x) for x in raw_names]
        if features.ndim != 2 or features.shape != (len(timestamps), len(feature_order)):
            raise RuntimeError("canonical H5 dataset shape mismatch")
        if feature_order != selected:
            raise RuntimeError("canonical H5 feature order differs from selected_features")
        if timestamps.ndim != 1 or len(timestamps) != features.shape[0]:
            raise RuntimeError("canonical H5 row index shape mismatch")
    return selected


def _materialize_deterministic_subset(
    service: ICAnalysisService,
    max_features: int,
) -> tuple[Path, Path, list[str]]:
    h5_existing = INPUT_DIR / f"{SYMBOL}_{TIMEFRAME}_{CONFIG_HASH}_top{max_features}.h5"
    meta_existing = INPUT_DIR / f"{SYMBOL}_{TIMEFRAME}_{CONFIG_HASH}_top{max_features}_meta.json"
    if h5_existing.exists() != meta_existing.exists():
        raise RuntimeError("canonical input pair is incomplete; refusing overwrite")
    if h5_existing.exists() and meta_existing.exists():
        sel = _validate_reusable_inputs(h5_existing, meta_existing, max_features)
        return h5_existing, meta_existing, sel

    reader = create_feature_reader()
    feature_names = reader.list_features_v2(SYMBOL, TIMEFRAME, CONFIG_HASH)
    selected_features = sorted(feature_names)[:max_features]
    if len(selected_features) != max_features:
        raise RuntimeError(f"expected {max_features} features, found {len(selected_features)}")

    features_df = reader.load_columns_v2(SYMBOL, TIMEFRAME, CONFIG_HASH, selected_features)
    row_index = reader.load_row_index_v2(SYMBOL, TIMEFRAME, CONFIG_HASH)
    if row_index is not None:
        features_df.index = row_index

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    h5_path = INPUT_DIR / f"{SYMBOL}_{TIMEFRAME}_{CONFIG_HASH}_top{max_features}.h5"
    meta_path = INPUT_DIR / f"{SYMBOL}_{TIMEFRAME}_{CONFIG_HASH}_top{max_features}_meta.json"
    service._write_features_h5(h5_path, SYMBOL, TIMEFRAME, features_df)
    meta_payload = service._build_ic_metadata_from_run(
        SYMBOL,
        TIMEFRAME,
        CONFIG_HASH,
        selected_features,
    )
    meta_payload["baseline_subset"] = {
        "selection": "sorted(feature_names)[:max_features]",
        "max_features": max_features,
        "selected_features": selected_features,
        "source_feature_count": len(feature_names),
    }
    meta_path.write_bytes(_canonical_bytes(meta_payload))
    try:
        selected_features = _validate_reusable_inputs(h5_path, meta_path, max_features)
    except Exception:
        h5_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        raise
    return h5_path, meta_path, selected_features


async def _run_baseline(
    max_features: int,
    timeout_seconds: int,
    poll_seconds: float,
) -> tuple[str, dict[str, Any], Path, Path, list[str]]:
    service = ICAnalysisService()
    features_path, meta_path, selected_features = _materialize_deterministic_subset(service, max_features)
    request = ICAnalyzeRequest(
        features_path=str(features_path.resolve()),
        meta_path=str(meta_path.resolve()),
        symbol=SYMBOL,
        timeframe=TIMEFRAME,
        config_hash=CONFIG_HASH,
        mode=MODE,
        # G-OLD=flag-off:顯式寫死(schema 預設 True;原凍結者曾以未入腳本的 override 產出
        # full-sample 內容——854d444 測試綠可證——本行永久關閉該隱形參數債,2026-07-11)
        config_override={"ic_train_test_split": False},
        feature_filter=FeatureFilterConfig(max_features=max_features),
    )
    start = time.monotonic()
    started = await service.start_analysis(request)
    task_id = started["task_id"]

    while True:
        status = service.get_task_status(task_id)
        if status and status.get("status") == "completed":
            result = service.get_result(task_id)
            if result is None:
                raise RuntimeError(f"completed task has no result: {task_id}")
            return task_id, result, features_path, meta_path, selected_features
        if status and status.get("status") == "failed":
            raise RuntimeError(f"IC baseline run failed: {status.get('error')}")
        if time.monotonic() - start > timeout_seconds:
            raise TimeoutError(f"IC baseline run timed out after {timeout_seconds}s; last_status={status}")
        await asyncio.sleep(poll_seconds)


def _build_meta(
    *,
    task_id: str,
    max_features: int,
    timeout_seconds: int,
    baseline_sha256: str,
    result: dict[str, Any],
    features_path: Path,
    meta_path: Path,
    selected_features: list[str],
) -> dict[str, Any]:
    request_payload = {
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "mode": MODE,
        "config_hash": CONFIG_HASH,
        "feature_filter": {"max_features": max_features},
        "config_override": {"ic_train_test_split": False},
    }
    metadata = result.get("metadata", {}) if isinstance(result.get("metadata"), dict) else {}
    command = [
        "python",
        "tests/golden/ic_phase1_1a_cut1/freeze_baseline.py",
        "--max-features",
        str(max_features),
        "--timeout-seconds",
        str(timeout_seconds),
    ]
    return {
        "baseline_file": str(BASELINE_PATH.relative_to(REPO_ROOT)),
        "baseline_sha256": baseline_sha256,
        "config_hash": CONFIG_HASH,
        "mode": MODE,
        "reference_registry": {
            "symbol": SYMBOL,
            "timeframe": TIMEFRAME,
            "feature_count": REGISTRY_FEATURE_COUNT,
            "row_count": REGISTRY_ROW_COUNT,
        },
        "reproduction_command": " ".join(command),
        "request": request_payload,
        "materialized_inputs": {
            "features_path": str(features_path.relative_to(REPO_ROOT)),
            "meta_path": str(meta_path.relative_to(REPO_ROOT)),
            "selection": "sorted(feature_names)[:max_features]",
            "selected_features": selected_features,
        },
        "input_manifest": {
            "h5_sha256": _sha256(features_path),
            "meta_sha256": _sha256(meta_path),
            "schema": f"{SYMBOL}/{TIMEFRAME}:features,timestamps,feature_names",
        },
        "canonical_projection": {
            "comparison": "canonical JSON normalized SHA256 or deep-equal",
            "exempt_fields": ["generated_at", "task_id_used_for_freeze"],
        },
        "provenance_limitations": {
            "gate_a": "Committed input SHA/schema guard plus semantic golden replay is the reproducible provenance gate.",
            "gate_b": "Source-to-input rebuild is manual and is not reproducible from a clean checkout because the feature registry is gitignored and Feature Factory code may drift.",
            "manual_rebuild_config_hash": CONFIG_HASH,
            "manual_rebuild_command": " ".join(command),
        },
        "task_id_used_for_freeze": task_id,
        "actual_result_metadata": {
            "feature_count_original": metadata.get("feature_count_original"),
            "feature_count_filtered": metadata.get("feature_count_filtered"),
            "feature_filter_applied": metadata.get("feature_filter_applied"),
            "truncation_mode": metadata.get("truncation_mode"),
            "symbol": metadata.get("symbol"),
            "timeframe": metadata.get("timeframe"),
            "config_hash": metadata.get("config_hash"),
        },
        "notes": [
            "Baseline is generated through ICAnalysisService.start_analysis() and get_result(task_id).",
            "A deterministic feature_filter subset is used to avoid local OOM from full 90857 x 20352 materialization.",
            "G1 tests must replay the exact request recorded here before comparing v1 output.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-features", type=int, default=50)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()

    if args.max_features < 1:
        raise SystemExit("--max-features must be >= 1")

    task_id, result, features_path, meta_path, selected_features = asyncio.run(
        _run_baseline(
            max_features=args.max_features,
            timeout_seconds=args.timeout_seconds,
            poll_seconds=args.poll_seconds,
        )
    )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_bytes(_canonical_bytes(result))
    baseline_sha256 = _sha256(BASELINE_PATH)
    meta = _build_meta(
        task_id=task_id,
        max_features=args.max_features,
        timeout_seconds=args.timeout_seconds,
        baseline_sha256=baseline_sha256,
        result=result,
        features_path=features_path,
        meta_path=meta_path,
        selected_features=selected_features,
    )
    META_PATH.write_bytes(_canonical_bytes(meta))
    print(json.dumps({"baseline": str(BASELINE_PATH), "sha256": baseline_sha256}, indent=2))
    return 0


if __name__ == "__main__":
    with run_with_manual_redirect():
        raise SystemExit(main())
