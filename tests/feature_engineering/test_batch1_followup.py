from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_validator import FeatureValidator


REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = REPO_ROOT / "tests/_golden/batch1_followup/baseline.json"


def _load_baseline() -> dict[str, object]:
    if not BASELINE_PATH.exists():
        pytest.fail(f"Batch1 follow-up baseline missing: {BASELINE_PATH}")
    try:
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        pytest.fail(f"Batch1 follow-up baseline unreadable: {exc}")


def _winsor_fixture() -> pd.DataFrame:
    rng = np.random.default_rng(20260612)
    values = rng.standard_normal((1_000, 3)).astype(np.float32)
    values[:60, 0] = np.nan
    values[400:405, 1] = np.nan
    values[250, 2] = 8.0 * float(np.nanstd(values[:, 2]))
    values[750, 2] = -8.0 * float(np.nanstd(values[:, 2]))
    return pd.DataFrame(values, columns=["leading", "mid_hole", "outliers"])


def _hash_array(values: np.ndarray) -> tuple[str, str]:
    mask = np.isnan(values)
    normalized = np.where(mask, 0.0, values).astype(np.float64)
    return (
        hashlib.sha256(normalized.tobytes()).hexdigest(),
        hashlib.sha256(mask.tobytes()).hexdigest(),
    )


class TestGolden:
    def test_golden_baseline_is_readable_and_complete(self) -> None:
        baseline = _load_baseline()
        required = {
            "winsor_default_value_hash",
            "winsor_default_mask_hash",
            "winsor_w100_value_hash",
            "winsor_w100_mask_hash",
            "winsor_w100_min_periods",
            "max_nan_ratio_btc_12h",
            "nan_stats_reference",
            "perf_wall_seconds",
            "perf_peak_bytes",
        }
        assert required <= baseline.keys()
        assert set(baseline["nan_stats_reference"]) == {
            "empty",
            "all_nan",
            "leading_only",
            "trailing_only",
            "mid_hole",
            "cross_chunk",
        }

    def test_golden_default_winsor_matches_public_validator(self) -> None:
        baseline = _load_baseline()
        frame = _winsor_fixture()
        result = SimpleNamespace(
            features_df=frame.copy(),
            feature_count=frame.shape[1],
            config_used={},
        )
        FeatureValidator().validate_factory_output(result)
        value_hash, mask_hash = _hash_array(result.features_df.to_numpy())
        assert value_hash == baseline["winsor_default_value_hash"]
        assert mask_hash == baseline["winsor_default_mask_hash"]

    def test_golden_max_nan_ratio_matches_head(self) -> None:
        baseline = _load_baseline()
        assert FeatureFactory._default_max_nan_ratio("BTCUSDT", "12h") == baseline[
            "max_nan_ratio_btc_12h"
        ]
