import pytest

from api.models.ic_models import DeepAnalysisResponse, ICFullAnalysisRequest


def test_api_request_with_tier():
    request = ICFullAnalysisRequest(
        features_path="test",
        labels_path="test",
        feature_tiers={"active_preset": "foundation"},
    )
    assert request.feature_tiers is not None
    assert request.feature_tiers.active_preset == "foundation"


def test_api_response_includes_applied_tier():
    response = DeepAnalysisResponse(
        task_id="task",
        status="completed",
        progress=1.0,
        applied_tier="intermediate",
    )
    assert response.applied_tier == "intermediate"


def test_invalid_tier_rejected():
    with pytest.raises(Exception):
        ICFullAnalysisRequest(
            features_path="test",
            labels_path="test",
            feature_tiers={"active_preset": "invalid"},
        )


def test_tier_config_serialization():
    request = ICFullAnalysisRequest(
        features_path="test",
        labels_path="test",
        feature_tiers={
            "active_preset": "custom",
            "custom_overrides": {
                "stage_overrides": {"ic_decay": False},
                "module_overrides": {"factor_return": False},
            },
        },
    )
    data = request.model_dump()
    assert data["feature_tiers"]["active_preset"] == "custom"
    assert data["feature_tiers"]["custom_overrides"]["module_overrides"]["factor_return"] is False
