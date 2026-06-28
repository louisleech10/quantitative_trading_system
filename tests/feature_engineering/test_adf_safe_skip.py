"""ADF safe-skip whitelist 單元 + 邊界 + 跨 symbol 一致性測試。

對應 docs/NAN_REDUCTION_STRATEGY.md §4.5 與 PLAN §3.5。
"""

from __future__ import annotations

import pytest

from momentum.FeatureEngineering.utils.adf_safe_skip import (
    ADF_SAFE_SKIP_PATTERNS,
    filter_safe_skip,
    is_safe_skip,
)


# ─── 功能性測試 ───────────────────────────────────────────────


class TestIsSafeSkipBoundedOscillator:
    """(a) 嚴格有界振盪器 → 必 skip。

    命名取自真實 catalog（2026-05-28 驗證）：{source}_{tf}_{category}_{indicator}_{params}
    多組件指標用 hyphen。
    """

    @pytest.mark.parametrize(
        "col_name",
        [
            "close_12h_momentum_RSI_5",
            "close_1h_momentum_RSI_233",
            "hlc_12h_momentum_ADX_8",
            "hlc_12h_momentum_ADXR_8",
            "hlc_12h_momentum_DX_8",
            "hlc_12h_momentum_WILLR_5",
            "hlcv_12h_momentum_MFI_8",
            "hl_12h_momentum_AROON-aroonup_13",
            "hl_12h_momentum_AROON-aroondown_13",
            "hl_12h_momentum_AROONOSC_13",
            "hlc_12h_momentum_ULTOSC_13-21-55",
            "hlc_12h_momentum_STOCH-slowk_13-3-0-3-0",
            "hlc_12h_momentum_STOCH-slowd_13-3-0-3-0",
            "hlc_12h_momentum_STOCHF-fastk_13-3-0",
            "hlc_12h_momentum_STOCHF-fastd_13-3-0",
            "close_12h_momentum_STOCHRSI-fastk_14-3-3-0",
            "close_12h_momentum_STOCHRSI-fastd_14-3-3-0",
            "ohlc_12h_momentum_BOP",
            "hl_12h_statistics_CORREL_5",
            "close-volume_12h_statistics_Correl-CloseVolume_5",
            "close_12h_momentum_CMO_5",
            "close_12h_statistics_LINEARREG-ANGLE_5",
            "hlc_12h_momentum_PLUS-DI_8",
            "hlc_12h_momentum_MINUS-DI_8",
        ],
    )
    def test_strictly_bounded_indicators_are_skipped(self, col_name: str) -> None:
        assert is_safe_skip(col_name, enabled=True) is True


class TestIsSafeSkipFirstDifference:
    """(b) 一階差分 / 共整合差 → 必 skip"""

    @pytest.mark.parametrize(
        "col_name",
        [
            "close_12h_momentum_MOM_5",
            "close_12h_momentum_ROC_5",
            "close_12h_momentum_ROCP_5",
            "close_12h_momentum_ROCR_5",
            "close_12h_momentum_ROCR100_5",
            "close_12h_momentum_TRIX_5",
            "close_12h_momentum_MACD-Line_12-26-9",
            "close_12h_momentum_MACD-Signal_12-26-9",
            "close_12h_momentum_MACD-Hist_12-26-9",
            "close_12h_momentum_MACDEXT-Line_12-26-9",
            "close_12h_momentum_MACDEXT-Signal_12-26-9",
            "close_12h_momentum_MACDEXT-Hist_12-26-9",
            "close_12h_momentum_MACDFIX-Line_3",
            "close_12h_momentum_MACDFIX-Hist_3",
            "close_12h_momentum_APO_12-26-0",
            "close_12h_momentum_PPO_12-26-0",
        ],
    )
    def test_first_difference_indicators_are_skipped(self, col_name: str) -> None:
        assert is_safe_skip(col_name, enabled=True) is True


class TestIsSafeSkipBinarySinusoidNormalized:
    """(a) 二元 / sinusoid / normalized → 必 skip"""

    @pytest.mark.parametrize(
        "col_name",
        [
            "close_12h_cycle_HT-TRENDMODE",
            "close_12h_cycle_HT-SINE-LeadSine",
            "close_1h_cycle_HT-SINE-LeadSine",
            "hlc_12h_volatility_NATR_5",
        ],
    )
    def test_binary_sinusoid_normalized_are_skipped(self, col_name: str) -> None:
        assert is_safe_skip(col_name, enabled=True) is True


class TestIsSafeSkipL2Constructed:
    """L2 構造性離散 / 有界 → 必 skip"""

    @pytest.mark.parametrize(
        "col_name",
        [
            "close_12h_trend_EMA_5_20_Cross",              # Cross 是 suffix
            "close_12h_momentum_RSI_5_BinarySignal_Overbought",
            "close_12h_momentum_RSI_5_BinarySignal_Oversold",
            "close_12h_trend_EMA_5_Sign_W21",
            "close_12h_trend_EMA_5_TsRank_W5",
            "close_12h_trend_EMA_5_TsArgMax_W21",
            "close_12h_trend_EMA_5_TsArgMin_W21",
            "close_12h_trend_EMA_5_TsCorr_W21_volume",
        ],
    )
    def test_l2_constructed_are_skipped(self, col_name: str) -> None:
        assert is_safe_skip(col_name, enabled=True) is True


class TestIsSafeSkipNotInWhitelist:
    """數學上 I(1) 或 borderline → NOT skip（仍跑 ADF）"""

    @pytest.mark.parametrize(
        "col_name",
        [
            # 趨勢追蹤 I(1)
            "close_EMA_20_1h",
            "close_SMA_50_1h",
            "close_WMA_14_1h",
            "close_DEMA_20_1h",
            "close_TEMA_20_1h",
            "close_KAMA_30_1h",
            "close_T3_5_0.7_1h",
            "close_MAMA_0.5_0.05_1h",
            "close_HT_TRENDLINE_1h",
            "hl_MIDPOINT_14_1h",
            "hl_MIDPRICE_14_1h",
            "ohlc_SAR_0.02_0.2_1h",
            "close_BBANDS_Upper_20_2_1h",
            "close_BBANDS_Middle_20_2_1h",
            "close_BBANDS_Lower_20_2_1h",
            "close_LINEARREG_14_1h",
            "close_LINEARREG_INTERCEPT_14_1h",
            "close_TSF_14_1h",
            "hlc_Keltner_Upper_20_2_1h",
            "hlc_Keltner_Lower_20_2_1h",
            "hl_Donchian_Upper_20_1h",
            "hlcv_VWAP_1h",
            # 累積 volume I(1)
            "ohlcv_OBV_1h",
            "hlcv_AD_1h",
            # 絕對波動率 I(1)
            "hlc_ATR_14_1h",
            "hl_Parkinson_Vol_14_1h",
            "ohlc_GarmanKlass_Vol_14_1h",
            "hlc_TRANGE_1h",
            # Borderline 統計估計（含 hyphen 變體，確認不誤命中）
            "close_12h_momentum_CCI_5",
            "close_12h_statistics_STDDEV_5_1",
            "close_12h_statistics_VAR_5_1",
            "hl_12h_statistics_BETA_5",
            "close-volume_12h_statistics_Beta-CloseVolume_5",
            "close_12h_statistics_LINEARREG-SLOPE_5",     # hyphen，但非 whitelist
            "close_12h_statistics_LINEARREG_5",           # LINEARREG 本體（I(1)）
            "close_12h_statistics_LINEARREG-INTERCEPT_5",
            "close_12h_statistics_TSF_5",
            # 無硬限的 cycle（HT-DCPERIOD / HT-PHASOR 不在 whitelist）
            "close_12h_cycle_HT-DCPERIOD",
            "close_12h_cycle_HT-PHASOR-InPhase",
            "close_12h_cycle_HT-PHASOR-Quadrature",
            # 方向動量 PLUS-DM/MINUS-DM（hyphen，確認不被 PLUS-DI 誤命中）
            "hl_12h_momentum_PLUS-DM_8",
            "hl_12h_momentum_MINUS-DM_8",
            # 衍生 volume oscillator（borderline）
            "hlcv_12h_volume_ADOSC_3-10",
            "ohlcv_12h_volume_Force-Index_13",
            "hlcv_12h_volume_Klinger-Volume-Osc",
            "volume_12h_volume_VolumeMA_Ratio_20",
            "hlcv_12h_volume_Ease-of-Movement_14",
            # 趨勢追蹤 I(1)（含 hyphen channel）
            "close_12h_trend_EMA_5",
            "close_12h_trend_SMA_50",
            "close_12h_trend_BBANDS-Upper_20-2",
            "close_12h_trend_HT-TRENDLINE",
            "hlc_12h_volatility_ATR_5",
            "ohlcv_12h_volume_OBV",
            # L2 with I(1) base（decay_linear/log1p/abs/SignedStrength）
            "close_12h_trend_EMA_5_DecayLinear_W14",
            "close_12h_trend_EMA_5_Log1p",
            "close_12h_trend_EMA_5_SignedStrength",
            # L2 Distance / Ratio / Momentum（共整合差但未列入 whitelist）
            "close_12h_trend_EMA_5_Distance",
            "close_12h_trend_EMA_5_Momentum_L3",
        ],
    )
    def test_indicators_not_in_whitelist_keep_adf(self, col_name: str) -> None:
        assert is_safe_skip(col_name, enabled=True) is False


# ─── 配置開關測試 ─────────────────────────────────────────────


class TestIsSafeSkipConfig:
    """enabled / additional / exclusion 行為"""

    def test_disabled_returns_false_for_whitelist(self) -> None:
        # I-4: enabled=False 等同 no-op
        assert is_safe_skip("close_RSI_14_1h", enabled=False) is False

    def test_disabled_returns_false_for_anything(self) -> None:
        for col in ("anything", "close_RSI_14_1h", "close_EMA_20_1h", ""):
            assert is_safe_skip(col, enabled=False) is False

    def test_additional_patterns_skip(self) -> None:
        col = "close_MyCustomI0_14_1h"
        assert is_safe_skip(col, enabled=True) is False  # 未列入內建
        assert is_safe_skip(col, enabled=True, additional_patterns=["_MyCustomI0_"]) is True

    def test_exclusion_overrides_whitelist(self) -> None:
        # exclusion 優先於 whitelist
        assert is_safe_skip("close_RSI_14_1h", enabled=True) is True
        assert is_safe_skip(
            "close_RSI_14_1h", enabled=True, exclusion_patterns=["_RSI_"]
        ) is False

    def test_exclusion_overrides_additional(self) -> None:
        col = "close_Foo_14_1h"
        assert is_safe_skip(col, enabled=True, additional_patterns=["_Foo_"]) is True
        assert is_safe_skip(
            col,
            enabled=True,
            additional_patterns=["_Foo_"],
            exclusion_patterns=["_Foo_"],
        ) is False


# ─── 邊界 ──────────────────────────────────────────────────────


class TestEdgeCases:
    def test_empty_column_name(self) -> None:
        assert is_safe_skip("", enabled=True) is False
        assert is_safe_skip("", enabled=False) is False

    def test_special_characters_in_column_name(self) -> None:
        # 不 raise，回傳 False
        for col in ("a/b/c", "前綴_RSI_14_1h", "_RSI_14_1h\n", "💀_RSI_14_1h"):
            # 前綴/後綴特殊字符不影響 substring match
            result = is_safe_skip(col, enabled=True)
            assert isinstance(result, bool)
        # 含 _RSI_ substring → 仍 skip
        assert is_safe_skip("前綴_RSI_14_1h", enabled=True) is True

    def test_empty_additional_pattern_string(self) -> None:
        # additional 中含空字串不應導致 false positive
        assert is_safe_skip("close_EMA_20_1h", enabled=True, additional_patterns=[""]) is False

    def test_empty_exclusion_pattern_string(self) -> None:
        # exclusion 中含空字串不應導致 false exclusion
        assert is_safe_skip("close_RSI_14_1h", enabled=True, exclusion_patterns=[""]) is True


# ─── filter_safe_skip ─────────────────────────────────────────


class TestFilterSafeSkip:
    def test_preserves_order(self) -> None:
        cols = ["close_RSI_14_1h", "close_EMA_20_1h", "close_MOM_14_1h", "close_SMA_50_1h"]
        needs, skipped = filter_safe_skip(cols, enabled=True)
        assert needs == ["close_EMA_20_1h", "close_SMA_50_1h"]
        assert skipped == ["close_RSI_14_1h", "close_MOM_14_1h"]

    def test_disabled_returns_all_in_needs(self) -> None:
        cols = ["close_RSI_14_1h", "close_EMA_20_1h"]
        needs, skipped = filter_safe_skip(cols, enabled=False)
        assert needs == cols
        assert skipped == []

    def test_empty_input(self) -> None:
        needs, skipped = filter_safe_skip([], enabled=True)
        assert needs == []
        assert skipped == []

    def test_no_duplicates_no_loss(self) -> None:
        # I-3 contract: needs + skipped 集合 = input 集合（preserve all）
        cols = [
            "close_RSI_14_1h", "close_EMA_20_1h", "close_MACD_Hist_12-26-9_1h",
            "close_ATR_14_1h", "close_BinarySignal_Foo_1h", "close_Custom_1h",
        ]
        needs, skipped = filter_safe_skip(cols, enabled=True)
        assert set(needs) | set(skipped) == set(cols)
        assert set(needs) & set(skipped) == set()


# ─── 跨 symbol 一致性 ─────────────────────────────────────────


class TestCrossSymbolConsistency:
    """safe-skip 決策只看 column name；同名特徵跨 symbol 行為 deterministic。"""

    def test_same_column_same_decision_regardless_of_symbol(self) -> None:
        # 模擬 BTC / ETH / SOL 在同一段 pipeline 內處理同名 RSI
        col_name = "close_RSI_14_1h"
        for _symbol_simulation in range(10):
            assert is_safe_skip(col_name, enabled=True) is True
        for _symbol_simulation in range(10):
            assert is_safe_skip("close_EMA_20_1h", enabled=True) is False


# ─── 內建 whitelist 完整性 ────────────────────────────────────


class TestWhitelistContract:
    """ADF_SAFE_SKIP_PATTERNS 結構契約。"""

    def test_whitelist_is_frozenset(self) -> None:
        assert isinstance(ADF_SAFE_SKIP_PATTERNS, frozenset)

    def test_whitelist_contains_no_empty_strings(self) -> None:
        assert "" not in ADF_SAFE_SKIP_PATTERNS

    def test_patterns_use_correct_delimiter(self) -> None:
        # 單組件指標用 underscore 包夾；多組件指標用 hyphen（對照真實 catalog 命名）
        # 不允許「underscore 形式的多組件 pattern」（這正是 20260528 抓到的 bug）
        forbidden_underscore_multicomponent = [
            "_MACD_Line_", "_MACD_Hist_", "_MACD_Signal_",
            "_HT_DCPHASE", "_HT_SINE_", "_HT_TRENDMODE",
            "_STOCH_slowk_", "_AROON_aroonup_", "_LINEARREG_ANGLE_",
            "_PLUS_DI_", "_MINUS_DI_",
        ]
        for pat in forbidden_underscore_multicomponent:
            assert pat not in ADF_SAFE_SKIP_PATTERNS, (
                f"{pat!r} 是 underscore 形式的多組件 pattern — 應改用 hyphen"
            )

    def test_known_indicators_covered(self) -> None:
        # 哨兵測試：以下 pattern 必在 whitelist（hyphen 形式）
        sentinel_indicators = [
            "_RSI_", "_MOM_", "_NATR_",
            "MACD-Hist", "MACD-Line",
            "HT-TRENDMODE", "HT-SINE",
            "STOCH-slowk", "AROON-aroonup", "LINEARREG-ANGLE", "PLUS-DI",
            "_Cross", "_BinarySignal_", "_TsRank_",
        ]
        for s in sentinel_indicators:
            assert s in ADF_SAFE_SKIP_PATTERNS, f"{s!r} missing from whitelist"

    def test_known_excluded_indicators_not_in_whitelist(self) -> None:
        # 反向哨兵：以下「不該」在 whitelist（borderline / I(1)）
        excluded = [
            "_CCI_", "_STDDEV_", "_VAR_", "_BETA_",
            "LINEARREG-SLOPE", "_TRANGE", "_ATR_",
            "HT-DCPERIOD", "HT-PHASOR",
            "PLUS-DM", "MINUS-DM",
            "_ADOSC_", "Force-Index", "Klinger",
            "_Distance", "_Ratio_", "_Momentum_",
            "_DecayLinear_", "_Log1p_", "_Abs_", "_SignedStrength",
            "_EMA_", "_SMA_", "_DEMA_", "_TEMA_", "_KAMA_", "_T3_", "_MAMA_",
            "BBANDS", "Keltner", "Donchian", "_VWAP_", "_OBV_", "_AD_",
        ]
        for e in excluded:
            assert e not in ADF_SAFE_SKIP_PATTERNS, (
                f"{e!r} unexpectedly in whitelist — borderline indicators "
                f"should NOT be auto-skipped (let ADF decide)"
            )

    def test_real_catalog_naming_regression(self) -> None:
        """回歸測試：用真實 catalog 命名格式驗證 hyphen 指標確實被命中。

        這是 20260528 比較抓到 bug 後加的防線 — 確保 pattern 與真實命名同步。
        命名格式：{source}_{tf}_{category}_{indicator}_{params}[_derivation]
        """
        must_skip = [
            "close_12h_momentum_MACD-Line_12-26-9",
            "close_12h_momentum_MACD-Hist_12-26-9",
            "close_12h_cycle_HT-TRENDMODE",
            "close_12h_cycle_HT-SINE-LeadSine",
            "hlc_12h_momentum_STOCH-slowk_13-3-0-3-0",
            "hl_12h_momentum_AROON-aroonup_13",
            "close_12h_statistics_LINEARREG-ANGLE_5",
            "hlc_12h_momentum_PLUS-DI_8",
            "close_12h_trend_EMA_5_20_Cross",
        ]
        for col in must_skip:
            assert is_safe_skip(col, enabled=True) is True, (
                f"{col!r} (真實命名) 應被 skip 但未命中 — pattern 與 catalog 命名脫節"
            )

        must_not_skip = [
            "close_12h_statistics_LINEARREG-SLOPE_5",  # borderline
            "hl_12h_momentum_PLUS-DM_8",               # 不可被 PLUS-DI 誤命中
            "close_12h_cycle_HT-DCPERIOD",
            "close_12h_trend_EMA_5",                   # I(1)
        ]
        for col in must_not_skip:
            assert is_safe_skip(col, enabled=True) is False, (
                f"{col!r} 不該被 skip（borderline/I(1)）但被命中"
            )
