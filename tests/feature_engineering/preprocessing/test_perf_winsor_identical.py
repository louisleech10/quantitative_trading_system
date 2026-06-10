"""P0 winsor byte-identical gate(FF_CAUSAL_PERF_FIX SPEC §G/§V)。

主 gate:production rolling_quantile_2d 在 sliding kernel 下,對 vendored 改前 legacy kernel
**逐位元相同**(np.array_equal(equal_nan=True) 且 uint8-view 相等;lower+upper)。
reference / 輸入 / numba 缺失 → FAIL 非 skip。

P0.0(本任務):production 仍 == legacy,cross-check 確認 vendored 為改前忠實副本 + 骨架就緒。
P0.1:production rolling_quantile_2d 路由 sliding kernel 後,同一 gate 成為真實 byte 防線。
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

import numpy as np
import pytest

from tests._fixtures.rolling_quantile_legacy import (
    _HAS_NUMBA as LEGACY_HAS_NUMBA,
    rolling_quantile_2d_legacy,
)

ROOT = Path(__file__).resolve().parents[3]
FIXTURE_NPY = ROOT / "tests/_fixtures/winsor_input_eth1h.npy"
FIXTURE_SHA = ROOT / "tests/_fixtures/winsor_input_eth1h.sha256"

# (lower_q, upper_q, window, min_periods) — 涵蓋預設與邊界窗
CONFIGS = [
    (0.05, 0.95, 252, max(20, 252 // 4)),  # 生產預設 winsor 窗
    (0.05, 0.95, 1, 1),                    # 最小窗
    (0.01, 0.99, 24, 6),
    (0.10, 0.90, 96, 24),
]


def _load_fixture() -> np.ndarray:
    if not FIXTURE_NPY.is_file() or not FIXTURE_SHA.is_file():
        pytest.fail(f"winsor fixture 缺失:{FIXTURE_NPY}(reference 缺失必 FAIL 非 skip)")
    digest = hashlib.sha256(FIXTURE_NPY.read_bytes()).hexdigest()
    expected = FIXTURE_SHA.read_text(encoding="utf-8").strip()
    if digest != expected:
        pytest.fail(f"winsor fixture sha256 不符:{digest} != {expected}")
    return np.load(FIXTURE_NPY, allow_pickle=False)


def _assert_byte_identical(actual: np.ndarray, expected: np.ndarray, label: str) -> None:
    assert actual.shape == expected.shape, f"{label} shape {actual.shape}!={expected.shape}"
    assert actual.dtype == expected.dtype == np.float32, f"{label} dtype {actual.dtype}"
    # 值 + NaN-mask
    assert np.array_equal(actual, expected, equal_nan=True), f"{label} array_equal 失敗"
    # 逐位元(擋 ±0.0 / NaN payload 差):NaN 位先對齊再比非 NaN bytes
    a_nan, e_nan = np.isnan(actual), np.isnan(expected)
    assert np.array_equal(a_nan, e_nan), f"{label} NaN mask 不一致"
    a_bytes = actual[~a_nan].view(np.uint8)
    e_bytes = expected[~e_nan].view(np.uint8)
    assert np.array_equal(a_bytes, e_bytes), f"{label} uint8-view 逐位元不一致"


def test_numba_required() -> None:
    """byte gate 釘 numba 路徑;numba 不可用 → FAIL 非 skip(SPEC §C numba 必需)。"""
    assert LEGACY_HAS_NUMBA, "numba 不可用:winsor byte gate 必須在 numba 路徑驗收(FAIL 非 skip)"


def test_fixture_present_and_pinned() -> None:
    mat = _load_fixture()
    assert mat.shape == (20352, 32), mat.shape
    assert mat.dtype == np.float64


@pytest.mark.parametrize("lower_q,upper_q,window,min_periods", CONFIGS)
def test_production_kernel_byte_identical_to_legacy(
    monkeypatch: pytest.MonkeyPatch,
    lower_q: float,
    upper_q: float,
    window: int,
    min_periods: int,
) -> None:
    """主 gate:production rolling_quantile_2d == vendored legacy,逐位元(lower+upper)。

    強制 sliding kernel(P0.1 實作期 default=legacy,故此處顯式要求 sliding 路徑)。
    P0.0 時該 env 尚未被 production 識別 → production 仍走 legacy → 與 vendored 相等(亦即
    cross-check:vendored 為改前忠實副本)。P0.1 後 production 走 sliding → 真實 byte 防線。
    """
    monkeypatch.setenv("FFACT_ROLLING_QUANTILE_KERNEL", "sliding")
    # 延遲 import 確保 env 在 call 時生效(P0.1 須在 call-time 讀 flag)
    from momentum.FeatureEngineering.preprocessing._numba_transforms import (
        rolling_quantile_2d as production_rolling_quantile_2d,
    )

    mat = _load_fixture()
    prod_lo, prod_hi = production_rolling_quantile_2d(mat, lower_q, upper_q, window, min_periods)
    ref_lo, ref_hi = rolling_quantile_2d_legacy(mat, lower_q, upper_q, window, min_periods)
    _assert_byte_identical(prod_lo, ref_lo, f"lower(w={window},mp={min_periods})")
    _assert_byte_identical(prod_hi, ref_hi, f"upper(w={window},mp={min_periods})")


@pytest.mark.parametrize("seed", range(8))
def test_sliding_kernel_fuzz_byte_identical(
    monkeypatch: pytest.MonkeyPatch,
    seed: int,
) -> None:
    """隨機有限值與特殊邊界對 vendored legacy 逐位元一致。"""
    from momentum.FeatureEngineering.preprocessing._numba_transforms import rolling_quantile_2d

    rng = np.random.default_rng(seed)
    mat = rng.normal(size=(257, 9)).astype(np.float64)
    mat[:, 0] = np.nan
    mat[::7, 1] = np.inf
    mat[::11, 1] = -np.inf
    mat[:, 2] = rng.choice(np.array([-2.0, -0.0, 0.0, 2.0]), size=mat.shape[0])
    mat[::5, 3] = -0.0
    mat[1::5, 3] = 0.0
    mat[::13, 4] = np.nextafter(0.0, 1.0)
    mat[::17, 5] = np.nan

    window = int(rng.integers(1, 80))
    min_periods = int(rng.integers(1, window + 1))
    lower_q = float(rng.choice(np.array([0.0, 0.01, 0.05, 0.25])))
    upper_q = float(rng.choice(np.array([0.75, 0.95, 0.99, 1.0])))
    monkeypatch.setenv("FFACT_ROLLING_QUANTILE_KERNEL", "sliding")

    actual = rolling_quantile_2d(mat, lower_q, upper_q, window, min_periods)
    expected = rolling_quantile_2d_legacy(mat, lower_q, upper_q, window, min_periods)
    _assert_byte_identical(actual[0], expected[0], f"fuzz lower(seed={seed})")
    _assert_byte_identical(actual[1], expected[1], f"fuzz upper(seed={seed})")


def test_default_kernel_byte_identical(monkeypatch: pytest.MonkeyPatch) -> None:
    """未設定 flag 時 production 走預設 kernel(現為 sliding),且對 vendored legacy 逐位元相同。"""
    from momentum.FeatureEngineering.preprocessing._numba_transforms import rolling_quantile_2d

    monkeypatch.delenv("FFACT_ROLLING_QUANTILE_KERNEL", raising=False)
    mat = _load_fixture()[:384, :8]
    actual = rolling_quantile_2d(mat, 0.05, 0.95, 24, 6)
    expected = rolling_quantile_2d_legacy(mat, 0.05, 0.95, 24, 6)
    _assert_byte_identical(actual[0], expected[0], "default legacy lower")
    _assert_byte_identical(actual[1], expected[1], "default legacy upper")


@pytest.mark.perf
def test_sliding_kernel_microbench_ratio(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """記錄 sliding/legacy median runtime ratio；計時結果不作正確性 gate。"""
    from momentum.FeatureEngineering.preprocessing._numba_transforms import rolling_quantile_2d

    mat = _load_fixture()[:4096, :16]
    timings: dict[str, list[float]] = {"legacy": [], "sliding": []}
    for kernel in ("legacy", "sliding"):
        monkeypatch.setenv("FFACT_ROLLING_QUANTILE_KERNEL", kernel)
        rolling_quantile_2d(mat[:64], 0.05, 0.95, 24, 6)
        for _ in range(3):
            start = time.perf_counter()
            rolling_quantile_2d(mat, 0.05, 0.95, 252, 63)
            timings[kernel].append(time.perf_counter() - start)

    legacy_median = float(np.median(timings["legacy"]))
    sliding_median = float(np.median(timings["sliding"]))
    ratio = sliding_median / legacy_median
    with capsys.disabled():
        print(
            f"winsor microbench sliding/legacy={ratio:.4f} "
            f"(sliding={sliding_median:.6f}s legacy={legacy_median:.6f}s)"
        )
