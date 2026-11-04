"""ICPERF Task 0.4 ㊺ B：趨勢推論核心之精確 oracle 測試（SPEC v5.78 ㊺ 列驗證 B①–④ 之純函式部分）。

oracle 皆獨立於產品實作：密集式 Bartlett 二次型、由殘差投影矩陣直接形成之 B 與其特徵分解、F(1,1)／χ² 閉式、
固定種子蒙地卡羅。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats

from momentum.Analysis import trend_inference as ti


def _dense_bartlett_var(x: np.ndarray, y: np.ndarray) -> float:
    """獨立 oracle：Var(β̂)＝m·Ω̂／S_xx²，Ω̂＝(1/m)Σ_tΣ_u(1−|t−u|/m)s_t s_u。"""
    m = x.size
    X = np.column_stack([np.ones(m), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ beta
    xc = x - x.mean()
    s = xc * e
    t = np.arange(m)
    K = 1.0 - np.abs(t[:, None] - t[None, :]) / m
    omega = (s @ K @ s) / m
    return m * omega / (xc @ xc) ** 2


def _dense_B(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """獨立 oracle：由殘差投影 M 直接形成 a 與 B（SE²＝y'By）。"""
    m = x.size
    xc = x - x.mean()
    sxx = xc @ xc
    a = xc / sxx
    X = np.column_stack([np.ones(m), x])
    M = np.eye(m) - X @ np.linalg.pinv(X)
    L = np.tril(np.ones((m, m)))
    P = np.diag(np.r_[np.ones(m - 1), 0.0])
    G = P @ L @ np.diag(xc) @ M
    B = m * (2.0 / m**2) * (G.T @ G) / sxx**2
    return a, B


# ── B① 貪婪選取 ──────────────────────────────────────────────────────────────


def test_select_nonoverlapping_hand_cases() -> None:
    # 滾動 IC：窗 3、h＝2、步長 1、標籤有限列軸中斷（原列 0..4 有限、6..9 有限，5 為標籤缺）
    axis = np.array([0, 1, 2, 3, 4, 6, 7, 8, 9])
    w, h = 3, 2
    starts = axis[: len(axis) - w + 1]
    ends = axis[w - 1:] + h - 1
    idx = ti.select_nonoverlapping(starts, ends)
    # 值 0：[0,3]；下一值須起點>3 ⇒ 值 3（起 3）不可、值 4（起 4）可：[4,8]；下一須起>8 ⇒ 無（值 6 起 8）
    assert idx.tolist() == [0, 4]
    # 步長 s＝2 之窗終點序列
    s_starts = np.array([0, 2, 4, 6, 8])
    s_ends = s_starts + 3 + 2 - 2
    assert ti.select_nonoverlapping(s_starts, s_ends).tolist() == [0, 2, 4]
    # ls_spread：每值支撐 [t, t+h−1]、h＝3
    t_pos = np.arange(10)
    assert ti.select_nonoverlapping(t_pos, t_pos + 2).tolist() == [0, 3, 6, 9]
    # factor_return：已每 h 取一 ⇒ 全選
    fr = np.array([0, 3, 6, 9])
    assert ti.select_nonoverlapping(fr, fr + 2).tolist() == [0, 1, 2, 3]
    # 中心性二層窗：W＝2 個滾動 IC 列（窗 3、h＝1、步長 1）⇒ 支撐 (W−1)s＋w＋h−1＝5 根
    c_start = np.arange(6)
    c_end = c_start + 4
    assert ti.select_nonoverlapping(c_start, c_end).tolist() == [0, 5]
    with pytest.raises(ValueError):
        ti.select_nonoverlapping(np.array([2]), np.array([1]))


# ── B② Bartlett b＝1 ────────────────────────────────────────────────────────


@pytest.mark.parametrize("m", [3, 5, 23, 101])
def test_bartlett_cumsum_equals_dense_oracle(m: int) -> None:
    rng = np.random.default_rng(m)
    x = np.cumsum(rng.integers(1, 4, size=m)).astype(float)
    y = rng.standard_normal(m) + 0.01 * x
    fit = ti.bartlett_fixedb_slope(x, y)
    var_dense = _dense_bartlett_var(x, y)
    assert fit.se**2 == pytest.approx(var_dense, rel=1e-12)
    assert fit.slope == pytest.approx(stats.linregress(x, y).slope, rel=1e-12)


def test_bartlett_t_affine_invariant_in_x() -> None:
    rng = np.random.default_rng(1)
    x = np.array([0, 3, 6, 12, 15, 21, 24, 30, 33, 39], float)
    y = rng.standard_normal(10)
    t0 = ti.bartlett_fixedb_slope(x, y).t_stat
    assert ti.bartlett_fixedb_slope(7 * x + 123, y).t_stat == pytest.approx(t0, rel=1e-12)
    assert ti.bartlett_fixedb_slope((x - x[0]) / 3, y).t_stat == pytest.approx(t0, rel=1e-12)


# ── B③ 解析譜與精確 p ────────────────────────────────────────────────────────


@pytest.mark.parametrize("m", [3, 23, 95])
def test_design_spectrum_matches_dense_B(m: int) -> None:
    x = np.cumsum(np.r_[0, np.random.default_rng(m).integers(1, 3, size=m - 1)]).astype(float)
    a, B = _dense_B(x)
    assert np.linalg.norm(B @ a) <= 1e-12 * np.linalg.norm(B) * np.linalg.norm(a)
    lam_pos, mu = ti.design_spectrum(x)
    assert lam_pos == pytest.approx(a @ a, rel=1e-12)
    eig = np.sort(np.linalg.eigvalsh((B + B.T) / 2))
    eig = eig[eig > 1e-12 * eig.max()]
    assert np.sort(mu) == pytest.approx(eig, rel=1e-10)


@pytest.mark.parametrize("k", [1e-3, 1.0, 1e10, 1e12])
def test_imhof_two_root_matches_f11_closed_form(k: float) -> None:
    p, eps = ti.imhof_upper_tail(1.0, np.array([k]))
    closed = stats.f.sf(k, 1, 1)
    assert p == pytest.approx(closed, rel=1e-6)
    assert abs(p - closed) <= eps


@pytest.mark.parametrize("r", [2, 5, 40])
@pytest.mark.parametrize("k", [1e-2, 1.0, 1e6])
def test_imhof_equal_negative_roots_match_f_closed_form(r: int, k: float) -> None:
    # 等負根：P(χ²₁ ≥ k·χ²_r)＝F(1,r).sf(k·r)（本結構唯一正根，故「全部特徵值相等」之 χ² 情形不可達，以等負根之 F 閉式代之）
    p, eps = ti.imhof_upper_tail(1.0, np.full(r, k))
    closed = stats.f.sf(k * r, 1, r)
    assert p == pytest.approx(closed, rel=1e-6, abs=eps)


def test_overflowing_t_is_unreliable_not_exception() -> None:
    pv = ti.slope_pvalue(np.arange(10, dtype=float), 1e200)
    assert not pv.reliable


@pytest.mark.parametrize("x", [np.array([0.0, 1.0, 2.0]), np.array([0.0, 14.0, 28.0])])
@pytest.mark.parametrize("t", [1.0, 1e3, 1e6, 1e9])
def test_m3_slope_pvalue_matches_closed_form(x: np.ndarray, t: float) -> None:
    # m＝3：λ₊＝1/S_xx、單一負根；P(|t|≥c)＝F(1,1).sf(c²/9)（codex r102／r103 反例）
    pv = ti.slope_pvalue(x, t)
    closed = stats.f.sf(t * t / 9.0, 1, 1)
    assert pv.reliable
    assert pv.p == pytest.approx(closed, rel=1e-6)


def test_zero_t_gives_p_one() -> None:
    pv = ti.slope_pvalue(np.arange(23, dtype=float), 0.0)
    assert pv.p == 1.0 and pv.reliable


@pytest.mark.parametrize("m", [23, 95])
def test_slope_pvalue_matches_monte_carlo(m: int) -> None:
    rng = np.random.default_rng(20261105 + m)
    x = np.arange(m, dtype=float)
    a, B = _dense_B(x)
    R = 200_000
    Y = rng.standard_normal((R, m))
    tsim = np.abs((Y @ a) / np.sqrt(np.einsum("ij,jk,ik->i", Y, B, Y)))
    for t in (3.0, 6.0):
        pv = ti.slope_pvalue(x, t)
        mc = float(np.mean(tsim >= t))
        se = np.sqrt(mc * (1 - mc) / R)
        assert abs(pv.p - mc) <= 3 * se


def test_large_t_nonnegative_and_reliable() -> None:
    for m in (23, 95, 238):
        pv = ti.slope_pvalue(np.arange(m, dtype=float), 1e3)
        assert pv.reliable
        assert 0.0 <= pv.p <= pv.abs_error + 1e-300


def test_nonfinite_t_is_unreliable() -> None:
    assert not ti.slope_pvalue(np.arange(10, dtype=float), float("nan")).reliable


# ── B④ 分類與封閉狀態決策表 ──────────────────────────────────────────────────


def test_infer_trend_decision_table() -> None:
    x = np.arange(30, dtype=float)
    assert ti.infer_trend(x[:2], np.array([1.0, 2.0]), 0.05).status == ti.STATUS_INSUFFICIENT_POINTS
    assert ti.infer_trend(x, np.full(30, 3.0), 0.05).status == ti.STATUS_CONSTANT_SERIES
    assert ti.infer_trend(x, 2.0 * x + 1.0, 0.05).status == ti.STATUS_DEGENERATE
    y_nan = np.r_[np.full(28, np.nan), 1.0, 2.0]
    assert ti.infer_trend(x, y_nan, 0.05).status == ti.STATUS_INSUFFICIENT_POINTS

    rng = np.random.default_rng(3)
    y = rng.standard_normal(30) + 0.5 * x
    sig = ti.infer_trend(x, y, 0.05)
    assert sig.status == ti.STATUS_OK and sig.significant is True and sig.slope > 0
    y0 = rng.standard_normal(30)
    res = ti.infer_trend(x, y0, 0.05)
    assert res.status in {ti.STATUS_OK}
    # 區間跨 α ⇒ p_numeric_unreliable：以 α＝p 本身
    edge = ti.infer_trend(x, y0, res.p_value)
    assert edge.status == ti.STATUS_P_NUMERIC_UNRELIABLE
    assert ti.STATUS_P_NUMERIC_UNRELIABLE in ti.INFERENCE_STATUS_VALUES


# ── 資料不足警示（SPEC ㊺ B：沿用 ㊹ 判準工具，生成器＝同一設計上之 AR(1)(φ̂_e)，對照 REFERENCE_RHO） ──


def _design(m: int, seed: int = 3) -> np.ndarray:
    return np.cumsum(np.random.default_rng(seed).integers(20, 25, size=m)).astype(float)


@pytest.mark.parametrize("m", [7, 23, 120])
def test_critical_t2_inverts_exact_p(m: int) -> None:
    """c²_α 處之精確 p＝α（slope_pvalue 為獨立路徑：含奇異值擾動之誤差界）；c² 兩側 p 跨 α。"""
    x = _design(m)
    c2 = ti.critical_t2(x, 0.05)
    assert ti.slope_pvalue(x, float(np.sqrt(c2))).p == pytest.approx(0.05, abs=1e-10)
    assert ti.slope_pvalue(x, float(np.sqrt(c2 * 0.98))).p > 0.05 > ti.slope_pvalue(x, float(np.sqrt(c2 * 1.02))).p


@pytest.mark.parametrize("alpha", [0.2, 0.05, 1e-4, 1e-9, 1e-12])
def test_critical_t2_m3_matches_f_closed_form_without_cap(alpha: float) -> None:
    """r106 CODEX-P1-02：m＝3 設計只有一個負根 ⇒ P(t² ≥ c²)＝P(F(1,1) ≥ c²·μ／λ₊)，c²_α＝F.isf(α,1,1)·λ₊／μ
    （scipy.stats.f 閉式）；schema 允許之小 α（臨界值逾 1e12）亦須有限（無字面搜尋上限），且臨界值處之閉式尾機率與 α
    之差 ≤ 該點 Imhof 絕對誤差界（p 之數值解析度；α 越小相對誤差越大，屬解析度而非上限）＋1e-15；α ≥ 1e-4 另驗 c² 相對
    誤差 ≤ 1e-8。"""
    x = np.array([0.0, 1.0, 2.0])
    lam_pos, mu = ti.design_spectrum(x)
    assert mu.size == 1
    exact = float(stats.f.isf(alpha, 1, 1)) * lam_pos / float(mu[0])
    got = ti.critical_t2(x, alpha)
    assert np.isfinite(got) and got > 1e12 if alpha <= 1e-9 else np.isfinite(got)
    _, eps = ti.imhof_upper_tail(lam_pos, got * mu)
    assert abs(float(stats.f.sf(got * float(mu[0]) / lam_pos, 1, 1)) - alpha) <= eps + 1e-15, (alpha, got, exact)
    if alpha >= 1e-4:
        assert got == pytest.approx(exact, rel=1e-8)


def test_fixedb_t2_rows_equals_scalar_path() -> None:
    """向量化 t² 逐列等於 :func:`bartlett_fixedb_slope` 之 t²；常數列（SE＝0）為 NaN。"""
    x = _design(40)
    y = np.random.default_rng(5).standard_normal((30, 40))
    y[3] = 1.0
    got = ti.fixedb_t2_rows(x, y)
    for i in range(30):
        t = ti.bartlett_fixedb_slope(x, y[i]).t_stat
        if np.isfinite(t):
            assert got[i] == pytest.approx(t * t, rel=1e-12)
        else:
            assert np.isnan(got[i])


def test_reject_rows_match_per_row_exact_p() -> None:
    """拒絕指示（t² ≥ c²_α）逐列等於獨立路徑「單列 Imhof p ≤ α」（避開 |p−α| ≤ 1e-9 之邊界列）。"""
    from momentum.Analysis import hac_ewc as he

    x = _design(23)
    c2 = ti.critical_t2(x, 0.05)
    rej = ti._reject_rows(x, 0.5, c2)
    seed = he.simulation_seed(1, ti.WARNING_METHOD_KEY)
    y = he._ar1_rows(he._feature_innovations(seed, 0, 60, 23), 0.5)
    for i in range(60):
        p = ti.slope_pvalue(x, ti.bartlett_fixedb_slope(x, y[i]).t_stat).p
        if abs(p - 0.05) > 1e-9:
            assert rej[i] == float(p <= 0.05), i


def test_null_reject_rate_near_alpha_under_iid() -> None:
    """φ＝0（y iid 常態）時 R＝1,000 條之拒絕率落於 Binomial(1000, 0.05) 之 99.9% 雙尾區間（精確臨界值之自洽）。"""
    lo, hi = stats.binom.ppf([0.0005, 0.9995], 1000, 0.05) / 1000
    for m in (7, 23, 120):
        x = _design(m)
        rate = float(ti._reject_rows(x, 0.0, ti.critical_t2(x, 0.05)).mean())
        assert lo <= rate <= hi, (m, rate)


def test_design_median_function_monotone_and_inverts() -> None:
    """同設計中位數函數於 PHI_GRID 弱遞增；左廣義逆於嚴格遞增處之網格點回原 φ（中位數不偏）。"""
    from momentum.Analysis import hac_ewc as he

    x = _design(120)
    med = ti._design_median_function(x)
    assert med.shape == (len(he.PHI_GRID),) and np.all(np.diff(med) >= 0.0)
    k = he.PHI_GRID.index(0.5)
    assert med[k - 1] < med[k]
    assert he._left_inverse(med, float(med[k])) == pytest.approx(0.5, abs=1e-12)


def test_trend_data_warning_cases_and_closed_keys() -> None:
    """iid 不警示；近單根（AR 0.99）警示且 detail 為 ㊹ 封閉八鍵（horizon＝1）；殘差全 0（滯後段常數）⇒
    persistence_not_estimable；清快取後重算結果相同（快取不改值）。"""
    from momentum.Analysis import hac_ewc as he

    x = _design(60)
    rng = np.random.default_rng(11)
    assert ti.trend_data_warning(x, rng.standard_normal(60), 0.05) == {"data_warning": None,
                                                                       "data_warning_detail": None}
    y = he._ar1_rows(rng.standard_normal((1, 60)), 0.99)[0]
    w = ti.trend_data_warning(x, y, 0.05)
    assert w["data_warning"] == "small_effective_sample"
    d = w["data_warning_detail"]
    assert set(d) == {"n_obs", "horizon", "approx_independent_n", "phi_hat", "alpha", "estimated_null_reject_rate",
                      "reference_reject_rate", "replications"}
    assert d["n_obs"] == 60 and d["horizon"] == 1 and d["replications"] == he.WARNING_SIM_REPLICATIONS
    assert d["estimated_null_reject_rate"] > d["reference_reject_rate"]
    ti._DESIGN_CACHE.clear()
    assert ti.trend_data_warning(x, y, 0.05) == w
    xl = np.arange(5, dtype=float)
    assert ti.trend_data_warning(xl, 2.0 * xl, 0.05)["data_warning"] == "persistence_not_estimable"


@pytest.mark.parametrize("x", [np.array([0.0, 66.0, 132.0]), np.array([0.0, 5.0, 300.0])])
def test_trend_data_warning_three_points_not_identifiable(x: np.ndarray) -> None:
    """選取 3 點（等距與不等距）：殘差只 1 自由度、ρ̂ 與 φ 無關 ⇒ 同設計中位數函數為常數 ⇒ persistence_not_estimable
    （不得因捨入噪音給出 small_effective_sample；r106 收據 L.deep_analysis 實例）；4 點起中位數函數非常數。"""
    assert np.ptp(ti._design_median_function(x)) == pytest.approx(0.0, abs=ti.MEDIAN_FLAT_TOL)
    for y in (np.array([1.0, 3.0, 2.0]), np.array([0.2, -0.1, 0.4])):
        assert ti.trend_data_warning(x, y, 0.05) == {"data_warning": "persistence_not_estimable",
                                                     "data_warning_detail": None}
    assert np.ptp(ti._design_median_function(np.arange(4, dtype=float) * 66.0)) > 0.1


def test_trend_data_warning_memory_error_not_evaluated(monkeypatch: pytest.MonkeyPatch) -> None:
    """模擬記憶體不足 ⇒ warning_not_evaluated（可重試、p 照常；同 ㊹）。"""
    from momentum.Analysis import hac_ewc as he

    def _boom(*_a, **_k):
        raise he.WarningSimulationMemoryError("simulated")

    ti._DESIGN_CACHE.clear()
    monkeypatch.setattr(he, "_rows_per_chunk", _boom)
    x = _design(30, seed=9)
    out = ti.trend_data_warning(x, np.random.default_rng(1).standard_normal(30), 0.05)
    assert out == {"data_warning": "warning_not_evaluated", "data_warning_detail": None}
