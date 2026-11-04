"""ICPERF Task 0.4 ㊺ A：跨標的逐期 IC 序列之 EWC 均值檢定（SPEC v5.78 ㊺ 列驗證 A①–④）。

b2c 已施工（施工前之 xfail 標記已移除）。
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats


def _cosine_ewc_oracle(z: np.ndarray) -> tuple[float, float, int]:
    """獨立 oracle：論文式餘弦基底直算 EWC（LLSW 2018），回 (t, p, ν)。"""
    m = z.size
    nu = int(np.floor(0.4 * m ** (2.0 / 3.0)))
    zc = z - z.mean()
    tt = np.arange(1, m + 1) - 0.5
    basis = np.sqrt(2.0 / m) * np.cos(np.pi * np.arange(1, nu + 1)[:, None] * tt[None, :] / m)
    omega = float(np.sum((basis @ zc) ** 2)) / nu
    t = z.mean() / np.sqrt(omega / m)
    return float(t), float(2.0 * stats.t.sf(abs(t), nu)), nu


def test_a1_xsec_ewc_matches_cosine_oracle() -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series

    z = np.random.default_rng(45).standard_normal(250) * 0.05 + 0.01
    out = _compute_hac_on_ic_series(z, 5)
    t, p, nu = _cosine_ewc_oracle(z)
    assert out["hac_method"] == "ewc_llsw2018"
    assert out["ewc_dof"] == nu
    assert out["t_stat"] == pytest.approx(t, rel=1e-12)
    assert out["p_value"] == pytest.approx(p, rel=1e-10)


def test_a2_interior_gaps_equal_finite_subsequence() -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series

    z = np.random.default_rng(7).standard_normal(300) * 0.05
    full = z.copy()
    full[[0, 1, 50, 120, 121, 299]] = [np.nan, np.nan, np.nan, np.inf, -np.inf, np.nan]
    finite = full[np.isfinite(full)]
    a = _compute_hac_on_ic_series(full, 5)
    b = _compute_hac_on_ic_series(finite, 5)
    assert a["t_stat"] == b["t_stat"] and a["p_value"] == b["p_value"]
    assert a["interior_gap_count"] == 3  # 50、120、121；0、1 為暖機、299 為尾段


def test_a3_routing_and_closed_status() -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series

    z = np.random.default_rng(9).standard_normal(200) * 0.05
    assert _compute_hac_on_ic_series(z, 5, maxlags=8)["hac_method"] == "newey_west_fixed"
    tiny = _compute_hac_on_ic_series(z[:3], 1)
    assert tiny["inference_status"] == "insufficient_sample" and np.isnan(tiny["p_value"])
    const = _compute_hac_on_ic_series(np.full(50, 0.02), 1)
    assert const["inference_status"] == "degenerate" and np.isnan(const["p_value"])
    assert _compute_hac_on_ic_series(z, 5)["inference_status"] == "ok"


def _xsec_method_module():
    """共用 test_icperf_xsec_method.py 之真實 4h 截面面板與執行入口（同一資料定義，不另寫一份）。"""
    import importlib.util
    import sys
    from pathlib import Path

    name = "icperf_xsec_method_helpers"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("test_icperf_xsec_method.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return sys.modules[name]


@pytest.mark.slow
@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", ["spearman", "pearson", "kendall"])
def test_a4_real_kline_xsec_wiring_three_methods(method: str) -> None:
    """真實 kline 4h 全部標的之截面（ICPERF ㊺ A）：各方法之報告逐特徵 t／p／ν 等於以報告逐期 IC 序列（有限值，等距模型）
    之論文式餘弦 EWC 獨立重算；hac_method、inference_status 與 metadata 顯著性揭露一致；警示欄屬封閉值。"""
    helpers = _xsec_method_module()
    report = helpers._run(helpers._real_xsec_panel(), method)
    sig = report["metadata"]["significance"]
    assert sig["hac_method"] == "ewc_llsw2018" and sig["horizon"] == 1
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == {"ret1", "dev20", "vol20", "mom10"}
    for f, row in rows.items():
        z = np.asarray(report["rolling_ic_series"][f]["window_cross_sectional"], dtype=float)
        assert z.size >= 200, f"{f}：有效截面 {z.size} 過少（資料不足）"
        t, p, nu = _cosine_ewc_oracle(z)
        assert row["hac_method"] == "ewc_llsw2018" and row["inference_status"] == "ok", (f, row)
        assert row["ewc_dof"] == nu
        assert row["t_stat"] == pytest.approx(t, rel=1e-12), f
        assert row["p_value"] == pytest.approx(p, rel=1e-10), f
        assert row["data_warning"] in {None, "small_effective_sample", "persistence_not_estimable",
                                       "warning_not_evaluated"}
    dofs = [r["ewc_dof"] for r in rows.values()]
    assert sig["ewc_dof_range"] == [min(dofs), max(dofs)]
