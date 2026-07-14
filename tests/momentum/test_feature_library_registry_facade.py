"""FeatureLibrary registry 轉發 façade 契約測試。"""

from unittest.mock import MagicMock

from momentum.FeatureEngineering.feature_library import FeatureLibrary


def _library_with_registry(registry: MagicMock) -> FeatureLibrary:
    """建立只用於 registry façade 測試的 library。"""
    library = object.__new__(FeatureLibrary)
    library._registry = registry
    return library


def test_get_entry_forwards_arguments_and_identity() -> None:
    """get_entry 原樣轉發參數與 mock 回傳物。"""
    registry = MagicMock()
    expected = {"config_hash": "cfg"}
    registry.get.return_value = expected
    library = _library_with_registry(registry)

    actual = library.get_entry("BTCUSDT", "12h", "cfg")

    assert actual is expected
    registry.get.assert_called_once_with("BTCUSDT", "12h", "cfg")


def test_get_entry_passes_none_through() -> None:
    """get_entry 不轉換 mock registry 的 None。"""
    registry = MagicMock()
    registry.get.return_value = None
    library = _library_with_registry(registry)

    assert library.get_entry("BTCUSDT", "12h", "missing") is None
    registry.get.assert_called_once_with("BTCUSDT", "12h", "missing")


def test_find_latest_materialized_forwards_arguments_and_identity() -> None:
    """latest 查詢原樣轉發參數與 mock 回傳物。"""
    registry = MagicMock()
    expected = {"config_hash": "latest"}
    registry.find_latest_materialized.return_value = expected
    library = _library_with_registry(registry)

    actual = library.find_latest_materialized("ETHUSDT", "1h")

    assert actual is expected
    registry.find_latest_materialized.assert_called_once_with("ETHUSDT", "1h")


def test_find_latest_materialized_passes_none_through() -> None:
    """latest 查詢不轉換 mock registry 的 None。"""
    registry = MagicMock()
    registry.find_latest_materialized.return_value = None
    library = _library_with_registry(registry)

    assert library.find_latest_materialized("ETHUSDT", "1h") is None
    registry.find_latest_materialized.assert_called_once_with("ETHUSDT", "1h")
