"""ICPERF Task 0.3 深度分析模組 oracle 對照——組 quality_netic（docs/ICPERF_SPEC.md Task 0.3 v5.26 深度分析涵蓋、資料充足判準；
Task 0.4「深度分析讀碼盤點」之 feature_quality 與 net_ic 兩條待證）。

被測模組（深度報告 `results.<模組鍵>`）：
- `feature_quality_diagnostics`：`momentum/Analysis/feature_quality_diagnostics.py`（呼叫端
  `ic_filter_orchestrator.py:3209-3219` `_run_feature_quality_diagnostics`；滾動 IC 取用 `:3362-3372`
  `_extract_rolling_ic_series`）。
- `net_ic_analysis`：`momentum/Analysis/net_ic_analyzer.py`（呼叫端 `ic_filter_orchestrator.py:3221-3268` `_run_net_ic`；
  換手率來源 `:3246-3250` 讀第 5 段 `turnover_analysis.<特徵>.quantile_turnover`）。

本檔為**稽核**：參考實作 `ref_*` 以 statsmodels（`adfuller`、`breaks_cusumolsresid`）、scipy（`chi2.sf`、`pearsonr`、
`spearmanr`）、numpy／pandas 與測試自寫之最簡公式獨立重算，不呼叫被測模組或其內部函式；不一致是要找的結果，以
`xfail(strict=True)` 斷言正確（oracle）行為，裁定前不修產品碼。

oracle 定義與產品不同之處（即本檔所記不一致，皆附理由）：
- ADF 值不得依牆鐘時間而變（使用者 2026-10-27「全專案禁時間上限停運算」；產品 `:68-70` 逾時即丟棄已算結果）。
- 未做 ADF 檢定之欄（全缺、樣本不足、常數、ADF 例外、逾時）不得標「非平穩」（產品 `:264`、`:269-270`）。
- CUSUM 漂移判定以 Ploberger–Krämer OLS-CUSUM（statsmodels `breaks_cusumolsresid`，統計量＝max|S_k|／(σ√n)）於
  `ORACLE_CUSUM_ALPHA` 判定；產品 `:158-160` 之門檻 5σ 未隨 √n 縮放 ⇒ 長序列恆判漂移。
- 有效樣本比於 lag-1 自相關無定義（常數序列）時為 NaN，不得寫 1.0（產品 `:316-317`）。
- net_ic 之 `turnover`／`cost_drag_return`／`cost_sensitivity`／`capacity`／`avg_cost_drag_return` 以該特徵因子擇時序列之
  逐根 PIT 換手率 mean(|position_t − position_{t−1}|)（首根 0）為準——與同列 `net_factor_return`、`breakeven_cost_bps`
  （`net_ic_analyzer.py:316`）同一定義、同一樣本；產品改用第 5 段頂分位單邊 `quantile_turnover`（測試段樣本，
  `ic_filter_orchestrator.py:3247`）卻標 `membership_change_both_legs_per_bar`（`net_ic_analyzer.py:16`、`:448`）。

本檔之 requires_kline 測試須經共用監看執行（autouse 自證，同 test_icperf_correctness.py）。
"""

from __future__ import annotations

import math
import os
import warnings
from types import SimpleNamespace
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.diagnostic import breaks_cusumolsresid
from statsmodels.tsa.stattools import adfuller

from momentum.Analysis import feature_quality_diagnostics as fq_mod
from momentum.Analysis.factor_return_analyzer import FactorReturnAnalyzer, FactorTimingReturnSeries
from momentum.Analysis.feature_quality_diagnostics import FeatureQualityDiagnostics
from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator
from momentum.Analysis.net_ic_analyzer import NetICAnalyzer
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
#: SPEC Task 0.3「驗證」：浮點相對誤差門檻
REL_TOL = 1e-12
HEAVY_MARKERS = ("slow", "requires_kline")
RECEIPT = "handoffs/run_receipts/20261029-icperf-correctness.json"
#: oracle 之 CUSUM 顯著水準（產品無此參數；我的判斷：取同模組 adf／ljungbox 之預設 0.05）
ORACLE_CUSUM_ALPHA = 0.05
#: 長資料格 L（SPEC Task 0.3 v5.26：BTCUSDT 1h 末 2,000 根）
L_ROWS = 2000
FQ = "feature_quality_diagnostics"
NET = "net_ic_analysis"
NON_STAT = "非統計欄"
_FQ_PY = "momentum/Analysis/feature_quality_diagnostics.py"
_NET_PY = "momentum/Analysis/net_ic_analyzer.py"
_ORCH_PY = "momentum/Analysis/ic_filter_orchestrator.py"


def _f(oracle: str, producer: str) -> Dict[str, str]:
    return {"oracle": oracle, "producer": producer}


#: 欄位清冊：模組回傳 dict 每一欄位路徑（前綴＝深度報告 results 之模組鍵；逐特徵段＝`*`、list 索引＝`#`）
MODULE_FIELDS: Dict[str, Dict[str, str]] = {
    # ── feature_quality_diagnostics ──
    f"{FQ}/adf_results/*/adf_statistic": _f("fq.adf", f"{_FQ_PY}:73"),
    f"{FQ}/adf_results/*/p_value": _f("fq.adf", f"{_FQ_PY}:71-74"),
    f"{FQ}/adf_results/*/is_stationary": _f("fq.adf", f"{_FQ_PY}:75"),
    f"{FQ}/adf_results/*/skipped": _f("fq.adf", f"{_FQ_PY}:38-64,76,78-96"),
    f"{FQ}/adf_results/*/reason": _f("fq.adf", f"{_FQ_PY}:41,50,59,81,91"),
    f"{FQ}/adf_results/*/timeout": _f(NON_STAT, f"{_FQ_PY}:82"),
    f"{FQ}/adf_results/*/error": _f(NON_STAT, f"{_FQ_PY}:92"),
    f"{FQ}/autocorrelation_results/*/ljungbox_stat": _f("fq.ljungbox", f"{_FQ_PY}:116-117"),
    f"{FQ}/autocorrelation_results/*/p_value": _f("fq.ljungbox", f"{_FQ_PY}:118"),
    f"{FQ}/autocorrelation_results/*/significant_autocorrelation": _f("fq.ljungbox", f"{_FQ_PY}:123"),
    f"{FQ}/autocorrelation_results/*/effective_sample_ratio": _f("fq.ess", f"{_FQ_PY}:119,310-319"),
    f"{FQ}/autocorrelation_results/*/skipped": _f("fq.ljungbox", f"{_FQ_PY}:104-113,125,127-137"),
    f"{FQ}/autocorrelation_results/*/reason": _f("fq.ljungbox", f"{_FQ_PY}:107,131"),
    f"{FQ}/autocorrelation_results/*/error": _f(NON_STAT, f"{_FQ_PY}:132"),
    f"{FQ}/drift_results/*/feature_name": _f(NON_STAT, f"{_FQ_PY}:148,169,239,249"),
    f"{FQ}/drift_results/*/skipped": _f("fq.drift", f"{_FQ_PY}:146-154,173,237-255"),
    f"{FQ}/drift_results/*/reason": _f("fq.drift", f"{_FQ_PY}:150,241,251"),
    f"{FQ}/drift_results/*/cusum_breakpoint": _f("fq.cusum", f"{_FQ_PY}:156-159,170"),
    f"{FQ}/drift_results/*/psi_score": _f("fq.psi", f"{_FQ_PY}:162-165,171,321-337"),
    f"{FQ}/drift_results/*/drifted": _f("fq.drift", f"{_FQ_PY}:158-160,166"),
    f"{FQ}/coverage_stats/*/coverage": _f("fq.coverage", f"{_FQ_PY}:180-182"),
    f"{FQ}/coverage_stats/*/nan_count": _f("fq.coverage", f"{_FQ_PY}:181"),
    f"{FQ}/coverage_stats/*/total": _f(NON_STAT, f"{_FQ_PY}:177,186"),
    f"{FQ}/redundancy_scan/high_correlation_pairs/#/#": _f("fq.redundancy", f"{_FQ_PY}:203-210"),
    f"{FQ}/redundancy_scan/threshold": _f(NON_STAT, f"{_FQ_PY}:28,214"),
    f"{FQ}/redundancy_scan/method": _f(NON_STAT, f"{_FQ_PY}:215,227"),
    f"{FQ}/redundancy_scan/skipped": _f("fq.redundancy", f"{_FQ_PY}:195-201,216"),
    f"{FQ}/quality_flags/non_stationary/#": _f("fq.flags.non_stationary", f"{_FQ_PY}:264,269-270"),
    f"{FQ}/quality_flags/high_autocorrelation/#": _f("fq.flags", f"{_FQ_PY}:265,271-272"),
    f"{FQ}/quality_flags/low_coverage/#": _f("fq.flags", f"{_FQ_PY}:266,273-274"),
    f"{FQ}/quality_flags/drifted/#": _f("fq.flags.drifted", f"{_FQ_PY}:267,275-276"),
    f"{FQ}/summary/total_features": _f(NON_STAT, f"{_FQ_PY}:279,297"),
    f"{FQ}/summary/stationary_rate": _f("fq.summary", f"{_FQ_PY}:278,298"),
    f"{FQ}/summary/mean_coverage": _f("fq.summary", f"{_FQ_PY}:280,299"),
    f"{FQ}/summary/low_quality_count": _f("fq.summary", f"{_FQ_PY}:282-287,300"),
    # ── net_ic_analysis ──
    f"{NET}/status": _f(NON_STAT, f"{_ORCH_PY}:3236-3237"),
    f"{NET}/skipped": _f(NON_STAT, f"{_NET_PY}:359-362"),
    f"{NET}/reason": _f(NON_STAT, f"{_NET_PY}:362;{_ORCH_PY}:3237"),
    f"{NET}/features/*/skipped": _f("net.branch", f"{_NET_PY}:377-426"),
    f"{NET}/features/*/reason": _f("net.branch", f"{_NET_PY}:381,390,397,405,417,424"),
    f"{NET}/features/*/gross_ic": _f("net.gross_ic", f"{_NET_PY}:409-411,446,469;{_ORCH_PY}:3241-3245"),
    f"{NET}/features/*/turnover": _f("net.turnover", f"{_NET_PY}:384-386,447,470;{_ORCH_PY}:3246-3250"),
    f"{NET}/features/*/turnover_semantics": _f(NON_STAT, f"{_NET_PY}:16,448,471"),
    f"{NET}/features/*/capacity/estimated_capacity_usd": _f("net.capacity", f"{_NET_PY}:239-257,282"),
    f"{NET}/features/*/capacity/capacity_tier": _f("net.capacity", f"{_NET_PY}:259-264,283"),
    f"{NET}/features/*/capacity/calibration": _f(NON_STAT, f"{_NET_PY}:284"),
    f"{NET}/features/*/cost_bps": _f(NON_STAT, f"{_NET_PY}:456,473"),
    f"{NET}/features/*/cost_semantics": _f(NON_STAT, f"{_NET_PY}:17,474"),
    f"{NET}/features/*/cost_drag_return": _f("net.cost_drag", f"{_NET_PY}:175-180,457,475"),
    f"{NET}/features/*/cost_sensitivity/#/cost_bps": _f("net.cost_ladder", f"{_NET_PY}:225-233"),
    f"{NET}/features/*/cost_sensitivity/#/cost_drag_return": _f("net.cost_drag", f"{_NET_PY}:234,476"),
    f"{NET}/features/*/net_factor_return/status": _f("net.net_return", f"{_NET_PY}:301-328"),
    f"{NET}/features/*/net_factor_return/value": _f("net.net_return", f"{_NET_PY}:86-106,316-328"),
    f"{NET}/features/*/net_factor_return/reason": _f("net.net_return", f"{_NET_PY}:304,320-321"),
    f"{NET}/features/*/breakeven_cost_bps/status": _f("net.breakeven", f"{_NET_PY}:307,323,332-338"),
    f"{NET}/features/*/breakeven_cost_bps/value": _f("net.breakeven", f"{_NET_PY}:108-119,132,338"),
    f"{NET}/features/*/breakeven_cost_bps/reason": _f("net.breakeven", f"{_NET_PY}:308,323,334-336"),
    f"{NET}/features/*/profitable_after_cost/status": _f("net.profitable", f"{_NET_PY}:310,324,339"),
    f"{NET}/features/*/profitable_after_cost/value": _f("net.profitable", f"{_NET_PY}:329,339"),
    f"{NET}/features/*/profitable_after_cost/reason": _f("net.profitable", f"{_NET_PY}:311,324,339"),
    f"{NET}/summary/total_analyzed": _f(NON_STAT, f"{_NET_PY}:480-482,484"),
    f"{NET}/summary/evaluable_count": _f("net.summary", f"{_NET_PY}:443-444,464-465,485"),
    f"{NET}/summary/profitable_count": _f("net.summary", f"{_NET_PY}:466-467,486"),
    f"{NET}/summary/avg_cost_drag_return": _f("net.cost_drag", f"{_NET_PY}:488-491"),
}
_FEATURE_MAPS = {
    FQ: {"adf_results", "autocorrelation_results", "drift_results", "coverage_stats"},
    NET: {"features"},
}
#: 已查之不一致（欄位 → 原因）；真實資料對照斷言其餘統計欄一致，本表欄位另以 xfail(strict=True) 斷言 oracle 行為
KNOWN_INCONSISTENT: Dict[str, str] = {
    f"{FQ}/quality_flags/non_stationary/#": "未檢定之欄標非平穩",
    f"{FQ}/summary/low_quality_count": "由上項導出",
    f"{FQ}/autocorrelation_results/*/effective_sample_ratio": "常數序列寫 1.0（應 NaN）；非常數欄另斷言一致",
    f"{NET}/features/*/turnover": "換手率定義與 net_factor_return 不同",
    f"{NET}/features/*/cost_drag_return": "同上",
    f"{NET}/features/*/cost_sensitivity/#/cost_drag_return": "同上",
    f"{NET}/features/*/capacity/estimated_capacity_usd": "同上",
    f"{NET}/features/*/capacity/capacity_tier": "同上",
    f"{NET}/summary/avg_cost_drag_return": "同上",
}


# ── 共用監看（同 test_icperf_correctness.py） ──────────────────────────────────────────────────────


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_gate.py：本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


def _rel(a: float, b: float) -> float:
    """相對誤差（兩者皆 NaN ⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


# ── 欄位路徑與通用比對 ──────────────────────────────────────────────────────────────────────────────


def _concrete(obj: Any, path: str = "") -> Dict[str, Any]:
    """巢狀 dict／list → {具體路徑: 葉值}；list 索引段寫 `#<i>`；空 dict／空 list 不產葉。"""
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_concrete(v, f"{path}/{k}" if path else str(k)))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out.update(_concrete(v, f"{path}/#{i}"))
    else:
        out[path] = obj
    return out


def _pattern(concrete_path: str, module: str) -> str:
    """具體路徑 → 欄位路徑（逐特徵段 `*`、list 索引 `#`）。"""
    segs = concrete_path.split("/")
    out: List[str] = []
    for i, seg in enumerate(segs):
        if seg.startswith("#"):
            out.append("#")
        elif i == 1 and segs[0] in _FEATURE_MAPS[module]:
            out.append("*")
        else:
            out.append(seg)
    return "/".join(out)


def field_keys(output: Any, module: str) -> set:
    """產品輸出之欄位路徑集合（含模組前綴）。"""
    return {f"{module}/{_pattern(p, module)}" for p in _concrete(output)}


def _is_float_like(v: Any) -> bool:
    return isinstance(v, (float, np.floating)) or v is None


def _value_diff(a: Any, b: Any) -> Tuple[bool, Optional[float]]:
    """回（相等, 相對誤差或 None）；浮點 rel ≤ REL_TOL；None 視同 NaN；bool／int／str 完全相等。"""
    if isinstance(a, (bool, np.bool_)) or isinstance(b, (bool, np.bool_)):
        return (isinstance(a, (bool, np.bool_)) and isinstance(b, (bool, np.bool_)) and bool(a) == bool(b)), None
    if isinstance(a, str) or isinstance(b, str):
        return a == b, None
    if isinstance(a, (int, np.integer)) and isinstance(b, (int, np.integer)):
        return int(a) == int(b), None
    if (_is_float_like(a) or isinstance(a, (int, np.integer))) and (_is_float_like(b) or isinstance(b, (int, np.integer))):
        fa = math.nan if a is None else float(a)
        fb = math.nan if b is None else float(b)
        r = _rel(fa, fb)
        return r <= REL_TOL, r
    return a == b, None


def _finite_leaf(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (float, np.floating)):
        return math.isfinite(float(v))
    return True


def _compare(product: Any, oracle: Any, module: str) -> Dict[str, Dict[str, Any]]:
    """對 MODULE_FIELDS 中該模組每一統計欄位逐具體路徑比對。"""
    p = _concrete(product)
    o = _concrete(oracle)
    by_pat: Dict[str, List[str]] = {}
    for key in set(p) | set(o):
        by_pat.setdefault(f"{module}/{_pattern(key, module)}", []).append(key)
    result: Dict[str, Dict[str, Any]] = {}
    for field, meta in MODULE_FIELDS.items():
        if not field.startswith(module + "/") or meta["oracle"] == NON_STAT:
            continue
        keys = sorted(by_pat.get(field, []))
        bad: List[str] = []
        rels: List[float] = []
        n_finite = 0
        for k in keys:
            if k not in p or k not in o:
                bad.append(f"{k}：{'產品' if k not in p else 'oracle'}缺鍵（產品={p.get(k)!r}，oracle={o.get(k)!r}）")
                continue
            if _finite_leaf(p[k]):
                n_finite += 1
            eq, r = _value_diff(p[k], o[k])
            if r is not None and math.isfinite(r):
                rels.append(r)
            if not eq:
                bad.append(f"{k}：產品={p[k]!r} oracle={o[k]!r}")
        result[field] = {
            "verdict": "一致" if not bad else "不一致",
            "max_rel_diff": max(rels) if rels else None,
            "n_finite": n_finite,
            "detail": "；".join(bad[:5]) if bad else ("兩方皆無此鍵（本輸入未走此分支）" if not keys else "")
        }
    return result


# ── 參考實作：feature_quality_diagnostics ───────────────────────────────────────────────────────────


def _fq_cfg(config: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    cfg = dict(config or {})
    return {
        "adf_significance": float(cfg.get("adf_significance", 0.05)),
        "ljungbox_lags": int(cfg.get("ljungbox_lags", 10)),
        "ljungbox_significance": float(cfg.get("ljungbox_significance", 0.05)),
        "coverage_threshold": float(cfg.get("coverage_threshold", 0.8)),
        "drift_threshold": float(cfg.get("drift_threshold", 0.25)),
        "redundancy_threshold": float(cfg.get("redundancy_threshold", 0.85)),
        "adf_min_samples": int(cfg.get("adf_min_samples", 20)),
    }


def _ref_adf(values: np.ndarray, significance: float, min_samples: int) -> Dict[str, Any]:
    """ADF oracle：分支同 `:38-64`；縮尾 1%／99%（`:305-308`，線性內插分位＝numpy 預設）；
    `adfuller(regression="c", autolag="AIC", maxlag=⌈12(n/100)^{1/4}⌉ 且 ≤ n//2−2)`（statsmodels 預設，產品 `:69` 未給參數）；
    無逾時（值不依牆鐘而變）。"""
    clean = values[~np.isnan(values)]
    nan_out = {"adf_statistic": math.nan, "p_value": math.nan, "is_stationary": False}
    if clean.size == 0:
        return {"skipped": True, "reason": "all_nan", **nan_out}
    if clean.size < min_samples:
        return {"skipped": True, "reason": "insufficient_samples", **nan_out}
    if np.unique(clean).size <= 1:
        return {"skipped": True, "reason": "constant_feature", **nan_out}
    lo, hi = np.quantile(clean, [0.01, 0.99])
    w = np.clip(clean, lo, hi)
    nobs = w.size
    maxlag = min(nobs // 2 - 1 - 1, int(np.ceil(12.0 * (nobs / 100.0) ** 0.25)))
    try:
        stat, pval, *_ = adfuller(w, maxlag=maxlag, regression="c", autolag="AIC")
    except Exception as exc:  # noqa: BLE001 — 同產品之例外分支
        return {"skipped": True, "reason": "adf_error", "error": str(exc), **nan_out}
    return {"adf_statistic": float(stat), "p_value": float(pval), "is_stationary": bool(float(pval) < significance),
            "skipped": False}


def _ref_ljungbox(values: np.ndarray, lags: int, significance: float) -> Dict[str, Any]:
    """Ljung–Box oracle：Q＝n(n+2)Σ_{k=1}^{L} ρ_k²／(n−k)，ρ_k＝Σ(x_t−x̄)(x_{t−k}−x̄)／Σ(x_t−x̄)²，p＝`scipy.stats.chi2.sf(Q, L)`
    （產品 `:116-118` 以 statsmodels `acorr_ljungbox`）；樣本＝去缺值後（`:103`）；不足 max(10, L+5) 跳過（`:104`）。
    有效樣本比 oracle：lag-1 相關 `scipy.stats.pearsonr`，ratio＝clip((1−ρ)／(1+ρ), 0, 1)；ρ 無定義 ⇒ NaN；ρ＝−1 ⇒ 1（極限）。"""
    x = values[~np.isnan(values)]
    n = x.size
    if n < max(10, lags + 5):
        return {"skipped": True, "reason": "insufficient_samples", "ljungbox_stat": math.nan, "p_value": math.nan,
                "significant_autocorrelation": False, "effective_sample_ratio": math.nan}
    with np.errstate(divide="ignore", invalid="ignore"):
        xc = x - x.mean()
        denom = float(np.dot(xc, xc))
        q = 0.0
        for k in range(1, lags + 1):
            rho = float(np.dot(xc[k:], xc[:-k])) / denom if denom != 0.0 else math.nan
            q += rho * rho / (n - k)
        q *= n * (n + 2)
    p = float(stats.chi2.sf(q, lags))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rho1 = float(stats.pearsonr(x[:-1], x[1:])[0])
    if not math.isfinite(rho1):
        ess = math.nan
    elif rho1 <= -1.0:
        ess = 1.0
    else:
        ess = float(min(1.0, max(0.0, (1.0 - rho1) / (1.0 + rho1))))
    return {"ljungbox_stat": float(q), "p_value": p, "significant_autocorrelation": bool(p < significance),
            "effective_sample_ratio": ess, "skipped": False}


def _ref_psi(front: np.ndarray, back: np.ndarray, bins: int = 10) -> float:
    """PSI oracle（產品 `:321-337`）：兩半合併之等分位邊界（numpy 線性分位）去重；邊界 < 3 ⇒ 0；
    計數以 `searchsorted`（左閉右開、末箱右閉，同直方圖慣例）自算；比例截 [1e-8, 1]；PSI＝Σ(f−b)·ln(f／b)。"""
    if front.size < 5 or back.size < 5:
        return math.nan
    edges = np.unique(np.quantile(np.concatenate([front, back]), np.linspace(0, 1, bins + 1)))
    if edges.size < 3:
        return 0.0

    def counts(v: np.ndarray) -> np.ndarray:
        idx = np.searchsorted(edges, v, side="right") - 1
        idx = np.where(v == edges[-1], edges.size - 2, idx)
        idx = idx[(idx >= 0) & (idx <= edges.size - 2)]
        return np.bincount(idx, minlength=edges.size - 1).astype(float)

    fc, bc = counts(front), counts(back)
    fr = np.clip(fc / max(1.0, fc.sum()), 1e-8, 1.0)
    br = np.clip(bc / max(1.0, bc.sum()), 1e-8, 1.0)
    return float(np.sum((fr - br) * np.log(fr / br)))


def _ref_drift(series: Optional[pd.Series], name: str, drift_threshold: float, reason_absent: str) -> Dict[str, Any]:
    """漂移 oracle：去缺值後 < 20 跳過（`:145-154`）；斷點＝argmax|Σ(x−x̄)| 之索引標籤（同產品，取首次）；
    CUSUM 判定＝`breaks_cusumolsresid(x−x̄, ddof=0)` 之 p < ORACLE_CUSUM_ALPHA；PSI 前後兩半（`:162-165`）＞門檻；兩者取或。"""
    if series is None:
        return {"feature_name": name, "skipped": True, "reason": reason_absent, "cusum_breakpoint": None,
                "psi_score": math.nan, "drifted": False}
    s = pd.Series(series, dtype=float)
    vals = s.to_numpy(dtype=float)
    keep = ~np.isnan(vals)
    x = vals[keep]
    labels = s.index[keep]
    if x.size < 20:
        return {"feature_name": name, "skipped": True, "reason": "insufficient_rolling_ic", "cusum_breakpoint": None,
                "psi_score": math.nan, "drifted": False}
    centered = x - x.mean()
    cum = np.cumsum(centered)
    bp = labels[int(np.argmax(np.abs(cum)))]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _, cusum_p, _ = breaks_cusumolsresid(centered, ddof=0)
    mid = x.size // 2
    psi = _ref_psi(x[:mid], x[mid:])
    drifted = bool((math.isfinite(cusum_p) and cusum_p < ORACLE_CUSUM_ALPHA)
                   or (math.isfinite(psi) and psi > drift_threshold))
    return {"feature_name": name, "cusum_breakpoint": str(bp), "psi_score": psi if math.isfinite(psi) else math.nan,
            "drifted": drifted, "skipped": False}


def _ref_redundancy(df: pd.DataFrame, threshold: float) -> Dict[str, Any]:
    """冗餘預掃 oracle（產品 `:190-217` 以 pandas `corr(method="spearman")`）：逐對兩欄共同非缺值列以
    `scipy.stats.spearmanr` 重算 |ρ|，有限且 ≥ 門檻入列（列序＝欄序 i<j）。"""
    if df.shape[1] < 2:
        return {"high_correlation_pairs": [], "threshold": threshold, "method": "spearman", "skipped": True}
    cols = list(df.columns)
    arr = df.to_numpy(dtype=float)
    pairs: List[List[Any]] = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            m = ~np.isnan(arr[:, i]) & ~np.isnan(arr[:, j])
            if m.sum() < 2:
                continue
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                rho = float(stats.spearmanr(arr[m, i], arr[m, j])[0])
            v = abs(rho)
            if math.isfinite(v) and v >= threshold:
                pairs.append([cols[i], cols[j], v])
    return {"high_correlation_pairs": pairs, "threshold": threshold, "method": "spearman", "skipped": False}


def ref_feature_quality_diagnostics(
    features_df: pd.DataFrame,
    rolling_ic_dict: Optional[Mapping[str, pd.Series]] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """`FeatureQualityDiagnostics(config).run_full_diagnostics(features_df, rolling_ic_dict)` 之獨立參考實作。
    旗標（oracle 定義）：非平穩＝已做 ADF（未跳過）且 p 有限且 ≥ α；高自相關＝Ljung–Box p < α；低覆蓋＝覆蓋 < 門檻；
    漂移＝上列 oracle。摘要：平穩率＝平穩數／總欄數（同產品 `:298`），平均覆蓋＝逐欄覆蓋均值，低品質數＝四旗標聯集大小。"""
    c = _fq_cfg(config)
    cols = list(features_df.columns)
    adf: Dict[str, Any] = {}
    ac: Dict[str, Any] = {}
    cov: Dict[str, Any] = {}
    drift: Dict[str, Any] = {}
    total = len(features_df)
    for name in cols:
        v = features_df[name].to_numpy(dtype=float)
        adf[name] = _ref_adf(v, c["adf_significance"], c["adf_min_samples"])
        ac[name] = _ref_ljungbox(v, c["ljungbox_lags"], c["ljungbox_significance"])
        nn = int((~np.isnan(v)).sum())
        cov[name] = {"coverage": float(nn / total) if total > 0 else 0.0, "nan_count": int(total - nn), "total": int(total)}
        if rolling_ic_dict:
            series = rolling_ic_dict.get(name)
            drift[name] = _ref_drift(series, name, c["drift_threshold"], "rolling_ic_missing")
        else:
            drift[name] = _ref_drift(None, name, c["drift_threshold"], "rolling_ic_unavailable")
    flags = {
        "non_stationary": [n for n in cols if not adf[n]["skipped"] and math.isfinite(adf[n]["p_value"])
                           and adf[n]["p_value"] >= c["adf_significance"]],
        "high_autocorrelation": [n for n in cols if ac[n]["significant_autocorrelation"]],
        "low_coverage": [n for n in cols if cov[n]["coverage"] < c["coverage_threshold"]],
        "drifted": [n for n in cols if drift[n]["drifted"]],
    }
    stationary = sum(1 for n in cols if adf[n]["is_stationary"])
    low = set().union(*[set(v) for v in flags.values()])
    return {
        "adf_results": adf,
        "autocorrelation_results": ac,
        "drift_results": drift,
        "coverage_stats": cov,
        "redundancy_scan": _ref_redundancy(features_df, c["redundancy_threshold"]),
        "quality_flags": flags,
        "summary": {
            "total_features": len(cols),
            "stationary_rate": float(stationary / len(cols)) if cols else 0.0,
            "mean_coverage": float(np.mean([cov[n]["coverage"] for n in cols])) if cols else 0.0,
            "low_quality_count": len(low),
        },
    }


def compare_feature_quality_diagnostics(
    product_output: Mapping[str, Any],
    features_df: pd.DataFrame,
    rolling_ic_dict: Optional[Mapping[str, pd.Series]] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """產品 `run_full_diagnostics` 輸出 vs oracle；輸入＝產品公開入口之同一組（features_df、rolling_ic_dict、建構 config）。"""
    return _compare(product_output, ref_feature_quality_diagnostics(features_df, rolling_ic_dict, config), FQ)


# ── 參考實作：net_ic_analysis ──────────────────────────────────────────────────────────────────────


def _ref_series(obj: Any) -> Optional[Tuple[pd.Series, pd.Series]]:
    """取 (ls_return, position)；裸 Series／缺欄／空 ⇒ None（同 `net_ic_analyzer.py:55-73` 之契約）。"""
    if obj is None:
        return None
    ls = getattr(obj, "ls_return", None)
    pos = getattr(obj, "position", None)
    if ls is None and isinstance(obj, dict):
        ls, pos = obj.get("ls_return"), obj.get("position")
    if not isinstance(ls, pd.Series) or not isinstance(pos, pd.Series) or ls.empty or pos.empty:
        return None
    return ls, pos


def _ref_series_turnover(ls: pd.Series, pos: pd.Series) -> Tuple[np.ndarray, np.ndarray]:
    """逐根 PIT 換手率 |position_t − position_{t−1}|（首根 0，只用 t−1、t）；與 ls_return 依索引對齊、去缺值。"""
    p = pos.to_numpy(dtype=float)
    to = np.empty_like(p)
    if p.size:
        to[0] = 0.0
        to[1:] = np.abs(p[1:] - p[:-1])
    frame = pd.concat([ls.rename("g"), pd.Series(to, index=pos.index, name="t")], axis=1).dropna()
    return frame["g"].to_numpy(dtype=float), frame["t"].to_numpy(dtype=float)


def _ref_unavail(reason: str) -> Dict[str, Any]:
    return {"status": "unavailable", "value": None, "reason": reason}


def _ref_ok(value: Any) -> Dict[str, Any]:
    return {"status": "ok", "value": value, "reason": None}


def _ref_capacity(turnover: float, volume: Optional[float], rate: float) -> Dict[str, Any]:
    """容量 oracle（產品 `:239-285`）：無量能 ⇒ None／unknown；否則 量能×參與率／換手率（換手率 0 ⇒ 不除）；
    級距：換手率 > 1 ⇒ low、> 0.5 ⇒ medium、否則 high。"""
    t = max(0.0, turnover)
    if volume is None or volume <= 0:
        return {"estimated_capacity_usd": None, "capacity_tier": "unknown", "calibration": "uncalibrated"}
    cap = volume * rate if t <= 0 else volume * rate / t
    tier = "low" if t > 1.0 else ("medium" if t > 0.5 else "high")
    return {"estimated_capacity_usd": cap if math.isfinite(cap) else None, "capacity_tier": tier,
            "calibration": "uncalibrated"}


def ref_net_ic_analysis(
    ic_summary: Mapping[str, Mapping[str, Any]],
    turnover_data: Mapping[str, Any],
    factor_return_series: Optional[Mapping[str, Any]] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """`NetICAnalyzer(config).batch_analyze(ic_summary, turnover_data, factor_return_series)` 之獨立參考實作。
    跳過分支同產品（換手率輸入缺／非有限／負、gross 缺）；**換手率 oracle**＝該特徵因子擇時序列之
    mean(|Δposition|)（序列有效時；無序列時退用輸入值），成本拖累＝(c／10⁴)×換手率（＝gross 均值 − net 均值），
    階梯、容量同此換手率；net＝mean(ls_t − (c／10⁴)·|Δposition_t|)（c 未啟用 ⇒ 0）、損益兩平＝mean(ls)／mean(|Δposition|)×10⁴。"""
    cfg = dict(config or {})
    cost_enabled = bool(cfg.get("cost_enabled", False))
    cost_bps = None if cfg.get("cost_bps") is None else float(cfg["cost_bps"])
    rate = float(cfg.get("participation_rate", 0.01))
    series_map = factor_return_series or {}
    if not turnover_data:
        return {"skipped": True, "reason": "turnover_not_available", "features": {},
                "summary": {"total_analyzed": 0, "evaluable_count": 0, "profitable_count": 0}}
    feats: Dict[str, Any] = {}
    drags: List[float] = []
    n_eval = 0
    n_prof = 0
    for name, metric in ic_summary.items():
        if name not in turnover_data:
            feats[name] = {"skipped": True, "reason": "turnover_missing"}
            continue
        try:
            t_in = float(turnover_data[name])
        except (TypeError, ValueError):
            feats[name] = {"skipped": True, "reason": "non_finite_turnover"}
            continue
        if not math.isfinite(t_in):
            feats[name] = {"skipped": True, "reason": "non_finite_turnover"}
            continue
        if t_in < 0.0:
            feats[name] = {"skipped": True, "reason": "negative_turnover"}
            continue
        g_raw = metric.get("gross_ic", metric.get("ic_mean", metric.get("mean_ic", math.nan)))
        try:
            g = float(g_raw)
        except (TypeError, ValueError):
            g = math.nan
        if not math.isfinite(g):
            feats[name] = {"skipped": True, "reason": "gross_ic_missing"}
            continue
        sobj = series_map.get(name)
        ext = _ref_series(sobj)
        use_c = cost_bps if cost_enabled else None
        cond: Dict[str, Any]
        evaluable = False
        profitable = False
        turnover = t_in
        if ext is None:
            reason = "factor_return_series_missing_or_invalid" if sobj is not None else \
                "canonical_factor_return_series_not_built (1c-FR)"
            cond = {"net_factor_return": _ref_unavail(reason)}
            if cost_enabled:
                cond["breakeven_cost_bps"] = _ref_unavail(reason)
                cond["profitable_after_cost"] = _ref_unavail(reason)
        else:
            gross, to = _ref_series_turnover(*ext)
            if gross.size == 0:
                reason = "insufficient_aligned_series"
                cond = {"net_factor_return": _ref_unavail(reason)}
                if cost_enabled:
                    cond["breakeven_cost_bps"] = _ref_unavail(reason)
                    cond["profitable_after_cost"] = _ref_unavail(reason)
            else:
                c = 0.0 if use_c is None else use_c
                gm = float(np.mean(gross))
                tm = float(np.mean(to))
                net = float(np.mean(gross - (c / 10000.0) * to))
                turnover = tm
                if not math.isfinite(tm) or tm == 0.0:
                    be, reason_be = None, "zero_mean_turnover"
                elif not math.isfinite(gm) or not math.isfinite(net):
                    net, be, reason_be = math.nan, None, "insufficient_aligned_series"
                else:
                    be, reason_be = gm / tm * 10000.0, None
                if not math.isfinite(net):
                    r = reason_be or "insufficient_aligned_series"
                    cond = {"net_factor_return": _ref_unavail(r)}
                    if cost_enabled:
                        cond["breakeven_cost_bps"] = _ref_unavail(r)
                        cond["profitable_after_cost"] = _ref_unavail(r)
                else:
                    evaluable = True
                    profitable = net > 0.0
                    cond = {"net_factor_return": _ref_ok(net)}
                    if cost_enabled:
                        cond["breakeven_cost_bps"] = _ref_ok(be) if be is not None and math.isfinite(be) \
                            else _ref_unavail(reason_be or "zero_mean_turnover")
                        cond["profitable_after_cost"] = _ref_ok(profitable)
        vol = metric.get("avg_daily_volume_usd")
        cap = _ref_capacity(turnover, float(vol) if vol is not None else None, rate)
        row: Dict[str, Any] = {"gross_ic": g, "turnover": turnover, "turnover_semantics": "membership_change_both_legs_per_bar",
                               "capacity": cap}
        if evaluable:
            n_eval += 1
        if cost_enabled:
            assert cost_bps is not None
            drag = cost_bps / 10000.0 * turnover
            drags.append(drag)
            ladder = sorted({round(min(1000.0, max(0.1, x)), 1)
                             for x in (cost_bps / 2.0, cost_bps, 2.0 * cost_bps, 5.0 * cost_bps)})
            row.update({"cost_bps": cost_bps, "cost_semantics": "per_rebalance_not_annualized", "cost_drag_return": drag,
                        "cost_sensitivity": [{"cost_bps": float(s), "cost_drag_return": s / 10000.0 * turnover}
                                             for s in ladder]})
            if evaluable and profitable:
                n_prof += 1
        row.update(cond)
        feats[name] = row
    summary: Dict[str, Any] = {"total_analyzed": sum(1 for v in feats.values() if not v.get("skipped")),
                               "evaluable_count": n_eval, "profitable_count": n_prof}
    if cost_enabled:
        summary["avg_cost_drag_return"] = float(np.mean(drags)) if drags else None
    return {"features": feats, "summary": summary}


def compare_net_ic_analysis(
    product_output: Mapping[str, Any],
    ic_summary: Mapping[str, Mapping[str, Any]],
    turnover_data: Mapping[str, Any],
    factor_return_series: Optional[Mapping[str, Any]] = None,
    config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    """產品 `batch_analyze` 輸出 vs oracle；輸入＝產品公開入口之同一組（三參數＋建構 config）。"""
    return _compare(product_output, ref_net_ic_analysis(ic_summary, turnover_data, factor_return_series, config), NET)


def _assert_consistent(cmp: Dict[str, Dict[str, Any]], fields: Optional[Sequence[str]] = None,
                       exclude: Sequence[str] = ()) -> None:
    for field, r in cmp.items():
        if fields is not None and field not in fields:
            continue
        if field in exclude:
            continue
        assert r["verdict"] == "一致", f"{field}：{r['detail']}"


# ── 秒級：feature_quality_diagnostics 邊界 ─────────────────────────────────────────────────────────


def _ar1(n: int, phi: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    e = rng.normal(size=n)
    x = np.empty(n)
    x[0] = e[0]
    for t in range(1, n):
        x[t] = phi * x[t - 1] + e[t]
    return x


def _boundary_frame() -> pd.DataFrame:
    """明列邊界輸入（SPEC §V 單元邊界案）：AR(1) 平穩、隨機漫步、首段缺值、剛好 20／19 筆、常數、全缺、縮尾後常數。"""
    n = 200
    rw = np.cumsum(np.random.default_rng(1).normal(size=n))
    head_nan = _ar1(n, 0.3, 2)
    head_nan[:50] = np.nan
    exactly20 = np.full(n, np.nan)
    exactly20[-20:] = _ar1(20, 0.1, 3)
    only19 = np.full(n, np.nan)
    only19[-19:] = _ar1(19, 0.1, 4)
    wconst = np.zeros(n)
    wconst[-1] = 5.0  # 唯一非零 < 1% 尾 ⇒ 縮尾後常數 ⇒ adfuller 例外
    return pd.DataFrame({
        "ar1": _ar1(n, 0.5, 0), "rw": rw, "head_nan": head_nan, "exactly20": exactly20, "only19": only19,
        "const": np.full(n, 3.0), "allnan": np.full(n, np.nan), "wconst": wconst,
    })


def test_fq_adf_coverage_matches_oracle_boundaries() -> None:
    """ADF（stat、p、平穩、跳過與原因）、覆蓋率對 statsmodels／自算 oracle：每一邊界欄之分支與數值一致。"""
    df = _boundary_frame()
    out = FeatureQualityDiagnostics({}).run_full_diagnostics(df)
    cmp = compare_feature_quality_diagnostics(out, df)
    adf_fields = [k for k in cmp if "/adf_results/" in k or "/coverage_stats/" in k]
    _assert_consistent(cmp, adf_fields)
    assert out["adf_results"]["wconst"]["reason"] == "adf_error"
    assert {out["adf_results"][k]["reason"] for k in ("const", "allnan", "only19")} == {
        "constant_feature", "all_nan", "insufficient_samples"}
    assert math.isfinite(out["adf_results"]["exactly20"]["p_value"])
    assert cmp[f"{FQ}/adf_results/*/adf_statistic"]["n_finite"] >= 4


@pytest.mark.parametrize("lags", [1, 3, 10])
def test_fq_ljungbox_ess_match_oracle_boundaries(lags: int) -> None:
    """Ljung–Box（Q、p、顯著、跳過）與有效樣本比對自算 Q 公式＋`scipy.stats.chi2.sf`／`pearsonr`：
    樣本數＝max(10, L+5)−1（跳過）與＝max(10, L+5)（計算）兩邊界、首段缺值、AR(1) 強弱自相關、負自相關（截 1）。"""
    need = max(10, lags + 5)
    n = 300
    cols: Dict[str, np.ndarray] = {}
    for tag, m in (("below", need - 1), ("at", need)):
        v = np.full(n, np.nan)
        v[-m:] = _ar1(m, 0.4, 10 + m)
        cols[tag] = v
    cols["strong"] = _ar1(n, 0.95, 11)
    cols["weak"] = _ar1(n, 0.05, 12)
    cols["neg"] = _ar1(n, -0.6, 13)
    hn = _ar1(n, 0.5, 14)
    hn[:40] = np.nan
    cols["head_nan"] = hn
    df = pd.DataFrame(cols)
    cfg = {"ljungbox_lags": lags}
    out = FeatureQualityDiagnostics(cfg).run_full_diagnostics(df)
    cmp = compare_feature_quality_diagnostics(out, df, config=cfg)
    _assert_consistent(cmp, [k for k in cmp if "/autocorrelation_results/" in k])
    assert out["autocorrelation_results"]["below"]["skipped"] is True
    assert out["autocorrelation_results"]["at"]["skipped"] is False
    assert out["autocorrelation_results"]["neg"]["effective_sample_ratio"] == 1.0


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：常數序列 lag-1 自相關無定義，有效樣本比寫 1.0（應 NaN）；"
                                        f"收據 {RECEIPT}")
def test_fq_ess_undefined_for_constant_series() -> None:
    """常數序列（ρ₁ 無定義）之有效樣本比 oracle＝NaN；產品 `feature_quality_diagnostics.py:316-317` 回 1.0（宣稱樣本完全獨立）。"""
    df = pd.DataFrame({"const": np.full(50, 2.0)})
    out = FeatureQualityDiagnostics({}).run_batch_autocorrelation_test(df)
    assert math.isnan(out["const"]["effective_sample_ratio"])


def _drift_inputs() -> Tuple[pd.DataFrame, Dict[str, pd.Series]]:
    """滾動 IC 邊界：19 筆（跳過）、20 筆（計算）、含缺值、少相異值（PSI 邊界 < 3 ⇒ 0）、強均值移位（兩定義皆判漂移）、缺鍵。"""
    n = 120
    df = pd.DataFrame({k: _ar1(n, 0.2, i) for i, k in enumerate(["s19", "s20", "gap", "few", "shift", "nokey"])})
    rng = np.random.default_rng(7)
    gap = rng.normal(size=80)
    gap[[3, 10, 50]] = np.nan
    shift = np.r_[rng.normal(-1.0, 0.1, 60), rng.normal(1.0, 0.1, 60)]
    few = np.zeros(30)
    few[-1] = 0.5
    ric = {
        "s19": pd.Series(np.r_[0.1 + rng.normal(0, 0.01, 19), np.nan]),
        "s20": pd.Series(np.r_[rng.normal(0.4, 0.05, 10), rng.normal(-0.4, 0.05, 10)]),
        "gap": pd.Series(gap),
        "few": pd.Series(few),
        "shift": pd.Series(shift),
    }
    return df, ric


def test_fq_drift_psi_breakpoint_match_oracle_boundaries() -> None:
    """漂移：跳過分支、PSI（自算計數）、CUSUM 斷點（argmax |Σ|）、均值大幅移位時之漂移判定，皆與 oracle 一致；
    滾動 IC 缺鍵 ⇒ rolling_ic_missing；未給滾動 IC ⇒ rolling_ic_unavailable。"""
    df, ric = _drift_inputs()
    out = FeatureQualityDiagnostics({}).run_full_diagnostics(df, rolling_ic_dict=ric)
    cmp = compare_feature_quality_diagnostics(out, df, ric)
    _assert_consistent(cmp, [f"{FQ}/drift_results/*/skipped", f"{FQ}/drift_results/*/reason",
                             f"{FQ}/drift_results/*/cusum_breakpoint", f"{FQ}/drift_results/*/psi_score"])
    assert out["drift_results"]["s19"]["reason"] == "insufficient_rolling_ic"
    assert out["drift_results"]["nokey"]["reason"] == "rolling_ic_missing"
    assert out["drift_results"]["few"]["psi_score"] == 0.0
    assert out["drift_results"]["shift"]["drifted"] is True
    ref = ref_feature_quality_diagnostics(df, ric)
    assert ref["drift_results"]["shift"]["drifted"] is True
    none = FeatureQualityDiagnostics({}).run_full_diagnostics(df)
    _assert_consistent(compare_feature_quality_diagnostics(none, df), [f"{FQ}/drift_results/*/reason"])


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：CUSUM 漂移門檻 5σ 未隨 √n 縮放，無漂移之序列（n≥~30）恆判漂移；"
                                        f"收據 {RECEIPT}")
@pytest.mark.parametrize("n", [200, 1000])
def test_fq_drift_iid_noise_not_flagged(n: int) -> None:
    """無結構變化之 i.i.d. 常態序列：oracle（statsmodels `breaks_cusumolsresid`，p ≫ 0.05；PSI < 門檻）判未漂移；
    產品 `feature_quality_diagnostics.py:158-160` max|S_k| > 5σ（未除 √n）⇒ 判漂移（實測種子 100–149 之 n=1000 序列 50/50 判漂移）。"""
    df = pd.DataFrame({"x": np.zeros(10)})
    ric = {"x": pd.Series(np.random.default_rng(100).normal(size=n))}
    ref = ref_feature_quality_diagnostics(df, ric)["drift_results"]["x"]
    assert ref["drifted"] is False
    out = FeatureQualityDiagnostics({}).detect_concept_drift(ric["x"], "x")
    assert out["drifted"] is ref["drifted"]


def test_fq_redundancy_matches_scipy_boundaries() -> None:
    """冗餘預掃對逐對 `scipy.stats.spearmanr`（兩欄共同非缺值列）：含缺值對、常數欄（ρ NaN 不入列）、|ρ|＝1 恰等於門檻 1.0
    （≥ 含等號）、負相關取絕對值；單欄 ⇒ skipped。"""
    rng = np.random.default_rng(5)
    a = rng.normal(size=150)
    b = a.copy()
    b[:20] = np.nan
    c = -a ** 3
    d = rng.normal(size=150)
    d[100:] = np.nan
    df = pd.DataFrame({"a": a, "b": b, "c": c, "d": d, "k": np.ones(150)})
    for thr in (0.85, 1.0, 0.0):
        cfg = {"redundancy_threshold": thr}
        out = FeatureQualityDiagnostics(cfg).redundancy_pre_scan(df)
        ref = _ref_redundancy(df, thr)
        cmp = _compare({"redundancy_scan": out}, {"redundancy_scan": ref}, FQ)
        _assert_consistent(cmp, [f"{FQ}/redundancy_scan/high_correlation_pairs/#/#", f"{FQ}/redundancy_scan/skipped"])
    assert [p[:2] for p in FeatureQualityDiagnostics({"redundancy_threshold": 1.0}).redundancy_pre_scan(df)
            ["high_correlation_pairs"]] == [["a", "b"], ["a", "c"], ["b", "c"]]
    single = FeatureQualityDiagnostics({}).redundancy_pre_scan(df[["a"]])
    assert single["skipped"] is True and single["high_correlation_pairs"] == []


def test_fq_flags_summary_match_oracle_when_all_tested() -> None:
    """全部欄皆實際檢定（無跳過）且漂移以兩定義同判之輸入：四旗標與摘要（平穩率、平均覆蓋、低品質數）與 oracle 一致；
    空特徵表 ⇒ 摘要 0、旗標空、冗餘 skipped。"""
    rng = np.random.default_rng(9)
    n = 240
    rw = np.cumsum(rng.normal(size=n))
    low = _ar1(n, 0.2, 21)
    low[:100] = np.nan
    df = pd.DataFrame({"ar": _ar1(n, 0.2, 20), "rw": rw, "low": low, "noise": rng.normal(size=n)})
    ric = {"ar": pd.Series(np.r_[rng.normal(-1, 0.1, 30), rng.normal(1, 0.1, 30)]),
           "noise": pd.Series(np.r_[rng.normal(-1, 0.1, 30), rng.normal(1, 0.1, 30)])}
    out = FeatureQualityDiagnostics({}).run_full_diagnostics(df, rolling_ic_dict=ric)
    cmp = compare_feature_quality_diagnostics(out, df, ric)
    _assert_consistent(cmp)
    assert "rw" in out["quality_flags"]["non_stationary"] and "low" in out["quality_flags"]["low_coverage"]
    assert cmp[f"{FQ}/summary/stationary_rate"]["n_finite"] == 1
    empty = pd.DataFrame(index=range(10))
    e_out = FeatureQualityDiagnostics({}).run_full_diagnostics(empty)
    _assert_consistent(compare_feature_quality_diagnostics(e_out, empty))
    assert e_out["summary"] == {"total_features": 0, "stationary_rate": 0.0, "mean_coverage": 0.0, "low_quality_count": 0}


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：未做 ADF 檢定之欄（全缺／樣本不足／常數／ADF 例外）仍列入"
                                        f"non_stationary 並計入低品質數；收據 {RECEIPT}")
def test_fq_skipped_adf_not_flagged_non_stationary() -> None:
    """oracle：非平穩旗標只含已做 ADF 且 p ≥ α 之欄；產品 `feature_quality_diagnostics.py:264`、`:269-270` 以
    `is_stationary=False` 判，跳過之欄（`:44`、`:53`、`:62`、`:85`、`:95` 寫死 False）一律標非平穩。"""
    df = _boundary_frame()
    out = FeatureQualityDiagnostics({}).run_full_diagnostics(df)
    cmp = compare_feature_quality_diagnostics(out, df)
    _assert_consistent(cmp, [f"{FQ}/quality_flags/non_stationary/#", f"{FQ}/summary/low_quality_count"])


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：ADF 逾時（牆鐘上限）即丟棄已算之值改 NaN／跳過，且 with 區塊"
                                        f"仍等待工作執行緒算完、逾時不省時間；收據 {RECEIPT}")
def test_fq_adf_value_independent_of_wall_clock() -> None:
    """oracle：ADF 值與牆鐘無關（使用者 2026-10-27「全專案禁時間上限停運算」）。產品 `feature_quality_diagnostics.py:68-70`
    以 `future.result` 帶逾時參數等待，逾時 ⇒ `:78-86` 跳過；`ThreadPoolExecutor.__exit__` 為 `shutdown(wait=True)`，逾時後仍待算完。
    以極小逾時（建構 config `adf_timeout_sec`；生產路徑為預設 5 秒，2 萬列 ADF 本機實測 1.7–3.5 秒／欄）重現。"""
    df = pd.DataFrame({"x": np.cumsum(np.random.default_rng(3).normal(size=400))})
    cfg = {"adf_timeout_sec": 1e-9}
    out = FeatureQualityDiagnostics(cfg).run_batch_adf_test(df)
    ref = _ref_adf(df["x"].to_numpy(), 0.05, 20)
    assert out["x"]["skipped"] is False
    assert _rel(out["x"]["adf_statistic"], ref["adf_statistic"]) <= REL_TOL


# ── 秒級：net_ic_analysis 邊界 ────────────────────────────────────────────────────────────────────


def _series(pos: Sequence[int], ls: Sequence[float], name: str = "f") -> FactorTimingReturnSeries:
    idx = pd.date_range("2024-01-01", periods=len(pos), freq="h", tz="UTC")
    return FactorTimingReturnSeries(feature=name, ls_return=pd.Series(ls, index=idx, dtype=float),
                                    position=pd.Series(pos, index=idx, dtype=int), index_policy="frame_dropna")


def _series_turnover(s: FactorTimingReturnSeries) -> float:
    _, to = _ref_series_turnover(s.ls_return, s.position)
    return float(np.mean(to))


def _net_inputs() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """明列邊界：雙邊翻倉（|Δ|＝2）、零換手（持倉不變）、ls 含 NaN（對齊去缺值）、虧損、無序列、裸 Series（形狀無效）、
    換手率缺鍵／NaN／負／非數、gross 缺／NaN；容量級距邊界（換手率 0、0.5、0.7、1.5）。"""
    rng = np.random.default_rng(31)
    flip = _series([0, 1, -1, -1, 1, 0, 0, 1, 1, -1] * 3, rng.normal(0.001, 0.01, 30))
    hold = _series([1] * 25, rng.normal(0.002, 0.01, 25))
    ls_nan = rng.normal(0.0, 0.01, 20)
    ls_nan[[2, 7]] = np.nan
    gap = _series([0, 1, 1, 0, -1] * 4, ls_nan)
    loss = _series([1, -1] * 10, np.full(20, -0.001))
    series = {"flip": flip, "hold": hold, "gap": gap, "loss": loss, "bare": pd.Series([0.1, 0.2])}
    turnover: Dict[str, Any] = {k: _series_turnover(v) for k, v in series.items() if k != "bare"}
    turnover.update({"bare": 0.5, "noser": 0.7, "big": 1.5, "nan_t": math.nan, "neg_t": -0.1, "str_t": "x",
                     "nan_g": 0.3, "none_g": 0.3})
    summary = {k: {"ic_mean": 0.05 + 0.01 * i} for i, k in enumerate(
        ["flip", "hold", "gap", "loss", "bare", "noser", "big", "nan_t", "neg_t", "str_t", "missing_t"])}
    summary["nan_g"] = {"ic_mean": math.nan}
    summary["none_g"] = {"ic_mean": None}
    summary["noser"]["avg_daily_volume_usd"] = 2.0e8
    summary["big"]["avg_daily_volume_usd"] = 2.0e8
    summary["flip"]["avg_daily_volume_usd"] = 1.0e8
    summary["hold"]["avg_daily_volume_usd"] = 1.0e8
    return summary, turnover, series


@pytest.mark.parametrize("cfg", [{}, {"cost_enabled": True, "cost_bps": 10.0}, {"cost_enabled": True, "cost_bps": 0.15},
                                 {"cost_enabled": True, "cost_bps": 400.0, "participation_rate": 0.05}])
def test_net_ic_matches_oracle_boundaries(cfg: Dict[str, Any]) -> None:
    """換手率輸入取序列之 mean(|Δposition|)（兩定義重合之輸入）時，全部統計欄（跳過分支與原因、gross、換手率、容量與級距、
    成本拖累與階梯〔c／2 截 0.1、5c 截 1000、四捨五入 0.1 去重〕、net、損益兩平、獲利、摘要）與 oracle 一致；
    三 profile（gross-only、成本啟用 10／0.15／400 bps）。"""
    summary, turnover, series = _net_inputs()
    out = NetICAnalyzer(cfg).batch_analyze(summary, turnover, factor_return_series=series)
    cmp = compare_net_ic_analysis(out, summary, turnover, series, cfg)
    _assert_consistent(cmp)
    f = out["features"]
    assert f["hold"]["net_factor_return"]["status"] == "ok"
    if cfg.get("cost_enabled"):
        assert f["hold"]["breakeven_cost_bps"] == {"status": "unavailable", "value": None, "reason": "zero_mean_turnover"}
        assert f["flip"]["breakeven_cost_bps"]["status"] == "ok"
    assert {f[k]["reason"] for k in ("nan_t", "neg_t", "str_t", "missing_t", "nan_g", "none_g")} == {
        "non_finite_turnover", "negative_turnover", "turnover_missing", "gross_ic_missing"}
    assert f["bare"]["net_factor_return"]["reason"] == "factor_return_series_missing_or_invalid"
    assert f["big"]["capacity"]["capacity_tier"] == "low" and f["noser"]["capacity"]["capacity_tier"] == "medium"
    empty = NetICAnalyzer(cfg).batch_analyze(summary, {})
    _assert_consistent(compare_net_ic_analysis(empty, summary, {}, None, cfg))
    assert empty["skipped"] is True


@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：turnover／cost_drag_return／成本階梯／容量用第 5 段頂分位單邊"
                                        "quantile_turnover，與同列 net_factor_return／breakeven 之逐根 |Δposition| 不同定義；"
                                        f"收據 {RECEIPT}")
def test_net_ic_turnover_consistent_with_series() -> None:
    """oracle：同一列之成本拖累＝gross 均值 − net 均值＝(c／10⁴)·mean(|Δposition|)。輸入之 quantile_turnover 0.2（頂分位單邊）
    與序列換手率 mean(|Δposition|) 不同時，產品 `net_ic_analyzer.py:457`、`:470`、`:476` 用前者、`:316` 用後者。"""
    s = _series([0, 1, -1, -1, 1, 0, 0, 1, 1, -1] * 3, np.random.default_rng(2).normal(0.001, 0.01, 30))
    cfg = {"cost_enabled": True, "cost_bps": 10.0}
    out = NetICAnalyzer(cfg).batch_analyze({"f": {"ic_mean": 0.05}}, {"f": 0.2}, factor_return_series={"f": s})
    row = out["features"]["f"]
    gm = float(s.ls_return.mean())
    drag_identity = gm - row["net_factor_return"]["value"]
    assert abs(row["cost_drag_return"] - drag_identity) <= 1e-15 + REL_TOL * abs(drag_identity)
    assert _rel(row["turnover"], _series_turnover(s)) <= REL_TOL


def test_net_ic_caller_passes_quantile_turnover_and_disabled_envelope() -> None:
    """呼叫端 `ic_filter_orchestrator.py:3233-3268`：turnover 停用 ⇒ {status: unavailable, reason: turnover_disabled}；
    否則 ic_summary 只帶 summary_table 之 ic_mean（無 avg_daily_volume_usd ⇒ 容量恆 unknown）、換手率取 quantile_turnover。"""
    stub = SimpleNamespace(
        _report={"turnover_analysis": {"status": "disabled", "reason": "turnover_disabled"}},
        _factor_return_series={},
        _net_ic_payload_depends_on_series_owner=ICFilterOrchestrator._net_ic_payload_depends_on_series_owner,
    )
    out = ICFilterOrchestrator._run_net_ic(stub, ["f"], ICConfig())
    assert out == {"status": "unavailable", "reason": "turnover_disabled"}
    s = _series([0, 1, 1, -1, 0] * 6, np.random.default_rng(4).normal(0.0, 0.01, 30))
    stub._report = {"summary_table": [{"feature_name": "f", "ic_mean": 0.03}],
                    "turnover_analysis": {"f": {"quantile_turnover": 0.25}}}
    stub._factor_return_series = {"f": s}
    got = ICFilterOrchestrator._run_net_ic(stub, ["f"], ICConfig())
    direct = NetICAnalyzer(ICConfig().net_ic_analysis.model_dump()).batch_analyze(
        {"f": {"ic_mean": 0.03}}, {"f": 0.25}, factor_return_series={"f": s})
    assert got == direct
    assert got["features"]["f"]["turnover"] == 0.25 and got["features"]["f"]["capacity"]["capacity_tier"] == "unknown"


# ── 真實 kline（requires_kline） ─────────────────────────────────────────────────────────────────


def _real_kline(rows: int = L_ROWS, symbol: str = "BTCUSDT") -> pd.DataFrame:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.DataFrame({k: data[k].astype("float64") for k in ("close", "volume", "quote_volume")}, index=idx)


def _real_fq_features(k: pd.DataFrame) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）：報酬、兩均線偏離（高相關對）、對數價（非平穩）、量能篩選之報酬（低覆蓋）、
    大跳動指示（縮尾後常數 ⇒ ADF 例外）、常數、末 12 根（樣本不足）、全缺。"""
    c = k["close"]
    ret1 = c.pct_change()
    short = ret1.copy()
    short.iloc[:-12] = np.nan
    return pd.DataFrame({
        "ret1": ret1,
        "dev20": c / c.rolling(20).mean() - 1.0,
        "dev24": c / c.rolling(24).mean() - 1.0,
        "logc": np.log(c),
        "sparse": ret1.where(k["volume"] > k["volume"].rolling(24).median()),
        "spike": ret1.where(ret1.abs() > 0.03, 0.0),
        "const": c * 0.0 + 1.0,
        "short": short,
        "allnan": pd.Series(np.nan, index=k.index),
    })


def _rolling_ic_lists(feat: pd.Series, label: pd.Series, windows: Sequence[int]) -> Dict[str, List[float]]:
    """測試端建滾動 IC 輸入（形狀同 `ic_engine.py:454-465`：{window_w: list}）：逐窗 `scipy.stats.spearmanr`，只用特徵與標籤
    皆有限之列。"""
    pair = pd.concat([feat, label], axis=1).dropna().to_numpy(dtype=float)
    out: Dict[str, List[float]] = {}
    for w in windows:
        vals: List[float] = []
        for end in range(w, pair.shape[0] + 1):
            seg = pair[end - w:end]
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                vals.append(float(stats.spearmanr(seg[:, 0], seg[:, 1])[0]))
        out[f"window_{w}"] = vals
    return out


def _extract_longest(window_dict: Mapping[str, List[float]]) -> pd.Series:
    """測試端獨立重寫呼叫端取用規則（`ic_filter_orchestrator.py:3362-3372`）：取最長 list（同長取首鍵）、RangeIndex。"""
    best = None
    for k, v in window_dict.items():
        if best is None or len(v) > len(window_dict[best]):
            best = k
    return pd.Series(window_dict[best] if best is not None else [], dtype=float)


def _real_fq_case() -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, pd.Series], Dict[str, Any]]:
    k = _real_kline()
    feats = _real_fq_features(k)
    label = (k["close"].shift(-1) / k["close"] - 1.0).rename("label")
    ric: Dict[str, Any] = {name: _rolling_ic_lists(feats[name], label, (63, 126))
                           for name in ("ret1", "dev20", "dev24", "logc", "spike")}
    ric["sparse"] = {"window_63": _rolling_ic_lists(feats["sparse"], label, (63,))["window_63"][:10]}
    stub = SimpleNamespace(_ic_cache={"features_df": feats, "rolling_ic": ric},
                           _extract_rolling_ic_series=ICFilterOrchestrator._extract_rolling_ic_series)
    out = ICFilterOrchestrator._run_feature_quality_diagnostics(stub, list(feats.columns), ICConfig())
    series = {n: _extract_longest(v) for n, v in ric.items()}
    return feats, out, series, ICConfig().feature_quality_diagnostics.model_dump()


def _real_net_case(cost_cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Tuple[Any, ...], Dict[str, Any]]:
    """真實 BTCUSDT 1h 末 2,000 根；標籤＝1 根前瞻報酬；因子擇時序列由產品第 6 段 `FactorReturnAnalyzer.compute_batch`（全樣本）、
    quantile_turnover 由第 5 段 `TurnoverAnalyzer.compute_all`（末 20% 測試段，同 `ic_filter_orchestrator.py:4400`、`:4502`）、
    ic_mean 以測試段 `scipy.stats.spearmanr`；經呼叫端 `_run_net_ic`。"""
    k = _real_kline()
    c = k["close"]
    feats = pd.DataFrame({
        "ret1": c.pct_change(), "dev20": c / c.rolling(20).mean() - 1.0, "logc": np.log(c), "const": c * 0.0 + 1.0,
        "nanic": c / c.rolling(48).mean() - 1.0, "nofr": c.pct_change(5), "noturn": c.pct_change(3),
    })
    label = (c.shift(-1) / c - 1.0).rename("label")
    cfg = ICConfig(net_ic_analysis=cost_cfg)
    fr = FactorReturnAnalyzer(cfg.factor_return.model_dump())
    # nofr：有換手率、無因子擇時序列（net 三欄 unavailable）；noturn：無換手率（turnover_missing）
    fr.compute_batch(feats.drop(columns=["nofr"]), label, top_n=feats.shape[1])
    test = feats.iloc[int(len(feats) * 0.8):]
    turnover = TurnoverAnalyzer(cfg.turnover.model_dump()).compute_all(test.drop(columns=["noturn"]))
    rows = []
    for name in feats.columns:
        pair = pd.concat([test[name], label.loc[test.index]], axis=1).dropna().to_numpy(dtype=float)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            ic = float(stats.spearmanr(pair[:, 0], pair[:, 1])[0]) if pair.shape[0] > 2 else math.nan
        rows.append({"feature_name": name, "ic_mean": math.nan if name == "nanic" else ic})
    stub = SimpleNamespace(_report={"summary_table": rows, "turnover_analysis": turnover},
                           _factor_return_series=fr.get_series_map(),
                           _net_ic_payload_depends_on_series_owner=ICFilterOrchestrator._net_ic_payload_depends_on_series_owner)
    selected = list(feats.columns)
    out = ICFilterOrchestrator._run_net_ic(stub, selected, cfg)
    ic_summary = {r["feature_name"]: {"ic_mean": r["ic_mean"]} for r in rows}
    turnover_data = {n: float(d["quantile_turnover"]) for n, d in turnover.items() if n in selected}
    inputs = (ic_summary, turnover_data, fr.get_series_map(), cfg.net_ic_analysis.model_dump())
    extra = {"kline": k, "stub": stub, "selected": selected, "cfg": cfg}
    return out, inputs, extra


def _daily_usd_volume(k: pd.DataFrame) -> float:
    """平均日成交額（USD）：quote_volume 依 UTC 日加總之均值（只取完整日）。"""
    daily = k["quote_volume"].groupby(k.index.floor("D")).agg(["sum", "count"])
    return float(daily.loc[daily["count"] == 24, "sum"].mean())


@pytest.mark.requires_kline
def test_quality_netic_fields_closed() -> None:
    """封閉集合：真實 kline 小輸入上執行產品（呼叫端路徑＋走遍分支之輸入：逾時、Ljung–Box 例外、成本啟用／停用、
    換手率停用、換手率全缺）之實際欄位路徑聯集 == MODULE_FIELDS 鍵集合。"""
    feats, fq_out, _, _ = _real_fq_case()
    keys = field_keys(fq_out, FQ)
    small = feats[["logc", "ret1"]].iloc[-300:]
    keys |= field_keys(FeatureQualityDiagnostics({"adf_timeout_sec": 1e-9}).run_full_diagnostics(small), FQ)

    def _boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("forced ljungbox failure")

    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(fq_mod, "acorr_ljungbox", _boom)
        keys |= field_keys(FeatureQualityDiagnostics({}).run_full_diagnostics(small), FQ)
    finally:
        mp.undo()
    for cost in ({"cost_enabled": True, "cost_bps": 10.0}, {}):
        out, _, extra = _real_net_case(cost)
        keys |= field_keys(out, NET)
    stub = extra["stub"]
    stub._report = {"summary_table": stub._report["summary_table"], "turnover_analysis": {}}
    keys |= field_keys(ICFilterOrchestrator._run_net_ic(stub, extra["selected"], extra["cfg"]), NET)
    stub._report = {"turnover_analysis": {"status": "disabled", "reason": "turnover_disabled"}}
    keys |= field_keys(ICFilterOrchestrator._run_net_ic(stub, extra["selected"], extra["cfg"]), NET)
    assert keys == set(MODULE_FIELDS), (f"產品多出：{sorted(keys - set(MODULE_FIELDS))}；"
                                        f"清冊多出：{sorted(set(MODULE_FIELDS) - keys)}")


@pytest.mark.requires_kline
def test_feature_quality_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h 末 2,000 根，經呼叫端 `_run_feature_quality_diagnostics`：除 KNOWN_INCONSISTENT 外之統計欄全一致，
    且每一統計欄至少一個有限值（資料充足判準）。"""
    feats, out, series, cfg = _real_fq_case()
    cmp = compare_feature_quality_diagnostics(out, feats, series, cfg)
    _assert_consistent(cmp, exclude=list(KNOWN_INCONSISTENT))
    empty = [f for f, r in cmp.items() if r["n_finite"] == 0]
    assert not empty, f"無有限值之統計欄：{empty}"
    assert out["adf_results"]["spike"]["reason"] == "adf_error"
    # 有效樣本比：常數欄以外之欄須一致（常數欄之不一致另由 xfail 斷言）
    ess = f"{FQ}/autocorrelation_results/*/effective_sample_ratio"
    nonconst = [c for c in feats.columns if c != "const"]
    out_nc = {"autocorrelation_results": {c: out["autocorrelation_results"][c] for c in nonconst}}
    ref_nc = {"autocorrelation_results": ref_feature_quality_diagnostics(feats[nonconst], series, cfg)
              ["autocorrelation_results"]}
    r = _compare(out_nc, ref_nc, FQ)[ess]
    assert r["verdict"] == "一致" and r["n_finite"] >= 1, r["detail"]
    # 真實滾動 IC（重疊窗、強自相關）上兩種 CUSUM 定義皆判漂移，漂移欄於本資料一致（不一致之反例見 i.i.d. xfail）
    assert cmp[f"{FQ}/drift_results/*/drifted"]["verdict"] == "一致"


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：真實資料上常數欄之有效樣本比寫 1.0（lag-1 自相關無定義，應 NaN）；"
                                        f"收據 {RECEIPT}")
def test_feature_quality_ess_constant_on_real_kline() -> None:
    """真實 BTCUSDT 1h：常數欄 `autocorrelation_results.const.effective_sample_ratio` == oracle（NaN）。"""
    feats, out, series, cfg = _real_fq_case()
    cmp = compare_feature_quality_diagnostics(out, feats, series, cfg)
    _assert_consistent(cmp, [f"{FQ}/autocorrelation_results/*/effective_sample_ratio"])


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：真實資料上常數／樣本不足／全缺／ADF 例外之欄列為非平穩；"
                                        f"收據 {RECEIPT}")
def test_feature_quality_non_stationary_flag_on_real_kline() -> None:
    """真實 BTCUSDT 1h：`quality_flags.non_stationary` 與低品質數 == oracle（只含已檢定且 p ≥ α 之欄）。"""
    feats, out, series, cfg = _real_fq_case()
    cmp = compare_feature_quality_diagnostics(out, feats, series, cfg)
    _assert_consistent(cmp, [f"{FQ}/quality_flags/non_stationary/#"])


@pytest.mark.requires_kline
def test_net_ic_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h，經呼叫端 `_run_net_ic`（成本啟用 10 bps 與 gross-only），另以真實日成交額直呼模組驗容量：
    除 KNOWN_INCONSISTENT 外之統計欄全一致，且每一統計欄至少一個有限值。"""
    finite: Dict[str, int] = {}
    for cost in ({"cost_enabled": True, "cost_bps": 10.0}, {}):
        out, inputs, extra = _real_net_case(cost)
        cmp = compare_net_ic_analysis(out, *inputs)
        _assert_consistent(cmp, exclude=list(KNOWN_INCONSISTENT))
        for f_, r in cmp.items():
            finite[f_] = finite.get(f_, 0) + r["n_finite"]
        assert out["features"]["ret1"]["net_factor_return"]["status"] == "ok"
    ic_summary, turnover_data, series, _ = inputs
    vol = _daily_usd_volume(extra["kline"])
    with_vol = {n: {**m, "avg_daily_volume_usd": vol} for n, m in ic_summary.items()}
    cfg_cost = {"cost_enabled": True, "cost_bps": 10.0}
    # 換手率輸入改為序列換手率（兩定義重合）以驗容量、成本拖累與階梯公式本身
    to_series = {n: (_series_turnover(series[n]) if n in series else t) for n, t in turnover_data.items()}
    direct_eq = NetICAnalyzer(cfg_cost).batch_analyze(with_vol, to_series, factor_return_series=series)
    cmp_eq = compare_net_ic_analysis(direct_eq, with_vol, to_series, series, cfg_cost)
    _assert_consistent(cmp_eq)
    for f_, r in cmp_eq.items():
        finite[f_] = finite.get(f_, 0) + r["n_finite"]
    assert direct_eq["features"]["ret1"]["capacity"]["estimated_capacity_usd"] is not None
    empty = [f_ for f_, n in finite.items() if n == 0]
    assert not empty, f"無有限值之統計欄：{empty}"


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason="ICPERF Task 0.3 不一致：真實資料上 turnover／cost_drag_return 為測試段頂分位單邊換手率，"
                                        "非同列 net_factor_return 所用全樣本雙邊 |Δposition|；收據 " + RECEIPT)
def test_net_ic_turnover_consistent_with_series_on_real_kline() -> None:
    """真實 BTCUSDT 1h（成本 10 bps）：每一有序列之特徵 turnover == mean(|Δposition|)、cost_drag_return == (c／10⁴)·該值。"""
    out, inputs, _ = _real_net_case({"cost_enabled": True, "cost_bps": 10.0})
    cmp = compare_net_ic_analysis(out, *inputs)
    _assert_consistent(cmp, [f"{NET}/features/*/turnover", f"{NET}/features/*/cost_drag_return"])
