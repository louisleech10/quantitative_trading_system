import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory


@pytest.fixture
def feature_factory() -> FeatureFactory:
    """建立最小 FeatureFactory 實例供 CGSA 測試使用。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = Mock()
    factory._registry = Mock()
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    return factory


def test_cgsa_deterministic_path(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試決定性路徑：相同 symbol、timeframe、hash 應產生相同 work_dir。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)

    registry_one = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "abcdef1234567890")
    registry_two = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "abcdef1234567890")

    expected = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_abcdef12").resolve()
    assert registry_one is not None
    assert registry_two is not None
    assert registry_one.work_dir == expected
    assert registry_two.work_dir == expected


def test_cgsa_resume_from_existing_manifest(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試既有 manifest：應走 resume_from_manifest 而非新建 Registry。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    work_dir = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_12345678").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
    expected_registry = ColumnGroupRegistry(work_dir=work_dir)
    resume_mock = Mock(return_value=expected_registry)
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume_mock)

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "1234567890abcdef")

    assert registry is expected_registry
    resume_mock.assert_called_once_with(work_dir)


def test_cgsa_force_fresh_skips_existing_manifest(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試 force_regenerate fresh run：既有 manifest 不應被 resume 重用。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    work_dir = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_12345678").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "manifest.json").write_text(json.dumps({"groups": []}), encoding="utf-8")
    resume_mock = Mock(return_value=ColumnGroupRegistry(work_dir=work_dir))
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", resume_mock)
    feature_factory._cgsa_force_fresh = True

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "1234567890abcdef")

    assert registry is not None
    assert registry.work_dir == work_dir
    assert resume_mock.call_count == 0


def test_cgsa_config_hash_passed_correctly(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """測試 generate_features：config_hash 應正確傳入 _prepare_cgsa_registry。"""
    config = SimpleNamespace(timeframes=SimpleNamespace(training=["1h"]))
    captured: dict[str, str] = {}

    monkeypatch.setattr(feature_factory, "_resolve_config", lambda override: config)
    monkeypatch.setattr(feature_factory, "_compute_config_hash", lambda *args, **kwargs: "1234567890abcdef")
    monkeypatch.setattr(feature_factory, "_try_load_cache", lambda *args, **kwargs: None)

    def fake_prepare(symbol: str, timeframe: str, config_hash: str = "") -> None:
        captured["symbol"] = symbol
        captured["timeframe"] = timeframe
        captured["config_hash"] = config_hash
        return None

    monkeypatch.setattr(feature_factory, "_prepare_cgsa_registry", fake_prepare)

    def stop_after_prepare(*args, **kwargs):
        raise RuntimeError("stop-after-prepare")

    monkeypatch.setattr(feature_factory, "_layer0_data_ingestion", stop_after_prepare)

    with pytest.raises(RuntimeError, match="stop-after-prepare"):
        feature_factory.generate_features("ETHUSDT", "1h", persist=False)

    assert captured == {
        "symbol": "ETHUSDT",
        "timeframe": "1h",
        "config_hash": "1234567890abcdef",
    }


def test_cgsa_corrupt_manifest_fallback(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試損壞 manifest：應 fallback 為新 Registry，不得拋例外。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    work_dir = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_deadbeef").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "manifest.json").write_text("{", encoding="utf-8")

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "deadbeefcafefeed")

    assert registry is not None
    assert registry.work_dir == work_dir


def test_cgsa_empty_config_hash(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試空 config_hash：work_dir 名稱應使用 nohash。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "")

    assert registry is not None
    assert registry.work_dir.name == "ETHUSDT_1h_nohash"


def test_cgsa_special_chars_in_symbol(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試特殊字元 symbol：應清理成可預測的安全路徑名稱。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)

    registry = feature_factory._prepare_cgsa_registry("BTC/USDT:PERP", "1h", "1122334455667788")

    assert registry is not None
    assert registry.work_dir.name == "BTC_USDT_PERP_1h_11223344"


def test_cgsa_work_dir_env_override(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試 FFACT_CGSA_WORK_DIR 覆蓋：應優先使用環境變數路徑。"""
    override_dir = tmp_path / "override_cgsa"
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(override_dir))

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "abcdef1234567890")

    assert registry is not None
    assert registry.work_dir == override_dir


def test_cgsa_empty_manifest_json(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試空 manifest.json：應 fallback 為新 Registry。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    work_dir = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_a1b2c3d4").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "manifest.json").write_text("", encoding="utf-8")

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "a1b2c3d4ef567890")

    assert registry is not None
    assert registry.work_dir == work_dir


def test_cgsa_missing_npy_files_in_manifest(
    feature_factory: FeatureFactory,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """測試 manifest 指向遺失 .npy：應跳過缺失 group 並維持可用 Registry。"""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    work_dir = (tmp_path / "data_cache" / "cgsa_work" / "ETHUSDT_1h_ffeeddcc").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest_payload = {
        "groups": [
            {
                "group_id": "1h_L1_trend_EMA",
                "layer": "L1",
                "timeframe": "1h",
                "data_source": "close",
                "indicator": "EMA",
                "columns": ["close_1h_trend_EMA_5"],
                "shape": [10, 1],
                "dtype": "float32",
                "npy_path": "missing.npy",
            }
        ]
    }
    (work_dir / "manifest.json").write_text(json.dumps(manifest_payload), encoding="utf-8")

    registry = feature_factory._prepare_cgsa_registry("ETHUSDT", "1h", "ffeeddcc99887766")

    assert registry is not None
    assert list(registry.iter_all()) == []