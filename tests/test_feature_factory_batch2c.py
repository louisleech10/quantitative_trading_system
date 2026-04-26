"""Batch 2c tests for Task 2.7 and Task 2.8."""

from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _make_group(group_id: str, columns: Tuple[str, ...]) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="synthetic",
        columns=columns,
        shape=(0, 0),
        dtype="float32",
        disk_path=None,
    )


def _materialize_registry(registry: ColumnGroupRegistry) -> pd.DataFrame:
    frames = []
    for group_id, group in registry.iter_all():
        group_data = np.asarray(registry.load_data(group_id), dtype=np.float32)
        frames.append(pd.DataFrame(group_data, columns=list(group.columns), copy=False))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, axis=1, copy=False)


def test_t217_l65_per_group_matches_legacy(tmp_path: Path):
    """T2.17: L6.5 per-group preprocessing should match legacy wide-DF output."""
    features = pd.DataFrame(
        {
            "close_1h_trend_EMA_5_mean": [1.0, 2.0, 100.0, 4.0, 5.0, 6.0],
            "close_1h_trend_EMA_5_std": [0.1, 0.2, 0.3, 0.4, np.nan, 0.6],
            "close_1h_momentum_RSI_14_mean": [50.0, 51.0, 52.0, 53.0, 54.0, 55.0],
        },
        dtype=np.float32,
    )

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group_a_cols = ("close_1h_trend_EMA_5_mean", "close_1h_trend_EMA_5_std")
    group_b_cols = ("close_1h_momentum_RSI_14_mean",)
    registry.save_data(
        _make_group("1h_L3_trend_group_a", group_a_cols),
        features.loc[:, list(group_a_cols)].to_numpy(dtype=np.float32),
    )
    registry.save_data(
        _make_group("1h_L3_momentum_group_b", group_b_cols),
        features.loc[:, list(group_b_cols)].to_numpy(dtype=np.float32),
    )

    preprocess_config = {
        "rank_transform": {"enabled": True, "apply_to": "all", "window": 3},
    }

    per_group_preprocessor = FeaturePreprocessor(preprocess_config)
    processed_group_count = per_group_preprocessor.transform_registry_groups(registry)
    per_group_output = _materialize_registry(registry).loc[:, list(features.columns)]

    legacy_output = FeaturePreprocessor(preprocess_config).transform(features)
    legacy_output = legacy_output.loc[:, list(features.columns)]

    assert processed_group_count == 2
    np.testing.assert_allclose(
        per_group_output.to_numpy(dtype=np.float64),
        legacy_output.to_numpy(dtype=np.float64),
        atol=1e-6,
        equal_nan=True,
    )


def test_t215_per_group_parquet_duckdb_readable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """T2.15: per-group parquet should be DuckDB-readable and preserve total columns.

    The L7 compactor (FFACT_L7_COMPACTOR_ENABLED=1 by default) may merge multiple
    parts into a single parquet for streaming efficiency; this test exercises the
    *unmerged* per-group writer to verify each group remains DuckDB-readable.
    Total column count remains the integrity invariant either way.
    """
    duckdb = pytest.importorskip("duckdb")
    monkeypatch.setenv("FFACT_L7_COMPACTOR_ENABLED", "0")

    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")
    group_a_cols = ("f_a_1", "f_a_2")
    group_b_cols = ("f_b_1",)

    registry.save_data(
        _make_group("1h_L3_group_a", group_a_cols),
        np.array(
            [
                [1.0, 2.0],
                [3.0, 4.0],
                [5.0, 6.0],
            ],
            dtype=np.float32,
        ),
    )
    registry.save_data(
        _make_group("1h_L3_group_b", group_b_cols),
        np.array(
            [
                [10.0],
                [11.0],
                [12.0],
            ],
            dtype=np.float32,
        ),
    )

    storage = FeatureStorage(base_path=str(tmp_path / "features"))
    output_paths = storage.persist_registry_to_parquet(
        symbol="ETHUSDT",
        config_hash="cfg_hash_001",
        registry=registry,
        cleanup_intermediate=False,
    )

    assert len(output_paths) == 2
    expected_parent = tmp_path / "features" / "ETHUSDT" / "cfg_hash_001"
    assert all(Path(path).parent == expected_parent for path in output_paths)

    conn = duckdb.connect(database=":memory:")
    total_columns = 0
    for parquet_path in sorted(output_paths):
        escaped = str(parquet_path).replace("'", "''")
        schema_rows = conn.execute(
            f"DESCRIBE SELECT * FROM read_parquet('{escaped}')"
        ).fetchall()
        total_columns += len(schema_rows)

    conn.close()
    assert total_columns == registry.total_columns()
