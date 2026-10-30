import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.rolling_oos_validator import RollingOOSValidator


def _make_data(n=420):
    rng = np.random.default_rng(123)
    idx = pd.date_range("2024-01-01", periods=n, freq="12h")
    feature = pd.Series(rng.normal(size=n), index=idx)
    labels = pd.Series(feature.values * 0.03 + rng.normal(scale=0.02, size=n), index=idx)
    return feature, labels


def test_validate_success():
    feature, labels = _make_data()
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})

    result = analyzer.validate(feature, labels, horizon=1)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h

    assert isinstance(result, dict)
    assert "oos_stability" in result
    assert result["assessment"] in {"robust", "moderate", "overfitting"}


def test_data_too_short_for_oos():
    feature, labels = _make_data(100)
    analyzer = RollingOOSValidator({"train_window": 80, "test_window": 40, "step": 10})

    result = analyzer.validate(feature, labels, horizon=1)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h

    assert isinstance(result, SkippedResult)


def test_auto_reduce_step_generate_splits():
    analyzer = RollingOOSValidator({"train_window": 100, "test_window": 20, "step": 50, "min_splits": 5})
    splits = analyzer._generate_splits(260)
    assert len(splits) >= 1


def test_validate_batch():
    feature, labels = _make_data()
    features_df = pd.DataFrame({"f1": feature, "f2": feature * 0.8 + 0.1})
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})

    result = analyzer.validate_batch(features_df, labels, horizon=1, top_n=2)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h

    assert "features" in result
    assert "summary" in result
    assert len(result["features"]) == 2


def test_no_valid_splits_skip(monkeypatch):
    feature, labels = _make_data(300)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 40, "step": 20})

    monkeypatch.setattr(analyzer, "_generate_splits", lambda n: [])
    result = analyzer.validate(feature, labels, horizon=1)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h
    assert isinstance(result, SkippedResult)
    assert result.reason == "no valid splits generated"


def test_all_splits_invalid_skip(monkeypatch):
    feature, labels = _make_data(360)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15})

    monkeypatch.setattr(analyzer, "_compute_ic", lambda x, y, method: np.nan)
    result = analyzer.validate(feature, labels, horizon=1)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h
    assert isinstance(result, SkippedResult)
    assert result.reason == "all splits invalid"


def test_validate_with_pearson_path():
    feature, labels = _make_data(420)
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})
    result = analyzer.validate(feature, labels, method="pearson", horizon=1)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h
    assert isinstance(result, dict)
    assert "oos_stability" in result


def test_compute_ic_short_and_constant():
    short = RollingOOSValidator._compute_ic(pd.Series([1, 2]), pd.Series([1, 2]), "spearman")
    assert np.isnan(short)

    constant = RollingOOSValidator._compute_ic(pd.Series([1] * 10), pd.Series(np.arange(10)), "spearman")
    assert np.isnan(constant)  # ICPERF Task 0.4 ⑳：常數窗 0.0→NaN（相關係數於常數輸入未定義，同 scipy；不入統計）


def test_classify_assessment_boundaries():
    analyzer = RollingOOSValidator({
        "assessment_thresholds": {
            "robust_hit_rate": 0.7,
            "robust_max_degradation": 0.3,
            "moderate_hit_rate": 0.5,
            "moderate_max_degradation": 0.5,
        }
    })
    assert analyzer._classify_assessment(0.8, 0.2) == "robust"
    assert analyzer._classify_assessment(0.55, 0.4) == "moderate"
    assert analyzer._classify_assessment(0.4, 0.9) == "overfitting"


def test_validate_batch_with_skipped_feature_summary_counts():
    analyzer = RollingOOSValidator({"train_window": 120, "test_window": 30, "step": 15, "min_splits": 5})
    f1, labels = _make_data(420)
    f2, _ = _make_data(80)
    features_df = pd.DataFrame({"f1": f1.reindex(labels.index), "f2": f2.reindex(labels.index)})

    result = analyzer.validate_batch(features_df, labels, horizon=1, top_n=2)  # ICPERF Task 0.4 ⑬／⑳：補必填 horizon（標籤與特徵同期、無前瞻語意 ⇒ 取 1），訓練段 purge ≥ h
    assert result["summary"]["total_validated"] >= 1
    assert result["features"]["f2"].get("skipped", False) is True


def test_auto_reduce_step_exact_splits_and_no_overlap():
    """自動縮步精確驗：n=260、train100/test20、step50 只得 3 段（<min_splits=5）⇒ 縮為 step25。

    手算 oracle：step25 起點 s∈{0,25,50,75,100,125}（s=150 時 test_end=270>260 停）共 6 段；
    每段 train=range(s,s+100)、test=range(s+100,s+120)，test 緊接 train 之後且不重疊（OOS 無前視）。
    """
    analyzer = RollingOOSValidator({"train_window": 100, "test_window": 20, "step": 50, "min_splits": 5})
    splits = analyzer._generate_splits(260)
    expected = [(range(s, s + 100), range(s + 100, s + 120)) for s in (0, 25, 50, 75, 100, 125)]
    assert [(tr, te) for tr, te in splits] == expected and all(max(tr) < min(te) and set(tr).isdisjoint(te) for tr, te in splits), f"splits={splits}"
