"""TESTSEL I1b｜SPEC Task 2.4：L3 skew／kurt 之非預設臂（pandas 串流、numba 單窗、非串流、numba 例外後備）改為獨立 numpy
兩遍法，逐窗對精確 oracle（tests/references/exact_moments.py）≤ 1 float32 ulp。

資料：真實 BTCUSDT/1h（data_cache/feature_klines/kline_cache.h5）close（大均值）與 log return（小均值），窗 [5, 13, 21]
（feature_config.py:451 預設）。I1b 實測（runs/testsel_route/i1b/i1b_facts.md ①）：現行 pandas 臂 close 窗 5 kurt 19,035 窗
不符；兩遍法 0 不符。實作前（rolling_moments_numpy 為空殼）accept／boundary 為紅。
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.operators import numba_rolling
from momentum.FeatureEngineering.operators import rolling_moments_numpy as rmn
from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
from tests.references.exact_moments import exact_rolling_skew_kurt, judge_f32_ulp

REPO = Path(__file__).resolve().parents[2]
WINDOWS = [5, 13, 21]
CONFIG = {"enabled": True, "windows": WINDOWS, "aggregators": ["skew", "kurt"], "apply_to": "all",
          "keep_all_columns": True}

# 非預設臂之四種生效情形（SPEC Task 2.4 驗證）
ARMS = {
    "use_numba_off": {"FFACT_L3_STREAMING": "1", "FFACT_USE_NUMBA_ROLLING": "0"},
    "single_window": {"FFACT_L3_STREAMING": "1", "FFACT_USE_NUMBA_ROLLING": "1", "FFACT_L3_MULTI_WINDOW": "0"},
    "non_streaming": {"FFACT_L3_STREAMING": "0"},
    "numba_exception_fallback": {"FFACT_L3_STREAMING": "1", "FFACT_USE_NUMBA_ROLLING": "1", "FFACT_L3_MULTI_WINDOW": "1"},
}


@pytest.fixture(scope="module")
def real_frame() -> pd.DataFrame:
    from momentum.DataExtraction.kline_storage import KlineStorageManager

    df = KlineStorageManager(cache_dir=str(REPO / "data_cache" / "feature_klines")).read_klines(
        "BTCUSDT", "1h", validate_continuity=False)
    close = df["close"].to_numpy(dtype=np.float64)
    if len(close) < 1000:
        pytest.fail("真實 BTCUSDT/1h K 線不足（資料缺件須補齊，不得 skip）")
    logret = np.concatenate([[np.nan], np.diff(np.log(close))])
    return pd.DataFrame({"close": close, "logret": logret})


@pytest.fixture(scope="module")
def oracle(real_frame: pd.DataFrame) -> Dict[tuple, np.ndarray]:
    return {(col, w): exact_rolling_skew_kurt(real_frame[col].to_numpy(), w) for col in real_frame for w in WINDOWS}


def _boom(*a, **k):
    raise RuntimeError("injected numba failure")


def _run_arm(arm: str, frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch) -> pd.DataFrame:
    for key in ("FFACT_L3_STREAMING", "FFACT_USE_NUMBA_ROLLING", "FFACT_L3_MULTI_WINDOW"):
        monkeypatch.delenv(key, raising=False)
    for key, val in ARMS[arm].items():
        monkeypatch.setenv(key, val)
    if arm == "numba_exception_fallback":
        for name in ("fused_rolling_stats", "fused_rolling_stats_multi_window", "rolling_skew_kurt"):
            monkeypatch.setattr(numba_rolling, name, _boom)
    return RollingAggregator(dict(CONFIG)).compute_all(frame)


def _col(out: pd.DataFrame, base: str, stat: str, w: int) -> np.ndarray:
    hits = [c for c in out.columns if str(c).startswith(base + "_") and str(c).endswith(f"_{stat}-W{w}")]
    assert len(hits) == 1, (base, stat, w, [c for c in out.columns if str(c).startswith(base)][:10])
    return out[hits[0]].to_numpy(dtype=np.float64)


@pytest.mark.parametrize("arm", list(ARMS))
def test_accept_01_non_default_arm_matches_exact_oracle(arm: str, real_frame, oracle, monkeypatch) -> None:
    """四種非預設臂於真實 close／log return × 窗 5／13／21 之 skew、kurt 全部窗對精確 oracle ≤ 1 float32 ulp。"""
    out = _run_arm(arm, real_frame, monkeypatch)
    fails = {}
    for col in real_frame:
        for w in WINDOWS:
            for k, stat in ((0, "Skew"), (1, "Kurt")):
                bad, nfin = judge_f32_ulp(_col(out, col, stat, w), oracle[(col, w)][:, k])
                assert nfin > 0
                if bad:
                    fails[(col, w, stat)] = bad
    assert fails == {}, fails


def test_accept_02_numpy_function_matches_exact_oracle(real_frame, oracle) -> None:
    """`rolling_skew_kurt_numpy` 本身於真實兩序列全部窗對精確 oracle ≤ 1 float32 ulp（I1b 實測 fail＝0）。"""
    for col in real_frame:
        for w in WINDOWS:
            got = rmn.rolling_skew_kurt_numpy(real_frame[col].to_numpy(), w)
            for k in (0, 1):
                bad, _ = judge_f32_ulp(got[:, k], oracle[(col, w)][:, k])
                assert bad == 0, (col, w, k, bad)


@pytest.mark.parametrize("scratch", ["one_window", "odd_block", "default", "single_block"])
def test_boundary_06_block_size_does_not_change_values(scratch: str, real_frame, monkeypatch) -> None:
    """暫存分塊（`_SCRATCH_ELEMS`）只限記憶體、不改值：真實 close／log return（含首列 NaN）× 窗 5／21／233，
    各塊大小之輸出與單一大塊逐位元相同（NaN 位置相同）。窗 233 於預設塊大小下實際分多塊（20k 列 ÷ 4,500 窗／塊）。"""
    for col in real_frame:
        x = real_frame[col].to_numpy()
        for w in (5, 21, 233):
            monkeypatch.setattr(rmn, "_SCRATCH_ELEMS", len(x) * w + 1)
            ref = rmn.rolling_skew_kurt_numpy(x, w)
            elems = {"one_window": w, "odd_block": 7 * w + 3, "default": 1 << 20, "single_block": len(x) * w + 1}[scratch]
            monkeypatch.setattr(rmn, "_SCRATCH_ELEMS", elems)
            got = rmn.rolling_skew_kurt_numpy(x, w)
            assert np.array_equal(got, ref, equal_nan=True), (col, w, scratch)
            assert np.isfinite(got).sum() > 0, (col, w)


def test_boundary_07_scratch_bounded_independent_of_window(real_frame, monkeypatch) -> None:
    """每塊實體暫存之窗數 × 窗長 ≤ `_SCRATCH_ELEMS`（窗長大於上界時每塊 1 窗）：以攔截 `_moments_block` 記錄每塊形狀；
    真實 close，窗 5／233／4,000，各塊窗數加總＝輸出窗數（不漏不重）。"""
    seen = []
    real_block = rmn._moments_block

    def spy(view, w, start, out):
        seen.append((view.shape[0], w))
        return real_block(view, w, start, out)

    monkeypatch.setattr(rmn, "_moments_block", spy)
    x = real_frame["close"].to_numpy()
    for w in (5, 233, 4_000):
        seen.clear()
        rmn.rolling_skew_kurt_numpy(x, w)
        assert len(seen) > 0 and all(b * ww <= max(rmn._SCRATCH_ELEMS, ww) for b, ww in seen), (w, seen[:3])
        assert sum(b for b, _ in seen) == len(x) - w + 1


def test_boundary_01_small_mean_series_arms_agree(real_frame, monkeypatch) -> None:
    """邊界①：小均值欄（log return）numpy 臂與 numba 預設臂每窗差 ≤ 1 float32 ulp。"""
    x = real_frame["logret"].to_numpy()
    for w in WINDOWS:
        a = rmn.rolling_skew_kurt_numpy(x, w)
        b = numba_rolling.rolling_skew_kurt(x, w).astype(np.float64)
        for k in (0, 1):
            bad, _ = judge_f32_ulp(a[:, k], b[:, k])
            assert bad == 0, (w, k, bad)


def test_boundary_02_low_cardinality_exclusion_unchanged(monkeypatch) -> None:
    """邊界②：低基數欄（≤2 個相異值）之 skew／kurt 既有排除不變（非預設臂亦不產該欄）。"""
    rng = np.random.default_rng(0)
    frame = pd.DataFrame({"binary": rng.integers(0, 2, 400).astype(float), "cont": rng.normal(0, 1, 400)})
    cfg = {k: v for k, v in CONFIG.items() if k != "keep_all_columns"}
    for arm in ARMS:
        for key in ("FFACT_L3_STREAMING", "FFACT_USE_NUMBA_ROLLING", "FFACT_L3_MULTI_WINDOW"):
            monkeypatch.delenv(key, raising=False)
        for key, val in ARMS[arm].items():
            monkeypatch.setenv(key, val)
        out = RollingAggregator(dict(cfg)).compute_all(frame)
        assert not any(str(c).startswith("binary_") and ("Skew" in str(c) or "Kurt" in str(c)) for c in out.columns), arm
        assert any(str(c).startswith("cont_") and "Kurt" in str(c) for c in out.columns), arm


def _run_arm_cfg(arm: str, frame: pd.DataFrame, monkeypatch: pytest.MonkeyPatch, windows) -> pd.DataFrame:
    for key in ("FFACT_L3_STREAMING", "FFACT_USE_NUMBA_ROLLING", "FFACT_L3_MULTI_WINDOW"):
        monkeypatch.delenv(key, raising=False)
    for key, val in ARMS[arm].items():
        monkeypatch.setenv(key, val)
    if arm == "numba_exception_fallback":
        for name in ("fused_rolling_stats", "fused_rolling_stats_multi_window", "rolling_skew_kurt"):
            monkeypatch.setattr(numba_rolling, name, _boom)
    cfg = dict(CONFIG, windows=list(windows))
    return RollingAggregator(cfg).compute_all(frame)


@pytest.mark.parametrize("arm", list(ARMS))
def test_boundary_03_window_longer_than_series_all_nan(arm: str, monkeypatch) -> None:
    """邊界③：窗長 > 樣本數 ⇒ 全 NaN——numpy 函式本身與四種非預設聚合器臂皆然（審查 r1 P1-02：邊界須經產品臂）。"""
    out = rmn.rolling_skew_kurt_numpy(np.arange(4, dtype=float), 5)
    assert out.shape == (4, 2) and np.isnan(out).all()
    frame = pd.DataFrame({"x": [1.0, 3.0, 2.0, 5.0]})
    agg = _run_arm_cfg(arm, frame, monkeypatch, [5])
    for stat in ("Skew", "Kurt"):
        hits = [c for c in agg.columns if str(c).endswith(f"_{stat}-W5")]
        assert all(np.isnan(agg[c].to_numpy(dtype=np.float64)).all() for c in hits), (arm, stat)


@pytest.mark.parametrize("arm", list(ARMS))
def test_boundary_04_constant_window_is_nan(arm: str, monkeypatch) -> None:
    """邊界④：常數窗（max＝min）⇒ NaN——函式本身、numba 臂與四種非預設聚合器臂（現行 pandas 臂輸出 skew 0／kurt −3）。"""
    x = np.array([1.0, 3.0, 2.0, 5.0, 4.0, 2.0, 2.0, 2.0, 2.0, 2.0])
    assert np.isnan(rmn.rolling_skew_kurt_numpy(x, 5)[-1]).all()
    assert np.isnan(numba_rolling.rolling_skew_kurt(x, 5)[-1]).all()
    agg = _run_arm_cfg(arm, pd.DataFrame({"x": x}), monkeypatch, [5])
    for stat in ("Skew", "Kurt"):
        v = _col(agg, "x", stat, 5)
        assert np.isnan(v[-1]), (arm, stat, v[-1])


@pytest.mark.parametrize("arm", list(ARMS))
@pytest.mark.parametrize("bad", [np.inf, -np.inf, np.nan])
def test_boundary_05_nonfinite_in_window_is_nan(arm: str, bad: float, monkeypatch) -> None:
    """邊界⑤：窗內含 ±inf 或 NaN ⇒ NaN；離開該值之窗恢復有限——函式本身與四種非預設聚合器臂。"""
    x = np.array([1.0, 2.0, 4.0, 3.0, bad, 2.5, 7.0, 1.5, 6.0, 3.3])
    out = rmn.rolling_skew_kurt_numpy(x, 5)
    assert np.isnan(out[4:9]).all() and np.isfinite(out[9]).all()
    agg = _run_arm_cfg(arm, pd.DataFrame({"x": x}), monkeypatch, [5])
    for stat in ("Skew", "Kurt"):
        v = _col(agg, "x", stat, 5)
        assert np.isnan(v[4:9]).all() and np.isfinite(v[9]), (arm, stat, v)


def test_accept_03_helper_methods_match_exact_oracle(real_frame, oracle) -> None:
    """`RollingAggregator._compute_skew`／`_compute_kurt`（SPEC 列之第四計算點 :950–954）於真實 close 對精確 oracle ≤ 1 float32 ulp。"""
    ra = RollingAggregator(dict(CONFIG))
    s = pd.Series(real_frame["close"].to_numpy())
    for w in WINDOWS:
        for k, fn in ((0, ra._compute_skew), (1, ra._compute_kurt)):
            bad, _ = judge_f32_ulp(np.asarray(fn(s, w), dtype=np.float64), oracle[("close", w)][:, k])
            assert bad == 0, (w, k, bad)


def _pandas_impl(values, window):
    s = pd.Series(values)
    return np.stack([s.rolling(window).skew().to_numpy(), s.rolling(window).kurt().to_numpy()], axis=1)


@pytest.mark.parametrize("arm", list(ARMS))
def test_mutation_m1_pandas_rolling_through_aggregator_arm_fails_oracle(arm: str, real_frame, oracle, monkeypatch) -> None:
    """M1：numpy 函式換回 pandas rolling ⇒ 經各非預設聚合器臂，close 窗 5 kurt 對 oracle 不符（實測 19,035 窗）——
    證聚合器確經模組參照呼叫 `rolling_moments_numpy.rolling_skew_kurt_numpy`（審查 r1 P1-02）。"""
    monkeypatch.setattr(rmn, "rolling_skew_kurt_numpy", _pandas_impl)
    out = _run_arm(arm, real_frame, monkeypatch)
    bad, _ = judge_f32_ulp(_col(out, "close", "Kurt", 5), oracle[("close", 5)][:, 1])
    assert bad > 1000, (arm, bad)


def test_mutation_m1b_helper_method_reverted_to_pandas_fails_oracle(real_frame, oracle, monkeypatch) -> None:
    """M1b：`_compute_kurt` 單獨改回 `series.rolling(window).kurt()` ⇒ 直接驗收之 oracle 判準翻轉。"""
    monkeypatch.setattr(RollingAggregator, "_compute_kurt", lambda self, series, window: series.rolling(window).kurt())
    ra = RollingAggregator(dict(CONFIG))
    got = np.asarray(ra._compute_kurt(pd.Series(real_frame["close"].to_numpy()), 5), dtype=np.float64)
    bad, _ = judge_f32_ulp(got, oracle[("close", 5)][:, 1])
    assert bad > 1000, bad


def test_mutation_m2_fallback_must_not_depend_on_numba(real_frame, monkeypatch) -> None:
    """M2：numpy 函式改呼 numba ⇒ 注入 numba 全公開入口例外時後備臂失敗（證後備不依賴任何 numba 函式）。"""
    monkeypatch.setattr(rmn, "rolling_skew_kurt_numpy",
                        lambda values, window: numba_rolling.rolling_skew_kurt(values, window).astype(np.float64))
    for name in ("fused_rolling_stats", "fused_rolling_stats_multi_window", "rolling_skew_kurt"):
        monkeypatch.setattr(numba_rolling, name, _boom)
    with pytest.raises(RuntimeError, match="injected numba failure"):
        _run_arm("numba_exception_fallback", real_frame.iloc[:300], monkeypatch)
