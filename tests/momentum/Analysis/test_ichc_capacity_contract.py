"""ICHC Task 6.1 — capacity unknown 契約鎖死（產品碼零改，測試釘住防回退）。

實查（COMPOSER-R3-P2-04）：前端無 capacity_tier/badge consumer → 前端面 N/A；
本檔為唯一防回退閘。unknown 語意=無 ADV 資料不得給出任何可交易 tier。
"""

import math

import pytest

from momentum.Analysis.ic_config_schema import ICConfig
from momentum.Analysis.net_ic_analyzer import NetICAnalyzer


@pytest.fixture()
def analyzer():
    return NetICAnalyzer(ICConfig().net_ic_analysis.model_dump())


class TestCapacityUnknownContract:
    def test_no_adv_is_unknown(self, analyzer):
        result = analyzer.estimate_factor_capacity(turnover=0.3, avg_daily_volume_usd=None)
        assert result["capacity_tier"] == "unknown"
        assert math.isnan(result["estimated_capacity_usd"])

    def test_zero_adv_is_unknown(self, analyzer):
        result = analyzer.estimate_factor_capacity(turnover=0.3, avg_daily_volume_usd=0.0)
        assert result["capacity_tier"] == "unknown"

    def test_negative_adv_is_unknown(self, analyzer):
        result = analyzer.estimate_factor_capacity(turnover=0.3, avg_daily_volume_usd=-5.0)
        assert result["capacity_tier"] == "unknown"

    def test_normal_adv_computes_tier(self, analyzer):
        """回歸：有 ADV → tier 依 turnover 分級、capacity 為有限正值。"""
        result = analyzer.estimate_factor_capacity(
            turnover=0.3, avg_daily_volume_usd=1_000_000.0
        )
        assert result["capacity_tier"] == "high"
        assert result["estimated_capacity_usd"] > 0
        assert math.isfinite(result["estimated_capacity_usd"])

    def test_unknown_never_in_tradable_tiers(self, analyzer):
        tradable = {"low", "medium", "high"}
        result = analyzer.estimate_factor_capacity(turnover=1.5, avg_daily_volume_usd=None)
        assert result["capacity_tier"] not in tradable
