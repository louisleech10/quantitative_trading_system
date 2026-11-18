"""TESTSEL I1e｜SPEC Task 2.5：L3 kurt 守衛下界依窗長奇偶取可達最小值（numba 臂與 numpy 臂同式）。

依據（runs/testsel_route/i1e/i1e_facts.md）：樣本超額峰度可達最小值——偶數 n：−2(n−1)/(n−3)；奇數 n：−2n/(n−2)
（平衡兩點 k／k+1；n≥7 解析證明、n=5 精確證書、數值驗至 n≤10001）。現行兩臂對所有 n 用偶數式 ⇒ 奇數 n 守衛偏寬。
平衡兩點窗以真實 BTCUSDT/1h close 之兩相異值排成（值來自真實資料；排列為邊界構造）。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from momentum.FeatureEngineering.operators import numba_rolling
from momentum.FeatureEngineering.operators import rolling_moments_numpy as rmn

REPO = Path(__file__).resolve().parents[2]
ODD = [5, 7, 13, 21, 233]
EVEN = [4, 6, 14, 22]


def _exact_lower(n: int) -> float:
    return -2.0 * n / (n - 2.0) if n % 2 else -2.0 * (n - 1.0) / (n - 3.0)


@pytest.fixture(scope="module")
def two_values() -> tuple:
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    df = KlineStorageManager(cache_dir=str(REPO / "data_cache" / "feature_klines")).read_klines(
        "BTCUSDT", "1h", validate_continuity=False)
    close = df["close"].to_numpy(dtype=np.float64)
    if len(close) < 1000:
        pytest.fail("真實 BTCUSDT/1h K 線不足（資料缺件須補齊，不得 skip）")
    a = float(close[-1])
    b = float(next(v for v in close[::-1] if v != a))
    return a, b


def _balanced_window(n: int, a: float, b: float) -> np.ndarray:
    k = n // 2
    return np.array([a] * k + [b] * (n - k), dtype=np.float64)


def _numba_last_kurt(x: np.ndarray, n: int) -> float:
    out = numba_rolling.rolling_skew_kurt(x, n)
    return float(np.asarray(out)[-1, 1])


def _kurt_from_target(n: int, g: float) -> tuple:
    """回 (m2, m4) 使 `_compute_kurt` 之未守衛結果恰為 g（m2＝1、mean＝0）。"""
    excess = (g * (n - 2.0) * (n - 3.0) / (n - 1.0) - 6.0) / (n + 1.0)
    return 1.0, (excess + 3.0) / n


@pytest.mark.parametrize("n", ODD + EVEN)
def test_accept_01_balanced_two_point_both_arms_equal_exact_lower(n: int, two_values) -> None:
    """① 平衡兩點窗：兩臂 kurt 有限且等於可達最小值（奇數 −2n/(n−2)、偶數 −2(n−1)/(n−3)）。"""
    x = _balanced_window(n, *two_values)
    got_np = float(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])
    got_nb = _numba_last_kurt(x, n)
    want = _exact_lower(n)
    # numpy 臂回 float64（≤1e-9 相對）；numba 臂 `rolling_skew_kurt` 回 float32（≤1 float32 ulp）
    assert np.isfinite(got_np) and abs(got_np - want) <= 1e-9 * abs(want), (n, got_np, want)
    assert np.isfinite(got_nb) and (abs(got_nb - want) <= abs(float(np.spacing(np.float32(want))))), (n, got_nb, want)


@pytest.mark.parametrize("n", ODD)
def test_accept_02_numba_guard_rejects_between_even_and_odd_bound(n: int) -> None:
    """② 奇數 n：結果落於 (偶數式, 奇數式) 之間 ⇒ NaN；恰於奇數式 ⇒ 保留（numba `_compute_kurt` 直呼）。"""
    even, odd = -2.0 * (n - 1.0) / (n - 3.0), -2.0 * n / (n - 2.0)
    mid = (even + odd) / 2.0
    m2, m4 = _kurt_from_target(n, mid)
    assert np.isnan(numba_rolling._compute_kurt(m2, m4, n, 0.0)), (n, mid)
    m2, m4 = _kurt_from_target(n, odd)
    kept = numba_rolling._compute_kurt(m2, m4, n, 0.0)
    assert np.isfinite(kept) and abs(kept - odd) <= 1e-9 * abs(odd), (n, kept)


@pytest.mark.parametrize("n", ODD + EVEN)
def test_accept_03_numpy_lower_bound_helper_matches_exact(n: int) -> None:
    """② numpy 臂之下界式（`_kurt_lower`）逐 n 等於可達最小值。"""
    assert abs(rmn._kurt_lower(float(n)) - _exact_lower(n)) <= 1e-15 * abs(_exact_lower(n)), n


def test_accept_04_numpy_core_guard_uses_helper(two_values, monkeypatch) -> None:
    """numpy 核心之下界判定經 `_kurt_lower`：換成高於平衡兩點值之下界 ⇒ 該窗 kurt 變 NaN（證守衛真走此式）。"""
    n = 5
    x = _balanced_window(n, *two_values)
    assert np.isfinite(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])
    monkeypatch.setattr(rmn, "_kurt_lower", lambda nn: -1.0)
    assert np.isnan(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])


@pytest.mark.parametrize("n", ODD + EVEN)
def test_boundary_02_numba_tolerance_unchanged(n: int) -> None:
    """容差 `_MOMENT_BOUND_TOL`（1e-9）不變：下界 L 之相對 0.5e-9 外推仍保留、2e-9 外推 ⇒ NaN（numba `_compute_kurt` 直呼）。"""
    lower = _exact_lower(n)
    m2, m4 = _kurt_from_target(n, lower * (1.0 + 0.5e-9))
    assert np.isfinite(numba_rolling._compute_kurt(m2, m4, n, 0.0)), (n, "容差內須保留")
    m2, m4 = _kurt_from_target(n, lower * (1.0 + 2e-9))
    assert np.isnan(numba_rolling._compute_kurt(m2, m4, n, 0.0)), (n, "容差外須 NaN")


def test_boundary_03_numpy_tolerance_and_comparison_unchanged(two_values, monkeypatch) -> None:
    """numpy 臂之下界比較與容差：真實平衡兩點窗之實際 kurt g，將 `_kurt_lower` 置於 g 兩側——
    g/(1+0.5e-9)（g 在容差內）⇒ 保留；g/(1+2e-9)（g 在容差外）⇒ NaN（經 `_moments_block` 實際比較）。"""
    n = 7
    x = _balanced_window(n, *two_values)
    g = float(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])
    assert np.isfinite(g) and g < 0
    monkeypatch.setattr(rmn, "_kurt_lower", lambda nn: g / (1.0 + 0.5e-9))
    assert np.isfinite(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])
    monkeypatch.setattr(rmn, "_kurt_lower", lambda nn: g / (1.0 + 2e-9))
    assert np.isnan(rmn.rolling_skew_kurt_numpy(x, n)[-1, 1])


@pytest.mark.parametrize("n", EVEN)
def test_boundary_01_even_n_unchanged(n: int) -> None:
    """③ 偶數 n：恰於 −2(n−1)/(n−3) ⇒ 保留；低於其容差外 ⇒ NaN（行為不變）。"""
    lower = -2.0 * (n - 1.0) / (n - 3.0)
    m2, m4 = _kurt_from_target(n, lower)
    assert np.isfinite(numba_rolling._compute_kurt(m2, m4, n, 0.0))
    m2, m4 = _kurt_from_target(n, lower * 1.01)
    assert np.isnan(numba_rolling._compute_kurt(m2, m4, n, 0.0))
