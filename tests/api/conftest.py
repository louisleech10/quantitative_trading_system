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


@pytest.fixture(autouse=True)
def _fresh_ic_admission():
    """每條測試一個乾淨之 IC 分析准入控制器（ICPERF v5.87 (h)「⑤ IC 分析啟動准入」）。

    TestClient 於每個請求結束即關閉其事件迴圈，`/analyze` 以 `asyncio.create_task` 排入之背景分析隨之銷毀、
    不跑完 ⇒ 其保留量不會經 worker 結束釋放，會跨測試累積而使後續請求排隊（實際踩到：受影響測試合跑卡在深度分析
    監看之事件等待）。正式伺服器之事件迴圈常駐，背景任務跑完即釋放，無此情形；本 fixture 只做測試隔離。"""
    from api.services import ic_analysis_service as svc_mod
    from momentum.factories import create_ic_admission_controller

    svc = svc_mod.ic_analysis_service
    saved = (svc._admission, dict(svc._queued_starts), dict(svc._early_admission))  # noqa: SLF001
    fresh = create_ic_admission_controller()
    fresh.on_admit = svc._on_admitted  # noqa: SLF001
    fresh.on_reject = svc._on_rejected  # noqa: SLF001
    svc._admission = fresh  # noqa: SLF001
    svc._queued_starts.clear()  # noqa: SLF001
    svc._early_admission.clear()  # noqa: SLF001
    yield
    svc._admission = saved[0]  # noqa: SLF001
    svc._queued_starts.clear()  # noqa: SLF001
    svc._queued_starts.update(saved[1])  # noqa: SLF001
    svc._early_admission.clear()  # noqa: SLF001
    svc._early_admission.update(saved[2])  # noqa: SLF001


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
