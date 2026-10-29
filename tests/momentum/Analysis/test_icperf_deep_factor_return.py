"""ICPERF Task 0.3 深度分析 oracle 對照：factor_return 組（docs/ICPERF_SPEC.md Task 0.3／0.4，第 108、109、123–127 行）。

涵蓋兩模組（深度報告 `results` 之鍵）：
- `factor_returns`＝`momentum/Analysis/factor_return_analyzer.py` `FactorReturnAnalyzer.compute_batch`（呼叫端
  `ic_filter_orchestrator.py:2934-2952` `_run_factor_return`；定義＝1c-FR canonical 單標的逐因子擇時多空，PIT expanding
  分位 membership：頂分位 +1／底分位 −1／其餘 0，`ls_return = position * future_return`）。
- `long_short_analysis`＝`momentum/Analysis/long_short_analyzer.py` `LongShortAnalyzer.batch_analyze`（呼叫端
  `ic_filter_orchestrator.py:3201-3207` `_run_long_short`；PIT 分箱 `pit_expanding_qcut_label(min_samples=100,
  require_full_q=True)`，RB-3：分箱只看特徵自身時序）。

本檔為**稽核**：參考實作 `ref_factor_return`／`ref_long_short` 依產品公式（逐式註明產品 `檔:行`）以 numpy／pandas／scipy
獨立重算，**不呼叫被測模組或其內部函式**；以下三處 oracle 採正確定義而非照抄產品（各有 xfail(strict=True) 證實其不一致）：
  ① 頂分位＝當根實際箱數 k_t 之最大標籤 k_t−1（`pd.qcut(duplicates="drop")` 減箱後；k_t < 2 ⇒ 無頂底、position 0）——
     產品 `factor_return_analyzer.py:335-351` 以 `q_eff − 1` 判頂（SPEC 第 125 行；與 Task 0.4 ① 同型）；
  ② factor_return 之分箱歷史＝特徵自身有限值 0..t（同 RB-3，`long_short_analyzer.py:47-50`），不受標籤可得性影響——
     產品 `factor_return_analyzer.py:78-81` 以特徵∩標籤 dropna 後之序列建（SPEC 第 127 行）；
  ③ long_short 之分箱樣本門檻以**有限值**計數（同模組 finite gate，`long_short_analyzer.py:25-28`）——產品經
     `pit_stats.effective_count`（`pit_stats.py:49-52`，計 ~isnan，±inf 亦計）。
業界定義差異（Sortino 下行偏差、年化報酬 CAGR、h 根重疊標籤之年化、非 24/7 市場之年化期數）另以 xfail 記錄，
參考實作本身照產品公式（compare 只驗產品是否照其自身公式算對）。

不一致收據：handoffs/run_receipts/<日期>-icperf-correctness.json（主委彙整）。
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.long_short_analyzer import LongShortAnalyzer
from momentum.factories import create_factor_return_analyzer

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
REL_TOL = 1e-12
HEAVY_MARKERS = ("slow", "requires_kline")
RECEIPT = "handoffs/run_receipts/<日期>-icperf-correctness.json"
NON_STAT = "非統計欄"
FR_KEY = "factor_returns"
LS_KEY = "long_short_analysis"
#: 產品預設標籤 horizon（`ic_config_schema.py:20` `default_horizon = 5`）
DEFAULT_H = 5
#: long_short 分箱樣本門檻（`long_short_analyzer.py:22` `_BIN_MIN_SAMPLES = MIN_SAMPLES`，`pit_stats.py:39` = 100）
LS_BIN_MIN = 100

FRA = "momentum/Analysis/factor_return_analyzer.py"
LSA = "momentum/Analysis/long_short_analyzer.py"


# ── 共用監看（同 test_icperf_correctness.py） ───────────────────────────────────────────────────────


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """同 test_icperf_gate.py：本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── 欄位清冊 ─────────────────────────────────────────────────────────────────────────────────────────

_RISK_PRODUCERS = {
    "sharpe_ratio": f"{FRA}:219-226",
    "sortino_ratio": f"{FRA}:228-238",
    "calmar_ratio": f"{FRA}:248-256",
    "max_drawdown": f"{FRA}:240-247",
    "win_rate": f"{FRA}:258-260",
    "annualized_return": f"{FRA}:205-210",
    "annualized_volatility": f"{FRA}:212-217",
}
_FR_FEAT = f"{FR_KEY}/value/features/*"
_LS_FEAT = f"{LS_KEY}/*"

MODULE_FIELDS: Dict[str, Dict[str, str]] = {
    f"{FR_KEY}/status": {"oracle": NON_STAT, "producer": f"{FRA}:305"},
    f"{FR_KEY}/reason": {"oracle": NON_STAT, "producer": f"{FRA}:315"},
    f"{FR_KEY}/value/schema_version": {"oracle": NON_STAT, "producer": f"{FRA}:307"},
    f"{FR_KEY}/value/semantics": {"oracle": NON_STAT, "producer": f"{FRA}:308"},
    f"{FR_KEY}/value/quantile_fit": {"oracle": NON_STAT, "producer": f"{FRA}:309"},
    f"{FR_KEY}/value/return_transform": {"oracle": NON_STAT, "producer": f"{FRA}:310"},
    f"{FR_KEY}/value/turnover_semantics": {"oracle": NON_STAT, "producer": f"{FRA}:311"},
    f"{FR_KEY}/value/warmup_periods": {"oracle": NON_STAT, "producer": f"{FRA}:312"},
    f"{_FR_FEAT}/long_short_mean_return": {"oracle": "fr.ls_mean", "producer": f"{FRA}:133,165"},
    f"{_FR_FEAT}/ls_cumulative_sampled/#": {"oracle": "fr.ls_cumulative", "producer": f"{FRA}:138,166,377-383"},
    **{f"{_FR_FEAT}/risk_metrics/{k}": {"oracle": f"fr.risk.{k}", "producer": v} for k, v in _RISK_PRODUCERS.items()},
    f"{_FR_FEAT}/active_bar_count": {"oracle": "fr.position_pit", "producer": f"{FRA}:139,319-352"},
    f"{_FR_FEAT}/turnover": {"oracle": "fr.turnover", "producer": f"{FRA}:140-141"},
    f"{_FR_FEAT}/quantile_summary/descriptive_full_sample": {"oracle": NON_STAT, "producer": f"{FRA}:361"},
    **{f"{_FR_FEAT}/quantile_summary/Q{i}": {"oracle": "fr.quantile_summary", "producer": f"{FRA}:362-374"}
       for i in range(1, 6)},
    f"{_FR_FEAT}/num_quantiles_used": {"oracle": NON_STAT, "producer": f"{FRA}:119,171"},
    f"{_FR_FEAT}/newey_west_adjusted": {"oracle": NON_STAT, "producer": f"{FRA}:172"},
    **{f"{_LS_FEAT}/{side}_analysis/{k}": {"oracle": o, "producer": f"{LSA}:{p}"}
       for side in ("long", "short")
       for k, o, p in (("mean_return", "ls.side_mean", "219,223"), ("ic", "ls.side_ic_spearman", "212-216"),
                       ("hit_rate", "ls.side_hit_rate", "225"), ("sharpe", "ls.side_sharpe", "218-220"),
                       ("samples", "ls.pit_bins", "211,227"), ("side", NON_STAT, "226"))},
    f"{_LS_FEAT}/asymmetry/type": {"oracle": "ls.asymmetry", "producer": f"{LSA}:244-250"},
    f"{_LS_FEAT}/asymmetry/long_contribution": {"oracle": "ls.asymmetry", "producer": f"{LSA}:236-254"},
    f"{_LS_FEAT}/asymmetry/short_contribution": {"oracle": "ls.asymmetry", "producer": f"{LSA}:236-255"},
    f"{_LS_FEAT}/asymmetry/ratio": {"oracle": "ls.asymmetry", "producer": f"{LSA}:244"},
    f"{_LS_FEAT}/recommendation": {"oracle": "ls.recommendation", "producer": f"{LSA}:145-157,259-269"},
    f"{_LS_FEAT}/num_quantiles_used": {"oracle": NON_STAT, "producer": f"{LSA}:103,165"},
    f"{_LS_FEAT}/skipped": {"oracle": NON_STAT, "producer": f"{LSA}:181"},
    f"{_LS_FEAT}/reason": {"oracle": NON_STAT, "producer": f"{LSA}:182"},
    f"{_LS_FEAT}/error_type": {"oracle": NON_STAT, "producer": f"{LSA}:183"},
}


# ── 參考實作：factor_return ─────────────────────────────────────────────────────────────────────────


def _fr_cfg(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """產品預設（`factor_return_analyzer.py:33-40`）。"""
    cfg = dict(config or {})
    return {
        "q": int(cfg.get("num_quantiles", 5)),
        "rf": float(cfg.get("risk_free_rate", 0.0)),
        "min_samples": int(cfg.get("min_samples", 30)),
        "warmup": int(cfg.get("warmup_periods", 20)),
    }


def _qcut_last(hist: np.ndarray, q: int) -> Tuple[Optional[int], int]:
    """`pd.qcut(hist, q, duplicates="drop")` 之末筆（當根）標籤與實際箱數 k（相異邊界數 − 1）；不可分 ⇒ (None, 0)。"""
    try:
        labels, edges = pd.qcut(hist, q, labels=False, duplicates="drop", retbins=True)
    except ValueError:
        return None, 0
    last = np.asarray(labels, dtype=float)[-1]
    if not np.isfinite(last):
        return None, len(edges) - 1
    return int(last), len(edges) - 1


def ref_fr_position(feature: pd.Series, frame_index: pd.Index, q: int, warmup: int) -> pd.Series:
    """PIT expanding 邊分位 position（產品 `factor_return_analyzer.py:319-352` 之正確定義）。

    第 t 根：歷史＝特徵自身於 0..t 之有限值（oracle ②，不受標籤可得性影響）；有限歷史序位 < warmup ⇒ 0（`:332`）；
    q_eff＝min(q, 歷史相異值數)（`:335`），< 2 ⇒ 0；`pd.qcut(歷史, q_eff, duplicates="drop")` 之當根標籤 ℓ、實際箱數 k；
    k < 2 ⇒ 0；ℓ＝k−1 ⇒ +1（oracle ①；產品 `:348` 用 q_eff−1）；ℓ＝0 ⇒ −1（`:350`）。只用 0..t。
    """
    vals = pd.Series(feature, dtype=float).to_numpy()
    fin = np.isfinite(vals)
    cum = np.cumsum(fin)
    pos_of = {ts: i for i, ts in enumerate(feature.index)}
    out = np.zeros(len(frame_index), dtype=int)
    for j, ts in enumerate(frame_index):
        i = pos_of[ts]
        if cum[i] - 1 < warmup:
            continue
        hist = vals[: i + 1][fin[: i + 1]]
        q_eff = min(int(q), int(np.unique(hist).size))
        if q_eff < 2:
            continue
        label, k = _qcut_last(hist, q_eff)
        if label is None or k < 2:
            continue
        if label == k - 1:
            out[j] = 1
        elif label == 0:
            out[j] = -1
    return pd.Series(out, index=frame_index, dtype=int)


def ref_periods_per_year(index: pd.Index) -> int:
    """`factor_return_analyzer.py:385-394`：非 DatetimeIndex 或 < 2 列 ⇒ 365；否則 round(24·365／相鄰間隔中位數〔時〕)。"""
    if not isinstance(index, pd.DatetimeIndex) or len(index) < 2:
        return 365
    med_h = float(np.median(np.diff(index.asi8) / 1e9)) / 3600.0
    if not np.isfinite(med_h) or med_h <= 0:
        return 365
    return int(round((24.0 * 365.0) / med_h))


def ref_risk_metrics(returns: Sequence[float], rf: float = 0.0, periods: Optional[int] = None) -> Dict[str, float]:
    """`factor_return_analyzer.py:175-270` 之公式（numpy 重算）。"""
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    nan = float("nan")
    keys = ("sharpe_ratio", "sortino_ratio", "calmar_ratio", "max_drawdown", "win_rate",
            "annualized_return", "annualized_volatility")
    if r.size == 0:
        return {k: nan for k in keys}
    P = int(periods or 365)
    m = float(np.mean(r))
    s = float(np.std(r, ddof=1)) if r.size > 1 else nan
    try:  # :205-210
        ann = float((1.0 + m) ** P - 1.0)
        if not math.isfinite(ann) or abs(ann) > 1e6:
            ann = nan
    except (OverflowError, ValueError):
        ann = nan
    vol = float(s * math.sqrt(P)) if math.isfinite(s) and s > 0 else nan  # :212-217
    rfp = rf / P
    sharpe = float((m - rfp) / s * math.sqrt(P)) if math.isfinite(s) and s > 0 else nan  # :219-224
    down = r[r < 0.0]
    dstd = float(np.std(down, ddof=1)) if down.size >= 2 else nan  # :228-229
    sortino = float((m - rfp) / dstd * math.sqrt(P)) if math.isfinite(dstd) and dstd > 0 else nan
    eq = np.cumprod(1.0 + r)  # :240-245
    with np.errstate(divide="ignore", invalid="ignore"):
        dd = eq / np.maximum.accumulate(eq) - 1.0
    mdd = float(np.min(dd))
    if not math.isfinite(mdd):
        mdd = nan
    calmar = float(ann / abs(mdd)) if math.isfinite(ann) and math.isfinite(mdd) and mdd < 0 else nan  # :248-254
    win = float(np.mean(r > 0))
    out = {"sharpe_ratio": sharpe, "sortino_ratio": sortino, "calmar_ratio": calmar, "max_drawdown": mdd,
           "win_rate": win, "annualized_return": ann, "annualized_volatility": vol}
    return {k: (v if math.isfinite(v) else nan) for k, v in out.items()}


def _ref_quantile_summary(feat: np.ndarray, y: np.ndarray, q: int) -> Dict[str, Any]:
    """`factor_return_analyzer.py:354-375`：全樣本描述性分位平均報酬（Q{標籤+1}）。"""
    out: Dict[str, Any] = {"descriptive_full_sample": True}
    q_eff = min(int(q), int(np.unique(feat).size))
    if q_eff < 2:
        return out
    try:
        bins = np.asarray(pd.qcut(feat, q=q_eff, labels=False, duplicates="drop"), dtype=float)
    except ValueError:
        return out
    for lab in np.unique(bins[np.isfinite(bins)]):
        sel = y[bins == lab]
        out[f"Q{int(lab) + 1}"] = float(np.mean(sel)) if sel.size else float("nan")
    return out


def _ref_sample(values: np.ndarray, max_points: int = 100) -> List[float]:
    """`factor_return_analyzer.py:377-383`：dropna 後 ≤ max_points 原樣，否則 linspace 取整索引。"""
    v = values[~np.isnan(values)]
    if v.size <= max_points:
        return [float(x) for x in v]
    idx = np.linspace(0, v.size - 1, max_points).astype(int)
    return [float(x) for x in v[idx]]


def _ref_fr_feature(feature: pd.Series, y: pd.Series, cfg: Dict[str, Any]
                    ) -> Tuple[Optional[Dict[str, Any]], Optional[pd.Series]]:
    """單特徵 oracle：回 (結果 dict 或 None〔產品 SkippedResult，`compute_batch` 不入 features〕, position)。"""
    f = pd.Series(feature, dtype=float)
    yy = pd.Series(y, dtype=float).reindex(f.index)
    fv, yv = f.to_numpy(), yy.to_numpy()
    m = np.isfinite(fv) & np.isfinite(yv)  # :78-97 特徵∩標籤有限
    n = int(m.sum())
    if n < cfg["min_samples"]:  # :99
        return None, None
    fm, ym = fv[m], yv[m]
    if np.unique(fm).size <= 1:  # :105
        return None, None
    if float(np.std(ym)) == 0.0:  # :110
        return None, None
    frame_index = f.index[m]
    pos = ref_fr_position(f, frame_index, cfg["q"], cfg["warmup"])
    pv = pos.to_numpy()
    if int((pv != 0).sum()) == 0:  # :127
        return None, pos
    ls = pv.astype(float) * ym  # :133
    cum = np.cumprod(1.0 + ls) - 1.0  # :138
    turnover = float(np.concatenate([[0.0], np.abs(np.diff(pv.astype(float)))]).mean())  # :140-141
    result = {
        "long_short_mean_return": float(np.mean(ls)),
        "ls_cumulative_sampled": _ref_sample(cum),
        "risk_metrics": ref_risk_metrics(ls, cfg["rf"], ref_periods_per_year(frame_index)),
        "active_bar_count": int((pv != 0).sum()),
        "turnover": turnover,
        "quantile_summary": _ref_quantile_summary(fm, ym, cfg["q"]),
        "num_quantiles_used": cfg["q"],
        "newey_west_adjusted": False,
    }
    return result, pos


def ref_factor_return(features_df: pd.DataFrame, future_returns: pd.Series, top_n: int = 30,
                      config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """`FactorReturnAnalyzer(config).compute_batch(features_df, future_returns, top_n)` 之 oracle（`:272-316`）。"""
    cfg = _fr_cfg(config)
    feats: Dict[str, Any] = {}
    for name in list(features_df.columns)[: max(1, int(top_n))]:  # :281
        res, _ = _ref_fr_feature(features_df[name], future_returns, cfg)
        if res is not None:
            feats[str(name)] = res
    return {"status": "ok", "value": {
        "schema_version": "fr_full_v1", "semantics": "single_asset_factor_timing_ls", "quantile_fit": "pit_expanding",
        "return_transform": "identity", "turnover_semantics": "abs_delta_position_p1",
        "warmup_periods": cfg["warmup"], "features": feats}, "reason": None}


# ── 參考實作：long_short ────────────────────────────────────────────────────────────────────────────


def _ls_cfg(config: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """產品預設（`long_short_analyzer.py:33-39`）。"""
    cfg = dict(config or {})
    return {"q": int(cfg.get("num_quantiles", 5)), "long": list(cfg.get("long_quantiles", [4, 5])),
            "short": list(cfg.get("short_quantiles", [1, 2])), "min_samples": int(cfg.get("min_samples", 30))}


def ref_ls_bins(feature: pd.Series, q: int) -> pd.Series:
    """PIT expanding 分箱（產品 `long_short_analyzer.py:41-61` → `pit_stats.py:356-403`）：第 t 根特徵有限、有限歷史數
    ≥ 100（oracle ③）、`pd.qcut(有限歷史, q, duplicates="drop")` 之歷史實得標籤種數 ≥ q（require_full_q）⇒ 當根標籤。"""
    vals = pd.Series(feature, dtype=float).to_numpy()
    fin = np.isfinite(vals)
    cum = np.cumsum(fin)
    out = np.full(vals.size, np.nan)
    for t in range(vals.size):
        if not fin[t] or cum[t] < LS_BIN_MIN:
            continue
        hist = vals[: t + 1][fin[: t + 1]]
        try:
            labels = np.asarray(pd.qcut(hist, q, labels=False, duplicates="drop"), dtype=float)
        except ValueError:
            continue
        if np.unique(labels[np.isfinite(labels)]).size < q:
            continue
        if np.isfinite(labels[-1]):
            out[t] = labels[-1]
    return pd.Series(out, index=feature.index, dtype=float)


def _ref_side(x: np.ndarray, y: np.ndarray, side: str) -> Dict[str, Any]:
    """`long_short_analyzer.py:191-229`：IC＝scipy.stats.rankdata（平均名次）後 Pearson（np.corrcoef）。"""
    fin = np.isfinite(x) & np.isfinite(y)
    if not fin.any():
        return {"mean_return": float("nan"), "ic": float("nan"), "hit_rate": float("nan"), "sharpe": float("nan"),
                "side": side, "samples": 0}
    xf, yf = x[fin], y[fin]
    n = int(yf.size)
    if n < 2 or np.unique(xf).size <= 1 or np.unique(yf).size <= 1:
        ic = float("nan")
    else:
        ic = float(np.corrcoef(stats.rankdata(xf), stats.rankdata(yf))[0, 1])
        ic = ic if math.isfinite(ic) else float("nan")
    sd = float(np.std(yf, ddof=1)) if n > 1 else float("nan")
    mu = float(np.mean(yf))
    return {"mean_return": mu, "ic": ic, "hit_rate": float(np.mean(yf > 0)),
            "sharpe": float(mu / sd) if math.isfinite(sd) and sd > 0 else float("nan"), "side": side, "samples": n}


def _ref_asym(lr: float, sr: float) -> Dict[str, Any]:
    """`long_short_analyzer.py:231-257`。"""
    la = abs(lr) if math.isfinite(lr) else 0.0
    sa = abs(sr) if math.isfinite(sr) else 0.0
    tot = la + sa
    if tot == 0.0:
        return {"type": "symmetric", "long_contribution": 0.5, "short_contribution": 0.5, "ratio": 1.0}
    ratio = la / sa if sa > 0 else float("inf")
    typ = "long_dominant" if ratio > 1.5 else ("short_dominant" if ratio < 1 / 1.5 else "symmetric")
    return {"type": typ, "long_contribution": la / tot, "short_contribution": sa / tot, "ratio": ratio}


def _ref_recommend(long_side: Dict[str, Any], short_side: Dict[str, Any]) -> str:
    """`long_short_analyzer.py:145-157`、`:259-269`。"""
    if long_side["samples"] == 0 or short_side["samples"] == 0:
        return "不建議"
    li, si = long_side["ic"], short_side["ic"]
    lg, sg = math.isfinite(li) and li > 0, math.isfinite(si) and si > 0
    if not math.isfinite(li) and not math.isfinite(si):
        return "不建議"
    return {(True, True): "雙向交易", (True, False): "只做多", (False, True): "只做空"}.get((lg, sg), "不建議")


def _ref_ls_feature(feature: pd.Series, future_returns: pd.Series, cfg: Dict[str, Any]) -> Dict[str, Any]:
    f = pd.Series(feature, dtype=float)
    r = pd.Series(future_returns, dtype=float).reindex(f.index)  # :89
    fv, rv = f.to_numpy(), r.to_numpy()
    n_pair = int((np.isfinite(fv) & np.isfinite(rv)).sum())
    if n_pair < cfg["min_samples"]:  # :95-101
        return {"skipped": True, "reason": f"insufficient samples: {n_pair} < {cfg['min_samples']}",
                "error_type": "INSUFFICIENT_DATA"}
    q = max(2, cfg["q"])  # :103
    bins = ref_ls_bins(f, q).to_numpy()
    if int(np.isfinite(bins).sum()) == 0 and int(np.isfinite(fv).sum()) < LS_BIN_MIN:  # :109-119
        return {"skipped": True, "reason": "cannot form quantiles", "error_type": "NUMERICAL_ERROR"}
    long_q = [k for k in cfg["long"] if 1 <= k <= q] or [q]  # :72-77
    short_q = [k for k in cfg["short"] if 1 <= k <= q] or [1]
    lsel = np.isin(bins, [k - 1 for k in long_q]) & np.isfinite(rv)
    ssel = np.isin(bins, [k - 1 for k in short_q]) & np.isfinite(rv)
    long_side = _ref_side(fv[lsel], rv[lsel], "long")
    short_side = _ref_side(fv[ssel], -rv[ssel], "short")  # :127 空側報酬取負
    return {"long_analysis": long_side, "short_analysis": short_side,
            "asymmetry": _ref_asym(long_side["mean_return"], short_side["mean_return"]),
            "recommendation": _ref_recommend(long_side, short_side), "num_quantiles_used": q}


def ref_long_short(features_df: pd.DataFrame, future_returns: pd.Series, top_n: int = 30,
                   config: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """`LongShortAnalyzer(config).batch_analyze(features_df, future_returns, top_n)` 之 oracle（`:168-189`）。"""
    cfg = _ls_cfg(config)
    return {str(n): _ref_ls_feature(features_df[n], future_returns, cfg)
            for n in list(features_df.columns)[: max(1, int(top_n))]}


# ── 比對 ─────────────────────────────────────────────────────────────────────────────────────────────


def _leaves_raw(obj: Any, norm: str, real: str, feature_parent: str) -> Iterator[Tuple[str, str, Any]]:
    """逐葉 (正規化路徑, 正規化路徑＋NUL＋實際路徑, 值)：`feature_parent` 之子鍵（特徵名）→ `*`，list 索引 → `#`。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            seg = "*" if norm == feature_parent else str(k)
            yield from _leaves_raw(v, f"{norm}/{seg}", f"{real}/{k}", feature_parent)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from _leaves_raw(v, f"{norm}/#", f"{real}/{i}", feature_parent)
    else:
        yield norm, norm + "\x00" + real, obj


def _flat(obj: Any, root: str, feature_parent: str) -> Dict[str, Tuple[str, Any]]:
    """{實際路徑: (正規化路徑, 值)}。"""
    return {key.split("\x00", 1)[1]: (norm, val) for norm, key, val in _leaves_raw(obj, root, root, feature_parent)}


def field_paths(output: Any, root: str) -> set:
    """模組輸出之正規化欄位路徑集合（`MODULE_FIELDS` 之鍵形）。"""
    parent = f"{FR_KEY}/value/features" if root == FR_KEY else LS_KEY
    return {norm for norm, _ in _flat(output, root, parent).values()}


def _leaf_cmp(a: Any, b: Any) -> Tuple[bool, Optional[float]]:
    if any(isinstance(v, (str, bool, np.bool_)) or v is None for v in (a, b)):
        return (type(a) is type(b) or {type(a), type(b)} <= {bool, np.bool_}) and a == b, None
    if isinstance(a, (int, np.integer)) and isinstance(b, (int, np.integer)):
        return int(a) == int(b), None
    fa, fb = float(a), float(b)
    if math.isnan(fa) and math.isnan(fb):
        return True, 0.0
    if math.isnan(fa) or math.isnan(fb):
        return False, math.inf
    if math.isinf(fa) or math.isinf(fb):
        return fa == fb, (0.0 if fa == fb else math.inf)
    rel = abs(fa - fb) / abs(fb) if fb != 0 else abs(fa - fb)
    return rel <= REL_TOL, rel


def _compare(product: Any, oracle: Any, root: str) -> Dict[str, Dict[str, Any]]:
    parent = f"{FR_KEY}/value/features" if root == FR_KEY else LS_KEY
    fp, fo = _flat(product, root, parent), _flat(oracle, root, parent)
    groups: Dict[str, Dict[str, Any]] = {}
    for real in sorted(set(fp) | set(fo)):
        norm = (fp.get(real) or fo.get(real))[0]
        meta = MODULE_FIELDS.get(norm)
        if meta is not None and meta["oracle"] == NON_STAT:
            continue
        g = groups.setdefault(norm, {"verdict": "一致", "max_rel_diff": None, "n_finite": 0, "detail": []})
        if meta is None:
            g["detail"].append("未列 MODULE_FIELDS")
        if real not in fp or real not in fo:
            g["verdict"] = "不一致"
            g["detail"].append(f"{real}：{'產品' if real not in fp else 'oracle'}缺")
            continue
        a, b = fp[real][1], fo[real][1]
        ok, rel = _leaf_cmp(a, b)
        if isinstance(a, (float, int, np.floating, np.integer)) and not isinstance(a, (bool, np.bool_)) \
                and math.isfinite(float(a)):
            g["n_finite"] += 1
        if rel is not None:
            g["max_rel_diff"] = rel if g["max_rel_diff"] is None else max(g["max_rel_diff"], rel)
        if not ok:
            g["verdict"] = "不一致"
            if len(g["detail"]) < 5:
                g["detail"].append(f"{real}：產品 {a!r} vs oracle {b!r}")
    for g in groups.values():
        g["detail"] = "；".join(g["detail"])
    return groups


def compare_factor_return(product_output: Mapping[str, Any], features_df: pd.DataFrame, future_returns: pd.Series,
                          top_n: int = 30, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """產品 `compute_batch` 輸出 vs `ref_factor_return`（同一組輸入）；逐統計欄位回 verdict／max_rel_diff／n_finite／detail。"""
    return _compare(product_output, ref_factor_return(features_df, future_returns, top_n, config), FR_KEY)


def compare_long_short(product_output: Mapping[str, Any], features_df: pd.DataFrame, future_returns: pd.Series,
                       top_n: int = 30, config: Optional[Mapping[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """產品 `batch_analyze` 輸出 vs `ref_long_short`（同一組輸入）。"""
    return _compare(product_output, ref_long_short(features_df, future_returns, top_n, config), LS_KEY)


# ── 產品執行 ─────────────────────────────────────────────────────────────────────────────────────────


def _run_fr(features_df: pd.DataFrame, y: pd.Series, top_n: int = 30, config: Optional[dict] = None):
    analyzer = create_factor_return_analyzer(config or {})
    return analyzer.compute_batch(features_df, y, top_n=top_n), analyzer.get_series_map()


def _run_ls(features_df: pd.DataFrame, y: pd.Series, top_n: int = 30, config: Optional[dict] = None):
    return LongShortAnalyzer(config or {}).batch_analyze(features_df, y, top_n=top_n)


def _assert_all_consistent(cmp: Dict[str, Dict[str, Any]]) -> None:
    bad = {k: v for k, v in cmp.items() if v["verdict"] != "一致"}
    assert not bad, f"不一致：{bad}"


def _assert_every_stat_field_finite(cmp: Dict[str, Dict[str, Any]], root: str) -> None:
    """資料充足判準（SPEC 第 109 行）：每一統計欄位至少一個有限值經 oracle 對照。"""
    need = {k for k, v in MODULE_FIELDS.items() if k.startswith(root + "/") and v["oracle"] != NON_STAT}
    if root == LS_KEY:
        need.discard(f"{_LS_FEAT}/asymmetry/type")
        need.discard(f"{_LS_FEAT}/recommendation")
        assert {f"{_LS_FEAT}/asymmetry/type", f"{_LS_FEAT}/recommendation"} <= set(cmp)
    missing = {k for k in need if cmp.get(k, {}).get("n_finite", 0) == 0}
    assert not missing, f"無有限值經對照之統計欄：{sorted(missing)}"


# ── 秒級明列輸入 ─────────────────────────────────────────────────────────────────────────────────────


def _hourly(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-01", periods=n, freq="h", tz="UTC")


def _explicit_inputs(n: int = 240, seed: int = 7, h: int = DEFAULT_H) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """明列邊界輸入（秒級；固定種子之價格路徑）：因果特徵（過去 1 根報酬、對 20 根均線偏離）與 h 根前瞻報酬標籤。"""
    rng = np.random.default_rng(seed)
    price = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=_hourly(n))
    feats = pd.DataFrame({"ret1": price.pct_change(), "dev20": price / price.rolling(20).mean() - 1.0})
    label = (price.shift(-h) / price - 1.0).rename("label")
    return feats, label, price


def test_module_fields_inventory_shape() -> None:
    """清冊每欄必有 oracle 與 producer（檔:行）；統計欄之 oracle id 非空。"""
    for k, v in MODULE_FIELDS.items():
        assert set(v) == {"oracle", "producer"} and v["oracle"] and ":" in v["producer"], k
        assert k.startswith((FR_KEY + "/", LS_KEY + "/")), k


def test_factor_return_matches_oracle_explicit() -> None:
    """一般輸入（特徵與標籤同索引，標籤只尾端缺）：全部統計欄一致且每欄有有限值。"""
    feats, label, _ = _explicit_inputs()
    out, _ = _run_fr(feats, label)
    cmp = compare_factor_return(out, feats, label)
    _assert_all_consistent(cmp)
    _assert_every_stat_field_finite(cmp, FR_KEY)


def test_factor_return_positions_match_oracle_explicit() -> None:
    """position 序列（net_ic 消費之 series artifact，`ic_filter_orchestrator.py:3253`）逐根 == oracle。"""
    feats, label, _ = _explicit_inputs()
    _, series = _run_fr(feats, label)
    cfg = _fr_cfg(None)
    for name in feats.columns:
        _, pos = _ref_fr_feature(feats[name], label, cfg)
        pd.testing.assert_series_equal(series[name].position, pos, check_names=False)


@pytest.mark.parametrize("cfg", [{"num_quantiles": 2}, {"num_quantiles": 10}, {"warmup_periods": 0},
                                 {"warmup_periods": 150}, {"risk_free_rate": 0.05}, {"min_samples": 2}])
def test_factor_return_config_variants_match_oracle(cfg: dict) -> None:
    """設定分支（q、warmup、rf、min_samples）。"""
    feats, label, _ = _explicit_inputs(n=200, seed=11)
    out, _ = _run_fr(feats, label, config=cfg)
    _assert_all_consistent(compare_factor_return(out, feats, label, config=cfg))


def test_factor_return_skip_branches_match_oracle() -> None:
    """空、常數、全 NaN、含 ±inf、樣本數門檻 29／30、標籤零變異、top_n 截斷：產品 features 鍵集合與值 == oracle。"""
    feats, label, _ = _explicit_inputs(n=200, seed=3)
    idx = feats.index
    df = feats.copy()
    df["const"] = 1.0
    df["allnan"] = np.nan
    df["withinf"] = feats["dev20"].where(np.arange(200) % 17 != 0, np.inf)
    df["n29"] = feats["dev20"].where(np.arange(200) >= 200 - DEFAULT_H - 29)
    df["n30"] = feats["dev20"].where(np.arange(200) >= 200 - DEFAULT_H - 30)
    out, _ = _run_fr(df, label)
    assert set(out["value"]["features"]) == {"ret1", "dev20", "withinf", "n30"}
    _assert_all_consistent(compare_factor_return(out, df, label))
    flat_y = pd.Series(0.0, index=idx)
    out0, _ = _run_fr(feats, flat_y)
    assert out0["value"]["features"] == {} == ref_factor_return(feats, flat_y)["value"]["features"]
    # 常數 0.01 標籤：浮點下 nanstd 非恰 0（`:110` 以 == 0.0 判）⇒ 不 skip，其 Sortino 退化見
    # test_fr_sortino_degenerate_downside_is_nan_xfail
    out1, _ = _run_fr(df, label, top_n=1)
    assert list(out1["value"]["features"]) == ["ret1"]
    _assert_all_consistent(compare_factor_return(out1, df, label, top_n=1))
    empty = pd.DataFrame({"x": pd.Series(dtype=float)})
    oute, _ = _run_fr(empty, pd.Series(dtype=float))
    assert oute["value"]["features"] == {} == ref_factor_return(empty, pd.Series(dtype=float))["value"]["features"]


def test_factor_return_interior_label_nan_h1_matches_oracle() -> None:
    """標籤中段缺值但 h=1（缺值不屬未來）：只驗 ls 等以同一 frame 計之欄；position 之歷史差異見 xfail 測試。"""
    feats, label, _ = _explicit_inputs(n=200, seed=5, h=1)
    out, _ = _run_fr(feats, label)
    _assert_all_consistent(compare_factor_return(out, feats, label))


@pytest.mark.parametrize("returns", [[], [0.01], [0.01, 0.02, 0.03], [-0.01, 0.02], [0.05] * 3 + [-0.02, -0.01],
                                     [0.5] * 40, [np.inf, 0.01, -0.02, np.nan, 0.03, -0.01]])
def test_risk_metrics_boundaries_match_oracle(returns: list) -> None:
    """`compute_risk_metrics` 邊界：空、單筆（std NaN）、無下行（sortino NaN、mdd 0 ⇒ calmar NaN）、恰一筆下行、
    年化 > 1e6 ⇒ NaN、含 ±inf／NaN（先剔除）。"""
    got = create_factor_return_analyzer({}).compute_risk_metrics(pd.Series(returns, dtype=float), 0.0, 8760)
    exp = ref_risk_metrics(returns, 0.0, 8760)
    for k, v in exp.items():
        ok, rel = _leaf_cmp(got[k], v)
        assert ok, f"{k}：{got[k]} vs {v}（rel {rel}）"


def test_ls_cumulative_sampling_boundary_matches_oracle() -> None:
    """抽樣上限邊界：frame 列數 ≤ 100（原樣）與 > 100（linspace 100 點）。"""
    for n in (60, 100 + DEFAULT_H, 101 + DEFAULT_H, 300):
        feats, label, _ = _explicit_inputs(n=n, seed=n)
        out, _ = _run_fr(feats, label)
        _assert_all_consistent(compare_factor_return(out, feats, label))


def test_periods_per_year_branches() -> None:
    """年化期數（產品經公開輸出驗）：RangeIndex ⇒ 365、1h ⇒ 8760、1d ⇒ 365、15m ⇒ 35040。"""
    assert ref_periods_per_year(pd.RangeIndex(10)) == 365
    for freq, exp in (("h", 8760), ("D", 365), ("15min", 35040)):
        assert ref_periods_per_year(pd.date_range("2024-01-01", periods=50, freq=freq)) == exp
    feats, label, _ = _explicit_inputs(n=200, seed=9)
    rfeats, rlabel = feats.reset_index(drop=True), label.reset_index(drop=True)
    out, _ = _run_fr(rfeats, rlabel)
    _assert_all_consistent(compare_factor_return(out, rfeats, rlabel))


# long_short 秒級


def test_long_short_matches_oracle_explicit() -> None:
    """一般輸入：全部統計欄一致且每欄有有限值；另以標籤只覆蓋末段（同呼叫端測試段標籤）驗分箱用特徵全歷史。"""
    feats, label, _ = _explicit_inputs(n=400, seed=21)
    out = _run_ls(feats, label)
    cmp = compare_long_short(out, feats, label)
    _assert_all_consistent(cmp)
    _assert_every_stat_field_finite(cmp, LS_KEY)
    test_label = label.iloc[-120:]
    out2 = _run_ls(feats, test_label)
    _assert_all_consistent(compare_long_short(out2, feats, test_label))


def test_long_short_pit_bins_match_oracle() -> None:
    """`compute_pit_bins` 逐根 == oracle（含 NaN 暖機、常數段、減箱致 require_full_q NaN）。"""
    feats, _, _ = _explicit_inputs(n=300, seed=4)
    tied = pd.Series(np.where(np.arange(300) % 4 == 0, np.arange(300) / 300.0, 0.0), index=feats.index)
    analyzer = LongShortAnalyzer({})
    for s in (feats["ret1"], feats["dev20"], tied):
        pd.testing.assert_series_equal(analyzer.compute_pit_bins(s), ref_ls_bins(s, 5), check_names=False)


def test_long_short_skip_and_edge_branches_match_oracle() -> None:
    """樣本 < 30 ⇒ INSUFFICIENT_DATA；有限特徵 < 100 ⇒ NUMERICAL_ERROR；常數特徵（n ≥ 100）⇒ 空側、不建議；
    標籤含 ±inf／NaN；空輸入。"""
    feats, label, _ = _explicit_inputs(n=300, seed=8)
    df = feats.copy()
    df["n20"] = feats["dev20"].where(np.arange(300) >= 270)
    df["n60"] = feats["dev20"].where(np.arange(300) >= 230)
    df["const"] = 3.0
    lab = label.copy()
    lab.iloc[::23] = np.inf
    lab.iloc[5::31] = np.nan
    out = _run_ls(df, lab)
    assert out["n20"]["error_type"] == "INSUFFICIENT_DATA" and out["n60"]["error_type"] == "NUMERICAL_ERROR"
    assert out["const"]["recommendation"] == "不建議"
    _assert_all_consistent(compare_long_short(out, df, lab))
    empty = pd.DataFrame({"x": pd.Series(dtype=float)})
    assert _run_ls(empty, pd.Series(dtype=float)) == ref_long_short(empty, pd.Series(dtype=float))


@pytest.mark.parametrize("cfg", [{"num_quantiles": 3, "long_quantiles": [3], "short_quantiles": [1]},
                                 {"num_quantiles": 10, "long_quantiles": [8, 9, 10], "short_quantiles": [1, 2, 3]},
                                 {"min_samples": 250}])
def test_long_short_config_variants_match_oracle(cfg: dict) -> None:
    feats, label, _ = _explicit_inputs(n=300, seed=13)
    _assert_all_consistent(compare_long_short(_run_ls(feats, label, config=cfg), feats, label, config=cfg))


@pytest.mark.parametrize("lr,sr", [(0.0, 0.0), (np.nan, np.nan), (0.03, 0.01), (0.01, 0.03), (0.02, 0.018),
                                   (0.02, 0.0), (-0.02, 0.01)])
def test_long_short_asymmetry_branches_match_oracle(lr: float, sr: float) -> None:
    """不對稱分類之全部分支（總和 0、long／short dominant、symmetric、空側 0 ⇒ ratio inf）。"""
    got = LongShortAnalyzer._classify_asymmetry(lr, sr)
    exp = _ref_asym(lr, sr)
    for k in exp:
        assert _leaf_cmp(got[k], exp[k])[0], f"{k}：{got[k]} vs {exp[k]}"


@pytest.mark.parametrize("li,si,exp", [(0.1, 0.1, "雙向交易"), (0.1, -0.1, "只做多"), (-0.1, 0.1, "只做空"),
                                       (-0.1, -0.1, "不建議"), (np.nan, 0.1, "只做空"), (np.nan, np.nan, "不建議")])
def test_long_short_recommendation_branches(li: float, si: float, exp: str) -> None:
    side = {"samples": 5}
    assert _ref_recommend({**side, "ic": li}, {**side, "ic": si}) == exp
    if not (math.isnan(li) and math.isnan(si)):
        assert LongShortAnalyzer._recommendation(li, si) == exp


# ── 秒級：已查不一致（xfail strict） ───────────────────────────────────────────────────────────────────


def _tied_feature(n: int, zero_every: int) -> pd.Series:
    """大量相同值（0）夾少量相異正值之特徵——`pd.qcut(duplicates="drop")` 減箱之最小重現。"""
    i = np.arange(n)
    return pd.Series(np.where(i % zero_every == 0, (i + 1) / n, 0.0), index=_hourly(n), name="tied")


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：factor_return 減箱時以 q_eff−1 判頂分位、頂箱永不 +1"
                   f"（factor_return_analyzer.py:335-351）；收據 {RECEIPT}")
def test_fr_top_quantile_uses_actual_bin_count_xfail() -> None:
    """50% 為 0：q=5 之 20%／40% 分位邊界重複被刪，實際 3 箱（標籤 0..2）；oracle 頂箱標籤 2 ⇒ +1。產品只比 4 ⇒ 0 次 +1。"""
    n = 120
    feat = _tied_feature(n, 2)
    label = pd.Series(np.random.default_rng(1).normal(0, 0.01, n), index=feat.index)
    _, series = _run_fr(feat.to_frame(), label)
    _, pos = _ref_fr_feature(feat, label, _fr_cfg(None))
    assert int((pos == 1).sum()) > 0
    pd.testing.assert_series_equal(series["tied"].position, pos, check_names=False)


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：factor_return 只得 1 箱時當根標籤 0 被判為底分位、"
                   f"每根皆 −1（含特徵最大值之根）（factor_return_analyzer.py:335-351）；收據 {RECEIPT}")
def test_fr_single_bin_yields_no_position_xfail() -> None:
    """95% 為 0、其餘 1：q_eff＝2 而 qcut 邊界 [0, 0, 1] 刪重後只 1 箱；oracle 無頂底 ⇒ 無 position ⇒ skip。
    產品每根 −1（連特徵＝1 之根也做空）而輸出 ok。"""
    n = 200
    i = np.arange(n)
    feat = pd.Series(np.where(i % 20 == 0, 1.0, 0.0), index=_hourly(n), name="tied")
    label = pd.Series(np.random.default_rng(2).normal(0, 0.01, n), index=feat.index)
    out, _ = _run_fr(feat.to_frame(), label)
    assert out["value"]["features"] == ref_factor_return(feat.to_frame(), label)["value"]["features"]


@pytest.mark.xfail(strict=True, reason=f"偷看未來：ICPERF Task 0.3 不一致：factor_return 分箱歷史取特徵∩標籤 dropna，"
                   f"t 之後之價格缺值（使 t−h+1..t 間某根標籤 NaN）改寫第 t 根 position"
                   f"（factor_return_analyzer.py:78-81,120-124）；收據 {RECEIPT}")
def test_fr_position_prefix_invariant_to_future_price_gap_xfail() -> None:
    """情境 A 與 B 之價格於 0..g−1 完全相同，B 只令 p_g＝NaN（g 之後才發生）；h＝5 ⇒ B 之 y_{g−5} 為 NaN。第 t 根
    （t < g）可得資訊兩情境相同，正確 PIT position 必相同（oracle 自證見下一測試）；產品之 position 於某 t < g 不同。"""
    feats, label, price = _explicit_inputs(n=160, seed=17)
    diffs = []
    _, sa = _run_fr(feats, label)
    for g in range(28, 150):
        pb = price.copy()
        pb.iloc[g] = np.nan
        fb = pd.DataFrame({"ret1": pb.pct_change(fill_method=None), "dev20": pb / pb.rolling(20).mean() - 1.0})
        lb = pb.shift(-DEFAULT_H) / pb - 1.0
        _, sb = _run_fr(fb, lb)
        for name in ("ret1", "dev20"):
            if name not in sa or name not in sb:
                continue
            pa, pbp = sa[name].position, sb[name].position
            common = pa.index.intersection(pbp.index)
            common = common[common < price.index[g]]
            if not (pa.loc[common] == pbp.loc[common]).all():
                diffs.append((g, name))
    assert not diffs, f"t < g 之 position 隨 g 處未來缺值而變：{diffs[:10]}（共 {len(diffs)}）"


def test_fr_oracle_position_prefix_invariant_to_future_price_gap() -> None:
    """oracle 自證 PIT：同上情境，oracle position 於 t < g 恆不變。"""
    feats, label, price = _explicit_inputs(n=160, seed=17)
    cfg = _fr_cfg(None)
    for g in range(28, 150, 7):
        pb = price.copy()
        pb.iloc[g] = np.nan
        fb = pd.DataFrame({"ret1": pb.pct_change(fill_method=None), "dev20": pb / pb.rolling(20).mean() - 1.0})
        lb = pb.shift(-DEFAULT_H) / pb - 1.0
        for name in ("ret1", "dev20"):
            _, pa = _ref_fr_feature(feats[name], label, cfg)
            _, pbp = _ref_fr_feature(fb[name], lb, cfg)
            common = pa.index.intersection(pbp.index)
            common = common[common < price.index[g]]
            assert (pa.loc[common] == pbp.loc[common]).all(), (g, name)


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：factor_return 未收標籤 horizon，h 根重疊前瞻報酬以每根一期"
                   f"年化（年化波動、Sharpe 高估約 √h 倍）（factor_return_analyzer.py:143-147,212-224）；收據 {RECEIPT}")
def test_fr_annualization_accounts_for_label_horizon_xfail() -> None:
    """h＝5 之前瞻報酬每根取樣而相鄰重疊：一年只有 P／h 個獨立 h 根期，業界（Lo 2002；alphalens 以 period 換算）年化
    波動＝std·√(P／h)、Sharpe＝mean／std·√(P／h)。嚴格遞增特徵 ⇒ 暖機後每根皆頂分位 +1。"""
    feats, label, _ = _explicit_inputs(n=300, seed=19)
    feat = pd.Series(np.arange(300, dtype=float), index=feats.index, name="trend")
    out, series = _run_fr(feat.to_frame(), label)
    ls = series["trend"].ls_return.to_numpy()
    P = 8760
    std = float(np.std(ls, ddof=1))
    rm = out["value"]["features"]["trend"]["risk_metrics"]
    assert _leaf_cmp(rm["annualized_volatility"], std * math.sqrt(P / DEFAULT_H))[0]
    assert _leaf_cmp(rm["sharpe_ratio"], float(np.mean(ls)) / std * math.sqrt(P / DEFAULT_H))[0]


_INDUSTRY_R = [0.012, -0.004, 0.007, -0.011, 0.003, 0.009, -0.002, -0.006, 0.010, 0.001, -0.008, 0.005]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：Sortino 下行偏差取負報酬子樣本之標準差（ddof=1、對其自身"
                   f"均值），非業界 √mean(min(r,0)²)（factor_return_analyzer.py:228-236）；收據 {RECEIPT}")
def test_fr_sortino_uses_industry_downside_deviation_xfail() -> None:
    """Sortino & Price（1994）／empyrical.sortino_ratio：下行偏差＝√(Σ min(r−0,0)²／N)，N＝全部觀測。"""
    r = np.asarray(_INDUSTRY_R)
    dd = math.sqrt(float(np.mean(np.minimum(r, 0.0) ** 2)))
    got = create_factor_return_analyzer({}).compute_risk_metrics(pd.Series(r), 0.0, 8760)
    assert _leaf_cmp(got["sortino_ratio"], float(np.mean(r)) / dd * math.sqrt(8760))[0]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：下行報酬全相同時 pandas Series.std 得 ~3.5e-18 而非 0，"
                   f"Sortino 輸出 ~1e16 之垃圾值而非 NaN（factor_return_analyzer.py:229-236）；收據 {RECEIPT}")
def test_fr_sortino_degenerate_downside_is_nan_xfail() -> None:
    """下行報酬 50 筆皆 −0.01（離散跳動、常數標籤時可達）：數學上下行標準差＝0 ⇒ 產品自身之守衛（`:233` dstd > 0）
    應給 NaN；numpy.std 得恰 0、pandas 兩段式得 3.5e-18 ⇒ 守衛失效。"""
    r = pd.Series([0.02] * 30 + [-0.01] * 50, dtype=float)
    got = create_factor_return_analyzer({}).compute_risk_metrics(r, 0.0, 8760)
    assert math.isnan(got["sortino_ratio"]), got["sortino_ratio"]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：年化報酬以 (1+算術均值)^P−1，非業界幾何 CAGR"
                   f"（prod(1+r))^(P/N)−1；Calmar 隨之偏（factor_return_analyzer.py:205-210,248-254）；收據 {RECEIPT}")
def test_fr_annualized_return_is_cagr_xfail() -> None:
    """empyrical.annual_return／calmar_ratio：CAGR＝(Π(1+r))^(P／N)−1，Calmar＝CAGR／|MDD|。"""
    r = np.asarray(_INDUSTRY_R)
    P = 365
    cagr = float(np.prod(1.0 + r) ** (P / r.size) - 1.0)
    eq = np.cumprod(1.0 + r)
    mdd = float(np.min(eq / np.maximum.accumulate(eq) - 1.0))
    got = create_factor_return_analyzer({}).compute_risk_metrics(pd.Series(r), 0.0, P)
    assert _leaf_cmp(got["annualized_return"], cagr)[0]
    assert _leaf_cmp(got["calmar_ratio"], cagr / abs(mdd))[0]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：年化期數寫死 24·365／間隔中位數，非 24/7 市場（交易日"
                   f"日線）得 365 而非實際每年根數（factor_return_analyzer.py:385-394）；收據 {RECEIPT}")
def test_fr_periods_per_year_follows_observed_bar_density_xfail() -> None:
    """工作日日線（週末無資料）：每年實得根數＝(N−1)·365 日／跨度；產品以間隔中位數 1 日 ⇒ 365（√(365／261) 高估年化
    波動與 Sharpe）。不得寫死 24h（使用者「不得侷限加密貨幣」）。"""
    n = 520
    idx = pd.bdate_range("2022-01-03", periods=n, tz="UTC")
    rng = np.random.default_rng(23)
    price = pd.Series(100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n))), index=idx)
    feat = pd.Series(np.arange(n, dtype=float), index=idx, name="trend")
    label = price.shift(-1) / price - 1.0
    out, series = _run_fr(feat.to_frame(), label)
    fidx = series["trend"].ls_return.index
    P = int(round((len(fidx) - 1) * 365.0 * 86400.0 / ((fidx[-1] - fidx[0]).total_seconds())))
    ls = series["trend"].ls_return.to_numpy()
    rm = out["value"]["features"]["trend"]["risk_metrics"]
    assert _leaf_cmp(rm["annualized_volatility"], float(np.std(ls, ddof=1)) * math.sqrt(P))[0]


@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：long_short 分箱樣本門檻經 effective_count 計 ~isnan，±inf "
                   f"亦計入，有限值不足 100 即分箱（pit_stats.py:49-52,374-377；long_short_analyzer.py:56-61）；收據 {RECEIPT}")
def test_ls_bin_min_samples_counts_finite_only_xfail() -> None:
    """首根 +inf、其後 149 根相異有限值：第 99 根（有限歷史 99 筆）不得有標籤；產品已標。"""
    n = 150
    vals = np.concatenate([[np.inf], np.random.default_rng(29).normal(0, 1, n - 1)])
    feat = pd.Series(vals, index=_hourly(n))
    got = LongShortAnalyzer({}).compute_pit_bins(feat)
    pd.testing.assert_series_equal(got, ref_ls_bins(feat, 5), check_names=False)


# ── 真實資料（requires_kline） ───────────────────────────────────────────────────────────────────────


def _real_close(rows: int = 2000, symbol: str = "BTCUSDT") -> pd.Series:
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/1h/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    return pd.Series(data["close"].astype("float64"), index=idx, name="close")


def _real_inputs(rows: int = 2000) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """真實 BTCUSDT 1h（L 格 2,000 列，SPEC 第 108 行 FACT-RECEIPT）：因果特徵（只用 0..t）與 h＝5 前瞻簡單報酬
    close[t+5]／close[t]−1（同產品預設 horizon）。"""
    close = _real_close(rows)
    feats = pd.DataFrame({"ret1": close.pct_change(), "dev20": close / close.rolling(20).mean() - 1.0,
                          "mom24": close / close.shift(24) - 1.0})
    label = (close.shift(-DEFAULT_H) / close - 1.0).rename("label")
    return feats, label, close


@pytest.mark.requires_kline
def test_factor_return_fields_closed() -> None:
    """真實 kline 小輸入（600 列；含有限值僅 20 筆之欄 ⇒ long_short skipped、factor_return 不入 features）：兩模組實際
    輸出之正規化欄位集合 == `MODULE_FIELDS` 鍵集合。"""
    feats, label, _ = _real_inputs(600)
    feats["sparse"] = feats["dev20"].where(np.arange(len(feats)) >= len(feats) - 20)
    fr, _ = _run_fr(feats, label)
    ls = _run_ls(feats, label)
    actual = field_paths(fr, FR_KEY) | field_paths(ls, LS_KEY)
    assert actual == set(MODULE_FIELDS), (
        f"清冊多：{sorted(set(MODULE_FIELDS) - actual)}；實際多：{sorted(actual - set(MODULE_FIELDS))}")


@pytest.mark.requires_kline
def test_factor_return_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h 2,000 列、特徵與標籤同索引：全部統計欄一致，且每一統計欄至少一特徵得有限值。"""
    feats, label, _ = _real_inputs()
    out, series = _run_fr(feats, label)
    cmp = compare_factor_return(out, feats, label)
    _assert_all_consistent(cmp)
    _assert_every_stat_field_finite(cmp, FR_KEY)
    cfg = _fr_cfg(None)
    for name in feats.columns:
        _, pos = _ref_fr_feature(feats[name], label, cfg)
        pd.testing.assert_series_equal(series[name].position, pos, check_names=False)


@pytest.mark.requires_kline
def test_long_short_matches_oracle_on_real_kline() -> None:
    """真實 BTCUSDT 1h：(a) 特徵與標籤同索引 (b) 標籤只覆蓋末 400 列（同呼叫端：`_ic_cache` 之 features_df 全長、
    label_series 為測試段，`ic_filter_orchestrator.py:4829-4831`）；全部統計欄一致且每欄有有限值。"""
    feats, label, _ = _real_inputs()
    for lab in (label, label.iloc[-400:]):
        out = _run_ls(feats, lab)
        cmp = compare_long_short(out, feats, lab)
        _assert_all_consistent(cmp)
        _assert_every_stat_field_finite(cmp, LS_KEY)


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：呼叫端標籤只覆蓋測試段時，factor_return 之分箱歷史被截為"
                   f"測試段（另付 20 根暖機），非特徵自身全歷史（違 RB-3，long_short_analyzer.py:47-50）"
                   f"（factor_return_analyzer.py:78-81）；收據 {RECEIPT}")
def test_fr_history_not_truncated_by_label_segment_on_real_kline_xfail() -> None:
    """真實 BTCUSDT 1h：features 全長 2,000 列、標籤只末 400 列（同 `_run_factor_return` 之實際輸入形狀）。"""
    feats, label, _ = _real_inputs()
    lab = label.iloc[-400:]
    out, _ = _run_fr(feats, lab)
    _assert_all_consistent(compare_factor_return(out, feats, lab))


@pytest.mark.requires_kline
@pytest.mark.xfail(strict=True, reason=f"ICPERF Task 0.3 不一致：離散特徵（報酬正負號）於真實資料減為 1 箱，factor_return "
                   f"每根皆 −1（factor_return_analyzer.py:335-351）；收據 {RECEIPT}")
def test_fr_discrete_feature_on_real_kline_xfail() -> None:
    """真實 BTCUSDT 1h：sign(過去 1 根報酬)（因果，取值 {−1, 0, 1}）。"""
    feats, label, _ = _real_inputs()
    df = pd.DataFrame({"sign1": np.sign(feats["ret1"])})
    out, _ = _run_fr(df, label)
    _assert_all_consistent(compare_factor_return(out, df, label))
