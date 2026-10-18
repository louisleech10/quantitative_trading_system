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
        # FF-NAME Task 3.2：比對 parse 後之 indicator（欄名為 FF-NAME 文法）
        cols = [
            "ohlc_1h_pattern_CDLDOJI",
            "ohlc_12h_pattern_CDLHAMMER",
            "ohlc_1h_pattern_CDL3LINESTRIKE",
            "close_1h_trend_EMA_20",
            "close_1h_momentum_RSI_14",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert "ohlc_1h_pattern_CDLDOJI" in matched
        assert "ohlc_12h_pattern_CDLHAMMER" in matched
        assert "ohlc_1h_pattern_CDL3LINESTRIKE" in matched
        assert "close_1h_trend_EMA_20" not in matched
        assert "close_1h_momentum_RSI_14" not in matched

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
        # L2/L3 衍生（FF-NAME 文法：身分之 indicator 不變、後接 op 段）
        cols = [
            "ohlc_1h_pattern_CDLDOJI_Distance",
            "ohlc_12h_pattern_CDLHAMMER_Mean-W21",
            "close_1h_trend_EMA_20",
        ]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert "ohlc_1h_pattern_CDLDOJI_Distance" in matched
        assert "ohlc_12h_pattern_CDLHAMMER_Mean-W21" in matched
        assert "close_1h_trend_EMA_20" not in matched

    def test_HT_DCPHASE_derived_features_also_match(self) -> None:
        # 衍生命名（FF-NAME 文法）：close_12h_cycle_HT-DCPHASE_Momentum-L3
        cols = [
            "close_12h_cycle_HT-DCPHASE_Momentum-L3",
            "close_12h_cycle_HT-DCPHASE_Mean-W21",
            "close_12h_trend_EMA_5",
        ]
        matched = expand_blacklist_patterns(["HT-DCPHASE"], cols)
        assert "close_12h_cycle_HT-DCPHASE_Momentum-L3" in matched
        assert "close_12h_cycle_HT-DCPHASE_Mean-W21" in matched
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
        cols = ["ohlc_1h_pattern_CDLDOJI", "close_1h_trend_EMA_20"]
        assert expand_blacklist_patterns([], cols) == frozenset()

    def test_empty_columns_returns_empty(self) -> None:
        assert expand_blacklist_patterns(["CDL_PATTERN_ALL"], []) == frozenset()

    def test_both_empty_returns_empty(self) -> None:
        assert expand_blacklist_patterns([], []) == frozenset()

    def test_custom_indicator_pattern_exact(self) -> None:
        # FF-NAME Task 3.2：非 alias 之 pattern 比對 parse 後之 indicator（精確相等，不走子字串：ATR 不命中 NATR）
        cols = ["hlc_1h_volatility_ATR_14", "hlc_1h_volatility_NATR_14", "close_1h_trend_EMA_20"]
        matched = expand_blacklist_patterns(["ATR"], cols)
        assert matched == frozenset({"hlc_1h_volatility_ATR_14"})

    def test_returns_frozenset_of_str(self) -> None:
        cols = ["ohlc_1h_pattern_CDLDOJI"]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert isinstance(matched, frozenset)
        assert matched == frozenset(cols)
        for c in matched:
            assert isinstance(c, str)

    def test_skips_empty_string_pattern(self) -> None:
        # 空字串 pattern 應被忽略（避免命中所有欄位）
        cols = ["close_1h_trend_EMA_20", "close_1h_momentum_RSI_14"]
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
        # FF-NAME Task 3.2：不合文法之欄名（含非 ASCII）不命中、不拋錯；合文法之 CDL 欄照常命中
        cols = ["前綴_CDLDOJI_1h", "正常_EMA_20_1h", "💀_RSI_14_1h", "ohlc_1h_pattern_CDLDOJI"]
        matched = expand_blacklist_patterns(["CDL_PATTERN_ALL"], cols)
        assert matched == frozenset({"ohlc_1h_pattern_CDLDOJI"})

    def test_column_name_with_underscores_and_digits(self) -> None:
        # 帶參數段與 op 段（含數字）之 CDL 衍生欄皆以 indicator 命中
        cols = ["ohlc_1h_pattern_CDLDOJI_Mean-W21", "ohlc_12h_pattern_CDL2CROWS_Lag-99"]
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
