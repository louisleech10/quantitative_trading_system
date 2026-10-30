"""ICPERF Task 0.4 ㉗–㉛ oracle 測試（docs/ICPERF_SPEC.md v5.39 Task 0.4 擴列表 ㉗㉘㉙㉚㉛ 列之「驗證」欄）。

契約（SPEC 各列「修正」欄）：
- ㉗ `ICEngine.compute_rolling_ic` 之 `method == "kendall"` ⇒ 逐窗 Kendall τ-b（同 `scipy.stats.kendalltau` 之定義；窗內
  任一非有限 ⇒ NaN，同 ④；常數窗 ⇒ NaN）。
- ㉘ Pearson 滾動 IC 之窗內動差以數值穩定算法計（不以原值累積和相減），與逐窗 `scipy.stats.pearsonr` 相對誤差 ≤ 1e-12。
- ㉙ `TurnoverAnalyzer.compute_factor_autocorrelation`：去 NaN 後有限值相異數 < 2、或 lag 兩段任一為常數、或含 ±inf ⇒ NaN。
- ㉚ 點 IC（`ICEngine.compute_ic` 向量化路徑）相關矩陣一律二維處理；常數標籤 ⇒ 全欄 NaN；常數特徵 ⇒ 該欄 NaN、他欄不受影響。
- ㉛ ICIR 窗以同一 `_adjust_rolling_windows` 換算；換算後之窗不在滾動窗集合 ⇒ 另算該窗（不靜默退回第一個窗）；IC 頁
  ICIR 與參數敏感度（⑬⑳）之 ICIR 同窗同值。

oracle（不呼叫被測模組之計算函式）：逐窗 `scipy.stats.{spearmanr,pearsonr,kendalltau}`、numpy 自寫之 lag-1 Pearson 公式、
滾動 IC 之 ICIR＝nanmean／nanstd(ddof=0)（同現行定義，`test_icperf_correctness.py::test_icir_definitions_match_oracle`）。
時間軸＝標籤有限之列（同 Task 0.4 ④）；窗終點＝window−1, window−1+stride, …。

真實資料：`data_cache/feature_klines/kline_cache.h5`（BTCUSDT 1h／4h／12h）。邊界案為明列輸入之秒級測試（SPEC §V
「單元邊界案除外，需明列為邊界輸入」）。本檔之 requires_kline 測試須經共用監看執行（autouse 自證，同
test_icperf_correctness.py）。
"""

from __future__ import annotations

import json
import math
import os
import warnings
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

import h5py
import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.ic_engine import ICEngine
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer
from momentum.Analysis.turnover_analyzer import TurnoverAnalyzer
from momentum.FeatureEngineering.feature_naming import stamp_h5_feature_naming_version
from momentum.factories import create_ic_analyzer, create_kline_storage_manager

REPO = Path(__file__).resolve().parents[3]
KLINE_CACHE = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
HEAVY_MARKERS = ("slow", "requires_kline")
#: SPEC ㉗㉘「驗證」：逐窗相對誤差門檻
REL_TOL = 1e-12
SCIPY: Dict[str, Callable[..., Any]] = {
    "spearman": stats.spearmanr,
    "pearson": stats.pearsonr,
    "kendall": stats.kendalltau,
}
#: 預設設定（ic_config_schema.py `ICCalculationConfig`）：滾動窗、ICIR 窗、參考週期
DEFAULT_WINDOWS = [21, 63, 126]
DEFAULT_ICIR_WINDOW = 63
REFERENCE_TF = "12h"
TF_HOURS = {"1h": 1.0, "4h": 4.0, "12h": 12.0}


# ── 共用監看（同 test_icperf_correctness.py） ──────────────────────────────────────────────────────


def _watchdog_missing(markers: Sequence[str], environ: Mapping[str, str]) -> bool:
    """標 slow 或 requires_kline 而未在共用監看下執行 ⇒ True（共用監看對子行程恆注入 `WATCHDOG_STACK_FILE`）。"""
    return any(m in HEAVY_MARKERS for m in markers) and not environ.get("WATCHDOG_STACK_FILE")


@pytest.fixture(autouse=True)
def _heavy_tests_require_shared_watchdog(request: pytest.FixtureRequest) -> None:
    """本檔重型／真實資料測試於執行端自證經共用監看，未經即 FAIL。"""
    if _watchdog_missing([m.name for m in request.node.iter_markers()], os.environ):
        pytest.fail("本檔標 slow／requires_kline 之測試須經共用監看執行："
                    "venv/bin/python scripts/run_watched.py --log <路徑> -- <pytest 命令>（背景）")


# ── 真實 kline 與 oracle ────────────────────────────────────────────────────────────────────────────


def _kline(symbol: str, timeframe: str, rows: int) -> pd.DataFrame:
    """真實 kline 末 rows 根（float64；索引＝UTC 開盤時間）。"""
    assert KLINE_CACHE.is_file(), f"真實 kline 不存在：{KLINE_CACHE}"
    with h5py.File(KLINE_CACHE, "r") as f:
        data = f[f"{symbol}/{timeframe}/data"][-rows:]
    idx = pd.to_datetime(data["timestamp"].astype("int64"), unit="s", utc=True)
    cols = ("open", "high", "low", "close", "volume", "quote_volume", "number_of_trades")
    frame = pd.DataFrame({c: data[c].astype("float64") for c in cols}, index=idx)
    assert len(frame) == rows, f"{symbol}/{timeframe} 只有 {len(frame)} 根（需 {rows}）"
    return frame


def _label(close: pd.Series, horizon: int = 1) -> pd.Series:
    """真實標籤：簡單報酬 close[t+h]／close[t]−1（label_generator.py:45-47）。"""
    return (close.shift(-horizon) / close - 1.0).rename("label")


def _causal(close: pd.Series) -> pd.DataFrame:
    """真實 kline 上之因果特徵（只用 0..t）：過去 1 根報酬、對 20 根均線偏離、10 根動量。"""
    return pd.DataFrame({"ret1": close.pct_change(), "dev20": close / close.rolling(20).mean() - 1.0,
                         "mom10": close / close.shift(10) - 1.0})


def _rel(a: float, b: float) -> float:
    """相對誤差（兩者皆 NaN ⇒ 0；一方 NaN ⇒ inf；b 為 0 ⇒ 絕對誤差）。"""
    if math.isnan(a) and math.isnan(b):
        return 0.0
    if math.isnan(a) or math.isnan(b):
        return math.inf
    return abs(a - b) / abs(b) if b != 0 else abs(a - b)


def _oracle_rolling(F: pd.DataFrame, y: pd.Series, window: int, method: str, stride: int = 1) -> Dict[str, List[float]]:
    """滾動 IC 之 oracle：時間軸＝標籤有限之列；每窗每特徵獨立，窗內該特徵或標籤有任一非有限值、或任一為常數 ⇒ NaN；
    否則逐窗 scipy 對應函式（kendall＝τ-b）。"""
    yv = y.reindex(F.index).to_numpy(dtype=float)
    rows = np.flatnonzero(np.isfinite(yv))
    X = F.to_numpy(dtype=float)
    out: Dict[str, List[float]] = {c: [] for c in F.columns}
    for end in range(window - 1, rows.size, stride):
        sel = rows[end - window + 1:end + 1]
        yw = yv[sel]
        for j, c in enumerate(F.columns):
            xw = X[sel, j]
            if not (np.all(np.isfinite(xw)) and np.all(np.isfinite(yw))) or np.ptp(xw) == 0 or np.ptp(yw) == 0:
                out[c].append(math.nan)
            else:
                out[c].append(float(SCIPY[method](xw, yw)[0]))
    return out


def _exact_pearson(x: np.ndarray, y: np.ndarray) -> Decimal:
    """Pearson 之精確值：浮點輸入轉有理數（`fractions.Fraction` 精確表示二進位浮點）求均值與中心化動差，開方以 60 位
    `decimal`。只供 scipy 本身之捨入不足以判 1e-12 之窗（相關近 0 ⇒ 相對誤差病態）裁定用。"""
    fx = [Fraction(float(v)) for v in x]
    fy = [Fraction(float(v)) for v in y]
    n = len(fx)
    mx, my = sum(fx) / n, sum(fy) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(fx, fy))
    sxx = sum((a - mx) ** 2 for a in fx)
    syy = sum((b - my) ** 2 for b in fy)
    with localcontext() as ctx:
        ctx.prec = 60
        num = Decimal(sxy.numerator) / Decimal(sxy.denominator)
        den = (Decimal(sxx.numerator) / Decimal(sxx.denominator)
               * (Decimal(syy.numerator) / Decimal(syy.denominator))).sqrt()
        return num / den


def _window_rows(F: pd.DataFrame, y: pd.Series, window: int, stride: int, i: int) -> tuple[np.ndarray, np.ndarray]:
    """第 i 個輸出窗之時間軸列（同 `_oracle_rolling`）。"""
    yv = y.reindex(F.index).to_numpy(dtype=float)
    rows = np.flatnonzero(np.isfinite(yv))
    end = window - 1 + i * stride
    return rows[end - window + 1:end + 1], yv


def _assert_rolling(got: Mapping[str, Any], exp: Mapping[str, List[float]], window: int, tol: float = REL_TOL,
                    F: Optional[pd.DataFrame] = None, y: Optional[pd.Series] = None, stride: int = 1) -> None:
    """逐窗 == oracle（相對誤差 ≤ tol）。給 F、y（Pearson）時，與 scipy 差逾 tol 之窗以精確值裁定：產品對精確值之相對誤差
    ≤ tol，或產品對精確值之絕對誤差 ≤ scipy 對精確值之絕對誤差（相關近 0 之窗，scipy 自身之捨入即逾 1e-12 相對，
    `routeE_exact` 實測：真實 ema55 窗 r≈−8.6e-6 時 scipy 相對真值 2.9e-12、產品 8.1e-14）。"""
    for c, vals in exp.items():
        g = got[c][f"window_{window}"]
        assert len(g) == len(vals), f"{c}/window_{window}：長度 {len(g)} vs oracle {len(vals)}"
        bad = [(i, a, b) for i, (a, b) in enumerate(zip(g, vals)) if _rel(float(a), float(b)) > tol]
        if F is not None and y is not None:
            unresolved = []
            for i, a, b in bad:
                if not (math.isfinite(float(a)) and math.isfinite(float(b))):
                    unresolved.append((i, a, b))
                    continue
                sel, yv = _window_rows(F, y, window, stride, i)
                ex = _exact_pearson(F[c].to_numpy(dtype=float)[sel], yv[sel])
                e_prod, e_scipy = abs(Decimal(float(a)) - ex), abs(Decimal(float(b)) - ex)
                if not (e_prod <= Decimal(tol) * abs(ex) or e_prod <= e_scipy):
                    unresolved.append((i, a, b, float(ex)))
            bad = unresolved
        assert not bad, f"{c}/window_{window}：{len(bad)} 窗超差，首例 {bad[:3]}"


def _icir_oracle(values: Sequence[float]) -> Dict[str, float]:
    """ICIR 之現行定義：nanmean／nanstd(ddof=0)；std ≤ 0 ⇒ NaN；勝率＝有限值中 > 0 之比例。"""
    v = np.asarray(values, dtype=float)
    fin = v[np.isfinite(v)]
    if fin.size == 0:
        return {"ic_mean": math.nan, "ic_std": math.nan, "icir": math.nan, "ic_hit_rate": math.nan}
    mean = float(fin.sum() / fin.size)
    std = float(np.sqrt(((fin - mean) ** 2).sum() / fin.size))
    return {"ic_mean": mean, "ic_std": std, "icir": mean / std if std > 0 else math.nan,
            "ic_hit_rate": float((fin > 0).sum() / fin.size)}


def _adjusted(window: int, timeframe: str) -> int:
    """依週期換算之窗（同 SPEC TFWINDOW：round(window × reference／current)，至少 1）。"""
    return max(int(round(window * TF_HOURS[REFERENCE_TF] / TF_HOURS[timeframe])), 1)


# ── ㉗ Kendall 滾動 IC ────────────────────────────────────────────────────────────────────────────


@pytest.mark.requires_kline
@pytest.mark.parametrize("stride", [1, 3])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_kendall_matches_kendalltau_on_real_kline(stride: int) -> None:
    """SPEC ㉗：method＝kendall 之滾動 IC 逐窗 == `scipy.stats.kendalltau`（τ-b，相對誤差 ≤ 1e-12）。真實 BTCUSDT 1h 末
    500 根：因果特徵三欄、報酬符號（大量同值，驗 τ-b 之同值修正）、成交量與收盤（價格水準）；stride 1 與 3。"""
    k = _kline("BTCUSDT", "1h", 500)
    close = k["close"]
    F = _causal(close).assign(sign_ret=np.sign(close.pct_change()), volume=k["volume"], close=close).iloc[20:]
    y = _label(close).reindex(F.index)
    got = ICEngine({}).compute_rolling_ic(F, y, [21, 63], stride, "kendall")
    for w in (21, 63):
        _assert_rolling(got, _oracle_rolling(F, y, w, "kendall", stride), w)
    assert F["sign_ret"].nunique() <= 3, "前提：報酬符號欄須有大量同值"


def _boundary_inputs(case: str) -> tuple[pd.DataFrame, pd.Series]:
    """明列邊界輸入（60 列、窗 10）：含同值之兩特徵；依 case 置入非有限值、常數段或標籤缺值。"""
    i = np.arange(60, dtype=float)
    idx = pd.date_range("2026-01-01", periods=60, freq="2h", tz="UTC")
    F = pd.DataFrame({"a": (5.0 * i) % 7.0, "b": np.round(np.sin(i / 3.0), 1)}, index=idx)
    y = pd.Series(((3.0 * i) % 11.0) - 5.0 + np.round(np.cos(i / 4.0), 1), index=idx, name="label")
    if case == "nan_in_window":
        F.iloc[12, 0] = np.nan
    elif case == "inf_in_window":
        F.iloc[25, 1] = np.inf
        F.iloc[40, 0] = -np.inf
    elif case == "constant_feature_window":
        F.iloc[20:38, 0] = 2.0
    elif case == "constant_label_window":
        y.iloc[30:45] = 0.5
    elif case == "label_nan":
        y.iloc[[15, 33]] = np.nan
    elif case == "near_constant_price_level":
        F["a"] = 26767.52 + 0.01 * ((7.0 * i) % 5.0)
        F["b"] = 1.0e9 + ((3.0 * i) % 4.0)
    return F, y


BOUNDARY_CASES = ["ties", "nan_in_window", "inf_in_window", "constant_feature_window", "constant_label_window",
                  "label_nan", "near_constant_price_level"]


@pytest.mark.parametrize("method", sorted(SCIPY))
@pytest.mark.parametrize("case", BOUNDARY_CASES)
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_ic_boundaries_match_scipy(method: str, case: str) -> None:
    """SPEC ㉗㉘（④ 同規則）之明列邊界：同值、窗內 NaN、窗內 ±inf、窗內特徵常數、窗內標籤常數、標籤缺值（時間軸剔除）、
    近常數價格水準（大偏移小變異）——三方法逐窗 == scipy oracle（相對誤差 ≤ 1e-12）；stride 1 與 4。"""
    F, y = _boundary_inputs(case)
    for stride in (1, 4):
        got = ICEngine({"icir": {"window": 10}}).compute_rolling_ic(F, y, [10], stride, method)
        adjudicate = {"F": F, "y": y, "stride": stride} if method == "pearson" else {}
        _assert_rolling(got, _oracle_rolling(F, y, 10, method, stride), 10, **adjudicate)
    if case in ("nan_in_window", "inf_in_window", "constant_feature_window", "constant_label_window"):
        series = ICEngine({"icir": {"window": 10}}).compute_rolling_ic(F, y, [10], 1, method)
        assert any(math.isnan(v) for c in F.columns for v in series[c]["window_10"]), "前提：邊界須產生 NaN 窗"


# ── ㉘ Pearson 滾動 IC 數值穩定 ───────────────────────────────────────────────────────────────────


def _price_level_inputs(case: str) -> tuple[pd.DataFrame, pd.Series]:
    """真實 BTCUSDT 1h 末 2,000 根之價格水準輸入（SPEC ㉘「驗證」三類）。"""
    k = _kline("BTCUSDT", "1h", 2000)
    close = k["close"]
    if case == "price_features":
        F = pd.DataFrame({"close": close, "sma20": close.rolling(20).mean(),
                          "ema55": close.ewm(span=55, adjust=False).mean(), "high": k["high"]})
        y = _label(close)
    elif case == "close_vs_sma_label":
        F = pd.DataFrame({"close": close, "high": k["high"], "low": k["low"]})
        y = close.rolling(20).mean().rename("label")
    else:
        F = pd.DataFrame({"volume": k["volume"], "quote_volume": k["quote_volume"],
                          "trades": k["number_of_trades"]})
        y = k["volume"].rolling(20).mean().rename("label")
    F = F.iloc[60:]
    return F, y.reindex(F.index)


@pytest.mark.requires_kline
@pytest.mark.parametrize("case", ["price_features", "close_vs_sma_label", "volume"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_rolling_pearson_price_level_matches_pearsonr_on_real_kline(case: str) -> None:
    """SPEC ㉘：Pearson 滾動 IC 逐窗 == `scipy.stats.pearsonr`（相對誤差 ≤ 1e-12）於真實價格水準輸入——收盤／均線／高價
    對報酬標籤、收盤對 20 根均線（標籤亦為價格水準）、成交量類對成交量均線；窗 21／63／252。"""
    F, y = _price_level_inputs(case)
    got = ICEngine({}).compute_rolling_ic(F, y, [21, 63, 252], 1, "pearson")
    for w in (21, 63, 252):
        _assert_rolling(got, _oracle_rolling(F, y, w, "pearson"), w, F=F, y=y)


# ── ㉙ 常數序列 lag-1 自相關 ─────────────────────────────────────────────────────────────────────


def _autocorr_oracle(values: Sequence[float]) -> float:
    """lag-1 自相關之 numpy 獨立公式：去 NaN；含 ±inf、列數 < 2 或 lag 兩段任一常數 ⇒ NaN；否則
    Σ(a−ā)(b−b̄)／√(Σ(a−ā)²·Σ(b−b̄)²)，a＝v[:-1]、b＝v[1:]。"""
    v = np.asarray(values, dtype=float)
    v = v[~np.isnan(v)]
    if v.size < 2 or not np.all(np.isfinite(v)):
        return math.nan
    a, b = v[:-1], v[1:]
    if np.ptp(a) == 0 or np.ptp(b) == 0:
        return math.nan
    da, db = a - a.mean(), b - b.mean()
    return float((da * db).sum() / math.sqrt(float((da * da).sum()) * float((db * db).sum())))


_C, _D = 26767.52, 26801.13
AUTOCORR_CASES: Dict[str, List[float]] = {
    "constant": [_C] * 19,
    "near_constant": [_C + 1e-6 * ((7 * j) % 5) for j in range(19)],
    "single_distinct_first": [_D] + [_C] * 18,
    "single_distinct_last": [_C] * 18 + [_D],
    "single_distinct_middle": [_C] * 9 + [_D] + [_C] * 9,
    "alternating_two_values": [_C, _D] * 10,
    "two_points": [_C, _D],
    "one_point": [_C],
    "with_nan": [_C, np.nan, _D, _C + 3.0, np.nan, _D - 1.0, _C + 7.5, _D + 2.0],
    "with_nan_constant_rest": [np.nan, _C, np.nan, _C, _C, np.nan, _C],
    "with_inf": [_C, _D, np.inf, _C + 3.0, _D - 1.0],
    "price_like": [_C + 13.7 * math.sin(j / 2.0) + 0.9 * j for j in range(19)],
}


@pytest.mark.parametrize("case", sorted(AUTOCORR_CASES))
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_factor_autocorrelation_boundaries_match_numpy_oracle(case: str) -> None:
    """SPEC ㉙：`compute_factor_autocorrelation` 與 `compute_all` 之 autocorrelation == numpy 獨立公式（相對誤差 ≤ 1e-12）；
    常數、單一相異值於首／尾（lag 一段常數）、去 NaN 後常數、含 ±inf、列數 < 2 ⇒ NaN；近常數、單一相異值於中段、兩值交替、
    含 NaN 之一般序列 ⇒ 有值。"""
    values = AUTOCORR_CASES[case]
    idx = pd.date_range("2026-02-24", periods=len(values), freq="4h", tz="UTC")
    x = pd.Series(values, index=idx, name="f")
    exp = _autocorr_oracle(values)
    got = TurnoverAnalyzer({}).compute_factor_autocorrelation(x)
    assert _rel(float(got), exp) <= REL_TOL, f"{case}：{got!r} vs oracle {exp!r}"
    got_all = TurnoverAnalyzer({}).compute_all(x.to_frame())["f"]["autocorrelation"]
    assert _rel(float(got_all), exp) <= REL_TOL, f"{case}（compute_all）：{got_all!r} vs oracle {exp!r}"
    expect_nan = case in {"constant", "single_distinct_first", "single_distinct_last", "two_points", "one_point",
                          "with_nan_constant_rest", "with_inf"}
    assert math.isnan(exp) == expect_nan, f"前提：{case} 之 oracle NaN 與否不符明列預期"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_factor_autocorrelation_real_kline_constant_feature_is_nan() -> None:
    """SPEC ㉙「驗證」：真實 BTCUSDT 4h（L 格同標的同週期）末 2,000 根之測試段（末 600 根）——常數特徵（收盤 > 0 之指示、
    區間最大成交筆數上限指示）自相關＝NaN；價格水準特徵（收盤、20 根均線）== numpy oracle（相對誤差 ≤ 1e-12）。"""
    k = _kline("BTCUSDT", "4h", 2000).iloc[-600:]
    close = k["close"]
    frame = pd.DataFrame({"close_pos": (close > 0).astype(float),
                          "trades_cap": (k["number_of_trades"] <= k["number_of_trades"].max()).astype(float),
                          "close": close, "sma20": close.rolling(20).mean()})
    out = TurnoverAnalyzer({}).compute_all(frame)
    for c in frame.columns:
        exp = _autocorr_oracle(frame[c].to_numpy(dtype=float))
        assert _rel(float(out[c]["autocorrelation"]), exp) <= REL_TOL, f"{c}：{out[c]['autocorrelation']!r} vs {exp!r}"
    assert math.isnan(float(out["close_pos"]["autocorrelation"])) and math.isnan(float(out["trades_cap"]["autocorrelation"]))
    assert math.isfinite(float(out["close"]["autocorrelation"]))


# ── ㉚ 點 IC 單欄與常數標籤 ──────────────────────────────────────────────────────────────────────


def _point_oracle(x: np.ndarray, y: np.ndarray, method: str) -> float:
    """點 IC 之 oracle：兩欄共同非 NaN 列；列數 < 2 或任一常數 ⇒ NaN；否則 scipy 對應函式。"""
    ok = ~np.isnan(x) & ~np.isnan(y)
    xa, ya = x[ok], y[ok]
    if xa.size < 2 or np.ptp(xa) == 0 or np.ptp(ya) == 0:
        return math.nan
    return float(SCIPY[method](xa, ya)[0])


POINT_CASES = ["single_feature", "two_features", "constant_label", "constant_first_feature",
               "constant_middle_feature", "all_constant_features", "constant_label_single_feature"]


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(SCIPY))
@pytest.mark.parametrize("case", POINT_CASES)
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_point_ic_degenerate_inputs_match_scipy(method: str, case: str) -> None:
    """SPEC ㉚：`compute_ic`（無缺值 ⇒ 向量化路徑；單欄 ⇒ 逐對路徑）於單特徵、兩特徵、常數標籤、常數特徵（首欄／中欄／全部）
    不拋例外，逐欄 == scipy oracle（常數 ⇒ NaN；他欄不受常數欄影響）。輸入＝真實 BTCUSDT 1h 末 400 根之因果特徵（去暖機
    與末根標籤缺值，使無缺值）；常數欄＝真實資料導出之常數（收盤 > 0 之指示）。"""
    k = _kline("BTCUSDT", "1h", 400)
    close = k["close"]
    F = _causal(close)
    y = _label(close)
    keep = F.notna().all(axis=1) & y.notna()
    F, y = F[keep], y[keep]
    const = (close[keep] > 0).astype(float)
    if case == "single_feature":
        F = F[["dev20"]]
    elif case == "two_features":
        F = F[["ret1", "dev20"]]
    elif case == "constant_label":
        y = pd.Series(np.full(len(y), 0.5), index=y.index, name="label")
    elif case == "constant_label_single_feature":
        F = F[["dev20"]]
        y = pd.Series(np.full(len(y), 0.5), index=y.index, name="label")
    elif case == "constant_first_feature":
        F = pd.concat([const.rename("const"), F], axis=1)
    elif case == "constant_middle_feature":
        F = pd.concat([F[["ret1"]], const.rename("const"), F[["dev20", "mom10"]]], axis=1)
    elif case == "all_constant_features":
        F = pd.DataFrame({"c1": const, "c2": const * 3.0})
    assert not F.isna().any().any() and not y.isna().any(), "前提：無缺值（走向量化路徑）"
    got = ICEngine({}).compute_ic(F, y, method)
    assert set(got) == set(F.columns)
    for c in F.columns:
        exp = _point_oracle(F[c].to_numpy(dtype=float), y.to_numpy(dtype=float), method)
        assert _rel(float(got[c]), exp) <= REL_TOL, f"{method}/{case}/{c}：{got[c]} vs scipy {exp}"


def _write_h5(path: Path, group_key: str, name: str, frame: pd.DataFrame, names_key: str) -> None:
    with h5py.File(path, "w") as f:
        stamp_h5_feature_naming_version(f.attrs)
        g = f.create_group(group_key)
        g.create_dataset(name, data=frame.to_numpy(dtype=np.float32))
        g.create_dataset("timestamps", data=(frame.index.asi8 // 10**9).astype(np.int64))
        g.create_dataset(names_key, data=np.array(frame.columns.tolist(), dtype=object),
                         dtype=h5py.string_dtype(encoding="utf-8"))


def _e2e_inputs(tmp_path: Path, feats: pd.DataFrame, label: pd.Series, timeframe: str) -> Dict[str, Path]:
    """float32 交接（同 IC 頁之 h5 交接）；oracle 用同一 float32 值。"""
    paths = {"features": tmp_path / "features.h5", "labels": tmp_path / "labels.h5", "meta": tmp_path / "meta.json"}
    _write_h5(paths["features"], f"BTCUSDT/{timeframe}", "features", feats, "feature_names")
    _write_h5(paths["labels"], f"BTCUSDT/{timeframe}", "labels", label.to_frame(), "label_names")
    meta = {"symbol": "BTCUSDT", "timeframe": timeframe, "case_id": "icperf_rolling_numerics"}
    meta.update({c: {"name": c, "category": "trend", "layer": 1, "data_source": "close"} for c in feats.columns})
    paths["meta"].write_text(json.dumps(meta), encoding="utf-8")
    return paths


def _e2e_override(method: str) -> Dict[str, Any]:
    grouped = {"by_regime": False, "by_year": False, "by_quarter": False, "by_category": False,
               "by_data_source": False, "by_layer": False}
    return {
        "global": {"default_method": method},
        "preprocessing": {"winsorization": {"enabled": False, "method": "none"},
                          "missing_values": {"max_fill_forward": 0, "min_coverage": 0.0}},
        "report": {"include_regime_analysis": False, "include_decay_analysis": False,
                   "include_turnover_analysis": False, "include_quantile_curves": False,
                   "include_correlation_heatmap": False, "include_layer_analysis": False, "ai_summary": False},
        "turnover": {"enabled": False},
        "ic_calculation": {"methods": [method], "grouped_analysis": grouped},
        "thresholds": {"ic_mean_min": -1.0, "icir_min": -1.0, "p_value_max": 1.0, "ic_hit_rate_min": 0.0,
                       "monotonicity_score_min": 0.0, "coverage_min": 0.0, "long_short_spread": {"enabled": False}},
    }


def _scope_rows(report: Mapping[str, Any], index: pd.DatetimeIndex) -> np.ndarray:
    """IC 之列範圍：切分成立 ⇒ 測試段時間界內；否則全樣本。"""
    split = (report.get("metadata") or {}).get("ic_train_test_split") or {}
    if not split.get("applied"):
        return np.ones(len(index), dtype=bool)
    lo, hi = (pd.Timestamp(t) for t in split["test_time_bounds"])
    naive = index.tz_convert("UTC").tz_localize(None)
    return np.asarray((naive >= lo) & (naive <= hi), dtype=bool)


def _analyze(tmp_path: Path, feats: pd.DataFrame, label: pd.Series, timeframe: str, method: str) -> Dict[str, Any]:
    paths = _e2e_inputs(tmp_path, feats, label, timeframe)
    override = _e2e_override(method)
    orch = create_ic_analyzer(override)
    return orch.analyze(features_path=str(paths["features"]), labels_path=str(paths["labels"]),
                        meta_path=str(paths["meta"]), config_override=override,
                        kline_reader=create_kline_storage_manager(cache_dir=str(KLINE_CACHE.parent)))


def _f32(frame: Any) -> Any:
    return frame.astype(np.float32).astype(np.float64)


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
@pytest.mark.parametrize("case", ["single_feature", "constant_first_feature"])
@pytest.mark.parametrize("method", ["spearman", "pearson"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_point_ic_degenerate_request_end_to_end(tmp_path: Path, method: str, case: str) -> None:
    """SPEC ㉚「驗證」：真實 BTCUSDT 4h 末 2,000 根之 IC 頁 `analyze`——單特徵請求、首欄為常數特徵（真實資料導出之常數）
    之請求端到端不崩潰；summary_table 含請求之全部非常數特徵且 ic_mean 有限；常數特徵或由前處理剔除（現行），或在表中則
    ic_mean 非有限（未定義）。"""
    k = _kline("BTCUSDT", "4h", 2000)
    close = k["close"]
    label = _f32(_label(close)).rename("return_1")
    causal = _causal(close)
    if case == "single_feature":
        feats = causal[["dev20"]]
    else:
        feats = pd.concat([(close > 0).astype(float).rename("const"), causal], axis=1)
    feats = _f32(feats)
    report = _analyze(tmp_path, feats, label, "4h", method)
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) - {"const"} == set(feats.columns) - {"const"}
    for c, r in rows.items():
        v = r.get("ic_mean")
        finite = v is not None and math.isfinite(float(v))
        assert finite == (c != "const"), f"{c}：ic_mean {v!r}"


# ── ㉛ ICIR 窗依週期換算 ─────────────────────────────────────────────────────────────────────────


ICIR_TF_ROWS = {"1h": 2400, "4h": 1500, "12h": 1200}


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(SCIPY))
@pytest.mark.parametrize("timeframe", sorted(ICIR_TF_ROWS))
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_icir_window_follows_timeframe_and_matches_parameter_sensitivity(timeframe: str, method: str) -> None:
    """SPEC ㉛「驗證」：1h／4h／12h 三週期（預設設定：滾動窗 21／63／126、ICIR 窗 63、參考 12h）——`compute_icir` 選中之窗
    ＝換算後 ICIR 窗（1h 756、4h 189、12h 63），ic_mean／ic_std／ICIR／勝率 == 以本檔滾動參考實作於該窗之 oracle；
    參數敏感度（⑬⑳：`ParameterSensitivityAnalyzer` 以 IC 頁之調整後 ICIR 窗，ic_filter_orchestrator.py `_run_parameter_sensitivity`）
    之 ICIR 同窗同值（相對誤差 ≤ 1e-12）。真實 BTCUSDT 各週期末若干根之因果特徵三欄。"""
    cfg = ICConfig().ic_calculation
    assert list(cfg.rolling_windows) == DEFAULT_WINDOWS and cfg.icir.window == DEFAULT_ICIR_WINDOW
    eng = ICEngine(cfg.model_dump())
    assert eng.set_timeframe(timeframe, reference_tf=cfg.icir.reference_tf) == "applied"
    w_star = _adjusted(DEFAULT_ICIR_WINDOW, timeframe)
    k = _kline("BTCUSDT", timeframe, ICIR_TF_ROWS[timeframe])
    close = k["close"]
    F = _causal(close).iloc[20:]
    y = _label(close).reindex(F.index)
    rolling = eng.compute_rolling_ic(F, y, list(cfg.rolling_windows), 1, method)
    icir = eng.compute_icir(rolling)
    exp_series = _oracle_rolling(F, y, w_star, method)
    for c in F.columns:
        assert len(exp_series[c]) > 1, "前提：換算後 ICIR 窗須有窗終點"
        exp = _icir_oracle(exp_series[c])
        for key in ("ic_mean", "ic_std", "icir", "ic_hit_rate"):
            assert _rel(float(icir[c][key]), exp[key]) <= REL_TOL, f"{timeframe}/{method}/{c}/{key}：{icir[c][key]} vs {exp[key]}"
    # 參數敏感度之 ICIR 窗＝IC 頁之調整後 ICIR 窗（同 orchestrator 之換算式）
    ps_window = eng._adjust_rolling_windows([int(cfg.icir.window)])[0]
    assert ps_window == w_star
    psa = ParameterSensitivityAnalyzer({"icir_window": int(ps_window)})
    ps_icir = psa._compute_rolling_icir(F, y, method, int(ps_window))
    for c in F.columns:
        assert _rel(float(ps_icir[c]), float(icir[c]["icir"])) <= REL_TOL, f"{timeframe}/{method}/{c}：參數敏感度 {ps_icir[c]} vs IC 頁 {icir[c]['icir']}"
    sel = eng.icir_window_selection(list(cfg.rolling_windows))
    assert sel["adjusted_window"] == w_star and sel["source"] == "rolling_windows"


@pytest.mark.requires_kline
@pytest.mark.parametrize("method", sorted(SCIPY))
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_icir_window_outside_rolling_windows_is_computed(method: str) -> None:
    """SPEC ㉛「修正」：換算後之 ICIR 窗不在滾動窗集合（4h：滾動窗 21／126 ⇒ 63／378，ICIR 窗 63 ⇒ 189）⇒ 另算該窗之滾動
    IC（輸出含 window_189 且逐窗 == oracle），ICIR 取該窗（不退回第一個窗）；選窗結果揭露為 extra_window。真實 BTCUSDT 4h。"""
    eng = ICEngine({"rolling_windows": [21, 126], "icir": {"window": 63, "reference_tf": "12h"}})
    assert eng.set_timeframe("4h", reference_tf="12h") == "applied"
    k = _kline("BTCUSDT", "4h", 1200)
    close = k["close"]
    F = _causal(close).iloc[20:]
    y = _label(close).reindex(F.index)
    rolling = eng.compute_rolling_ic(F, y, [21, 126], 1, method)
    for c in F.columns:
        assert set(rolling[c]) == {"window_63", "window_378", "window_189"}
    exp = _oracle_rolling(F, y, 189, method)
    _assert_rolling(rolling, exp, 189)
    icir = eng.compute_icir(rolling)
    for c in F.columns:
        assert _rel(float(icir[c]["icir"]), _icir_oracle(exp[c])["icir"]) <= REL_TOL
    sel = eng.icir_window_selection([21, 126])
    assert sel == {"configured_window": 63, "adjusted_window": 189, "key": "window_189", "source": "extra_window"}


def test_icir_missing_window_key_is_nan_not_first_window() -> None:
    """SPEC ㉛「修正」（不靜默退回）：滾動結果無 ICIR 窗之鍵 ⇒ ic_mean／ic_std／ICIR／勝率與 IC 自相關皆 NaN，不取第一個窗
    （明列邊界：ICIR 窗 99、只有 window_5）。"""
    eng = ICEngine({"icir": {"window": 99}})
    rolling = {"f": {"window_5": [0.1, 0.25, 0.3, 0.05, 0.2]}}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = eng.compute_icir(rolling)["f"]
        auto = eng.compute_ic_autocorrelation(rolling)["f"]
    for key in ("ic_mean", "ic_std", "icir", "ic_hit_rate"):
        assert math.isnan(out[key]), f"{key}：{out[key]!r}（不得退回 window_5）"
    assert math.isnan(auto)
    assert eng._select_icir_series(rolling["f"]) == []


@pytest.mark.requires_kline
@pytest.mark.usefixtures("ic_persist_redirect")
@pytest.mark.ic_persist_redirect
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_icir_window_end_to_end_4h_summary_uses_adjusted_window(tmp_path: Path) -> None:
    """SPEC ㉛ 端到端：真實 BTCUSDT 4h 末 2,000 根之 IC 頁 `analyze`（樣本外切分、預設滾動窗與 ICIR 窗）——summary_table
    之 ICIR == 以本檔滾動參考實作於測試段、換算後 ICIR 窗 189 之 oracle（改前取 window_63）。"""
    k = _kline("BTCUSDT", "4h", 2000)
    close = k["close"]
    label = _f32(_label(close)).rename("return_1")
    feats = _f32(_causal(close))
    report = _analyze(tmp_path, feats, label, "4h", "spearman")
    scope = _scope_rows(report, feats.index)
    w_star = _adjusted(DEFAULT_ICIR_WINDOW, "4h")
    exp = _oracle_rolling(feats[scope], label[scope], w_star, "spearman")
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    assert set(rows) == set(feats.columns)
    for c in feats.columns:
        e = _icir_oracle(exp[c])["icir"]
        assert math.isfinite(e), "前提：測試段須有換算後 ICIR 窗之有限滾動 IC"
        assert _rel(float(rows[c]["icir"]), e) <= REL_TOL, f"{c}：summary icir {rows[c]['icir']} vs oracle {e}"
