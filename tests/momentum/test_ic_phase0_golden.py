import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from momentum.Analysis.ic_config_schema import FeatureFilterSchema
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.ic_config_schema import load_ic_config


FIXTURE_DIR = Path("tests/fixtures/ic_phase0")


def _mask_hash(index: pd.Index) -> str:
    return hashlib.sha256(",".join(map(str, index)).encode()).hexdigest()


def _sha_columns(columns: list[str]) -> str:
    return hashlib.sha256("\n".join(columns).encode()).hexdigest()


def _assert_float_close(actual: object, expected: object) -> None:
    if expected is None:
        assert actual is None or (isinstance(actual, float) and np.isnan(actual))
        return
    if isinstance(expected, float):
        assert np.isclose(float(actual), expected, atol=1e-6, rtol=1e-4)
        return
    assert actual == expected


def test_grouped_baseline() -> None:
    baseline = json.loads((FIXTURE_DIR / "baseline_grouped_post_timeaxis.json").read_text())
    features = pd.DataFrame(
        {
            "feature_neg": [3, 2, 1, 6, 5, 4],
            "feature_pos": [1, 2, 3, 4, 5, 6],
        }
    )
    label = pd.Series([1, 2, 3, 4, 5, 6])
    raw_data = pd.DataFrame(
        {
            "timestamp": [
                1704067200,
                1704153600,
                1704240000,
                1735689600,
                1735776000,
                1735862400,
            ],
            "close": [10, 11, 12, 13, 14, 15],
        }
    )

    grouped = ICEngine({}).compute_grouped_ic(
        features,
        label,
        raw_data,
        metadata={},
        config={
            "method": "spearman",
            "by_year": True,
            "by_quarter": False,
            "by_regime": False,
            "by_category": False,
            "by_data_source": False,
            "by_layer": False,
            "by_volatility": False,
        },
    )

    years = pd.to_datetime(raw_data["timestamp"], unit="s").dt.year
    assert set(grouped["by_year"]) == set(baseline["groups"])
    for year, idx in years.groupby(years).groups.items():
        year_key = str(year)
        values = grouped["by_year"][year_key]
        assert baseline["groups"][year_key]["group_size"] == len(idx)
        assert baseline["groups"][year_key]["row_mask_hash"] == _mask_hash(idx)
        assert np.isclose(
            float(np.nanmean(list(values.values()))),
            baseline["groups"][year_key]["ic_mean"],
            atol=1e-6,
            rtol=1e-4,
        )


def test_feature_filter_baseline() -> None:
    baseline = json.loads((FIXTURE_DIR / "baseline_feature_filter.json").read_text())
    orchestrator = ICFilterOrchestrator(load_ic_config())
    features = pd.DataFrame(
        {
            "beta": [1.0, 2.0, 3.0],
            "alpha": [1.0, 1.5, 2.0],
            "gamma": [3.0, 2.0, 1.0],
            "delta": [4.0, 5.0, 6.0],
        }
    )

    filtered, _metadata, info = orchestrator._apply_feature_filter(
        features,
        metadata={},
        feature_filter=FeatureFilterSchema(max_features=2),
    )

    columns = list(filtered.columns)
    assert columns == baseline["filtered_columns"]
    assert _sha_columns(columns) == baseline["filtered_sha256"]
    assert info["feature_count_original"] == baseline["feature_count_original"]
    assert info["feature_count_filtered"] == baseline["feature_count_filtered"]
    assert info["truncation_mode"] == baseline["truncation_mode"]
    assert info["truncation_order"] == baseline["truncation_order"]


def test_decay_baseline() -> None:
    baseline = json.loads((FIXTURE_DIR / "baseline_decay.json").read_text())
    features = pd.DataFrame(
        {
            "decay_good": np.linspace(1, 20, 20),
            "decay_bad": [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 55, 34, 21, 13, 8, 5, 3, 2, 1, 1],
        }
    )
    close = pd.Series(np.linspace(100, 125, 20))

    actual = ICEngine({}).compute_ic_decay(
        features,
        close,
        horizons=[1, 2, 3],
        method="spearman",
        return_type="simple",
    )

    assert set(actual) == set(baseline)
    for feature, expected_payload in baseline.items():
        assert set(actual[feature]) == set(expected_payload)
        for key, expected_value in expected_payload.items():
            actual_value = actual[feature][key]
            if isinstance(expected_value, list):
                assert len(actual_value) == len(expected_value)
                for item_actual, item_expected in zip(actual_value, expected_value):
                    _assert_float_close(item_actual, item_expected)
            else:
                _assert_float_close(actual_value, expected_value)
