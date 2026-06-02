from __future__ import annotations

from typing import Any, Dict, List

import numpy as np
import pandas as pd
import pytest

import momentum.FeatureEngineering.preprocessing.feature_preprocessor as fp_mod
from momentum.FeatureEngineering.preprocessing._slow_path_parallel import (
    ParallelSlowPath,
    process_fracdiff_column_values,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor
from momentum.core.config import get_slowpath_n_jobs


def _metadata(column: str) -> Dict[str, Any]:
    return {
        "column": column,
        "cached_d_star": None,
        "adf_threshold": 0.1,
        "d_range": (0.0, 1.0),
        "precision": 0.1,
        "max_lag": 16,
        "weight_threshold": 1e-5,
        "sample_size": 80,
    }


def test_slow_path_parallel_results_match_serial() -> None:
    rng = np.random.default_rng(11)
    values_a = np.cumsum(rng.normal(0.0, 1.0, size=180))
    values_b = np.cumsum(rng.normal(0.0, 1.0, size=180))
    items = [(values_a, _metadata("L1_alpha")), (values_b, _metadata("L1_beta"))]

    serial_results = ParallelSlowPath(1).map(items, process_fracdiff_column_values)
    parallel_results = ParallelSlowPath(2).map(items, process_fracdiff_column_values)

    for serial_result, parallel_result in zip(serial_results, parallel_results):
        assert parallel_result["column"] == serial_result["column"]
        assert parallel_result["d_star"] == serial_result["d_star"]
        assert np.allclose(
            parallel_result["fracdiff_values"],
            serial_result["fracdiff_values"],
            equal_nan=True,
        )


def test_nested_protection_forces_single_job(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setenv("FFACT_BATCH_NESTED", "1")

    assert get_slowpath_n_jobs(8) == 1


def test_get_slowpath_n_jobs_concurrent_aware(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)
    monkeypatch.setattr(
        "momentum.core.config.get_slowpath_parallel_enabled",
        lambda: False,
    )
    assert get_slowpath_n_jobs(8, 1) == 1

    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setattr(
        "momentum.core.config.get_slowpath_parallel_enabled",
        lambda: True,
    )
    assert get_slowpath_n_jobs(16, 1) == 4
    assert get_slowpath_n_jobs(16, 2) == 2
    assert get_slowpath_n_jobs(32, 4) == 2
    assert get_slowpath_n_jobs(16, 0) == 4


def test_resolve_slowpath_n_jobs_batch_concurrency(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)
    monkeypatch.setenv("FFACT_PARALLEL_BUDGET", "1")
    monkeypatch.setenv("FFACT_BATCH_SYMBOL_CONCURRENCY", "2")
    monkeypatch.setattr(
        "momentum.core.config.get_slowpath_parallel_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.preprocessing.feature_preprocessor.get_current_tier_gb",
        lambda: 16,
    )

    preprocessor = FeaturePreprocessor({})
    assert preprocessor._resolve_slowpath_n_jobs() == 2


def test_resolve_slowpath_n_jobs_parallel_budget_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.delenv("FFACT_PARALLEL_BUDGET", raising=False)
    monkeypatch.setenv("FFACT_BATCH_NESTED", "1")
    monkeypatch.setenv("FFACT_BATCH_SYMBOL_CONCURRENCY", "2")
    monkeypatch.setattr(
        "momentum.core.config.get_slowpath_parallel_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.preprocessing.feature_preprocessor.get_current_tier_gb",
        lambda: 16,
    )

    preprocessor = FeaturePreprocessor({})
    assert preprocessor._resolve_slowpath_n_jobs() == 1


def test_resolve_slowpath_n_jobs_ops_nested_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setenv("FFACT_PARALLEL_BUDGET", "1")
    monkeypatch.setenv("FFACT_BATCH_NESTED", "1")
    monkeypatch.setenv("FFACT_BATCH_SYMBOL_CONCURRENCY", "2")
    monkeypatch.setattr(
        "momentum.core.config.get_slowpath_parallel_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "momentum.FeatureEngineering.preprocessing.feature_preprocessor.get_current_tier_gb",
        lambda: 16,
    )

    preprocessor = FeaturePreprocessor({})
    assert preprocessor._resolve_slowpath_n_jobs() == 1


def test_slow_path_parallel_default_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FFACT_L65_SLOWPATH_PARALLEL", raising=False)
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)

    assert get_slowpath_n_jobs(8) == 1


def test_joblib_pickle_fail_falls_back_to_serial(monkeypatch: pytest.MonkeyPatch) -> None:
    fallback_called = {"serial": False}
    original_serial = FeaturePreprocessor._apply_fractional_differencing_serial

    def failing_map(
        self: ParallelSlowPath,
        items: List[Any],
        worker_function: Any,
    ) -> List[Dict[str, Any]]:
        raise RuntimeError("pickle failed")

    def spy_serial(
        self: FeaturePreprocessor,
        result: pd.DataFrame,
        eligible_columns: List[str],
        **kwargs: Any,
    ) -> pd.DataFrame:
        fallback_called["serial"] = True
        return original_serial(self, result, eligible_columns, **kwargs)

    def stub_find_min_d(self: FeaturePreprocessor, series: pd.Series, **kwargs: Any) -> float:
        return 1.0

    monkeypatch.setenv("FFACT_L65_SLOWPATH_PARALLEL", "1")
    monkeypatch.setenv("FFACT_MEMORY_TIER", "8gb")
    monkeypatch.delenv("FFACT_BATCH_NESTED", raising=False)
    monkeypatch.setattr(fp_mod.ParallelSlowPath, "map", failing_map)
    monkeypatch.setattr(FeaturePreprocessor, "_apply_fractional_differencing_serial", spy_serial)
    monkeypatch.setattr(FeaturePreprocessor, "_find_min_d", stub_find_min_d)
    monkeypatch.setattr(fp_mod, "HAS_STATSMODELS", True)

    frame = pd.DataFrame(
        {
            "L1_alpha": np.arange(1.0, 121.0),
            "L1_beta": np.arange(2.0, 122.0),
        }
    )
    preprocessor = FeaturePreprocessor(
        {
            "fractional_differencing": {
                "enabled": True,
                "apply_to": ["L1_alpha", "L1_beta"],
                "cache_d_star": False,
                "precision": 0.02,
                "max_lag": 8,
            },
            "mode": "append",
        }
    )

    output = preprocessor.transform(frame)

    assert fallback_called["serial"] is True
    assert "L1_alpha_fracdiff" in output.columns
    assert "L1_beta_fracdiff" in output.columns
