"""FeatureFactory progress_callback fail-open tests (T2 Task 1.1)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from momentum.factories import create_feature_factory


def test_report_progress_failopen_swallows_callback_exception(tmp_path) -> None:
    """callback raise 時 _report_progress 不得向上傳播。"""
    factory = create_feature_factory(cache_dir=str(tmp_path), validate_continuity=False)

    def _boom(_payload: dict) -> None:
        raise RuntimeError("boom")

    factory._progress_callback = _boom
    factory._report_progress("layer_0", 0.0, "Starting layer_0...")


def test_generate_features_progress_failopen(tmp_path) -> None:
    """注入 raise callback 時 generate_features 仍完成。"""
    factory = create_feature_factory(cache_dir=str(tmp_path), validate_continuity=False)

    def _boom(_payload: dict) -> None:
        raise RuntimeError("boom")

    def fake_impl(*_args, **_kwargs):
        factory._report_progress("layer_0", 0.0, "Starting layer_0...")
        result = MagicMock()
        result.hdf5_path = str(tmp_path / "out.h5")
        return result

    factory._generate_features_impl = fake_impl  # type: ignore[method-assign]
    result = factory.generate_features(
        symbol="BTCUSDT",
        timeframe="1h",
        progress_callback=_boom,
    )
    assert result.hdf5_path == str(tmp_path / "out.h5")
