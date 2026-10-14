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
    assert {
        "minimal",
        "standard",
        "extended",
        "full",
        "basic_essential",
        "intermediate_research",
        "professional_full",
        "ml_optimized",
    }.issubset(names)

    preset_map = {item["name"]: item for item in presets}
    assert isinstance(preset_map["professional_full"].get("config"), dict)
    assert preset_map["basic_essential"].get("level") == "L1"


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


def test_mcp_generate_features_forwards_primary_timeframe_and_summarizes():
    """純增：上列 test_mcp_generate_features_returns_dict 以預設全設定跑真實完整生成（約 309 秒、寫 data_cache），斷言
    「有 error 或有 feature_count」——生成失敗亦過（空心）。本案以替身工廠測包裝契約：以合併設定之主週期與原
    config_override 呼叫工廠、成功回傳摘要欄（feature_count 等取自結果）、工廠拋例外 ⇒ 回 {"error": 例外訊息}。"""
    import inspect
    from types import SimpleNamespace

    calls = []

    class _Factory:
        def __init__(self, fail: bool) -> None:
            self.fail = fail

        def generate_features(self, symbol, timeframe, config_override=None):
            calls.append((symbol, timeframe, config_override))
            if self.fail:
                raise RuntimeError("boom-xyz")
            return SimpleNamespace(feature_count=7, generation_time=1.5, layer_counts={"L1": 7},
                                   metadata={"k": "v"}, hdf5_path="")

    config_manager = ConfigManager()
    override = {"preset": "minimal"}
    primary = config_manager.get_merged_config(override).timeframes.primary
    ok = FeatureFactoryMCP(_Factory(False), config_manager).generate_features("BTCUSDT", override)
    bad = FeatureFactoryMCP(_Factory(True), config_manager).generate_features("BTCUSDT", override)
    real_params = inspect.signature(create_feature_factory().generate_features).parameters
    assert "config_override" in real_params and calls == [("BTCUSDT", primary, override)] * 2, calls
    assert ok == {"feature_count": 7, "generation_time": 1.5, "layer_counts": {"L1": 7}, "metadata": {"k": "v"},
                  "hdf5_path": ""} and bad == {"error": "boom-xyz"}, (ok, bad)
