import numpy as np
import pandas as pd

from momentum.Analysis.deep_analysis_types import SkippedResult
from momentum.Analysis.parameter_sensitivity_analyzer import ParameterSensitivityAnalyzer


def _rolling_icir_oracle(x, y, window):
    """ICPERF Task 0.4 ⑳：滾動 ICIR oracle（逐窗 scipy.stats.spearmanr；窗內常數 ⇒ NaN；nanmean／nanstd ddof=0）。"""
    from scipy import stats as _stats

    vals = []
    for end in range(window, len(y) + 1):
        xs, ys = x[end - window:end], y[end - window:end]
        vals.append(np.nan if np.unique(xs).size <= 1 or np.unique(ys).size <= 1 else _stats.spearmanr(xs, ys)[0])
    arr = np.asarray(vals, dtype=float)
    if not np.isfinite(arr).any():
        return np.nan
    sd = float(np.nanstd(arr))
    return float(np.nanmean(arr) / sd) if sd > 0 else np.nan


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

    # ICPERF Task 0.4 ⑳：icir 代理 `_compute_icir_proxy` 已刪 → 改測 `_compute_rolling_icir`（常數特徵 ⇒ 全窗 NaN ⇒ ICIR NaN；
    # 一般輸入 == 逐窗 scipy spearman 之 nanmean／nanstd(ddof=0)）
    zeros = pd.Series([0.0] * 6)
    assert np.isnan(ParameterSensitivityAnalyzer._compute_rolling_icir(zeros.to_frame("z"), y2.astype(float), "spearman", 3)["z"])
    i = np.arange(40, dtype=float)
    feat = pd.Series(np.sin(i / 3.0) + 0.2 * np.cos(i / 1.3))
    lab = pd.Series(np.sin((i + 1) / 3.0) + 0.5 * np.cos(i / 2.1))
    got = ParameterSensitivityAnalyzer._compute_rolling_icir(feat.to_frame("f"), lab, "spearman", 10)["f"]
    exp = _rolling_icir_oracle(feat.to_numpy(), lab.to_numpy(), 10)
    assert np.isfinite(exp) and abs(got - exp) <= 1e-12 * abs(exp), (got, exp)


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
    labels = pd.Series(base + rng.normal(scale=1.0, size=240), index=idx)  # ICPERF Task 0.4 ⑳：標籤雜訊 0.1→1.0（icir 改滾動 ICIR 後，IC≈0.99 之窗間 std 趨 0 使 ICIR 爆大、穩定族 icir_std 達 60；改為中等 IC 使 ICIR 落一般量級）
    df = pd.DataFrame(
        {
            "stable_10": base + rng.normal(scale=0.001, size=240),  # ICPERF Task 0.4 ⑳：變體雜訊 0.01→0.001（同族變體近乎相同 ⇒ 滾動 ICIR 近乎相同，stable 仍判 low）
            "stable_20": base + rng.normal(scale=0.001, size=240),
            "stable_30": base + rng.normal(scale=0.001, size=240),
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
        # ICPERF Task 0.4 ⑳：icir oracle 由代理 mean(x·y)/std(x·y) → 滾動 IC（窗 63、步長 1、逐窗 scipy spearman）之 nanmean／nanstd（同 compute_icir）
        icirs = np.array([_rolling_icir_oracle(df[c].to_numpy(), labels.to_numpy(), 63) for c in cols])
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
