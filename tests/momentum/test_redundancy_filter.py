import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.redundancy_filter import RedundancyFilter


def test_compute_correlation_matrix_values():
    """相關性矩陣計算正確。"""
    df = pd.DataFrame(
        {
            "f1": [1.0, 2.0, 3.0, 4.0],
            "f2": [1.0, 2.0, 3.0, 4.0],
            "f3": [1.0, 0.0, 1.0, 0.0],
        }
    )
    rf = RedundancyFilter({"correlation_threshold": 0.7})

    corr = rf.compute_correlation_matrix(df)

    assert np.isclose(corr.loc["f1", "f2"], 1.0)
    assert corr.shape == (3, 3)


def test_greedy_dedup_prefers_higher_icir():
    """高相關時保留 ICIR 較高者。"""
    base = np.linspace(0, 1, 100)
    df = pd.DataFrame(
        {
            "f1": base,
            "f2": base + 0.0001,
            "f3": np.random.default_rng(42).normal(size=100),
        }
    )
    rf = RedundancyFilter({"correlation_threshold": 0.9, "tiebreaker": "icir"})
    corr = rf.compute_correlation_matrix(df)
    ic_scores = {
        "f1": {"icir": 0.8},
        "f2": {"icir": 0.2},
        "f3": {"icir": 0.5},
    }

    selected = rf.greedy_dedup(corr, ic_scores, threshold=0.9, tiebreaker="icir")

    assert "f1" in selected
    assert "f2" not in selected
    assert "f3" in selected


def test_hierarchical_clustering_selects_top_per_cluster():
    """階層聚類保留每群最高分特徵。"""
    base = np.linspace(0, 1, 120)
    df = pd.DataFrame(
        {
            "f1": base,
            "f2": base + 0.0001,
            "f3": np.random.default_rng(7).normal(size=120),
        }
    )
    rf = RedundancyFilter({"correlation_threshold": 0.85})
    corr = rf.compute_correlation_matrix(df)
    ic_scores = {"f1": {"icir": 0.4}, "f2": {"icir": 0.9}, "f3": {"icir": 0.3}}

    selected = rf.hierarchical_clustering(corr, ic_scores, linkage_method="average")

    assert "f3" in selected
    assert ("f1" in selected) != ("f2" in selected)


def test_vif_filter_removes_collinear():
    """VIF 過高時移除共線特徵。"""
    base = np.linspace(0, 1, 200)
    df = pd.DataFrame(
        {
            "f1": base,
            "f2": base * 1.01,
            "f3": np.random.default_rng(123).normal(size=200),
        }
    )
    rf = RedundancyFilter({"vif": {"max_vif": 5.0}})

    selected = rf.vif_filter(df, max_vif=5.0)

    assert "f3" in selected
    assert len(selected) == 2


def test_diversification_metrics_coverages():
    """多元化覆蓋率計算正確。"""
    rf = RedundancyFilter({})
    selected = ["f1", "f3"]
    corr = pd.DataFrame(
        [[1.0, 0.2], [0.2, 1.0]],
        index=selected,
        columns=selected,
    )
    metadata = {
        "f1": {"category": "a", "data_source": "x", "layer": 1},
        "f2": {"category": "b", "data_source": "x", "layer": 1},
        "f3": {"category": "c", "data_source": "y", "layer": 2},
        "f4": {"category": "d", "data_source": "z", "layer": 3},
    }

    metrics = rf.compute_diversification_metrics(selected, corr, metadata)

    assert np.isclose(metrics["category_coverage"], 0.5)
    assert np.isclose(metrics["data_source_coverage"], 2.0 / 3.0)
    assert np.isclose(metrics["layer_coverage"], 2.0 / 3.0)


def test_filter_empty_and_invalid_method():
    """空 DataFrame 與未知方法處理。"""
    rf = RedundancyFilter({})

    empty_df = pd.DataFrame()
    filtered, log = rf.filter(empty_df, ic_scores={}, method="greedy")
    assert filtered.empty
    assert log["output_features"] == 0

    with pytest.raises(ValueError):
        rf.filter(pd.DataFrame({"a": [1.0, 2.0]}), ic_scores={}, method="unknown")


def test_correlation_matrix_with_nan():
    """含 NaN 時走 pandas corr 分支。"""
    df = pd.DataFrame({"a": [1.0, np.nan, 3.0], "b": [1.0, 2.0, 3.0]})
    rf = RedundancyFilter({})

    corr = rf.compute_correlation_matrix(df)

    assert corr.shape == (2, 2)


def test_vif_filter_handles_empty_and_single_feature():
    """空資料或單欄位應回傳原特徵。"""
    rf = RedundancyFilter({})

    assert rf.vif_filter(pd.DataFrame()) == []

    df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
    assert rf.vif_filter(df) == ["a"]


def test_compute_vif_scores_edge_cases():
    """VIF 計算的例外與特殊值分支。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"a": [1.0, 1.0, 1.0], "b": [2.0, 3.0, 4.0]})

    vifs = rf._compute_vif_scores(df)
    assert vifs["a"] == float("inf")


def test_diversification_metrics_empty_inputs():
    """無特徵或 metadata 應回預設值。"""
    rf = RedundancyFilter({})

    metrics = rf.compute_diversification_metrics([], pd.DataFrame(), {})
    assert metrics["effective_independent_features"] == 0.0

    metrics = rf.compute_diversification_metrics(["f1"], pd.DataFrame(), None)
    assert metrics["category_coverage"] == 0.0


def test_filter_none_features_raises():
    """features_df 為 None 應拋錯。"""
    rf = RedundancyFilter({})

    with pytest.raises(ValueError):
        rf.filter(None, ic_scores={})


def test_filter_hierarchical_and_vif_paths():
    """filter 應涵蓋 hierarchical 與 vif。"""
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [1.0, 2.0, 3.0]})
    rf = RedundancyFilter({"correlation_threshold": 0.5, "vif": {"max_vif": 100.0}})

    filtered, _ = rf.filter(df, ic_scores={"f1": 0.1, "f2": 0.2}, method="hierarchical")
    assert not filtered.empty

    filtered, _ = rf.filter(df, ic_scores={"f1": 0.1, "f2": 0.2}, method="vif")
    assert not filtered.empty


def test_compute_correlation_matrix_empty():
    """空資料應回空矩陣。"""
    rf = RedundancyFilter({})
    assert rf.compute_correlation_matrix(pd.DataFrame()).empty


def test_greedy_dedup_empty_and_nan_correlations():
    """空相關矩陣與 NaN 相關分支。"""
    rf = RedundancyFilter({})

    assert rf.greedy_dedup(pd.DataFrame(), {}, threshold=0.7) == []

    corr = pd.DataFrame(
        [[1.0, np.nan], [np.nan, 1.0]],
        index=["f1", "f2"],
        columns=["f1", "f2"],
    )
    selected = rf.greedy_dedup(corr, {"f1": 0.2, "f2": 0.1}, threshold=0.7)
    assert set(selected) == {"f1", "f2"}


def test_hierarchical_empty_and_single_feature():
    """hierarchical 空矩陣或單特徵應回空或自身。"""
    rf = RedundancyFilter({})

    assert rf.hierarchical_clustering(pd.DataFrame(), {}, linkage_method="average") == []

    corr = pd.DataFrame([[1.0]], index=["f1"], columns=["f1"])
    assert rf.hierarchical_clustering(corr, {"f1": 0.2}, linkage_method="average") == ["f1"]


def test_vif_filter_breaks_and_tiebreaker(monkeypatch):
    """VIF 分支的 break 與 tiebreaker 路徑。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [1.0, 2.0, 3.0]})

    monkeypatch.setattr(rf, "_compute_vif_scores", lambda _data: {})
    assert rf.vif_filter(df, max_vif=5.0) == ["f1", "f2"]

    def _vifs(_data):
        return {"f1": 2.0, "f2": 2.0}

    monkeypatch.setattr(rf, "_compute_vif_scores", _vifs)
    selected = rf.vif_filter(df, max_vif=1.0, ic_scores={"f1": {"icir": 0.1}, "f2": {"icir": 0.9}})
    assert len(selected) == 1


def test_vif_filter_breaks_on_max_vif_threshold(monkeypatch):
    """VIF 低於閾值時應直接停止。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [2.0, 3.0, 4.0]})

    monkeypatch.setattr(rf, "_compute_vif_scores", lambda _data: {"f1": 1.0, "f2": 1.1})
    selected = rf.vif_filter(df, max_vif=5.0)

    assert set(selected) == {"f1", "f2"}


def test_vif_filter_breaks_on_low_vif_values():
    """實際 VIF 值偏低時應直接停止。"""
    rng = np.random.default_rng(0)
    df = pd.DataFrame({"f1": rng.normal(size=200), "f2": rng.normal(size=200)})
    rf = RedundancyFilter({})

    selected = rf.vif_filter(df, max_vif=10.0)

    assert set(selected) == {"f1", "f2"}


def test_vif_filter_breaks_when_max_vif_met(monkeypatch):
    """max_vif 條件成立時應中止迴圈。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [2.0, 3.0, 4.0]})
    calls: list[str] = []

    def _vifs(_data):
        calls.append("called")
        return {"f1": 0.0, "f2": 0.0}

    monkeypatch.setattr(rf, "_compute_vif_scores", _vifs)
    selected = rf.vif_filter(df, max_vif=0.0)

    assert len(calls) == 1
    assert set(selected) == {"f1", "f2"}


def test_vif_filter_breaks_when_max_vif_not_exceeded(monkeypatch):
    """max_vif 未被超過時應直接停止。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"f1": [1.0, 2.0, 3.0], "f2": [2.0, 3.0, 4.0]})

    monkeypatch.setattr(rf, "_compute_vif_scores", lambda _data: {"f1": 0.5, "f2": 0.8})
    selected = rf.vif_filter(df, max_vif=1.0)

    assert set(selected) == {"f1", "f2"}


def test_compute_vif_scores_single_feature():
    """單一特徵 x.size=0 分支。"""
    rf = RedundancyFilter({})
    vifs = rf._compute_vif_scores(pd.DataFrame({"f1": [1.0, 2.0, 3.0]}))
    assert vifs["f1"] == 1.0


def test_compute_vif_scores_regression_exception(monkeypatch):
    """回歸例外應回 inf。"""
    rf = RedundancyFilter({})
    df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [2.0, 1.0, 0.0]})

    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("sklearn.linear_model.LinearRegression.fit", _raise)
    vifs = rf._compute_vif_scores(df)
    assert vifs["a"] == float("inf")


def test_score_value_branches():
    """score_value 的空、dict、數值分支。"""
    assert RedundancyFilter._score_value({}, "f1", "icir") == float("-inf")

    ic_scores = {"f1": {"icir": 0.3}}
    assert RedundancyFilter._score_value(ic_scores, "f1", "unknown") == 0.3

    ic_scores = {"f1": 0.5}
    assert RedundancyFilter._score_value(ic_scores, "f1", "icir") == 0.5

    ic_scores = {"f1": "bad"}
    assert RedundancyFilter._score_value(ic_scores, "f1", "icir") == float("-inf")


def test_compute_coverage_no_total_values():
    """缺少 key 時 coverage 回 0。"""
    metadata = {"f1": {}}
    assert RedundancyFilter._compute_coverage(metadata, ["f1"], "category") == 0.0
