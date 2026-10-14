import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer


def _make_dataset():
    rng = np.random.default_rng(42)
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    base = rng.normal(size=240)
    labels = pd.Series(base * 0.02 + rng.normal(scale=0.01, size=240), index=idx)
    df = pd.DataFrame(
        {
            "close_RSI_10": base + rng.normal(scale=0.1, size=240),
            "close_RSI_14": base + rng.normal(scale=0.1, size=240),
            "close_RSI_21": base + rng.normal(scale=0.1, size=240),
            "other": rng.normal(size=240),
        },
        index=idx,
    )
    return df, labels


def test_detect_feature_families():
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    families = analyzer.detect_feature_families(["close_RSI_10", "close_RSI_14", "x"])
    assert "close_RSI" in families


def test_analyze_from_variants_success():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="close_RSI",
        variant_params={"variants": ["close_RSI_10", "close_RSI_14", "close_RSI_21"]},
    )
    assert isinstance(result, dict)
    assert "stability_metrics" in result


def test_small_family_skip():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="small",
        variant_params={"variants": ["close_RSI_10", "close_RSI_14"]},
    )
    assert isinstance(result, SkippedResult)


def test_batch_analyze():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.batch_analyze(df, labels)
    assert "families" in result
    assert "summary" in result


def test_detect_feature_families_with_metadata():
    analyzer = ParameterSensitivityAnalyzer({})
    features = ["a_10", "a_20", "b_10"]
    metadata = {
        "a_10": {"indicator": "rsi", "data_source": "close"},
        "a_20": {"indicator": "rsi", "data_source": "close"},
        "b_10": {"indicator": "ema", "data_source": "close"},
    }
    families = analyzer.detect_feature_families(features, metadata)
    assert "close_rsi" in families
    assert len(families["close_rsi"]) == 2


def test_analyze_from_variants_insufficient_valid_variants():
    df, labels = _make_dataset()
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="close_RSI",
        variant_params={"variants": ["close_RSI_10", "missing_1", "missing_2"]},
    )
    assert isinstance(result, SkippedResult)


def test_analyze_from_variants_all_nan_ic():
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    labels = pd.Series(0.1, index=idx)
    df = pd.DataFrame(
        {
            "f_10": np.arange(240, dtype=float),
            "f_20": np.arange(240, dtype=float) + 1,
            "f_30": np.arange(240, dtype=float) + 2,
        },
        index=idx,
    )
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.analyze_from_variants(
        df,
        labels,
        feature_family="f",
        variant_params={"variants": ["f_10", "f_20", "f_30"]},
    )
    assert isinstance(result, SkippedResult)


def test_classify_overfitting_risk_levels():
    analyzer = ParameterSensitivityAnalyzer({"ic_std_threshold_low": 0.02, "ic_std_threshold_high": 0.05})
    assert analyzer.classify_overfitting_risk(0.01, 0.1) == "low"
    assert analyzer.classify_overfitting_risk(0.03, 0.2) == "medium"
    assert analyzer.classify_overfitting_risk(0.08, 0.4) == "high"


def test_batch_analyze_collects_high_and_low_risk():
    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    rng = np.random.default_rng(11)
    base = rng.normal(size=240)
    labels = pd.Series(base + rng.normal(scale=0.1, size=240), index=idx)

    df = pd.DataFrame(
        {
            "stable_10": base + rng.normal(scale=0.01, size=240),
            "stable_20": base + rng.normal(scale=0.01, size=240),
            "stable_30": base + rng.normal(scale=0.01, size=240),
            "noisy_10": rng.normal(size=240),
            "noisy_20": rng.normal(size=240),
            "noisy_30": rng.normal(size=240),
        },
        index=idx,
    )
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3})
    result = analyzer.batch_analyze(df, labels)

    assert "high_risk_families" in result
    assert "robust_families" in result


def test_compute_ic_and_icir_proxy_edge_cases():
    x = pd.Series([1, 2, 3, 4])
    y = pd.Series([1, 2, 3, 4])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_ic(x, y))

    x2 = pd.Series([1, 1, 1, 1, 1, 1])
    y2 = pd.Series([1, 2, 3, 4, 5, 6])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_ic(x2, y2))

    zeros = pd.Series([0, 0, 0, 0, 0, 0])
    assert np.isnan(ParameterSensitivityAnalyzer._compute_icir_proxy(zeros, y2))


def test_extract_param_value_without_suffix():
    value = ParameterSensitivityAnalyzer._extract_param_value("feature_alpha")
    assert value == "feature_alpha"


def test_batch_analyze_classifies_stable_robust_and_noisy_not_robust():
    """TESTREG 純增改寫：batch_analyze 須把 stable 家族收進 robust、noisy 不得進 robust；
    各家族 ic_std／風險分級對獨立 oracle（scipy spearman＋手算 std(ddof=0)＋文件門檻）。

    舊測試只驗 high_risk_families／robust_families 兩鍵存在（生產無條件回傳）⇒ 恆綠。
    """
    from scipy import stats as _stats

    idx = pd.date_range("2024-01-01", periods=240, freq="12h")
    rng = np.random.default_rng(11)
    base = rng.normal(size=240)
    labels = pd.Series(base + rng.normal(scale=0.1, size=240), index=idx)
    df = pd.DataFrame(
        {
            "stable_10": base + rng.normal(scale=0.01, size=240),
            "stable_20": base + rng.normal(scale=0.01, size=240),
            "stable_30": base + rng.normal(scale=0.01, size=240),
            "noisy_10": rng.normal(size=240),
            "noisy_20": rng.normal(size=240),
            "noisy_30": rng.normal(size=240),
        },
        index=idx,
    )
    analyzer = ParameterSensitivityAnalyzer({"min_family_size": 3, "ic_std_threshold_low": 0.02, "ic_std_threshold_high": 0.05})
    result = analyzer.batch_analyze(df, labels)

    assert result["robust_families"] == ["stable"] and "noisy" not in result["robust_families"] and "stable" not in result["high_risk_families"] and result["summary"]["robust_count"] == 1, result

    def _oracle(prefix):
        cols = [f"{prefix}_{p}" for p in (10, 20, 30)]
        ics = np.array([_stats.spearmanr(df[c].to_numpy(), labels.to_numpy())[0] for c in cols])
        prods = [df[c].to_numpy() * labels.to_numpy() for c in cols]
        icirs = np.array([p.mean() / np.sqrt(((p - p.mean()) ** 2).sum() / (p.size - 1)) for p in prods])
        ic_std = float(np.sqrt(((ics - ics.mean()) ** 2).mean()))
        icir_std = float(np.sqrt(((icirs - icirs.mean()) ** 2).mean()))
        risk = "low" if (ic_std < 0.02 and icir_std < 0.15) else ("medium" if (ic_std < 0.05 and icir_std < 0.3) else "high")
        return ic_std, risk

    oracle = {fam: _oracle(fam) for fam in ("stable", "noisy")}
    assert set(result["families"]) == {"stable", "noisy"} and all(
        abs(result["families"][fam]["stability_metrics"]["ic_std_across_params"] - oracle[fam][0]) <= 1e-12
        and result["families"][fam]["stability_metrics"]["overfitting_risk"] == oracle[fam][1]
        for fam in oracle
    ), (oracle, {f: v["stability_metrics"] for f, v in result["families"].items()})
