from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

KLINE_PATH = ROOT / "data_cache" / "feature_klines" / "kline_cache.h5"
GOLDEN_DIR = ROOT / "tests" / "_golden" / "batch2d"
SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
START_DATE = "2024-06-01"
END_DATE = "2024-12-01"
FREEZE_ENV_DEFAULTS = {
    # Freeze control is the classic in-memory path. Polars currently bypasses
    # pandas column chunking for fracdiff-disabled runs and can be OOM-killed on
    # the full BTCUSDT/12h frame; keep this script on the chunked pandas path.
    "FFACT_USE_POLARS": "0",
    "FFACT_L65_CHUNK_SIZE": "500",
    "FFACT_L65_SLOWPATH_PARALLEL": "0",
    "FFACT_BATCH_NESTED": "1",
}


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _index_payload(index: pd.Index) -> Dict[str, Any]:
    if isinstance(index, pd.DatetimeIndex):
        values = np.ascontiguousarray(index.asi8.astype("<i8", copy=False))
        dtype = "datetime64[ns]"
    else:
        hashed = pd.util.hash_pandas_object(index, index=False).to_numpy(
            dtype=np.uint64, copy=False
        )
        values = np.ascontiguousarray(hashed.astype("<u8", copy=False))
        dtype = str(index.dtype)
    return {
        "dtype": dtype,
        "name": index.name,
        "length": len(index),
        "sha256": _sha256_bytes(values.view(np.uint8).tobytes()),
    }


def canonical_frame(frame: pd.DataFrame) -> Dict[str, Any]:
    columns = [str(column) for column in frame.columns]
    per_column: Dict[str, Dict[str, Any]] = {}
    for column in frame.columns:
        values = frame[column].to_numpy(dtype=np.float32, na_value=np.nan, copy=True)
        mask = np.ascontiguousarray(np.isnan(values), dtype=np.bool_)
        canonical_values = np.ascontiguousarray(values.astype("<f4", copy=False))
        canonical_values[mask] = np.float32(0.0)
        per_column[str(column)] = {
            "value_sha256": _sha256_bytes(canonical_values.view(np.uint8).tobytes()),
            "nan_mask_sha256": _sha256_bytes(mask.view(np.uint8).tobytes()),
            "nan_count": int(mask.sum()),
        }
    index_payload = _index_payload(frame.index)
    ordered_column_sha256 = _sha256_json(columns)
    components = {
        "rows": len(frame),
        "columns": len(columns),
        "ordered_columns": columns,
        "ordered_column_sha256": ordered_column_sha256,
        "row_index": index_payload,
        "per_column": per_column,
    }
    return {"canonical_sha256": _sha256_json(components), **components}


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temp_path.write_text(content, encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _package_versions() -> Dict[str, str]:
    versions: Dict[str, str] = {}
    for package in ("numpy", "pandas", "statsmodels", "pyarrow"):
        versions[package] = importlib_metadata.version(package)
    return versions


def _base_override() -> Dict[str, Any]:
    return {
        "timeframes": {
            "primary": TIMEFRAME,
            "training": [TIMEFRAME],
        }
    }


def _tagged_map(factory: Any, column_layer_map: Dict[str, str]) -> Dict[str, str]:
    empty = pd.DataFrame(columns=list(column_layer_map))
    tagged_columns = factory._apply_timeframe_tag(empty, TIMEFRAME).columns
    return {
        str(tagged): column_layer_map[raw]
        for raw, tagged in zip(column_layer_map, tagged_columns)
    }


def _manifest_columns(manifest: Dict[str, Any]) -> list[str]:
    groups = manifest["artifacts"]["raw"]["groups"]
    return [
        str(column)
        for group in groups.values()
        for column in group.get("columns", [])
    ]


def _registry_layer_map(factory: Any) -> Dict[str, str]:
    from momentum.FeatureEngineering.core.column_group import LayerSource

    layer_sources = (
        LayerSource.L1,
        LayerSource.L2,
        LayerSource.L3,
        LayerSource.L4,
        LayerSource.L5,
        LayerSource.L6,
    )
    registry = factory._cgsa_registry
    if registry is None:
        raise RuntimeError("CGSA registry missing after baseline generation")
    layer_map: Dict[str, str] = {}
    for layer_source in layer_sources:
        for group in registry.list_by_layer(layer_source):
            tagged = factory._apply_timeframe_tag(
                pd.DataFrame(columns=list(group.columns)), TIMEFRAME
            ).columns
            for column in tagged:
                existing = layer_map.setdefault(str(column), layer_source.value)
                if existing != layer_source.value:
                    raise AssertionError(
                        f"CGSA column layer mismatch: {column} {existing} != {layer_source.value}"
                    )
    return layer_map


def _metadata(config: Any, config_hash: str, cache_dir: Path) -> Dict[str, Any]:
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.utils.hardware_utils import get_memory_tier

    return {
        "symbol": SYMBOL,
        "timeframe": TIMEFRAME,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "config": config.model_dump(by_alias=True),
        "config_hash": config_hash,
        "environment": {
            "FFACT_USE_CGSA": os.getenv("FFACT_USE_CGSA"),
            "FFACT_L65_WORKERS": os.getenv("FFACT_L65_WORKERS"),
            "FFACT_MEMORY_TIER_GB": os.getenv("FFACT_MEMORY_TIER_GB"),
            "FFACT_ADF_ENGINE": os.getenv("FFACT_ADF_ENGINE"),
            "FFACT_FRACDIFF_PRECISION": os.getenv("FFACT_FRACDIFF_PRECISION"),
            "resolved_memory_tier": str(get_memory_tier()),
        },
        "storage_schema": {
            "cgsa_raw": FeatureStorage.L7_RAW_SCHEMA_VERSION,
            "registry": 2,
            "frame": "factory_hdf5",
        },
        "package_versions": _package_versions(),
        "kline": {
            "path": str(KLINE_PATH.relative_to(ROOT)),
            "sha256": _sha256_file(KLINE_PATH),
        },
        "d_star_cache": {
            "fresh": True,
            "isolated_temp_directory": True,
        },
    }


def _run_control(temp_root: Path) -> tuple[Dict[str, Any], Dict[str, str]]:
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.factories import create_feature_factory

    os.environ["FFACT_USE_CGSA"] = "0"
    feature_dir = temp_root / "control" / "features"
    cache_dir = temp_root / "control" / "d_star"
    FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
    factory = create_feature_factory(
        cache_dir=str(KLINE_PATH.parent), validate_continuity=False
    )
    factory._storage = FeatureStorage(str(feature_dir))
    override = _base_override()
    override["preprocessing"] = {"fractional_differencing": {"enabled": False}}
    config = factory._resolve_config(override)
    result = factory.generate_features(
        SYMBOL,
        TIMEFRAME,
        config_override=override,
        force_regenerate=True,
        start_date=START_DATE,
        end_date=END_DATE,
        persist=True,
    )
    if result.features_df.empty:
        raise RuntimeError("non-CGSA control returned an empty features_df")
    column_layer_map = dict(factory._column_layer_map or {})
    if not column_layer_map:
        raise RuntimeError("non-CGSA control provenance map is empty")
    tagged_map = _tagged_map(factory, column_layer_map)
    payload = {
        "metadata": _metadata(config, str(result.metadata["config_hash"]), cache_dir),
        "manifest_columns": [str(column) for column in result.features_df.columns],
        "frame": canonical_frame(result.features_df),
    }
    return payload, tagged_map


def _run_cgsa(temp_root: Path) -> tuple[Dict[str, Any], Dict[str, str]]:
    from momentum.FeatureEngineering.feature_reader import FeatureReader
    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
    from momentum.factories import create_feature_factory

    os.environ["FFACT_USE_CGSA"] = "1"
    work_dir = temp_root / "cgsa" / "registry"
    feature_dir = temp_root / "cgsa" / "features"
    cache_dir = temp_root / "cgsa" / "d_star"
    os.environ["FFACT_CGSA_WORK_DIR"] = str(work_dir)
    FeaturePreprocessor._d_star_cache_dir = staticmethod(lambda: cache_dir)
    factory = create_feature_factory(
        cache_dir=str(KLINE_PATH.parent), validate_continuity=False
    )
    factory._storage = FeatureStorage(str(feature_dir))
    override = _base_override()
    config = factory._resolve_config(override)
    result = factory.generate_features(
        SYMBOL,
        TIMEFRAME,
        config_override=override,
        force_regenerate=True,
        start_date=START_DATE,
        end_date=END_DATE,
        persist=True,
    )
    config_hash = str(result.metadata["config_hash"])
    reader = FeatureReader(str(feature_dir))
    manifest = reader.load_manifest_v2(SYMBOL, TIMEFRAME, config_hash, artifact_kind="raw")
    columns = _manifest_columns(manifest)
    if not columns:
        raise RuntimeError("CGSA raw manifest contains no columns")
    frame = reader.load_columns_v2(
        SYMBOL, TIMEFRAME, config_hash, columns, artifact_kind="raw"
    )
    row_index = reader.load_row_index_v2(SYMBOL, TIMEFRAME, config_hash, artifact_kind="raw")
    if row_index is None:
        raise RuntimeError("CGSA raw manifest row index missing")
    frame.index = row_index
    payload = {
        "metadata": _metadata(config, config_hash, cache_dir),
        "manifest_columns": columns,
        "frame": canonical_frame(frame.loc[:, columns]),
    }
    return payload, _registry_layer_map(factory)


def _apply_freeze_env() -> None:
    for key, value in FREEZE_ENV_DEFAULTS.items():
        os.environ.setdefault(key, value)


def _phase_env(phase: str) -> Dict[str, str]:
    env = os.environ.copy()
    for key, value in FREEZE_ENV_DEFAULTS.items():
        env.setdefault(key, value)
    env["FFACT_USE_CGSA"] = "1" if phase == "cgsa" else "0"
    if phase != "cgsa":
        env.pop("FFACT_CGSA_WORK_DIR", None)
    return env


def _run_phase(phase: str, out_path: Path) -> None:
    """Run a single generation phase in this (fresh) process and dump its result.

    每個 phase 跑在獨立子程序，避免同進程連續兩次全特徵生成累積記憶體被 OOM-kill
    （control 成功、CGSA 接著死的實測根因；UI 一次一個 generation 故無此問題）。
    """
    _apply_freeze_env()
    with tempfile.TemporaryDirectory(prefix=f"batch2d_{phase}_") as temp_dir:
        temp_root = Path(temp_dir)
        if phase == "control":
            payload, provenance = _run_control(temp_root)
        elif phase == "cgsa":
            payload, provenance = _run_cgsa(temp_root)
        else:
            raise ValueError(f"unknown phase: {phase}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(
            json.dumps({"payload": payload, "provenance": provenance}, ensure_ascii=False),
            encoding="utf-8",
        )


def main() -> None:
    if not KLINE_PATH.is_file():
        raise FileNotFoundError(f"required real kline cache missing: {KLINE_PATH}")

    import argparse
    import subprocess

    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["control", "cgsa"])
    parser.add_argument("--out")
    args = parser.parse_args()

    if args.phase:
        # 子程序：跑單一 phase 並寫出結果（記憶體隔離）
        _run_phase(args.phase, Path(args.out))
        return

    # Orchestrator：每 phase 一個乾淨子程序，再合併。
    with tempfile.TemporaryDirectory(prefix="batch2d_freeze_") as temp_dir:
        temp_root = Path(temp_dir)
        results: Dict[str, Dict[str, Any]] = {}
        for phase in ("control", "cgsa"):
            out_path = temp_root / f"{phase}.json"
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()),
                 "--phase", phase, "--out", str(out_path)],
                check=True,
                env=_phase_env(phase),
            )
            results[phase] = json.loads(out_path.read_text(encoding="utf-8"))

    control = results["control"]["payload"]
    frame_provenance = results["control"]["provenance"]
    cgsa = results["cgsa"]["payload"]
    cgsa_provenance = results["cgsa"]["provenance"]

    common_columns = sorted(set(frame_provenance) & set(cgsa_provenance))
    mismatches = {
        column: {"frame": frame_provenance[column], "cgsa": cgsa_provenance[column]}
        for column in common_columns
        if frame_provenance[column] != cgsa_provenance[column]
    }
    if mismatches:
        raise AssertionError(f"frame/CGSA provenance mismatch: {mismatches}")

    provenance = {
        "frame_column_to_layer": frame_provenance,
        "cgsa_column_to_layer": cgsa_provenance,
        "common_column_count": len(common_columns),
        "same_layer_for_common_columns": True,
    }
    _write_json(GOLDEN_DIR / "control.json", control)
    _write_json(GOLDEN_DIR / "cgsa_baseline.json", cgsa)
    _write_json(GOLDEN_DIR / "provenance.json", provenance)


if __name__ == "__main__":
    main()
