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
from collections import OrderedDict
from dataclasses import dataclass
from typing import Optional

import numpy as np
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


#: Imhof 每段求積容差（同改前逐段 scipy quad 之 epsabs／epsrel；SPEC ㊺ v5.80 沿用）
_QUAD_EPSABS = 1e-16
_QUAD_EPSREL = 1e-12
#: 自適應二分層數上限——只作失敗偵測：耗盡即回 (nan, nan)，不以未收斂結果出值（SPEC ㊺ v5.80，r111 CODEX-P1-01）
_QUAD_MAX_DEPTH = 40
#: 每原段片數上限（同改前逐段 scipy quad 之 limit＝200）；逾限即未收斂回 (nan, nan)，並界定最壞片數 400×200
_QUAD_LIMIT = 200
#: 每批被積函數評估之元素上限（段×15 點×特徵值數），控制暫存記憶體（約 8 bytes × 此值 × 數個暫存陣列）
_QUAD_CHUNK_ELEMS = 2_000_000

# QUADPACK qk15（Piessens et al. 1983）：Kronrod 15 點節點／權重與內嵌 Gauss 7 點權重
_XGK = np.array([0.991455371120812639206854697526329, 0.949107912342758524526189684047851,
                 0.864864423359769072789712788640926, 0.741531185599394439863864773280788,
                 0.586087235467691130294144845693013, 0.405845151377397166906606412076961,
                 0.207784955007898467600689403773245, 0.0])
_WGK = np.array([0.022935322010529224963732008058970, 0.063092092629978553290700663189204,
                 0.104790010322250183839876322541518, 0.140653259715525918745189590510238,
                 0.169004726639267902826583426598550, 0.190350578064785409913256402421014,
                 0.204432940075298892414161999234649, 0.209482141084727828012999174891714])
_WG = np.array([0.129484966168869693270611432679082, 0.279705391489276667901467771423780,
                0.381830050505118944950369775488975, 0.417959183673469387755102040816327])
#: 15 點（−x₁…−x₇, 0, x₇…x₁ 之對稱排列）與對應 Kronrod／Gauss 權重（Gauss 點＝x₂、x₄、x₆ 與 0，其餘權重 0）
_GK_NODES = np.r_[-_XGK[:-1], _XGK[::-1]]
_GK_WK = np.r_[_WGK[:-1], _WGK[::-1]]
_GK_WG = np.zeros(15)
for _k, _i in enumerate((1, 3, 5, 7)):
    _GK_WG[np.abs(np.abs(_GK_NODES) - _XGK[_i]) == 0.0] = _WG[_k]
del _k, _i


def _imhof_setup(lam_pos: float, lam_neg: np.ndarray) -> Optional[tuple[np.ndarray, float, float]]:
    """正規化特徵值 λ＝(1, −ν/λ₊) 與對數空間求積區間 [v_min, v_max]（同改前：v_min＝−40−ln Σ|λ|，v_max＝max(ln U, 5,
    v_min＋1)，U 取自 Imhof (1961) 式 (3.2) 截斷界 ≤ _TAIL_BOUND）。"""
    nu = np.asarray(lam_neg, dtype=float)
    lam = np.r_[1.0, -nu / lam_pos]
    n = lam.size
    log_abs = np.log(np.abs(lam))
    log_u = (np.log(2.0 / (np.pi * n)) - 0.5 * float(np.sum(log_abs)) - np.log(_TAIL_BOUND)) / (n / 2.0)
    v_min = _V_MIN - float(np.log(np.sum(np.abs(lam))))
    v_max = max(float(log_u), 5.0, v_min + 1.0)
    if not (np.isfinite(v_min) and np.isfinite(v_max)):
        return None
    return lam, v_min, v_max


def _gk15_pieces(lam: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """同一組 λ 之多段 G7K15：回各段 (積分值, QUADPACK dqk15 誤差估計)。被積函數（v＝ln u 空間）
    sin(½Σatan(λu))·exp(−¼Σlog1p((λu)²))·… 之 v 空間形式＝sin θ(u)／ρ(u)（u＝e^v，du/u＝dv）。
    誤差估計照 dqk15：abserr＝|K−G|·h，resasc＞0 時 abserr＝resasc·min(1, (200·abserr／resasc)^{1.5})，再取
    max(50·eps·resabs, abserr)（浮點誤差下限）。按 _QUAD_CHUNK_ELEMS 分批評估以控制暫存記憶體。"""
    centr = 0.5 * (lo + hi)
    hlgth = 0.5 * (hi - lo)
    n_pieces = centr.size
    per = max(1, _QUAD_CHUNK_ELEMS // (15 * max(1, lam.size)))
    resk = np.empty(n_pieces)
    resg = np.empty(n_pieces)
    resabs = np.empty(n_pieces)
    resasc = np.empty(n_pieces)
    for s in range(0, n_pieces, per):
        sl = slice(s, min(n_pieces, s + per))
        v = centr[sl, None] + hlgth[sl, None] * _GK_NODES[None, :]
        lu = np.exp(v)[..., None] * lam
        theta = 0.5 * np.sum(np.arctan(lu), axis=-1)
        log_rho = 0.25 * np.sum(np.log1p(lu * lu), axis=-1)
        f = np.sin(theta) * np.exp(-log_rho)
        k = f @ _GK_WK
        resk[sl] = k
        resg[sl] = f @ _GK_WG
        resabs[sl] = np.abs(f) @ _GK_WK
        resasc[sl] = np.abs(f - 0.5 * k[:, None]) @ _GK_WK
    result = resk * hlgth
    dh = np.abs(hlgth)
    resabs = resabs * dh
    resasc = resasc * dh
    abserr = np.abs((resk - resg) * hlgth)
    with np.errstate(divide="ignore", invalid="ignore"):
        scaled = resasc * np.minimum(1.0, (200.0 * abserr / resasc) ** 1.5)
    abserr = np.where((resasc != 0.0) & (abserr != 0.0), scaled, abserr)
    abserr = np.where(resabs > np.finfo(float).tiny / (50.0 * _EPS), np.maximum(50.0 * _EPS * resabs, abserr), abserr)
    return result, abserr


def _imhof_one(lam: np.ndarray, v_min: float, v_max: float) -> tuple[float, float]:
    """單組 λ 之 Imhof 尾機率：v 空間 400 段均分，每段 G7K15；段之誤差估計 > max(epsabs, epsrel·|值|)·(片寬／原段寬)
    之片二分重評（片內容差按寬度比例分配，使各原段誤差和 ≤ 改前逐段 quad 之容差）。層數耗盡、片寬不再可分
    （浮點停滯）或任何量非有限 ⇒ (nan, nan)。"""
    edges = np.linspace(v_min, v_max, _N_SEGMENTS + 1)
    seg_w = float(edges[1] - edges[0])
    lo, hi = edges[:-1], edges[1:]
    seg = np.arange(_N_SEGMENTS)
    pieces = np.ones(_N_SEGMENTS, dtype=np.int64)  # 每原段目前累計片數（同改前 quad limit＝_QUAD_LIMIT）
    total = 0.0
    err = 0.0
    for _ in range(_QUAD_MAX_DEPTH + 1):
        val, e = _gk15_pieces(lam, lo, hi)
        if not (np.all(np.isfinite(val)) and np.all(np.isfinite(e))):
            return float("nan"), float("nan")
        tol = np.maximum(_QUAD_EPSABS, _QUAD_EPSREL * np.abs(val)) * ((hi - lo) / seg_w)
        ok = e <= tol
        total += float(np.sum(val[ok]))
        err += float(np.sum(e[ok]))
        if ok.all():
            return total, err
        lo_b, hi_b, seg_b = lo[~ok], hi[~ok], seg[~ok]
        mid = 0.5 * (lo_b + hi_b)
        if np.any((mid <= lo_b) | (mid >= hi_b)):
            return float("nan"), float("nan")  # 浮點停滯：片寬已不可再分
        np.add.at(pieces, seg_b, 1)
        if np.any(pieces > _QUAD_LIMIT):
            return float("nan"), float("nan")  # 片數逾限＝未收斂（亦界定最壞記憶體與耗時）
        lo, hi, seg = np.r_[lo_b, mid], np.r_[mid, hi_b], np.r_[seg_b, seg_b]
    return float("nan"), float("nan")  # 層數耗盡＝未收斂


def imhof_upper_tail_batch(lam_pos: float, lam_neg_rows: list) -> list[tuple[float, float]]:
    """多組負特徵值（同一 λ₊）之 Imhof 尾機率 P(λ₊χ²₁ − Σ_j ν_j χ²₁ ≥ 0)，各組獨立求積、各自回 (p̂, ε)
    （SPEC ㊺ v5.80：`slope_pvalue` 之 p̂ 與奇異值擾動上下界同批，各自保留收斂與誤差結果）。"""
    return [imhof_upper_tail(lam_pos, nu) for nu in lam_neg_rows]


def imhof_upper_tail(lam_pos: float, lam_neg: np.ndarray) -> tuple[float, float]:
    """P(λ₊χ²₁ − Σ_j ν_j χ²₁ ≥ 0)（ν_j＞0）以 Imhof 反演公式於對數空間分段求積；回 (p̂, ε)。

    特徵值以 λ₊ 正規化；v＝ln u 於 [v_min, ln U] 均分 400 段，v_min＝−40−ln Σ|λ|（頭段誤差與特徵值量級無關），
    U 取自 Imhof 截斷誤差界 ≤1e−14；頭段 [0, e^{v_min}] 以 ½Σλ·e^{v_min} 計。各段以向量化自適應 Gauss–Kronrod
    G7K15（QUADPACK qk15 節點與權重、dqk15 誤差估計）求積（SPEC ㊺ v5.80，取代逐段 scipy quad；r111 共識）。
    ε＝各段誤差估計和＋截斷界＋頭段量（數值估計、非嚴格誤差界）。未收斂、浮點停滯或任何中間量非有限 ⇒ (nan, nan)。
    """
    nu = np.asarray(lam_neg, dtype=float)
    if not np.isfinite(lam_pos) or lam_pos <= 0.0 or np.any(~np.isfinite(nu)):
        return float("nan"), float("nan")
    if nu.size == 0:
        return 1.0, 0.0
    setup = _imhof_setup(lam_pos, nu)
    if setup is None:
        return float("nan"), float("nan")
    lam, v_min, v_max = setup
    total, err = _imhof_one(lam, v_min, v_max)
    if not (np.isfinite(total) and np.isfinite(err)):
        return float("nan"), float("nan")
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
    # SPEC ㊺ B(3)：μ「每一設計只算一次，與 c 無關、同設計各特徵共用」——依設計快取（b2d BUDGET-12 量測前發現每特徵
    # 重算 O(m³) SVD）
    lam_pos, mu = design_spectrum_cached(x)
    if not np.isfinite(lam_pos) or np.any(~np.isfinite(mu)):
        return PValue(float("nan"), float("nan"), False)
    m = np.asarray(x).size
    delta = m * _EPS
    (p_hat, eps), (p_lo, _), (p_hi, _) = imhof_upper_tail_batch(
        lam_pos, [c2 * mu, c2 * mu * (1.0 + delta) ** 2, c2 * mu * (1.0 - delta) ** 2])
    if not all(np.isfinite(v) for v in (p_hat, eps, p_lo, p_hi)):
        return PValue(float("nan"), float("nan"), False)
    eps_total = eps + max(abs(p_hat - p_lo), abs(p_hat - p_hi))
    reliable = (-eps_total <= p_hat <= 1.0 + eps_total)
    return PValue(float(min(max(p_hat, 0.0), 1.0)), float(eps_total), bool(reliable))


# ── 資料不足警示（SPEC ㊺ B：沿用 ㊹ 判準工具，生成器＝同一設計上之 AR(1)(φ̂_e)） ──────────────────────────

#: 警示模擬之方法鍵（入共同隨機數 seed；與 ㊹ 各 IC 方法之串流分離）
WARNING_METHOD_KEY = "trend_fixedb_b1"
#: 設計快取上限（標準有界 LRU；SPEC ㊺ B(3)）：同請求共用設計之 ic／centrality 維恆為最近使用而命中，ls_spread
#: 每特徵設計本不重用；被淘汰之設計再遇時重算同值（不改任何數值與輸出語意），記憶體與特徵數脫鉤。
DESIGN_CACHE_MAXSIZE = 256
_DESIGN_CACHE: "OrderedDict[bytes, dict]" = OrderedDict()


def _design_key(x: np.ndarray) -> bytes:
    return hashlib.sha256(np.ascontiguousarray(x, dtype=np.float64).tobytes()).digest()


def _design_entry(xv: np.ndarray) -> dict:
    """取（或建）設計之快取條目並標為最近使用；超過 `DESIGN_CACHE_MAXSIZE` 時淘汰最久未用者。"""
    key = _design_key(xv)
    entry = _DESIGN_CACHE.get(key)
    if entry is None:
        entry = {}
        _DESIGN_CACHE[key] = entry
        while len(_DESIGN_CACHE) > DESIGN_CACHE_MAXSIZE:
            _DESIGN_CACHE.popitem(last=False)
    else:
        _DESIGN_CACHE.move_to_end(key)
    return entry


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


def design_spectrum_cached(x: np.ndarray) -> tuple[float, np.ndarray]:
    """:func:`design_spectrum` 之行程內依設計快取（同 `design_median_cached`；快取值與直接計算逐位元相同）。"""
    xv = np.asarray(x, dtype=float)
    cache = _design_entry(xv)
    if "spectrum" not in cache:
        cache["spectrum"] = design_spectrum(xv)
    return cache["spectrum"]


def critical_t2(x: np.ndarray, alpha: float) -> float:
    """同一設計之精確臨界值 c²_α：P(t² ≥ c²_α｜y iid 常態)＝α（Imhof 尾機率對 c² 嚴格遞減，以 brentq 反解）。
    無負根（μ 空）⇒ p 恆為 1 ⇒ 回 +inf（永不拒絕）。根於 u＝ln c² 上夾擠（每步 ×e²，無字面上下限；r106 CODEX-P1-02），
    只有 Imhof 回非有限或 c² 溢位（數值不可算）才回 NaN。"""
    lam_pos, mu = design_spectrum_cached(x)
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
    cache = _design_entry(xv)
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
    cache = _design_entry(xv)
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
    # 不可辨識：殘差自由度 m−2 < 2（m < 4：殘差形狀由設計決定、ρ̂ 與 φ 無關），或同設計中位數函數數值平坦
    # （近共線之設計；r108 GROK-P3-01）——兩者皆 ⇒ persistence_not_estimable
    if not np.isfinite(rho_hat) or m < 4:
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
