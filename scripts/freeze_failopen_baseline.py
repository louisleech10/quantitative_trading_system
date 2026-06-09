#!/usr/bin/env python3
"""凍結 fail-open 改造前的真實 kline 全量 golden baseline。"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
KLINE_PATH = ROOT / "data_cache/feature_klines/kline_cache.h5"
GOLDEN_DIR = ROOT / "tests/_golden/failopen"
# 委員會 2026-06-09:baseline 縮到 2 代表性 symbol × 2 TF(primary 1h, training 1h+12h)。
# 理由:① 整機硬碟僅 ~10GB free;② 全量逐格 hash 下 2 symbol 已足以抓任何行為回歸
# (改壞不會只壞單一 symbol);③ per-symbol 生成→hash→刪,峰值 ~1.4GB 守住硬碟。
SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = ("1h", "12h")
PRIMARY_TIMEFRAME = "1h"
FIXED_ENV = {
    "FFACT_LAYER1_PARALLEL": "0",
    "FFACT_USE_CGSA": "1",
    "FFACT_USE_POLARS": "1",
    "FFACT_L3_PERSIST_MODE": "streaming",
    "FFACT_USE_SEARCHSORTED": "1",
    "FFACT_MERGE_CHUNK_SIZE": "5000",
    "FFACT_MULTI_TF_PARALLEL": "0",
}


def _sha256_file(path: Path, chunk_size: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


def _package_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def _git_sha() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


# 委員會 2026-06-09:baseline 用使用者真實 UI 設定 = IC-First + Winsorization + Fracdiff,
# L1-L6 全開(IC-First 在生成期跳過 rank/zscore/gaussian)。窗 365 天:12h 約 730 根
# (>500 fracdiff 校準、>233 最長 rolling),完整跑到所有 code path,約全量 43% 省時。
WINDOW_DAYS = 365


def _fixed_config_payload(training: Sequence[str], primary: str) -> dict[str, Any]:
    return {
        "timeframes": {
            "primary": primary,
            "training": list(training),
            "alignment": "point_in_time",
            "alignment_mode": "open_minus",
        },
        # 委員會 2026-06-09(真派 b9qmxol8l/committee):減特徵(7 來源→1)。降特徵數可
        # 減 L6.5 winsor 成本;合併/對齊/CGSA/rollback 邏輯與特徵數無關,減特徵仍完整
        # 覆蓋重構動到的路徑。合併正確性另由 V-6 獨立 as-of oracle + 既有 MTF golden 守。
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        # fracdiff=OFF。誠實更正(2026-06-10 階段計時實測):多框 80 分 = L6.5+L7
        # raw-sink serial winsor 78 分(非 fracdiff)。我先前「fracdiff 是大成本/關掉省時」
        # 是未驗證的錯誤推論,實測坐實 fracdiff ON/OFF 同速(72.3 vs 72.9s)。fracdiff=OFF
        # 之所以可行,是「重構不碰 fracdiff 數學」,不是為省時。winsor+IC-First 保留。
        "preprocessing": {
            "ic_first_pipeline": True,
            "winsorization": {"enabled": True},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        },
    }


def _window_dates() -> tuple[str, str]:
    """固定可重現的 365 天窗:讀真實 kline 1h 末根時間戳,回 (start,end) ISO 日期。"""
    import h5py
    import numpy as np
    import pandas as pd

    with h5py.File(KLINE_PATH, "r") as f:
        ts = np.asarray(f["/BTCUSDT/1h/data"]["timestamp"], dtype=np.int64)
    end_epoch = int(ts.max())  # epoch 秒(L1-L4 事故已確認單位=秒)
    end = pd.Timestamp(end_epoch, unit="s", tz="UTC")
    start = end - pd.Timedelta(days=WINDOW_DAYS)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _require_fixed_environment() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("Run with PYTHONHASHSEED=0; it cannot be fixed after interpreter startup")
    for name, value in FIXED_ENV.items():
        os.environ[name] = value


def _index_metadata(index: Any) -> dict[str, Any]:
    import pandas as pd

    dtype = getattr(index, "dtype", None)
    unit = None
    timezone = None
    if isinstance(index, pd.DatetimeIndex):
        unit = getattr(dtype, "unit", "ns")
        timezone = str(index.tz) if index.tz is not None else None
    elif isinstance(index, pd.TimedeltaIndex):
        unit = getattr(dtype, "unit", "ns")
    return {
        "class": f"{type(index).__module__}.{type(index).__qualname__}",
        "dtype": str(dtype),
        "name": index.name,
        "unit": unit,
        "timezone": timezone,
        "length": int(len(index)),
    }


def _canonical_array_bytes(values: Any) -> bytes:
    import numpy as np

    array = np.asarray(values)
    if array.dtype.kind in {"O", "U", "S"}:
        encoded = bytearray()
        for value in array.reshape(-1, order="C"):
            item = str(value).encode("utf-8")
            encoded.extend(len(item).to_bytes(8, "little"))
            encoded.extend(item)
        return bytes(encoded)

    canonical = np.array(array, copy=True, order="C")
    if canonical.dtype.kind == "f":
        nan_mask = np.isnan(canonical)
        negative_zero = (canonical == 0) & np.signbit(canonical)
        canonical[nan_mask] = np.nan
        canonical[negative_zero] = -0.0
    if canonical.dtype.kind in {"M", "m"}:
        canonical = canonical.astype("<i8", copy=False)
    elif canonical.dtype.itemsize > 1:
        canonical = canonical.astype(canonical.dtype.newbyteorder("<"), copy=False)
    return canonical.tobytes(order="C")


def _hash_index(index: Any) -> dict[str, Any]:
    metadata = _index_metadata(index)
    digest = hashlib.sha256()
    digest.update(_json_bytes(metadata))
    digest.update(_canonical_array_bytes(index.to_numpy(copy=False)))
    return {"metadata": metadata, "sha256": digest.hexdigest()}


def _ordered_groups(registry: Any, groups: Iterable[Any]) -> list[Any]:
    return sorted(
        groups,
        key=lambda group: registry._column_sort_key(
            group, group.columns[0] if group.columns else group.group_id
        ),
    )


def _hash_registry_table(registry: Any, groups: Iterable[Any], index: Any) -> dict[str, Any]:
    import numpy as np

    ordered_groups = _ordered_groups(registry, groups)
    columns: list[str] = []
    dtypes: list[str] = []
    for group in ordered_groups:
        columns.extend(str(column) for column in group.columns)
        dtypes.extend([str(np.dtype(group.dtype))] * len(group.columns))

    column_hash = _sha256_json(columns)
    dtype_hash = _sha256_json(dtypes)
    index_hash = _hash_index(index)
    value_digest = hashlib.sha256()
    mask_digest = hashlib.sha256()
    nan_count = 0
    cell_count = 0

    for group in ordered_groups:
        data = np.asarray(registry.load_data_native(group.group_id))
        if data.shape != tuple(group.shape):
            raise ValueError(f"Registry shape mismatch for {group.group_id}: {data.shape} != {group.shape}")
        for column_index in range(data.shape[1]):
            values = data[:, column_index]
            mask = np.asarray(np.isnan(values), dtype=np.uint8)
            value_digest.update(_canonical_array_bytes(values))
            mask_digest.update(np.packbits(mask, bitorder="little").tobytes())
            nan_count += int(mask.sum())
            cell_count += int(mask.size)

    components = {
        "column_order_sha256": column_hash,
        "dtypes_sha256": dtype_hash,
        "index_sha256": index_hash["sha256"],
        "values_sha256": value_digest.hexdigest(),
        "nan_mask_sha256": mask_digest.hexdigest(),
    }
    return {
        "canonical_sha256": _sha256_json(components),
        **components,
        "index_metadata": index_hash["metadata"],
        "rows": int(len(index)),
        "columns": len(columns),
        "groups": len(ordered_groups),
        "nan_count": nan_count,
        "cell_count": cell_count,
        "nan_ratio": (float(nan_count) / float(cell_count)) if cell_count else 0.0,
        "storage": "registry_groups",
    }


def _artifact_hashes(work_dir: Path) -> dict[str, Any]:
    files = sorted(path for path in work_dir.rglob("*") if path.is_file())
    entries = [
        {
            "path": str(path.relative_to(work_dir)),
            "size": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in files
    ]
    return {
        "files": entries,
        "file_count": len(entries),
        "aggregate_sha256": _sha256_json(entries),
    }


def _group_set_hash(groups: Iterable[Any]) -> str:
    payload = [
        {
            "group_id": group.group_id,
            "layer": group.layer.value,
            "timeframe": group.timeframe,
            "columns": list(group.columns),
            "dtype": group.dtype,
            "shape": list(group.shape),
        }
        for group in sorted(groups, key=lambda item: item.group_id)
    ]
    return _sha256_json(payload)


def _all_registry_groups(registry: Any) -> list[Any]:
    return [group for _group_id, group in registry.iter_all()]


def _measure_rss_mb() -> float:
    """進程當前 RSS(MB),psutil 優先,fallback resource。"""
    try:
        import psutil  # type: ignore

        return psutil.Process().memory_info().rss / (1024 * 1024)
    except Exception:
        import resource

        maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux=KB, macOS=bytes
        return maxrss / (1024 * 1024) if sys.platform == "darwin" else maxrss / 1024


def _perf_record(
    result: Any,
    generation_wall_seconds: float,
    rss_before: float,
    rss_after: float,
    *,
    hash_wall_seconds: float = 0.0,
) -> dict[str, Any]:
    """效能/記憶體基準(使用者 2026-06-09:防時間爆炸/記憶體爆炸回歸)。"""
    import resource

    maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    peak_mb = maxrss / (1024 * 1024) if sys.platform == "darwin" else maxrss / 1024
    layer_counts = {}
    multi_tf_stage_seconds: dict[str, float] = {}
    try:
        layer_counts = dict(result.metadata.get("layer_counts", {}) or {})
        stage_raw = result.metadata.get("multi_tf_stage_seconds", {}) or {}
        if isinstance(stage_raw, dict):
            multi_tf_stage_seconds = {
                str(key): round(float(value), 3) for key, value in stage_raw.items()
            }
    except Exception:
        pass
    generation_wall_seconds = round(float(generation_wall_seconds), 3)
    hash_wall_seconds = round(float(hash_wall_seconds), 3)
    return {
        "generation_wall_seconds": generation_wall_seconds,
        "hash_wall_seconds": hash_wall_seconds,
        "wall_seconds": round(generation_wall_seconds + hash_wall_seconds, 3),
        "rss_before_mb": round(float(rss_before), 1),
        "rss_after_mb": round(float(rss_after), 1),
        "rss_delta_mb": round(float(rss_after - rss_before), 1),
        "process_peak_rss_mb": round(float(peak_mb), 1),
        "layer_counts": layer_counts,  # 各層 cols(規模回歸訊號)
        "multi_tf_stage_seconds": multi_tf_stage_seconds,
        "feature_count": int(getattr(result, "feature_count", 0) or 0),
    }


def _hash_l7_parquet_table(
    feature_base: Path,
    symbol: str,
    timeframe: str,
    config_hash: str,
    index: Any,
) -> dict[str, Any]:
    """對持久化 L7_raw parquet 做與 registry 相同的 canonical hash。"""
    import numpy as np
    from momentum.FeatureEngineering.feature_reader import FeatureReader

    reader = FeatureReader(str(feature_base))
    n_rows = int(len(index))
    column_arrays: dict[str, tuple[np.ndarray, str]] = {}

    for _group_name, group_df in reader.stream_groups_v2(
        symbol, timeframe, config_hash, artifact_kind="raw"
    ):
        if len(group_df) != n_rows:
            raise ValueError(
                f"L7 parquet row count mismatch for {symbol}/{timeframe}: "
                f"{len(group_df)} != {n_rows}"
            )
        for column_name in group_df.columns:
            values = np.asarray(group_df[column_name].to_numpy(copy=False))
            column_arrays[str(column_name)] = (values, str(np.dtype(values.dtype)))

    if not column_arrays:
        raise ValueError(f"No L7_raw columns found for {symbol}/{timeframe}/{config_hash}")

    columns = sorted(column_arrays)
    dtypes = [column_arrays[column][1] for column in columns]
    column_hash = _sha256_json(columns)
    dtype_hash = _sha256_json(dtypes)
    index_hash = _hash_index(index)
    value_digest = hashlib.sha256()
    mask_digest = hashlib.sha256()
    nan_count = 0
    cell_count = 0

    for column in columns:
        values, _dtype = column_arrays[column]
        mask = np.asarray(np.isnan(values), dtype=np.uint8)
        value_digest.update(_canonical_array_bytes(values))
        mask_digest.update(np.packbits(mask, bitorder="little").tobytes())
        nan_count += int(mask.sum())
        cell_count += int(mask.size)

    components = {
        "column_order_sha256": column_hash,
        "dtypes_sha256": dtype_hash,
        "index_sha256": index_hash["sha256"],
        "values_sha256": value_digest.hexdigest(),
        "nan_mask_sha256": mask_digest.hexdigest(),
    }
    return {
        "canonical_sha256": _sha256_json(components),
        **components,
        "index_metadata": index_hash["metadata"],
        "rows": n_rows,
        "columns": len(columns),
        "groups": 0,
        "nan_count": nan_count,
        "cell_count": cell_count,
        "nan_ratio": (float(nan_count) / float(cell_count)) if cell_count else 0.0,
        "storage": "l7_raw_parquet",
    }


def _combined_artifact_hashes(*work_dirs: Path) -> dict[str, Any]:
    """合併多個產物目錄的檔案 hash(registry work_dir + L7 run dir)。"""
    entries: list[dict[str, Any]] = []
    for work_dir in work_dirs:
        if not work_dir.exists():
            continue
        root_label = work_dir.name
        for path in sorted(p for p in work_dir.rglob("*") if p.is_file()):
            entries.append(
                {
                    "root": root_label,
                    "path": str(path.relative_to(work_dir)),
                    "size": path.stat().st_size,
                    "sha256": _sha256_file(path),
                }
            )
    return {
        "files": entries,
        "file_count": len(entries),
        "aggregate_sha256": _sha256_json(entries),
    }


def _run_generation(
    symbol: str,
    training: Sequence[str],
    primary: str,
    temp_root: Path,
    *,
    persist: bool,
) -> tuple[Any, Any, Any, dict[str, Any], Path, Path, dict[str, Any]]:
    import time as _time

    from momentum.FeatureEngineering.feature_storage import FeatureStorage
    from momentum.factories import create_feature_factory

    run_name = f"{symbol}_{primary}_{'-'.join(training)}"
    work_dir = temp_root / run_name / "registry"
    feature_dir = temp_root / run_name / "features"
    shutil.rmtree(work_dir.parent, ignore_errors=True)
    os.environ["FFACT_CGSA_WORK_DIR"] = str(work_dir)

    factory = create_feature_factory(
        cache_dir=str(KLINE_PATH.parent), validate_continuity=False
    )
    factory._storage = FeatureStorage(str(feature_dir))
    payload = _fixed_config_payload(training, primary)
    start_date, end_date = _window_dates()
    rss_before = _measure_rss_mb()
    _t0 = _time.perf_counter()
    result = factory.generate_features(
        symbol=symbol,
        timeframe=primary,
        config_override=payload,
        force_regenerate=True,
        start_date=start_date,
        end_date=end_date,
        persist=persist,
    )
    generation_wall_seconds = _time.perf_counter() - _t0
    perf = _perf_record(
        result,
        generation_wall_seconds,
        rss_before,
        _measure_rss_mb(),
    )
    registry = factory._cgsa_registry
    if registry is None:
        raise RuntimeError(f"CGSA registry missing for {run_name}")
    return factory, result, registry, payload, work_dir, feature_dir, perf


def _single_tf_record(symbol: str, timeframe: str, temp_root: Path) -> dict[str, Any]:
    import time as _time

    from momentum.FeatureEngineering.core.column_group import LayerSource

    factory, result, registry, payload, work_dir, _feature_dir, perf = _run_generation(
        symbol, [timeframe], timeframe, temp_root, persist=False
    )
    _start, _end = _window_dates()
    raw = factory._layer0_data_ingestion(
        symbol, timeframe, factory._resolve_config(payload), start_date=_start, end_date=_end
    )
    _hash_start = _time.perf_counter()
    layers: dict[str, Any] = {}
    for layer_number, layer_source in enumerate(
        (LayerSource.L1, LayerSource.L2, LayerSource.L3, LayerSource.L4, LayerSource.L5, LayerSource.L6),
        start=1,
    ):
        layers[f"L{layer_number}"] = _hash_registry_table(
            registry, registry.list_by_layer(layer_source), raw.index
        )
    all_groups = _all_registry_groups(registry)
    final = _hash_registry_table(registry, all_groups, raw.index)
    perf = _perf_record(
        result,
        perf["generation_wall_seconds"],
        perf["rss_before_mb"],
        perf["rss_after_mb"],
        hash_wall_seconds=_time.perf_counter() - _hash_start,
    )
    record = {
        "symbol": symbol,
        "timeframe": timeframe,
        "config_payload": payload,
        "config_payload_sha256": _sha256_json(payload),
        "config_hash": str(result.metadata["config_hash"]),
        "layers": layers,
        "final_L7": final,
        "group_set_sha256": _group_set_hash(all_groups),
        "artifacts": _artifact_hashes(work_dir),
        "feature_count": int(result.feature_count),
        "perf": perf,
    }
    shutil.rmtree(work_dir.parent, ignore_errors=True)
    return record


def _multi_tf_record(symbol: str, temp_root: Path) -> dict[str, Any]:
    import time as _time

    factory, result, registry, payload, work_dir, feature_dir, perf = _run_generation(
        symbol, TIMEFRAMES, PRIMARY_TIMEFRAME, temp_root, persist=True
    )
    config_hash = str(result.metadata["config_hash"])
    if not result.hdf5_path:
        raise RuntimeError(
            f"Multi-TF persist=True but no L7 manifest for {symbol}: "
            f"raw_path={result.metadata.get('raw_path')!r}"
        )
    _start, _end = _window_dates()
    raw = factory._layer0_data_ingestion(
        symbol, PRIMARY_TIMEFRAME, factory._resolve_config(payload), start_date=_start, end_date=_end
    )
    groups = _all_registry_groups(registry)
    l7_run_dir = (
        feature_dir / symbol / PRIMARY_TIMEFRAME / config_hash
    )
    _hash_start = _time.perf_counter()
    merged_l7 = _hash_l7_parquet_table(
        feature_dir, symbol, PRIMARY_TIMEFRAME, config_hash, raw.index
    )
    perf = _perf_record(
        result,
        perf["generation_wall_seconds"],
        perf["rss_before_mb"],
        perf["rss_after_mb"],
        hash_wall_seconds=_time.perf_counter() - _hash_start,
    )
    record = {
        "symbol": symbol,
        "primary_timeframe": PRIMARY_TIMEFRAME,
        "training_timeframes": list(TIMEFRAMES),
        "config_payload": payload,
        "config_payload_sha256": _sha256_json(payload),
        "config_hash": config_hash,
        "merged_L7": merged_l7,
        "merged_L7_source": {
            "kind": "l7_raw_parquet",
            "feature_run_dir": str(l7_run_dir.relative_to(feature_dir.parent)),
            "manifest_path": str(result.hdf5_path),
            "raw_path": str(result.metadata.get("raw_path") or ""),
        },
        "group_set_sha256": _group_set_hash(groups),
        "artifacts": _combined_artifact_hashes(work_dir, l7_run_dir),
        "feature_count": int(result.feature_count),
        "perf": perf,
    }
    shutil.rmtree(work_dir.parent, ignore_errors=True)
    return record


def _environment_manifest() -> dict[str, Any]:
    import psutil
    from momentum.FeatureEngineering.polars_adapter import polars_enabled
    from momentum.FeatureEngineering.utils.hardware_utils import get_l3_persist_mode, get_memory_tier

    total_ram = int(psutil.virtual_memory().total)
    return {
        "commit_sha": _git_sha(),
        "kline_path": str(KLINE_PATH.relative_to(ROOT)),
        "kline_sha256": _sha256_file(KLINE_PATH),
        "env": {
            **FIXED_ENV,
            "PYTHONHASHSEED": os.environ["PYTHONHASHSEED"],
            "resolved_polars_enabled": polars_enabled(),
            "resolved_l3_persist_mode": get_l3_persist_mode(),
        },
        "versions": {
            "python": platform.python_version(),
            "pandas": _package_version("pandas"),
            "numpy": _package_version("numpy"),
            "TA-Lib": _package_version("TA-Lib"),
            "numba": _package_version("numba"),
            "polars": _package_version("polars"),
        },
        "tier": {
            "resolved": get_memory_tier(),
            "total_ram_bytes": total_ram,
            "total_ram_gib": total_ram / (1024 ** 3),
        },
    }


def freeze(symbols: Sequence[str], resume: bool, max_units: int = 0) -> None:
    """max_units>0:本次 invocation 最多做 N 個生成單元就停(供外層 shell loop 每單元
    開新 process 達成記憶體隔離,照 production ProcessPoolExecutor 模式)。0=不限。"""
    _require_fixed_environment()
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.gettempdir()) / "ff_failopen_baseline"
    temp_root.mkdir(parents=True, exist_ok=True)

    manifest_path = GOLDEN_DIR / "baseline.json"
    if resume and manifest_path.exists():
        baseline = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        start_date, end_date = _window_dates()
        env = _environment_manifest()
        env["window"] = {"days": WINDOW_DAYS, "start_date": start_date, "end_date": end_date}
        baseline = {
            "schema_version": 1,
            "canonical_hash_version": 1,
            "symbols": list(SYMBOLS),
            "timeframes": list(TIMEFRAMES),
            "environment": env,
            "single_tf": {},
            "multi_tf": {},
        }

    done = 0
    stopped = False
    for symbol in symbols:
        if stopped:
            break
        symbol_records = baseline["single_tf"].setdefault(symbol, {})
        for timeframe in TIMEFRAMES:
            if resume and timeframe in symbol_records:
                continue
            symbol_records[timeframe] = _single_tf_record(symbol, timeframe, temp_root)
            _write_json(manifest_path, baseline)
            done += 1
            if max_units and done >= max_units:
                stopped = True
                break
        if stopped:
            break
        if not (resume and symbol in baseline["multi_tf"]):
            baseline["multi_tf"][symbol] = _multi_tf_record(symbol, temp_root)
            _write_json(manifest_path, baseline)
            done += 1
            if max_units and done >= max_units:
                stopped = True
                break

    nan_limits = {
        symbol: {
            timeframe: baseline["single_tf"][symbol][timeframe]["final_L7"]["nan_ratio"]
            for timeframe in TIMEFRAMES
        }
        for symbol in SYMBOLS
        if symbol in baseline["single_tf"] and all(
            timeframe in baseline["single_tf"][symbol] for timeframe in TIMEFRAMES
        )
    }
    _write_json(
        GOLDEN_DIR / "max_nan_ratio.json",
        {
            "schema_version": 1,
            "definition": "observed healthy-run final_L7 nan_ratio upper bound",
            "ratios": nan_limits,
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", nargs="+", choices=SYMBOLS, default=list(SYMBOLS))
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--max-units", type=int, default=0,
                        help="本次 invocation 最多做 N 個生成單元就停(配 shell loop 做 process 隔離);0=不限")
    args = parser.parse_args()
    freeze(args.symbols, resume=not args.no_resume, max_units=args.max_units)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
