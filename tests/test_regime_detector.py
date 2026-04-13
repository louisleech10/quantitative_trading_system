"""
Test suite for RegimeDetector (K-Means 無監督市場體制偵測)

覆蓋範圍：
  - 基本 K-Means detect（全局 fit / expanding fit）
  - Label alignment（按 volatility 排序）
  - Fallback to rule-based（資料不足時）
  - 邊界條件：NaN、常數資料、單一 cluster、極小樣本
  - detect_phases_for_index（供 RegimeAnalyzer 使用）
  - IC Engine 整合（config dispatch）
  - Config schema 新欄位驗證
"""

import numpy as np
import pandas as pd
import pytest

from momentum.Analysis.regime_detector import (
    RegimeDetector,
    RegimeDetectionResult,
    REGIME_LABELS_3,
    REGIME_LABELS_4,
)


# ==================== Fixtures ====================

@pytest.fixture
def simple_price_series():
    """產生模擬 K 線收盤價（含趨勢 + 波動變化）"""
    np.random.seed(42)
    n = 500
    # 前 250: 低波動上漲，後 250: 高波動下跌
    prices_up = 100 + np.cumsum(np.random.normal(0.05, 0.3, 250))
    prices_down = prices_up[-1] + np.cumsum(np.random.normal(-0.1, 1.5, 250))
    prices = np.concatenate([prices_up, prices_down])
    return pd.Series(prices, name="close")


@pytest.fixture
def price_with_volume():
    """收盤價 + 成交量"""
    np.random.seed(42)
    n = 500
    prices = 100 + np.cumsum(np.random.normal(0.02, 0.5, n))
    volume = np.abs(np.random.normal(1000, 200, n))
    # 後段放大成交量
    volume[300:] *= 3
    return pd.Series(prices, name="close"), pd.Series(volume, name="volume")


@pytest.fixture
def constant_price_series():
    """常數價格（零波動）"""
    return pd.Series([100.0] * 200, name="close")


@pytest.fixture
def tiny_price_series():
    """極小樣本（< min_samples_for_fit）"""
    np.random.seed(42)
    return pd.Series(100 + np.cumsum(np.random.normal(0, 0.5, 20)), name="close")


@pytest.fixture
def nan_heavy_price_series():
    """含大量 NaN 的價格序列"""
    np.random.seed(42)
    n = 500
    prices = 100 + np.cumsum(np.random.normal(0.02, 0.5, n))
    series = pd.Series(prices, name="close")
    # 隨機 30% 設為 NaN
    mask = np.random.random(n) < 0.3
    series[mask] = np.nan
    return series


# ==================== 基本功能測試 ====================

class TestRegimeDetectorBasic:
    """基本 K-Means detect 功能"""

    def test_detect_global_fit(self, simple_price_series):
        """全局 fit 應回傳正確結構"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)

        assert isinstance(result, RegimeDetectionResult)
        assert result.method == "kmeans"
        assert result.n_clusters == 4
        assert len(result.labels) == len(simple_price_series)
        assert len(result.feature_names) >= 2  # volatility + trend_strength

    def test_detect_expanding_fit(self, simple_price_series):
        """Expanding fit 應回傳正確結構"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=True)

        assert result.method == "kmeans"
        assert len(result.labels) == len(simple_price_series)

    def test_detect_with_volume(self, price_with_volume):
        """含 volume 應多一個 volume_ratio 特徵"""
        close, volume = price_with_volume
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(close, volume=volume, expanding=False)

        assert "volume_ratio" in result.feature_names
        assert result.method == "kmeans"

    def test_detect_3_clusters(self, simple_price_series):
        """n_clusters=3 應使用 REGIME_LABELS_3"""
        detector = RegimeDetector(n_clusters=3, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)

        valid_labels = set(REGIME_LABELS_3) | {"", "unknown"}
        for label in result.labels:
            assert label in valid_labels, f"Unexpected label: {label}"


# ==================== Label Alignment 測試 ====================

class TestLabelAlignment:
    """驗證 label 按 volatility 降序排列"""

    def test_high_vol_label_has_highest_volatility(self, simple_price_series):
        """high_vol_trending cluster 應有最高波動率均值"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)

        stats = result.cluster_stats
        if not stats:
            pytest.skip("No cluster stats available")

        # 找出有 volatility_mean 的 stats
        vol_means = {s["regime"]: s.get("volatility_mean", 0) for s in stats}
        sorted_regimes = sorted(vol_means, key=lambda k: vol_means[k], reverse=True)

        # 第一個應是 high_vol_trending
        if "high_vol_trending" in vol_means:
            assert sorted_regimes[0] == "high_vol_trending"

    def test_deterministic_labels(self, simple_price_series):
        """同樣輸入應產出相同 labels"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        r1 = detector.detect(simple_price_series, expanding=False)
        r2 = detector.detect(simple_price_series, expanding=False)
        np.testing.assert_array_equal(r1.labels, r2.labels)


# ==================== Fallback 測試 ====================

class TestFallbackRuleBased:
    """資料不足時 fallback 到規則式"""

    def test_fallback_on_tiny_data(self, tiny_price_series):
        """樣本不足應 fallback 到 rule-based"""
        detector = RegimeDetector(n_clusters=4, lookback=10, min_samples_for_fit=100)
        result = detector.detect(tiny_price_series, expanding=False)

        assert result.method == "rule"
        assert len(result.labels) == len(tiny_price_series)

    def test_fallback_labels_are_semantic(self, tiny_price_series):
        """Fallback 的 labels 應是有意義的字串"""
        detector = RegimeDetector(n_clusters=4, lookback=5, min_samples_for_fit=100)
        result = detector.detect(tiny_price_series, expanding=False)

        valid_rule_labels = {
            "high_vol_trending", "mid_vol_trending",
            "mid_vol_ranging", "low_vol_ranging", "unknown"
        }
        for label in result.labels:
            assert label in valid_rule_labels, f"Unexpected fallback label: {label}"


# ==================== 邊界條件測試 ====================

class TestEdgeCases:
    """邊界條件和異常輸入"""

    def test_constant_price(self, constant_price_series):
        """常數價格（零波動）不應 crash"""
        detector = RegimeDetector(n_clusters=4, lookback=10, min_samples_for_fit=50)
        result = detector.detect(constant_price_series, expanding=False)
        assert len(result.labels) == len(constant_price_series)

    def test_nan_heavy_data(self, nan_heavy_price_series):
        """大量 NaN 資料不應 crash"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(nan_heavy_price_series, expanding=False)
        assert len(result.labels) == len(nan_heavy_price_series)

    def test_all_nan_data(self):
        """全 NaN 應 fallback"""
        series = pd.Series([np.nan] * 100, name="close")
        detector = RegimeDetector(n_clusters=4, lookback=10, min_samples_for_fit=50)
        result = detector.detect(series, expanding=False)
        assert result.method == "rule"

    def test_invalid_n_clusters(self):
        """n_clusters < 2 應 raise ValueError"""
        with pytest.raises(ValueError, match="n_clusters"):
            RegimeDetector(n_clusters=1)

    def test_invalid_lookback(self):
        """lookback < 5 應 raise ValueError"""
        with pytest.raises(ValueError, match="lookback"):
            RegimeDetector(lookback=3)

    def test_volume_all_nan(self, simple_price_series):
        """volume 全 NaN 應忽略不用"""
        volume = pd.Series([np.nan] * len(simple_price_series))
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, volume=volume, expanding=False)
        assert "volume_ratio" not in result.feature_names

    def test_single_value_after_dropna(self):
        """dropna 後只剩極少資料應 fallback"""
        series = pd.Series([np.nan] * 99 + [100.0], name="close")
        detector = RegimeDetector(n_clusters=4, lookback=10, min_samples_for_fit=50)
        result = detector.detect(series, expanding=False)
        assert result.method == "rule"


# ==================== detect_phases_for_index 測試 ====================

class TestDetectPhasesForIndex:
    """供 RegimeAnalyzer 使用的 phase label 產生"""

    def test_produces_list_of_strings(self, simple_price_series):
        """回傳應是 List[str]"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        phases = detector.detect_phases_for_index(simple_price_series)
        assert isinstance(phases, list)
        assert len(phases) == len(simple_price_series)
        assert all(isinstance(p, str) for p in phases)

    def test_custom_index_alignment(self, simple_price_series):
        """自訂 index 時應正確對齊"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        subset_index = simple_price_series.index[100:200]
        phases = detector.detect_phases_for_index(
            simple_price_series, index=subset_index
        )
        assert len(phases) == 100


# ==================== Cluster Stats 測試 ====================

class TestClusterStats:
    """聚類統計品質"""

    def test_cluster_stats_sum_to_100(self, simple_price_series):
        """所有 cluster 的 pct 加總應接近 100%"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)

        if not result.cluster_stats:
            pytest.skip("No cluster stats")

        total_pct = sum(s["pct"] for s in result.cluster_stats)
        # 允許因 NaN 等原因的小誤差
        assert 90.0 <= total_pct <= 100.5, f"Total pct = {total_pct}"

    def test_cluster_stats_have_volatility(self, simple_price_series):
        """每個 stat 應包含 volatility_mean"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)

        for stat in result.cluster_stats:
            assert "volatility_mean" in stat
            assert "volatility_std" in stat


# ==================== Config Schema 整合測試 ====================

class TestConfigSchemaIntegration:
    """ic_config_schema 新欄位驗證"""

    def test_grouped_config_accepts_regime_method(self):
        """GroupedConfig 應接受 regime_method 欄位"""
        from momentum.Analysis.ic_config_schema import ICCalculationConfig

        config = ICCalculationConfig(
            grouped_analysis={
                "regime_method": "kmeans",
                "regime_kmeans": {
                    "n_clusters": 3,
                    "lookback": 30,
                    "min_samples_for_fit": 200,
                },
            }
        )
        assert config.grouped_analysis.regime_method == "kmeans"
        assert config.grouped_analysis.regime_kmeans["n_clusters"] == 3

    def test_grouped_config_default_is_rule(self):
        """預設 regime_method 應是 'rule'"""
        from momentum.Analysis.ic_config_schema import ICCalculationConfig

        config = ICCalculationConfig()
        assert config.grouped_analysis.regime_method == "rule"

    def test_full_ic_config_with_kmeans(self):
        """完整 ICConfig 應能載入 kmeans 設定"""
        from momentum.Analysis.ic_config_schema import ICConfig

        data = {
            "ic_calculation": {
                "grouped_analysis": {
                    "regime_method": "kmeans",
                    "regime_kmeans": {
                        "n_clusters": 4,
                        "lookback": 55,
                        "min_samples_for_fit": 100,
                    },
                }
            }
        }
        config = ICConfig.model_validate(data)
        assert config.ic_calculation.grouped_analysis.regime_method == "kmeans"


# ==================== Factory 整合測試 ====================

class TestFactoryIntegration:
    """momentum.factories 整合驗證"""

    def test_create_regime_detector_default(self):
        """create_regime_detector 預設參數"""
        from momentum.factories import create_regime_detector

        detector = create_regime_detector()
        assert isinstance(detector, RegimeDetector)
        assert detector.n_clusters == 4

    def test_create_regime_detector_custom(self):
        """create_regime_detector 自訂參數"""
        from momentum.factories import create_regime_detector

        detector = create_regime_detector(n_clusters=3, lookback=30, min_samples_for_fit=200)
        assert detector.n_clusters == 3
        assert detector.lookback == 30
        assert detector.min_samples_for_fit == 200


# ==================== RegimeDetectionResult.to_dict 測試 ====================

class TestResultSerialization:
    """結果序列化"""

    def test_to_dict_structure(self, simple_price_series):
        """to_dict 應包含必要 keys"""
        detector = RegimeDetector(n_clusters=4, lookback=20, min_samples_for_fit=50)
        result = detector.detect(simple_price_series, expanding=False)
        d = result.to_dict()

        assert "n_clusters" in d
        assert "method" in d
        assert "feature_names" in d
        assert "cluster_stats" in d
        assert d["method"] == "kmeans"
