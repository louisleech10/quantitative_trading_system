import pytest

from momentum.Strategy.position_sizing import (
	FixedPositionSizer,
	KellyPositionSizer,
	ProbabilityScaledSizer,
)


@pytest.mark.parametrize(
	"proba,expected",
	[
		(0.0, 0.0),
		(0.2, 0.0),
		(0.5, 0.0),
		(0.8, 0.25),
		(1.0, 0.25),
	],
)
def test_kelly_position_size_range(proba, expected):
	sizer = KellyPositionSizer(kelly_fraction=0.5, max_position=0.25)
	value = sizer.calculate_position_size(
		predicted_proba=proba,
		equity=1.0,
		risk_params={"win_loss_ratio": 1.0},
	)
	assert value == pytest.approx(expected, rel=1e-6)


def test_kelly_proba_one_hits_max_position():
	sizer = KellyPositionSizer(kelly_fraction=1.0, max_position=0.25)
	value = sizer.calculate_position_size(1.0, 1.0, {"win_loss_ratio": 1.5})
	assert value == pytest.approx(0.25)


def test_kelly_equity_zero_returns_zero():
	sizer = KellyPositionSizer()
	value = sizer.calculate_position_size(0.8, 0.0, {"win_loss_ratio": 1.5})
	assert value == 0.0


def test_kelly_nan_proba_returns_zero():
	sizer = KellyPositionSizer()
	value = sizer.calculate_position_size(float("nan"), 1.0, {"win_loss_ratio": 1.5})
	assert value == 0.0


def test_kelly_win_loss_ratio_zero_error():
	sizer = KellyPositionSizer()
	with pytest.raises(ValueError):
		sizer.calculate_position_size(0.8, 1.0, {"win_loss_ratio": 0})


@pytest.mark.parametrize("fraction", [-0.1, 1.1])
def test_kelly_invalid_fraction_error(fraction):
	with pytest.raises(ValueError):
		KellyPositionSizer(kelly_fraction=fraction)


def test_kelly_invalid_max_position_error():
	with pytest.raises(ValueError):
		KellyPositionSizer(max_position=0)


def test_fixed_position_always_same():
	sizer = FixedPositionSizer(fixed_size=0.2)
	for proba in [0.0, 0.3, 0.7, 1.0]:
		assert sizer.calculate_position_size(proba, 1.0, {}) == pytest.approx(0.2)


def test_fixed_negative_size_error():
	with pytest.raises(ValueError):
		FixedPositionSizer(fixed_size=-0.1)


@pytest.mark.parametrize(
	"proba,expected",
	[
		(0.1, 0.0),
		(0.5, 0.0),
		(0.75, 0.125),
		(1.0, 0.25),
	],
)
def test_probability_scaled_size(proba, expected):
	sizer = ProbabilityScaledSizer(max_position=0.25, threshold=0.5)
	value = sizer.calculate_position_size(proba, 1.0, {})
	assert value == pytest.approx(expected, rel=1e-6)


def test_probability_scaled_equity_zero_returns_zero():
	sizer = ProbabilityScaledSizer()
	assert sizer.calculate_position_size(0.9, 0.0, {}) == 0.0


def test_probability_scaled_nan_proba_returns_zero():
	sizer = ProbabilityScaledSizer()
	assert sizer.calculate_position_size(float("nan"), 1.0, {}) == 0.0


@pytest.mark.parametrize("threshold", [-0.1, 1.0, 1.2])
def test_probability_scaled_invalid_threshold_error(threshold):
	with pytest.raises(ValueError):
		ProbabilityScaledSizer(threshold=threshold)


def test_probability_scaled_invalid_max_position_error():
	with pytest.raises(ValueError):
		ProbabilityScaledSizer(max_position=0)


def test_all_sizers_protocol_methods_exist():
	for sizer in [KellyPositionSizer(), FixedPositionSizer(), ProbabilityScaledSizer()]:
		assert hasattr(sizer, "calculate_position_size")
