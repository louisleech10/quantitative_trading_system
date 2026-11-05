"""ICPERF Task 0.4 ㊺：虛無拒絕率與檢定力研究（SPEC v5.78 ㊺ 列驗證 A⑤、B⑥、B⑦）。

重型（背景、共用監看、估時收據）。各研究把逐格結果寫入 `runs/icperf/hac45/<研究>.json`（gitignored），由主委組成
`handoffs/run_receipts/` 之收據。

通過判準（A⑤、B⑥，SPEC ㊺「驗證」節）：每格 N 次重複之拒絕次數 ≤ Binomial(N, 0.05) 於 1−0.05／格數（格間
Bonferroni，各研究自為一族）之單尾上界；低於名目不判失敗。未警示子集（N_u 次）之拒絕次數與條件拒絕率只報告不判
（警示依同一樣本之持續性判定，條件拒絕率不受保證）。初判超限之格依預先登記之確認規則處置一次（:func:`decide_cell`）。
「拒絕」＝推論狀態 `ok` 且 p ≤ α（狀態非 ok 者 p＝NaN，不出 p 即不拒絕，另列計數）。

受檢對象全為產品碼：A⑤＝`ic_filter_orchestrator._compute_hac_on_ic_series`＋`_xsec_data_warning`；B⑥＝產品
`ICEngine.compute_rolling_ic`、`holdout_boundary` 切測試段、`ICFilterOrchestrator._slice_rolling_ic_to_test`／
`_rolling_window_positions_test`／`_centrality_support`、`FactorCentralityAnalyzer.compute_rolling_centrality`、
`LongShortAnalyzer.analyze` 與 `TrendAnalyzer.analyze_trend`（推論＋警示）。測試端只寫資料生成器與計數。
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

REPO = Path(__file__).resolve().parents[3]
OUT_DIR = REPO / "runs" / "icperf" / "hac45"
ALPHA = 0.05

# ── SPEC ㊺ 驗證之格點（封閉清單；改此即改規格） ─────────────────────────────────────────

#: A⑤：m∈{250,1000}×φ∈{0,0.9,0.99}×缺值率∈{0,30%}、h＝5、K＝10，每格 2,000 次；另壓力 1 格
A5_REPS = 2000
A5_H = 5
A5_K = 10
A5_GRID: List[dict] = [
    {"m": m, "phi": phi, "q": q, "h": A5_H, "k": A5_K, "stress": False}
    for m in (250, 1000) for phi in (0.0, 0.9, 0.99) for q in (0.0, 0.3)
] + [{"m": 250, "phi": 0.9, "q": 0.0, "h": A5_H, "k": "3..10", "stress": True}]

#: B⑥：滾動 Spearman IC n∈{500,2000,5000}×φ∈{0,0.9,0.99}、w＝21、h＝5（9 格）；w＝63 於 n＝2000、φ∈{0,0.99}（2 格）；
#: 中心性二層窗 1 格（n＝2000、φ＝0.9）；條件持倉 ls_spread 1 格（n＝2000、φ＝0.9）；每格 1,000 次
B6_REPS = 1000
B6_H = 5
B6_GRID: List[dict] = (
    [{"dim": "ic", "n": n, "phi": phi, "w": 21, "h": B6_H} for n in (500, 2000, 5000) for phi in (0.0, 0.9, 0.99)]
    + [{"dim": "ic", "n": 2000, "phi": phi, "w": 63, "h": B6_H} for phi in (0.0, 0.99)]
    + [{"dim": "centrality", "n": 2000, "phi": 0.9, "w": 21, "h": B6_H, "j": 10}]
    + [{"dim": "ls_spread", "n": 2000, "phi": 0.9, "w": 21, "h": B6_H}]
)

#: B⑦：檢定力（研究輸出、不設門檻）δ∈{0,2,4,8}；格＝B⑥ 之 w＝21 九格；各方法以獨立虛無模擬校正至同一實際 size
B7_REPS = 1000
B7_DELTAS = (0, 2, 4, 8)
B7_GRID: List[dict] = [g for g in B6_GRID if g["dim"] == "ic" and g["w"] == 21]

BURN_IN = 500


def bonferroni_upper_bound(n_reps: int, n_cells: int, alpha: float = 0.05) -> int:
    """單尾上界：Binomial(N, α) 於水準 1−0.05／格數之分位（格點數由測試計算，不寫死）。"""
    return int(stats.binom.ppf(1.0 - 0.05 / n_cells, n_reps, alpha))


#: 預先登記之確認規則（SPEC ㊺ 判準）：初判超限之格以獨立種子（格鍵加 `|confirm`）跑該格 10 倍次數一次
CONFIRM_FACTOR = 10
CONFIRM_EXTRA = "confirm"


def decide_cell(rejected: int, reps: int, n_cells: int, confirm: Optional[Tuple[int, int]] = None) -> dict:
    """單格判定：初判＝拒絕數 ≤ Bonferroni 上界；初判超限且有確認跑（拒絕數, 次數）⇒ 對 H0：size ≤ 0.05 做單尾精確
    二項檢定（p＝P(X ≥ k)），p ≤ 0.05／格數 ⇒ 不通過，否則記「初判超限、確認未重現」並通過。初判超限而未給確認 ⇒
    `needs_confirmation`（pass＝None，呼叫端須跑確認）。"""
    ub = bonferroni_upper_bound(reps, n_cells)
    out: dict = {"upper_bound": ub, "initial_pass": bool(rejected <= ub), "confirmation": None}
    if out["initial_pass"]:
        out["pass"], out["verdict"] = True, "pass"
        return out
    if confirm is None:
        out["pass"], out["verdict"] = None, "needs_confirmation"
        return out
    k, n = int(confirm[0]), int(confirm[1])
    p = float(stats.binom.sf(k - 1, n, ALPHA))
    level = 0.05 / n_cells
    out["confirmation"] = {"rejected": k, "reps": n, "reject_rate": k / n, "one_sided_p": p, "level": level}
    significant = p <= level
    out["pass"] = not significant
    out["verdict"] = "confirmed_excess" if significant else "initial_excess_not_confirmed"
    return out


def cell_key(prefix: str, cell: dict, extra: str = "") -> str:
    return prefix + "|" + "|".join(f"{k}={cell[k]}" for k in sorted(cell)) + (f"|{extra}" if extra else "")


def cell_seed(key: str) -> int:
    """每格種子＝格參數字串之 SHA-256 前 8 位元組（SPEC ㊺ 生成器節）。"""
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "little")


def ar1_paths(rng: np.random.Generator, shape: Tuple[int, ...], length: int, phi: float) -> np.ndarray:
    """獨立高斯 AR(1)(φ)：變異 1、平穩初值、燒入 BURN_IN；回 shape＋(length,)。"""
    e = rng.standard_normal(shape + (length + BURN_IN,))
    x = np.empty_like(e)
    x[..., 0] = e[..., 0]
    s = math.sqrt(1.0 - phi * phi)
    for t in range(1, e.shape[-1]):
        x[..., t] = phi * x[..., t - 1] + s * e[..., t]
    return x[..., BURN_IN:]


def forward_sum(r: np.ndarray, h: int) -> np.ndarray:
    """標籤＝其後 h 期報酬和：label_t＝r_{t+1}＋…＋r_{t+h}；輸入末軸長 L＋h ⇒ 輸出長 L。"""
    c = np.cumsum(r, axis=-1)
    c = np.concatenate([np.zeros(r.shape[:-1] + (1,)), c], axis=-1)
    length = r.shape[-1] - h
    return c[..., 1 + h: 1 + h + length] - c[..., 1: 1 + length]


def cross_sectional_spearman(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """逐期截面 Spearman（平均名次處理 ties）：x、y 形 (..., K, T) ⇒ (..., T)；截面常數 ⇒ NaN。"""
    rx = stats.rankdata(x, axis=-2)
    ry = stats.rankdata(y, axis=-2)
    rx = rx - rx.mean(axis=-2, keepdims=True)
    ry = ry - ry.mean(axis=-2, keepdims=True)
    num = (rx * ry).sum(axis=-2)
    den = np.sqrt((rx * rx).sum(axis=-2) * (ry * ry).sum(axis=-2))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / den, np.nan)


# ── A⑤ 跨標的 ────────────────────────────────────────────────────────────────


def a5_ic_series(cell: dict, rng: np.random.Generator, reps: int) -> np.ndarray:
    """A⑤ 生成器：每標的特徵 AR(1)(φ)、報酬 iid N(0,1) 與特徵獨立、標籤＝其後 h 期報酬和；逐期 IC＝跨標的 Spearman；
    缺值率 q ⇒ 逐期獨立 Bernoulli(q) 刪整期（IC＝NaN）。壓力格：K_t 逐期取 {3,…,10} 均勻、特徵四捨五入至 1 位小數。
    回 (reps, m)。"""
    m, h, phi = int(cell["m"]), int(cell["h"]), float(cell["phi"])
    k_max = 10 if cell["stress"] else int(cell["k"])
    x = ar1_paths(rng, (reps, k_max), m, phi)
    y = forward_sum(rng.standard_normal((reps, k_max, m + h)), h)
    if cell["stress"]:
        x = np.round(x, 1)
        k_t = rng.integers(3, 11, size=(reps, m))
        ic = np.full((reps, m), np.nan)
        for k in range(3, 11):
            ri, ti = np.nonzero(k_t == k)
            if ri.size:
                # 進階索引 ri、ti 被切片隔開 ⇒ 結果形 (點數, k)；標的數 K_t＝k（前 k 個標的，標的間 iid 故等同隨機子集）
                ic[ri, ti] = cross_sectional_spearman(x[ri, :k, ti][:, :, None], y[ri, :k, ti][:, :, None])[:, 0]
    else:
        ic = cross_sectional_spearman(x, y)
    if float(cell["q"]) > 0.0:
        ic[rng.random((reps, m)) < float(cell["q"])] = np.nan
    return ic


def a5_run_cell(cell: dict, reps: int = A5_REPS, extra: str = "") -> dict:
    """A⑤ 單格（分塊 250 次生成；分塊大小影響亂數抽取順序，重現須同此值）；`extra`＝種子鍵附加段（確認跑用）。"""
    from momentum.Analysis.ic_filter_orchestrator import _compute_hac_on_ic_series, _xsec_data_warning

    key = cell_key("A5", cell, extra)
    seed = cell_seed(key)
    rng = np.random.Generator(np.random.PCG64(seed))
    t0 = time.perf_counter()
    counts: Dict[str, int] = {"ok": 0, "rejected": 0, "unwarned": 0, "rejected_unwarned": 0}
    status_counts: Dict[str, int] = {}
    warning_counts: Dict[str, int] = {}
    finite_m: List[int] = []
    chunk = 250
    done = 0
    while done < reps:
        n = min(chunk, reps - done)
        ic = a5_ic_series(cell, rng, n)
        for row in ic:
            finite_m.append(int(np.isfinite(row).sum()))
            hac = _compute_hac_on_ic_series(row, horizon=int(cell["h"]))
            warn = _xsec_data_warning(row, hac, ALPHA)
            st = str(hac["inference_status"])
            status_counts[st] = status_counts.get(st, 0) + 1
            w = warn["data_warning"]
            warning_counts[str(w)] = warning_counts.get(str(w), 0) + 1
            ok = st == "ok" and np.isfinite(hac["p_value"])
            rej = bool(ok and hac["p_value"] <= ALPHA)
            counts["ok"] += int(ok)
            counts["rejected"] += int(rej)
            if w is None and ok:
                counts["unwarned"] += 1
                counts["rejected_unwarned"] += int(rej)
        done += n
    fm = np.asarray(finite_m)
    return {"cell": cell, "key": key, "seed": seed, "reps": reps, **counts,
            "status_counts": status_counts, "warning_counts": warning_counts,
            "finite_m": {"min": int(fm.min()), "median": float(np.median(fm)), "max": int(fm.max())},
            "seconds": round(time.perf_counter() - t0, 3)}


# ── B⑥／B⑦ 趨勢 ──────────────────────────────────────────────────────────────


def _trend_cfg() -> dict:
    from momentum.Analysis.ic_config_schema import TrendAnalysisConfig

    cfg = TrendAnalysisConfig().model_dump()
    cfg["significance_level"] = ALPHA
    return cfg


def _orchestrator_stub(w: int):
    """只帶 `_ic_engine` 之協調器（產品 `_slice_rolling_ic_to_test`／`_rolling_window_positions_test` 只讀此屬性）。"""
    from momentum.Analysis.ic_engine import ICEngine
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    engine = ICEngine({"rolling_windows": [w], "rolling_stride": 1, "icir": {"window": w}})
    stub = ICFilterOrchestrator.__new__(ICFilterOrchestrator)
    stub._ic_engine = engine
    return stub, engine


def _test_mask(index: pd.DatetimeIndex, h: int) -> np.ndarray:
    """產品切分：`holdout_boundary`（oos_test_size＝ICConfig 預設、purge＝max(預設, h)、embargo＝預設）。"""
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.core.split_preview import holdout_boundary

    cfg = ICConfig()
    b = holdout_boundary(index, oos_test_size=float(cfg.oos_test_size), purge_gap=int(h), embargo=int(cfg.embargo))
    mask = np.zeros(len(index), dtype=bool)
    mask[np.asarray(b["test_row_index"], dtype=int)] = True
    return mask


def _product_t_only(y: np.ndarray, sup_start: np.ndarray, sup_end: np.ndarray) -> dict:
    """產品推論之 t（不算精確 p）：同 `TrendAnalyzer.analyze_trend` 之選取（`select_nonoverlapping`）、有效點數
    < min_samples ⇒ 不可判定、`infer_trend` 之剔非有限與狀態前置判定，以產品 `bartlett_fixedb_slope` 取斜率與 SE。
    B⑦ 只需 |t| 作 size 校正（p 為 |t| 之單調函數，同設計下校正後拒絕集合相同）。"""
    from momentum.Analysis import trend_inference as ti

    if int(np.count_nonzero(~np.isnan(y))) < int(_trend_cfg()["min_samples"]):
        return {"inference_status": ti.STATUS_BELOW_MIN_SAMPLES, "inference_slope": None, "inference_se": None}
    sel = ti.select_nonoverlapping(sup_start, sup_end)
    xv, yv = sup_end[sel].astype(float), y[sel]
    fin = np.isfinite(xv) & np.isfinite(yv)
    xv, yv = xv[fin], yv[fin]
    if xv.size < 3:
        return {"inference_status": ti.STATUS_INSUFFICIENT_POINTS, "inference_slope": None, "inference_se": None}
    if np.all(yv == yv[0]):
        return {"inference_status": ti.STATUS_CONSTANT_SERIES, "inference_slope": 0.0, "inference_se": None}
    fit = ti.bartlett_fixedb_slope(xv, yv)
    if not (np.isfinite(fit.slope) and np.isfinite(fit.se) and fit.se > 0.0):
        return {"inference_status": ti.STATUS_DEGENERATE, "inference_slope": None, "inference_se": None}
    return {"inference_status": ti.STATUS_OK, "inference_slope": fit.slope, "inference_se": fit.se}


def b_single_rep(cell: dict, rng: np.random.Generator, slope_delta: float = 0.0,
                 sigma_lr: Optional[float] = None, t_only: bool = False) -> dict:
    """單次 B 生成＋產品趨勢檢定；回該維第一特徵之 analyze_trend 結果，另附 `_series`（注入前）、`_y`（受檢序列）、
    `_support_end`（各值支撐迄點；ls_spread 為〔位置＋h−1〕）、`_series_len`（有限值數）。

    生成器（SPEC ㊺ 生成器節 B⑥）：單標的 n 根，特徵 AR(1)(φ)、報酬 iid N(0,1)、標籤＝其後 h 根報酬和（生成 n＋h 根
    報酬，故 n 列標籤皆有限）。ls_spread 維：產品多空分析於整段，趨勢輸入經產品同一測試段切法
    （`ICFilterOrchestrator._ls_spread_test_values`，SPEC ㊺ B(2)）。
    `slope_delta`（B⑦，SPEC ㊺ ⑦）：對長度 L 之受檢序列 y 注入 β·j（j＝序列位置 0..L−1），β＝δ·σ_LR／L^{3/2}，
    σ_LR＝未注入受檢序列之長期標準差（由呼叫端以獨立虛無校正重複估）。"""
    from momentum.Analysis.factor_centrality_analyzer import FactorCentralityAnalyzer
    from momentum.Analysis.ic_config_schema import FactorCentralityConfig, LongShortAnalysisConfig
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
    from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
    from momentum.Analysis.trend_analyzer import TrendAnalyzer

    n, h, w, phi, dim = int(cell["n"]), int(cell["h"]), int(cell["w"]), float(cell["phi"]), cell["dim"]
    j = int(cell.get("j", 1))
    x = ar1_paths(rng, (j,), n, phi)
    label_vals = forward_sum(rng.standard_normal(n + h), h)
    index = pd.date_range("2020-01-01", periods=n, freq="h")
    names = [f"f{i}" for i in range(j)]
    feats = pd.DataFrame(x.T, index=index, columns=names)
    label = pd.Series(label_vals, index=index)
    analyzer = TrendAnalyzer(_trend_cfg())

    def _inject(y: np.ndarray) -> np.ndarray:
        if slope_delta == 0.0:
            return y
        return y + b7_beta(slope_delta, float(sigma_lr), y.size) * np.arange(y.size, dtype=float)

    if dim == "ls_spread":
        # 產品 `_run_long_short` 以整段特徵框呼叫（PIT 擴張分位持倉）；趨勢 ls_spread 維只取測試段（產品同一切法）
        res = LongShortAnalyzer(LongShortAnalysisConfig().model_dump()).analyze(feats["f0"], label)
        series = np.asarray(ICFilterOrchestrator._ls_spread_test_values(
            [float(v) for v in res["ls_spread_series"]], h, _test_mask(index, h)), dtype=float)
        y = _inject(series)
        out = analyzer.analyze_trend(pd.Series(y), "ls_spread", overlap_window=h, select_finite_only=True)
        support_end = np.arange(series.size, dtype=np.int64) + h - 1
    else:
        stub, engine = _orchestrator_stub(w)
        mask = _test_mask(index, h)
        rolling = engine.compute_rolling_ic(feats, label, [w], 1, "spearman")
        rolling = stub._slice_rolling_ic_to_test(rolling, feats, label, [w], 1, mask)
        start, end = stub._rolling_window_positions_test(feats, label, [w], 1, mask)[f"window_{w}"]
        ic_support = (start, end + h - 1)  # 同 `_ic_trend_support`
        key = f"window_{w}"
        if dim == "ic":
            series = np.asarray(rolling["f0"][key], dtype=float)
            support = ic_support
        elif dim == "centrality":
            matrix = pd.DataFrame({nm: rolling[nm][key] for nm in names}, dtype=float)
            cen = FactorCentralityAnalyzer(FactorCentralityConfig().model_dump())
            rc = cen.compute_rolling_centrality(matrix)
            support = ICFilterOrchestrator._centrality_support(ic_support, cen.effective_rolling_window(len(matrix)))
            series = rc["f0"].to_numpy(dtype=float) if "f0" in rc else np.full(0, np.nan)
        else:
            raise ValueError(dim)
        if support is None or series.size != np.asarray(support[0]).size:
            raise AssertionError(f"{dim} 序列與支撐長度不一致")
        y = _inject(series)
        support_end = np.asarray(support[1], dtype=np.int64)
        if t_only:
            out = _product_t_only(y, np.asarray(support[0], dtype=np.int64), support_end)
        else:
            out = analyzer.analyze_trend(pd.Series(y), dim, support=support)
    out["_series"] = series
    out["_y"] = y
    out["_support_end"] = support_end
    out["_series_len"] = int(np.isfinite(series).sum())
    return out


def b6_run_cell(cell: dict, reps: int = B6_REPS, extra: str = "") -> dict:
    key = cell_key("B6", cell, extra)
    seed = cell_seed(key)
    rng = np.random.Generator(np.random.PCG64(seed))
    t0 = time.perf_counter()
    counts: Dict[str, int] = {"ok": 0, "rejected": 0, "unwarned": 0, "rejected_unwarned": 0, "classified_up_down": 0}
    status_counts: Dict[str, int] = {}
    warning_counts: Dict[str, int] = {}
    points: List[int] = []
    for _ in range(reps):
        res = b_single_rep(cell, rng)
        st = str(res["inference_status"])
        status_counts[st] = status_counts.get(st, 0) + 1
        w = res.get("data_warning")
        warning_counts[str(w)] = warning_counts.get(str(w), 0) + 1
        p = res.get("p_value")
        ok = st == "ok" and p is not None and np.isfinite(p)
        rej = bool(ok and p <= ALPHA)
        counts["ok"] += int(ok)
        counts["rejected"] += int(rej)
        counts["classified_up_down"] += int(res.get("trend") in ("up", "down"))
        points.append(int(res.get("subsample_points") or 0))
        if w is None and ok:
            counts["unwarned"] += 1
            counts["rejected_unwarned"] += int(rej)
    pts = np.asarray(points)
    return {"cell": cell, "key": key, "seed": seed, "reps": reps, **counts,
            "status_counts": status_counts, "warning_counts": warning_counts,
            "subsample_points": {"min": int(pts.min()), "median": float(np.median(pts)), "max": int(pts.max())},
            "seconds": round(time.perf_counter() - t0, 3)}


# B⑦ 比較方法（研究輸出）：產品推論＝不重疊子序列 Bartlett fixed-b(b＝1)；對照＝重疊全序列上之舊法（OLS＋固定頻寬
# Newey–West、落後＝支撐長−1、t(n−2)）與 EWC（斜率分數之 LLSW 2018 EWC、t_ν）。兩對照為 SPEC ㊺ 現況欄所列已實測失準之法。


def _overlap_scores(x: np.ndarray, y: np.ndarray) -> Tuple[float, np.ndarray, float]:
    fin = np.isfinite(y)
    x, y = x[fin], y[fin]
    xc = x - x.mean()
    sxx = float(xc @ xc)
    beta = float(xc @ (y - y.mean())) / sxx
    e = (y - y.mean()) - beta * xc
    return beta, xc * e, sxx


def t_nw_overlap(x: np.ndarray, y: np.ndarray, lag: int) -> float:
    beta, s, sxx = _overlap_scores(x, y)
    n = s.size
    L = min(int(lag), n - 1)
    omega = float(s @ s) / n
    for l in range(1, L + 1):
        omega += 2.0 * (1.0 - l / (L + 1.0)) * float(s[l:] @ s[:-l]) / n
    var = n * omega / (sxx * sxx)
    return beta / math.sqrt(var) if var > 0 else float("nan")


def t_ewc_overlap(x: np.ndarray, y: np.ndarray) -> float:
    from momentum.Analysis.hac_ewc import ewc_dof, ewc_long_run_variance

    beta, s, sxx = _overlap_scores(x, y)
    n = s.size
    nu = ewc_dof(n)
    if nu < 1:
        return float("nan")
    omega = ewc_long_run_variance(s, nu)
    var = n * omega / (sxx * sxx)
    return beta / math.sqrt(var) if var > 0 else float("nan")


B7_METHODS = ("product_nonoverlap_fixedb", "nw_overlap_fixed_lag", "ewc_overlap")
B7_DELTA_DEFINITION = ("β＝δ·σ_LR／L^{3/2}（對序列位置 0..L−1）；σ_LR²＝L·Var(ȳ)，ȳ＝未注入受檢序列之有限值均值，"
                       "Var 取獨立虛無校正重複之樣本變異")


def b7_beta(delta: float, sigma_lr: float, length: int) -> float:
    """SPEC ㊺ ⑦ 注入斜率 β＝δ·σ_LR／L^{3/2}。"""
    return float(delta) * float(sigma_lr) / float(length) ** 1.5


def b7_sigma_lr(null_means: List[float], length: int) -> float:
    """σ_LR 估計：σ_LR²＝L·Var(ȳ)（ȳ 跨獨立虛無重複之樣本變異，ddof＝1）。"""
    return math.sqrt(float(length) * float(np.var(np.asarray(null_means, dtype=float), ddof=1)))


def b7_statistics(cell: dict, res: dict) -> Dict[str, float]:
    """三方法之 |t|（size 校正用統計量）。產品法取推論斜率／推論 SE（狀態非 ok ⇒ NaN）；對照法於重疊全序列
    （x＝支撐迄點原列位置、y＝受檢序列）。"""
    w, h = int(cell["w"]), int(cell["h"])
    y = np.asarray(res["_y"], dtype=float)
    x = np.asarray(res["_support_end"], dtype=float)
    se = res.get("inference_se")
    t_prod = abs(res["inference_slope"] / se) if res.get("inference_status") == "ok" and se else float("nan")
    return {"product_nonoverlap_fixedb": t_prod,
            "nw_overlap_fixed_lag": abs(t_nw_overlap(x, y, w + h - 2)),
            "ewc_overlap": abs(t_ewc_overlap(x, y))}


def b7_run_cell(cell: dict, reps: int = B7_REPS, deltas=B7_DELTAS) -> dict:
    """size 校正：獨立虛無模擬（種子鍵加 `null`）取各方法 |t| 之 1−α 分位為臨界值；各 δ（獨立種子）之檢定力＝
    |t|＞臨界值之比例（NaN 計為不拒絕並另列數）；δ＝0 列即校正後 size 之獨立檢查。"""
    t0 = time.perf_counter()
    null_key = cell_key("B7", cell, "null")
    rng0 = np.random.Generator(np.random.PCG64(cell_seed(null_key)))
    null_t: Dict[str, List[float]] = {k: [] for k in B7_METHODS}
    means: List[float] = []
    lengths: set = set()
    for _ in range(reps):
        res = b_single_rep(cell, rng0, t_only=True)
        means.append(float(np.nanmean(res["_series"])))
        lengths.add(int(np.asarray(res["_series"]).size))
        for k, v in b7_statistics(cell, res).items():
            null_t[k].append(v)
    if len(lengths) != 1:
        raise AssertionError(f"B⑦ 受檢序列長度不固定：{sorted(lengths)}")
    length = lengths.pop()
    sigma_lr = b7_sigma_lr(means, length)
    crit = {k: float(np.nanquantile(np.asarray(v), 1.0 - ALPHA)) for k, v in null_t.items()}
    power: Dict[str, dict] = {}
    for d in deltas:
        rng = np.random.Generator(np.random.PCG64(cell_seed(cell_key("B7", cell, f"delta={d}"))))
        ts: Dict[str, List[float]] = {k: [] for k in B7_METHODS}
        for _ in range(reps):
            res = b_single_rep(cell, rng, slope_delta=float(d), sigma_lr=sigma_lr, t_only=True)
            for k, v in b7_statistics(cell, res).items():
                ts[k].append(v)
        arr = {k: np.asarray(v, dtype=float) for k, v in ts.items()}
        power[str(d)] = {k: float(np.mean(np.where(np.isnan(a), False, a > crit[k]))) for k, a in arr.items()}
        power[str(d)]["nan_counts"] = {k: int(np.isnan(a).sum()) for k, a in arr.items()}
        power[str(d)]["beta"] = b7_beta(float(d), sigma_lr, length)
    return {"cell": cell, "reps": reps, "null_key": null_key, "delta_definition": B7_DELTA_DEFINITION,
            "series_length": length, "sigma_lr_null": sigma_lr,
            # δ＝0 列含校正誤差之標準誤（校正批與評估批各 N 次，名目 size 0.05）
            "delta0_se_with_calibration": math.sqrt(ALPHA * (1.0 - ALPHA) * 2.0 / reps),
            "null_nan_counts": {k: int(np.isnan(np.asarray(v)).sum()) for k, v in null_t.items()},
            "size_adjusted_critical_abs_t": crit, "size_adjusted_power": power,
            "seconds": round(time.perf_counter() - t0, 3)}


# ── 收據 ─────────────────────────────────────────────────────────────────────


def _write(name: str, payload: dict) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    return path


def _judge(cells: List[dict], rerun: Optional[Callable[[dict, int, str], dict]] = None) -> List[dict]:
    """逐格判定（:func:`decide_cell`）；初判超限且給 `rerun`（cell, 次數, 種子鍵附加段 ⇒ 單格結果）⇒ 依確認規則跑一次。
    未警示子集只報告。"""
    n_cells = len(cells)
    for c in cells:
        nu = int(c["unwarned"])
        c["n_cells_bonferroni"] = n_cells
        c["raw_reject_rate"] = c["rejected"] / c["reps"]
        c["warning_rate"] = 1.0 - c["unwarned"] / c["reps"]
        c["unwarned_reject_rate"] = (c["rejected_unwarned"] / nu) if nu else None
        decision = decide_cell(int(c["rejected"]), int(c["reps"]), n_cells)
        if decision["verdict"] == "needs_confirmation" and rerun is not None:
            conf = rerun(c["cell"], CONFIRM_FACTOR * int(c["reps"]), CONFIRM_EXTRA)
            c["confirmation_run"] = conf
            decision = decide_cell(int(c["rejected"]), int(c["reps"]), n_cells,
                                   confirm=(int(conf["rejected"]), int(conf["reps"])))
        c.update(decision)
    return cells


# ── 測試 ─────────────────────────────────────────────────────────────────────


def test_bonferroni_upper_bound_definition() -> None:
    # 純定義測試（非研究本體）：上界隨 N 遞增、隨格數遞增；N＝2000、13 格＝scipy 直算 127
    assert bonferroni_upper_bound(2000, 13) >= bonferroni_upper_bound(1000, 13)
    assert bonferroni_upper_bound(1000, 26) >= bonferroni_upper_bound(1000, 13)
    assert bonferroni_upper_bound(2000, 13) == int(stats.binom.ppf(1 - 0.05 / 13, 2000, 0.05)) == 127


def test_judge_unconditional_with_preregistered_confirmation() -> None:
    """SPEC ㊺ 判準（r109 改無條件）：①條件不過而無條件過 ⇒ 過（首輪 A5 m=250 φ=0.9：111／2000、未警示 42／481）；
    ②N_u＝0 仍依全部 N 判；③128／2000 於 13 格初判超限 ⇒ 需確認，確認跑之拒絕數決定通過與否（精確二項單尾）；
    ④確認只跑一次、種子鍵加 `|confirm`、次數＝10 倍。"""
    filler = [{"cell": {"i": i}, "reps": 2000, "rejected": 100, "unwarned": 2000, "rejected_unwarned": 100}
              for i in range(10)]
    cond_fail = {"cell": {"i": "a"}, "reps": 2000, "rejected": 111, "unwarned": 481, "rejected_unwarned": 42}
    nu_zero = {"cell": {"i": "b"}, "reps": 2000, "rejected": 92, "unwarned": 0, "rejected_unwarned": 0}
    edge = {"cell": {"i": "c"}, "reps": 2000, "rejected": 128, "unwarned": 22, "rejected_unwarned": 5}
    calls: List[tuple] = []

    def rerun_ok(cell: dict, reps: int, extra: str) -> dict:
        calls.append((cell["i"], reps, extra))
        return {"rejected": 1010, "reps": reps}

    cells = _judge([dict(c) for c in filler] + [dict(cond_fail), dict(nu_zero), dict(edge)], rerun=rerun_ok)
    by = {c["cell"]["i"]: c for c in cells}
    assert by["a"]["pass"] is True and by["a"]["unwarned_reject_rate"] == pytest.approx(42 / 481)
    assert by["b"]["pass"] is True and by["b"]["unwarned_reject_rate"] is None
    assert by["c"]["initial_pass"] is False and by["c"]["verdict"] == "initial_excess_not_confirmed"
    assert by["c"]["pass"] is True and calls == [("c", 20000, "confirm")]
    # 確認重現超額 ⇒ 不通過
    bad = _judge([dict(c) for c in filler] + [dict(cond_fail), dict(nu_zero), dict(edge)],
                 rerun=lambda cell, reps, extra: {"rejected": 1150, "reps": reps})
    assert {c["cell"]["i"]: c["verdict"] for c in bad}["c"] == "confirmed_excess"
    assert {c["cell"]["i"]: c["pass"] for c in bad}["c"] is False
    # 未給確認 ⇒ needs_confirmation（pass None，不得默認通過）
    pending = decide_cell(128, 2000, 13)
    assert pending["verdict"] == "needs_confirmation" and pending["pass"] is None
    # 精確二項：p＝P(X≥k)
    d = decide_cell(128, 2000, 13, confirm=(1050, 20000))
    assert d["confirmation"]["one_sided_p"] == pytest.approx(float(stats.binom.sf(1049, 20000, 0.05)), rel=1e-12)


def test_b7_beta_and_sigma_lr_definition() -> None:
    """SPEC ㊺ ⑦：β＝δ·σ_LR／L^{3/2}；σ_LR²＝L·Var(ȳ)（ddof＝1）。iid N(0,1) 序列之 σ_LR≈1（大樣本）。"""
    assert b7_beta(4.0, 0.5, 100) == pytest.approx(4.0 * 0.5 / 1000.0, rel=1e-15)
    assert b7_beta(0.0, 0.5, 100) == 0.0
    rng = np.random.Generator(np.random.PCG64(5))
    L = 50
    means = [float(rng.standard_normal(L).mean()) for _ in range(4000)]
    assert b7_sigma_lr(means, L) == pytest.approx(math.sqrt(L * np.var(means, ddof=1)), rel=1e-15)
    assert abs(b7_sigma_lr(means, L) - 1.0) < 0.05


def test_generators_match_reference_definitions() -> None:
    """生成器秒級自驗：截面 Spearman 對 scipy.stats.spearmanr（含 ties）逐期相等；前瞻和對逐項加總相等；
    AR(1) 樣本一階自相關近 φ；格點數等於 SPEC 封閉清單（A⑤ 13 格、B⑥ 13 格）。"""
    rng = np.random.Generator(np.random.PCG64(7))
    x = np.round(rng.standard_normal((3, 6, 40)), 1)
    y = rng.standard_normal((3, 6, 40))
    got = cross_sectional_spearman(x, y)
    for r in range(3):
        for t in range(40):
            assert got[r, t] == pytest.approx(stats.spearmanr(x[r, :, t], y[r, :, t]).correlation, abs=1e-12)
    r = rng.standard_normal((2, 30))
    fs = forward_sum(r, 5)
    assert fs.shape == (2, 25)
    assert np.allclose(fs[:, 3], r[:, 4:9].sum(axis=1))
    a = ar1_paths(rng, (1,), 20000, 0.9)[0]
    assert abs(np.corrcoef(a[:-1], a[1:])[0, 1] - 0.9) < 0.02 and abs(a.var() - 1.0) < 0.15
    assert len(A5_GRID) == 13 and len(B6_GRID) == 13 and len(B7_GRID) == 9
    # 壓力格：K_t ∈ {3..10} 之 IC 與逐期 spearmanr 相等
    cell = dict(A5_GRID[-1])
    ic = a5_ic_series({**cell, "m": 30}, np.random.Generator(np.random.PCG64(3)), 2)
    assert ic.shape == (2, 30) and np.isfinite(ic).mean() > 0.9


def test_b_single_rep_uses_product_supports() -> None:
    """B 生成器秒級自驗：IC 維之序列長＝測試段整窗數、支撐迄點＝窗末列＋h−1（測試段末列＝n−1 ⇒ 末值迄點 n−1＋h−1）；
    中心性維序列長＝IC 數−W＋1；ls_spread 維支撐為〔位置, 位置＋h−1〕。"""
    n, w, h = 500, 21, 5
    mask = _test_mask(pd.date_range("2020-01-01", periods=n, freq="h"), h)
    n_test = int(mask.sum())
    res = b_single_rep({"dim": "ic", "n": n, "phi": 0.0, "w": w, "h": h}, np.random.Generator(np.random.PCG64(11)))
    assert res["_series"].size == n_test - w + 1
    assert int(res["_support_end"][-1]) == n - 1 + h - 1
    assert int(res["_support_end"][0]) == int(np.flatnonzero(mask)[0]) + w - 1 + h - 1
    assert res["inference_method"] == "bartlett_fixedb_b1_nonoverlap"
    cen = b_single_rep({"dim": "centrality", "n": 2000, "phi": 0.0, "w": w, "h": h, "j": 10},
                       np.random.Generator(np.random.PCG64(12)))
    n_ic = int(_test_mask(pd.date_range("2020-01-01", periods=2000, freq="h"), h).sum()) - w + 1
    from momentum.Analysis.ic_config_schema import FactorCentralityConfig
    assert cen["_series"].size == n_ic - min(FactorCentralityConfig().rolling_window, n_ic) + 1
    ls = b_single_rep({"dim": "ls_spread", "n": 500, "phi": 0.0, "w": w, "h": h}, np.random.Generator(np.random.PCG64(13)))
    assert ls["_series"].size == n and int(ls["_support_end"][0]) == h - 1
    # SPEC ㊺ B(2)：ls_spread 趨勢輸入只含支撐〔t, t＋h−1〕起迄皆在測試段之列（其餘 NaN）；測試段內有持倉值
    held = np.isfinite(ls["_series"])
    in_test = np.zeros(n, dtype=bool)
    in_test[: n - h + 1] = mask[: n - h + 1] & mask[h - 1:]
    assert not held[~in_test].any() and held[in_test].any()
    assert int(ls["subsample_start_pos"]) >= int(np.flatnonzero(mask)[0])
    # B⑦ 之 t_only 路徑＝產品 analyze_trend 之推論斜率與 SE（同種子、含注入）
    for n_, d in ((2000, 0.0), (5000, 4.0)):
        cell = {"dim": "ic", "n": n_, "phi": 0.9, "w": w, "h": h}
        full = b_single_rep(cell, np.random.Generator(np.random.PCG64(21)), slope_delta=d, sigma_lr=0.2)
        fast = b_single_rep(cell, np.random.Generator(np.random.PCG64(21)), slope_delta=d, sigma_lr=0.2,
                            t_only=True)
        assert full["inference_status"] == fast["inference_status"] == "ok"
        assert fast["inference_slope"] == full["inference_slope"] and fast["inference_se"] == full["inference_se"]


def test_study_runners_smoke() -> None:
    """三研究之逐格執行器以極少次數跑通、輸出鍵完整（研究本體為 slow）。"""
    a = a5_run_cell(A5_GRID[-1], reps=3)
    assert a["reps"] == 3 and sum(a["status_counts"].values()) == 3
    b = b6_run_cell(B6_GRID[3], reps=2)
    assert b["reps"] == 2 and sum(b["warning_counts"].values()) == 2
    c = b7_run_cell(B7_GRID[3], reps=4, deltas=(0, 8))
    assert set(c["size_adjusted_power"]) == {"0", "8"}
    assert c["size_adjusted_power"]["8"]["beta"] == pytest.approx(b7_beta(8, c["sigma_lr_null"], c["series_length"]))
    assert a["finite_m"]["max"] <= int(A5_GRID[-1]["m"])
    assert a5_run_cell(A5_GRID[-1], reps=3, extra=CONFIRM_EXTRA)["key"].endswith("|confirm")


@pytest.mark.slow
def test_a5_xsec_null_rejection_conditional_on_no_warning() -> None:
    """A⑤ 判準為無條件 size（r109 起；函式名沿用以免改名立碑）；未警示子集之條件拒絕率只報告。"""
    cells = _judge([a5_run_cell(c) for c in A5_GRID],
                   rerun=lambda cell, reps, extra: a5_run_cell(cell, reps, extra))
    _write("a5", {"study": "A5", "alpha": ALPHA, "cells": cells})
    failed = [c["key"] for c in cells if c["pass"] is not True]
    assert not failed, failed


@pytest.mark.slow
def test_b6_trend_null_rejection_conditional_on_no_warning() -> None:
    """B⑥ 判準為無條件 size（r109 起；函式名沿用以免改名立碑）；未警示子集之條件拒絕率只報告。"""
    cells = _judge([b6_run_cell(c) for c in B6_GRID],
                   rerun=lambda cell, reps, extra: b6_run_cell(cell, reps, extra))
    _write("b6", {"study": "B6", "alpha": ALPHA, "cells": cells})
    failed = [c["key"] for c in cells if c["pass"] is not True]
    assert not failed, failed


@pytest.mark.slow
def test_b7_size_adjusted_power_report() -> None:
    cells = [b7_run_cell(c) for c in B7_GRID]
    _write("b7", {"study": "B7", "alpha": ALPHA, "cells": cells})
    # 研究輸出、不設門檻（SPEC ㊺ B⑦）；只驗輸出完整：每格每 δ 三方法皆有有限之檢定力值
    for c in cells:
        for d in map(str, B7_DELTAS):
            assert all(np.isfinite(c["size_adjusted_power"][d][k]) for k in B7_METHODS), (c["cell"], d)
