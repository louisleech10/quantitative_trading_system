"""ICPERF Task 0.4 ㊹（SPEC v5.63 (af)(ag)）：縱向顯著性依 IC 方法、檢定改 LLSW 2018 EWC、無上限、資料不足照常出 p 並警示。

驗收對應 SPEC v5.63「驗證」①–⑥（⑦＝Task 0.3 正確性收據重擷取，另於收據驗）。
oracle：測試自寫之論文式餘弦基底矩陣直算（EWC 長期變異數，與產品 DCT 路徑獨立）、十進位高精度 ν、O(n²) numpy 直算
（Kendall 投影）、`arch` 平穩區塊 bootstrap 重抽 `scipy.stats.kendalltau`（Kendall SE）、模擬虛無拒絕率之直接模擬。
無上限行為測試以放大 n、h 實跑驗（不讀程式文字）。跨標的 IC 序列與趨勢斜率不在本項（SPEC Task 0.4 ㊺）。
"""
from __future__ import annotations

import decimal
import math
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from momentum.Analysis import hac_ewc as H
from momentum.Analysis import ic_filter_orchestrator as orch_mod
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.statistical_validator import _hac_nan_result, compute_hac_ic_statistics

REL_TOL = 1e-12
NO_SPLIT = {"ic_train_test_split": False}
DETAIL_KEYS = {"n_obs", "horizon", "approx_independent_n", "phi_hat", "alpha", "estimated_null_reject_rate",
               "reference_reject_rate", "replications"}


# ── oracle ───────────────────────────────────────────────────────────────────────────────────────


def _ref_nu(n: int) -> int:
    with decimal.localcontext() as ctx:
        ctx.prec = 50
        return int((decimal.Decimal("0.4") * decimal.Decimal(n) ** (decimal.Decimal(2) / decimal.Decimal(3)))
                   .to_integral_value(rounding=decimal.ROUND_FLOOR))


def _ref_omega(e: np.ndarray, nu: int) -> float:
    n = e.size
    t = np.arange(1, n + 1, dtype=float)
    basis = np.sqrt(2.0 / n) * np.cos(np.pi * np.arange(1, nu + 1, dtype=float)[:, None] * (t[None, :] - 0.5) / n)
    lam = basis @ (e - e.mean())
    return float(np.mean(lam ** 2))


def _ref_kendall_h(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    return (np.sign(x[:, None] - x[None, :]) * np.sign(y[:, None] - y[None, :])).sum(axis=1) / (x.size - 1)


def _ref_z(x: np.ndarray, y: np.ndarray, method: str):
    if method == "spearman":
        rx, ry = stats.rankdata(x), stats.rankdata(y)
        return ((rx - rx.mean()) / rx.std(ddof=1)) * ((ry - ry.mean()) / ry.std(ddof=1)), 1.0
    if method == "pearson":
        return ((x - x.mean()) / x.std(ddof=1)) * ((y - y.mean()) / y.std(ddof=1)), 1.0
    return _ref_kendall_h(x, y), 2.0


def _ref_ewc(x: np.ndarray, y: np.ndarray, method: str) -> Dict[str, Any]:
    z, factor = _ref_z(x, y, method)
    n = z.size
    nu = _ref_nu(n)
    se = factor * math.sqrt(_ref_omega(z, nu) / n)
    t = float(z.mean()) / se
    return {"t_stat": t, "p_value": float(2.0 * stats.t.sf(abs(t), df=nu)), "se": se, "ewc_dof": nu}


def _rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-300)


def _ar1(rng: np.random.Generator, n: int, phi: float) -> np.ndarray:
    e = rng.standard_normal(n)
    x = np.empty(n)
    x[0] = e[0] / math.sqrt(1.0 - phi * phi)
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def _overlap_label(rng: np.random.Generator, n: int, h: int) -> np.ndarray:
    r = rng.standard_normal(n + h)
    cs = np.concatenate([[0.0], np.cumsum(r)])
    return cs[1 + h:n + 1 + h] - cs[1:n + 1]


def _frame(x: np.ndarray, y: np.ndarray):
    idx = pd.RangeIndex(x.size)
    return pd.DataFrame({"f": x}, index=idx), pd.Series(y, index=idx)


def _two_se(r1: float, r2: float) -> float:
    R = H.WARNING_SIM_REPLICATIONS
    return 2.0 * math.sqrt(r1 * (1 - r1) / R + r2 * (1 - r2) / R)


# ── ① EWC 長期變異數與 ν ─────────────────────────────────────────────────────────────────────────


def test_ewc_long_run_variance_matches_cosine_basis_longitudinal() -> None:
    """① 縱向：EWC 長期變異數 == 論文式餘弦基底直算（相對誤差 ≤ 1e-12）；ν＝⌊0.4·n^(2/3)⌋ 於 n∈{8, 41, 339, 1,017, 4,070}
    （另含整數邊界 n＝125、1,000，浮點直算會差 1）。"""
    rng = np.random.default_rng(1)
    for n in (8, 41, 125, 339, 1000, 1017, 4070):
        nu = H.ewc_dof(n)
        assert nu == _ref_nu(n), n
        e = _ar1(rng, n, 0.6)
        assert _rel(H.ewc_long_run_variance(e, nu), _ref_omega(e, nu)) <= REL_TOL, n


# ── ② Kendall 投影 ──────────────────────────────────────────────────────────────────────────────


def test_kendall_projection_equals_bruteforce() -> None:
    """② Kendall 投影 h 對 O(n²) 直算逐元素相等（重複值、全同值、n＝2、3）；mean(h)＝τ_a＝(C−D)／C(n,2)。"""
    rng = np.random.default_rng(2)
    cases = [
        (np.array([1.0, 2.0]), np.array([2.0, 1.0])),
        (np.array([1.0, 2.0, 3.0]), np.array([1.0, 3.0, 2.0])),
        (np.ones(6), rng.standard_normal(6)),
        (rng.integers(0, 4, 50).astype(float), rng.integers(0, 3, 50).astype(float)),
        (rng.standard_normal(200), rng.standard_normal(200)),
        (np.round(rng.standard_normal(300), 1), np.round(rng.standard_normal(300), 1)),
    ]
    for x, y in cases:
        h = H.kendall_projection_h(x, y)
        np.testing.assert_array_equal(h, _ref_kendall_h(x, y))
        n = x.size
        cd = sum(np.sign(x[i] - x[j]) * np.sign(y[i] - y[j]) for i in range(n) for j in range(i + 1, n))
        assert math.isclose(float(h.mean()), cd / (n * (n - 1) / 2), rel_tol=1e-12, abs_tol=1e-15)


# ── ③ Kendall SE 對區塊 bootstrap ───────────────────────────────────────────────────────────────


def test_kendall_se_matches_block_bootstrap() -> None:
    """③ Kendall SE（因子 2）對固定 seed 平穩區塊 bootstrap（`arch` StationaryBootstrap，區塊長＝`optimal_block_length`；
    重抽 `scipy.stats.kendalltau`）之標準差相對差 ≤ 15%。"""
    from arch.bootstrap import StationaryBootstrap, optimal_block_length

    rng = np.random.default_rng(3)
    n = 500
    x = _ar1(rng, n, 0.5)
    y = 0.3 * x + rng.standard_normal(n)
    se = H.ewc_test(H.kendall_projection_h(x, y), H.KENDALL_SE_FACTOR)["se"]
    block = float(optimal_block_length(np.column_stack([x, y])).loc[:, "stationary"].max())
    bs = StationaryBootstrap(block, x, y, seed=12345)
    taus = np.array([stats.kendalltau(xb, yb)[0] for (xb, yb), _ in bs.bootstrap(1000)])
    assert abs(se - taus.std(ddof=1)) / taus.std(ddof=1) <= 0.15, (se, taus.std(ddof=1))


# ── ④(a) 無上限 ─────────────────────────────────────────────────────────────────────────────────


def test_no_sample_size_cap() -> None:
    """④(a) 同一 h 與特徵生成方式：n＝500 能算出 p 者，n＝5,000、50,000 亦必算出 p（inference_status＝ok）。"""
    for n in (500, 5000, 50000):
        rng = np.random.default_rng(n)
        f, y = _frame(rng.standard_normal(n), _overlap_label(rng, n, 5))
        r = compute_hac_ic_statistics(f, y, 5, method="pearson", alpha=0.05)["f"]
        assert r["inference_status"] == "ok" and np.isfinite(r["p_value"]), (n, r)


def test_no_horizon_cap() -> None:
    """④(a) h∈{1, 5, 21, 60, 120, 365} 各存在足夠大之 n 使 p 算出且無 data_warning。"""
    n = 5000
    for h in (1, 5, 21, 60, 120, 365):
        rng = np.random.default_rng(h)
        f, y = _frame(rng.standard_normal(n), _overlap_label(rng, n, h))
        r = compute_hac_ic_statistics(f, y, h, method="pearson", alpha=0.05)["f"]
        assert r["inference_status"] == "ok" and np.isfinite(r["p_value"]), (h, r)
        assert r["data_warning"] is None, (h, r["data_warning_detail"])


# ── ④(b) 資料足夠時警示消失 ─────────────────────────────────────────────────────────────────────


def test_warning_disappears_with_enough_data() -> None:
    """④(b) h∈{5, 24, 60}、φ＝0.99、n_obs＝50,000 無 small_effective_sample；警示判定等於以實際 n_obs、h、方法、α、φ̂
    計算之判準。"""
    n = 50000
    for h in (5, 24, 60):
        rng = np.random.default_rng(100 + h)
        x = _ar1(rng, n, 0.99)
        f, y = _frame(x, _overlap_label(rng, n, h))
        r = compute_hac_ic_statistics(f, y, h, method="pearson", alpha=0.05)["f"]
        assert r["data_warning"] is None, (h, r["data_warning_detail"])
        st = H.warning_statistics(n, h, "pearson", 0.05, H.ls_ar1_coefficient(x))
        assert st["warn"] is False and st["warn"] == H.paired_warning(st["delta"], st["se"])


# ── ④(c) 判準、內插、快取、分塊、邊界 ─────────────────────────────────────────────────────────────


def test_warning_criterion_interpolation_cache(monkeypatch) -> None:
    """④(c)（SPEC v5.64）判準＝配對差 D_r 之均值 Δ 與 s＝sqrt(Σ(D_r−Δ)²／(R(R−1)))，Δ > 2s 警示、s＝0 時 Δ > 0，
    R＝WARNING_SIM_REPLICATIONS；同輸入逐位元相同；α 改 0.10 以同批虛無 p 值重新計數不重抽；兩個不同 seed 族判定一致；
    共同隨機數（各 φ 點與參照同一特徵創新、n 節點取前綴）；n 節點對數內插與直接模擬之差 ≤ 2 標準誤；φ 網格（含 ±1 端點）
    內插於 φ̂∈{−0.9995, −0.99, −0.5, 0.9995, 0.99995, 0.999995} 與直接模擬之差 ≤ 2 標準誤；φ̂＝±1 取端點組且 p 有限；
    中位數不偏 φ̂ 值域恆在 [−1, 1]（ρ̂ 超出 m(±1) 取端點）；分塊與一次計算逐位元相同；快取命中；ν < 1、Ω ≤ 0 邊界；
    n＝7 可算序列出 p。"""
    R = H.WARNING_SIM_REPLICATIONS
    assert R == 1000
    rng = np.random.default_rng(31)
    for _ in range(4):
        d = rng.choice([-1.0, 0.0, 0.0, 1.0, 0.4], size=R)
        delta = float(d.mean())
        s = math.sqrt(float(((d - delta) ** 2).sum()) / (R * (R - 1)))
        assert H.paired_warning(delta, s) is (delta > 2 * s)
    assert H.paired_warning(0.001, 0.0) is True and H.paired_warning(0.0, 0.0) is False
    assert H.paired_warning(-0.01, 0.0) is False

    # 同輸入逐位元相同（清快取重算）；分塊與一次計算逐位元相同
    H._NULL_PVALUE_CACHE.clear()
    p1 = H.simulate_null_pvalues(173, 5, "spearman", 0.9)
    H._NULL_PVALUE_CACHE.clear()
    p2 = H.simulate_null_pvalues(173, 5, "spearman", 0.9)
    np.testing.assert_array_equal(p1, p2)
    for method in ("pearson", "spearman", "kendall"):
        np.testing.assert_array_equal(H.simulate_null_pvalues(173, 5, method, 0.5, rows_per_chunk=7),
                                      H.simulate_null_pvalues(173, 5, method, 0.5, rows_per_chunk=R))
    np.testing.assert_array_equal(H.simulate_null_pvalues(173, 5, "pearson", H.REFERENCE_POINT, rows_per_chunk=3),
                                  H.simulate_null_pvalues(173, 5, "pearson", H.REFERENCE_POINT, rows_per_chunk=R))

    # 快取命中與 α 後置：換 α 不再呼叫模擬
    calls = {"n": 0}
    real_chunk = H._simulate_chunk

    def _counting(*a, **k):
        calls["n"] += 1
        return real_chunk(*a, **k)

    monkeypatch.setattr(H, "_simulate_chunk", _counting)
    H._NULL_PVALUE_CACHE.clear()
    d05 = H.warning_statistics(339, 24, "pearson", 0.05, 0.97)
    first = calls["n"]
    assert first > 0
    d10 = H.warning_statistics(339, 24, "pearson", 0.10, 0.97)
    assert calls["n"] == first, "換 α 不得重抽"
    assert d10["r_hat"] >= d05["r_hat"] and d10["r_ref"] >= d05["r_ref"]
    monkeypatch.setattr(H, "_simulate_chunk", real_chunk)

    # 共同隨機數：seed 不含 n 節點、φ、α；n 節點取同一串流之前綴
    seed = H.simulation_seed(24, "pearson")
    np.testing.assert_array_equal(H._feature_innovations(seed, 0, 5, 326),
                                  H._feature_innovations(seed, 0, 5, 343)[:, :326])
    np.testing.assert_array_equal(H._return_innovations(seed, 0, 5, 350),
                                  H._return_innovations(seed, 0, 5, 367)[:, :350])
    assert H.simulation_seed(24, "pearson") != H.simulation_seed(5, "pearson")

    # 兩個不同 seed 族之判定於已知案例一致（ρ̂ 為含截距 AR(1) 最小平方估計之輸入）
    def _decisions() -> tuple:
        H._NULL_PVALUE_CACHE.clear()
        H._LS_MEDIAN_CACHE.clear()
        return (H.small_sample_warning(339, 24, "pearson", 0.05, 0.985) is not None,
                H.small_sample_warning(4070, 5, "pearson", 0.05, 0.5) is not None)

    base = _decisions()
    real_seed = H.simulation_seed
    monkeypatch.setattr(H, "simulation_seed", lambda *a: real_seed(*a) ^ 0x5A5A5A5A5A5A5A5A)
    assert _decisions() == base == (True, False)
    monkeypatch.setattr(H, "simulation_seed", real_seed)
    H._NULL_PVALUE_CACHE.clear()
    H._LS_MEDIAN_CACHE.clear()

    # n 節點對數內插 vs 直接模擬（同 R）
    for n_obs in (339, 1017, 4070, 20352):
        lo, hi = H.node_bracket(n_obs)
        r_lo = H.reject_rate(H.simulate_null_pvalues(lo, 5, "pearson", 0.9), 0.05)
        r_hi = H.reject_rate(H.simulate_null_pvalues(hi, 5, "pearson", 0.9), 0.05)
        w = 0.0 if lo == hi else (math.log(n_obs) - math.log(lo)) / (math.log(hi) - math.log(lo))
        r_interp = (1 - w) * r_lo + w * r_hi
        r_direct = H.reject_rate(H.simulate_null_pvalues(n_obs, 5, "pearson", 0.9), 0.05)
        assert abs(r_interp - r_direct) <= _two_se(r_interp, r_direct), (n_obs, lo, hi, r_interp, r_direct)

    # φ 網格內插 vs 直接模擬（含負 φ 與近 1 區段）；±1 端點
    node = 339
    for phi in (-0.9995, -0.99, -0.5, 0.9995, 0.99995, 0.999995):
        lo, hi, w = H.phi_bracket(phi)
        r_lo = H.reject_rate(H.simulate_null_pvalues(node, 24, "pearson", lo), 0.05)
        r_hi = H.reject_rate(H.simulate_null_pvalues(node, 24, "pearson", hi), 0.05)
        r_interp = (1 - w) * r_lo + w * r_hi
        r_direct = H.reject_rate(H.simulate_null_pvalues(node, 24, "pearson", phi), 0.05)
        assert abs(r_interp - r_direct) <= _two_se(r_interp, r_direct), (phi, r_interp, r_direct)
    for phi in (-1.0, 1.0):
        assert H.phi_bracket(phi) == (phi, phi, 0.0)
        assert np.isfinite(H.simulate_null_pvalues(node, 24, "pearson", phi)).all()

    # 中位數不偏 φ̂ 值域（含交錯序列、近單根、ρ̂ 超出 m(±1)）
    rng = np.random.default_rng(9)
    for x in (np.cumsum(rng.standard_normal(300)), (-1.0) ** np.arange(300) * np.cumsum(rng.standard_normal(300)),
              (-1.0) ** np.arange(50) + 0.01 * rng.standard_normal(50), np.arange(400, dtype=float)):
        rho = H.ls_ar1_coefficient(x)
        v = H.median_unbiased_phi(rho, x.size)
        assert -1.0 <= v <= 1.0, (rho, v)
    assert H.median_unbiased_phi(1.5, 339) == 1.0
    assert H.median_unbiased_phi(-1.5, 339) == -1.0
    # 端點與相等之優先序（v5.66）：上端平台、下端平台、全網格常數、嚴格越界
    g = np.array(H.PHI_GRID)
    top = np.linspace(-0.99, 0.98, g.size)
    top[-2:] = 0.99  # m̃(0.99999)＝m̃(1)＝0.99
    assert H._left_inverse(top, 0.99) == 0.99999  # 相等 ⇒ 左廣義逆（平台最小 φ）
    assert H._left_inverse(top, 0.9900001) == 1.0  # 嚴格越界 ⇒ 1
    bottom = np.linspace(-0.98, 0.99, g.size)
    bottom[:2] = -0.99  # m̃(−1)＝m̃(−0.999)
    assert H._left_inverse(bottom, -0.99) == -1.0  # 相等 ⇒ 左廣義逆＝−1
    assert H._left_inverse(bottom, -0.9900001) == -1.0  # 嚴格越界 ⇒ −1
    const = np.full(g.size, 0.5)
    assert H._left_inverse(const, 0.5) == -1.0 and H._left_inverse(const, 0.6) == 1.0
    assert H._left_inverse(const, 0.4) == -1.0

    # ν < 1、Ω ≤ 0 邊界；n＝7 出 p
    assert H.ewc_test(np.array([1.0, -1.0, 0.5]))["inference_status"] == "insufficient_sample"
    assert H.ewc_test(np.full(20, 0.3))["inference_status"] == "degenerate"
    seven = H.ewc_test(np.array([0.3, -1.2, 0.8, 2.0, -0.4, 0.1, 1.5]))
    assert seven["inference_status"] == "ok" and np.isfinite(seven["p_value"]) and seven["ewc_dof"] == 1


def test_median_unbiased_phi_matches_truth() -> None:
    """④(c)（v5.65，諮詢 R4 codex 要求之獨立對照、規格審查 r90）：真值 AR(1) φ∈{0.9, 0.99, 0.995, 1}、
    n∈{339, 500, 1,017, 2,000}（含落在兩 n 節點之間者）各 400 條實現之 Andrews 中位數不偏 φ̂ 中位數與真值之差 ≤ 0.01；
    以 ρ̂ 中位數為輸入之警示判定 == 以真值 φ 於 n_obs 直接模擬（同 R、同共同隨機數）之配對差判定；m̃ 投影後各節點弱遞增、
    同一 ρ̂ 反解唯一；同一特徵之 φ̂ 不隨 h、方法改變（校準串流獨立）。"""
    from scipy import signal

    rng = np.random.default_rng(64)
    for n in (339, 500, 1017, 2000):
        for node in set(H.node_bracket(n)):
            assert np.all(np.diff(H.ls_ar1_monotone_medians(node)) >= 0.0), node
        for phi in (0.9, 0.99, 0.995, 1.0):
            e = rng.standard_normal((400, n))
            if phi < 1:
                e[:, 0] /= math.sqrt(1 - phi * phi)
            rho = H.ls_ar1_coefficient_rows(signal.lfilter([1.0], [1.0, -phi], e, axis=1))
            phis = np.array([H.median_unbiased_phi(r, n) for r in rho])
            assert np.array_equal(phis, np.array([H.median_unbiased_phi(r, n) for r in rho]))
            assert abs(float(np.median(phis)) - phi) <= 0.01, (n, phi, float(np.median(phis)))
            st = H.warning_statistics(n, 24, "pearson", 0.05, float(np.median(rho)))
            i_true = (H.simulate_null_pvalues(n, 24, "pearson", phi) <= 0.05).astype(float)
            j_true = (H.simulate_null_pvalues(n, 24, "pearson", H.REFERENCE_POINT) <= 0.05).astype(float)
            dt = i_true - j_true
            warn_true = H.paired_warning(float(dt.mean()), float(dt.std(ddof=1) / math.sqrt(dt.size)))
            assert st["warn"] == warn_true, (n, phi, st, float(dt.mean()))
    # φ̂ 不隨 h、方法改變：中位數函數之 seed 不含 h、方法（同 ρ̂、同 n_obs 之 φ̂ 逐位元相同）
    a = H.warning_statistics(500, 24, "pearson", 0.05, 0.97)["phi_hat"]
    b = H.warning_statistics(500, 5, "spearman", 0.05, 0.97)["phi_hat"]
    assert a == b == H.median_unbiased_phi(0.97, 500)


@pytest.mark.slow
def test_warning_large_n_chunked_completes() -> None:
    """④(c) n＝500,000 以分塊完成且 p 正常輸出（任意 n 皆可算；峰值記憶體另入收據）。"""
    n = 500_000
    rng = np.random.default_rng(500)
    f, y = _frame(rng.standard_normal(n), _overlap_label(rng, n, 5))
    r = compute_hac_ic_statistics(f, y, 5, method="pearson", alpha=0.05)["f"]
    assert r["inference_status"] == "ok" and np.isfinite(r["p_value"])


# ── ④(d) 已知案例、警示不改 p ───────────────────────────────────────────────────────────────────


def test_warning_known_cases_and_does_not_change_p(monkeypatch) -> None:
    """④(d) n＝339、h＝24、φ̂≈0.99 有 small_effective_sample 且 detail 封閉八鍵皆有值；n＝4,070、h＝5 無警示；
    low_confidence 致 α＝0.10 時 detail.alpha＝0.10；警示不改 p、q 與門檻判定（有無警示之 p、q、倖存集合逐值相等）。"""
    rng = np.random.default_rng(339)
    x = np.cumsum(rng.standard_normal(339))  # 近單根特徵（中位數不偏 φ̂≈0.99 以上）
    f, y = _frame(x, _overlap_label(rng, 339, 24))
    r = compute_hac_ic_statistics(f, y, 24, method="pearson", alpha=0.05)["f"]
    assert r["data_warning"] == "small_effective_sample"
    d = r["data_warning_detail"]
    assert set(d) == DETAIL_KEYS and all(v is not None for v in d.values())
    assert d["phi_hat"] >= 0.98
    assert d["n_obs"] == 339 and d["horizon"] == 24 and d["alpha"] == 0.05 and d["replications"] == 1000
    assert math.isclose(d["approx_independent_n"], 339 / 24)
    r10 = compute_hac_ic_statistics(f, y, 24, method="pearson", alpha=0.10)["f"]
    assert r10["data_warning_detail"]["alpha"] == 0.10 and r10["p_value"] == r["p_value"]

    rng = np.random.default_rng(4070)
    x2 = _ar1(rng, 4070, 0.5)
    f2, y2 = _frame(x2, _overlap_label(rng, 4070, 5))
    r2 = compute_hac_ic_statistics(f2, y2, 5, method="pearson", alpha=0.05)["f"]
    assert r2["data_warning"] is None and r2["data_warning_detail"] is None  # 未觸發 ⇒ detail 依定義為 null（收據 verified-na 證明）

    # low_confidence ⇒ 第 5 段 α＝0.10 傳入警示
    feats, label = _stage5_inputs()
    seen = []
    real = orch_mod.compute_hac_ic_statistics

    def _spy(*a, **k):
        seen.append(k["alpha"])
        return real(*a, **k)

    monkeypatch.setattr(orch_mod, "compute_hac_ic_statistics", _spy)
    _run_stage5(feats, label, "pearson", event_info={"tier": "low_confidence"})
    assert seen == [0.10]
    monkeypatch.setattr(orch_mod, "compute_hac_ic_statistics", real)

    # 警示不改 p、q、倖存集合
    with_warn = _run_stage5(feats, label, "pearson")
    import momentum.Analysis.hac_ewc as hmod

    monkeypatch.setattr(hmod, "small_sample_warning", lambda *a, **k: None)
    no_warn = _run_stage5(feats, label, "pearson")
    for col in feats.columns:
        for k in ("p_value", "p_value_adj", "t_stat"):
            a, b = with_warn["ic_stats"][col][k], no_warn["ic_stats"][col][k]
            assert (a == b) or (np.isnan(a) and np.isnan(b)), (col, k)
    assert [r["feature_name"] for r in with_warn["summary_table"]] == [r["feature_name"] for r in no_warn["summary_table"]]


# ── ⑤ 變異 ──────────────────────────────────────────────────────────────────────────────────────


def test_mutation_kendall_factor_nu_dof_dct_method(monkeypatch) -> None:
    """⑤ 變異：Kendall 因子 2→1、ν 係數 0.4 改他值、自由度改 n−1、DCT 正規化錯、method 固定 spearman ⇒ 各至少一條紅
    （以 ①② 之 oracle 對照判定「紅」）。"""
    from fractions import Fraction

    rng = np.random.default_rng(5)
    x = _ar1(rng, 240, 0.4)
    y = 0.4 * x + rng.standard_normal(240)
    f, lab = _frame(x, y)
    expected = {m: _ref_ewc(x, y, m) for m in ("spearman", "pearson", "kendall")}  # oracle 先算（變異不得波及 oracle）

    def _matches(method: str) -> bool:
        got = compute_hac_ic_statistics(f, lab, 1, method=method, alpha=0.05)["f"]
        exp = expected[method]
        return all(_rel(got[k], exp[k]) <= REL_TOL for k in ("se", "t_stat", "p_value")) and got["ewc_dof"] == exp["ewc_dof"]

    assert _matches("kendall") and _matches("pearson") and _matches("spearman")
    monkeypatch.setattr(H, "KENDALL_SE_FACTOR", 1.0)
    assert not _matches("kendall")
    monkeypatch.setattr(H, "KENDALL_SE_FACTOR", 2.0)
    monkeypatch.setattr(H, "EWC_NU_COEF", Fraction(1, 2))
    assert not _matches("pearson")
    monkeypatch.setattr(H, "EWC_NU_COEF", Fraction(2, 5))
    real_sf = H.stats.t.sf
    monkeypatch.setattr(H.stats.t, "sf", lambda v, df: real_sf(v, df=239))
    assert not _matches("pearson")
    monkeypatch.setattr(H.stats.t, "sf", real_sf)
    real_dct = H._fft.dct
    monkeypatch.setattr(H._fft, "dct", lambda a, type=2, norm="ortho", axis=-1: real_dct(a, type=type, norm=None, axis=axis))
    assert not _matches("pearson")
    monkeypatch.setattr(H._fft, "dct", real_dct)
    import momentum.Analysis.statistical_validator as sv

    real_mc = sv._method_contribution
    monkeypatch.setattr(sv, "_method_contribution", lambda method, a, b: real_mc("spearman", a, b))
    assert not _matches("pearson")


# ── ⑥ 端到端 ────────────────────────────────────────────────────────────────────────────────────


def _stage5_inputs(n: int = 240):
    rng = np.random.default_rng(7)
    index = pd.Index(np.arange(n, dtype=np.int64) * 3600 + 1_600_000_000, name="timestamp")
    latent = rng.standard_normal(n)
    feats = pd.DataFrame({
        "f0": np.exp(2.0 * latent) + 0.5 * rng.standard_normal(n),
        "f1": rng.standard_normal(n),
        "f2": 0.3 * latent + rng.standard_normal(n),
        "const": np.ones(n),
        "persist": np.cumsum(rng.standard_normal(n)),
    }, index=index)
    label = pd.Series(latent + 0.1 * rng.standard_normal(n), index=index, name="label")
    return feats, label


def _stage5_overlap_inputs(n: int = 240, h: int = 24):
    """重疊標籤（未來 h 根報酬和）＋持續性特徵（平滑隨機漫步）＋常數欄：供警示與 FDR 計入規則。"""
    rng = np.random.default_rng(17)
    index = pd.Index(np.arange(n, dtype=np.int64) * 3600 + 1_600_000_000, name="timestamp")
    walk = np.cumsum(rng.standard_normal(n + 50))
    smooth = np.convolve(walk, np.ones(50) / 50, mode="valid")[: n]
    feats = pd.DataFrame({
        "noise": rng.standard_normal(n),
        "smooth": smooth,
        "walk": walk[:n],
        "const": np.ones(n),
    }, index=index)
    label = pd.Series(_overlap_label(rng, n, h), index=index, name="label")
    return feats, label


def _run_stage5(feats, label, method: str, *, maxlags=None, event_info=None, horizon: int = 1):
    cfg: Dict[str, Any] = {**NO_SPLIT, "global": {"default_method": method, "default_horizon": horizon},
                           "labels": {"horizons": [horizon]}}
    if maxlags is not None:
        cfg["significance"] = {"maxlags": maxlags}
    config = ICConfig.model_validate(cfg)
    orch = ICFilterOrchestrator(config)
    icir = {c: {"ic_mean": 0.05, "ic_std": 0.1, "icir": 0.5, "ic_hit_rate": 0.6} for c in feats.columns}
    return orch._stage5_statistical_validation(
        feats, label, {"rolling_ic": {c: {"window_5": [0.1, 0.2]} for c in feats.columns}, "icir": icir,
                       "ic_decay": {}},
        config, event_info or {"tier": "sufficient"}, metadata={"symbol": "BTCUSDT"},
    )


@pytest.mark.parametrize("method", ["spearman", "pearson", "kendall"])
def test_stage5_tested_estimator_and_t_follow_method(method: str) -> None:
    """⑥ 端到端：第 5 段 `tested_estimator`＝`bar_level_<method>`，t／p == oracle；`hac_method`＝`ewc_llsw2018`。"""
    feats, label = _stage5_inputs()
    out = _run_stage5(feats, label, method)
    sig = out["significance"]
    assert sig["tested_estimator"] == f"bar_level_{method}" and sig["hac_method"] == "ewc_llsw2018"
    assert sig["maxlags"] is None and sig["horizon"] == 1
    for col in ("f0", "f1", "f2", "persist"):
        exp = _ref_ewc(feats[col].to_numpy(), label.to_numpy(), method)
        got = out["ic_stats"][col]
        assert _rel(got["t_stat"], exp["t_stat"]) <= REL_TOL and _rel(got["p_value"], exp["p_value"]) <= REL_TOL
        assert got["ewc_dof"] == exp["ewc_dof"]


def test_not_computable_excluded_warned_included_in_fdr() -> None:
    """⑥ insufficient_sample／degenerate ⇒ p／q＝NaN、BH 之 m 不計；有 small_effective_sample 警示者照常進 BH 與門檻。"""
    feats, label = _stage5_overlap_inputs()
    out = _run_stage5(feats, label, "pearson", horizon=24)
    st = out["ic_stats"]
    assert out["significance"]["horizon"] == 24
    assert st["const"]["inference_status"] == "degenerate"
    assert np.isnan(st["const"]["p_value"]) and np.isnan(st["const"]["p_value_adj"])
    computable = [c for c in feats.columns if st[c]["inference_status"] == "ok"]
    assert out["n_tests"] == len(computable) == 3
    assert out["significance"]["not_computable_count"] == 1
    warned = [c for c in computable if st[c]["data_warning"] is not None]
    assert warned, "前提：至少一欄有資料不足警示（平滑隨機漫步、n＝240、h＝24）"
    assert out["significance"]["data_warning_count"] == len(warned)
    for c in warned:
        assert np.isfinite(st[c]["p_value_adj"])
    rows = {r["feature_name"]: r for r in out["summary_table"]}
    for c in warned:
        if c in rows:
            assert rows[c]["data_warning"] == "small_effective_sample"
            assert set(rows[c]["data_warning_detail"]) == DETAIL_KEYS


def test_persistence_not_estimable_is_distinct_from_no_warning() -> None:
    """（v5.67，r92 CODEX-R92-P1-01）滯後段常數而整段非常數之特徵：EWC 照常出 p（ok），ρ̂ 不可估 ⇒
    data_warning＝`persistence_not_estimable`、detail＝null（不得與「未觸發」之 null 混同）；metadata 另計其數。"""
    x = np.array([1.0, 1, 1, 1, 1, 1, 2])
    y = np.array([1.0, 4, 2, 7, 3, 5, 6])
    f, lab = _frame(x, y)
    r = compute_hac_ic_statistics(f, lab, 24, method="pearson", alpha=0.05)["f"]
    assert r["inference_status"] == "ok" and np.isfinite(r["p_value"])
    assert not np.isfinite(H.ls_ar1_coefficient(x))
    assert r["data_warning"] == "persistence_not_estimable" and r["data_warning_detail"] is None
    rng = np.random.default_rng(3)
    ok_x = rng.standard_normal(200)
    f2, lab2 = _frame(ok_x, rng.standard_normal(200))
    assert compute_hac_ic_statistics(f2, lab2, 1, method="pearson", alpha=0.05)["f"]["data_warning"] is None


def test_chunk_rows_follow_current_available_memory(monkeypatch) -> None:
    """（v5.67，r92 CODEX-R92-P1-02）分塊列數依當下可用記憶體（psutil available），可用量降低則每塊列數隨之降低。"""
    import psutil

    class _VM:
        def __init__(self, avail: int) -> None:
            self.available = avail

    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM(8 * 1024 ** 3))
    high = H._rows_per_chunk(20000, 24)
    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM(64 * 1024 ** 2))
    low = H._rows_per_chunk(20000, 24)
    assert high > low >= 1
    per_row = (2 * 20000 + 24) * 8 * H._ARRAYS_PER_ROW
    assert low == max(1, (64 * 1024 ** 2 // 4) // per_row)

    # （v5.68，r93 CODEX-R93-P1-01）單列超過當下可用量 ⇒ 具名錯誤，不強行配置；第 5 段記 warning_not_evaluated、p 照常
    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM(1024 * 1024))
    with pytest.raises(H.WarningSimulationMemoryError):
        H._rows_per_chunk(20000, 24)
    H._NULL_PVALUE_CACHE.clear()
    H._LS_MEDIAN_CACHE.clear()
    rng = np.random.default_rng(8)
    f, lab = _frame(np.cumsum(rng.standard_normal(20000)), rng.standard_normal(20000))
    r = compute_hac_ic_statistics(f, lab, 24, method="pearson", alpha=0.05)["f"]
    assert r["inference_status"] == "ok" and np.isfinite(r["p_value"])
    assert r["data_warning"] == "warning_not_evaluated" and r["data_warning_detail"] is None

    # （r94 CODEX-R94-P1-01）實際配置失敗之一般 MemoryError 亦記 warning_not_evaluated，p 照常，且下一特徵照常判定
    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM(8 * 1024 ** 3))
    import momentum.Analysis.hac_ewc as hmod

    real_ssw = hmod.small_sample_warning
    calls = {"n": 0}

    def _fail_first(*a, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            raise MemoryError("allocation failed")
        return real_ssw(*a, **k)

    monkeypatch.setattr(hmod, "small_sample_warning", _fail_first)
    rng = np.random.default_rng(9)
    two = pd.DataFrame({"a": np.cumsum(rng.standard_normal(339)), "b": np.cumsum(rng.standard_normal(339))})
    out = compute_hac_ic_statistics(two, pd.Series(_overlap_label(rng, 339, 24)), 24, method="pearson", alpha=0.05)
    assert out["a"]["data_warning"] == "warning_not_evaluated" and np.isfinite(out["a"]["p_value"])
    assert out["b"]["data_warning"] in ("small_effective_sample", None) and calls["n"] == 2
    monkeypatch.setattr(hmod, "small_sample_warning", real_ssw)

    # 每塊開始前重新評估：可用量於第一塊後下降 ⇒ 後續塊列數隨之變小，且結果與一次計算逐位元相同
    avail = iter([400 * 1024 ** 2] + [30 * 1024 ** 2] * 2000)  # n＝2000：首塊約 327 列，之後約 24 列
    monkeypatch.setattr(psutil, "virtual_memory", lambda: _VM(next(avail)))
    seen = []
    real_chunk = H._simulate_chunk

    def _spy(node, horizon, method, point, seed, r0, r1):
        seen.append(r1 - r0)
        return real_chunk(node, horizon, method, point, seed, r0, r1)

    monkeypatch.setattr(H, "_simulate_chunk", _spy)
    H._NULL_PVALUE_CACHE.clear()
    p_var = H.simulate_null_pvalues(2000, 5, "pearson", 0.5)
    monkeypatch.setattr(H, "_simulate_chunk", real_chunk)
    assert len(set(seen)) > 1 and seen[0] > seen[-1]
    np.testing.assert_array_equal(p_var, H.simulate_null_pvalues(2000, 5, "pearson", 0.5, rows_per_chunk=1000))


@pytest.mark.requires_kline
def test_default_threshold_zero_survivors_on_la1_fixture_is_locked() -> None:
    """（規格審查 r95 決策 1）la1 真實 fixture（BTCUSDT 1h、ETHUSDT 12h）於 EWC 預設門檻下第 5 段倖存 0、無
    `filtered_features_path`（使用者可見數值變化：改前 NW 固定頻寬下 BTC 1、ETH 2）；control golden 另以
    `thresholds.p_value_max`＝1.0 保住倖存者下游路徑覆蓋。"""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "golden" / "la1"))
    import gen_baseline as G  # noqa: E402

    for run in G.RUNS:
        h5_path, meta_path = G._resolve_la0_feature_inputs(run)
        _orch, report = G._run_analyze(h5_path, meta_path, G.control_non_trigger_fallback_config())
        out5 = report["filter_log"]["stage5_thresholds"]["output_features"]
        assert out5["count"] == 0, (run["symbol"], out5)
        assert "filtered_features_path" not in (report.get("metadata") or {})
        assert report["metadata"]["significance"]["hac_method"] == "ewc_llsw2018"


def test_cross_sectional_hac_output_unchanged() -> None:
    """⑥ 跨標的 `_compute_hac_on_ic_series`：㊺ A（SPEC v5.78）後預設改 EWC（另由 test_icperf_xsec_ewc 對論文餘弦
    oracle 驗值）；本測試守「明示 maxlags ⇒ 沿用改前 Newey–West 固定 L」之值不變：對 statsmodels OLS HAC Bartlett
    （use_correction=False）＋t(n−1) 之 oracle，鍵集＝改前鍵集＋㊺ 新增推論鍵；短序列 fail-closed。"""
    rng = np.random.default_rng(11)
    ic = 0.02 + 0.05 * _ar1(rng, 120, 0.3)
    n = ic.size
    L = max(int(4 * (n / 100.0) ** (2.0 / 9.0)), 4)
    out = orch_mod._compute_hac_on_ic_series(ic, 5, maxlags=L)
    new_keys = {"ewc_dof", "hac_method", "inference_status", "interior_gap_count"}
    assert set(out) == set(_hac_nan_result()) | new_keys
    assert out["hac_method"] == "newey_west_fixed" and out["ewc_dof"] is None and out["inference_status"] == "ok"
    fit = sm.OLS(ic, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": L, "kernel": "bartlett",
                                                                "use_correction": False})
    se = float(fit.bse[0])
    t = float(ic.mean()) / se
    assert out["maxlags"] == L and out["n_obs"] == n
    assert _rel(out["se"], se) <= 1e-10 and _rel(out["p_value"], float(2 * stats.t.sf(abs(t), df=n - 1))) <= 1e-10
    default = orch_mod._compute_hac_on_ic_series(ic, 5)
    assert default["hac_method"] == "ewc_llsw2018" and default["maxlags"] is None
    short = orch_mod._compute_hac_on_ic_series(ic[:7], 1, maxlags=4)
    assert set(short) == set(_hac_nan_result()) | new_keys and np.isnan(short["p_value"])
    assert short["inference_status"] == "insufficient_sample"
    tiny = orch_mod._compute_hac_on_ic_series(ic[:3], 1)
    assert np.isnan(tiny["p_value"]) and tiny["inference_status"] == "insufficient_sample"


def test_explicit_maxlags_keeps_newey_west_fixed() -> None:
    """⑥ 明示 `significance.maxlags` ⇒ 沿用現行 Newey–West 固定 L 與 t(n−1)，`hac_method`＝`newey_west_fixed`。"""
    feats, label = _stage5_inputs()
    out = _run_stage5(feats, label, "spearman", maxlags=6)
    sig = out["significance"]
    assert sig["hac_method"] == "newey_west_fixed" and sig["maxlags"] == 6
    for col in ("f0", "f1"):
        z, _ = _ref_z(feats[col].to_numpy(), label.to_numpy(), "spearman")
        fit = sm.OLS(z, np.ones(z.size)).fit(cov_type="HAC", cov_kwds={"maxlags": 6, "kernel": "bartlett",
                                                                       "use_correction": False})
        t = float(z.mean()) / float(fit.bse[0])
        got = out["ic_stats"][col]
        assert got["maxlags"] == 6 and got["ewc_dof"] is None
        assert _rel(got["t_stat"], t) <= 1e-10
        assert _rel(got["p_value"], float(2 * stats.t.sf(abs(t), df=z.size - 1))) <= 1e-10
