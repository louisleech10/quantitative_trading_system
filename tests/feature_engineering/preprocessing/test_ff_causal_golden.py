from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.factories import create_feature_factory, create_kline_storage_manager
from momentum.FeatureEngineering.preprocessing._numba_transforms import _rolling_rank_numba
from momentum.FeatureEngineering.preprocessing.feature_preprocessor import HAS_SCIPY, FeaturePreprocessor

try:
    from scipy.special import ndtri
except Exception:  # pragma: no cover
    ndtri = None


REAL_BASELINE = Path("tests/golden/l65/tier2_reduced/ETHUSDT_1h_2000rows.parquet")


def _real_numeric_frame() -> pd.DataFrame:
    if not REAL_BASELINE.exists():
        pytest.skip("missing real ETHUSDT L6.5 baseline parquet")
    frame = pd.read_parquet(REAL_BASELINE)
    # FFSTAT b4：縮尾窗 252 之不完整窗遮罩後 rank 再需暖身 ⇒ 320 列無可比值，改 640 列；ICPOSTLEAK：gaussian 另遮
    # 窗未滿（基準首個有限值於第 199 列 ⇒ 縮尾後 450、gaussian 後 701）⇒ 改 1000 列（基準共 2000 列）
    numeric = frame.select_dtypes(include=[np.number]).iloc[:1000, :3]
    if numeric.empty or len(numeric) < 260:
        pytest.skip("real baseline does not have enough numeric rows")
    return numeric.astype(float)


def _mask_incomplete_window(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    """FFSTAT b4（SPEC v32 逐欄穩定點第①類）：縮尾輸出逐欄自首個有限值起 window−1 列（及其前）為 NaN。
    獨立於生產 `stable_mask.mask_incomplete_window_inplace` 之逐欄實作（只施於縮尾；rank／gaussian 不另遮）。"""
    out = frame.copy()
    for col in out.columns:
        finite = np.flatnonzero(np.isfinite(frame[col].to_numpy(np.float64)))
        cut = len(out) if finite.size == 0 else min(int(finite[0]) + int(window) - 1, len(out))
        out.iloc[:cut, out.columns.get_loc(col)] = np.nan
    return out


def test_causal_preprocessing_changes_legacy_values_on_real_baseline() -> None:
    if not HAS_SCIPY:
        pytest.skip("scipy required")
    if ndtri is None:
        pytest.skip("scipy ndtri required")

    frame = _real_numeric_frame()
    base = {
        "mode": "replace",
        "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.05, 0.95], "window": 252, "apply_to": "all"},
        "rank_transform": {"enabled": False},
        "adaptive_zscore": {"enabled": False},
        "gaussian_normalize": {"enabled": True, "clip_range": [0.001, 0.999], "apply_to": "all"},
    }
    # causal 釘死後，外部 False 會被強制為 True；legacy(False) fingerprint 已不可達。
    forced = FeaturePreprocessor({**base, "causal_preprocessing": False}).transform(frame)
    causal = FeaturePreprocessor({**base, "causal_preprocessing": True}).transform(frame)

    window = 252
    min_periods = max(20, window // 4)
    lower = frame.rolling(window, min_periods=min_periods).quantile(0.05)
    upper = frame.rolling(window, min_periods=min_periods).quantile(0.95)
    clipped = frame.where(
        lower.isna() | upper.isna(),
        frame.clip(lower=lower, upper=upper, axis=1),
    )
    clipped = _mask_incomplete_window(clipped, window)  # FFSTAT b4：縮尾之不完整窗遮罩先於 rank
    ranked = pd.DataFrame(
        _rolling_rank_numba(clipped.to_numpy(dtype=np.float64, copy=False), window, min_periods),
        index=frame.index,
        columns=frame.columns,
    )
    expected = pd.DataFrame(
        ndtri(ranked.clip(0.001, 0.999).to_numpy(float)),
        index=frame.index,
        columns=frame.columns,
    )
    # ICPOSTLEAK Task 1.1：gaussian 輸出另遮窗未滿之列（錨點＝gaussian 之輸入 clipped 之逐欄首個有限值、窗 252）
    for column in expected.columns:
        finite = np.flatnonzero(np.isfinite(clipped[column].to_numpy(dtype=np.float64)))
        cut = len(expected) if finite.size == 0 else min(int(finite[0]) + window - 1, len(expected))
        expected.iloc[:cut, expected.columns.get_loc(column)] = np.nan

    assert np.isfinite(expected.to_numpy(np.float64)).sum() > 0, "前提：遮罩後仍有可比之有限值"
    assert list(forced.columns) == list(causal.columns)
    assert list(forced.shape) == list(causal.shape)
    np.testing.assert_allclose(
        forced.to_numpy(np.float32),
        expected.to_numpy(np.float32),
        atol=1e-6,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        causal.to_numpy(np.float32),
        expected.to_numpy(np.float32),
        atol=1e-6,
        equal_nan=True,
    )
    diff = np.nanmax(np.abs(forced.to_numpy(np.float64) - causal.to_numpy(np.float64)))
    assert diff < 1e-6
    forced_value_sha256 = hashlib.sha256(
        np.ascontiguousarray(forced.to_numpy(np.float64)).tobytes()
    ).hexdigest()
    causal_value_sha256 = hashlib.sha256(
        np.ascontiguousarray(causal.to_numpy(np.float64)).tobytes()
    ).hexdigest()
    assert forced_value_sha256 == causal_value_sha256


def test_rolling_quantile_oracle_on_real_baseline() -> None:
    frame = _real_numeric_frame()
    config = {
        "mode": "replace",
        "causal_preprocessing": True,
        "winsorization": {"enabled": True, "method": "quantile", "quantile_range": [0.05, 0.95], "window": 252, "apply_to": "all"},
    }
    result = FeaturePreprocessor(config)._apply_winsorization(frame)

    window = 252
    min_periods = max(20, window // 4)
    lower = frame.rolling(window, min_periods=min_periods).quantile(0.05)
    upper = frame.rolling(window, min_periods=min_periods).quantile(0.95)
    expected = frame.copy()
    valid = lower.notna() & upper.notna()
    expected = expected.where(~valid, expected.clip(lower=lower, upper=upper, axis=1))
    expected = _mask_incomplete_window(expected, window)  # FFSTAT b4
    assert np.isfinite(expected.to_numpy(np.float64)).sum() > 0, "前提：遮罩後仍有可比之有限值"
    np.testing.assert_allclose(result.to_numpy(np.float32), expected.to_numpy(np.float32), atol=1e-6, equal_nan=True)

    perturbed = frame.copy()
    perturbed.iloc[-2:, :] = perturbed.iloc[-2:, :] * -1000.0
    perturbed_result = FeaturePreprocessor(config)._apply_winsorization(perturbed)
    np.testing.assert_allclose(
        result.iloc[:-2].to_numpy(np.float32),
        perturbed_result.iloc[:-2].to_numpy(np.float32),
        atol=1e-6,
        equal_nan=True,
    )


@pytest.mark.requires_kline
def test_real_generate_e2e_causal_preprocessing_no_persist(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    storage = create_kline_storage_manager()
    try:
        klines = storage.read_klines("ETHUSDT", "1h", validate_continuity=False)
    except Exception:
        klines = None
    if klines is None or klines.empty:
        pytest.fail("missing real ETHUSDT/1h klines")

    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
    factory = create_feature_factory(validate_continuity=False)
    result = factory.generate_features(
        "ETHUSDT",
        "1h",
        config_override={
            "preset": "minimal",
            "preprocessing": {
                "causal_preprocessing": True,
                "winsorization": {"window": 252},
            },
        },
        force_regenerate=True,
        persist=False,
    )
    assert result.feature_count > 0
    assert result.features_df.shape[0] > 100
    assert not np.isinf(result.features_df.select_dtypes(include=[np.number]).to_numpy()).any()
