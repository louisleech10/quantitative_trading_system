"""fracdiff max_lag golden 凍結用 canonical digest helper。"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Mapping

import numpy as np
import pandas as pd


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def canonical_index_hash(index: pd.Index) -> str:
    """回傳 index dtype/name/value 的穩定 SHA-256。"""
    digest = hashlib.sha256()
    payload = {
        "dtype": str(index.dtype),
        "name": None if index.name is None else str(index.name),
        "length": int(len(index)),
        "class": type(index).__name__,
    }
    digest.update(_json_bytes(payload))
    hashed = pd.util.hash_pandas_object(index, index=True).to_numpy(dtype="<u8", copy=False)
    digest.update(np.ascontiguousarray(hashed).view(np.uint8))
    return digest.hexdigest()


def canonical_schema_hash(columns: Iterable[Any], dtypes: Mapping[str, str]) -> str:
    """回傳欄名順序與 dtype schema 的穩定 SHA-256。"""
    ordered = [str(column) for column in columns]
    payload = {
        "columns": ordered,
        "dtypes": {column: str(dtypes[column]) for column in ordered},
    }
    return hashlib.sha256(_json_bytes(payload)).hexdigest()


def _series_value_bytes(series: pd.Series) -> bytes:
    values = series.to_numpy(copy=True)
    if pd.api.types.is_float_dtype(values):
        arr = np.asarray(values, dtype="<f8")
        mask = pd.isna(arr)
        if mask.any():
            arr = arr.copy()
            arr[mask] = np.nan
        return np.ascontiguousarray(arr).view(np.uint8).tobytes()
    if pd.api.types.is_integer_dtype(values):
        return np.ascontiguousarray(np.asarray(values, dtype="<i8")).view(np.uint8).tobytes()
    if pd.api.types.is_bool_dtype(values):
        return np.ascontiguousarray(np.asarray(values, dtype=np.uint8)).view(np.uint8).tobytes()
    if pd.api.types.is_datetime64_any_dtype(values):
        return np.ascontiguousarray(np.asarray(values, dtype="datetime64[ns]").astype("<i8")).view(
            np.uint8
        ).tobytes()
    encoded = series.astype("string").fillna("<NA>").to_numpy(dtype=str)
    return "\0".join(encoded.tolist()).encode("utf-8")


def canonical_column_digests(df: pd.DataFrame) -> Dict[str, Any]:
    """產生全欄 byte 級 digest；不做抽樣。"""
    index_hash = canonical_index_hash(df.index)
    dtype_map = {str(column): str(df[column].dtype) for column in df.columns}
    schema_hash = canonical_schema_hash(df.columns, dtype_map)
    columns: Dict[str, Dict[str, Any]] = {}

    for column in df.columns:
        name = str(column)
        series = df[column]
        nan_mask = pd.isna(series.to_numpy(copy=False))
        value_hash = hashlib.sha256(_series_value_bytes(series)).hexdigest()
        nan_hash = hashlib.sha256(
            np.packbits(nan_mask.astype(np.uint8), bitorder="little").tobytes()
        ).hexdigest()
        numeric = pd.to_numeric(series, errors="coerce")
        finite = numeric[np.isfinite(numeric.to_numpy(dtype=float, copy=False))]
        columns[name] = {
            "dtype": dtype_map[name],
            "value_sha256": value_hash,
            "nan_mask_sha256": nan_hash,
            "nan_ratio": float(nan_mask.mean()) if len(nan_mask) else 0.0,
            "mean": None if finite.empty else float(finite.mean()),
            "std": None if finite.empty else float(finite.std(ddof=0)),
        }

    return {
        "row_count": int(len(df.index)),
        "column_count": int(len(df.columns)),
        "index_hash": index_hash,
        "index_dtype": str(df.index.dtype),
        "schema_hash": schema_hash,
        "columns": columns,
    }


def digest_frame_sha256(digest_payload: Mapping[str, Any]) -> str:
    """整體 digest hash，供穩定性前置快速比對。"""
    relevant = {
        "row_count": digest_payload["row_count"],
        "column_count": digest_payload["column_count"],
        "index_hash": digest_payload["index_hash"],
        "index_dtype": digest_payload["index_dtype"],
        "schema_hash": digest_payload["schema_hash"],
        "columns": {
            name: {
                "dtype": data["dtype"],
                "value_sha256": data["value_sha256"],
                "nan_mask_sha256": data["nan_mask_sha256"],
            }
            for name, data in digest_payload["columns"].items()
        },
    }
    return hashlib.sha256(_json_bytes(relevant)).hexdigest()


def is_fracdiff_column(name: str) -> bool:
    """依 Feature Factory L6.5 命名分類 fracdiff 欄。"""
    return "fracdiff" in str(name).lower()


def compare_golden_digests(g1: Mapping[str, Any], g2: Mapping[str, Any]) -> Dict[str, Any]:
    """比較 G1/G2：fracdiff 欄應不同，非 fracdiff 欄應相同。"""
    g1_cols: Mapping[str, Mapping[str, Any]] = g1["columns"]
    g2_cols: Mapping[str, Mapping[str, Any]] = g2["columns"]
    common = sorted(set(g1_cols).intersection(g2_cols))
    only_g1 = sorted(set(g1_cols).difference(g2_cols))
    only_g2 = sorted(set(g2_cols).difference(g1_cols))
    fracdiff_equal: list[str] = []
    fracdiff_different: list[str] = []
    non_fracdiff_different: list[str] = []

    for column in common:
        left = g1_cols[column]
        right = g2_cols[column]
        same = (
            left["dtype"] == right["dtype"]
            and left["value_sha256"] == right["value_sha256"]
            and left["nan_mask_sha256"] == right["nan_mask_sha256"]
        )
        if is_fracdiff_column(column):
            if same:
                fracdiff_equal.append(column)
            else:
                fracdiff_different.append(column)
        elif not same:
            non_fracdiff_different.append(column)

    return {
        "row_count_equal": int(g1["row_count"]) == int(g2["row_count"]),
        "index_hash_equal": g1["index_hash"] == g2["index_hash"],
        "schema_hash_equal": g1["schema_hash"] == g2["schema_hash"],
        "common_column_count": len(common),
        "only_g1": only_g1,
        "only_g2": only_g2,
        "fracdiff_column_count": len([column for column in common if is_fracdiff_column(column)]),
        "fracdiff_different_count": len(fracdiff_different),
        "fracdiff_equal_count": len(fracdiff_equal),
        "non_fracdiff_different_count": len(non_fracdiff_different),
        "fracdiff_equal_examples": fracdiff_equal[:20],
        "fracdiff_different_examples": fracdiff_different[:20],
        "non_fracdiff_different_examples": non_fracdiff_different[:20],
        "passed": (
            not only_g1
            and not only_g2
            and int(g1["row_count"]) == int(g2["row_count"])
            and g1["index_hash"] == g2["index_hash"]
            and len(fracdiff_different) > 0
            and len(non_fracdiff_different) == 0
        ),
    }


def canonical_raw_dir_digests(raw_dir: Any) -> Dict[str, Any]:
    """L7 raw 目錄串流版全欄 digest（逐 parquet 檔處理，不 concat，225k 欄安全）。

    persist=True streaming 模式下 generate_features 不回傳 features_df，
    真實產物在 run_dir/raw/*.parquet（與 ff_truncation_mr_helpers 讀法一致）。
    """
    from pathlib import Path

    raw_path = Path(raw_dir)
    files = sorted(p for p in raw_path.glob("*.parquet") if p.name != "timestamps.parquet")
    if not files:
        raise RuntimeError(f"no raw parquet files in {raw_path}")

    columns: Dict[str, Dict[str, Any]] = {}
    ordered_names: list[str] = []
    index_hash: str | None = None
    index_dtype: str | None = None
    row_count: int | None = None

    for path in files:
        frame = pd.read_parquet(path)
        part = canonical_column_digests(frame)
        if index_hash is None:
            index_hash = part["index_hash"]
            index_dtype = part["index_dtype"]
            row_count = part["row_count"]
        else:
            if part["index_hash"] != index_hash:
                raise RuntimeError(f"index mismatch across raw parquet: {path.name}")
            if part["row_count"] != row_count:
                raise RuntimeError(f"row_count mismatch across raw parquet: {path.name}")
        for name in part["columns"]:
            if name in columns:
                raise RuntimeError(f"duplicate column across raw parquet: {name} ({path.name})")
        columns.update(part["columns"])
        ordered_names.extend(str(c) for c in frame.columns)

    schema_hash = canonical_schema_hash(
        ordered_names, {name: columns[name]["dtype"] for name in ordered_names}
    )
    return {
        "row_count": int(row_count or 0),
        "column_count": len(ordered_names),
        "index_hash": index_hash,
        "index_dtype": index_dtype,
        "schema_hash": schema_hash,
        "columns": columns,
    }
