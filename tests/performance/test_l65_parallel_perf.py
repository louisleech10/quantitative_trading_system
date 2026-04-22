import time
from pathlib import Path

import psutil
import pytest

from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import FeaturePreprocessor


def _build_group(group_id: str, n_cols: int) -> ColumnGroup:
    columns = tuple(f"{group_id}_col_{index}" for index in range(n_cols))
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource.L2,
        timeframe="1h",
        data_source="close",
        indicator="mock",
        columns=columns,
        shape=(16, n_cols),
        dtype="float32",
    )


def _build_registry(tmp_path: Path) -> ColumnGroupRegistry:
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    for index, width in enumerate([2, 3, 4, 5], start=1):
        registry.register(_build_group(f"group_{index}", width))
    return registry


@pytest.fixture
def preprocessor() -> FeaturePreprocessor:
    """建立效能驗證用的最小 L6.5 preprocessor。"""
    return FeaturePreprocessor(
        {
            "mode": "replace",
            "winsorization": {"enabled": False},
            "rank_transform": {"enabled": False},
            "adaptive_zscore": {"enabled": False},
            "fractional_differencing": {"enabled": False},
            "adf_differencing": {"enabled": False},
            "gaussian_normalize": {"enabled": False},
        }
    )


def test_l65_parallel_4workers_speedup(
    tmp_path: Path,
    preprocessor: FeaturePreprocessor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試平行 L6.5：4 workers 對獨立 group 應有至少 2 倍加速。"""
    serial_registry = _build_registry(tmp_path / "serial")
    parallel_registry = _build_registry(tmp_path / "parallel")

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(
        preprocessor,
        "_transform_single_group",
        lambda registry, group, context: time.sleep(0.05),
    )

    serial_started = time.perf_counter()
    preprocessor.transform_registry_groups(serial_registry, n_workers=1)
    serial_elapsed = time.perf_counter() - serial_started

    parallel_started = time.perf_counter()
    preprocessor.transform_registry_groups(parallel_registry, n_workers=4)
    parallel_elapsed = time.perf_counter() - parallel_started

    assert parallel_elapsed > 0
    assert serial_elapsed / parallel_elapsed >= 2.0


def test_l65_parallel_rss_under_limit(
    tmp_path: Path,
    preprocessor: FeaturePreprocessor,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試平行 L6.5：RSS 增量應維持在 1GB 以下。"""
    registry = _build_registry(tmp_path / "rss")
    process = psutil.Process()

    monkeypatch.setattr(preprocessor, "_build_registry_transform_context", lambda: {"use_fast": False})
    monkeypatch.setattr(
        preprocessor,
        "_transform_single_group",
        lambda registry, group, context: time.sleep(0.02),
    )

    rss_before = process.memory_info().rss
    preprocessor.transform_registry_groups(registry, n_workers=4)
    rss_after = process.memory_info().rss

    assert rss_after - rss_before < 1 * 1024 ** 3