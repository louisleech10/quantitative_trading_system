"""ICPERF Task 0.2 v5.58 (v)（Task 0.4 ㊸ 之補；code review r69 群集 A）：跨標的模式之設定按模式生效——秒級 oracle 測試。

使用者 2026-11-01：「以前太多東西都放去殘留，我印象我有說過能做就做完，不要放殘留。」；2026-09-10：「前後端務必同步，
不能再有幽靈狀態」。

跨標的路徑（`ic_filter_orchestrator.analyze_cross_sectional`）改前固定「每截面排名後 Pearson」＝Spearman，IC 頁選 Pearson／
Kendall 時畫面與「本次設定」顯示所選方法而實際仍算 Spearman。本檔以 scipy 為獨立 oracle 驗：

1. 每截面 IC（`rolling_ic_series[*].window_cross_sectional` 與 summary 之 ic_mean／ic_std／icir）＝逐截面
   `scipy.stats.pearsonr`／`spearmanr`／`kendalltau`（τ-b）；Kendall 另以 O(n²) 直接數對之 τ-b 為第二 oracle。
2. 逐標的時間序列 IC（`cross_sectional_symbol_ic`）與 IC 衰減逐 horizon 之截面 IC（`ic_decay[*].ic_values`）同用所選方法
   （與縱向 `compute_ic_decay(…, method, …)`、分組 IC 同估計量之規則一致）。
3. 收益率類型於跨標的模式之消費點＝IC 衰減之前瞻報酬（`_xsec_placeholder_stats` → `ICEngine._compute_returns`；主 IC 之標籤
   由呼叫端給定，服務端固定為一根 K 線對數報酬）：非預設值 ⇒ 衰減值改變且等於以該定義獨立算之 oracle。
4. 縮尾、去重、單調性門檻於跨標的路徑無消費點（不做預處理、不做去重、不設門檻）：非預設值 ⇒ 報告逐鍵相同（證不適用，
   前端據此停用並標「此模式不適用」）。

mutation：方法未傳入（固定排名後 Pearson）⇒ 第 1、2 節 pearson／kendall 案紅；收益率未傳入 ⇒ 第 3 節紅；跨標的路徑日後
接入縮尾等 ⇒ 第 4 節紅（提醒前端改回可用）。

輸入為明列之 6 標的 × 48 時點面板（非線性單調變換使 Pearson ≠ Spearman、取整造成同值使 τ-b ≠ τ-a、含 NaN 與 ±inf）；真實
資料驗收另見 `test_xsec_methods_match_scipy_on_real_kline`（`data_cache/feature_klines/kline_cache.h5` 4h 全部標的）。
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(
    (REPO / "momentum" / "Analysis" / "contracts" / "ui_stage_toggles.json").read_text(encoding="utf-8")
)
LABEL = "return_1"
METHODS = ("spearman", "pearson", "kendall")
SYMBOLS = ("AAA", "BBB", "CCC", "DDD", "EEE", "FFF")
NO_SPLIT = {"ic_train_test_split": False}
DECAY = {"report": {"include_decay_analysis": True}, "ic_calculation": {"ic_decay_horizons": [1, 2, 3]}}


def _kendall_tau_b_direct(x: np.ndarray, y: np.ndarray) -> float:
    """τ-b 之定義直接數對（第二 oracle，不經 scipy）：(C − D)／√((n0 − n1)(n0 − n2))，n1／n2＝x／y 同值對數。"""
    conc = disc = tx = ty = 0
    n = len(x)
    for i, j in itertools.combinations(range(n), 2):
        dx, dy = np.sign(x[i] - x[j]), np.sign(y[i] - y[j])
        if dx == 0:
            tx += 1
        if dy == 0:
            ty += 1
        if dx != 0 and dy != 0:
            conc += int(dx == dy)
            disc += int(dx != dy)
    n0 = n * (n - 1) / 2
    den = math.sqrt((n0 - tx) * (n0 - ty))
    return (conc - disc) / den if den > 0 else math.nan


ORACLES: Dict[str, Callable[[np.ndarray, np.ndarray], float]] = {
    "spearman": lambda x, y: float(stats.spearmanr(x, y)[0]),
    "pearson": lambda x, y: float(stats.pearsonr(x, y)[0]),
    "kendall": lambda x, y: float(stats.kendalltau(x, y, variant="b")[0]),
}


def _slice_corr(x: np.ndarray, y: np.ndarray, method: str) -> Optional[float]:
    """截面（或逐標的序列）IC 之 oracle：兩側皆有限之列（SPEC ㊴：±inf 同缺值）數 ≥ 2 且兩側皆非常數 ⇒ scipy 該方法；
    否則 None（該截面不入序列，同產品）。"""
    m = np.isfinite(x) & np.isfinite(y)
    xs, ys = x[m], y[m]
    if xs.size < 2 or np.unique(xs).size < 2 or np.unique(ys).size < 2:
        return None
    value = ORACLES[method](xs, ys)
    return value if math.isfinite(value) else None


def _panel() -> pd.DataFrame:
    """6 標的 × 48 時點：`f_cube`＝`f_lin`³（單調非線性 ⇒ Spearman 同 `f_lin`、Pearson 不同）、`f_tie`＝取整（同值 ⇒ τ-b
    與 τ-a 不同）、`f_gap`＝含 NaN 與 ±inf；標籤 `return_1`；第 5 時點只剩 1 標的（截面跳過）。"""
    ts = pd.date_range("2024-03-01", periods=48, freq="4h")
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(SYMBOLS):
            if t == 5 and j > 0:
                continue
            lin = math.sin(t / 4.0 + 1.1 * j) + 0.15 * j - 0.3
            y = 0.02 * math.cos(t / 3.0 + 0.7 * j) + 0.004 * lin + 0.001 * ((t * 7 + j * 3) % 5 - 2)
            gap = math.cos(t / 2.5 + 0.9 * j)
            if (t + j) % 11 == 0:
                gap = math.nan
            if (t, j) == (9, 2):
                gap = math.inf
            if (t, j) == (17, 4):
                gap = -math.inf
            rows.append((stamp, sym, lin, lin ** 3, float(round(2.0 * lin)), gap, y))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f_lin", "f_cube", "f_tie", "f_gap", LABEL])
    return df.set_index(["timestamp", "symbol"]).sort_index()


def _close_panel(df: pd.DataFrame) -> pd.Series:
    """與 `df` 同索引之收盤（逐標的正值序列；供 IC 衰減之前瞻報酬）。"""
    vals = []
    for stamp, sym in df.index:
        t = (stamp - df.index.get_level_values(0)[0]) / pd.Timedelta("4h")
        j = SYMBOLS.index(sym)
        vals.append(100.0 * (1.0 + 0.1 * j) * math.exp(0.03 * math.sin(t / 3.0 + j) + 0.002 * t * (j - 2)))
    return pd.Series(vals, index=df.index, dtype=np.float64)


def _features(df: pd.DataFrame) -> List[str]:
    return [c for c in df.columns if c != LABEL]


def _oracle_series(df: pd.DataFrame, method: str, label: Optional[pd.Series] = None) -> Dict[str, List[float]]:
    """逐時點（排序）截面 IC 序列（只收有限值，同產品 `window_cross_sectional`）。"""
    y_all = df[LABEL] if label is None else label
    out: Dict[str, List[float]] = {f: [] for f in _features(df)}
    for stamp, g in df.groupby(level=0, sort=True):
        if len(g) < 2:
            continue
        y = y_all.loc[g.index].to_numpy(dtype=float)
        for f in out:
            v = _slice_corr(g[f].to_numpy(dtype=float), y, method)
            if v is not None:
                out[f].append(v)
    return out


def _run(df: pd.DataFrame, method: Optional[str], extra: Optional[Dict[str, Any]] = None,
         close: Optional[pd.Series] = None) -> Dict[str, Any]:
    override: Dict[str, Any] = {**NO_SPLIT, **(extra or {})}
    if method is not None:
        override["global"] = {"default_method": method}
    return create_ic_analyzer().analyze_cross_sectional(df, config_override=override, close=close)


def _stable(report: Dict[str, Any]) -> str:
    """報告之逐鍵序列化（去掉唯一之時鐘欄 `generated_at`，ic_reporter.py:344）。"""
    return json.dumps({k: v for k, v in report.items() if k != "generated_at"}, sort_keys=True, default=str)


def _assert_list_close(got: List[float], exp: List[float], where: str) -> None:
    assert len(got) == len(exp), f"{where}：長度 {len(got)} != oracle {len(exp)}"
    np.testing.assert_allclose(np.asarray(got, dtype=float), np.asarray(exp, dtype=float), rtol=1e-12, atol=1e-15,
                               err_msg=where)


# ── 前提：輸入使三方法確實不同（否則 oracle 等式無辨識力）────────────────────────────────────────────────────


def test_panel_discriminates_methods() -> None:
    df = _panel()
    ser = {m: _oracle_series(df, m) for m in METHODS}
    assert ser["spearman"]["f_cube"] == pytest.approx(ser["spearman"]["f_lin"], abs=0, rel=0), "單調變換不改秩"
    assert not np.allclose(ser["pearson"]["f_cube"], ser["spearman"]["f_cube"]), "前提失效：Pearson 與 Spearman 相同"
    assert not np.allclose(ser["kendall"]["f_lin"], ser["spearman"]["f_lin"]), "前提失效：Kendall 與 Spearman 相同"
    tau_a_differs = False
    for stamp, g in df.groupby(level=0, sort=True):
        x, y = g["f_tie"].to_numpy(float), g[LABEL].to_numpy(float)
        if len(g) >= 2 and np.unique(x).size < len(x) and np.unique(x).size >= 2:
            tau_b = ORACLES["kendall"](x, y)
            tau_a = float(stats.kendalltau(x, y, variant="c")[0])
            tau_a_differs = tau_a_differs or not math.isclose(tau_b, tau_a)
    assert tau_a_differs, "前提失效：f_tie 無同值截面使 τ-b ≠ 其他變體"


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_direct_tau_b_equals_scipy(seed: int) -> None:
    """第二 oracle 自證：直接數對之 τ-b == scipy `kendalltau(variant="b")`（含同值）。"""
    rng = np.random.default_rng(seed)
    x = np.round(rng.normal(size=9), 0)
    y = np.round(rng.normal(size=9), 1)
    assert math.isclose(_kendall_tau_b_direct(x, y), ORACLES["kendall"](x, y), rel_tol=1e-12, abs_tol=1e-15)


# ── 1. 每截面 IC 與 summary ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
def test_cross_sectional_ic_series_follows_method(method: str) -> None:
    df = _panel()
    report = _run(df, method)
    exp = _oracle_series(df, method)
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f, values in exp.items():
        _assert_list_close(report["rolling_ic_series"][f]["window_cross_sectional"], values, f"{method}/{f}/series")
        v = np.asarray(values, dtype=float)
        mean, std = float(np.mean(v)), float(np.std(v))
        assert math.isclose(rows[f]["ic_mean"], mean, rel_tol=1e-12, abs_tol=1e-15), f"{method}/{f}/ic_mean"
        assert math.isclose(rows[f]["ic_std"], std, rel_tol=1e-12, abs_tol=1e-15), f"{method}/{f}/ic_std"
        assert math.isclose(rows[f]["icir"], mean / std, rel_tol=1e-12, abs_tol=1e-15), f"{method}/{f}/icir"
    if method == "kendall":
        # 第二 oracle：直接數對之 τ-b
        direct: Dict[str, List[float]] = {f: [] for f in exp}
        for stamp, g in df.groupby(level=0, sort=True):
            if len(g) < 2:
                continue
            y = g[LABEL].to_numpy(float)
            for f in direct:
                x = g[f].to_numpy(float)
                m = np.isfinite(x) & np.isfinite(y)
                if m.sum() >= 2 and np.unique(x[m]).size >= 2 and np.unique(y[m]).size >= 2:
                    direct[f].append(_kendall_tau_b_direct(x[m], y[m]))
        for f, values in direct.items():
            _assert_list_close(report["rolling_ic_series"][f]["window_cross_sectional"], values, f"direct-tau-b/{f}")


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_default_request_is_spearman() -> None:
    """未帶方法（IC 頁預設不送）⇒ 與顯式 spearman 逐鍵相同（預設路徑不變）。"""
    df = _panel()
    assert _stable(_run(df, None)) == _stable(_run(df, "spearman"))


# ── 2. 逐標的序列 IC 與 IC 衰減同用所選方法 ─────────────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
def test_symbol_ic_matrix_follows_method(method: str) -> None:
    df = _panel()
    report = _run(df, method)
    matrix = report["cross_sectional_symbol_ic"]["matrix"]
    for sym, g in df.groupby(level=1, sort=True):
        y = g[LABEL].to_numpy(float)
        for f in _features(df):
            exp = _slice_corr(g[f].to_numpy(float), y, method)
            got = matrix[f][str(sym)]
            if exp is None:
                assert got is None, f"{method}/{f}/{sym}：oracle 無值、產品 {got!r}"
            else:
                assert got is not None and math.isclose(got, exp, rel_tol=1e-12, abs_tol=1e-15), (
                    f"{method}/{f}/{sym}：產品 {got!r} != oracle {exp!r}")


def _oracle_forward(close: pd.Series, h: int, return_type: str) -> pd.Series:
    """逐標的前瞻報酬（分析段內位置位移；label_generator.py:45-53 之定義獨立重寫）。"""
    parts = []
    for _, c in close.groupby(level=1, sort=True):
        c = c.sort_index(level=0)
        nxt = c.shift(-h)
        if return_type == "simple":
            parts.append(nxt / c - 1.0)
        elif return_type == "log":
            parts.append(np.log(nxt / c))
        elif return_type == "risk_adjusted":
            vol = c.pct_change().rolling(21).std()
            parts.append((nxt / c - 1.0) / vol.replace(0, np.nan))
        else:
            raise AssertionError(return_type)
    return pd.concat(parts).reindex(close.index)


def _oracle_decay(df: pd.DataFrame, close: pd.Series, method: str, return_type: str) -> Dict[str, List[float]]:
    out: Dict[str, List[float]] = {f: [] for f in _features(df)}
    for h in (1, 2, 3):
        fwd = _oracle_forward(close, h, return_type)
        for f in out:
            vals = []
            for stamp, g in df.groupby(level=0, sort=True):
                v = _slice_corr(g[f].to_numpy(float), fwd.loc[g.index].to_numpy(float), method)
                if v is not None:
                    vals.append(v)
            out[f].append(float(np.mean(vals)) if vals else math.nan)
    return out


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
def test_decay_ic_values_follow_method(method: str) -> None:
    df = _panel()
    close = _close_panel(df)
    report = _run(df, method, DECAY, close=close)
    exp = _oracle_decay(df, close, method, "simple")
    for f, values in exp.items():
        _assert_list_close(report["ic_decay"][f]["ic_values"], values, f"{method}/{f}/decay")


# ── 3. 收益率類型：跨標的之消費點＝IC 衰減之前瞻報酬 ────────────────────────────────────────────────────


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method,return_type", [("spearman", "risk_adjusted"), ("pearson", "log")])
def test_return_type_reaches_cross_sectional_decay(method: str, return_type: str) -> None:
    """對數報酬為簡單報酬之單調變換 ⇒ 秩方法（Spearman／Kendall）下衰減值相同、只 Pearson 會變；除以波動逐標的縮放
    ⇒ 截面秩亦變。故兩案：Spearman＋除以波動、Pearson＋對數。"""
    df = _panel()
    close = _close_panel(df)
    simple = _run(df, method, DECAY, close=close)
    other = _run(df, method, {**DECAY, "labels": {"return_type": return_type}}, close=close)
    exp = _oracle_decay(df, close, method, return_type)
    differs = False
    for f, values in exp.items():
        _assert_list_close(other["ic_decay"][f]["ic_values"], values, f"{return_type}/{f}/decay")
        differs = differs or not np.allclose(simple["ic_decay"][f]["ic_values"], values, equal_nan=True)
    assert differs, f"前提失效：{method} 下簡單報酬與 {return_type} 之衰減值全同（無辨識力）"
    # 主 IC 之標籤由呼叫端給定（本面板為 in-frame `return_1`）⇒ 收益率類型不改主 IC 序列
    for f in _features(df):
        assert simple["rolling_ic_series"][f] == other["rolling_ic_series"][f]


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_log_return_does_not_change_rank_decay() -> None:
    """ⓘ 文案依據：秩方法下對數報酬與簡單報酬之衰減值逐位相同（單調變換不改秩）。"""
    df = _panel()
    close = _close_panel(df)
    simple = _run(df, None, DECAY, close=close)
    log = _run(df, None, {**DECAY, "labels": {"return_type": "log"}}, close=close)
    for f in _features(df):
        assert simple["ic_decay"][f]["ic_values"] == log["ic_decay"][f]["ic_values"]


# ── 4. 縮尾／去重／單調性門檻：跨標的路徑無消費點 ⇒ 報告逐鍵相同 ─────────────────────────────────────────


#: 契約 `setting_keys[*].not_applicable_modes` 含 cross_sectional 之鍵與其非預設值
NOT_APPLICABLE = {
    key: spec for key, spec in CONTRACT["setting_keys"].items()
    if "cross_sectional" in (spec.get("not_applicable_modes") or [])
}


def _non_default(spec: Dict[str, Any]) -> List[Any]:
    return [not spec["default"]] if spec["kind"] == "toggle" else [v for v in spec["options"] if v != spec["default"]]


def _nested(path: List[str], value: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    cur = out
    for part in path[:-1]:
        cur = cur.setdefault(part, {})
    cur[path[-1]] = value
    return out


def test_contract_not_applicable_set_is_exactly_the_three_unconsumed_settings() -> None:
    """契約所標「跨標的不適用」＝縮尾、去重、單調性門檻（IC 方法與收益率類型於跨標的有消費點，見第 1–3 節）。"""
    assert set(NOT_APPLICABLE) == {"winsorization_method", "redundancy_method_selection", "monotonicity_test"}
    for key in ("ic_method_selection", "return_type_selection"):
        assert "cross_sectional" not in (CONTRACT["setting_keys"][key].get("not_applicable_modes") or [])


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("key,value", [(k, v) for k, s in sorted(NOT_APPLICABLE.items()) for v in _non_default(s)])
def test_not_applicable_settings_do_not_change_cross_sectional_report(key: str, value: Any) -> None:
    df = _panel()
    close = _close_panel(df)
    base = _run(df, None, DECAY, close=close)
    spec = CONTRACT["setting_keys"][key]
    extra = {**DECAY}
    for k, v in _nested(spec["path"], value).items():
        extra[k] = {**(extra.get(k) or {}), **v} if isinstance(v, dict) else v
    other = _run(df, None, extra, close=close)
    assert _stable(base) == _stable(other), (
        f"{key}={value!r} 改變了跨標的報告 ⇒ 跨標的已有消費點，契約不得再標不適用")


# ── 真實資料（requires_kline，秒級）：kline_cache.h5 4h 全部標的之截面 ───────────────────────────────────


def _real_xsec_panel(rows: int = 300) -> pd.DataFrame:
    """`data_cache/feature_klines/kline_cache.h5` 4h 全部標的末 `rows` 根：因果特徵（只用 0..t）ret1、dev20、vol20、mom10，
    標籤 `return_1`＝log(close[t+1]／close[t])（同服務 `_append_cross_sectional_labels`）。"""
    import h5py

    path = REPO / "data_cache" / "feature_klines" / "kline_cache.h5"
    if not path.is_file():
        pytest.fail(f"requires_kline: missing {path}")
    frames = []
    with h5py.File(path, "r") as fh:
        symbols = sorted(k for k in fh.keys() if not k.startswith("_") and "4h" in fh[k])
        for sym in symbols:
            data = fh[f"{sym}/4h/data"][-rows:]
            ts = data["timestamp"].astype("int64")
            idx = pd.to_datetime(ts, unit="ms" if int(ts[-1]) > 10 ** 12 else "s")
            close = pd.Series(data["close"].astype("float64"), index=idx)
            ret = close.pct_change()
            frame = pd.DataFrame({
                "ret1": ret, "dev20": close / close.rolling(20).mean() - 1.0, "vol20": ret.rolling(20).std(),
                "mom10": close / close.shift(10) - 1.0, LABEL: np.log(close.shift(-1) / close),
            })
            frame["symbol"] = sym
            frames.append(frame)
    df = pd.concat(frames).set_index("symbol", append=True).sort_index()
    df.index = df.index.set_names(["timestamp", "symbol"])
    assert df.index.get_level_values(1).nunique() >= 3, "前提失效：真實 4h 標的數 < 3（截面無辨識力）"
    return df


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("method", METHODS)
def test_xsec_methods_match_scipy_on_real_kline(method: str) -> None:
    df = _real_xsec_panel()
    report = _run(df, method)
    exp = _oracle_series(df, method)
    for f, values in exp.items():
        assert len(values) >= 200, f"{f}：有效截面 {len(values)} 過少（資料不足）"
        _assert_list_close(report["rolling_ic_series"][f]["window_cross_sectional"], values, f"real/{method}/{f}")
    if method != "spearman":
        sp = _oracle_series(df, "spearman")
        assert any(not np.allclose(sp[f], exp[f]) for f in exp), "前提失效：真實資料上方法間無差異"
