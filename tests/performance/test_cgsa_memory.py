"""Phase 2 記憶體驗證測試（T2.13）。"""

from __future__ import annotations

import platform
import resource
from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock

import numpy as np
import pytest

try:
    import psutil
except Exception:  # pragma: no cover
    psutil = None

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory


def _rss_mb() -> float:
    if psutil is not None:
        return float(psutil.Process().memory_info().rss / (1024.0 * 1024.0))

    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if platform.system() == "Darwin":
        return float(value) / (1024.0 * 1024.0)
    return float(value) / 1024.0


def _make_group(group_id: str, columns: tuple[str, ...]) -> ColumnGroup:
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="EMA",
        columns=columns,
        shape=(0, 0),
        dtype="float32",
        disk_path=None,
    )


@pytest.fixture(scope="module")
def cgsa_validation_run(tmp_path_factory: pytest.TempPathFactory) -> Dict[str, Any]:
    """CGSA per-group validate 跑一次：回傳驗證結果與前後行程 RSS（MB）。

    TESTSEL S3：驗證結果（has_inf／coverage）屬正確性；RSS 為整個 pytest 行程之絕對值，受同行程先前測試與配置器
    影響 ⇒ 該門檻移至 perf 測試。兩條共用本次計算，不重複。
    """
    tmp_path = tmp_path_factory.mktemp("cgsa_memory")
    registry = ColumnGroupRegistry(work_dir=tmp_path / "registry")

    rows = 50_000
    group_a = np.random.default_rng(42).normal(size=(rows, 16)).astype(np.float32)
    group_b = np.random.default_rng(7).normal(size=(rows, 16)).astype(np.float32)
    group_c = np.random.default_rng(99).normal(size=(rows, 16)).astype(np.float32)

    registry.save_data(
        _make_group(
            "1h_L3_trend_EMA_close",
            tuple(f"close_1h_trend_EMA_5_mean_{idx}" for idx in range(group_a.shape[1])),
        ),
        group_a,
    )
    registry.save_data(
        _make_group(
            "1h_L3_momentum_RSI_close",
            tuple(f"close_1h_momentum_RSI_14_rank_{idx}" for idx in range(group_b.shape[1])),
        ),
        group_b,
    )
    registry.save_data(
        _make_group(
            "1h_L3_volatility_ATR_close",
            tuple(f"close_1h_volatility_ATR_14_std_{idx}" for idx in range(group_c.shape[1])),
        ),
        group_c,
    )

    factory = FeatureFactory(config_manager=Mock(), adapter_registry=Mock())

    rss_before = _rss_mb()
    validation = factory._scan_cgsa_registry_validation(registry)
    rss_after = _rss_mb()
    return {"validation": validation, "rss_before": rss_before, "rss_after": rss_after}


def test_cgsa_validation_no_inf_full_coverage(cgsa_validation_run: Dict[str, Any]) -> None:
    """T2.13 之正確性部分：三組有限常態資料經 per-group validate ⇒ 無 inf、覆蓋率 > 0.99。"""
    validation = cgsa_validation_run["validation"]
    assert validation["has_inf"] is False
    assert validation["coverage"] > 0.99


@pytest.mark.perf
def test_cgsa_ram_peak_under_2gb(cgsa_validation_run: Dict[str, Any]) -> None:
    """T2.13: CGSA per-group validate 路徑的 RSS 峰值應低於 2GB。"""
    rss_before, rss_after = cgsa_validation_run["rss_before"], cgsa_validation_run["rss_after"]

    peak_rss_mb = max(rss_before, rss_after)

    assert peak_rss_mb < 2048.0
