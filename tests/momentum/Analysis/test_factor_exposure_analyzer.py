"""FactorExposureAnalyzer 單元測試（B1 intercept + B2 fail-closed）。"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.factor_exposure_analyzer import FactorExposureAnalyzer
from momentum.Analysis.ic_config_schema import FactorExposureConfig

# B0 freeze 的 real-OLS oracle（seed=20260721）；B1 逐欄對齊 alpha
_ORACLE_PATH = (
    Path(__file__).resolve().parents[3]
    / "handoffs"
    / "ic1d_baseline"
    / "analyzer_oracle.json"
)

_UNAVAILABLE_KEYS = {"status", "value", "reason"}


def _assert_unavailable(result: dict, reason_substr: str) -> None:
    """unavailable 恰三鍵 + reason 含指定子字串。"""
    assert set(result.keys()) == _UNAVAILABLE_KEYS
    assert result["status"] == "unavailable"
    assert result["value"] is None
    assert reason_substr in str(result["reason"])


def _finite_frame(n: int, n_factors: int = 3, seed: int = 0) -> tuple[pd.Series, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    portfolio = pd.Series(rng.normal(0.0, 0.01, n), name="portfolio")
    factors = pd.DataFrame(
        rng.normal(0.0, 0.01, (n, n_factors)),
        columns=[f"f{i + 1}" for i in range(n_factors)],
    )
    return portfolio, factors


def test_single_asset_mode():
    analyzer = FactorExposureAnalyzer(config={})
    positions = pd.Series({"A": 1.0})
    factor_values = pd.DataFrame({"f1": [0.3], "f2": [0.1]}, index=["A"])
    exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
    assert np.isfinite(exposure["f1"])


def test_hhi_normalization():
    analyzer = FactorExposureAnalyzer(config={"max_single_exposure": 0.4})
    exposures = pd.Series({"f1": 10.0, "f2": 5.0, "f3": 5.0})
    result = analyzer.monitor_exposure_concentration(exposures)
    assert 0 <= result["hhi"] <= 1
    assert result["max_exposure_factor"] == "f1"


def test_unnormalized_weights():
    analyzer = FactorExposureAnalyzer(config={})
    positions = pd.Series({"A": 10.0, "B": 10.0})
    factor_values = pd.DataFrame({"f1": [1.0, 0.0], "f2": [0.0, 1.0]}, index=["A", "B"])
    exposure = analyzer.calculate_portfolio_exposure(positions, factor_values)
    assert np.isclose(float(exposure["f1"]), 0.5)
    assert np.isclose(float(exposure["f2"]), 0.5)


def test_nan_factor_returns_exposure():
    """B2/B4 去固化：含 NaN → unavailable 三鍵 + nan_rows_dropped（禁 factor_betas 殘留）。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series([0.01, 0.02, np.nan, 0.01, -0.01])
    factors = pd.DataFrame(
        {"f1": [0.01, np.nan, 0.02, 0.0, -0.01], "f2": [0.02, 0.01, 0.0, np.nan, -0.02]}
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert set(result.keys()) == _UNAVAILABLE_KEYS
    assert result["status"] == "unavailable"
    assert result["value"] is None
    assert "nan_rows_dropped:" in str(result["reason"])
    assert "factor_betas" not in result


def test_factor_attribution_insufficient_rows():
    """B4 去固化（momentum 對稱 phase25）：樣本不足 → unavailable 三鍵 + insufficient_rows。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series(np.random.default_rng(5).normal(0, 0.01, 5))
    factors = pd.DataFrame(
        np.random.default_rng(6).normal(0, 0.01, (5, 2)), columns=["f1", "f2"]
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert set(result.keys()) == _UNAVAILABLE_KEYS
    assert result["status"] == "unavailable"
    assert result["value"] is None
    assert "insufficient_rows:" in str(result["reason"])
    assert "r_squared" not in result
    assert "factor_betas" not in result


def test_zero_r_squared():
    """RangeIndex + 有限輸入 → status:ok 且 alpha/r_squared 有限。"""
    analyzer = FactorExposureAnalyzer(config={})
    np.random.seed(123)
    portfolio = pd.Series(np.random.randn(120))
    factors = pd.DataFrame(np.random.randn(120, 3), columns=["f1", "f2", "f3"])
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"
    assert np.isfinite(result["alpha"])
    assert np.isfinite(result["r_squared"])


def test_b1_intercept_equals_unexplained_and_alpha():
    """B1：成功路徑 intercept == unexplained == alpha（同 beta[0]）。"""
    analyzer = FactorExposureAnalyzer(config={})
    rng = np.random.default_rng(20260721)
    n = 120
    portfolio = pd.Series(rng.normal(0.0, 0.01, n), name="portfolio")
    factors = pd.DataFrame(
        rng.normal(0.0, 0.01, (n, 3)),
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)

    assert result["status"] == "ok"
    assert "intercept" in result
    assert result["intercept"] == result["unexplained"] == result["alpha"]
    assert np.isfinite(result["intercept"])

    # 與 B0 analyzer_oracle.json 基準值逐欄相等（alpha 同源）
    assert _ORACLE_PATH.is_file(), f"missing oracle: {_ORACLE_PATH}"
    oracle = json.loads(_ORACLE_PATH.read_text(encoding="utf-8"))
    assert float(result["alpha"]) == pytest.approx(float(oracle["alpha"]), abs=0.0, rel=0.0)
    assert float(result["intercept"]) == pytest.approx(float(oracle["alpha"]), abs=0.0, rel=0.0)
    assert float(result["unexplained"]) == pytest.approx(
        float(oracle["unexplained"]), abs=0.0, rel=0.0
    )
    assert float(result["r_squared"]) == pytest.approx(
        float(oracle["r_squared"]), abs=0.0, rel=0.0
    )


def test_b1_unavailable_branch_has_no_intercept():
    """B2：樣本不足 → 恰三鍵 unavailable，不得出現 intercept/數值欄。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series([0.01, 0.02, -0.01])
    factors = pd.DataFrame({"f1": [0.01, 0.0, -0.01], "f2": [0.02, 0.01, 0.0]})
    result = analyzer.calculate_factor_attribution(portfolio, factors)

    assert "intercept" not in result
    assert set(result.keys()) == _UNAVAILABLE_KEYS
    assert result["status"] == "unavailable"
    assert result["value"] is None
    assert "insufficient_rows:" in result["reason"]


# ---------------------------------------------------------------------------
# B2 Task 2.1 / 2.2 驗收（單元級；禁 deep JSON）
# ---------------------------------------------------------------------------


def test_b2_nan_rows_dropped_1_of_40():
    """40 列含 1 NaN → nan_rows_dropped:1/40。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=1)
    portfolio.iloc[5] = np.nan
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "nan_rows_dropped:1/40")


def test_b2_inf_non_finite_values_no_linalg_error():
    """40 列含 1 inf → non_finite_values；不得 raise LinAlgError。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=2)
    factors.iloc[3, 0] = np.inf
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_values:")


def test_b2_output_overflow_1e200():
    """portfolio 含 1e200（輸入全有限）→ non_finite_output。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=3)
    portfolio.iloc[0] = 1e200
    # 確認輸入端無 inf（1e200 有限）
    assert np.isfinite(portfolio.to_numpy(dtype=float)).all()
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_output:")


def test_b2_range_index_pass():
    """RangeIndex 須 PASS → status:ok。"""
    analyzer = FactorExposureAnalyzer(config={})
    rng = np.random.default_rng(42)
    portfolio = pd.Series(rng.standard_normal(120))
    factors = pd.DataFrame(rng.standard_normal((120, 3)), columns=["f1", "f2", "f3"])
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"
    assert np.isfinite(result["alpha"])


def test_b2_misaligned_index_nan_rows_dropped_200_220():
    """錯位索引 range(100,220) vs range(0,120) → nan_rows_dropped:200/220。"""
    analyzer = FactorExposureAnalyzer(config={})
    rng = np.random.default_rng(7)
    portfolio = pd.Series(rng.normal(0, 0.01, 120), index=range(100, 220))
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (120, 3)),
        index=range(0, 120),
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "nan_rows_dropped:200/220")


def test_b2_insufficient_rows_9():
    """9 列 → insufficient_rows:9。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(9, n_factors=3, seed=8)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "insufficient_rows:9")


def test_b2_exactly_10_rows_ok():
    """10 列（預設門檻）→ status:ok。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(10, n_factors=3, seed=9)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"
    assert "value" not in result  # ok 形無 value 鍵（扁平）


def test_b2_attribution_min_rows_override_wiring():
    """config attribution_min_rows=11 → 10 列變 unavailable（證 wiring）。"""
    analyzer = FactorExposureAnalyzer(config={"attribution_min_rows": 11})
    portfolio, factors = _finite_frame(10, n_factors=3, seed=10)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "insufficient_rows:10<11")


def test_b2_schema_default_attribution_min_rows():
    """schema 預設 10 且 ge=2；model_dump 可餵進 analyzer。"""
    cfg = FactorExposureConfig()
    assert cfg.attribution_min_rows == 10
    dumped = cfg.model_dump()
    assert dumped["attribution_min_rows"] == 10
    analyzer = FactorExposureAnalyzer(config=dumped)
    assert analyzer._attribution_min_rows == 10
    with pytest.raises(Exception):
        FactorExposureConfig(attribution_min_rows=1)


def test_b2_single_factor_insufficient_factors():
    """單因子 → insufficient_factors:1<2。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, _ = _finite_frame(40, n_factors=1, seed=11)
    factors = pd.DataFrame({"f1": np.random.default_rng(11).normal(0, 0.01, 40)})
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "insufficient_factors:1<2")


def test_b2_cm8_priority_nan_over_insufficient_rows():
    """12 列含 3 NaN（dropna 後 9<10）→ nan_rows_dropped:3/12（非 insufficient_rows）。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(12, n_factors=3, seed=12)
    portfolio.iloc[0] = np.nan
    portfolio.iloc[1] = np.nan
    factors.iloc[2, 0] = np.nan
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "nan_rows_dropped:3/12")
    assert "insufficient_rows" not in result["reason"]


def test_b2_cm8_priority_inf_over_nan():
    """同時有 inf 與 NaN → non_finite_values 優先。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=13)
    portfolio.iloc[0] = np.nan
    factors.iloc[1, 0] = np.inf
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_values:")
    assert "nan_rows_dropped" not in result["reason"]


def test_b2_cm8_inf_over_index_tz_mismatch():
    """③ CM8：naive+aware tz + 1 inf → non_finite_values（非 index_tz_mismatch）。"""
    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(25)
    portfolio = pd.Series(
        rng.normal(0, 0.01, n),
        index=pd.date_range("2020-01-01", periods=n, freq="D"),  # naive
    )
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC"),  # aware
        columns=["f1", "f2", "f3"],
    )
    factors.iloc[0, 0] = np.inf
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_values:")
    assert "index_tz_mismatch" not in result["reason"]
    # 1 inf in factors (n*3) + 0 in portfolio (n) → 1/(n + n*3)
    assert result["reason"] == f"non_finite_values:1/{n + n * 3}"


def test_b2_cm8_pure_tz_still_index_tz_mismatch():
    """③：純 tz 不符、無 inf → 仍 index_tz_mismatch。"""
    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(26)
    portfolio = pd.Series(
        rng.normal(0, 0.01, n),
        index=pd.date_range("2020-01-01", periods=n, freq="D"),
    )
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC"),
        columns=["f1", "f2", "f3"],
    )
    assert np.isfinite(portfolio.to_numpy(dtype=float)).all()
    assert np.isfinite(factors.to_numpy(dtype=float)).all()
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "index_tz_mismatch")


def test_b2_output_non_finite_attribution_kills_mutation():
    """⑤：alpha/r_squared 可有限但 attribution 元素非有限 → non_finite_output:attribution。

    構造：某因子常數 1e308（輸入 isfinite=True，mean 溢位為 inf）→
    attribution = beta * mean 非有限。刪 attribution 檢查後本測應 FAIL。
    """
    analyzer = FactorExposureAnalyzer(config={})
    n = 40
    rng = np.random.default_rng(99)
    portfolio = pd.Series(rng.normal(0.0, 0.01, n))
    factors = pd.DataFrame(
        {
            "f1": np.full(n, 1e308),
            "f2": rng.normal(0.0, 0.01, n),
            "f3": rng.normal(0.0, 0.01, n),
        }
    )
    # 輸入端全有限（溢位發生在 mean/attribution，非輸入 inf）
    assert np.isfinite(portfolio.to_numpy(dtype=float)).all()
    assert np.isfinite(factors.to_numpy(dtype=float)).all()
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_output:attribution")


def test_b2_output_non_finite_scalar_field_kills_mutation():
    """⑤ residual：直接單元測 `_first_non_finite_output_field` 對每個純量欄的覆蓋。

    alpha/r_squared 非有限的自然輸入極難構造（多在 lstsq 前已被輸入 gate 攔），
    故直接測 helper：刪其檢查 tuple 任一欄 → 對應斷言 FAIL（可證偽）。
    """
    from momentum.Analysis.factor_exposure_analyzer import _first_non_finite_output_field

    base = {"alpha": 1.0, "r_squared": 0.5, "factor_betas": {"f1": 0.1}, "attribution": {"f1": 0.2}}
    # alpha 非有限 → 命中 alpha（刪 helper 的 alpha 檢查則此 assert 紅）
    assert _first_non_finite_output_field({**base, "alpha": np.inf}) == "alpha"
    # r_squared 非有限 → 命中 r_squared
    assert _first_non_finite_output_field({**base, "r_squared": np.nan}) == "r_squared"


def test_b2_output_non_finite_factor_betas_kills_mutation():
    """⑤ residual：factor_betas 某元素非有限 → 命中 factor_betas.<name>（刪 helper 的 factor_betas 檢查則紅）。"""
    from momentum.Analysis.factor_exposure_analyzer import _first_non_finite_output_field

    base = {"alpha": 1.0, "r_squared": 0.5, "factor_betas": {"f1": 0.1}, "attribution": {"f1": 0.2}}
    assert _first_non_finite_output_field({**base, "factor_betas": {"f1": np.inf}}) == "factor_betas.f1"


# --- 邊界 12 ---


def test_b2_boundary_all_nan():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series([np.nan] * 20)
    factors = pd.DataFrame({"f1": [np.nan] * 20, "f2": [np.nan] * 20, "f3": [np.nan] * 20})
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "unavailable"
    assert "nan_rows_dropped:" in result["reason"]


def test_b2_boundary_all_inf():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio = pd.Series([np.inf] * 20)
    factors = pd.DataFrame({"f1": [np.inf] * 20, "f2": [1.0] * 20, "f3": [1.0] * 20})
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_values:")


def test_b2_boundary_nan_and_inf_mix():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(20, seed=14)
    portfolio.iloc[0] = np.nan
    factors.iloc[1, 1] = -np.inf
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_values:")


def test_b2_boundary_single_row():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(1, seed=15)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "insufficient_rows:1")


def test_b2_boundary_duplicate_index():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(20, seed=16)
    dup_idx = pd.Index([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 0])
    portfolio.index = dup_idx
    factors.index = dup_idx
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "unavailable"
    assert result["reason"] in ("index_not_unique",) or "index" in result["reason"]


def test_b2_boundary_unsorted_index():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(20, seed=17)
    shuffled = list(range(19, -1, -1))
    portfolio.index = shuffled
    factors.index = shuffled
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "unavailable"
    assert "index" in result["reason"]


def test_b2_boundary_tz_naive_aware_mix():
    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(18)
    portfolio = pd.Series(
        rng.normal(0, 0.01, n),
        index=pd.date_range("2020-01-01", periods=n, freq="D"),
    )
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC"),
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "index_tz_mismatch")


def test_b2_boundary_aware_different_tz():
    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(19)
    portfolio = pd.Series(
        rng.normal(0, 0.01, n),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC"),
    )
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="US/Eastern"),
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "index_tz_mismatch")


def test_b2_boundary_range_index_pass_explicit():
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(120, seed=20)
    assert isinstance(portfolio.index, pd.RangeIndex)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"


def test_b2_boundary_object_mixed_index_fail():
    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(21)
    obj_idx = pd.Index([f"t{i}" for i in range(n)], dtype=object)
    portfolio = pd.Series(rng.normal(0, 0.01, n), index=obj_idx)
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=obj_idx,
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "index_type_uncomparable")


def test_b2_boundary_gapped_datetime_pass():
    """有間隙但 unique+monotonic → PASS（不驗 freq）。"""
    analyzer = FactorExposureAnalyzer(config={})
    n = 30
    rng = np.random.default_rng(22)
    # 連續日曆中刻意挖洞（freq=None 屬正常）
    base = pd.date_range("2020-01-01", periods=40, freq="D")
    days = base.delete([5, 6, 7, 15, 16, 20, 21, 22, 30, 31])  # 10 gaps → 30 bars
    assert len(days) == n
    assert days.freq is None or True  # 允許 freq=None
    portfolio = pd.Series(rng.normal(0, 0.01, n), index=days)
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=days,
        columns=["f1", "f2", "f3"],
    )
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"


def test_b2_boundary_input_finite_output_overflow():
    """輸入有限但輸出溢位（1e200）→ non_finite_output。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, seed=23)
    portfolio.iloc[2] = 1e200
    assert np.isfinite(float(portfolio.iloc[2]))
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(result, "non_finite_output:")


def test_b2_success_envelope_has_status_ok_and_no_value():
    """成功路徑現有 status:ok，扁平數值欄，無 value 鍵。"""
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(50, seed=24)
    result = analyzer.calculate_factor_attribution(portfolio, factors)
    assert result["status"] == "ok"
    assert "value" not in result
    for key in ("alpha", "r_squared", "intercept", "unexplained", "factor_betas", "attribution"):
        assert key in result


# ---------------------------------------------------------------------------
# B4 mutation 探針（test_mutation_*；基線綠 → 改壞 production 邏輯 → 斷言紅自證）
# ---------------------------------------------------------------------------


def test_mutation_dropna_restored_must_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-8：patch DataFrame.dropna→no-op（最窄 seam）→ nan_rows_dropped 斷言必紅。

    範式同 index/output：只壞 production 具名依賴，不替換整 method。
    40 列僅 1 NaN：no-op 後 dropped=0 穿過閘門，NaN 進 OLS → 行為偏離。
    """
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=101)
    portfolio.iloc[5] = np.nan

    # 基線綠
    baseline = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(baseline, "nan_rows_dropped:1/40")
    assert "factor_betas" not in baseline

    # mutation：最窄 seam — dropna 變成 no-op，列數不變 → dropped 閘門失效
    monkeypatch.setattr(
        pd.DataFrame, "dropna", lambda self, *a, **k: self  # noqa: ARG005
    )
    mutated = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
        portfolio, factors
    )
    with pytest.raises(AssertionError):
        _assert_unavailable(mutated, "nan_rows_dropped:")
    assert "nan_rows_dropped" not in str(mutated.get("reason", ""))


def test_mutation_insufficient_silent_nan_must_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-7：patch `_attribution_min_rows`→0（最窄 insufficient seam）→ 斷言必紅。

    9 列本應 insufficient_rows；門檻歸零後穿過該 branch → 不再 unavailable。
    """
    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(9, n_factors=3, seed=102)

    baseline = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(baseline, "insufficient_rows:9")
    assert "factor_betas" not in baseline

    # mutation：最窄 seam — 只把 min_rows 設 0，其餘 production 路徑不動
    monkeypatch.setattr(analyzer, "_attribution_min_rows", 0)
    mutated = analyzer.calculate_factor_attribution(portfolio, factors)
    with pytest.raises(AssertionError):
        _assert_unavailable(mutated, "insufficient_rows:")
    assert mutated.get("status") == "ok"
    assert "factor_betas" in mutated


def test_mutation_inf_passthrough_must_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """D-10：patch np.isinf→全 False（最窄 inf seam）→ non_finite_values 斷言必紅。

    真 mutation 可能 LinAlgError（inf 進 lstsq）；兩者皆證閘門被繞過。
    """
    from momentum.Analysis import factor_exposure_analyzer as fea_mod

    analyzer = FactorExposureAnalyzer(config={})
    portfolio, factors = _finite_frame(40, n_factors=3, seed=103)
    factors.iloc[3, 0] = np.inf

    baseline = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(baseline, "non_finite_values:")

    # mutation：最窄 seam — 只讓 isinf 永遠看不到 inf（不動 method / 不 coerce）
    def _never_inf(x: object, *a: object, **k: object) -> np.ndarray:  # noqa: ARG001
        return np.zeros(np.shape(x), dtype=bool)

    monkeypatch.setattr(fea_mod.np, "isinf", _never_inf)
    with pytest.raises((AssertionError, np.linalg.LinAlgError)):
        mutated = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
            portfolio, factors
        )
        _assert_unavailable(mutated, "non_finite_values:")
        assert "non_finite_values" not in str(mutated.get("reason", ""))


def test_mutation_output_overflow_passthrough_must_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-13：拿掉 output 非有限檢查 → 基線 non_finite_output 斷言必須紅。

    涵蓋 alpha/r_squared/factor_betas/attribution（helper 全欄）。
    """
    from momentum.Analysis import factor_exposure_analyzer as fea_mod

    analyzer = FactorExposureAnalyzer(config={})
    n = 40
    rng = np.random.default_rng(104)
    portfolio = pd.Series(rng.normal(0.0, 0.01, n))
    factors = pd.DataFrame(
        {
            "f1": np.full(n, 1e308),
            "f2": rng.normal(0.0, 0.01, n),
            "f3": rng.normal(0.0, 0.01, n),
        }
    )
    assert np.isfinite(portfolio.to_numpy(dtype=float)).all()
    assert np.isfinite(factors.to_numpy(dtype=float)).all()

    baseline = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(baseline, "non_finite_output:attribution")

    monkeypatch.setattr(fea_mod, "_first_non_finite_output_field", lambda _r: None)
    mutated = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
        portfolio, factors
    )
    with pytest.raises(AssertionError):
        _assert_unavailable(mutated, "non_finite_output:")
    # mutation 放行後應吐出含 attribution 的 ok（或至少非 unavailable:non_finite_output）
    assert mutated.get("status") == "ok" or "attribution" in mutated


def test_mutation_index_policy_bypassed_must_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D-5：拿掉 index 政策檢查 → 基線 index_tz_mismatch 斷言必須紅。"""
    from momentum.Analysis import factor_exposure_analyzer as fea_mod

    analyzer = FactorExposureAnalyzer(config={})
    n = 20
    rng = np.random.default_rng(105)
    portfolio = pd.Series(
        rng.normal(0, 0.01, n),
        index=pd.date_range("2020-01-01", periods=n, freq="D"),
    )
    factors = pd.DataFrame(
        rng.normal(0, 0.01, (n, 3)),
        index=pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC"),
        columns=["f1", "f2", "f3"],
    )

    baseline = analyzer.calculate_factor_attribution(portfolio, factors)
    _assert_unavailable(baseline, "index_tz_mismatch")

    monkeypatch.setattr(fea_mod, "_index_policy_reason", lambda *_a, **_k: None)
    mutated = FactorExposureAnalyzer(config={}).calculate_factor_attribution(
        portfolio, factors
    )
    with pytest.raises(AssertionError):
        _assert_unavailable(mutated, "index_tz_mismatch")
