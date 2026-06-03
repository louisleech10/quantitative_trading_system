"""Shared fixtures for API tests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from api.services.feature_factory_batch_service import FeatureFactoryBatchService


class MockBrowseRegistrar:
    """Test browse registrar that records manifest registrations."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, str]] = []

    def register(self, symbol: str, timeframe: str, manifest_path: str) -> str:
        self.calls.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "manifest_path": manifest_path,
        })
        return f"browse_{symbol}_{timeframe}"


class MockQualityComputer:
    """Test quality computer that returns deterministic batch summaries."""

    def __init__(self, payload: Optional[Dict[str, Any]] = None) -> None:
        self.calls: List[str] = []
        self.payload = payload

    def compute(self, manifest_path: str) -> dict:
        self.calls.append(manifest_path)
        if self.payload is not None:
            return dict(self.payload)
        return {
            "symbol": "MOCK",
            "bar_count": 500,
            "feature_count": 2,
            "nan_ratio_mean": 0.0,
            "nan_ratio_max": 0.0,
            "constant_feature_count": 0,
            "alert_count": 0,
            "grade": "pass",
        }


@pytest.fixture
def mock_browse_registrar() -> MockBrowseRegistrar:
    return MockBrowseRegistrar()


@pytest.fixture
def mock_quality_computer() -> MockQualityComputer:
    return MockQualityComputer()


@pytest.fixture
def batch_service_factory(mock_browse_registrar, mock_quality_computer, tmp_path):
    def _factory(checkpoint_dir: Optional[Path] = None) -> FeatureFactoryBatchService:
        # 縱深防禦:checkpoint_dir 省略時落到 tmp,絕不寫進正式 data_cache/feature_preprocessing
        # (否則測試批次會出現在使用者「歷史批次」下拉並無限增長)。
        return FeatureFactoryBatchService(
            checkpoint_dir=checkpoint_dir or tmp_path / "batch_checkpoints",
            browse_registrar=mock_browse_registrar,
            quality_computer=mock_quality_computer,
        )

    return _factory
