"""ICPERF Task 0.4 ㊱：跨標的報告佔位欄位（summary 五欄、相關矩陣、多元化指標）之獨立 oracle 測試。

SPEC `docs/ICPERF_SPEC.md` v5.40 Task 0.4 ㊱：「依縱向路徑同一定義由跨標的資料計算（各欄定義於施工時對照縱向產生端寫明），
無法定義者附原因」；驗證「秒級＋真實資料（`kline_cache.h5` 多標的 1h）：各欄以 scipy／numpy 獨立重算」。

本檔之 oracle 皆為測試自寫參考實作（pandas `pd.qcut`、`scipy.stats.spearmanr`／`pearsonr`、`scipy.optimize.curve_fit`、
numpy），不呼叫產品 helper。各欄定義（縱向產生端 → 跨標的；業界出處）：

- 分位：每時點對該時點特徵有限之標的 `pd.qcut(x, q, labels=False)`；邊界重複（含有限數 < 2）⇒ 該時點不入
  （alphalens `utils.quantize_factor` 之逐日 qcut、`no_raise`）。q：單調性與多空價差同縱向
  `MonotonicityTester._select_num_quantiles`（請求 5；q > 3 且「特徵有限且標籤有限」之總觀測數／q < 30 ⇒ 3）；換手率同縱向
  `TurnoverAnalyzer.compute_all` 之 5。
- `monotonicity_score`（monotonicity_tester.py `compute_monotonicity_score`）：各分位之標籤均值（標籤有限之觀測合併平均，
  alphalens `performance.mean_return_by_quantile(by_date=False, demeaned=False)`），相鄰兩分位皆有值之差 > 0 之比例；
  無相鄰有值對 ⇒ 0.0。
- `long_short_spread`（`compute_long_short_spread`）：最高分位均值 − 最低分位均值；任一無值 ⇒ NaN。
- `turnover_rate`（turnover_analyzer.py `compute_quantile_turnover`「頂部分位成分每期變化比例」）：alphalens
  `performance.quantile_turnover`——頂分位標的集合 S_t（依有效分位之時點序），|S_t − S_prev|／|S_t| 之平均；有效時點 < 2 ⇒
  NaN；設定 `turnover.enabled` 關 ⇒ 欄缺席（同縱向）。
- `coverage`（coverage_analyzer.py `compute_time_coverage`）：該特徵非 NaN 之列數／分析段總列數（面板列＝時點×標的）。
- `ic_half_life`（ic_engine.py `compute_ic_decay`＋`_fit_exponential_decay`）：各 horizon h 之 IC＝每時點截面 Spearman
  （特徵與 h 根前瞻報酬共同非 NaN 之標的 ≥ 2；常數 ⇒ 不入）之平均；前瞻報酬依縱向 `return_type`（simple：c[t+h]／c[t]−1）
  於分析段內逐標的計；IC(h)＝A·exp(−λh)＋C，半衰期＝ln2／λ（λ ≤ 0 ⇒ NaN）。半衰期為擬合參數之衍生量，依 SPEC
  v5.18／v5.22（衰減擬合驗最佳性與衍生一致、不比求解器參數）：逐 horizon IC 對 oracle 1e-12、產品殘差 ≤ 固定四起點
  `curve_fit` 之 oracle 最小 ×(1＋1e-9)（雙向）、半衰期＝ln2／產品 λ；逐特徵擬合輸出於 `ic_decay` 節（同縱向鍵）。
  未傳收盤 ⇒ None 並記原因 `close_not_provided`；`report.include_decay_analysis` 關 ⇒ `decay_analysis_off`。
- `correlation_matrix`（redundancy_filter.py `compute_correlation_matrix` 之 Pearson）：每時點截面 Pearson（兩特徵共同有限之
  標的 ≥ 2 且兩者於共同列皆非常數）之時間平均（Fama–MacBeth 式平均截面相關）；無有效時點 ⇒ NaN；對角＝1（該特徵任一時點
  有效）否則 NaN；輸出 NaN 填 0（同縱向 `_build_correlation_payload`）。特徵集合＝跨標的輸出之全部特徵（本路徑不設門檻）。
- `diversification_metrics`（`compute_diversification_metrics`）：同一公式於上列相關矩陣；未傳特徵 metadata ⇒ 三覆蓋率 None
  並記原因 `feature_metadata_not_provided`。
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import numpy as np
import pandas as pd
import pytest
from scipy import optimize, stats

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
LABEL = "return_1"
REL_TOL = 1e-12
FIELDS = ("monotonicity_score", "long_short_spread", "coverage", "turnover_rate", "ic_half_life")
DIV_KEYS = ("avg_abs_correlation", "max_correlation", "effective_independent_features", "category_coverage",
            "data_source_coverage", "layer_coverage")


def _rel(a: Any, b: Any) -> float:
    """相對誤差（兩者皆 NaN ⇒ 0；一方 NaN／None ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if a is None or b is None:
        return 0.0 if a is None and b is None else math.inf
    a, b = float(a), float(b)
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


def _nan_if_none(v: Any) -> Any:
    return math.nan if v is None else v


# ── 參考實作 ──────────────────────────────────────────────────────────────────────────────────────────


def _date_bins(df: pd.DataFrame, feat: str, q: int) -> Dict[Any, pd.Series]:
    """{時點: 以標的為索引之分位標籤}；只含 `pd.qcut` 成立之時點（alphalens quantize_factor no_raise）。"""
    out: Dict[Any, pd.Series] = {}
    for when, g in df.groupby(level=0, sort=True):
        x = g[feat].to_numpy(dtype=float)
        ok = np.isfinite(x)
        if not ok.any():
            continue
        try:
            lab = pd.qcut(x[ok], q, labels=False)
        except ValueError:
            continue
        out[when] = pd.Series(np.asarray(lab, dtype=int), index=np.asarray(g.index.get_level_values(1))[ok])
    return out


def _ref_quantile_fields(df: pd.DataFrame, feat: str) -> Dict[str, float]:
    x_all = df[feat].to_numpy(dtype=float)
    y_all = df[LABEL].to_numpy(dtype=float)
    n_pool = int(np.sum(np.isfinite(x_all) & np.isfinite(y_all)))
    q = 3 if (5 > 3 and n_pool / 5 < 30) else 5
    bins = _date_bins(df, feat, q)
    per_q: Dict[int, List[float]] = {k: [] for k in range(q)}
    for when, lab in bins.items():
        g = df.xs(when, level=0)
        y = g[LABEL].reindex(lab.index).to_numpy(dtype=float)
        for k, v in zip(lab.to_numpy(), y):
            if np.isfinite(v):
                per_q[int(k)].append(float(v))
    means = [float(np.mean(per_q[k])) if per_q[k] else math.nan for k in range(q)]
    pairs = [(a, b) for a, b in zip(means[:-1], means[1:]) if math.isfinite(a) and math.isfinite(b)]
    mono = float(np.mean([b - a > 0 for a, b in pairs])) if pairs else 0.0
    spread = means[-1] - means[0] if math.isfinite(means[-1]) and math.isfinite(means[0]) else math.nan
    bins5 = _date_bins(df, feat, 5)
    sets = [set(lab.index[lab.to_numpy() == 4]) for _, lab in sorted(bins5.items(), key=lambda kv: kv[0])]
    rates = [len(cur - prev) / len(cur) for prev, cur in zip(sets[:-1], sets[1:])]
    turnover = float(np.mean(rates)) if rates else math.nan
    coverage = float(df[feat].notna().sum() / len(df))
    return {"monotonicity_score": mono, "long_short_spread": spread, "turnover_rate": turnover, "coverage": coverage,
            "_q": q, "_means": means}


def _ref_aligned_monotonicity(means: List[float], direction: int) -> float:
    """方向對齊單調性（SPEC Task 0.4 ⑧）：+1 ⇒ 相鄰差 > 0 之比例、−1 ⇒ < 0 之比例；無可比之差 ⇒ 0.0；方向 0 ⇒ NaN。"""
    if direction == 0:
        return math.nan
    diffs = [b - a for a, b in zip(means[:-1], means[1:]) if math.isfinite(a) and math.isfinite(b)]
    if not diffs:
        return 0.0
    return float(np.mean([d > 0 if direction > 0 else d < 0 for d in diffs]))


def _sp(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape[0] < 2 or np.ptp(a) == 0.0 or np.ptp(b) == 0.0:
        return math.nan
    return float(stats.spearmanr(a, b)[0])


#: 衰減擬合最佳性之容許（同 test_icperf_correctness.py `SSR_SLACK`：產品殘差 ≤ oracle 最小 ×(1＋1e-9)）
SSR_SLACK = 1e-9


def _model(h: np.ndarray, a: float, lam: float, c: float) -> np.ndarray:
    return a * np.exp(-lam * h) + c


def _ref_min_ssr(horizons: List[int], ic: List[float]) -> float:
    """IC(h)＝A·exp(−λh)＋C 之 oracle 最小殘差平方和（SPEC Task 0.3 ②、Task 0.4 ③：先套有限值遮罩；固定起點集合 {預設、
    [y0,1,0]、[y0,0.1,0]、[y0−y_last,0.5,y_last]}，curve_fit maxfev 20000、無 bounds；有限點 < 3 或 std < 1e-8 ⇒ NaN
    〔不擬合〕；全部失敗 ⇒ inf）。半衰期為擬合參數之衍生量，依 SPEC v5.18／v5.22 驗最佳性與衍生一致、不比求解器參數。"""
    x = np.asarray(horizons, dtype=float)
    y = np.asarray(ic, dtype=float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    if x.size < 3 or np.nanstd(y) < 1e-8:
        return math.nan
    best = math.inf
    for p0 in (None, [y[0], 1.0, 0.0], [y[0], 0.1, 0.0], [y[0] - y[-1], 0.5, y[-1]]):
        try:
            cand, _ = optimize.curve_fit(_model, x, y, p0=p0, maxfev=20000)
        except (RuntimeError, ValueError, optimize.OptimizeWarning):
            continue
        ss = float(np.sum((y - _model(x, *cand)) ** 2))
        if math.isfinite(ss):
            best = min(best, ss)
    return best


def _assert_decay_fit(fit: Mapping[str, Any], ic_values: List[float], oracle_min: float, where: str) -> None:
    """產品擬合之最佳性（雙向）與衍生一致：half_life＝ln2／λ（λ ≤ 0 ⇒ NaN）、decay_type 依 r2、fit_warning 與原因。"""
    if math.isnan(oracle_min):
        assert fit["decay_type"] == "fit_failed", f"{where}：oracle 不擬合（點數或變異不足）而產品 {fit['decay_type']}"
        assert math.isnan(_nan_if_none(fit["half_life"])), where
        return
    assert fit["decay_type"] != "fit_failed" or not math.isfinite(oracle_min), f"{where}：產品 fit_failed 而 oracle 成功"
    assert math.isfinite(oracle_min) or fit["decay_type"] == "fit_failed", f"{where}：產品成功而 oracle 全部起點失敗"
    if fit["decay_type"] == "fit_failed":
        return
    y = np.asarray(ic_values, dtype=float)
    y = y[np.isfinite(y)]
    product_ssr = (1.0 - float(fit["fit_r2"])) * float(np.sum((y - np.mean(y)) ** 2))
    assert product_ssr <= oracle_min * (1 + SSR_SLACK) + 1e-300, f"{where}：產品殘差 {product_ssr} > oracle {oracle_min}"
    lam = float(fit["decay_rate"])
    if lam > 0:
        assert _rel(fit["half_life"], math.log(2) / lam) <= REL_TOL, where
    else:
        assert math.isnan(_nan_if_none(fit["half_life"])), where
    assert fit["decay_type"] == ("exponential" if fit["fit_r2"] >= 0.5 else "non_exponential"), where
    assert fit["fit_warning"] == (fit["decay_type"] != "exponential"), where
    assert fit["fit_warning_reason"] == ("low_r2" if fit["fit_warning"] else None), where


def _ref_decay(df: pd.DataFrame, feat: str, close: pd.Series, horizons: List[int]) -> Dict[str, Any]:
    c = close.reindex(df.index)
    fwd: Dict[int, pd.Series] = {}
    for h in horizons:
        parts = []
        for _, cs in c.groupby(level=1, sort=True):
            cs = cs.sort_index(level=0)
            parts.append(cs.shift(-h) / cs - 1.0)
        fwd[h] = pd.concat(parts).reindex(df.index)
    ics, scales = [], []
    for h in horizons:
        vals = []
        for when, g in df.groupby(level=0, sort=True):
            x = g[feat].to_numpy(dtype=float)
            y = fwd[h].loc[g.index].to_numpy(dtype=float)
            m = ~np.isnan(x) & ~np.isnan(y)
            if m.sum() >= 2:
                v = _sp(x[m], y[m])
                if math.isfinite(v):
                    vals.append(v)
        ics.append(float(np.mean(vals)) if vals else math.nan)
        scales.append(float(np.mean(np.abs(vals))) if vals else math.nan)
    return {"ic_values": ics, "scales": scales, "min_ssr": _ref_min_ssr(horizons, ics)}


def _mean_close(got: Any, want: float, scale: float) -> bool:
    """時間平均之比對：相對誤差 ≤ 1e-12；或真值因正負相消近 0 時，絕對誤差 ≤ 1e-12 × 被平均項之平均絕對值（求和之捨入
    誤差界＝條件數 Σ|r_t|／|Σr_t| 之標準分析；明列輸入之對稱結構可使平均於精確算術下恰為 0，兩方皆只剩 1e-17 級殘差）。"""
    g = _nan_if_none(got)
    if _rel(g, want) <= REL_TOL:
        return True
    return math.isfinite(g) and math.isfinite(want) and abs(g - want) <= REL_TOL * scale


def _ref_corr(df: pd.DataFrame, feats: List[str]) -> np.ndarray:
    n = len(feats)
    acc = [[[] for _ in range(n)] for _ in range(n)]
    for _, g in df.groupby(level=0, sort=True):
        vals = g[feats].to_numpy(dtype=float)
        for i in range(n):
            for j in range(n):
                m = np.isfinite(vals[:, i]) & np.isfinite(vals[:, j])
                a, b = vals[m, i], vals[m, j]
                if a.size >= 2 and np.ptp(a) > 0 and np.ptp(b) > 0:
                    acc[i][j].append(1.0 if i == j else float(stats.pearsonr(a, b)[0]))
    mean = np.array([[float(np.mean(acc[i][j])) if acc[i][j] else math.nan for j in range(n)] for i in range(n)])
    scale = np.array([[float(np.mean(np.abs(acc[i][j]))) if acc[i][j] else math.nan for j in range(n)]
                      for i in range(n)])
    return mean, scale


def _ref_diversification(corr: np.ndarray, feats: List[str], meta: Optional[Mapping[str, Mapping[str, Any]]]
                         ) -> Dict[str, Any]:
    n = len(feats)
    ab = np.nan_to_num(np.abs(corr), nan=0.0)
    upper = ab[np.triu_indices(n, k=1)]
    avg = float(np.mean(upper)) if upper.size else 0.0
    mx = float(np.max(upper)) if upper.size else 0.0
    out: Dict[str, Any] = {"avg_abs_correlation": avg, "max_correlation": mx,
                           "effective_independent_features": 1.0 if n <= 1 else float(n / (1.0 + avg * (n - 1)))}
    for key, out_key in (("category", "category_coverage"), ("data_source", "data_source_coverage"),
                         ("layer", "layer_coverage")):
        if meta is None:
            out[out_key] = None
            continue
        total = {v.get(key) for v in meta.values() if v} - {None}
        sel = {meta.get(f, {}).get(key) for f in feats} - {None}
        out[out_key] = float(len(sel) / len(total)) if total else 0.0
    return out


def _ref_all(df: pd.DataFrame, close: Optional[pd.Series], meta: Optional[Mapping[str, Mapping[str, Any]]],
             horizons: List[int]) -> Dict[str, Any]:
    feats = [c for c in df.columns if c != LABEL]
    rows = {f: _ref_quantile_fields(df, f) for f in feats}
    decay = {f: _ref_decay(df, f, close, horizons) for f in feats} if close is not None else None
    corr, corr_scale = _ref_corr(df, feats)
    return {"rows": rows, "features": feats, "corr": corr, "corr_scale": corr_scale,
            "div": _ref_diversification(corr, feats, meta),
            "decay": decay, "horizons": horizons}


def _assert_report(report: Mapping[str, Any], exp: Mapping[str, Any]) -> None:
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f, fields in exp["rows"].items():
        for k in FIELDS:
            got = rows[f].get(k)
            if k == "ic_half_life":
                if exp["decay"] is None:
                    assert got is None, f"{f}/ic_half_life：產品 {got!r} vs oracle None（無收盤或衰減關）"
                    continue
                # 半衰期＝擬合參數之衍生量：逐 horizon IC 對 oracle（1e-12）、擬合最佳性與衍生一致、summary＝ic_decay 之值
                fit = report["ic_decay"][f]
                assert fit["horizons"] == exp["horizons"], fit["horizons"]
                for h, g, w, s in zip(exp["horizons"], fit["ic_values"], exp["decay"][f]["ic_values"],
                                      exp["decay"][f]["scales"]):
                    assert _mean_close(g, w, s), f"{f}/ic_decay h={h}：產品 {g!r} vs oracle {w!r}（尺度 {s!r}）"
                # 最佳性以產品之（上行已對 oracle 驗至 1e-12 之）逐 horizon IC 為擬合輸入（同 test_icperf_correctness.py
                # `test_decay_fit_optimal_and_derived_consistent` 之同一 y）：三參數非線性擬合對 1e-16 級輸入差異不穩定，
                # 以 oracle IC 擬合會把「IC 對」與「擬合最佳」混為一項
                prod_ic = [_nan_if_none(v) for v in fit["ic_values"]]
                _assert_decay_fit(fit, prod_ic, _ref_min_ssr(exp["horizons"], prod_ic), f"{f}/ic_decay")
                assert _rel(_nan_if_none(got), _nan_if_none(fit["half_life"])) == 0.0, (f, got, fit["half_life"])
                continue
            want = fields[k]
            assert got is not None, f"{f}/{k}：產品 None（佔位）vs oracle {want!r}"
            assert _rel(got, want) <= REL_TOL, f"{f}/{k}：產品 {got!r} vs oracle {want!r}"
        # 方向對齊單調性取同一截面分位均值（方向欄本身由既有跨標的 oracle 測試驗）
        want_al = _ref_aligned_monotonicity(fields["_means"], int(rows[f]["direction"]))
        assert _rel(_nan_if_none(rows[f]["monotonicity_score_aligned"]), want_al) <= REL_TOL, \
            f"{f}/monotonicity_score_aligned：產品 {rows[f]['monotonicity_score_aligned']!r} vs oracle {want_al!r}"
    cm = report["correlation_matrix"]
    assert cm["features"] == exp["features"], cm["features"]
    want = np.nan_to_num(exp["corr"], nan=0.0)
    got = np.asarray(cm["matrix"], dtype=float)
    assert got.shape == want.shape, (got.shape, want.shape)
    for i, a in enumerate(exp["features"]):
        for j, b in enumerate(exp["features"]):
            assert _mean_close(got[i, j], want[i, j], exp["corr_scale"][i, j]), \
                f"corr {a}/{b}：產品 {got[i, j]!r} vs oracle {want[i, j]!r}"
    div = report["diversification_metrics"]
    for k in DIV_KEYS:
        assert k in div, f"diversification_metrics 缺 {k}：{div}"
        assert _rel(div[k], exp["div"][k]) <= REL_TOL, f"div/{k}：產品 {div[k]!r} vs oracle {exp['div'][k]!r}"


# ── 明列邊界輸入（秒級） ─────────────────────────────────────────────────────────────────────────────


def _explicit_inputs(n_dates: int = 60, symbols: tuple = ("AAA", "BBB", "CCC", "DDD", "EEE")
                     ) -> tuple[pd.DataFrame, pd.Series]:
    """明列邊界輸入（MultiIndex timestamp、symbol）：
    f1 連續相異；f2 整數值含大量同值（部分時點 qcut 邊界重複 ⇒ 該時點不入）與 NaN；f3 部分時點部分標的 NaN（相關矩陣之
    逐對共同列路徑）、含 +inf（t＝12、AAA）與 −inf（t＝30、CCC）；f4 每時點各標的同值（截面常數：分位全不成立、相關 NaN）；
    t＝10 只剩 1 標的（截面不成立）；標籤末時點全 NaN（標籤非有限之觀測不入分位均值；更多標籤缺值會觸發既有標籤覆蓋率
    門檻）；收盤為正之明列序列（衰減用）。"""
    ts = pd.date_range("2024-03-01", periods=n_dates, freq="h")
    rows, closes = [], []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(symbols):
            if t == 10 and j > 0:
                continue
            f1 = math.sin(t / 5.0 + j) + 0.1 * j
            f2 = math.nan if (t + j) % 13 == 0 else float(((3 * t + 7 * j) % 4) - 2) if t % 3 else float(j % 2)
            f3 = math.nan if ((sym == "EEE" and t % 7 == 0) or (sym == "BBB" and t % 5 == 0)) else math.cos(t / 4.0 + 0.5 * j)
            if (t, sym) == (12, "AAA"):
                f3 = math.inf
            if (t, sym) == (30, "CCC"):
                f3 = -math.inf
            f4 = 0.25 * t
            y = 0.01 * math.cos(t / 3.0 + 0.7 * j) + 0.002 * f1
            if t == n_dates - 1:
                y = math.nan
            close = 100.0 * (1.0 + 0.1 * j) * math.exp(0.002 * t + 0.01 * math.sin(t / 2.0 + j))
            rows.append((stamp, sym, f1, f2, f3, f4, y))
            closes.append((stamp, sym, close))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f1", "f2", "f3", "f4", LABEL]).set_index(
        ["timestamp", "symbol"]).sort_index()
    close = pd.DataFrame(closes, columns=["timestamp", "symbol", "close"]).set_index(["timestamp", "symbol"])["close"]
    return df, close.sort_index()


EXPLICIT_META = {"f1": {"category": "trend", "data_source": "kline", "layer": 1},
                 "f2": {"category": "trend", "data_source": "orderbook", "layer": 2},
                 "f3": {"category": "volatility", "data_source": "kline", "layer": 1},
                 "f4": {"category": "volume", "data_source": "kline", "layer": 1},
                 "not_in_data": {"category": "pattern", "data_source": "funding", "layer": 3}}


def _horizons() -> List[int]:
    return list(ICConfig().ic_calculation.ic_decay_horizons)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_placeholder_fields_match_oracle_explicit() -> None:
    """明列邊界輸入：summary 五欄、相關矩陣（含逐對共同列、±inf、截面常數、單標的時點）、多元化指標 == 參考實作。"""
    df, close = _explicit_inputs()
    report = create_ic_analyzer().analyze_cross_sectional(
        df, config_override={"ic_train_test_split": False}, close=close, feature_metadata=EXPLICIT_META)
    exp = _ref_all(df, close, EXPLICIT_META, _horizons())
    # 前提：邊界確實出現（f2 有時點 qcut 不成立、f4 全不成立、f3 有部分 NaN 時點、q＝5）
    assert len(_date_bins(df, "f2", 5)) < df.index.get_level_values(0).nunique() - 1, "f2 無 qcut 不成立時點（前提失效）"
    assert not _date_bins(df, "f4", 5), "f4 有 qcut 成立時點（前提失效）"
    assert exp["rows"]["f1"]["_q"] == 5
    assert any(report["ic_decay"][f]["decay_type"] != "fit_failed" for f in ("f1", "f2", "f3")), "衰減全不擬合（前提失效）"
    _assert_report(report, exp)
    assert "cross_sectional_unavailable_fields" not in report["metadata"] or not report["metadata"][
        "cross_sectional_unavailable_fields"], report["metadata"].get("cross_sectional_unavailable_fields")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_monotonicity_falls_back_to_three_quantiles_on_small_pool() -> None:
    """總觀測數／5 < 30 ⇒ 單調性與多空價差用 3 分位（同縱向 `_select_num_quantiles`）；換手率仍 5 分位。"""
    df, close = _explicit_inputs(n_dates=20, symbols=("AAA", "BBB", "CCC", "DDD"))
    report = create_ic_analyzer().analyze_cross_sectional(
        df, config_override={"ic_train_test_split": False}, close=close, feature_metadata=EXPLICIT_META)
    exp = _ref_all(df, close, EXPLICIT_META, _horizons())
    assert exp["rows"]["f1"]["_q"] == 3, "前提：總觀測數不足使 q 退回 3"
    _assert_report(report, exp)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_unavailable_fields_carry_reasons() -> None:
    """無收盤 ⇒ ic_half_life None＋`close_not_provided`；衰減關 ⇒ `decay_analysis_off`；無 metadata ⇒ 三覆蓋率 None＋
    `feature_metadata_not_provided`（不以 0.0 冒充）；其餘欄照常有值。"""
    df, close = _explicit_inputs()
    an = create_ic_analyzer()
    rep = an.analyze_cross_sectional(df, config_override={"ic_train_test_split": False})
    exp = _ref_all(df, None, None, _horizons())
    _assert_report(rep, exp)
    reasons = rep["metadata"]["cross_sectional_unavailable_fields"]
    assert reasons == {"ic_half_life": "close_not_provided",
                       "diversification_metrics.metadata_coverage": "feature_metadata_not_provided"}, reasons
    rep_off = an.analyze_cross_sectional(
        df, config_override={"ic_train_test_split": False, "report": {"include_decay_analysis": False}},
        close=close, feature_metadata=EXPLICIT_META)
    assert rep_off["metadata"]["cross_sectional_unavailable_fields"] == {"ic_half_life": "decay_analysis_off"}
    assert all(r["ic_half_life"] is None for r in rep_off["summary_table"])
    for r in (rep, rep_off):
        assert r["ic_decay"] == {"status": "not_applicable", "reason": "cross_sectional_mode"}, r["ic_decay"]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_turnover_disabled_drops_key() -> None:
    """`turnover.enabled` 關 ⇒ summary 之 turnover_rate 缺席（同縱向 ICHC R6 語意）；其餘四欄照常。"""
    df, close = _explicit_inputs()
    rep = create_ic_analyzer().analyze_cross_sectional(
        df, config_override={"ic_train_test_split": False, "turnover": {"enabled": False}}, close=close,
        feature_metadata=EXPLICIT_META)
    assert all("turnover_rate" not in r for r in rep["summary_table"])
    exp = _ref_all(df, close, EXPLICIT_META, _horizons())
    rows = {r["feature_name"]: r for r in rep["summary_table"]}
    for f, fields in exp["rows"].items():
        for k in ("monotonicity_score", "long_short_spread", "coverage"):
            assert _rel(rows[f][k], fields[k]) <= REL_TOL, (f, k, rows[f][k], fields[k])


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_single_feature_correlation_and_diversification() -> None:
    """單一特徵：相關矩陣 1×1（對角 1）、多元化之有效獨立特徵數＝1（`compute_diversification_metrics` 之 n ≤ 1 分支）。"""
    df, close = _explicit_inputs()
    one = df[["f1", LABEL]]
    rep = create_ic_analyzer().analyze_cross_sectional(
        one, config_override={"ic_train_test_split": False}, close=close, feature_metadata=EXPLICIT_META)
    _assert_report(rep, _ref_all(one, close, EXPLICIT_META, _horizons()))
    assert rep["correlation_matrix"]["matrix"] == [[1.0]]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_block_chunking_does_not_change_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """分塊上限壓到最小（每塊 1 特徵、1 時點、1 部分缺值欄）之報告 == 預設分塊之報告：逐特徵量（分位、換手、覆蓋、
    衰減）逐位元相同；相關矩陣為跨時點塊之累加，求和順序隨分塊而變 ⇒ 以 1e-12 比（分塊只界記憶體不改定義）。"""
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    df, close = _explicit_inputs()
    kw = dict(config_override={"ic_train_test_split": False}, close=close, feature_metadata=EXPLICIT_META)
    base = create_ic_analyzer().analyze_cross_sectional(df, **kw)
    monkeypatch.setattr(ICFilterOrchestrator, "_XSEC_BLOCK_BYTES", 1)
    tiny = create_ic_analyzer().analyze_cross_sectional(df, **kw)
    assert repr(tiny["ic_decay"]) == repr(base["ic_decay"])
    pick = lambda rep: [{k: r.get(k) for k in FIELDS} for r in rep["summary_table"]]  # noqa: E731
    assert repr(pick(tiny)) == repr(pick(base))
    assert tiny["correlation_matrix"]["features"] == base["correlation_matrix"]["features"]
    np.testing.assert_allclose(tiny["correlation_matrix"]["matrix"], base["correlation_matrix"]["matrix"],
                               rtol=REL_TOL, atol=1e-15)
    for k in DIV_KEYS:
        assert _rel(tiny["diversification_metrics"][k], base["diversification_metrics"][k]) <= REL_TOL, k


def test_xsec_misaligned_close_rejected() -> None:
    """收盤索引與特徵不對齊（如時區不同 ⇒ 全 NaN）⇒ InvalidInputError（不靜默產出全 NaN 衰減）。"""
    from momentum.core.exceptions import InvalidInputError

    df, close = _explicit_inputs()
    bad = close.copy()
    bad.index = bad.index.set_levels(bad.index.levels[0].tz_localize("UTC"), level=0)
    with pytest.raises(InvalidInputError):
        create_ic_analyzer().analyze_cross_sectional(df, config_override={"ic_train_test_split": False}, close=bad)


def test_xsec_duplicate_panel_rows_rejected() -> None:
    """同一 (時點, 標的) 重複列 ⇒ InvalidInputError（截面面板不唯一，不靜默覆寫）。"""
    from momentum.core.exceptions import InvalidInputError

    df, _ = _explicit_inputs()
    dup = pd.concat([df, df.iloc[[5]]]).sort_index()
    with pytest.raises(InvalidInputError):
        create_ic_analyzer().analyze_cross_sectional(dup, config_override={"ic_train_test_split": False})


# ── 真實 kline（requires_kline） ───────────────────────────────────────────────────────────────────


def _real_frame(rows: int) -> tuple[pd.DataFrame, pd.Series]:
    """kline_cache.h5 之全部 1h 標的末 rows 根（時間層 naive UTC，同服務端）：因果特徵 ret1、dev20、vol20、mom10、cret
    （ret1 只在收盤高於 50 根中位數時有值——真實資料決定之逐標的缺值，走相關矩陣之逐對共同列路徑）；標籤 return_1＝簡單報酬。"""
    import h5py

    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        symbols = sorted(k for k in f.keys() if not k.startswith("_") and f"{k}/1h/data" in f)
        raw = {s: f[f"{s}/1h/data"][-rows:] for s in symbols}
    frames, closes = [], []
    for sym in symbols:
        data = raw[sym]
        idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s")
        c = pd.Series(data["close"].astype("float64"), index=idx)
        ret = c.pct_change()
        part = pd.DataFrame({"ret1": ret, "dev20": c / c.rolling(20).mean() - 1.0, "vol20": ret.rolling(20).std(),
                             "mom10": c / c.shift(10) - 1.0, "cret": ret.where(c > c.rolling(50).median()),
                             LABEL: c.shift(-1) / c - 1.0})
        mi = pd.MultiIndex.from_arrays([idx, [sym] * len(idx)], names=["timestamp", "symbol"])
        part.index = mi
        frames.append(part)
        closes.append(pd.Series(c.to_numpy(), index=mi))
    return pd.concat(frames).sort_index(), pd.concat(closes).sort_index()


def _ref_split_test_mask(df: pd.DataFrame, oos: float, min_rows: int, embargo: int, horizon: int) -> np.ndarray:
    """跨標的預設切分（全域同步時間 holdout）之參考實作：唯一時點排序，train＝前 floor((1−oos)·n) 個時點；test＝≥ train 末
    時點＋(horizon＋embargo)×K 線間距（間距＝相鄰時點差之中位數，由資料導出）；全域與每標的 test 列數 ≥ min_rows 方成立。"""
    ts = pd.DatetimeIndex(df.index.get_level_values(0))
    uts = ts.unique().sort_values()
    sp = int(math.floor((1.0 - oos) * len(uts)))
    freq = pd.Timedelta(np.median(np.diff(uts.asi8)), unit="ns")
    t_end = uts[sp - 1]
    test = np.asarray(ts >= t_end + (horizon + embargo) * freq)
    sym = np.asarray(df.index.get_level_values(1)).astype(str)
    assert int((ts <= t_end).sum()) >= min_rows and int(test.sum()) >= min_rows
    assert all(int((test & (sym == s)).sum()) >= min_rows for s in set(sym)), "每標的測試段不足（資料不足）"
    return test


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_xsec_placeholder_fields_match_oracle_on_real_kline() -> None:
    """真實多標的 1h（kline_cache.h5 全部 1h 標的末 2,000 根）、預設設定（切分開）：測試段上 summary 五欄、相關矩陣、多元化
    指標 == 參考實作（測試段以 `_ref_split_test_mask` 獨立重建）；各欄於真實資料有有限值（非佔位）。"""
    df, close = _real_frame(2000)
    assert df.index.get_level_values(1).nunique() >= 2, "本機無多標的真實資料"
    cfg = ICConfig()
    assert cfg.ic_train_test_split, "前提：預設切分開"
    test = _ref_split_test_mask(df, float(cfg.oos_test_size), int(cfg.min_test_rows), int(cfg.embargo), 1)
    meta = {"ret1": {"category": "momentum", "data_source": "kline", "layer": 1},
            "dev20": {"category": "mean_reversion", "data_source": "kline", "layer": 1},
            "vol20": {"category": "volatility", "data_source": "kline", "layer": 1},
            "mom10": {"category": "momentum", "data_source": "kline", "layer": 1},
            "cret": {"category": "momentum", "data_source": "kline", "layer": 2}}
    report = create_ic_analyzer().analyze_cross_sectional(df, timeframe="1h", close=close, feature_metadata=meta)
    assert report["metadata"]["ic_train_test_split"].get("applied", True)
    seg = df.iloc[np.flatnonzero(test)]
    exp = _ref_all(seg, close, meta, _horizons())
    _assert_report(report, exp)
    for f, fields in exp["rows"].items():
        for k in ("monotonicity_score", "long_short_spread", "coverage", "turnover_rate"):
            assert math.isfinite(fields[k]), f"{f}/{k}：真實資料上非有限（前提失效）"
    off = np.abs(exp["corr"][np.triu_indices(len(exp["features"]), k=1)])
    assert np.isfinite(off).all() and (off > 0).all(), "真實資料相關矩陣含無效對（前提失效）"
