"""ICPERF Task 0.4 ㊺ B：趨勢斜率推論（不重疊子序列＋Bartlett fixed-b＋Imhof 精確 p）。

規格：`docs/ICPERF_SPEC.md` Task 0.4 ㊺ 列 B(1)–(4)（v5.78）。

- 不重疊子序列：每值帶來源支撐區間〔起, 迄〕（分析框架之原列位置），自第一個值起貪婪選取「支撐起點大於前一已選
  值支撐迄點」之下一值（:func:`select_nonoverlapping`）。
- 檢定：選取點有限值上 OLS（x＝支撐迄點原列位置、y＝未縮尾原值），標準誤＝Bartlett 核 b＝1 之 score sandwich
  （Kiefer & Vogelsang 2005 fixed-b）：Ω̂＝(2/m²)Σ_{t<m}Ŝ_t²，Var(β̂)＝m·Ω̂／S_xx²（:func:`bartlett_fixedb_slope`）。
- p＝同一設計、y iid 常態之虛無下 P(|t|≥|t_obs|)：B a＝0（a＝x_c／S_xx 在設計列空間、B 由殘差投影構成）⇒
  aa'−c²B 之特徵值解析為 λ₊＝1／S_xx 與 −c²μ_j，μ_j＝(2/m)σ_j(G)²／S_xx²，G＝P L diag(x_c) Q（Q 為 [1, x_c]
  之正交補；:func:`design_spectrum`）；p 以 Imhof (1961) 反演公式於對數空間分段求積（:func:`imhof_upper_tail`），
  附誤差界 ε（求積誤差＋截斷界＋頭段量＋奇異值誤差項）。
- 數值契約：p̂ 不在 [−ε, 1＋ε]、任何中間量非有限、或 [p̂−ε, p̂＋ε] 跨 α ⇒ `p_numeric_unreliable`。

純函式、無 I/O；不依賴 api/。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy import integrate
from scipy.optimize import brentq, isotonic_regression

from momentum.Analysis import hac_ewc as he
from momentum.core.logging import get_logger

logger = get_logger(__name__)

#: 推論狀態封閉值（SPEC ㊺ B(4)）
STATUS_OK = "ok"
STATUS_INSUFFICIENT_POINTS = "insufficient_points"
STATUS_DEGENERATE = "degenerate"
STATUS_CONSTANT_SERIES = "constant_series"
STATUS_SOURCE_UNAVAILABLE = "source_unavailable"
STATUS_BELOW_MIN_SAMPLES = "below_min_samples"
STATUS_P_NUMERIC_UNRELIABLE = "p_numeric_unreliable"
INFERENCE_STATUS_VALUES: frozenset[str] = frozenset(
    {
        STATUS_OK,
        STATUS_INSUFFICIENT_POINTS,
        STATUS_DEGENERATE,
        STATUS_CONSTANT_SERIES,
        STATUS_SOURCE_UNAVAILABLE,
        STATUS_BELOW_MIN_SAMPLES,
        STATUS_P_NUMERIC_UNRELIABLE,
    }
)
#: 推論法字面（輸出 `inference_method`）
INFERENCE_METHOD = "bartlett_fixedb_b1_nonoverlap"

_EPS = float(np.finfo(float).eps)
#: Imhof 對數空間求積之下界 v＝ln u 與分段數（SPEC ㊺ B(3)）
_V_MIN = -40.0
_N_SEGMENTS = 400
#: Imhof 截斷誤差界之目標（尾段 ≤ 此值）
_TAIL_BOUND = 1e-14


@dataclass(frozen=True)
class SlopeFit:
    """OLS 斜率與 Bartlett b＝1 fixed-b 標準誤。"""

    slope: float
    se: float
    t_stat: float


@dataclass(frozen=True)
class PValue:
    """精確 p 與其絕對誤差界；`reliable` 為數值契約是否成立（不含與 α 之比較）。"""

    p: float
    abs_error: float
    reliable: bool


@dataclass(frozen=True)
class TrendInference:
    """單一序列之推論結果（SPEC ㊺ B(5) 推論鍵之來源）。"""

    status: str
    slope: Optional[float]
    se: Optional[float]
    p_value: Optional[float]
    p_abs_error: Optional[float]
    significant: Optional[bool]
    points: int


def select_nonoverlapping(support_start: np.ndarray, support_end: np.ndarray) -> np.ndarray:
    """自第一個值起貪婪選取支撐不交疊之值；回選取值之索引（遞增）。

    `support_start[i]`／`support_end[i]` 為第 i 個值之來源支撐（含兩端之原列位置）；第一個值必選；其後選取
    「支撐起點大於前一已選值支撐迄點」之下一值。同維各特徵共用同一組支撐（呼叫端以共用位置軸呼叫一次）。
    """
    start = np.asarray(support_start, dtype=np.int64)
    end = np.asarray(support_end, dtype=np.int64)
    if start.shape != end.shape or start.ndim != 1:
        raise ValueError("support_start/support_end must be 1-D arrays of equal length")
    if start.size and np.any(end < start):
        raise ValueError("support_end must be >= support_start")
    selected: list[int] = []
    last_end: Optional[int] = None
    for i in range(start.size):
        if last_end is None or start[i] > last_end:
            selected.append(i)
            last_end = int(end[i])
    return np.asarray(selected, dtype=np.int64)


def bartlett_fixedb_slope(x: np.ndarray, y: np.ndarray) -> SlopeFit:
    """OLS 斜率與 Bartlett 核 b＝1 score sandwich 標準誤（累積和形式，O(m)）。

    s_t＝(x_t−x̄)e_t、Ŝ_t＝Σ_{j≤t}s_j；Ω̂＝(2/m²)Σ_{t=1}^{m−1}Ŝ_t²（＝(1/m)Σ_tΣ_u(1−|t−u|/m)s_t s_u）；
    Var(β̂)＝m·Ω̂／S_xx²。S_xx＝0 或 SE 非有限／≤0 時 se、t 為 NaN。
    """
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    m = xv.size
    xc = xv - xv.mean()
    sxx = float(xc @ xc)
    if m < 3 or not np.isfinite(sxx) or sxx <= 0.0:
        return SlopeFit(float("nan"), float("nan"), float("nan"))
    yc = yv - yv.mean()
    slope = float(xc @ yc) / sxx
    resid = yc - slope * xc
    partial = np.cumsum(xc * resid)
    omega = 2.0 / (m * m) * float(np.sum(partial[:-1] ** 2))
    var = m * omega / (sxx * sxx)
    if not np.isfinite(var) or var <= 0.0:
        return SlopeFit(slope, float("nan"), float("nan"))
    se = float(np.sqrt(var))
    return SlopeFit(slope, se, slope / se)


def design_spectrum(x: np.ndarray) -> tuple[float, np.ndarray]:
    """回 (λ₊, μ)：λ₊＝1／S_xx；μ＝(2/m)σ_j(G)²／S_xx²（結構性零根已剔除）。

    G＝P L diag(x_c) Q：L 為下三角全 1、P 刪末列、Q 為 [1, x_c] 之正交補（m×(m−2)）。
    """
    xv = np.asarray(x, dtype=float)
    m = xv.size
    xc = xv - xv.mean()
    sxx = float(xc @ xc)
    basis = np.column_stack([np.ones(m) / np.sqrt(m), xc / np.sqrt(sxx)])
    full_q, _ = np.linalg.qr(basis, mode="complete")
    q = full_q[:, 2:]
    g = np.cumsum(xc[:, None] * q, axis=0)[:-1, :]
    sigma = np.linalg.svd(g, compute_uv=False)
    if sigma.size == 0:
        return 1.0 / sxx, np.empty(0)
    keep = sigma > m * _EPS * sigma.max() if sigma.max() > 0 else np.zeros_like(sigma, dtype=bool)
    mu = (2.0 / m) * sigma[keep] ** 2 / (sxx * sxx)
    return 1.0 / sxx, mu


def imhof_upper_tail(lam_pos: float, lam_neg: np.ndarray) -> tuple[float, float]:
    """P(λ₊χ²₁ − Σ_j ν_j χ²₁ ≥ 0)（ν_j＞0）以 Imhof 反演公式於對數空間分段求積；回 (p̂, ε)。

    特徵值以 λ₊ 正規化；v＝ln u 於 [v_min, ln U] 均分 400 段，v_min＝−40−ln Σ|λ|（頭段誤差與特徵值量級無關），
    U 取自 Imhof 截斷誤差界 ≤1e−14；頭段 [0, e^{v_min}] 以 ½Σλ·e^{v_min} 計。ε＝各段求積誤差估計和＋截斷界＋頭段量。
    任何中間量非有限 ⇒ 回 (nan, nan)。
    """
    nu = np.asarray(lam_neg, dtype=float)
    if not np.isfinite(lam_pos) or lam_pos <= 0.0 or np.any(~np.isfinite(nu)):
        return float("nan"), float("nan")
    if nu.size == 0:
        return 1.0, 0.0
    lam = np.r_[1.0, -nu / lam_pos]
    n = lam.size
    log_abs = np.log(np.abs(lam))
    # Imhof (1961) 式 (3.2)：∫_U^∞ |·| ≤ 2／(π n U^{n/2} Π|λ_j|^{1/2})
    log_u = (np.log(2.0 / (np.pi * n)) - 0.5 * float(np.sum(log_abs)) - np.log(_TAIL_BOUND)) / (n / 2.0)
    v_max = max(float(log_u), 5.0)
    # 頭段 [0, e^{v_min}]：u→0 時 v 空間被積函數≈½Σλ·u，取 v_min 使 Σ|λ|·e^{v_min}＝e^{−40}
    v_min = _V_MIN - float(np.log(np.sum(np.abs(lam))))
    v_max = max(v_max, v_min + 1.0)

    def integrand(v: float) -> float:
        u = np.exp(v)
        theta = 0.5 * float(np.sum(np.arctan(lam * u)))
        log_rho = 0.25 * float(np.sum(np.log1p((lam * u) ** 2)))
        return float(np.sin(theta) * np.exp(-log_rho))

    edges = np.linspace(v_min, v_max, _N_SEGMENTS + 1)
    total = 0.0
    err = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        val, e = integrate.quad(integrand, lo, hi, limit=200, epsabs=1e-16, epsrel=1e-12)
        total += val
        err += abs(e)
    head = 0.5 * float(np.sum(lam)) * float(np.exp(v_min))
    p_hat = 0.5 + (total + head) / np.pi
    eps = (err + abs(head)) / np.pi + _TAIL_BOUND
    if not (np.isfinite(p_hat) and np.isfinite(eps)):
        return float("nan"), float("nan")
    return float(p_hat), float(eps)


def slope_pvalue(x: np.ndarray, t_obs: float) -> PValue:
    """同一設計、y iid 常態之虛無下 P(|t|≥|t_obs|)，含奇異值誤差項之誤差界與數值契約。"""
    if not np.isfinite(t_obs):
        return PValue(float("nan"), float("nan"), False)
    with np.errstate(over="ignore"):
        c2 = float(np.square(np.float64(t_obs)))
    if not np.isfinite(c2):
        return PValue(float("nan"), float("nan"), False)
    if c2 == 0.0:
        return PValue(1.0, 0.0, True)
    lam_pos, mu = design_spectrum(x)
    if not np.isfinite(lam_pos) or np.any(~np.isfinite(mu)):
        return PValue(float("nan"), float("nan"), False)
    p_hat, eps = imhof_upper_tail(lam_pos, c2 * mu)
    m = np.asarray(x).size
    delta = m * _EPS
    p_lo, _ = imhof_upper_tail(lam_pos, c2 * mu * (1.0 + delta) ** 2)
    p_hi, _ = imhof_upper_tail(lam_pos, c2 * mu * (1.0 - delta) ** 2)
    if not all(np.isfinite(v) for v in (p_hat, eps, p_lo, p_hi)):
        return PValue(float("nan"), float("nan"), False)
    eps_total = eps + max(abs(p_hat - p_lo), abs(p_hat - p_hi))
    reliable = (-eps_total <= p_hat <= 1.0 + eps_total)
    return PValue(float(min(max(p_hat, 0.0), 1.0)), float(eps_total), bool(reliable))


# ── 資料不足警示（SPEC ㊺ B：沿用 ㊹ 判準工具，生成器＝同一設計上之 AR(1)(φ̂_e)） ──────────────────────────

#: 警示模擬之方法鍵（入共同隨機數 seed；與 ㊹ 各 IC 方法之串流分離）
WARNING_METHOD_KEY = "trend_fixedb_b1"
_DESIGN_CACHE: dict[bytes, dict] = {}


def _design_key(x: np.ndarray) -> bytes:
    return hashlib.sha256(np.ascontiguousarray(x, dtype=np.float64).tobytes()).digest()


def _ols_residual_rows(xc: np.ndarray, sxx: float, y: np.ndarray) -> np.ndarray:
    yc = y - y.mean(axis=1, keepdims=True)
    slope = (yc @ xc) / sxx
    return yc - slope[:, None] * xc[None, :]


def fixedb_t2_rows(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """逐列 :func:`bartlett_fixedb_slope` 之 t²（向量化；SE 非有限／≤0 ⇒ NaN）。"""
    xv = np.asarray(x, dtype=float)
    m = xv.size
    xc = xv - xv.mean()
    sxx = float(xc @ xc)
    yc = y - y.mean(axis=1, keepdims=True)
    slope = (yc @ xc) / sxx
    resid = yc - slope[:, None] * xc[None, :]  # 同 _ols_residual_rows；slope 另需用於 t
    partial = np.cumsum(xc[None, :] * resid, axis=1)
    omega = 2.0 / (m * m) * np.sum(partial[:, :-1] ** 2, axis=1)
    var = m * omega / (sxx * sxx)
    with np.errstate(divide="ignore", invalid="ignore"):
        t2 = slope * slope / var
    t2[~(np.isfinite(var) & (var > 0.0))] = np.nan
    return t2


def critical_t2(x: np.ndarray, alpha: float) -> float:
    """同一設計之精確臨界值 c²_α：P(t² ≥ c²_α｜y iid 常態)＝α（Imhof 尾機率對 c² 嚴格遞減，以 brentq 反解）。
    無負根（μ 空）⇒ p 恆為 1 ⇒ 回 +inf（永不拒絕）。根於 u＝ln c² 上夾擠（每步 ×e²，無字面上下限；r106 CODEX-P1-02），
    只有 Imhof 回非有限或 c² 溢位（數值不可算）才回 NaN。"""
    lam_pos, mu = design_spectrum(x)
    if mu.size == 0:
        return float("inf")

    def g(u: float) -> float:
        with np.errstate(over="ignore"):
            c2 = float(np.exp(np.float64(u)))
        p = imhof_upper_tail(lam_pos, c2 * mu)[0] if np.isfinite(c2) else float("nan")
        return p - alpha

    lo = hi = 0.0
    g_hi = g(hi)
    while np.isfinite(g_hi) and g_hi > 0.0:  # p(c²) 仍 > α ⇒ 上移
        lo, hi = hi, hi + 2.0
        g_hi = g(hi)
    if not np.isfinite(g_hi):
        return float("nan")
    if hi == 0.0:  # p(1) ≤ α ⇒ 下移找 p > α 之下界
        g_lo = g(lo)
        while np.isfinite(g_lo) and g_lo <= 0.0:
            hi, lo = lo, lo - 2.0
            g_lo = g(lo)
        if not np.isfinite(g_lo):
            return float("nan")
    return float(np.exp(brentq(g, lo, hi, xtol=1e-13, rtol=1e-14)))


def _design_median_function(x: np.ndarray) -> np.ndarray:
    """Andrews (1993) 中位數函數之同設計版：AR(1)(φ) 於 PHI_GRID 各點、MEDIAN_FUNCTION_REPLICATIONS 條（㊹ 校準串流），
    對同一設計 [1, x] 之 OLS 殘差估含截距 LS ρ̂，取中位數後 isotonic 投影（弱遞增）。"""


    xv = np.asarray(x, dtype=float)
    m = xv.size
    xc = xv - xv.mean()
    sxx = float(xc @ xc)
    R = he.MEDIAN_FUNCTION_REPLICATIONS
    seed = he.median_function_seed()
    rho = np.empty((len(he.PHI_GRID), R))
    r1 = 0
    while r1 < R:
        r0 = r1
        r1 = min(r0 + he._rows_per_chunk(m, 0), R)
        e = he._feature_innovations(seed, r0, r1, m)
        for k, phi in enumerate(he.PHI_GRID):
            rho[k, r0:r1] = he.ls_ar1_coefficient_rows(_ols_residual_rows(xc, sxx, he._ar1_rows(e, phi)))
    med = np.median(rho, axis=1)
    return np.asarray(isotonic_regression(med, increasing=True).x, dtype=float)


def _reject_rows(x: np.ndarray, point: object, c2: float) -> np.ndarray:
    """同設計、共同隨機數（seed＝(1, WARNING_METHOD_KEY)）之 R 條虛無模擬拒絕指示（t² ≥ c²；NaN 不拒絕）。"""

    m = np.asarray(x).size
    phi = he.REFERENCE_RHO if point == he.REFERENCE_POINT else float(point)
    seed = he.simulation_seed(1, WARNING_METHOD_KEY)
    R = he.WARNING_SIM_REPLICATIONS
    out = np.empty(R)
    r1 = 0
    while r1 < R:
        r0 = r1
        r1 = min(r0 + he._rows_per_chunk(m, 0), R)
        t2 = fixedb_t2_rows(x, he._ar1_rows(he._feature_innovations(seed, r0, r1, m), phi))
        with np.errstate(invalid="ignore"):
            out[r0:r1] = (t2 >= c2).astype(float)
    return out


def trend_warning_statistics(x: np.ndarray, resid_rho_hat: float, alpha: float) -> dict:
    """配對差（同 ㊹ `warning_statistics`，單一設計故無 n 節點內插）：D_r＝(1−w)I_lo＋w·I_hi − J；Δ＝mean(D)、
    s＝sqrt(Σ(D−Δ)²／(R(R−1)))；φ̂＝同設計中位數函數之左廣義逆。"""

    xv = np.asarray(x, dtype=float)
    cache = _DESIGN_CACHE.setdefault(_design_key(xv), {})
    phi_hat = he._left_inverse(design_median_cached(xv), float(resid_rho_hat))
    ckey = ("c2", float(alpha))
    if ckey not in cache:
        cache[ckey] = critical_t2(xv, float(alpha))
    c2 = cache[ckey]
    if not np.isfinite(c2) and c2 != float("inf"):
        raise FloatingPointError("critical value not computable")

    def rej(point: object) -> np.ndarray:
        k = ("rej", point, float(alpha))
        if k not in cache:
            cache[k] = _reject_rows(xv, point, c2)
        return cache[k]

    plo, phi_, wp = he.phi_bracket(phi_hat)
    i_lo = rej(plo)
    i_node = i_lo if wp == 0.0 else (1.0 - wp) * i_lo + wp * rej(phi_)
    j = rej(he.REFERENCE_POINT)
    R = he.WARNING_SIM_REPLICATIONS
    d = i_node - j
    delta = float(d.mean())
    se = float(np.sqrt(float(((d - delta) ** 2).sum()) / (R * (R - 1))))
    return {"r_hat": float(i_node.mean()), "r_ref": float(j.mean()), "delta": delta, "se": se,
            "phi_hat": phi_hat, "warn": he.paired_warning(delta, se)}


#: 同設計中位數函數之全距 ≤ 此值 ⇒ 殘差之 ρ̂ 與 φ 無關、持續性不可由此設計辨識（如選取 3 點：殘差僅 1 自由度、形狀由設計
#: 決定，ρ̂ 恆為設計常數）；依資料判定、不設點數門檻（r106 收據 L.deep_analysis 中心性維實例）
MEDIAN_FLAT_TOL = 1e-12


def design_median_cached(x: np.ndarray) -> np.ndarray:
    """同設計中位數函數（行程內依設計快取）。"""
    xv = np.asarray(x, dtype=float)
    cache = _DESIGN_CACHE.setdefault(_design_key(xv), {})
    if "median" not in cache:
        cache["median"] = _design_median_function(xv)
    return cache["median"]


def trend_data_warning(x: np.ndarray, y: np.ndarray, alpha: float) -> dict:
    """SPEC ㊺ B 資料不足警示：受檢序列＝選取點有限值之 OLS 殘差（依 x 序）之含截距 LS ρ̂；回
    {data_warning, data_warning_detail}（封閉值同 ㊹：None／small_effective_sample／persistence_not_estimable／
    warning_not_evaluated；detail 鍵同 ㊹ 八鍵，選取點不重疊 ⇒ horizon＝1、approx_independent_n＝點數）。"""

    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    finite = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[finite], yv[finite]
    m = int(xv.size)
    xc = xv - xv.mean()
    sxx = float(xc @ xc)
    rho_hat = he.ls_ar1_coefficient(_ols_residual_rows(xc, sxx, yv[None, :])[0]) if m >= 3 and sxx > 0 else np.nan
    if not np.isfinite(rho_hat):
        return {"data_warning": "persistence_not_estimable", "data_warning_detail": None}
    try:
        if float(np.ptp(design_median_cached(xv))) <= MEDIAN_FLAT_TOL:
            return {"data_warning": "persistence_not_estimable", "data_warning_detail": None}
        st = trend_warning_statistics(xv, rho_hat, alpha)
    except MemoryError as exc:
        logger.warning("趨勢資料不足警示未執行（記憶體不足，可重跑）：%s", exc)
        return {"data_warning": "warning_not_evaluated", "data_warning_detail": None}
    except FloatingPointError as exc:
        logger.warning("趨勢資料不足警示未執行（臨界值不可算）：%s", exc)
        return {"data_warning": "warning_not_evaluated", "data_warning_detail": None}
    if not st["warn"]:
        return {"data_warning": None, "data_warning_detail": None}
    return {
        "data_warning": "small_effective_sample",
        "data_warning_detail": {
            "n_obs": m,
            "horizon": 1,
            "approx_independent_n": float(m),
            "phi_hat": float(st["phi_hat"]),
            "alpha": float(alpha),
            "estimated_null_reject_rate": float(st["r_hat"]),
            "reference_reject_rate": float(st["r_ref"]),
            "replications": int(he.WARNING_SIM_REPLICATIONS),
        },
    }


def infer_trend(x: np.ndarray, y: np.ndarray, alpha: float) -> TrendInference:
    """選取點（已為不重疊子序列）上之推論與封閉狀態（SPEC ㊺ B(3)(4)）。

    `x`、`y` 為選取點之原列位置與未縮尾原值（可含非有限 y，於此剔除）。`min_samples` 與 `source_unavailable`
    由呼叫端判定。
    """
    xv = np.asarray(x, dtype=float)
    yv = np.asarray(y, dtype=float)
    finite = np.isfinite(xv) & np.isfinite(yv)
    xv = xv[finite]
    yv = yv[finite]
    m = int(xv.size)
    if m < 3:
        return TrendInference(STATUS_INSUFFICIENT_POINTS, None, None, None, None, None, m)
    if np.all(yv == yv[0]):
        return TrendInference(STATUS_CONSTANT_SERIES, 0.0, None, None, None, False, m)
    fit = bartlett_fixedb_slope(xv, yv)
    if not (np.isfinite(fit.slope) and np.isfinite(fit.se) and fit.se > 0.0):
        return TrendInference(STATUS_DEGENERATE, None, None, None, None, None, m)
    pv = slope_pvalue(xv, fit.t_stat)
    if not pv.reliable:
        return TrendInference(STATUS_P_NUMERIC_UNRELIABLE, fit.slope, fit.se, None, None, None, m)
    if pv.p + pv.abs_error <= alpha:
        significant: Optional[bool] = True
    elif pv.p - pv.abs_error > alpha:
        significant = False
    else:
        return TrendInference(STATUS_P_NUMERIC_UNRELIABLE, fit.slope, fit.se, pv.p, pv.abs_error, None, m)
    return TrendInference(STATUS_OK, fit.slope, fit.se, pv.p, pv.abs_error, significant, m)
