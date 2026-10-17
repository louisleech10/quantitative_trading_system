"""Phase 4 tests: consumer migration (date range, IC, XGBoost, frontend types)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


def test_generate_features_accepts_date_range() -> None:
    """generate_features should accept start_date/end_date without error."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    import inspect

    sig = inspect.signature(FeatureFactory.generate_features)
    params = list(sig.parameters.keys())
    assert "start_date" in params, "start_date parameter missing"
    assert "end_date" in params, "end_date parameter missing"


def _layer0_with_frame(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """以生產 Layer 0（`FeatureFactory._layer0_data_ingestion`）之起訖裁切處理 df。

    只替身資料來源（adapter registry 回傳 df）；起訖換算與裁切全走生產碼。
    """
    from types import SimpleNamespace

    from momentum.FeatureEngineering.feature_factory import FeatureFactory

    class _Registry:
        def list_all(self):
            return ["stub"]

        def get(self, _name):
            return SimpleNamespace(market="crypto")

        def fetch_aligned(self, _symbol, _timeframe, _sources):
            return df.copy()

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._adapter_registry = _Registry()
    config = SimpleNamespace(data_sources=SimpleNamespace(enabled_sources=[], synthetic_sources=[]))
    return factory._layer0_data_ingestion("BTCUSDT", "1h", config, start_date=start_date, end_date=end_date)


def test_date_range_filters_data() -> None:
    """Date range filtering (production Layer 0) should reduce rows when range is narrow."""
    idx = pd.date_range("2024-01-01", periods=100, freq="h")
    df = pd.DataFrame({"close": range(100)}, index=idx.astype("int64") // 10**6)

    filtered = _layer0_with_frame(df, "2024-01-02", "2024-01-03")

    assert len(filtered) < len(df), "Filtering should reduce rows"
    assert len(filtered) > 0, "Filtering should not remove all rows"
    # 起訖兩端皆含（2024-01-02 00:00 … 2024-01-03 00:00，逐時 25 根）
    kept = pd.to_datetime(filtered.index, unit="ms")
    assert kept.min() == pd.Timestamp("2024-01-02")
    assert kept.max() == pd.Timestamp("2024-01-03")
    assert len(filtered) == 25
    assert filtered["close"].tolist() == list(range(24, 49))


def test_date_range_none_no_filtering() -> None:
    """When start_date/end_date are None, production Layer 0 should not filter."""
    idx = pd.date_range("2024-01-01", periods=50, freq="h")
    df = pd.DataFrame({"close": range(50)}, index=idx.astype("int64") // 10**6)

    filtered = _layer0_with_frame(df, None, None)

    assert len(filtered) == 50
    pd.testing.assert_frame_equal(filtered, df)


def test_ic_analysis_service_has_feature_library() -> None:
    """ICAnalysisService should have _feature_library attribute after init."""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"


def test_ic_analysis_feature_library_fallback() -> None:
    """When features_path is empty, IC service should support FeatureLibrary fallback."""
    from api.services.ic_analysis_service import ICAnalysisService
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    service = ICAnalysisService()
    assert isinstance(service._feature_library, FeatureLibrary)


def test_frontend_types_has_registry_entry() -> None:
    """Verify types.ts contains FeatureRegistryEntry interface."""
    types_path = Path("frontend/src/lib/types.ts")
    if not types_path.exists():
        pytest.skip("Frontend types.ts not found")
    content = types_path.read_text(encoding="utf-8")
    assert "FeatureRegistryEntry" in content, "Missing FeatureRegistryEntry type"


def test_config_hash_includes_date_range() -> None:
    """_compute_config_hash should accept date range parameters."""
    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    import inspect

    sig = inspect.signature(FeatureFactory._compute_config_hash)
    params = list(sig.parameters.keys())
    assert "start_date" in params, "_compute_config_hash missing start_date"
    assert "end_date" in params, "_compute_config_hash missing end_date"


def test_decoupling_no_api_in_momentum() -> None:
    """momentum/ must not import from api/."""
    import subprocess

    result = subprocess.run(
        ["grep", "-r", "from api\\.", "momentum/", "--include=*.py"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
    )
    offending = [
        line for line in result.stdout.strip().split("\n")
        if line and "__pycache__" not in line
    ]
    assert len(offending) == 0, "Decoupling violation:\n" + "\n".join(offending)


def test_feature_registry_route() -> None:
    """GET /api/v1/feature-registry/entries should return 200."""
    try:
        from fastapi.testclient import TestClient
        from api.main import app
    except ImportError:
        pytest.skip("FastAPI test client not available")

    client = TestClient(app)
    response = client.get("/api/v1/feature-registry/entries")
    assert response.status_code == 200
    body = response.json()
    assert "entries" in body
    assert "total" in body


def test_xgboost_batch_service_has_feature_library() -> None:
    """XGBoostBatchService should have _feature_library attribute."""
    from api.services.xgboost_batch_service import XGBoostBatchService

    service = XGBoostBatchService()
    assert hasattr(service, "_feature_library"), "Missing _feature_library attribute"






def test_feature_generation_request_has_date_fields() -> None:
    """FeatureGenerationRequest should expose start_date and end_date fields."""
    from api.models.feature_factory_models import FeatureGenerationRequest

    req = FeatureGenerationRequest(
        symbols=["BTCUSDT"],
        timeframe="1h",
        start_date="2024-01-01",
        end_date="2025-12-31",
    )
    assert req.start_date == "2024-01-01"
    assert req.end_date == "2025-12-31"


def test_kline_download_trigger_exists() -> None:
    """KlineDownloadTrigger.tsx should exist in common components."""
    component_path = Path("frontend/src/components/common/KlineDownloadTrigger.tsx")
    assert component_path.exists(), "KlineDownloadTrigger.tsx not found"
