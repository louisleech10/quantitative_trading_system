"""IC API model tests."""

from api.models.ic_models import CrossRunRef, ICAnalyzeRequest


def test_ic_analyze_request_config_hash_optional() -> None:
  request = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h")
  assert request.config_hash is None

  with_hash = ICAnalyzeRequest(symbol="BTCUSDT", timeframe="1h", config_hash="abc123")
  assert with_hash.config_hash == "abc123"


def test_ic_analyze_request_cross_sectional_runs() -> None:
  request = ICAnalyzeRequest(
    mode="cross_sectional",
    timeframe="12h",
    cross_sectional_runs=[
      CrossRunRef(symbol="BTCUSDT", config_hash="hash_a"),
      CrossRunRef(symbol="ETHUSDT", config_hash="hash_b"),
    ],
  )
  assert request.cross_sectional_runs is not None
  assert len(request.cross_sectional_runs) == 2
  assert request.cross_sectional_runs[0].symbol == "BTCUSDT"
  assert request.cross_sectional_runs[0].config_hash == "hash_a"
