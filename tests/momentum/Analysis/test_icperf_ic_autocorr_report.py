"""ICPERF Task 0.2 v5.58 (w)（Task 0.4 ㊸ 之補；code review r69 群集 B，三家共識 Q1-(a)）：IC 一階自相關報告欄——秒級 oracle。

使用者 2026-11-01：「以前太多東西都放去殘留，我印象我有說過能做就做完，不要放殘留。」

改前第 4 段算出 `ic_autocorr`（`ICEngine.compute_ic_autocorrelation`，lag 對齊之兩段 Pearson）但無任何消費者；改後
`summary_table` 每特徵增 `ic_autocorr`（值）與 `ic_autocorr_reason`（值為 None 時之原因，封閉集合）。

定義（產品 `ic_filter_orchestrator.ic_lag1_autocorrelation`）＝statsmodels `acf(x, nlags=1, adjusted=False, fft=False,
missing="conservative")[1]`：x＝ICIR 所用之同一滾動 IC 序列（縱向）或逐截面 IC 序列（跨標的，未成立之截面記缺值），非有限值
（NaN、±inf）視為缺值；均值與分母只用有限值、乘積跳過缺值（Box–Jenkins 有偏估計）。None 之原因：
- `insufficient_samples`：有限值 < 3（2 點時此估計量代數上恆為 −0.5，無資訊）；
- `no_adjacent_pairs`：無相鄰兩點皆有限（acf 此時回 0，為缺值造成之假值）；
- `constant_series`：有限值皆相同（acf 0／0）。

驗：①短序列、常數序列、含缺值（含 ±inf）、正常四案 == statsmodels；②縱向第 4→5 段之 summary 欄 == statsmodels 於同一 ICIR
序列（明列輸入＋真實 kline）；③跨標的 summary 欄 == statsmodels 於逐截面 IC 序列（含未成立截面之缺值）；④報告契約：
`ui_stage_toggles.json` 之 `ic_autocorrelation` 自 `disclosed_keys` 移出、歸 `report_keys`（指向 summary 欄）。
mutation：欄未寫入 summary ⇒ ②③紅；改回兩段 Pearson（`np.corrcoef(x[:-1], x[1:])`）⇒ ①②③紅（正常案兩定義不同，見前提斷言）。
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import pytest
from statsmodels.tsa.stattools import acf

from momentum.Analysis import ic_filter_orchestrator as orch
from momentum.factories import create_ic_analyzer

REPO = Path(__file__).resolve().parents[3]
CONTRACT = json.loads(
    (REPO / "momentum" / "Analysis" / "contracts" / "ui_stage_toggles.json").read_text(encoding="utf-8")
)
REASONS = {"insufficient_samples", "no_adjacent_pairs", "constant_series"}


def _oracle(values: List[float]) -> Optional[float]:
    """statsmodels acf lag-1（參數同產品定義；非有限值先轉 NaN 再交 missing="conservative"）。"""
    x = np.asarray(values, dtype=float)
    x = np.where(np.isfinite(x), x, np.nan)
    return float(acf(x, nlags=1, adjusted=False, fft=False, missing="conservative")[1])


CASES: Dict[str, List[float]] = {
    "normal": [0.12, 0.08, 0.15, 0.03, -0.02, 0.05, 0.11, 0.09, -0.04, 0.01, 0.07, 0.13],
    "with_missing": [0.12, math.nan, 0.15, 0.03, math.inf, 0.05, 0.11, -math.inf, -0.04, 0.01, math.nan, 0.13],
    "short_three": [0.1, -0.2, 0.05],
}


@pytest.mark.parametrize("case", sorted(CASES))
def test_lag1_autocorr_matches_statsmodels(case: str) -> None:
    got, reason = orch.ic_lag1_autocorrelation(CASES[case])
    exp = _oracle(CASES[case])
    assert reason is None and got is not None
    assert math.isclose(got, exp, rel_tol=1e-12, abs_tol=1e-15), f"{case}：產品 {got!r} != statsmodels {exp!r}"


def test_two_segment_pearson_differs_on_normal_case() -> None:
    """前提：正常案之 acf 與兩段 Pearson（改前 `compute_ic_autocorrelation` 之 np.corrcoef）不同 ⇒ 上列等式有辨識力。"""
    x = np.asarray(CASES["normal"])
    assert not math.isclose(float(np.corrcoef(x[:-1], x[1:])[0, 1]), _oracle(CASES["normal"]), rel_tol=1e-6)


@pytest.mark.parametrize(
    "values,reason",
    [
        ([], "insufficient_samples"),
        ([0.1], "insufficient_samples"),
        ([0.1, -0.3], "insufficient_samples"),
        ([0.1, math.nan, -0.3, math.inf], "insufficient_samples"),
        ([0.1, math.nan, 0.2, math.nan, -0.3], "no_adjacent_pairs"),
        ([0.07, 0.07, 0.07, 0.07], "constant_series"),
        ([0.07, math.nan, 0.07, 0.07, -math.inf, 0.07], "constant_series"),
    ],
)
def test_lag1_autocorr_none_cases(values: List[float], reason: str) -> None:
    got, why = orch.ic_lag1_autocorrelation(values)
    assert got is None and why == reason
    assert set(orch.IC_AUTOCORR_REASONS) == REASONS


def test_two_point_series_is_degenerate_in_statsmodels() -> None:
    """`insufficient_samples` 門檻（有限值 < 3）之依據：2 點時 statsmodels 估計量恆為 −0.5（與資料無關）。"""
    for pair in ([0.1, -0.3], [5.0, 7.0], [-1.0, 2.5]):
        assert math.isclose(_oracle(pair), -0.5, rel_tol=1e-12)


def test_no_adjacent_pairs_is_zero_artifact_in_statsmodels() -> None:
    """`no_adjacent_pairs` 之依據：無相鄰有限對時 statsmodels 回 0（缺值造成，非資料之自相關）。"""
    assert _oracle([0.1, math.nan, 0.2, math.nan, -0.3]) == 0.0


# ── 縱向：第 4 段 → 第 5 段 summary_table ─────────────────────────────────────────────────────────────────


def _icir_series(analyzer: Any, ic_results: Dict[str, Any], feature: str) -> List[float]:
    key = f"window_{analyzer._ic_engine._adjusted_icir_window()}"
    return list(ic_results["rolling_ic"][feature][key])


def _longitudinal_summary(features: pd.DataFrame, label: pd.Series, override: Dict[str, Any]) -> Any:
    analyzer = create_ic_analyzer(override)
    cfg = analyzer._apply_tier_config(analyzer._apply_config_override(override))
    ic_results = analyzer._stage4_ic_calculation(features, label, {}, cfg, None)
    stage5 = analyzer._stage5_statistical_validation(features, label, ic_results, cfg, {},
                                                     metadata={"symbol": "BTCUSDT"})
    return analyzer, ic_results, {r["feature_name"]: r for r in stage5["summary_table"]}


def _assert_rows_match(analyzer: Any, ic_results: Dict[str, Any], rows: Dict[str, Any]) -> int:
    n_valued = 0
    for f, row in rows.items():
        series = _icir_series(analyzer, ic_results, f)
        exp_val, exp_reason = orch.ic_lag1_autocorrelation(series)
        assert row["ic_autocorr_reason"] == exp_reason, f"{f}：reason {row['ic_autocorr_reason']!r} != {exp_reason!r}"
        if exp_reason is None:
            n_valued += 1
            exp = _oracle(series)
            assert math.isclose(row["ic_autocorr"], exp, rel_tol=1e-12, abs_tol=1e-15), (
                f"{f}：summary {row['ic_autocorr']!r} != statsmodels {exp!r}")
        else:
            assert row["ic_autocorr"] is None
    return n_valued


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_longitudinal_summary_column_matches_statsmodels() -> None:
    """明列輸入（400 根、3 欄；f_const 常數 ⇒ 滾動 IC 全缺 ⇒ insufficient_samples）：summary 欄 == statsmodels 於 ICIR 序列。"""
    n = 400
    idx = pd.date_range("2024-01-01", periods=n, freq="4h")
    t = np.arange(n, dtype=float)
    y = 0.01 * np.sin(t / 7.0) + 0.004 * np.cos(t / 3.1)
    features = pd.DataFrame({
        "f_sin": np.sin(t / 7.0 + 0.3) + 0.2 * np.cos(t / 2.3),
        "f_mix": np.cos(t / 5.0) * np.sin(t / 11.0),
        "f_const": np.full(n, 1.5),
    }, index=idx)
    label = pd.Series(np.roll(y, -1), index=idx, name="return_1")
    label.iloc[-1] = np.nan
    analyzer, ic_results, rows = _longitudinal_summary(features, label, {"ic_calculation": {"rolling_windows": [21]}})
    assert _assert_rows_match(analyzer, ic_results, rows) == 2
    assert rows["f_const"]["ic_autocorr_reason"] == "insufficient_samples"


@pytest.mark.requires_kline
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_longitudinal_summary_column_matches_statsmodels_on_real_kline(requires_kline_data: Any) -> None:
    """真實 BTCUSDT 4h 末 1,500 根：因果特徵四欄、簡單報酬 h＝1；IC 頁預設之滾動窗。"""
    kl = requires_kline_data("BTCUSDT", "4h", min_rows=1500).tail(1500)
    close = kl["close"].astype("float64")
    if "timestamp" in kl.columns:
        ts = kl["timestamp"].astype("int64")
        close.index = pd.to_datetime(ts, unit="ms" if int(ts.iloc[-1]) > 10 ** 12 else "s")
    ret = close.pct_change()
    features = pd.DataFrame({"ret1": ret, "dev20": close / close.rolling(20).mean() - 1.0,
                             "vol20": ret.rolling(20).std(), "mom10": close / close.shift(10) - 1.0})
    label = (close.shift(-1) / close - 1.0).rename("return_1")
    analyzer, ic_results, rows = _longitudinal_summary(features, label, {})
    assert _assert_rows_match(analyzer, ic_results, rows) == 4, "真實資料四欄皆應有值（資料不足則前提失效）"


# ── 跨標的：逐截面 IC 序列 ────────────────────────────────────────────────────────────────────────────────


def _xsec_panel() -> pd.DataFrame:
    """5 標的 × 50 時點；f_a 連續、f_b 於 t % 7 == 0 截面常數（該截面 IC 未成立 ⇒ 序列缺值）；第 4 時點只剩 1 標的。"""
    ts = pd.date_range("2024-03-01", periods=50, freq="4h")
    rows = []
    for t, stamp in enumerate(ts):
        for j, sym in enumerate(("AAA", "BBB", "CCC", "DDD", "EEE")):
            if t == 4 and j > 0:
                continue
            a = math.sin(t / 4.0 + 1.1 * j) + 0.1 * j
            b = 0.3 if t % 7 == 0 else math.cos(t / 3.0 + 0.8 * j)
            y = 0.02 * math.cos(t / 3.0 + 0.7 * j) + 0.003 * a
            rows.append((stamp, sym, a, b, y))
    df = pd.DataFrame(rows, columns=["timestamp", "symbol", "f_a", "f_b", "return_1"])
    return df.set_index(["timestamp", "symbol"]).sort_index()


def _xsec_full_series(df: pd.DataFrame, feature: str) -> List[float]:
    """逐時點（排序）截面 Spearman；未成立之截面（列 < 2、有限對 < 2、一側常數）記 NaN（保留時間間隔）。"""
    from scipy.stats import spearmanr

    out: List[float] = []
    for _, g in df.groupby(level=0, sort=True):
        x, y = g[feature].to_numpy(float), g["return_1"].to_numpy(float)
        m = np.isfinite(x) & np.isfinite(y)
        if m.sum() < 2 or np.unique(x[m]).size < 2 or np.unique(y[m]).size < 2:
            out.append(math.nan)
        else:
            out.append(float(spearmanr(x[m], y[m])[0]))
    return out


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_cross_sectional_summary_column_matches_statsmodels() -> None:
    df = _xsec_panel()
    report = create_ic_analyzer().analyze_cross_sectional(df, config_override={"ic_train_test_split": False})
    rows = {r["feature_name"]: r for r in report["summary_table"]}
    for f in ("f_a", "f_b"):
        full = _xsec_full_series(df, f)
        exp = _oracle(full)
        assert rows[f]["ic_autocorr_reason"] is None
        assert math.isclose(rows[f]["ic_autocorr"], exp, rel_tol=1e-12, abs_tol=1e-15), f"{f}"
    # 前提：f_b 之缺值截面確實存在，且「丟掉缺值後接起來」與保留缺值之估計不同（缺值處理有辨識力）
    full_b = _xsec_full_series(df, "f_b")
    assert sum(1 for v in full_b if math.isnan(v)) >= 5
    compact = [v for v in full_b if not math.isnan(v)]
    assert not math.isclose(_oracle(compact), _oracle(full_b), rel_tol=1e-9)


# ── 報告契約 ──────────────────────────────────────────────────────────────────────────────────────────────


def test_contract_moves_ic_autocorrelation_to_report_keys() -> None:
    assert "ic_autocorrelation" not in CONTRACT["disclosed_keys"]
    spec = CONTRACT["report_keys"]["ic_autocorrelation"]
    assert spec["summary_columns"] == ["ic_autocorr", "ic_autocorr_reason"]
    assert set(spec["reasons"]) == REASONS == set(orch.IC_AUTOCORR_REASONS)
