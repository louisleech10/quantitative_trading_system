"""ICPERF Task 0.4 ㊺ B：趨勢推論接線（SPEC v5.78 ㊺ 列驗證 B①⑤⑦⑧之接線部分）。

b2b 已施工（施工前之 xfail 標記已移除）。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis import trend_inference as ti


def test_b1_rolling_window_positions_on_label_axis_with_gap() -> None:
    from momentum.Analysis.ic_engine import ICEngine

    idx = pd.RangeIndex(10)
    label = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5, np.nan, 0.6, 0.7, 0.8, 0.9], index=idx)
    pos = ICEngine.rolling_window_positions(label, windows=[3], stride=1)
    assert pos["window_3"]["start"].tolist() == [0, 1, 2, 3, 4, 6, 7]
    assert pos["window_3"]["end"].tolist() == [2, 3, 4, 6, 7, 8, 9]


def test_b4_trend_result_carries_inference_keys_and_closed_status() -> None:
    from momentum.Analysis.trend_analyzer import TrendAnalyzer

    y = pd.Series(np.random.default_rng(1).standard_normal(120))
    start = np.arange(120)
    end = start + 4
    res = TrendAnalyzer({"min_samples": 20}).analyze_trend(y, "f", support=(start, end))
    for key in ("inference_slope", "inference_se", "p_value", "inference_method", "inference_status",
                "p_abs_error", "subsample_points", "subsample_start_pos", "omitted_tail_rows",
                "interior_gap_count"):
        assert key in res
    assert res["inference_method"] == ti.INFERENCE_METHOD
    assert res["inference_status"] in ti.INFERENCE_STATUS_VALUES


def test_b7_combined_signal_insufficient_info_not_normal() -> None:
    from momentum.Analysis.trend_analyzer import TrendAnalyzer

    an = TrendAnalyzer({})
    out = an._combine_signal({"trend": "down"}, {"trend": "indeterminate", "inference_status": "insufficient_points"}, None)
    assert out["recommendation"] == "資訊不足"
    assert "正常" not in out["recommendation"] and "訊號穩定" not in out["reason"]
    assert "IC 下降" in out["reason"]


def test_b4b_constant_series_classified_by_inference_status() -> None:
    """r106 CODEX-P1-01：描述全同之序列依推論狀態分類——選取點 < 3（insufficient_points）⇒ indeterminate、
    combined_signal「資訊不足」；選取點 ≥ 3（constant_series）⇒ flat；含 NaN 之常數同規則。"""
    from momentum.Analysis.trend_analyzer import TrendAnalyzer

    an = TrendAnalyzer({"min_samples": 20})
    short = an.analyze_trend(pd.Series(np.ones(20)), overlap_window=100)
    assert short["inference_status"] == ti.STATUS_INSUFFICIENT_POINTS and short["trend"] == "indeterminate"
    assert an._combine_signal(short, short, None)["recommendation"] == "資訊不足"
    ok = an.analyze_trend(pd.Series(np.ones(30)), overlap_window=10)
    assert ok["inference_status"] == ti.STATUS_CONSTANT_SERIES and ok["trend"] == "flat"
    y = np.ones(30)
    y[[3, 17]] = np.nan
    nan_const = an.analyze_trend(pd.Series(y), overlap_window=10)
    assert nan_const["trend"] == ("flat" if nan_const["inference_status"] == ti.STATUS_CONSTANT_SERIES
                                  else "indeterminate")


def test_b7b_ls_spread_selects_among_held_points_only() -> None:
    """r106 CODEX-P1-03（SPEC ㊺ B(7) 非持倉點不入設計）：ls_spread 非持倉為 NaN、持倉點相隔 2 根而 h＝2 ⇒ 全部 40 個持倉點
    互不重疊、皆入選（非持倉 NaN 不佔支撐）；兩特徵持倉相位不同各自選取；IC 維（共用位置軸）不受影響。"""
    from momentum.Analysis.trend_analyzer import TrendAnalyzer, TrendDimensionInput

    rng = np.random.default_rng(42)
    a = np.full(80, np.nan)
    a[1::2] = rng.normal(size=40)
    b = np.full(80, np.nan)
    b[0::2] = rng.normal(size=40)
    out = TrendAnalyzer({"min_samples": 20}).batch_analyze(
        pd.DataFrame({"fa": np.zeros(80), "fb": np.zeros(80)}), dimensions=["ls_spread"],
        dimension_inputs={"ls_spread": TrendDimensionInput(series={"fa": pd.Series(a), "fb": pd.Series(b)},
                                                           overlap_window=2, select_finite_only=True)})
    for name, first in (("fa", 1), ("fb", 0)):
        r = out[name]["ls_spread_trend"]
        assert r["subsample_points"] == 40 and r["subsample_start_pos"] == first, (name, r)
        assert r["interior_gap_count"] == 0
    # r107 CODEX-P1-01：既有 analyze_multi_dimension 入口同規則
    multi = TrendAnalyzer({"min_samples": 20}).analyze_multi_dimension(
        "fa", ls_spread_series=pd.Series(a), ls_spread_overlap_window=2)["fa"]["ls_spread_trend"]
    assert multi["subsample_points"] == 40 and multi["subsample_start_pos"] == 1 and multi["interior_gap_count"] == 0


def _deep_helpers():
    """共用 test_icperf_deep_centrality_trend.py 之真實資料載入、產品 orchestrator 與獨立 oracle（同一定義，不另寫）。"""
    import importlib.util
    import sys
    from pathlib import Path

    name = "icperf_deep_ct_helpers"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, Path(__file__).with_name("test_icperf_deep_centrality_trend.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return sys.modules[name]


@pytest.mark.requires_kline
@pytest.mark.parametrize("rows,split_applied", [(2600, False), (8000, True)])
def test_b1b_analyze_caches_rolling_positions_matching_independent_axis(tmp_path, monkeypatch, rows: int,
                                                                         split_applied: bool) -> None:
    """㊺ B(1) 產品接線：真實 BTCUSDT 1h 經 `analyze` 後 `_ic_cache["rolling_ic_positions"]` 存在，且每窗〔首, 末〕＝由
    「切分允許列（train∪test）上之標籤有限列」與「整窗落於測試段」獨立導出之原列位置，長度＝該窗滾動 IC 序列長；
    `_ic_trend_support` 因此不為 None（防快取漏帶使趨勢退回以窗長推算）。兩分支：2,600 根（測試段不足滾動暖機 ⇒ 全樣本退回、
    無遮罩）、8,000 根（預設切分成立 ⇒ 只留整窗落於測試段之窗）。"""
    import json

    from momentum.Analysis.ic_config_schema import load_ic_config
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    helpers = _orchestrator_test_helpers()
    deep = _deep_helpers()
    k = deep._load_kline("BTCUSDT", rows)
    feats = deep._real_features(k).iloc[:, :3]
    label = np.log(k["close"].shift(-1) / k["close"])
    ok = np.isfinite(feats.to_numpy()).all(axis=1)
    feats, label = feats[ok], label[ok]
    ts = pd.Index(feats.index.asi8 // 10**9, name="timestamp")
    feats = feats.set_axis(ts).astype("float64")
    helpers._write_features_h5(tmp_path / "f.h5", feats)
    helpers._write_labels_h5(tmp_path / "l.h5", pd.DataFrame({"return_1": label.to_numpy()}, index=ts))
    meta = {c: {"name": c, "category": "trend", "layer": 1, "data_source": "close"} for c in feats.columns}
    meta.update({"symbol": "BTCUSDT", "timeframe": "1h", "case_id": "BTCUSDT_1h"})
    (tmp_path / "m.json").write_text(json.dumps(meta), encoding="utf-8")

    orc = ICFilterOrchestrator(load_ic_config())
    monkeypatch.setattr(orc, "_persist_outputs", lambda *a, **kw: {})
    orc.analyze(features_path=str(tmp_path / "f.h5"), labels_path=str(tmp_path / "l.h5"),
                meta_path=str(tmp_path / "m.json"))
    cache = orc._ic_cache
    positions = cache.get("rolling_ic_positions")
    assert positions, "rolling_ic_positions 未進 _ic_cache"
    rolling = cache["rolling_ic"]
    first = next(n for n, v in rolling.items() if isinstance(v, dict) and v)
    sc = cache["split_context"]
    assert (sc is not None) == split_applied, "前提失效：切分分支與預期不符（資料列數）"
    n_rows = len(cache["features_df"])
    train = np.asarray(sc["train_mask"], dtype=bool) if sc else np.zeros(n_rows, dtype=bool)
    test = np.asarray(sc["test_mask"], dtype=bool) if sc else np.ones(n_rows, dtype=bool)
    allowed = train | test
    lab = cache["label_series"].reindex(cache["features_df"].index).to_numpy(dtype=float)[allowed]
    axis = np.flatnonzero(np.isfinite(lab))
    in_test = test[allowed][axis]
    stride = int(orc._config.ic_calculation.rolling_stride or 1)
    for key, series in rolling[first].items():
        w = int(key.split("_")[1])
        ends = np.arange(w, axis.size + 1, stride)
        keep = [e for e in ends if in_test[e - 1] and in_test[e - w]]
        exp_start = np.asarray([axis[e - w] for e in keep])
        exp_end = np.asarray([axis[e - 1] for e in keep])
        start, end = positions[key]
        assert len(start) == len(series), key
        np.testing.assert_array_equal(start, exp_start, err_msg=key)
        np.testing.assert_array_equal(end, exp_end, err_msg=key)
    assert orc._ic_trend_support(rolling, list(rolling), orc._apply_tier_config(orc._apply_config_override(None))) \
        is not None


def _orchestrator_test_helpers():
    """共用 tests/momentum/test_ic_filter_orchestrator.py 之 HDF5 寫檔輔助（同一格式，不另寫）。"""
    import importlib.util
    import sys
    from pathlib import Path

    name = "icperf_orc_io_helpers"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            name, Path(__file__).resolve().parents[1] / "test_ic_filter_orchestrator.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return sys.modules[name]


@pytest.mark.slow
@pytest.mark.requires_kline
def test_b5_real_kline_four_dimensions_match_independent_recompute() -> None:
    """真實 BTCUSDT 1h、h＝3（標籤＝3 根前瞻簡單報酬）、中段標籤缺口 60 根（標籤有限列軸跳號 ⇒ 位置支撐 ≠ 以窗長推算）：
    產品走位置快取（`ICEngine.rolling_window_positions`），經 `run_deep_analysis` 四維；oracle 由標籤有限列獨立推 IC 支撐
    〔L[k], L[k+W−1]＋h−1〕、中心性二層支撐、因子報酬〔j·h, j·h＋h−1〕、多空〔t, t＋h−1〕，以密集式 Bartlett＋特徵分解
    Imhof 重算——四維逐欄一致（含資料不足警示）；㉔ 逐特徵中心性趨勢與 centrality 維一致；每維皆有有限推論斜率。"""
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.ic_engine import ICEngine

    deep = _deep_helpers()
    h = 3
    k = deep._load_kline("BTCUSDT", deep.REAL_ROWS)
    feats = deep._real_features(k)
    label = (k["close"].shift(-h) / k["close"] - 1.0).rename("label")
    ok = np.isfinite(feats.to_numpy()).all(axis=1) & np.isfinite(label.to_numpy())
    feats, label = feats[ok], label[ok].copy()
    label.iloc[900:960] = np.nan
    names = list(feats.columns)
    rolling = ICEngine({"timeframe": "1h"}).compute_rolling_ic(feats, label, [21, 63, 126], 1, "spearman")
    windows = sorted(int(key.split("_")[1]) for key in rolling[names[0]])
    pos = ICEngine.rolling_window_positions(label, windows, 1)

    orc = deep._deep_orchestrator(feats, label, rolling, h)
    orc._ic_cache["rolling_ic_positions"] = {key: (v["start"], v["end"]) for key, v in pos.items()}
    rep = orc.run_deep_analysis(selected_features=names, force_modules=deep._FOUR)
    prod = rep.results["trend_analysis"]

    # oracle：IC 維所用窗鍵＝最長序列者（同 ref_ic_matrix）；支撐由標籤有限列直接推
    best = max(rolling[names[0]], key=lambda key: len(rolling[names[0]][key]))
    w = int(best.split("_")[1])
    axis = np.flatnonzero(np.isfinite(label.to_numpy()))
    n_vals = len(rolling[names[0]][best])
    assert axis.size - w + 1 == n_vals, (axis.size, w, n_vals)
    starts = axis[:n_vals]
    ends = axis[w - 1: w - 1 + n_vals] + h - 1
    assert np.any(ends - starts != w - 1 + h - 1), "前提失效：缺口未使位置支撐不同於以窗長推算"
    cfg = ICConfig()
    sources = deep._ref_trend_sources(rep, rolling, names, cfg, h, ic_support=(starts, ends))
    res = deep.compare_trend_analysis(prod, rolling, names, cfg.trend_analysis.model_dump(), sources=sources,
                                      ic_support=(starts, ends))
    deep._assert_all_consistent(res)
    deep._assert_feature_trend_matches_centrality_dim(rep)
    for dim in deep.TREND_DIMS:
        slopes = [v[f"{dim}_trend"]["inference_slope"] for v in prod.values() if f"{dim}_trend" in v]
        assert any(s is not None and np.isfinite(s) for s in slopes), (dim, slopes)
