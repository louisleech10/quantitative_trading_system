"""1c-FR-FULL F0: FactorReturnAnalyzer PIT 分位 + 序列 artifact + mutation 可證偽.

SPEC/TODO: docs/IC1CFR_FULL_{SPEC,TODO}.md §G / §V-matrix / F0.1+F0.2.
7-bar synthetic 僅代數 reference;正確性 oracle 另用 real-kline(M-winsorize).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.factor_return_analyzer import (
    INDEX_POLICY_FRAME_DROPNA,
    FactorTimingReturnSeries,
)
from momentum.Analysis.ic_reporter import ICReporter
from momentum.factories import create_factor_return_analyzer


# ---------------------------------------------------------------------------
# 獨立 numpy/pandas reference(不經 analyzer 碼路)——§G 7-bar
# ---------------------------------------------------------------------------

FEATURE_7 = [20.0, 40.0, 10.0, 55.0, 30.0, 5.0, 50.0]
FUTURE_7 = [0.02, -0.01, 0.03, -0.02, 0.04, -0.03, 0.05]
EXPECTED_POSITION_7 = [0, 0, -1, 1, 0, -1, 1]
EXPECTED_LS_7 = [0.0, 0.0, -0.03, -0.02, 0.0, 0.03, 0.05]
EXPECTED_MEAN_7 = 0.004285714285714286
EXPECTED_ACTIVE_7 = 4
EXPECTED_CUM_LAST_7 = 0.028073900
ATOL = 1e-12

KLINE_PATH = Path("data_cache/feature_klines/kline_cache.h5")
REAL_SYMBOL = "ETHUSDT"
REAL_TF = "12h"


def _ref_pit_position(
    feature: pd.Series,
    *,
    num_quantiles: int,
    warmup_periods: int,
) -> pd.Series:
    """獨立 reference: §C PIT expanding membership."""
    position = pd.Series(0, index=feature.index, dtype=int)
    for t in range(len(feature)):
        if t < warmup_periods:
            continue
        window = feature.iloc[: t + 1]
        q_eff = min(int(num_quantiles), int(window.nunique()))
        if q_eff < 2:
            continue
        try:
            labels = pd.qcut(window, q_eff, labels=False, duplicates="drop")
        except ValueError:
            continue
        label_t = labels.iloc[-1]
        if pd.isna(label_t):
            continue
        label_i = int(label_t)
        if label_i == q_eff - 1:
            position.iloc[t] = 1
        elif label_i == 0:
            position.iloc[t] = -1
    return position


def _ref_series(
    feature: pd.Series,
    future_return: pd.Series,
    *,
    num_quantiles: int = 3,
    warmup_periods: int = 2,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    frame = pd.concat(
        [feature.rename("feature"), future_return.rename("y")], axis=1
    ).dropna()
    pos = _ref_pit_position(
        frame["feature"].astype(float),
        num_quantiles=num_quantiles,
        warmup_periods=warmup_periods,
    )
    ls = (pos * frame["y"].astype(float)).astype(float)
    cum = (1.0 + ls).cumprod() - 1.0
    return pos, ls, cum


def _make_test_analyzer(**overrides: Any):
    """經 factory 建 analyzer(Rule 3;不直建 FactorReturnAnalyzer)。"""
    cfg = {
        "min_samples": 2,
        "warmup_periods": 2,
        "num_quantiles": 3,
        "risk_free_rate": 0.0,
    }
    cfg.update(overrides)
    return create_factor_return_analyzer(cfg)


def _series_hash(s: pd.Series) -> str:
    arr = np.ascontiguousarray(s.to_numpy(dtype=np.float64))
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _load_ethusdt_12h(n: int = 256) -> tuple[pd.Series, pd.Series]:
    """真 kline ETHUSDT/12h → feature=close 相對變化 proxy, future simple return."""
    if not KLINE_PATH.exists():
        pytest.fail(f"real kline missing: {KLINE_PATH}")
    with h5py.File(KLINE_PATH, "r") as f:
        key = f"{REAL_SYMBOL}/{REAL_TF}/data"
        if key not in f:
            pytest.fail(f"dataset missing: {key}")
        data = f[key][:]
    ts = pd.to_datetime(data["timestamp"], unit="ms", utc=True)
    close = pd.Series(data["close"].astype(np.float64), index=ts, name="close")
    close = close.sort_index().iloc[-n:]
    # feature: 過去 1 期 log-return(PIT-safe); label: 未來 1 期 simple return
    feature = np.log(close).diff().rename("feat_close_lr1")
    future = (close.shift(-1) / close - 1.0).rename("future_return")
    return feature, future


# ---------------------------------------------------------------------------
# Golden / schema / index
# ---------------------------------------------------------------------------


def test_golden_7bar() -> None:
    """§G 7-bar hand-calc: position/ls/cum/mean/active vs 獨立 reference."""
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, name="f1", dtype=float)
    future = pd.Series(FUTURE_7, index=idx, name="y", dtype=float)

    ref_pos, ref_ls, ref_cum = _ref_series(
        feature, future, num_quantiles=3, warmup_periods=2
    )
    assert ref_pos.tolist() == EXPECTED_POSITION_7
    assert all(abs(a - b) <= ATOL for a, b in zip(ref_ls.tolist(), EXPECTED_LS_7))
    assert abs(float(ref_ls.mean()) - EXPECTED_MEAN_7) <= ATOL
    assert abs(float(ref_cum.iloc[-1]) - EXPECTED_CUM_LAST_7) <= 1e-9

    analyzer = _make_test_analyzer()
    result = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    assert not hasattr(result, "reason") or not isinstance(result, type(None))
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(result, SkippedResult), getattr(result, "reason", result)
    assert isinstance(result, dict)

    smap = analyzer.get_series_map()
    assert "f1" in smap
    art = smap["f1"]
    assert isinstance(art, FactorTimingReturnSeries)
    assert art.position.tolist() == EXPECTED_POSITION_7
    assert art.index_policy == INDEX_POLICY_FRAME_DROPNA

    assert all(
        abs(float(a) - float(b)) <= ATOL
        for a, b in zip(art.ls_return.tolist(), EXPECTED_LS_7)
    )
    assert abs(float(result["long_short_mean_return"]) - EXPECTED_MEAN_7) <= ATOL
    assert int(result["active_bar_count"]) == EXPECTED_ACTIVE_7

    # ls_cumulative 經 sample 回 list;7 點全保留
    cum_sampled = result["ls_cumulative_sampled"]
    assert len(cum_sampled) == 7
    assert all(
        abs(float(a) - float(b)) <= ATOL for a, b in zip(cum_sampled, ref_cum.tolist())
    )
    assert abs(float(cum_sampled[-1]) - EXPECTED_CUM_LAST_7) <= 1e-9

    # risk_metrics 鍵名 sharpe_ratio
    assert "sharpe_ratio" in result["risk_metrics"]
    assert result["quantile_summary"].get("descriptive_full_sample") is True


def test_index_subset() -> None:
    """NaN / 時間不相交 → 輸出 index ⊆ frame.index、nan_mask exact、非等長 RangeIndex."""
    idx = pd.date_range("2024-01-01", periods=10, freq="12h")
    feature = pd.Series(
        [1.0, np.nan, 3.0, 4.0, np.nan, 6.0, 7.0, 8.0, 9.0, 10.0],
        index=idx,
        name="feat",
        dtype=float,
    )
    # future 在前半與 feature 重疊,後半 shift 造成部分 NaN 對齊
    future = pd.Series(
        [0.01, 0.02, np.nan, -0.01, 0.03, 0.0, -0.02, 0.04, np.nan, 0.01],
        index=idx,
        name="y",
        dtype=float,
    )
    # 另加不相交時間戳於 feature 尾端之外(future 沒有)——concat 後只留交集 dropna
    extra_idx = pd.date_range("2025-01-01", periods=2, freq="12h")
    feature = pd.concat(
        [feature, pd.Series([11.0, 12.0], index=extra_idx, dtype=float)]
    )
    feature.name = "feat"

    frame = pd.concat(
        [feature.rename("feature"), future.rename("y")], axis=1
    ).dropna()
    assert len(frame) >= 2

    analyzer = _make_test_analyzer(min_samples=2, warmup_periods=1, num_quantiles=3)
    result = analyzer.compute_factor_returns(feature, future, feature_name="feat")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    if isinstance(result, SkippedResult):
        # 若樣本過少或無 active edge,至少驗證 skip 非靜默崩
        assert "insufficient" in result.reason or "no active" in result.reason
        return

    art = analyzer.get_series_map()["feat"]
    assert isinstance(art.ls_return.index, pd.DatetimeIndex)
    # 輸出 index ⊆ frame.index
    assert set(art.ls_return.index).issubset(set(frame.index))
    assert set(art.position.index).issubset(set(frame.index))
    # 非「原 feature 等長 RangeIndex 廣播」
    assert not (
        isinstance(art.ls_return.index, pd.RangeIndex)
        and len(art.ls_return) == len(feature)
    )
    # nan_mask: 輸出無 NaN(已 dropna frame)
    assert art.ls_return.notna().all()
    assert art.position.notna().all()


def test_reporter_sharpe_key_aligned() -> None:
    """D9: analyzer 鍵 sharpe_ratio == reporter 讀取鍵."""
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, name="f1", dtype=float)
    future = pd.Series(FUTURE_7, index=idx, name="y", dtype=float)
    analyzer = _make_test_analyzer()
    payload = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(payload, SkippedResult)
    assert "sharpe_ratio" in payload["risk_metrics"]
    assert "sharpe" not in payload["risk_metrics"]

    # 模擬 deep_payload 為 per-feature map(reporter 在 unwrap 前/legacy 讀路徑)
    deep_payload = {"factor_returns": {"f1": payload}}
    # ICReporter 需 config;用空 dict 即可走 _build_deep_summary_columns
    reporter = ICReporter(config={})
    cols = reporter._build_deep_summary_columns("f1", deep_payload)
    sharpe_from_reporter = cols["factor_return_sharpe"]
    expected = payload["risk_metrics"]["sharpe_ratio"]
    if np.isnan(expected):
        assert sharpe_from_reporter is None or (
            isinstance(sharpe_from_reporter, float) and np.isnan(sharpe_from_reporter)
        )
    else:
        assert sharpe_from_reporter is not None
        assert abs(float(sharpe_from_reporter) - float(expected)) <= ATOL
    # 鍵名對齊: source 必須讀 sharpe_ratio(D9)
    import inspect

    src = inspect.getsource(ICReporter._build_deep_summary_columns)
    assert '"sharpe_ratio"' in src
    # 舊讀取鍵 "sharpe" 不得作為 risk_metrics 欄位名殘留
    assert 'None,\n                "sharpe",' not in src
    assert 'None, "sharpe"' not in src


def test_compute_batch_ok_union_schema() -> None:
    """F0.2: compute_batch 回 §U ok union 頂層 schema_version+warmup_periods."""
    idx = pd.RangeIndex(7)
    features = pd.DataFrame(
        {"f1": FEATURE_7, "f2": [x + 1 for x in FEATURE_7]},
        index=idx,
        dtype=float,
    )
    future = pd.Series(FUTURE_7, index=idx, dtype=float)
    analyzer = _make_test_analyzer()
    batch = analyzer.compute_batch(features, future, top_n=2)
    assert batch["status"] == "ok"
    assert batch["reason"] is None
    value = batch["value"]
    assert value["schema_version"] == "fr_full_v1"
    assert value["semantics"] == "single_asset_factor_timing_ls"
    assert value["quantile_fit"] == "pit_expanding"
    assert value["return_transform"] == "identity"
    assert value["turnover_semantics"] == "abs_delta_position_p1"
    assert value["warmup_periods"] == 2
    assert "f1" in value["features"]
    assert isinstance(analyzer.get_series_map()["f1"].ls_return, pd.Series)


# ---------------------------------------------------------------------------
# §V-matrix mutations(in-test 雙實作對照)
# ---------------------------------------------------------------------------


def _legacy_pos_subtract_ls(
    feature: pd.Series, future_return: pd.Series, num_quantiles: int = 3
) -> pd.Series:
    """M-pos 變體: full-sample qcut + reset_index iloc 位置相減(舊錯行為)."""
    data = pd.concat(
        [feature.rename("feature"), future_return.rename("future_returns")], axis=1
    ).dropna()
    bins = pd.qcut(data["feature"], q=num_quantiles, labels=False, duplicates="drop")
    returns_w = data["future_returns"].astype(float)
    low = returns_w[bins == bins.min()].reset_index(drop=True)
    high = returns_w[bins == bins.max()].reset_index(drop=True)
    paired = int(min(len(low), len(high)))
    return (high.iloc[:paired] - low.iloc[:paired]).astype(float)


def test_mutation_pos() -> None:
    """M-pos: reset_index+iloc 位置相減變體 ≠ PIT membership reference."""
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, dtype=float)
    future = pd.Series(FUTURE_7, index=idx, dtype=float)
    _, ref_ls, _ = _ref_series(feature, future)
    variant = _legacy_pos_subtract_ls(feature, future)
    # 長度/值必須可區分(抓不到回歸=FAIL)
    assert len(variant) != len(ref_ls) or not np.allclose(
        variant.to_numpy(dtype=float),
        ref_ls.to_numpy(dtype=float),
        atol=ATOL,
        equal_nan=True,
    )
    # production analyzer 對齊 reference
    analyzer = _make_test_analyzer()
    analyzer.compute_factor_returns(feature, future, feature_name="f1")
    prod_ls = analyzer.get_series_map()["f1"].ls_return
    assert np.allclose(prod_ls.to_numpy(dtype=float), ref_ls.to_numpy(dtype=float), atol=ATOL)


def _full_sample_position(
    feature: pd.Series, num_quantiles: int = 3, warmup_periods: int = 2
) -> pd.Series:
    """M-lookahead 變體: full-sample qcut 一次切完再 membership(前瞻)."""
    position = pd.Series(0, index=feature.index, dtype=int)
    q_eff = min(int(num_quantiles), int(feature.nunique()))
    if q_eff < 2:
        return position
    bins = pd.qcut(feature, q=q_eff, labels=False, duplicates="drop")
    top, bottom = q_eff - 1, 0
    for t in range(len(feature)):
        if t < warmup_periods:
            continue
        label = bins.iloc[t]
        if pd.isna(label):
            continue
        li = int(label)
        if li == top:
            position.iloc[t] = 1
        elif li == bottom:
            position.iloc[t] = -1
    return position


def test_mutation_lookahead() -> None:
    """M-lookahead: PIT≠full-sample 判別 fixture;production≡PIT 且 ≠full-sample.

    7-bar FEATURE_7 上 PIT≡full-sample,舊 tautological `or` 護網會在回歸 full-sample
    qcut 時仍綠。改用 seed=0 的 15-bar 使 `_ref_pit != _full_sample`,硬斷言。
    """
    n = 15
    warmup = 5
    nq = 5
    rng = np.random.RandomState(0)
    feature = pd.Series(rng.randn(n).astype(float), index=pd.RangeIndex(n), dtype=float)
    future = pd.Series(rng.randn(n).astype(float) * 0.01, index=feature.index, dtype=float)

    pit_full = _ref_pit_position(feature, num_quantiles=nq, warmup_periods=warmup)
    fs_full = _full_sample_position(feature, num_quantiles=nq, warmup_periods=warmup)
    # 硬判別:fixture 本身必須 PIT≠full-sample(無 tautological or fallback)
    assert pit_full.tolist() != fs_full.tolist(), (
        "fixture must distinguish PIT from full-sample; regenerate seed"
    )

    # 截掉最後 3 bar → PIT 早期不變
    early = 10
    feature_trunc = feature.iloc[:-3]
    pit_trunc = _ref_pit_position(
        feature_trunc, num_quantiles=nq, warmup_periods=warmup
    )
    assert pit_full.iloc[:early].tolist() == pit_trunc.iloc[:early].tolist()

    # production = PIT 且 ≠ full-sample(截未來不變式 + 前瞻回歸護網)
    analyzer = _make_test_analyzer(
        min_samples=5, warmup_periods=warmup, num_quantiles=nq
    )
    result = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(result, SkippedResult), getattr(result, "reason", result)
    production_position = analyzer.get_series_map()["f1"].position
    assert production_position.tolist() == pit_full.tolist()
    assert production_position.tolist() != fs_full.tolist()

    # 截未來後 production 早期仍 = PIT full 早期
    analyzer2 = _make_test_analyzer(
        min_samples=5, warmup_periods=warmup, num_quantiles=nq
    )
    fut_trunc = future.iloc[:-3]
    analyzer2.compute_factor_returns(feature_trunc, fut_trunc, feature_name="f1")
    assert (
        analyzer2.get_series_map()["f1"].position.iloc[:early].tolist()
        == pit_full.iloc[:early].tolist()
    )


def _winsorize_series(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    s = pd.Series(series, dtype=float)
    return s.clip(lower=float(s.quantile(lower)), upper=float(s.quantile(upper)))


def test_mutation_winsorize_regress() -> None:
    """M-winsorize-regress: winsorize 變體 ls_return hash ≠ raw 鎖定 hash(real-kline)."""
    feature, future = _load_ethusdt_12h(n=256)
    frame = pd.concat([feature.rename("f"), future.rename("y")], axis=1).dropna()
    assert len(frame) >= 50

    # raw identity reference(production 語意)
    pos = _ref_pit_position(
        frame["f"].astype(float), num_quantiles=5, warmup_periods=20
    )
    ls_raw = (pos * frame["y"].astype(float)).astype(float)
    # 若全 0 position,降 warmup 再試
    if int((pos != 0).sum()) == 0:
        pos = _ref_pit_position(
            frame["f"].astype(float), num_quantiles=5, warmup_periods=5
        )
        ls_raw = (pos * frame["y"].astype(float)).astype(float)
    assert int((pos != 0).sum()) > 0, "real-kline produced no active bars"

    hash_raw = _series_hash(ls_raw)
    ls_w = (pos * _winsorize_series(frame["y"].astype(float))).astype(float)
    hash_w = _series_hash(ls_w)
    assert hash_raw != hash_w, "winsorize variant must change ls_return hash on real-kline"

    # production analyzer 對齊 raw(非 winsorize);經 factory(Rule 3)
    analyzer = create_factor_return_analyzer(
        {"min_samples": 30, "warmup_periods": 20, "num_quantiles": 5}
    )
    result = analyzer.compute_factor_returns(
        frame["f"], frame["y"], feature_name="feat_close_lr1"
    )
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(result, SkippedResult), getattr(result, "reason", result)
    prod_ls = analyzer.get_series_map()["feat_close_lr1"].ls_return
    assert _series_hash(prod_ls) == hash_raw


def _mid_weighted_ls(
    feature: pd.Series,
    future_return: pd.Series,
    *,
    num_quantiles: int = 3,
    warmup_periods: int = 2,
) -> pd.Series:
    """M-mid 變體: 中間分位給非 0 權重(0.5)扭曲 mean."""
    frame = pd.concat(
        [feature.rename("feature"), future_return.rename("y")], axis=1
    ).dropna()
    position = pd.Series(0.0, index=frame.index, dtype=float)
    for t in range(len(frame)):
        if t < warmup_periods:
            continue
        window = frame["feature"].iloc[: t + 1]
        q_eff = min(int(num_quantiles), int(window.nunique()))
        if q_eff < 2:
            continue
        labels = pd.qcut(window, q_eff, labels=False, duplicates="drop")
        label_t = int(labels.iloc[-1])
        if label_t == q_eff - 1:
            position.iloc[t] = 1.0
        elif label_t == 0:
            position.iloc[t] = -1.0
        else:
            position.iloc[t] = 0.5  # 中間分位錯誤非 0
    return (position * frame["y"].astype(float)).astype(float)


def test_mutation_mid() -> None:
    """M-mid: 中間分位非 0 權重 → long_short_mean_return ≠ reference."""
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, dtype=float)
    future = pd.Series(FUTURE_7, index=idx, dtype=float)
    _, ref_ls, _ = _ref_series(feature, future)
    ref_mean = float(ref_ls.mean())
    var_ls = _mid_weighted_ls(feature, future)
    var_mean = float(var_ls.mean())
    assert abs(var_mean - ref_mean) > ATOL

    analyzer = _make_test_analyzer()
    result = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(result, SkippedResult)
    assert abs(float(result["long_short_mean_return"]) - ref_mean) <= ATOL


def test_no_full_sample_helper_name() -> None:
    """composer-14: 生產碼無 _assign_quantiles_with_fallback 殘留."""
    src = Path("momentum/Analysis/factor_return_analyzer.py").read_text(encoding="utf-8")
    assert "_assign_quantiles_with_fallback" not in src
    assert "_winsorize_series" not in src


def test_inf_rejected() -> None:
    """F0-codex-2: feature/future 含 inf → 不得進 ls/risk;明確 drop 或 INVALID_DATA."""
    idx = pd.RangeIndex(12)
    feature = pd.Series(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0],
        index=idx,
        dtype=float,
    )
    future = pd.Series(
        [0.01, 0.02, np.inf, -0.01, 0.03, 0.0, -0.02, 0.04, 0.01, -0.03, 0.02, 0.01],
        index=idx,
        dtype=float,
    )
    analyzer = _make_test_analyzer(min_samples=5, warmup_periods=2, num_quantiles=3)
    result = analyzer.compute_factor_returns(feature, future, feature_name="f_inf")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    if isinstance(result, SkippedResult):
        assert result.error_type in {"INVALID_DATA", "INSUFFICIENT_DATA"}
        assert "f_inf" not in analyzer.get_series_map()
        return

    art = analyzer.get_series_map()["f_inf"]
    assert np.isfinite(art.ls_return.to_numpy(dtype=float)).all()
    assert np.isfinite(art.position.to_numpy(dtype=float)).all()
    for k, v in result["risk_metrics"].items():
        assert v is None or (isinstance(v, (int, float)) and (np.isnan(v) or np.isfinite(v))), (
            f"risk_metrics[{k}] not finite-or-nan: {v!r}"
        )
    # 全 inf 輸入 → INVALID_DATA
    all_inf_y = pd.Series([np.inf] * 12, index=idx, dtype=float)
    skip = analyzer.compute_factor_returns(feature, all_inf_y, feature_name="f_all_inf")
    assert isinstance(skip, SkippedResult)
    assert skip.error_type == "INVALID_DATA"
    assert "f_all_inf" not in analyzer.get_series_map()

    # overflow finite-garbage: mean≈5 → (1+5)^365 仍 finite 但 abs>1e6 → nan
    huge = analyzer.compute_risk_metrics(pd.Series([5.0] * 10), periods_per_year=365)
    assert np.isnan(huge["annualized_return"])
    assert np.isnan(huge["calmar_ratio"])


def test_skipped_no_stale_series() -> None:
    """F0-codex-3: early SkippedResult 後同名 feature 不得殘留 series_map."""
    idx = pd.RangeIndex(7)
    feature = pd.Series(FEATURE_7, index=idx, name="f1", dtype=float)
    future = pd.Series(FUTURE_7, index=idx, dtype=float)
    analyzer = _make_test_analyzer()
    ok = analyzer.compute_factor_returns(feature, future, feature_name="f1")
    from momentum.Analysis.deep_analysis_types import SkippedResult

    assert not isinstance(ok, SkippedResult)
    assert "f1" in analyzer.get_series_map()

    # 同名 constant → skip,series_map 必須清掉
    const = pd.Series([1.0] * 7, index=idx, dtype=float)
    skip = analyzer.compute_factor_returns(const, future, feature_name="f1")
    assert isinstance(skip, SkippedResult)
    assert "f1" not in analyzer.get_series_map()

    # 再 skip insufficient,亦不得寫入
    short_f = pd.Series([1.0, 2.0], index=pd.RangeIndex(2), dtype=float)
    short_y = pd.Series([0.01, 0.02], index=pd.RangeIndex(2), dtype=float)
    skip2 = analyzer.compute_factor_returns(short_f, short_y, feature_name="f_short")
    assert isinstance(skip2, SkippedResult)
    assert "f_short" not in analyzer.get_series_map()


# ---------------------------------------------------------------------------
# F1.1 / F1.2 — orchestrator series owner + tier truth table
# ---------------------------------------------------------------------------


def _build_orch_for_f1(*, preset: str = "intermediate"):
    """最小 orchestrator fixture（有 ic_cache；不跑全 pipeline）。"""
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    raw = ICConfig().model_dump(by_alias=True)
    raw["feature_tiers"]["active_preset"] = preset
    # test-config：降 min_samples/warmup 以小 fixture 可算
    raw["factor_return"]["min_samples"] = 5
    raw["factor_return"]["warmup_periods"] = 2
    raw["factor_return"]["num_quantiles"] = 3
    config = ICConfig.model_validate(raw)
    orch = ICFilterOrchestrator(config)

    n = 40
    index = pd.date_range("2024-01-01", periods=n, freq="12h")
    rng = np.random.default_rng(11)
    features = pd.DataFrame(
        {
            "feat_a": rng.normal(size=n),
            "feat_b": rng.normal(size=n),
        },
        index=index,
        dtype=float,
    )
    labels = pd.Series(
        0.02 * features["feat_a"] + rng.normal(scale=0.01, size=n),
        index=index,
        name="future_return",
        dtype=float,
    )
    orch._ic_cache = {
        "features_df": features,
        "label_series": labels,
        "metadata": {},
        "icir": {name: {"icir": 0.1, "ic_mean": 0.02} for name in features.columns},
        "rolling_ic": {},
        "ic_decay": {},
        "grouped_ic": {},
        "event_info": {},
        "stage0_log": {},
        "preproc_log": {},
    }
    orch._filtered_features_df = features.copy()
    orch._report = {
        "summary_table": [
            {"feature_name": "feat_a", "ic_mean": 0.04},
            {"feature_name": "feat_b", "ic_mean": 0.02},
        ],
        "turnover_analysis": {},
    }
    return orch


def test_series_owner_reachable() -> None:
    """F1.1: force/_run_factor_return → series owner 有 pd.Series ls_return。"""
    orch = _build_orch_for_f1()
    result = orch._run_factor_return(["feat_a"], orch._config)

    assert isinstance(result, dict)
    assert result.get("status") == "ok"
    value = result.get("value") or {}
    assert value.get("schema_version") == "fr_full_v1"
    features = value.get("features") or {}
    assert "feat_a" in features

    series_map = orch._factor_return_series
    assert "feat_a" in series_map
    art = series_map["feat_a"]
    assert isinstance(art.ls_return, pd.Series)
    assert isinstance(art.ls_return.index, pd.DatetimeIndex)
    assert len(art.ls_return) > 0
    # 全序列有限（非只挑一個 finite 過關）
    assert np.isfinite(art.ls_return.to_numpy(dtype=float)).all()

    # force_modules 路徑亦寫入 owner（不經 sanitizer 斷言 completed——D16/F2）
    orch2 = _build_orch_for_f1()
    report = orch2.run_deep_analysis(force_modules=["factor_returns"])
    assert "feat_a" in orch2._factor_return_series
    assert isinstance(orch2._factor_return_series["feat_a"].ls_return, pd.Series)
    # 出口暫經 sanitizer → external 仍 unavailable；F1 不斷言 completed
    fr = report.results.get("factor_returns")
    assert isinstance(fr, dict)
    assert fr.get("status") == "unavailable"


def test_cache_hit_owner_consistency() -> None:
    """F1 雙審 codex-1：cache-hit/force-merge 缺 owner 時不得服務 series-dependent net_ic ok。

    契約：owner=[] 後，依賴 series 的 net_ic 必須 unavailable（或 owner 已重建）；
    不得 owner=[] 卻 net_ic status:ok / evaluable_count>0。
    """
    orch = _build_orch_for_f1()
    orch.run_deep_analysis(force_modules=["factor_returns"])
    assert orch._factor_return_series, "force run 應寫入 series owner"
    assert len(orch._deep_analysis_cache) >= 1
    key = next(iter(orch._deep_analysis_cache))
    # 注入 series-dependent stale net_ic（模擬 F4 接線後 cache 殘留）
    orch._deep_analysis_cache[key].results["net_ic_analysis"] = {
        "features": {
            "feat_a": {"status": "ok", "breakeven_cost_bps": 12.5},
        },
        "summary": {"evaluable_count": 1},
    }
    orch._deep_analysis_cache[key].module_summary["net_ic_analysis"] = "completed"

    # --- cache-hit：owner 清空，不得回傳 stale ok ---
    second = orch.run_deep_analysis()
    owner_keys = list(orch._factor_return_series.keys())
    net = second.results.get("net_ic_analysis")
    if not owner_keys:
        assert isinstance(net, dict), f"expected dict net_ic, got {net!r}"
        assert net.get("status") == "unavailable", (
            f"cache-hit owner=[] 卻 net_ic 非 unavailable: {net!r}"
        )
        assert net.get("reason") == "factor_return_series_unavailable_on_cache_hit"
        # 不得殘留 status:ok / evaluable>0
        assert net.get("status") != "ok"
        features = net.get("features") or {}
        for feat in features.values():
            if isinstance(feat, dict):
                assert feat.get("status") != "ok"
    else:
        # 允許重建 owner：則 net_ic 可保留；但不得空 owner 配 ok
        assert "feat_a" in owner_keys or "feat_b" in owner_keys

    # --- force-merge（只 force 非 FR 模組）：owner 仍空，cached series-ok 仍須降級 ---
    orch3 = _build_orch_for_f1()
    orch3.run_deep_analysis(force_modules=["factor_returns"])
    key3 = next(iter(orch3._deep_analysis_cache))
    orch3._deep_analysis_cache[key3].results["net_ic_analysis"] = {
        "features": {
            "feat_a": {
                "status": "ok",
                "net_factor_return": {"status": "ok", "value": 0.01},
                "breakeven_cost_bps": 12.5,
            },
        },
        "summary": {"evaluable_count": 1},
    }
    orch3._deep_analysis_cache[key3].module_summary["net_ic_analysis"] = "completed"
    # force 非 FR、非 net_ic → merge 保留 cache 的 net_ic + owner 入口清空
    third = orch3.run_deep_analysis(force_modules=["trend_analysis"])
    owner3 = list(orch3._factor_return_series.keys())
    net3 = third.results.get("net_ic_analysis")
    if not owner3:
        assert isinstance(net3, dict)
        assert net3.get("status") == "unavailable", (
            f"force-merge owner=[] 卻 net_ic 非 unavailable: {net3!r}"
        )
        assert net3.get("reason") == "factor_return_series_unavailable_on_cache_hit"
    else:
        assert any(k in owner3 for k in ("feat_a", "feat_b"))


def test_tier_truth_table() -> None:
    """F1.2 D13: 四 tier × enabled 矩陣；mock enabled=True 時 foundation 仍不含。"""
    from momentum.Analysis.ic_config_schema import ICConfig
    from momentum.Analysis.ic_filter_orchestrator import ICFilterOrchestrator

    # --- enabled=True mock：foundation 仍 False；其餘 True ---
    for preset, expect_enabled in (
        ("foundation", False),
        ("intermediate", True),
        ("advanced", True),
        ("custom", True),
    ):
        raw = ICConfig().model_dump(by_alias=True)
        raw["factor_return"]["enabled"] = True  # mock F5.2 後
        raw["feature_tiers"]["active_preset"] = preset
        if preset == "custom":
            raw["feature_tiers"]["custom_overrides"] = {
                "stage_overrides": {},
                "module_overrides": {"factor_return": True},
            }
        cfg = ICConfig.model_validate(raw)
        orch = ICFilterOrchestrator(cfg)
        applied = orch._apply_tier_config(cfg)
        assert applied.factor_return.enabled is expect_enabled, (
            f"tier={preset} enabled=True mock → got {applied.factor_return.enabled}, "
            f"want {expect_enabled}"
        )

    # --- enabled=False（F1.2~F4 現況）：四 tier 皆不開 FR ---
    for preset in ("foundation", "intermediate", "advanced", "custom"):
        raw = ICConfig().model_dump(by_alias=True)
        assert raw["factor_return"]["enabled"] is False
        raw["feature_tiers"]["active_preset"] = preset
        if preset == "custom":
            # custom 未覆寫 module → 保持 schema False
            raw["feature_tiers"]["custom_overrides"] = {
                "stage_overrides": {},
                "module_overrides": {},
            }
        cfg = ICConfig.model_validate(raw)
        orch = ICFilterOrchestrator(cfg)
        applied = orch._apply_tier_config(cfg)
        assert applied.factor_return.enabled is False, (
            f"tier={preset} enabled=False → got {applied.factor_return.enabled}"
        )


def test_tier_f12_enabled_still_false() -> None:
    """F1.2 機械鎖：FactorReturnConfig / ICConfig 預設 enabled 仍 False。"""
    from momentum.Analysis.ic_config_schema import FactorReturnConfig, ICConfig

    assert FactorReturnConfig().enabled is False
    assert ICConfig().factor_return.enabled is False
