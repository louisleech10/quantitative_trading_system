from __future__ import annotations

import pytest

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


def _real_mcp(tmp_path, monkeypatch):
    """真實工廠（K 線＝真實 `data_cache/feature_klines`、特徵根與 CGSA 工作目錄＝tmp_path）之 MCP；回 (mcp, 特徵根字串)。"""
    from pathlib import Path

    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    kline_dir = Path(__file__).resolve().parents[1] / "data_cache" / "feature_klines"
    if not (kline_dir / "kline_cache.h5").is_file():
        raise FileNotFoundError(f"missing real kline cache: {kline_dir / 'kline_cache.h5'}")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(tmp_path / "cgsa_work"))
    factory = create_feature_factory(cache_dir=str(kline_dir), validate_continuity=False)
    features_root = (tmp_path / "features").resolve()
    factory._storage = FeatureStorage(str(features_root))
    return FeatureFactoryMCP(factory, ConfigManager()), str(features_root)


@pytest.mark.requires_kline
def test_mcp_generate_features_returns_dict(tmp_path, monkeypatch):
    """MCP 包裝經真實工廠（真實 kline）端到端生成：成功回摘要（非 error）、摘要欄取自真實結果、落盤於本測試之根。

    TESTSEL I10 改寫：原以預設全設定、預設儲存根（寫入 data_cache）、非強制重生呼叫——約 309～320 秒，且斷言
    「有 error 或有 feature_count」生成失敗亦過（空心）、快取命中時不經生成。改為：工廠之 K 線來源＝真實
    `data_cache/feature_klines`、特徵根＝tmp_path、`force_regenerate` 由 MCP 包裝決定（不改產品碼；tmp 根無快取 ⇒ 必真實生成）；
    設定經 MCP 之 config 參數傳入精簡真實設定（12h 單週期、close 來源、L1 trend 兩指標、前處理關）。包裝層之轉交與失敗
    分支另由下方替身測試涵蓋；本案守「真實工廠之回傳物件可被包裝層摘要」與「設定經包裝層原樣生效」。"""
    mcp, features_root = _real_mcp(tmp_path, monkeypatch)
    config = {
        "timeframes": {"primary": "12h", "training": ["12h"], "alignment_mode": "open_minus"},
        "data_sources": {"enabled_sources": ["close"], "synthetic_sources": []},
        "preprocessing": {"enabled": False},
        "atomic_indicators": {
            "trend": {"enabled": True, "indicators": [{"name": "EMA", "params": {"timeperiod": 8}},
                                                      {"name": "SMA", "params": {"timeperiod": 13}}]},
            **{c: {"enabled": False} for c in ("momentum", "volatility", "volume", "cycle", "pattern", "statistics",
                                               "microstructure", "entropy", "tail_risk")},
        },
    }
    result = mcp.generate_features("BTCUSDT", config)
    assert isinstance(result, dict)
    assert "error" in result or "feature_count" in result
    assert "error" not in result, result.get("error")
    assert set(result) == {"feature_count", "generation_time", "layer_counts", "metadata", "hdf5_path"}, sorted(result)
    assert int(result["feature_count"]) > 0
    assert float(result["generation_time"]) > 0
    assert result["metadata"].get("config_hash")
    # 設定經包裝層原樣生效：L1 只有 trend 兩指標之欄（EMA_8／SMA_13），無其他 L1 類別
    l1_count = int((result["layer_counts"] or {}).get("layer1") or 0)  # 實跑鍵名 layer1..（EMA_8、SMA_13 ⇒ 2）
    assert 0 < l1_count <= 8, result["layer_counts"]
    storage_root = features_root  # 落盤於本測試之特徵根（非 data_cache 預設根）
    assert str(result["hdf5_path"]).startswith(storage_root), (result["hdf5_path"], storage_root)


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


def test_mcp_generate_features_uses_primary_timeframe_from_override():
    """純增（審碼 r6 CODEX-R6-P2-01）：上列替身測試之 override 不改主週期，包裝層若改以預設設定（不帶 override）取主週期
    仍過。本案 override 把主週期改為 4h（與預設 12h 不同），斷言工廠以 4h 呼叫。"""
    calls = []

    class _Factory:
        def generate_features(self, symbol, timeframe, config_override=None):
            calls.append(timeframe)
            return type("R", (), {"feature_count": 1, "generation_time": 0.0, "layer_counts": {}, "metadata": {},
                                  "hdf5_path": ""})()

    config_manager = ConfigManager()
    override = {"timeframes": {"primary": "4h"}}
    default_primary = config_manager.get_merged_config().timeframes.primary
    FeatureFactoryMCP(_Factory(), config_manager).generate_features("BTCUSDT", override)
    assert callable(create_feature_factory) and default_primary != "4h" and calls == ["4h"], (default_primary, calls)
