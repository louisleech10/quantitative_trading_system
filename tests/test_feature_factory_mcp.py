from __future__ import annotations

from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.config_manager import ConfigManager
from momentum.FeatureEngineering.mcp.feature_factory_mcp import FeatureFactoryMCP
from momentum.FeatureEngineering.mcp.nl2config import NL2ConfigConverter


def _make_mcp() -> FeatureFactoryMCP:
    factory = create_feature_factory()
    config_manager = ConfigManager()
    return FeatureFactoryMCP(factory, config_manager)


def test_mcp_list_indicators():
    mcp = _make_mcp()
    indicators = mcp.list_indicators()
    assert isinstance(indicators, list)
    assert len(indicators) >= 100
    assert any(item["name"] == "RSI" for item in indicators)


def test_mcp_list_data_sources():
    mcp = _make_mcp()
    sources = mcp.list_data_sources()
    names = {item["name"] for item in sources}
    assert "close" in names


def test_mcp_preview_update_validate():
    mcp = _make_mcp()
    preview = mcp.preview_feature_count()
    assert preview["total_features"] > 0

    updated = mcp.update_config({"atomic_indicators": {"trend": {"enabled": False}}})
    assert updated["atomic_indicators"]["trend"]["enabled"] is False

    invalid = mcp.validate_config(
        {"atomic_indicators": {"trend": {"indicators": [{"name": "NONEXIST"}]}}}
    )
    assert invalid["is_valid"] is False


def test_mcp_get_presets():
    mcp = _make_mcp()
    presets = mcp.get_presets()
    names = {item["name"] for item in presets}
    assert {"minimal", "standard", "extended", "full"}.issubset(names)


def test_mcp_get_feature_metadata():
    mcp = _make_mcp()
    metadata = mcp.get_feature_metadata("RSI")
    assert metadata["found"] is True
    assert metadata["indicator"]["name"] == "RSI"


def test_mcp_generate_features_returns_dict():
    mcp = _make_mcp()
    result = mcp.generate_features("BTCUSDT")
    assert isinstance(result, dict)
    assert "error" in result or "feature_count" in result


def test_nl2config_converter_no_match():
    converter = NL2ConfigConverter(config_schema={"foo": "bar"})
    patch = converter.convert("no match here")
    assert patch == {}


def test_mcp_nl2config():
    mcp = _make_mcp()
    result = mcp.nl2config("preset minimal")
    assert "config_patch" in result
    assert "preview" in result
