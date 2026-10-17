"""
Phase 1 策略註冊系統測試

測試策略元數據和註冊系統是否正常工作

Author: Claude
Date: 2025-12-03

TESTREG b5：原為模組層腳本（print + sys.exit，pytest 收集 0 項），改寫為 pytest 函式，
保留原 Test 1–10 之檢查；原只 print 不斷言之項改為斷言。
"""

import pytest

from momentum.Analysis.strategy_registry import strategy_registry
from momentum.Optimization.strategy_metadata import StrategyMetadata

_STRATEGY_IDS = ("three_line", "short_long_cross", "mid_long_cross")


def test_list_strategies_contains_builtin() -> None:
    """Test 2：列出策略，內建三策略皆在且為 StrategyMetadata。"""
    strategies = strategy_registry.list_strategies()
    ids = {s.strategy_id for s in strategies}
    assert set(_STRATEGY_IDS) <= ids
    assert all(isinstance(s, StrategyMetadata) for s in strategies)


def test_three_line_metadata() -> None:
    """Test 3：three_line 元數據含三個週期參數，min ≤ default ≤ max。"""
    three_line = strategy_registry.get_strategy("three_line")
    names = [p.name for p in three_line.parameters]
    assert names == ["short_period", "mid_period", "long_period"]
    for p in three_line.parameters:
        assert p.min_value <= p.default_value <= p.max_value


def test_validate_parameters_valid() -> None:
    """Test 4：有效參數通過驗證。"""
    result = strategy_registry.validate_parameters(
        "three_line", {"short_period": 7, "mid_period": 25, "long_period": 70}
    )
    assert result.is_valid, result.errors


def test_validate_parameters_out_of_range() -> None:
    """Test 5：超出參數範圍被拒絕。

    原腳本寫死 short_period=20（假設 max=15），現行元數據範圍已改（見 Test 3），
    故改由元數據取 max_value+1，保住「範圍錯誤須被識別」之原意。
    """
    meta = strategy_registry.get_strategy("three_line")
    short_def = next(p for p in meta.parameters if p.name == "short_period")
    too_big = int(short_def.max_value) + 1
    result = strategy_registry.validate_parameters(
        "three_line",
        {"short_period": too_big, "mid_period": too_big + 1, "long_period": too_big + 2},
    )
    assert not result.is_valid
    assert result.errors


def test_validate_parameters_constraint_violation() -> None:
    """Test 6：short > mid 違反約束被拒絕。"""
    result = strategy_registry.validate_parameters(
        "three_line", {"short_period": 25, "mid_period": 20, "long_period": 70}
    )
    assert not result.is_valid
    assert result.errors


def test_get_calculator_and_validator() -> None:
    """Test 7–8：three_line 之計算函數與驗證函數可取得且來自策略模組。"""
    calculator = strategy_registry.get_calculator("three_line")
    assert callable(calculator)
    assert calculator.__module__ == "momentum.Analysis.strategies.three_line_strategy"
    validator = strategy_registry.get_validator("three_line")
    assert validator is not None and callable(validator)


def test_get_parameter_ranges_matches_metadata() -> None:
    """Test 9：Optuna 參數範圍與元數據一致。"""
    ranges = strategy_registry.get_parameter_ranges("three_line")
    meta = strategy_registry.get_strategy("three_line")
    assert set(ranges) == {p.name for p in meta.parameters}
    for p in meta.parameters:
        assert ranges[p.name]["min"] == p.min_value
        assert ranges[p.name]["max"] == p.max_value


@pytest.mark.parametrize("strategy_id", ["short_long_cross", "mid_long_cross"])
def test_other_strategies_resolvable(strategy_id: str) -> None:
    """Test 10：其他策略之元數據與計算函數可取得。"""
    strategy = strategy_registry.get_strategy(strategy_id)
    assert strategy.strategy_id == strategy_id
    assert len(strategy.parameters) > 0
    assert callable(strategy_registry.get_calculator(strategy_id))
