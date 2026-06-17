"""causal_preprocessing 釘死 True：讀取端強制 + fast/registry 傳播鏈測試。

既有斷言 causal=False 差異的測試留待 B3 重寫；本檔僅驗證釘死與傳播。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.preprocessing._native_tf_helpers import (
    scale_preprocessing_config_for_native,
)
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import (
    HAS_SCIPY,
    FeaturePreprocessor,
)


def _winsor_config(*, causal: bool) -> dict:
    return {
        "mode": "replace",
        "causal_preprocessing": causal,
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.25, 0.75],
            "window": 20,
            "apply_to": "all",
        },
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "gaussian_normalize": {"enabled": False},
    }


def test_external_false_forced_true_no_warn_when_missing(caplog: pytest.LogCaptureFixture) -> None:
    """缺 key → True，不 warn。"""
    caplog.set_level("WARNING")
    pp = FeaturePreprocessor({"mode": "replace"})
    assert pp.causal_preprocessing is True
    assert "被忽略" not in caplog.text


def test_external_false_forced_true_no_warn_when_explicit_true(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """顯式 True → True，不 warn。"""
    caplog.set_level("WARNING")
    pp = FeaturePreprocessor(_winsor_config(causal=True))
    assert pp.causal_preprocessing is True
    assert "被忽略" not in caplog.text


def test_external_false_forced_true_with_warn(caplog: pytest.LogCaptureFixture) -> None:
    """顯式 False → 強制 True 並 warn 一次。"""
    caplog.set_level("WARNING")
    pp = FeaturePreprocessor(_winsor_config(causal=False))
    assert pp.causal_preprocessing is True
    assert "被忽略" in caplog.text
    assert "look-ahead" in caplog.text


def test_external_false_output_matches_causal_true_legacy_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """legacy transform 路徑：外部 False 輸出 == causal True。"""
    frame = pd.DataFrame({"alpha": np.r_[np.linspace(1.0, 30.0, 30), 9999.0, 31.0]})
    monkeypatch.setenv("FFACT_USE_POLARS", "0")
    monkeypatch.setenv("FFACT_L65_OPTIMIZATION_PROFILE", "legacy")

    causal_out = FeaturePreprocessor(_winsor_config(causal=True)).transform(frame)
    forced_out = FeaturePreprocessor(_winsor_config(causal=False)).transform(frame)
    np.testing.assert_allclose(
        causal_out.to_numpy(np.float32),
        forced_out.to_numpy(np.float32),
        atol=1e-6,
        equal_nan=True,
    )


def test_external_false_output_matches_causal_true_fast_registry_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fast/registry 路徑：外部 False 經 transform_context 傳播後輸出 == causal True。"""
    if not HAS_SCIPY:
        pytest.skip("scipy required")

    frame = pd.DataFrame({"alpha": np.r_[np.linspace(1.0, 30.0, 30), 9999.0, 31.0]})
    fast_config = {
        **_winsor_config(causal=True),
        "winsorization": {"enabled": False, "window": 20},
        "gaussian_normalize": {
            "enabled": True,
            "clip_range": [0.001, 0.999],
            "apply_to": "all",
        },
    }
    false_config = {**fast_config, "causal_preprocessing": False}

    causal_pre = FeaturePreprocessor(fast_config)
    forced_pre = FeaturePreprocessor(false_config)
    assert forced_pre.causal_preprocessing is True

    causal_ctx = causal_pre._build_registry_transform_context()
    forced_ctx = forced_pre._build_registry_transform_context()
    assert causal_ctx["causal_preprocessing"] is True
    assert forced_ctx["causal_preprocessing"] is True

    def _run_fast(pp: FeaturePreprocessor, ctx: dict, values: pd.DataFrame) -> np.ndarray:
        registry = Mock()
        registry.load_data.return_value = values.to_numpy(np.float32)
        captured: dict[str, np.ndarray] = {}
        registry.overwrite_data.side_effect = lambda _gid, data: captured.setdefault(
            "data", data.copy()
        )
        group = SimpleNamespace(
            group_id="fast",
            columns=("alpha",),
            alignment=None,
            layer="L1",
        )
        pp._transform_single_group(registry, group, ctx)
        return captured["data"]

    causal_fast = _run_fast(causal_pre, causal_ctx, frame)
    forced_fast = _run_fast(forced_pre, forced_ctx, frame)
    np.testing.assert_allclose(causal_fast, forced_fast, atol=1e-6, equal_nan=True)

    perturbed = frame.copy()
    perturbed.iloc[-1, 0] = -9999.0
    causal_perturbed = _run_fast(causal_pre, causal_ctx, perturbed)
    forced_perturbed = _run_fast(forced_pre, forced_ctx, perturbed)
    np.testing.assert_allclose(causal_perturbed, forced_perturbed, atol=1e-6, equal_nan=True)
    np.testing.assert_allclose(causal_fast[:-1], causal_perturbed[:-1], atol=1e-6, equal_nan=True)


def test_native_subinstance_external_false_still_causal() -> None:
    """native/shard 子實例經 __init__ 建立，外部 False 仍強制 True。"""
    parent_config = {
        **_winsor_config(causal=False),
        "winsorization": {
            "enabled": True,
            "method": "quantile",
            "quantile_range": [0.25, 0.75],
            "window": 240,
            "apply_to": "all",
        },
        "calibration_bars": 600,
    }
    parent = FeaturePreprocessor(parent_config)
    assert parent.causal_preprocessing is True

    scaled = scale_preprocessing_config_for_native(parent_config, "12h", "1h")
    native_pp = FeaturePreprocessor(scaled)
    assert native_pp.causal_preprocessing is True

    native_values = np.r_[np.linspace(1.0, 60.0, 60), 9999.0].astype(np.float32)[:, None]
    idx_map = np.repeat(np.arange(len(native_values), dtype=np.int32), 12)
    group = SimpleNamespace(
        group_id="native",
        columns=("alpha",),
        layer="L1",
        alignment=SimpleNamespace(
            source_timeframe="12h",
            primary_timeframe="1h",
            source_n_rows=len(native_values),
            primary_n_rows=len(idx_map),
        ),
    )

    def _run_native(values: np.ndarray) -> np.ndarray:
        registry = Mock()
        registry.load_data_native.return_value = values
        registry.get_alignment_idx_map.return_value = idx_map
        captured: dict[str, np.ndarray] = {}
        registry.overwrite_data.side_effect = lambda _gid, data: captured.setdefault(
            "data", data.copy()
        )
        assert parent._maybe_run_native_l65_inplace(registry, group)
        return captured["data"]

    native_out = _run_native(native_values)
    perturbed = native_values.copy()
    perturbed[-1, 0] = -9999.0
    native_perturbed = _run_native(perturbed)
    np.testing.assert_allclose(native_out[:-12], native_perturbed[:-12], atol=1e-6, equal_nan=True)
