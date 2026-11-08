"""ICPERF SPEC v5.85 Task 0.6 (d)：固定 L 之 HAC 拒算門檻改小樣本警示（L2 首批，真實 kline 小段＋statsmodels oracle）。

兩入口（`momentum/Analysis/ic_filter_orchestrator.py` `_compute_hac_on_ic_series`、`momentum/Analysis/statistical_validator.py`
`compute_hac_ic_statistics`）於明示 maxlags 時：只保留 n≥2、L 為非負整數與 SE 為零／非有限之退化；`n_valid < max(8, 2*L)` 與
`L >= n_valid - 1` 改為照常出值＋`data_warning="small_sample_fixed_lag"`（detail 含 (d) 欄位）。施工前現行碼拒算 ⇒ 本檔應為紅。
oracle：statsmodels `OLS(z, 1).fit(cov_type="HAC", cov_kwds={"maxlags": L, "use_correction": False})` 之 bse；p 依 t(n−1)。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats as scipy_stats

REPO = Path(__file__).resolve().parents[3]
CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
SYMBOL, TIMEFRAME = "ETHUSDT", "12h"
D_FIELDS = {"feature", "method", "n_obs", "horizon_bars", "need", "have", "reason"}


@pytest.fixture(scope="module")
def returns() -> np.ndarray:
    """真實 ETHUSDT 12h 收盤報酬（取第 1,500 根起之一段，避開上市初期；本機快取 1,695 筆報酬）。"""
    from momentum.factories import create_kline_storage_manager
    if not CACHE.is_file():
        pytest.fail(f"requires_kline: missing {CACHE}")
    kline = create_kline_storage_manager(cache_dir=str(CACHE.parent)).read_klines(SYMBOL, TIMEFRAME,
                                                                                   validate_continuity=False)
    close = pd.to_numeric(kline["close"], errors="coerce").to_numpy(dtype=float)
    r = close[1:] / close[:-1] - 1.0
    r = r[np.isfinite(r)]
    assert r.size > 1600
    return r[1500:1600]


def _oracle_se(z: np.ndarray, lag: int) -> float:
    res = sm.OLS(z, np.ones_like(z)).fit(cov_type="HAC", cov_kwds={"maxlags": lag, "use_correction": False})
    return float(res.bse[0])


def _series(returns: np.ndarray, n: int) -> np.ndarray:
    return np.asarray(returns[:n], dtype=float)


@pytest.mark.parametrize("lag", [1, 5, 6, 7])
def test_boundary_01_ic_series_small_n_computes_with_warning(returns: np.ndarray, lag: int) -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series
    z = _series(returns, 7)
    res = _compute_hac_on_ic_series(z, horizon=1, maxlags=lag)
    assert res["inference_status"] == "ok", "n=7 時舊門檻拒算，新契約須照常出值"
    se = _oracle_se(z, lag)
    assert res["se"] == pytest.approx(se, rel=1e-12)
    t = float(np.mean(z) / se)
    assert res["t_stat"] == pytest.approx(t, rel=1e-12)
    assert res["p_value"] == pytest.approx(float(2.0 * scipy_stats.t.sf(abs(t), df=z.size - 1)), rel=1e-12)
    assert res["data_warning"] == "small_sample_fixed_lag"
    detail = res["data_warning_detail"]
    assert D_FIELDS <= set(detail)
    assert detail["n_obs"] == 7 and detail["lag"] == lag and detail["horizon_bars"] == 1


def test_boundary_02_ic_series_adequate_n_no_warning(returns: np.ndarray) -> None:
    """n 充足（100、L=1）⇒ 照常出值、不附小樣本警示；值仍對 statsmodels。"""
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series
    z = _series(returns, 100)
    res = _compute_hac_on_ic_series(z, horizon=1, maxlags=1)
    assert res["inference_status"] == "ok" and res["se"] == pytest.approx(_oracle_se(z, 1), rel=1e-12)
    assert res.get("data_warning") is None


def test_boundary_03_ic_series_n_below_two_still_insufficient(returns: np.ndarray) -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series
    res = _compute_hac_on_ic_series(_series(returns, 1), horizon=1, maxlags=1)
    assert res["inference_status"] == "insufficient_sample" and not np.isfinite(res["se"])


def test_boundary_04_ic_series_constant_degenerate() -> None:
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series
    res = _compute_hac_on_ic_series(np.full(7, 0.01), horizon=1, maxlags=1)
    assert res["inference_status"] == "degenerate", "零變異仍為退化，不得以警示造值"


@pytest.mark.parametrize("lag", [1, 5, 6, 7])
def test_boundary_05_validator_entry_small_n_computes_with_warning(returns: np.ndarray, lag: int) -> None:
    from momentum.Analysis import statistical_validator as sv
    x = pd.Series(returns[:8], name="ret_lag1").shift(1).iloc[1:].reset_index(drop=True)
    y = pd.Series(returns[1:8]).reset_index(drop=True)
    out = sv.compute_hac_ic_statistics(pd.DataFrame({"ret_lag1": x}), y, horizon=1, method="spearman",
                                       alpha=0.05, maxlags=lag)["ret_lag1"]
    assert out["inference_status"] == "ok", f"n=7、L={lag} 須照常出值"
    z, se_factor = sv._method_contribution("spearman", x.to_numpy(dtype=float), y.to_numpy(dtype=float))
    assert out["se"] == pytest.approx(_oracle_se(np.asarray(z, dtype=float), lag) * se_factor, rel=1e-10)
    assert out["data_warning"] == "small_sample_fixed_lag"
    detail = out["data_warning_detail"]
    assert D_FIELDS <= set(detail) and detail["n_obs"] == 7 and detail["lag"] == lag


def test_mutation_se_kernel_broken_detected(returns: np.ndarray, monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞 Bartlett 核（SE 乘 2）⇒ boundary_02 之 statsmodels 對照翻紅。"""
    from momentum.Analysis import ic_filter_orchestrator as ifo
    real = ifo._newey_west_bartlett_se
    monkeypatch.setattr(ifo, "_newey_west_bartlett_se", lambda z, lag: 2.0 * real(z, lag))
    with pytest.raises(AssertionError):
        test_boundary_02_ic_series_adequate_n_no_warning(returns)
