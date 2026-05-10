from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from momentum.FeatureEngineering.feature_reader import FeatureReader
from momentum.FeatureEngineering.feature_storage import (
    L7_ENCODING_REGISTRY_METADATA_KEY,
    FeatureStorage,
    _write_parquet_with_codec,
    build_phase2_skip_evidence,
    decode_rank_from_uint16,
    decode_zscore_from_int16,
    encode_rank_as_uint16,
    encode_zscore_as_int16,
    write_phase2_skip_evidence,
)


def _max_abs_diff(left: np.ndarray, right: np.ndarray) -> float:
    valid_mask = ~np.isnan(left)
    if not valid_mask.any():
        return 0.0
    return float(np.max(np.abs(left[valid_mask] - right[valid_mask])))


def test_bss_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "1")
    values = np.array([1.25, -2.5, np.nan, 4.75], dtype=np.float32)
    table = pa.Table.from_arrays([pa.array(values)], names=["fallback_float32"])
    output_path = tmp_path / "bss.parquet"

    _write_parquet_with_codec(table, output_path, float32_cols=["fallback_float32"])

    loaded = pq.read_table(str(output_path)).to_pandas()["fallback_float32"].to_numpy(dtype=np.float32)
    np.testing.assert_array_equal(np.isnan(loaded), np.isnan(values))
    np.testing.assert_array_equal(loaded[~np.isnan(values)], values[~np.isnan(values)])


def test_rank_uint16_roundtrip() -> None:
    window = 4
    values = np.array([0.25, 0.5, 0.75, 1.0, np.nan], dtype=np.float32)

    encoded = encode_rank_as_uint16(values, window)
    decoded = decode_rank_from_uint16(encoded, window)

    assert encoded.dtype == np.uint16
    assert _max_abs_diff(values, decoded) <= 1.0 / (2 * window)
    np.testing.assert_array_equal(np.isnan(decoded), np.isnan(values))


def test_zscore_int16_roundtrip() -> None:
    values = np.array([-1.234, 0.0, 2.345, np.nan], dtype=np.float32)

    encoded = encode_zscore_as_int16(values)
    decoded = decode_zscore_from_int16(encoded)

    assert encoded.dtype == np.int16
    assert _max_abs_diff(values, decoded) <= 0.001
    np.testing.assert_array_equal(np.isnan(decoded), np.isnan(values))


def test_mixed_encoding_metadata_roundtrip(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "1")
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    frame = pd.DataFrame(
        {
            "alpha_rank_4": np.array([0.25, 0.5, 1.0, np.nan], dtype=np.float32),
            "beta_zscore": np.array([-1.25, 0.0, 1.25, np.nan], dtype=np.float32),
            "gamma_gaussian": np.array([-0.5, 0.5, 1.5, np.nan], dtype=np.float32),
            "plain_feature": np.array([10.0, 11.0, 12.0, 13.0], dtype=np.float32),
        }
    )

    processed_dir = storage.write_processed("SYNTHETIC", "1h", "cfg_codec", {"selected": frame})

    schema = pq.read_schema(str(processed_dir / "selected.parquet"))
    registry = json.loads(schema.metadata[L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8")])
    assert registry["alpha_rank_4"]["encoding_type"] == "rank_uint16"
    assert registry["alpha_rank_4"]["window"] == "4"
    assert registry["beta_zscore"]["encoding_type"] == "zscore_int16"
    assert registry["gamma_gaussian"]["encoding_type"] == "gaussian_int16"
    assert "plain_feature" not in registry

    loaded = reader.load_columns_v2(
        "SYNTHETIC",
        "1h",
        "cfg_codec",
        list(frame.columns),
        artifact_kind="processed",
    )
    for column in frame.columns:
        np.testing.assert_allclose(
            loaded[column].to_numpy(dtype=np.float32),
            frame[column].to_numpy(dtype=np.float32),
            atol=0.001,
            rtol=0.0,
            equal_nan=True,
        )


def test_codec_upgrade_disabled_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "0")
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    frame = pd.DataFrame(
        {"alpha_rank_4": np.array([0.25, 0.5, 1.0, np.nan], dtype=np.float32)}
    )

    processed_dir = storage.write_processed("SYNTHETIC", "1h", "cfg_disabled", {"selected": frame})

    schema = pq.read_schema(str(processed_dir / "selected.parquet"))
    metadata = schema.metadata or {}
    assert L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8") not in metadata
    loaded = reader.load_columns_v2(
        "SYNTHETIC",
        "1h",
        "cfg_disabled",
        ["alpha_rank_4"],
        artifact_kind="processed",
    )
    np.testing.assert_allclose(
        loaded["alpha_rank_4"].to_numpy(dtype=np.float32),
        frame["alpha_rank_4"].to_numpy(dtype=np.float32),
        equal_nan=True,
    )


def test_rank_nan_sentinel() -> None:
    encoded = encode_rank_as_uint16(np.array([np.nan, 0.5], dtype=np.float32), window=4)
    decoded = decode_rank_from_uint16(encoded, window=4)

    assert int(encoded[0]) == 0
    assert np.isnan(decoded[0])
    assert decoded[1] == 0.5


def test_zscore_overflow_fallback_float32(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "1")
    storage = FeatureStorage(str(tmp_path / "features"))
    reader = FeatureReader(str(tmp_path / "features"))
    frame = pd.DataFrame(
        {"overflow_zscore": np.array([0.0, 40.0, np.nan], dtype=np.float32)}
    )

    processed_dir = storage.write_processed("SYNTHETIC", "1h", "cfg_overflow", {"selected": frame})

    schema = pq.read_schema(str(processed_dir / "selected.parquet"))
    metadata = schema.metadata or {}
    assert L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8") not in metadata
    loaded = reader.load_columns_v2(
        "SYNTHETIC",
        "1h",
        "cfg_overflow",
        ["overflow_zscore"],
        artifact_kind="processed",
    )
    np.testing.assert_allclose(
        loaded["overflow_zscore"].to_numpy(dtype=np.float32),
        frame["overflow_zscore"].to_numpy(dtype=np.float32),
        equal_nan=True,
    )


def test_bss_pyarrow_version_fallback(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("FFACT_L7_CODEC_UPGRADE", "1")
    values = np.array([1.0, 2.0, 3.0], dtype=np.float32)
    table = pa.Table.from_arrays([pa.array(values)], names=["fallback_float32"])
    output_path = tmp_path / "fallback.parquet"
    original_write_table = pq.write_table
    calls = []

    def fake_write_table(table_arg, where, **kwargs):
        calls.append(dict(kwargs))
        if kwargs.get("column_encoding"):
            raise NotImplementedError("BYTE_STREAM_SPLIT unsupported")
        return original_write_table(table_arg, where, **kwargs)

    monkeypatch.setattr(pq, "write_table", fake_write_table)

    _write_parquet_with_codec(table, output_path, float32_cols=["fallback_float32"])

    assert len(calls) == 2
    assert calls[0].get("column_encoding") == {"fallback_float32": "BYTE_STREAM_SPLIT"}
    assert calls[1].get("column_encoding") is None
    loaded = pq.read_table(str(output_path)).to_pandas()["fallback_float32"].to_numpy(dtype=np.float32)
    np.testing.assert_array_equal(loaded, values)


def test_old_parquet_no_metadata(tmp_path) -> None:
    base_dir = tmp_path / "features"
    symbol = "LEGACY"
    config_hash = "cfg_legacy"
    legacy_dir = base_dir / symbol / config_hash
    legacy_dir.mkdir(parents=True)
    frame = pd.DataFrame({"legacy_alpha": np.array([1.0, 2.0, 3.0], dtype=np.float32)})
    legacy_path = legacy_dir / "legacy_group.parquet"
    frame.to_parquet(legacy_path, index=False)
    manifest = {
        "version": "7.0",
        "symbol": symbol,
        "config_hash": config_hash,
        "total_features": 1,
        "total_rows": 3,
        "groups": {
            "legacy_group": {
                "file": "legacy_group.parquet",
                "columns": ["legacy_alpha"],
                "column_count": 1,
                "dtype": "float32",
            }
        },
    }
    (legacy_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    schema_metadata = pq.read_schema(str(legacy_path)).metadata or {}
    assert L7_ENCODING_REGISTRY_METADATA_KEY.encode("utf-8") not in schema_metadata

    reader = FeatureReader(str(base_dir))
    loaded = reader.load_columns_v2(symbol, "1h", config_hash, ["legacy_alpha"], artifact_kind="raw")
    np.testing.assert_allclose(
        loaded["legacy_alpha"].to_numpy(dtype=np.float32),
        frame["legacy_alpha"].to_numpy(dtype=np.float32),
    )


def test_phase2_skip_evidence_manifest(tmp_path) -> None:
    evidence = build_phase2_skip_evidence(
        symbol="SYNTHETIC",
        tf="1h",
        config_hash="cfg_skip",
        feature_schema_hash="schema_hash",
        l7_raw_size_bytes=123,
        l7_processed_size_bytes=45,
        fracdiff_enabled=False,
        float32_fallback_group_count=0,
        reason="processed_size_under_threshold",
    )

    output_path = write_phase2_skip_evidence(tmp_path, evidence)

    payload = json.loads(Path(output_path).read_text(encoding="utf-8"))
    assert payload["symbol"] == "SYNTHETIC"
    assert payload["tf"] == "1h"
    assert payload["config_hash"] == "cfg_skip"
    assert payload["feature_schema_hash"] == "schema_hash"
    assert payload["l7_raw_size_bytes"] == 123
    assert payload["l7_processed_size_bytes"] == 45
    assert payload["fracdiff_enabled"] is False
    assert payload["float32_fallback_group_count"] == 0
    assert payload["pyarrow_version"]
    assert payload["reason"] == "processed_size_under_threshold"
    assert payload["created_at"]
