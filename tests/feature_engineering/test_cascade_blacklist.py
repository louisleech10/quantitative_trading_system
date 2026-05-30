"""Cascade categorical blacklist 單元 + 邊界 + 契約測試。

對應 docs/NAN_REDUCTION_STRATEGY.md §5.1 與 PLAN §1.5。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from momentum.FeatureEngineering.utils.cascade_blacklist import (
    CDL_PATTERN_NAMES,
    expand_blacklist_patterns,
    strip_blacklisted,
)


# ─── CDL_PATTERN_NAMES 結構契約 ───────────────────────────────


class TestCDLPatternNames:
    def test_has_exactly_61_patterns(self) -> None:
        # TA-Lib 61 個 CDL pattern（與 scan_config.yaml pattern 段一致）
        assert len(CDL_PATTERN_NAMES) == 61

    def test_is_frozenset(self) -> None:
        assert isinstance(CDL_PATTERN_NAMES, frozenset)

    def test_all_start_with_CDL(self) -> None:
        for name in CDL_PATTERN_NAMES:
            assert name.startswith("CDL"), f"{name!r} should start with 'CDL'"

    def test_includes_known_patterns(self) -> None:
        # 哨兵：必含這些
        for sentinel in ("CDLDOJI", "CDLHAMMER", "CDL3LINESTRIKE", "CDLENGULFING"):
            assert sentinel in CDL_PATTERN_NAMES


# ─── expand_blacklist_patterns ─────────────────────────────────


class TestExpandBlacklist:
    def test_CDL_PATTERN_ALL_matches_all_cdl_columns(self) -> None:
        cols = [
            "close_CDLDOJI_1h",
            "close_CDLHAMMER_12h",
            "close_CDL3LINESTRIKE_1h",
            "close_EMA_20_1h",
            "close_RSI_14_1h",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert "close_CDLDOJI_1h" in matched
        assert "close_CDLHAMMER_12h" in matched
        assert "close_CDL3LINESTRIKE_1h" in matched
        assert "close_EMA_20_1h" not in matched
        assert "close_RSI_14_1h" not in matched

    def test_HT_DCPHASE_matches_all_variants(self) -> None:
        # 真實命名用 hyphen：close_12h_cycle_HT-DCPHASE
        cols = [
            "close_1h_cycle_HT-DCPHASE",
            "close_12h_cycle_HT-DCPHASE",
            "close_12h_cycle_HT-DCPERIOD",  # 不應命中
            "close_12h_cycle_HT-TRENDMODE",
            "close_12h_cycle_HT-SINE-LeadSine",
        ]
        matched = expand_blacklist_patterns(["HT-DCPHASE"], cols)
        assert "close_1h_cycle_HT-DCPHASE" in matched
        assert "close_12h_cycle_HT-DCPHASE" in matched
        assert "close_12h_cycle_HT-DCPERIOD" not in matched
        assert "close_12h_cycle_HT-TRENDMODE" not in matched
        assert "close_12h_cycle_HT-SINE-LeadSine" not in matched

    def test_CDL_derived_features_also_match(self) -> None:
        # L2/L3 衍生：CDL_DOJI_Distance_..., rolling_W21_Mean_CDLHAMMER_...
        cols = [
            "close_EMA_20_1h_Distance_CDLDOJI_1h",
            "close_CDLHAMMER_12h_rolling_W21_Mean_1h",
            "close_EMA_20_1h",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert "close_EMA_20_1h_Distance_CDLDOJI_1h" in matched
        assert "close_CDLHAMMER_12h_rolling_W21_Mean_1h" in matched
        assert "close_EMA_20_1h" not in matched

    def test_HT_DCPHASE_derived_features_also_match(self) -> None:
        # 真實衍生命名（catalog 確認）：close_12h_cycle_HT-DCPHASE_Momentum_L3
        cols = [
            "close_12h_cycle_HT-DCPHASE_Momentum_L3",
            "close_12h_cycle_HT-DCPHASE_rolling_W21_Mean",
            "close_12h_trend_EMA_5",
        ]
        matched = expand_blacklist_patterns(["HT-DCPHASE"], cols)
        assert "close_12h_cycle_HT-DCPHASE_Momentum_L3" in matched
        assert "close_12h_cycle_HT-DCPHASE_rolling_W21_Mean" in matched
        assert "close_12h_trend_EMA_5" not in matched

    def test_both_patterns_together(self) -> None:
        cols = [
            "ohlc_12h_pattern_CDLDOJI",
            "close_12h_cycle_HT-DCPHASE",
            "close_12h_trend_EMA_5",
            "close_12h_momentum_RSI_5",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL", "HT-DCPHASE"], cols)
        assert matched == frozenset({
            "ohlc_12h_pattern_CDLDOJI",
            "close_12h_cycle_HT-DCPHASE",
        })

    def test_empty_patterns_returns_empty(self) -> None:
        cols = ["close_CDLDOJI_1h", "close_EMA_20_1h"]
        assert expand_blacklist_patterns([], cols) == frozenset()

    def test_empty_columns_returns_empty(self) -> None:
        assert expand_blacklist_patterns(["CDL_PATTERN_ALL"], []) == frozenset()

    def test_both_empty_returns_empty(self) -> None:
        assert expand_blacklist_patterns([], []) == frozenset()

    def test_custom_substring_pattern(self) -> None:
        # 非 alias 走通用 substring
        cols = ["close_MyIndicator_1h", "close_EMA_20_1h"]
        matched = expand_blacklist_patterns(["_MyIndicator_"], cols)
        assert "close_MyIndicator_1h" in matched
        assert "close_EMA_20_1h" not in matched

    def test_returns_frozenset_of_str(self) -> None:
        cols = ["close_CDLDOJI_1h"]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert isinstance(matched, frozenset)
        for c in matched:
            assert isinstance(c, str)

    def test_skips_empty_string_pattern(self) -> None:
        # 空字串 pattern 應被忽略（避免命中所有欄位）
        cols = ["close_EMA_20_1h", "close_RSI_14_1h"]
        assert expand_blacklist_patterns([""], cols) == frozenset()
        assert expand_blacklist_patterns(["", None], cols) == frozenset()  # type: ignore[list-item]


# ─── strip_blacklisted ───────────────────────────────────────


class TestStripBlacklisted:
    def _mock_df(self) -> pd.DataFrame:
        return pd.DataFrame({
            "ohlc_12h_pattern_CDLDOJI": [0, 100, 0, 0, 0],
            "close_12h_cycle_HT-DCPHASE": [10.0, 50.0, 180.0, 270.0, 359.0],
            "close_12h_trend_EMA_5": [1.0, 1.1, 1.2, 1.3, 1.4],
            "close_12h_momentum_RSI_5": [50.0, 55.0, 60.0, 65.0, 70.0],
        })

    def test_strip_with_explicit_set(self) -> None:
        df = self._mock_df()
        result = strip_blacklisted(df, {"ohlc_12h_pattern_CDLDOJI", "close_12h_cycle_HT-DCPHASE"})
        assert list(result.columns) == ["close_12h_trend_EMA_5", "close_12h_momentum_RSI_5"]

    def test_strip_empty_blacklist_returns_df(self) -> None:
        df = self._mock_df()
        result = strip_blacklisted(df, set())
        assert list(result.columns) == list(df.columns)

    def test_strip_nonexistent_columns_idempotent(self) -> None:
        df = self._mock_df()
        result = strip_blacklisted(df, {"not_in_df"})
        assert list(result.columns) == list(df.columns)

    def test_strip_idempotent(self) -> None:
        df = self._mock_df()
        blacklist = {"ohlc_12h_pattern_CDLDOJI"}
        once = strip_blacklisted(df, blacklist)
        twice = strip_blacklisted(once, blacklist)
        assert list(twice.columns) == list(once.columns)

    def test_strip_preserves_relative_order(self) -> None:
        df = self._mock_df()
        result = strip_blacklisted(df, {"close_12h_cycle_HT-DCPHASE"})
        # 順序保持 input 的相對順序
        assert list(result.columns) == [
            "ohlc_12h_pattern_CDLDOJI",
            "close_12h_trend_EMA_5",
            "close_12h_momentum_RSI_5",
        ]

    def test_strip_all_columns_returns_empty(self) -> None:
        df = self._mock_df()
        result = strip_blacklisted(df, set(df.columns))
        assert len(result.columns) == 0
        assert len(result) == len(df)  # row 數保留

    def test_strip_empty_df(self) -> None:
        result = strip_blacklisted(pd.DataFrame(), {"any"})
        assert result.empty

    def test_strip_does_not_mutate_input(self) -> None:
        df = self._mock_df()
        original_cols = list(df.columns)
        strip_blacklisted(df, {"ohlc_12h_pattern_CDLDOJI"})
        assert list(df.columns) == original_cols


# ─── 安全 invariant 契約 ─────────────────────────────────────


class TestSafetyContract:
    def test_output_columns_subset_of_input(self) -> None:
        """關鍵契約：strip 後欄位 ⊆ input 欄位"""
        np.random.seed(0)
        for _ in range(50):
            n = np.random.randint(1, 30)
            df = pd.DataFrame(
                np.random.randn(10, n),
                columns=[f"col_{i}" if i % 3 else f"close_CDLDOJI_{i}_1h" for i in range(n)],
            )
            input_cols = set(df.columns)
            matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], df.columns)
            result = strip_blacklisted(df, matched)
            assert set(result.columns).issubset(input_cols)

    def test_no_good_features_dropped_by_alias(self) -> None:
        """CDL_PATTERN_ALL 不應命中 EMA / SMA / RSI 等正常指標（真實命名）"""
        cols = [
            "close_12h_trend_EMA_5", "close_1h_trend_EMA_233",
            "close_12h_trend_SMA_50", "close_12h_momentum_RSI_5",
            "close_12h_momentum_MACD-Line_12-26-9", "close_12h_trend_BBANDS-Upper_20-2",
            "close_12h_trend_T3_233-0.7", "close_12h_trend_HT-TRENDLINE",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert matched == frozenset()

    def test_no_good_features_dropped_by_HT_DCPHASE(self) -> None:
        """HT-DCPHASE 不應命中其他 HT 指標（真實 hyphen 命名）"""
        cols = [
            "close_12h_cycle_HT-DCPERIOD", "close_12h_trend_HT-TRENDLINE",
            "close_12h_cycle_HT-TRENDMODE", "close_12h_cycle_HT-SINE-LeadSine",
            "close_12h_cycle_HT-PHASOR-InPhase", "close_12h_cycle_HT-PHASOR-Quadrature",
        ]
        matched = expand_blacklist_patterns(["HT-DCPHASE"], cols)
        assert matched == frozenset()


# ─── 邊界 ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_unicode_column_names(self) -> None:
        cols = ["前綴_CDLDOJI_1h", "正常_EMA_20_1h", "💀_RSI_14_1h"]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert "前綴_CDLDOJI_1h" in matched
        assert "正常_EMA_20_1h" not in matched
        assert "💀_RSI_14_1h" not in matched

    def test_column_name_with_underscores_and_digits(self) -> None:
        cols = ["xxx_CDLDOJI_1h_W21", "y_z_CDL2CROWS_99_1h"]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert matched == frozenset(cols)

    def test_strip_preserves_index(self) -> None:
        df = pd.DataFrame(
            {"close_CDLDOJI_1h": [1, 2, 3], "close_EMA_20_1h": [4, 5, 6]},
            index=pd.date_range("2024-01-01", periods=3, freq="h"),
        )
        result = strip_blacklisted(df, {"close_CDLDOJI_1h"})
        assert (result.index == df.index).all()

    def test_strip_preserves_dtypes(self) -> None:
        df = pd.DataFrame({
            "close_CDLDOJI_1h": pd.array([0, 100, 0], dtype="int32"),
            "close_EMA_20_1h": pd.array([1.0, 2.0, 3.0], dtype="float64"),
        })
        result = strip_blacklisted(df, {"close_CDLDOJI_1h"})
        assert result["close_EMA_20_1h"].dtype == np.float64
