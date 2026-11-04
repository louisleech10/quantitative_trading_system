"""縱向第 5 段顯著性：逐方法貢獻序列、LLSW 2018 等權餘弦（EWC）檢定、資料不足警示模擬（ICPERF SPEC v5.63 ㊹）。

出處：Lazarus, Lewis, Stock, Watson (2018) "HAR Inference: Recommendations for Practice", JBES 36(4):541–559。
- ν＝⌊0.4·n^(2/3)⌋；Λ_j＝中心化貢獻序列之 DCT-II（ortho）第 j 係數，j＝1..ν；Ω＝(1/ν)·Σ Λ_j²；
  t＝mean(e)／(因子·sqrt(Ω/n))；p＝2·t_ν.sf(|t|)。參數照原文、不另加上下限。
- Kendall 貢獻＝Hájek 投影 h_i＝(1/(n−1))·Σ_j sign(x_i−x_j)·sign(y_i−y_j)，SE 因子 2（Dehling–Vogel–Wendler–Wied 2017）。
- 資料不足警示（SPEC v5.64）：依實際 n_obs、h、方法、α 與特徵持續性（含截距 AR(1) 最小平方 ρ̂ 經 Andrews 1993
  中位數不偏反演得 φ̂）以共同隨機數模擬估虛無拒絕率 r̂，對照 z 為 AR(1) ρ＝0.7（LLSW 設計邊界）之 r̂_ref，
  以配對差之 2 個標準誤判定；只警示、不改 p／q／門檻；無樣本數或 horizon 上限，n 節點與 φ 網格只為共用計算。
"""

from __future__ import annotations

import hashlib
import math
from fractions import Fraction
from typing import Dict, Optional, Tuple, Union

import numpy as np
from numba import njit
from scipy import fft as _fft
from scipy import signal as _signal
from scipy import stats

#: 模擬次數（SPEC ㊹ 產品常數；`data_warning_detail.replications` 記所用值）。
WARNING_SIM_REPLICATIONS = 1000
#: Andrews (1993) 中位數函數之模擬次數（SPEC v5.65 產品常數）。
MEDIAN_FUNCTION_REPLICATIONS = 1000
#: LLSW 2018 之 ν 係數（以有理數存，ν 以整數不等式精確求得，免浮點於整數邊界誤差）。
EWC_NU_COEF = Fraction(2, 5)
#: Kendall 投影之 SE 因子（U 統計量投影之變異數因子）。
KENDALL_SE_FACTOR = 2.0
#: LLSW 設計邊界：z 為 Gaussian AR(1) ρ＝0.7。
REFERENCE_RHO = 0.7
#: φ 網格：兩端點＝φ̂（acf 一階）數學值域之端點；只為共用計算，非使用範圍限制。
PHI_GRID: Tuple[float, ...] = (
    -1.0, -0.999, -0.99, -0.9, -0.5, 0.0, 0.5, 0.9, 0.95, 0.99, 0.995, 0.999, 0.9999, 0.99999, 1.0,
)
#: n 幾何節點＝round(NODE_BASE·NODE_GROWTH^k)，k 為整數，隨實際 n_obs 隨需產生、無範圍限制。
NODE_BASE = 8
NODE_GROWTH = 1.05
#: 分塊：每列約佔用之 float64 陣列份數（創新、特徵、報酬、標籤、排名／投影、貢獻、DCT 等之保守估計）。
_ARRAYS_PER_ROW = 10

ReferencePoint = str
SimPoint = Union[float, ReferencePoint]
REFERENCE_POINT: ReferencePoint = "ref"

_NULL_PVALUE_CACHE: Dict[Tuple[int, int, str, SimPoint], np.ndarray] = {}
_LS_MEDIAN_CACHE: Dict[int, np.ndarray] = {}


# ── EWC 檢定 ──────────────────────────────────────────────────────────────


def ewc_dof(n: int) -> int:
    """ν＝⌊EWC_NU_COEF·n^(2/3)⌋，以 k³ ≤ c³·n² 之整數比較精確求得。"""
    n = int(n)
    if n < 1:
        return 0
    c3n2 = EWC_NU_COEF ** 3 * n * n
    k = int(float(EWC_NU_COEF) * n ** (2.0 / 3.0))
    while k > 0 and Fraction(k) ** 3 > c3n2:
        k -= 1
    while Fraction(k + 1) ** 3 <= c3n2:
        k += 1
    return k


def ewc_long_run_variance(e: np.ndarray, nu: int) -> float:
    """Ω＝(1/ν)·Σ_{j=1..ν} Λ_j²，Λ＝中心化序列之 DCT-II（ortho）。"""
    ec = e - float(np.mean(e))
    lam = _fft.dct(ec, type=2, norm="ortho")[1 : nu + 1]
    return float(np.mean(lam * lam))


def ewc_test(z: np.ndarray, se_factor: float = 1.0) -> dict:
    """單一序列之 EWC t 檢定（虛無 mean＝0）。

    Returns:
        t_stat／p_value／se／ewc_dof／inference_status（`ok`／`insufficient_sample`／`degenerate`）
    """
    n = int(z.size)
    nu = ewc_dof(n)
    if nu < 1:
        return {"t_stat": np.nan, "p_value": np.nan, "se": np.nan, "ewc_dof": int(nu),
                "inference_status": "insufficient_sample"}
    omega = ewc_long_run_variance(z, nu)
    if not np.isfinite(omega) or omega <= 0.0:
        return {"t_stat": np.nan, "p_value": np.nan, "se": np.nan, "ewc_dof": int(nu),
                "inference_status": "degenerate"}
    se = float(se_factor * math.sqrt(omega / n))
    t_stat = float(np.mean(z)) / se
    p_value = float(2.0 * stats.t.sf(abs(t_stat), df=nu))
    return {"t_stat": t_stat, "p_value": p_value, "se": se, "ewc_dof": int(nu), "inference_status": "ok"}


# ── 逐方法貢獻序列 ─────────────────────────────────────────────────────────


def pearson_contribution_z(x: np.ndarray, y: np.ndarray) -> Optional[np.ndarray]:
    """z＝zscore(x)·zscore(y)（ddof=1）；一側常數回 None。"""
    if x.size < 2 or y.size < 2 or x.size != y.size:
        return None
    sx = float(np.std(x, ddof=1))
    sy = float(np.std(y, ddof=1))
    if sx == 0.0 or sy == 0.0 or not np.isfinite(sx) or not np.isfinite(sy):
        return None
    return ((x - float(np.mean(x))) / sx) * ((y - float(np.mean(y))) / sy)


@njit(cache=True)
def _dense_rank(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    r = np.empty(a.size, np.int64)
    cur = 0
    for k in range(a.size):
        if k == 0 or a[order[k]] != a[order[k - 1]]:
            cur += 1
        r[order[k]] = cur
    return r


@njit(cache=True)
def _bit_query(tree: np.ndarray, i: int) -> int:
    s = 0
    while i > 0:
        s += tree[i]
        i -= i & (-i)
    return s


@njit(cache=True)
def _bit_add(tree: np.ndarray, i: int) -> None:
    m = tree.size - 1
    while i <= m:
        tree[i] += 1
        i += i & (-i)


@njit(cache=True)
def _kendall_projection_numba(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """h_i＝(1/(n−1))·Σ_{j≠i} sign(x_i−x_j)·sign(y_i−y_j)；並列之 sign＝0。排序＋Fenwick 樹，O(n log n)。

    兩趟：x 遞增時以先前（x 嚴格較小）者計 (y 較小 − y 較大)；x 遞減時以先前（x 嚴格較大）者計 (y 較大 − y 較小)。
    同 x 值之群組先全部查詢、再全部插入，使群組內彼此不計。
    """
    n = x.size
    ry = _dense_rank(y)
    m = 0
    for k in range(n):
        if ry[k] > m:
            m = ry[k]
    acc = np.zeros(n, np.int64)
    order = np.argsort(x, kind="mergesort")
    for direction in range(2):
        tree = np.zeros(m + 1, np.int64)
        inserted = 0
        pos = 0
        while pos < n:
            idx0 = order[pos] if direction == 0 else order[n - 1 - pos]
            end = pos
            while end < n:
                idx = order[end] if direction == 0 else order[n - 1 - end]
                if x[idx] != x[idx0]:
                    break
                end += 1
            for k in range(pos, end):
                i = order[k] if direction == 0 else order[n - 1 - k]
                below = _bit_query(tree, ry[i] - 1)
                above = inserted - _bit_query(tree, ry[i])
                if direction == 0:
                    acc[i] += below - above
                else:
                    acc[i] += above - below
            for k in range(pos, end):
                i = order[k] if direction == 0 else order[n - 1 - k]
                _bit_add(tree, ry[i])
                inserted += 1
            pos = end
    out = np.empty(n, np.float64)
    for i in range(n):
        out[i] = acc[i] / (n - 1)
    return out


def kendall_projection_h(x: np.ndarray, y: np.ndarray) -> Optional[np.ndarray]:
    """Kendall Hájek 投影 h（mean(h)＝τ_a）；n < 2 回 None。"""
    if x.size < 2 or y.size < 2 or x.size != y.size:
        return None
    return _kendall_projection_numba(np.ascontiguousarray(x, dtype=np.float64),
                                     np.ascontiguousarray(y, dtype=np.float64))


# ── 資料不足警示：模擬 ─────────────────────────────────────────────────────


def _node_value(k: int) -> int:
    return int(math.floor(NODE_BASE * NODE_GROWTH ** k + 0.5))


def node_bracket(n_obs: int) -> Tuple[int, int]:
    """n_obs 所在相鄰幾何節點（下, 上）；n_obs 恰為節點時兩者相同。"""
    n = int(n_obs)
    if n < 1:
        raise ValueError(f"n_obs must be >= 1, got {n_obs}")
    k = int(math.floor(math.log(n / NODE_BASE) / math.log(NODE_GROWTH)))
    while _node_value(k) > n:
        k -= 1
    while _node_value(k + 1) <= n:
        k += 1
    lo = _node_value(k)
    if lo == n:
        return n, n
    return lo, _node_value(k + 1)


def phi_bracket(phi: float) -> Tuple[float, float, float]:
    """φ̂ 所在相鄰網格點與內插權重 w（值＝(1−w)·r(lo)＋w·r(hi)）。φ̂ 須在 [−1, 1]。"""
    p = float(phi)
    if not np.isfinite(p) or p < PHI_GRID[0] or p > PHI_GRID[-1]:
        raise ValueError(f"phi_hat must be finite and within [-1, 1], got {phi}")
    for i in range(len(PHI_GRID) - 1):
        lo, hi = PHI_GRID[i], PHI_GRID[i + 1]
        if p == lo:
            return lo, lo, 0.0
        if lo < p < hi:
            return lo, hi, (p - lo) / (hi - lo)
    return PHI_GRID[-1], PHI_GRID[-1], 0.0


def simulation_seed(horizon: int, method: str) -> int:
    """共同隨機數之 seed＝SHA-256(h, 方法) 之前 8 位元組（α、n 節點、φ 點皆不入 seed）。"""
    key = f"{int(horizon)}|{method}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


#: 串流編號：第 r 條模擬之特徵創新與報酬創新各為 (seed, r, 串流編號) 之獨立串流（各 n 節點取前綴）。
_STREAM_FEATURE = 0
_STREAM_RETURN = 1


def _feature_innovations(seed: int, r0: int, r1: int, node: int) -> np.ndarray:
    e = np.empty((r1 - r0, node))
    for i, r in enumerate(range(r0, r1)):
        e[i] = np.random.default_rng([seed, r, _STREAM_FEATURE]).standard_normal(node)
    return e


def _return_innovations(seed: int, r0: int, r1: int, length: int) -> np.ndarray:
    ret = np.empty((r1 - r0, length))
    for i, r in enumerate(range(r0, r1)):
        ret[i] = np.random.default_rng([seed, r, _STREAM_RETURN]).standard_normal(length)
    return ret


def _ar1_rows(e: np.ndarray, phi: float) -> np.ndarray:
    """AR(1)：|φ| < 1 以平穩分布起始；φ＝±1 以 x₀＝ε₀ 起始之隨機漫步／交錯隨機漫步。"""
    e = e.copy()
    if abs(phi) < 1.0:
        e[:, 0] = e[:, 0] / math.sqrt(1.0 - phi * phi)
    return _signal.lfilter([1.0], [1.0, -phi], e, axis=1)


def ls_ar1_coefficient_rows(x: np.ndarray) -> np.ndarray:
    """含截距 AR(1) 之最小平方估計 ρ̂（逐列）：Σ(x_{t−1}−x̄₀)(x_t−x̄₁)／Σ(x_{t−1}−x̄₀)²（Andrews 1993 之統計量）。"""
    a, b = x[:, :-1], x[:, 1:]
    ac = a - a.mean(axis=1, keepdims=True)
    bc = b - b.mean(axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (ac * bc).sum(axis=1) / (ac * ac).sum(axis=1)


def ls_ar1_coefficient(x: np.ndarray) -> float:
    """單一序列之含截距 AR(1) 最小平方估計 ρ̂；長度 < 3 或滯後段常數回 NaN。"""
    x = np.asarray(x, dtype=float)
    if x.size < 3:
        return float("nan")
    return float(ls_ar1_coefficient_rows(x[None, :])[0])


class WarningSimulationMemoryError(MemoryError):
    """當下可用記憶體不足以模擬單列（可重試；警示判定記為未執行，p／q 照常）。"""


def _rows_per_chunk(n: int, horizon: int) -> int:
    """每塊列數依**當下可用記憶體**（`psutil.virtual_memory().available` 之 1／4）決定，每塊開始前重新評估；
    只決定分塊，不截斷資料、不限 n。單列估計（(2n＋h)·8·_ARRAYS_PER_ROW 位元組，n＝500,000 約 80 MB）超過當下可用量
    ⇒ `WarningSimulationMemoryError`（不強行配置）。"""
    import psutil

    per_row = (2 * n + horizon) * 8 * _ARRAYS_PER_ROW
    available = int(psutil.virtual_memory().available)
    if per_row > available:
        raise WarningSimulationMemoryError(
            f"warning simulation needs ~{per_row} bytes per replication (n={n}, h={horizon}); available {available}")
    return max(1, min(WARNING_SIM_REPLICATIONS, (available // 4) // max(per_row, 1)))


def _rank_rows(a: np.ndarray) -> np.ndarray:
    return np.argsort(np.argsort(a, axis=1, kind="mergesort"), axis=1, kind="mergesort").astype(np.float64)


def _zscore_rows(a: np.ndarray) -> np.ndarray:
    return (a - a.mean(axis=1, keepdims=True)) / a.std(axis=1, ddof=1, keepdims=True)


def _ewc_pvalues_rows(z: np.ndarray, se_factor: float) -> np.ndarray:
    n = z.shape[1]
    nu = ewc_dof(n)
    if nu < 1:
        return np.full(z.shape[0], np.nan)
    zc = z - z.mean(axis=1, keepdims=True)
    lam = _fft.dct(zc, type=2, norm="ortho", axis=1)[:, 1 : nu + 1]
    omega = (lam * lam).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        t = z.mean(axis=1) / (se_factor * np.sqrt(omega / n))
    p = 2.0 * stats.t.sf(np.abs(t), df=nu)
    p[~(np.isfinite(omega) & (omega > 0.0))] = np.nan
    return p


def _simulate_chunk(node: int, horizon: int, method: str, point: SimPoint, seed: int,
                    r0: int, r1: int) -> np.ndarray:
    rows = r1 - r0
    e = _feature_innovations(seed, r0, r1, node)
    if point == REFERENCE_POINT:
        z = _ar1_rows(e, REFERENCE_RHO)  # 參照：同一特徵創新建 z 之 AR(1) ρ＝0.7
        return _ewc_pvalues_rows(z, 1.0)
    x = _ar1_rows(e, float(point))
    ret = _return_innovations(seed, r0, r1, node + horizon)
    cs = np.concatenate([np.zeros((rows, 1)), np.cumsum(ret, axis=1)], axis=1)
    y = cs[:, 1 + horizon : node + 1 + horizon] - cs[:, 1 : node + 1]  # y_t＝Σ_{s=t+1}^{t+h} r_s
    if method == "kendall":
        z = np.empty((rows, node))
        for i in range(rows):
            z[i] = _kendall_projection_numba(x[i], y[i])
        return _ewc_pvalues_rows(z, KENDALL_SE_FACTOR)
    if method == "spearman":
        x, y = _rank_rows(x), _rank_rows(y)
    elif method != "pearson":
        raise ValueError(f"unknown IC method: {method!r}")
    return _ewc_pvalues_rows(_zscore_rows(x) * _zscore_rows(y), 1.0)


def simulate_null_pvalues(node: int, horizon: int, method: str, point: SimPoint, *,
                          rows_per_chunk: Optional[int] = None) -> np.ndarray:
    """(n 節點, h, 方法, φ 網格點或參照) 之 R 個虛無 EWC p 值（行程內快取；隨機流按序號確定、與分塊無關）。"""
    key = (int(node), int(horizon), str(method), point)
    if rows_per_chunk is None and key in _NULL_PVALUE_CACHE:
        return _NULL_PVALUE_CACHE[key]
    seed = simulation_seed(horizon, method)
    parts = []
    r0 = 0
    while r0 < WARNING_SIM_REPLICATIONS:  # 每塊開始前重新評估可用記憶體（v5.68）
        chunk = rows_per_chunk if rows_per_chunk is not None else _rows_per_chunk(int(node), int(horizon))
        r1 = min(r0 + chunk, WARNING_SIM_REPLICATIONS)
        parts.append(_simulate_chunk(int(node), int(horizon), str(method), point, seed, r0, r1))
        r0 = r1
    p = np.concatenate(parts)
    if rows_per_chunk is None:
        _NULL_PVALUE_CACHE[key] = p
    return p


def reject_rate(pvalues: np.ndarray, alpha: float) -> float:
    """α 後置：同一批虛無 p 值之拒絕率（NaN 計為不拒絕）。"""
    return float(np.count_nonzero(pvalues <= alpha) / WARNING_SIM_REPLICATIONS)


# ── Andrews (1993) 中位數不偏 φ̂ ───────────────────────────────────────────


def median_function_seed() -> int:
    """中位數函數校準之固定 seed（與 h、方法及警示模擬之 seed 無關；同一特徵之 φ̂ 不隨請求改變）。"""
    return int.from_bytes(hashlib.sha256(b"andrews1993-median-function").digest()[:8], "big")


def ls_ar1_raw_medians(node: int) -> np.ndarray:
    """中位數函數之模擬估計 m(φ)＝median(ρ̂｜AR(1) φ)，於 PHI_GRID 各點（MEDIAN_FUNCTION_REPLICATIONS 條、校準串流）。"""
    key = int(node)
    if key in _LS_MEDIAN_CACHE:
        return _LS_MEDIAN_CACHE[key]
    seed = median_function_seed()
    R = MEDIAN_FUNCTION_REPLICATIONS
    rho = np.empty((len(PHI_GRID), R))
    r1 = 0
    while r1 < R:  # 每塊開始前重新評估可用記憶體（v5.68）
        r0 = r1
        r1 = min(r0 + _rows_per_chunk(int(node), 0), R)
        e = _feature_innovations(seed, r0, r1, int(node))
        for k, phi in enumerate(PHI_GRID):
            rho[k, r0:r1] = ls_ar1_coefficient_rows(_ar1_rows(e, phi))
    med = np.median(rho, axis=1)
    _LS_MEDIAN_CACHE[key] = med
    return med


def ls_ar1_monotone_medians(node: int) -> np.ndarray:
    """m̃：中位數函數之等權 isotonic 回歸投影（PAVA，`scipy.optimize.isotonic_regression`），對 φ 弱遞增。"""
    from scipy.optimize import isotonic_regression

    return np.asarray(isotonic_regression(ls_ar1_raw_medians(node), increasing=True).x, dtype=float)


def median_unbiased_phi(rho_hat: float, n_obs: int) -> float:
    """Andrews (1993) 中位數不偏 φ̂：兩 n 節點之 m̃ 於各網格點對 log n 線性內插得 m̃_{n_obs}；ρ̂ 嚴格大於 m̃(1) ⇒ 1、
    嚴格小於 m̃(−1) ⇒ −1；其餘（含恰等於含端點之平坦段）取左廣義逆 min{φ：m̃(φ) ≥ ρ̂}（網格點間線性內插）。"""
    lo, hi = node_bracket(n_obs)
    med = ls_ar1_monotone_medians(lo)
    if hi != lo:
        w = (math.log(n_obs) - math.log(lo)) / (math.log(hi) - math.log(lo))
        med = (1.0 - w) * med + w * ls_ar1_monotone_medians(hi)
    return _left_inverse(med, float(rho_hat))


def _left_inverse(med: np.ndarray, r: float) -> float:
    """弱遞增 m̃（PHI_GRID 上）之反解：嚴格越界夾至端點；否則 min{φ：m̃(φ) ≥ r}（網格點間線性內插）。"""
    if r > med[-1]:
        return 1.0
    if r < med[0]:
        return -1.0
    k = int(np.argmax(med >= r))  # 首個 m̃_k ≥ r
    if k == 0:
        return float(PHI_GRID[0])
    lo_m, hi_m = med[k - 1], med[k]  # lo_m < r ≤ hi_m
    return float(PHI_GRID[k - 1] + (PHI_GRID[k] - PHI_GRID[k - 1]) * (r - lo_m) / (hi_m - lo_m))


# ── 警示判準：配對差 ───────────────────────────────────────────────────────


def warning_statistics(n_obs: int, horizon: int, method: str, alpha: float, rho_hat: float) -> dict:
    """配對差：D_r＝Σ_j w_j·(I_{r,j} − J_{r,j})（j＝n 節點×φ 角點；φ 角點由 n_obs 處單一中位數不偏 φ̂ 決定、兩節點共用；
    w_j＝log n 權重×φ 權重；J 只依 n 節點），Δ＝mean(D_r)＝r̂ − r̂_ref、s＝sqrt(Σ(D_r−Δ)²／(R(R−1)))。"""
    lo, hi = node_bracket(n_obs)
    nodes = [(lo, 1.0)] if lo == hi else [
        (lo, 1.0 - (math.log(n_obs) - math.log(lo)) / (math.log(hi) - math.log(lo))),
        (hi, (math.log(n_obs) - math.log(lo)) / (math.log(hi) - math.log(lo))),
    ]
    phi_hat = median_unbiased_phi(rho_hat, n_obs)
    plo, phi_, wp = phi_bracket(phi_hat)
    R = WARNING_SIM_REPLICATIONS
    d = np.zeros(R)
    r_hat = r_ref = 0.0
    for node, wn in nodes:
        i_lo = (simulate_null_pvalues(node, horizon, method, plo) <= alpha).astype(float)
        i_node = i_lo if wp == 0.0 else (1.0 - wp) * i_lo + wp * (
            simulate_null_pvalues(node, horizon, method, phi_) <= alpha).astype(float)
        j_node = (simulate_null_pvalues(node, horizon, method, REFERENCE_POINT) <= alpha).astype(float)
        d += wn * (i_node - j_node)
        r_hat += wn * float(i_node.mean())
        r_ref += wn * float(j_node.mean())
    delta = float(d.mean())
    se = float(math.sqrt(float(((d - delta) ** 2).sum()) / (R * (R - 1))))
    return {"r_hat": r_hat, "r_ref": r_ref, "delta": delta, "se": se, "phi_hat": phi_hat,
            "warn": paired_warning(delta, se)}


def paired_warning(delta: float, se: float) -> bool:
    """Δ > 2·s ⇒ 警示；s＝0 時 Δ > 0 即警示。"""
    return delta > 0.0 if se == 0.0 else delta > 2.0 * se


def small_sample_warning(n_obs: int, horizon: int, method: str, alpha: float,
                         rho_hat: float) -> Optional[dict]:
    """資料不足警示之 `data_warning_detail`（封閉八鍵；phi_hat＝n_obs 處之中位數不偏 φ̂）；未觸發回 None。"""
    if not np.isfinite(float(alpha)):
        raise ValueError(f"alpha must be finite, got {alpha}")
    if not np.isfinite(rho_hat):
        return None
    st = warning_statistics(n_obs, horizon, method, float(alpha), float(rho_hat))
    if not st["warn"]:
        return None
    return {
        "n_obs": int(n_obs),
        "horizon": int(horizon),
        "approx_independent_n": float(n_obs) / float(horizon),
        "phi_hat": float(st["phi_hat"]),
        "alpha": float(alpha),
        "estimated_null_reject_rate": float(st["r_hat"]),
        "reference_reject_rate": float(st["r_ref"]),
        "replications": int(WARNING_SIM_REPLICATIONS),
    }
