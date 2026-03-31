"""
驗證 ConfigManager.preview_feature_count 各分類的估算是否與
引擎實際輸出的特徵數一致。

涵蓋場景：
- entropy 單獨啟用
- microstructure 單獨啟用
- tail_risk 單獨啟用
- 變更 windows 參數
- entropy apply_to 不同來源組合
- 全部進階引擎同時啟用
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.atomic.entropy_indicators import EntropyIndicatorEngine
from momentum.FeatureEngineering.atomic.microstructure_indicators import MicrostructureIndicatorEngine
from momentum.FeatureEngineering.atomic.tail_risk_indicators import TailRiskIndicatorEngine
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.feature_config import (
    EntropyConfig,
    MicrostructureConfig,
    TailRiskConfig,
)


# ─── 共用工具 ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sample_df() -> pd.DataFrame:
    """300 根 K 線合成資料，包含所有欄位。"""
    np.random.seed(42)
    n = 300
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    return pd.DataFrame({
        "open_time":        (pd.date_range("2023-01-01", periods=n, freq="12h").astype("int64") // 10**6),
        "open":             close * (1 + np.random.randn(n) * 0.001),
        "high":             close * (1 + np.abs(np.random.randn(n)) * 0.005),
        "low":              close * (1 - np.abs(np.random.randn(n)) * 0.005),
        "close":            close,
        "volume":           np.random.uniform(100, 1000, n),
        "quote_volume":     np.random.uniform(10_000, 100_000, n),
        "trades":           np.random.randint(50, 500, n).astype(float),
        "taker_buy_volume": np.random.uniform(50, 500, n),
        "taker_ratio":      np.random.uniform(0.3, 0.7, n),
        "close_time":       (pd.date_range("2023-01-01", periods=n, freq="12h").astype("int64") // 10**6 + 1000),
    })


def _run_entropy(cfg: EntropyConfig, df: pd.DataFrame) -> int:
    engine = EntropyIndicatorEngine(cfg.model_dump(), list(cfg.apply_to))
    return engine.compute_all(df).shape[1]


def _run_microstructure(cfg: MicrostructureConfig, df: pd.DataFrame) -> int:
    d = cfg.model_dump()
    d["enabled_features"] = "all"
    sources = ["close", "volume", "taker_ratio", "quote_volume", "trades", "taker_buy_volume"]
    engine = MicrostructureIndicatorEngine(d, sources)
    return engine.compute_all(df).shape[1]


def _run_tail_risk(cfg: TailRiskConfig, df: pd.DataFrame) -> int:
    d = cfg.model_dump()
    d["enabled_features"] = "all"
    engine = TailRiskIndicatorEngine(d, ["close"])
    return engine.compute_all(df).shape[1]


_mgr = ConfigManager.__new__(ConfigManager)


# ─── Entropy 引擎測試 ────────────────────────────────────────────────────────

class TestEntropyEstimate:
    """_estimate_entropy_features 與實際引擎輸出的一致性。"""

    def test_default_config(self, sample_df):
        """預設設定（3 sources × 3 shannon windows + 其他）= 21。"""
        cfg = EntropyConfig()
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_close_return_only(self, sample_df):
        """只用 close_return：shannon 3 + apen 2 + sampen 2 + hurst 3 + fractal 2 + perm 3 = 15。"""
        cfg = EntropyConfig(apply_to=["close_return"])
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_two_sources(self, sample_df):
        """close_return + volume：shannon 6 + 其他 13 = 19。"""
        cfg = EntropyConfig(apply_to=["close_return", "volume"])
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_three_sources(self, sample_df):
        """close_return + volume + taker_ratio：估算 = 實際。"""
        cfg = EntropyConfig(apply_to=["close_return", "volume", "taker_ratio"])
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_custom_windows(self, sample_df):
        """縮小 windows，驗證公式隨 windows 線性縮放。"""
        cfg = EntropyConfig(
            apply_to=["close_return"],
            shannon_windows=[21],
            windows=[55],
            hurst_windows=[100, 200],
            perm_windows=[21],
        )
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_expanded_windows(self, sample_df):
        """擴大 windows 清單，驗證估算也跟著增長。"""
        cfg = EntropyConfig(
            apply_to=["close_return"],
            shannon_windows=[10, 21, 55, 100],
            windows=[21, 55, 100],
            hurst_windows=[55, 100, 200],
            perm_windows=[10, 21, 55],
        )
        estimated = _mgr._estimate_entropy_features(cfg)
        actual = _run_entropy(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"


# ─── Microstructure 引擎測試 ────────────────────────────────────────────────

class TestMicrostructureEstimate:
    """_estimate_microstructure_features 與實際引擎輸出的一致性。"""

    def test_default_config(self, sample_df):
        """預設設定：estimate = actual。"""
        cfg = MicrostructureConfig()
        estimated = _mgr._estimate_microstructure_features(cfg)
        actual = _run_microstructure(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_fewer_windows(self, sample_df):
        """縮減 windows 清單，驗證公式線性縮放。"""
        cfg = MicrostructureConfig(
            windows=[5, 13],
            kyle_lambda_windows=[5, 13],
            cs_spread_smooth=[5],
            vpin_n_buckets=[30],
            vpin_zscore_windows=[21],
        )
        estimated = _mgr._estimate_microstructure_features(cfg)
        actual = _run_microstructure(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_more_windows(self, sample_df):
        """增加 windows 清單，驗證估算跟著增加。"""
        cfg = MicrostructureConfig(
            windows=[5, 13, 21, 55],
            kyle_lambda_windows=[5, 13, 21, 55],
            cs_spread_smooth=[5, 13, 21],
            vpin_n_buckets=[30, 50, 100],
            vpin_zscore_windows=[21, 55],
        )
        estimated = _mgr._estimate_microstructure_features(cfg)
        actual = _run_microstructure(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"


# ─── Tail Risk 引擎測試 ──────────────────────────────────────────────────────

class TestTailRiskEstimate:
    """_estimate_tail_risk_features 與實際引擎輸出的一致性。"""

    def test_default_config(self, sample_df):
        """預設設定：estimate = actual。"""
        cfg = TailRiskConfig()
        estimated = _mgr._estimate_tail_risk_features(cfg)
        actual = _run_tail_risk(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_custom_windows(self, sample_df):
        """縮減 windows 與 alpha 清單。"""
        cfg = TailRiskConfig(
            windows=[21, 55],
            cvar_alphas=[0.05],
            rv_windows=[13, 21],
            mdd_windows=[21, 55],
        )
        estimated = _mgr._estimate_tail_risk_features(cfg)
        actual = _run_tail_risk(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"

    def test_single_alpha_single_window(self, sample_df):
        """最小設定：1 alpha × 1 window，驗證邊界。"""
        cfg = TailRiskConfig(
            windows=[21],
            cvar_alphas=[0.01],
            rv_windows=[13],
            mdd_windows=[21],
        )
        estimated = _mgr._estimate_tail_risk_features(cfg)
        actual = _run_tail_risk(cfg, sample_df)
        assert estimated == actual, f"estimated={estimated}, actual={actual}"


# ─── preview_feature_count 端到端測試 ───────────────────────────────────────

class TestPreviewFeatureCountE2E:
    """
    ConfigManager.preview_feature_count 整合測試：
    啟用各種引擎組合，驗證 breakdown 中對應分類的估算值。
    """

    def _mgr_with_config(self, override: dict):
        mgr = ConfigManager()
        return mgr.get_merged_config(override)

    def test_only_entropy_enabled(self, sample_df):
        """只啟用 entropy，其他全部關閉。preview breakdown['entropy'] == actual。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False},
                "momentum": {"enabled": False},
                "volatility": {"enabled": False},
                "volume": {"enabled": False},
                "cycle": {"enabled": False},
                "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "microstructure": {"enabled": False},
                "tail_risk": {"enabled": False},
                "entropy": {
                    "enabled": True,
                    "apply_to": ["close_return", "volume", "taker_ratio"],
                },
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {"binary": {"horizons": []}, "regression": {"horizons": []}},
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        # 從已知預設 EntropyConfig 計算估算
        ent_cfg = cfg.atomic_indicators.entropy
        expected_entropy = _mgr._estimate_entropy_features(ent_cfg)
        assert preview.breakdown["entropy"] == expected_entropy, (
            f"entropy breakdown={preview.breakdown['entropy']}, expected={expected_entropy}"
        )

        # 實際引擎輸出
        actual = _run_entropy(ent_cfg, sample_df)
        assert preview.breakdown["entropy"] == actual, (
            f"entropy preview={preview.breakdown['entropy']}, actual={actual}"
        )

    def test_only_microstructure_enabled(self, sample_df):
        """只啟用 microstructure。preview breakdown['microstructure'] == actual。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False}, "momentum": {"enabled": False},
                "volatility": {"enabled": False}, "volume": {"enabled": False},
                "cycle": {"enabled": False}, "pattern": {"enabled": False},
                "statistics": {"enabled": False}, "entropy": {"enabled": False},
                "tail_risk": {"enabled": False},
                "microstructure": {"enabled": True},
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {"binary": {"horizons": []}, "regression": {"horizons": []}},
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        ms_cfg = cfg.atomic_indicators.microstructure
        expected = _mgr._estimate_microstructure_features(ms_cfg)
        assert preview.breakdown["microstructure"] == expected

        actual = _run_microstructure(ms_cfg, sample_df)
        assert preview.breakdown["microstructure"] == actual, (
            f"microstructure preview={preview.breakdown['microstructure']}, actual={actual}"
        )

    def test_only_tail_risk_enabled(self, sample_df):
        """只啟用 tail_risk。preview breakdown['tail_risk'] == actual。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False}, "momentum": {"enabled": False},
                "volatility": {"enabled": False}, "volume": {"enabled": False},
                "cycle": {"enabled": False}, "pattern": {"enabled": False},
                "statistics": {"enabled": False}, "entropy": {"enabled": False},
                "microstructure": {"enabled": False},
                "tail_risk": {"enabled": True},
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {"binary": {"horizons": []}, "regression": {"horizons": []}},
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        tr_cfg = cfg.atomic_indicators.tail_risk
        expected = _mgr._estimate_tail_risk_features(tr_cfg)
        assert preview.breakdown["tail_risk"] == expected

        actual = _run_tail_risk(tr_cfg, sample_df)
        assert preview.breakdown["tail_risk"] == actual, (
            f"tail_risk preview={preview.breakdown['tail_risk']}, actual={actual}"
        )

    def test_all_three_advanced_engines(self, sample_df):
        """同時啟用全部三個進階引擎，total == sum of three engines。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False}, "momentum": {"enabled": False},
                "volatility": {"enabled": False}, "volume": {"enabled": False},
                "cycle": {"enabled": False}, "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "entropy": {"enabled": True, "apply_to": ["close_return", "volume", "taker_ratio"]},
                "microstructure": {"enabled": True},
                "tail_risk": {"enabled": True},
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {"binary": {"horizons": []}, "regression": {"horizons": []}},
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        actual_ent = _run_entropy(cfg.atomic_indicators.entropy, sample_df)
        actual_ms  = _run_microstructure(cfg.atomic_indicators.microstructure, sample_df)
        actual_tr  = _run_tail_risk(cfg.atomic_indicators.tail_risk, sample_df)
        actual_total = actual_ent + actual_ms + actual_tr

        assert preview.total_features == actual_total, (
            f"preview total={preview.total_features}, actual={actual_total} "
            f"(ent={actual_ent}, ms={actual_ms}, tr={actual_tr})"
        )

    def test_labels_only(self):
        """只啟用 labels，驗證 label 計數。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False}, "momentum": {"enabled": False},
                "volatility": {"enabled": False}, "volume": {"enabled": False},
                "cycle": {"enabled": False}, "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "entropy": {"enabled": False},
                "microstructure": {"enabled": False},
                "tail_risk": {"enabled": False},
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {
                "binary": {"horizons": [1, 3, 7]},
                "regression": {"horizons": [1, 3]},
            },
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        # 3 binary horizons + 2 regression horizons = 5
        assert preview.breakdown["labels"] == 5, (
            f"expected labels=5, got {preview.breakdown['labels']}"
        )
        # labels are Y targets, not X features — must NOT inflate total_features
        assert preview.total_features == 0, (
            f"expected total_features=0 (labels excluded), got {preview.total_features}"
        )

    def test_entropy_with_custom_windows_e2e(self, sample_df):
        """自訂 entropy windows：只有 1 個 shannon_window + 1 個 hurst_window。"""
        override = {
            "atomic_indicators": {
                "trend": {"enabled": False}, "momentum": {"enabled": False},
                "volatility": {"enabled": False}, "volume": {"enabled": False},
                "cycle": {"enabled": False}, "pattern": {"enabled": False},
                "statistics": {"enabled": False},
                "microstructure": {"enabled": False},
                "tail_risk": {"enabled": False},
                "entropy": {
                    "enabled": True,
                    "apply_to": ["close_return"],
                    "shannon_windows": [21],
                    "windows": [55],
                    "hurst_windows": [100],
                    "perm_windows": [21],
                },
            },
            "operators": {"distance": {"enabled": False}, "cross": {"enabled": False},
                          "momentum": {"enabled": False}, "ratio": {"enabled": False},
                          "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features": {"enabled": False},
            "meta_features": {"enabled": False},
            "cross_sectional": {"enabled": False},
            "labels": {"binary": {"horizons": []}, "regression": {"horizons": []}},
            "preprocessing": {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)

        actual = _run_entropy(cfg.atomic_indicators.entropy, sample_df)
        assert preview.breakdown["entropy"] == actual, (
            f"entropy preview={preview.breakdown['entropy']}, actual={actual}"
        )


# ─── L1 TA-Lib categories: Trend（精確可測） ────────────────────────────────

class TestL1TrendEstimate:
    """
    L1 原始技術指標（TA-Lib 類別）估算精確度測試。

    覆蓋：
      - 單數據源 vs 多數據源（single_series_factor 縮放）
      - 不同 periods 展開
      - category 關閉給 0

    ⚠️ 只測 trend 中的 EMA/SMA（純 TA-Lib 單輸入指標）。
       volume 類別因引擎有硬編碼 _compute_vwap 等固定特徵，
       count 與估算 config param 展開不一致，屬設計限制，不在此測試。
    """

    _DISABLE_ALL_EXCEPT_TREND = {
        "atomic_indicators": {
            "momentum":       {"enabled": False},
            "volatility":     {"enabled": False},
            "volume":         {"enabled": False},
            "cycle":          {"enabled": False},
            "pattern":        {"enabled": False},
            "statistics":     {"enabled": False},
            "microstructure": {"enabled": False},
            "entropy":        {"enabled": False},
            "tail_risk":      {"enabled": False},
        },
        "operators":        {"distance": {"enabled": False}, "cross": {"enabled": False},
                             "momentum": {"enabled": False}, "ratio": {"enabled": False},
                             "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
        "rolling_aggregation": {"enabled": False},
        "lag_features":     {"enabled": False},
        "meta_features":    {"enabled": False},
        "cross_sectional":  {"enabled": False},
        "labels":           {"binary": {"horizons": []}, "regression": {"horizons": []}},
        "preprocessing":    {"enabled": False},
    }

    @pytest.fixture(scope="class")
    def large_df(self) -> pd.DataFrame:
        """500 根合成 K 線，確保 TA-Lib 指標有充足資料。"""
        np.random.seed(1)
        n = 500
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        return pd.DataFrame({
            "open":      close * (1 + np.random.randn(n) * 0.002),
            "high":      close * (1 + np.abs(np.random.randn(n)) * 0.005),
            "low":       close * (1 - np.abs(np.random.randn(n)) * 0.005),
            "close":     close,
            "volume":    np.random.uniform(100, 1000, n),
            "open_time": np.arange(n, dtype=float) * 1000,
        })

    def _build_override(self, indicators: list, sources: list) -> dict:
        from copy import deepcopy
        override = deepcopy(self._DISABLE_ALL_EXCEPT_TREND)
        override["data_sources"] = {"enabled_sources": sources}
        override["atomic_indicators"]["trend"] = {
            "enabled": True,
            "indicators": indicators,
        }
        return override

    def test_ema_single_source(self, large_df):
        """EMA × 2 periods × 1 source = 2 estimated = 2 actual。"""
        indicators = [{"name": "EMA", "enabled": True, "periods": [21, 55]}]
        override = self._build_override(indicators, ["close"])
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        config_dict = cfg.model_dump(by_alias=True)

        estimated = mgr._estimate_atomic_counts(config_dict)["trend"]

        from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
        engine = TrendIndicatorEngine(config_dict["atomic_indicators"]["trend"], ["close"])
        actual = engine.compute_all(large_df).shape[1]

        assert estimated == actual, f"estimate={estimated}, actual={actual}"

    def test_ema_two_sources_doubles_count(self, large_df):
        """EMA × 2 periods × 2 sources → single_series_factor=2，count 翻倍。"""
        indicators = [{"name": "EMA", "enabled": True, "periods": [21, 55]}]
        override_1src = self._build_override(indicators, ["close"])
        override_2src = self._build_override(indicators, ["close", "volume"])

        mgr = ConfigManager()
        cfg_1 = mgr.get_merged_config(override_1src)
        cfg_2 = mgr.get_merged_config(override_2src)

        est_1 = mgr._estimate_atomic_counts(cfg_1.model_dump(by_alias=True))["trend"]
        est_2 = mgr._estimate_atomic_counts(cfg_2.model_dump(by_alias=True))["trend"]

        assert est_2 == 2 * est_1, f"2-source should be 2× 1-source: {est_2} vs {est_1}"
        # 驗證 est_2 也與實際引擎一致
        from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
        cfg2_dict = cfg_2.model_dump(by_alias=True)
        engine = TrendIndicatorEngine(
            cfg2_dict["atomic_indicators"]["trend"], ["close", "volume"]
        )
        actual_2 = engine.compute_all(large_df).shape[1]
        assert est_2 == actual_2, f"estimate={est_2}, actual={actual_2}"

    def test_three_sources_capped_at_two(self, large_df):
        """3 個數據源時 single_series_factor 仍為 2（min(3,2)=2），與 2 源相同。"""
        indicators = [{"name": "SMA", "enabled": True, "periods": [21]}]
        override_2src = self._build_override(indicators, ["close", "volume"])
        override_3src = self._build_override(indicators, ["close", "volume", "taker_ratio"])

        mgr = ConfigManager()
        est_2 = mgr._estimate_atomic_counts(
            mgr.get_merged_config(override_2src).model_dump(by_alias=True)
        )["trend"]
        est_3 = mgr._estimate_atomic_counts(
            mgr.get_merged_config(override_3src).model_dump(by_alias=True)
        )["trend"]

        assert est_2 == est_3, (
            f"3-source should give same estimate as 2-source (capped), "
            f"got 2src={est_2}, 3src={est_3}"
        )

    def test_trend_disabled_gives_zero(self):
        """trend disabled → atomic['trend'] == 0。"""
        override = {
            "data_sources": {"enabled_sources": ["close"]},
            "atomic_indicators": {"trend": {"enabled": False}},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        counts = mgr._estimate_atomic_counts(cfg.model_dump(by_alias=True))
        assert counts.get("trend", 0) == 0

    def test_sma_ema_combined_single_source(self, large_df):
        """SMA(1 period) + EMA(2 periods) + 1 source = 3 features。"""
        indicators = [
            {"name": "EMA", "enabled": True, "periods": [21, 55]},
            {"name": "SMA", "enabled": True, "periods": [21]},
        ]
        override = self._build_override(indicators, ["close"])
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        config_dict = cfg.model_dump(by_alias=True)

        estimated = mgr._estimate_atomic_counts(config_dict)["trend"]

        from momentum.FeatureEngineering.atomic.trend_indicators import TrendIndicatorEngine
        engine = TrendIndicatorEngine(config_dict["atomic_indicators"]["trend"], ["close"])
        actual = engine.compute_all(large_df).shape[1]

        assert estimated == actual, f"estimate={estimated}, actual={actual}"

    def test_disabled_indicator_within_trend(self):
        """
        trend 中某個指標 enabled=False，**估算器**應跳過不計入。

        ⚠️ 已知設計限制：TrendIndicatorEngine.compute_all() 本身不檢查 enabled 旗標，
        所以引擎實際輸出會包含 disabled 指標的欄位。
        此測試只驗證 _estimate_atomic_counts 的正確行為（估算=1），
        不對引擎輸出做 assert。
        """
        indicators = [
            {"name": "EMA", "enabled": True,  "periods": [21]},
            {"name": "SMA", "enabled": False, "periods": [21]},
        ]
        override = self._build_override(indicators, ["close"])
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        config_dict = cfg.model_dump(by_alias=True)

        estimated = mgr._estimate_atomic_counts(config_dict)["trend"]
        # 估算器應只算 enabled=True 的 EMA(21) × 1 source = 1
        assert estimated == 1, f"estimate should be 1 (only EMA), got {estimated}"


# ─── L3 Rolling Aggregation（精確可測） ─────────────────────────────────────

class TestL3RollingEstimate:
    """
    L3 Rolling Aggregation 估算精確度。

    公式：n_input_cols × n_enabled_agg × n_windows

    由於 L3 只作用於 L1（不含 L2），此公式在 apply_to='all' 時應精確吻合。
    測試直接對 synthetic L1 DataFrame 跑 RollingAggregator，
    驗證 actual 欄位數 == estimated。
    """

    @pytest.fixture(scope="class")
    def synthetic_l1(self) -> pd.DataFrame:
        """10 個合成 L1 特徵欄位（模擬 TA-Lib 輸出）。"""
        np.random.seed(2)
        n, k = 300, 10
        return pd.DataFrame(
            np.random.randn(n, k),
            columns=[f"close_trend_EMA_{p}" for p in range(k)],
        )

    def _build_rolling_cfg(self, agg_names: list, windows: list) -> dict:
        """
        傳給 RollingAggregator 的格式：aggregators 為 **list of names**。
        （FeatureFactory._filter_rolling_config 在呼叫 RollingAggregator 前
        已把 dict format 轉換成 list，此處直接傳 list 以符合引擎期望。）
        _estimate_rolling_count 同樣接受 list format，兩者結果一致。
        """
        return {
            "enabled": True,
            "windows": windows,
            "aggregators": agg_names,  # list of enabled agg names
            "apply_to": "all",
        }

    def _run_rolling(self, l1_df: pd.DataFrame, cfg: dict) -> int:
        from momentum.FeatureEngineering.operators.rolling_aggregator import RollingAggregator
        agg = RollingAggregator(cfg)
        return agg.compute_all(l1_df).shape[1]

    def test_2agg_2windows(self, synthetic_l1):
        """2 agg × 2 windows = 4 per input col（10 cols → 40）。"""
        n_cols = synthetic_l1.shape[1]  # 10
        cfg = self._build_rolling_cfg(["mean", "std"], [5, 13])
        estimated = _mgr._estimate_rolling_count(n_cols, cfg)
        actual = self._run_rolling(synthetic_l1, cfg)
        assert estimated == actual, f"estimate={estimated}, actual={actual}"
        assert actual == n_cols * 2 * 2

    def test_1agg_3windows(self, synthetic_l1):
        """1 agg × 3 windows = 3 per input col（10 cols → 30）。"""
        n_cols = synthetic_l1.shape[1]
        cfg = self._build_rolling_cfg(["rank"], [5, 13, 21])
        estimated = _mgr._estimate_rolling_count(n_cols, cfg)
        actual = self._run_rolling(synthetic_l1, cfg)
        assert estimated == actual, f"estimate={estimated}, actual={actual}"

    def test_all_agg_single_window(self, synthetic_l1):
        """所有 10 agg × 1 window（5 cols → 50）。"""
        all_aggs = ["slope", "std", "mean", "rank", "zscore", "skew", "kurt", "min", "max", "range"]
        n_cols = 5
        l1_sub = synthetic_l1.iloc[:, :n_cols]
        cfg = self._build_rolling_cfg(all_aggs, [21])
        estimated = _mgr._estimate_rolling_count(n_cols, cfg)
        actual = self._run_rolling(l1_sub, cfg)
        assert estimated == actual, f"estimate={estimated}, actual={actual}"

    def test_rolling_disabled_gives_zero(self, synthetic_l1):
        """rolling disabled → 0。"""
        cfg = {"enabled": False, "windows": [5, 13], "aggregators": {"mean": {"enabled": True}}}
        estimated = _mgr._estimate_rolling_count(synthetic_l1.shape[1], cfg)
        actual = self._run_rolling(synthetic_l1, cfg)
        assert estimated == 0
        assert actual == 0

    def test_more_windows_scales_linearly(self, synthetic_l1):
        """windows 翻倍 → count 翻倍（線性縮放驗證）。"""
        n_cols = synthetic_l1.shape[1]
        cfg_2w = self._build_rolling_cfg(["mean", "std"], [5, 13])
        cfg_4w = self._build_rolling_cfg(["mean", "std"], [5, 13, 21, 55])
        est_2w = _mgr._estimate_rolling_count(n_cols, cfg_2w)
        est_4w = _mgr._estimate_rolling_count(n_cols, cfg_4w)
        actual_2w = self._run_rolling(synthetic_l1, cfg_2w)
        actual_4w = self._run_rolling(synthetic_l1, cfg_4w)
        assert est_4w == 2 * est_2w, f"4w={est_4w} should be 2× 2w={est_2w}"
        assert actual_4w == actual_2w * 2, f"actual 4w={actual_4w} should be 2× {actual_2w}"
        assert est_4w == actual_4w


# ─── Labels 估算（精確可測） ─────────────────────────────────────────────────

class TestLabelsEstimate:
    """
    Labels 計數精確度測試。

    _estimate_label_count = len(binary.horizons) + len(regression.horizons)
    LabelGenerator.generate_all 的實際輸出欄位數應完全吻合。
    """

    @pytest.fixture(scope="class")
    def close_series(self) -> "pd.Series":
        np.random.seed(3)
        return pd.Series(100 + np.cumsum(np.random.randn(300) * 0.5), name="close")

    def _run_labels(self, cfg: dict, close) -> int:
        from momentum.FeatureEngineering.labels.label_generator import LabelGenerator
        gen = LabelGenerator(cfg)
        return gen.generate_all(close).shape[1]

    def test_default_horizons(self, close_series):
        """預設 horizons binary=[3,5,8,13,21] + regression=[5,13] = 7 labels。"""
        labels_cfg = {
            "binary":     {"horizons": [3, 5, 8, 13, 21]},
            "regression": {"horizons": [5, 13]},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 7

    def test_binary_only(self, close_series):
        """只有 binary labels。"""
        labels_cfg = {
            "binary":     {"horizons": [1, 3, 7]},
            "regression": {"horizons": []},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 3

    def test_regression_only(self, close_series):
        """只有 regression labels。"""
        labels_cfg = {
            "binary":     {"horizons": []},
            "regression": {"horizons": [5, 13, 21]},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 3

    def test_single_label(self, close_series):
        """最簡單：1 binary + 1 regression = 2。"""
        labels_cfg = {
            "binary":     {"horizons": [5]},
            "regression": {"horizons": [13]},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 2

    def test_zero_labels(self, close_series):
        """horizons 全空 → 0 labels。"""
        labels_cfg = {
            "binary":     {"horizons": []},
            "regression": {"horizons": []},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 0

    def test_many_horizons(self, close_series):
        """大量 horizons。"""
        b_horizons = [1, 2, 3, 5, 8, 13, 21, 34]   # 8
        r_horizons = [3, 5, 8, 13, 21]               # 5
        labels_cfg = {
            "binary":     {"horizons": b_horizons},
            "regression": {"horizons": r_horizons},
        }
        estimated = _mgr._estimate_label_count(labels_cfg)
        actual = self._run_labels(labels_cfg, close_series)
        assert estimated == actual == 13

    def test_label_count_in_e2e_preview(self):
        """end-to-end：只啟用 labels，preview.breakdown['labels'] 與實際一致。"""
        override = {
            "atomic_indicators": {
                cat: {"enabled": False}
                for cat in ["trend", "momentum", "volatility", "volume",
                            "cycle", "pattern", "statistics",
                            "entropy", "microstructure", "tail_risk"]
            },
            "operators":        {"distance": {"enabled": False}, "cross": {"enabled": False},
                                 "momentum": {"enabled": False}, "ratio": {"enabled": False},
                                 "binary_signal": {"enabled": False}, "worldquant": {"enabled": False}},
            "rolling_aggregation": {"enabled": False},
            "lag_features":     {"enabled": False},
            "meta_features":    {"enabled": False},
            "cross_sectional":  {"enabled": False},
            "labels":           {"binary": {"horizons": [3, 7]}, "regression": {"horizons": [5]}},
            "preprocessing":    {"enabled": False},
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)
        assert preview.breakdown["labels"] == 3
        # labels are Y targets, NOT X features — excluded from total_features
        assert preview.total_features == 0, (
            f"expected total_features=0 (labels excluded), got {preview.total_features}"
        )


# ─── L5 Cross-Sectional（精確可測） ─────────────────────────────────────────

class TestL5CrossSectionalEstimate:
    """
    L5 截面標準化特徵計數測試。

    估算邏輯：計算 cross_sectional.features 中 enabled=True 的項目數。
    不需要跑引擎（引擎需要多標的資料），直接驗證計數公式。
    """

    def test_disabled_gives_zero(self):
        """cross_sectional disabled → cross_sectional count = 0。"""
        override = {"cross_sectional": {"enabled": False}}
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)
        assert preview.breakdown["cross_sectional"] == 0

    def test_all_three_features_enabled(self):
        """3 個 features 全部 enabled → count = 3。"""
        override = {
            "cross_sectional": {
                "enabled": True,
                "reference_symbol": "BTCUSDT",
                "features": {
                    "relative_price":        {"enabled": True},
                    "beta":                  {"enabled": True},
                    "idiosyncratic_momentum":{"enabled": True},
                },
            }
        }
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        count = _mgr._estimate_cross_count(cfg.model_dump(by_alias=True)["cross_sectional"])
        assert count == 3

    def test_one_feature_enabled(self):
        """只啟用 relative_price → count = 1。"""
        cross_cfg = {
            "enabled": True,
            "features": {
                "relative_price":         {"enabled": True},
                "beta":                   {"enabled": False},
                "idiosyncratic_momentum": {"enabled": False},
            },
        }
        count = _mgr._estimate_cross_count(cross_cfg)
        assert count == 1

    def test_two_features_enabled(self):
        """啟用 2 個 → count = 2。"""
        cross_cfg = {
            "enabled": True,
            "features": {
                "relative_price":         {"enabled": True},
                "beta":                   {"enabled": True},
                "idiosyncratic_momentum": {"enabled": False},
            },
        }
        count = _mgr._estimate_cross_count(cross_cfg)
        assert count == 2


# ─── L2 Derived（近似：單調性測試） ─────────────────────────────────────────

class TestL2DerivedMonotonicity:
    """
    L2 衍生運算元特徵估算「單調性」測試。

    設計上為近似值（ atomic × 0.15 × N_operators），無法精確對比引擎輸出。
    驗證：disabled=0、增加 operator 數量→估算值增加。
    derived = 對 L1 特徵做的數學運算組合（distance/cross/momentum/ratio 等六種）。
    """

    _BASE_ATOMIC = 100  # 假設 L1 有 100 個特徵

    def test_all_operators_disabled_gives_zero(self):
        """所有 operators disabled → derived == 0。"""
        ops_cfg = {k: {"enabled": False}
                   for k in ["distance", "cross", "momentum", "ratio", "binary_signal", "worldquant"]}
        count = _mgr._estimate_derived_count(self._BASE_ATOMIC, {}, ops_cfg)
        assert count == 0

    def test_one_operator_enabled_gives_positive(self):
        """啟用 1 個 operator → derived > 0。"""
        ops_cfg = {
            "distance":     {"enabled": True},
            "cross":        {"enabled": False},
            "momentum":     {"enabled": False},
            "ratio":        {"enabled": False},
            "binary_signal":{"enabled": False},
            "worldquant":   {"enabled": False},
        }
        count = _mgr._estimate_derived_count(self._BASE_ATOMIC, {}, ops_cfg)
        assert count > 0

    def test_more_operators_gives_more_features(self):
        """4 個 operators > 2 個 operators > 0。"""
        def count_with_n_ops(n: int) -> int:
            op_keys = ["distance", "cross", "momentum", "ratio"]
            cfg = {k: {"enabled": (i < n)} for i, k in enumerate(op_keys)}
            cfg.update({"binary_signal": {"enabled": False}, "worldquant": {"enabled": False}})
            return _mgr._estimate_derived_count(self._BASE_ATOMIC, {}, cfg)

        c0 = count_with_n_ops(0)
        c2 = count_with_n_ops(2)
        c4 = count_with_n_ops(4)
        assert c0 == 0
        assert c2 > 0
        assert c4 > c2

    def test_derived_scales_with_atomic_count(self):
        """atomic 翻倍 → derived 也翻倍（線性比例）。"""
        ops_cfg = {
            "distance": {"enabled": True},
            "cross":    {"enabled": True},
            "momentum": {"enabled": False},
            "ratio":    {"enabled": False},
            "binary_signal": {"enabled": False},
            "worldquant": {"enabled": False},
        }
        c100 = _mgr._estimate_derived_count(100, {}, ops_cfg)
        c200 = _mgr._estimate_derived_count(200, {}, ops_cfg)
        assert c200 == 2 * c100, f"200 atoms: {c200}, 100 atoms: {c100}"

    def test_binary_signal_rules_counted(self):
        """binary_signal 啟用且有 rules → rules 數量加入計數。"""
        ops_cfg = {
            "distance": {"enabled": False},
            "cross":    {"enabled": False},
            "momentum": {"enabled": False},
            "ratio":    {"enabled": False},
            "binary_signal": {
                "enabled": True,
                "rules": [
                    {"name": "rule1", "enabled": True},
                    {"name": "rule2", "enabled": True},
                    {"name": "rule3", "enabled": False},
                ],
            },
            "worldquant": {"enabled": False},
        }
        count = _mgr._estimate_derived_count(self._BASE_ATOMIC, {}, ops_cfg)
        # 只有 2 個 enabled rules
        assert count == 2


# ─── L4 Lag（近似：單調性 + 策略切換） ──────────────────────────────────────

class TestL4LagMonotonicity:
    """
    L4 Lag 特徵估算「方向性」測試。

    設計限制：估算只用 atomic_total × lags_per_feature，
    實際引擎對 raw_data + L1 + L2 + L3 全部做 lag，所以估算是 L1 部分的近似。
    驗證：disabled=0、dense > adaptive、custom 依 len(custom_lags) 縮放。
    """

    def test_lag_disabled_gives_zero(self):
        """lag disabled → breakdown['lag'] == 0。"""
        override = {"lag_features": {"enabled": False}}
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)
        assert preview.breakdown["lag"] == 0

    def test_dense_more_than_adaptive(self):
        """dense 策略（5 lags/feature）> adaptive（3 lags/feature）。"""
        mgr = ConfigManager()
        cfg_adaptive = mgr.get_merged_config({
            "lag_features": {"enabled": True},
            "global": {"lag_strategy": "adaptive"},
        })
        cfg_dense = mgr.get_merged_config({
            "lag_features": {"enabled": True},
            "global": {"lag_strategy": "dense"},
        })
        lag_adaptive = mgr.preview_feature_count(cfg_adaptive).breakdown["lag"]
        lag_dense    = mgr.preview_feature_count(cfg_dense).breakdown["lag"]
        assert lag_dense > lag_adaptive, (
            f"dense={lag_dense} should > adaptive={lag_adaptive}"
        )

    def test_custom_lags_scales_by_length(self):
        """custom_lags=[1,2,3] (3 lags) vs custom_lags=[1,2,3,5,8] (5 lags)：比例吻合。"""
        mgr = ConfigManager()

        # 用相同的 atomic 設定，只變 custom_lags 長度
        base_override = {
            "lag_features": {"enabled": True},
            "global": {"lag_strategy": "custom"},
        }
        override_3 = {**base_override, "global": {"lag_strategy": "custom", "custom_lags": [1, 2, 3]}}
        override_5 = {**base_override, "global": {"lag_strategy": "custom", "custom_lags": [1, 2, 3, 5, 8]}}

        lag_3 = mgr.preview_feature_count(mgr.get_merged_config(override_3)).breakdown["lag"]
        lag_5 = mgr.preview_feature_count(mgr.get_merged_config(override_5)).breakdown["lag"]

        # 5 lags / 3 lags ≈ 5/3，可接受誤差範圍（整數截斷）
        ratio = lag_5 / lag_3
        assert abs(ratio - 5 / 3) < 0.1, (
            f"5 lags / 3 lags ratio={ratio:.3f}, expected≈{5/3:.3f}\n"
            f"lag_3={lag_3}, lag_5={lag_5}"
        )


# ─── L6 Meta features（近似：單調性） ───────────────────────────────────────

class TestL6MetaMonotonicity:
    """
    L6 Meta Features 估算「單調性」測試。

    公式：n_enabled_sub_engines × 3（近似，每個 sub-engine 輸出不恰好 3 個）。
    驗證：disabled=0、啟用越多 sub-engines → count 越高（單調遞增）。
    """

    _SUB_ENGINES = [
        "consensus", "interaction", "time_features", "trend_consensus",
        "momentum_divergence", "volume_price_divergence", "volatility_regime",
    ]

    def test_meta_disabled_gives_zero(self):
        """meta_features disabled → breakdown['meta'] == 0。"""
        override = {"meta_features": {"enabled": False}}
        mgr = ConfigManager()
        cfg = mgr.get_merged_config(override)
        preview = mgr.preview_feature_count(cfg)
        assert preview.breakdown["meta"] == 0

    def test_all_sub_engines_enabled(self):
        """所有 7 個 sub-engine 啟用 → meta = 7 × 3 = 21。"""
        meta_cfg = {"enabled": True, **{k: True for k in self._SUB_ENGINES}}
        count = _mgr._estimate_meta_count(meta_cfg)
        assert count == 7 * 3

    def test_one_sub_engine_gives_3(self):
        """啟用 1 個 sub-engine → meta = 3。"""
        meta_cfg = {"enabled": True, **{k: False for k in self._SUB_ENGINES}}
        meta_cfg["trend_consensus"] = True
        count = _mgr._estimate_meta_count(meta_cfg)
        assert count == 3

    def test_more_sub_engines_more_features(self):
        """啟用 N 個 sub-engines > 啟用 N-1 個（單調遞增）。"""
        counts = []
        for n in range(1, len(self._SUB_ENGINES) + 1):
            meta_cfg = {"enabled": True}
            for i, k in enumerate(self._SUB_ENGINES):
                meta_cfg[k] = (i < n)
            counts.append(_mgr._estimate_meta_count(meta_cfg))

        for i in range(1, len(counts)):
            assert counts[i] > counts[i - 1], (
                f"count[{i}]={counts[i]} should > count[{i-1}]={counts[i-1]}"
            )
