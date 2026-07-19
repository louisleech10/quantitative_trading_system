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
