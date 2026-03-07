from __future__ import annotations

import pandas as pd

from api.services.feature_factory_service import FeatureFactoryService
from momentum.FeatureEngineering.feature_factory import FeatureGenerationResult


def _build_result() -> FeatureGenerationResult:
    features_df = pd.DataFrame(
        {
            "f1": [1.0, 2.0, float("nan")],
            "f2": [3.0, 4.0, 5.0],
        },
        index=[100, 200, 300],
    )
    labels_df = pd.DataFrame({"label_ret": [0.0, 1.0, 0.0]}, index=[100, 200, 300])
    metadata = {
        "feature_names": ["f1", "f2"],
        "feature_count": 2,
        "layer_counts": {"layer1": 2, "layer2": 0, "layer3": 0, "layer4": 0, "layer5": 0, "layer6": 0},
        "symbol": "ETHUSDT",
        "timeframe": "12h",
        "data_range": ["2024-01-01T00:00:00", "2024-01-02T00:00:00"],
    }
    return FeatureGenerationResult(
        features_df=features_df,
        labels_df=labels_df,
        metadata=metadata,
        feature_count=2,
        generation_time=1.0,
        layer_counts=metadata["layer_counts"],
        config_used={},
    )


def test_phase_d_flag_default_off(monkeypatch):
    monkeypatch.delenv("FFACT_NEW_COMPUTE_PATH", raising=False)
    assert FeatureFactoryService._is_new_compute_path_enabled() is False


def test_phase_d_flag_on(monkeypatch):
    monkeypatch.setenv("FFACT_NEW_COMPUTE_PATH", "1")
    assert FeatureFactoryService._is_new_compute_path_enabled() is True


def test_dual_run_sampling_deterministic(monkeypatch):
    service = FeatureFactoryService.__new__(FeatureFactoryService)

    monkeypatch.setenv("FFACT_NEW_COMPUTE_DUALRUN_SAMPLE_RATE", "0")
    assert service._should_run_dual_path_check("task-a") is False

    monkeypatch.setenv("FFACT_NEW_COMPUTE_DUALRUN_SAMPLE_RATE", "1")
    assert service._should_run_dual_path_check("task-a") is True

    monkeypatch.setenv("FFACT_NEW_COMPUTE_DUALRUN_SAMPLE_RATE", "0.25")
    first = service._should_run_dual_path_check("task-a")
    second = service._should_run_dual_path_check("task-a")
    assert first == second


def test_compare_generation_results_pass():
    old_result = _build_result()
    new_result = _build_result()

    ok, reason = FeatureFactoryService._compare_generation_results(old_result, new_result)
    assert ok is True
    assert reason == "ok"


def test_compare_generation_results_fail_on_values():
    old_result = _build_result()
    new_result = _build_result()
    new_result.features_df.iloc[1, 1] = 999.0

    ok, reason = FeatureFactoryService._compare_generation_results(old_result, new_result)
    assert ok is False
    assert reason == "feature_values_mismatch"


def test_compare_generation_results_fail_on_metadata():
    old_result = _build_result()
    new_result = _build_result()
    new_result.metadata["feature_count"] = 3

    ok, reason = FeatureFactoryService._compare_generation_results(old_result, new_result)
    assert ok is False
    assert reason == "metadata_mismatch:feature_count"
