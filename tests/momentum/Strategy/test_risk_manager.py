import pytest

from momentum.Strategy.risk_manager import RiskManager


@pytest.mark.parametrize(
    "entry,atr,mult,expected",
    [
        (100.0, 2.0, 2.0, 96.0),
        (100.0, 1.0, 1.0, 99.0),
        (30000.0, 100.0, 3.0, 29700.0),
    ],
)
def test_calculate_stop_loss_normal(entry, atr, mult, expected):
    assert RiskManager.calculate_stop_loss(entry, atr, mult) == pytest.approx(expected)


def test_calculate_stop_loss_atr_zero_fallback():
    assert RiskManager.calculate_stop_loss(100.0, 0.0, 2.0) == 100.0


def test_calculate_stop_loss_multiplier_zero_fallback():
    assert RiskManager.calculate_stop_loss(100.0, 2.0, 0.0) == 100.0


@pytest.mark.parametrize(
    "entry,atr,mult",
    [
        (0.0, 1.0, 1.0),
        (-1.0, 1.0, 1.0),
        (100.0, -1.0, 1.0),
        (100.0, 1.0, -1.0),
    ],
)
def test_calculate_stop_loss_invalid_inputs(entry, atr, mult):
    with pytest.raises(ValueError):
        RiskManager.calculate_stop_loss(entry, atr, mult)


@pytest.mark.parametrize(
    "entry,atr,sl,tp_ratio,expected",
    [
        (100.0, 2.0, 2.0, 3.0, 112.0),
        (100.0, 1.0, 1.0, 2.0, 102.0),
    ],
)
def test_calculate_take_profit_normal(entry, atr, sl, tp_ratio, expected):
    assert RiskManager.calculate_take_profit(entry, atr, sl, tp_ratio) == pytest.approx(expected)


def test_calculate_take_profit_atr_zero_fallback():
    assert RiskManager.calculate_take_profit(100.0, 0.0, 2.0, 3.0) == 100.0


@pytest.mark.parametrize(
    "entry,atr,sl,tp_ratio",
    [
        (0.0, 1.0, 1.0, 1.0),
        (100.0, -1.0, 1.0, 1.0),
        (100.0, 1.0, -1.0, 1.0),
        (100.0, 1.0, 1.0, -1.0),
    ],
)
def test_calculate_take_profit_invalid_inputs(entry, atr, sl, tp_ratio):
    with pytest.raises(ValueError):
        RiskManager.calculate_take_profit(entry, atr, sl, tp_ratio)


def test_trailing_stop_not_activated_returns_none():
    result = RiskManager.calculate_trailing_stop(
        entry_price=100.0,
        current_high=101.0,
        atr=2.0,
        activation_multiplier=1.0,
    )
    assert result is None


def test_trailing_stop_activated_returns_value():
    result = RiskManager.calculate_trailing_stop(
        entry_price=100.0,
        current_high=103.0,
        atr=2.0,
        activation_multiplier=1.0,
    )
    assert result == pytest.approx(101.0)


def test_trailing_stop_atr_zero_returns_none():
    result = RiskManager.calculate_trailing_stop(100.0, 110.0, 0.0, 1.0)
    assert result is None


@pytest.mark.parametrize(
    "entry,current_high,atr,mult",
    [
        (0.0, 101.0, 2.0, 1.0),
        (100.0, 0.0, 2.0, 1.0),
        (100.0, 101.0, -1.0, 1.0),
        (100.0, 101.0, 2.0, -1.0),
    ],
)
def test_trailing_stop_invalid_inputs(entry, current_high, atr, mult):
    with pytest.raises(ValueError):
        RiskManager.calculate_trailing_stop(entry, current_high, atr, mult)
