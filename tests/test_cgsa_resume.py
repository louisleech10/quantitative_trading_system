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


# ──────────────────────────────────────────────────────────────────
# Resume support: registry helpers & multi-TF skip-completed
# (added 2026-04-25 to fix OOM-mid-pipeline restart)
# ──────────────────────────────────────────────────────────────────


def _make_group(
    group_id: str,
    layer: str,
    tf: str,
    n_rows: int = 4,
    n_cols: int = 2,
    work_dir=None,
):
    """建立一個帶有實體 .npy 的 ColumnGroup，便於 register/save_data 路徑測試。"""
    import numpy as np
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource

    npy_path = (work_dir / f"{group_id}.npy") if work_dir is not None else None
    if npy_path is not None:
        npy_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(npy_path, np.zeros((n_rows, n_cols), dtype=np.float32))
    return ColumnGroup(
        group_id=group_id,
        layer=LayerSource(layer),
        timeframe=tf,
        data_source="ms",
        indicator="dummy",
        columns=tuple(f"c{i}" for i in range(n_cols)),
        shape=(n_rows, n_cols),
        dtype="float32",
        disk_path=npy_path,
    )


def test_has_layers_for_timeframe_returns_true_when_all_present(tmp_path: Path) -> None:
    """has_layers_for_timeframe: TF 完整擁有指定 layer 時回傳 True。"""
    from momentum.FeatureEngineering.core.column_group import LayerSource

    registry = ColumnGroupRegistry(work_dir=tmp_path)
    for layer in ("L1", "L2", "L3", "L4", "L5", "L6"):
        registry.register(_make_group(f"1h_{layer}_x", layer, "1h"))

    assert registry.has_layers_for_timeframe(
        "1h",
        [LayerSource.L1, LayerSource.L2, LayerSource.L3,
         LayerSource.L4, LayerSource.L5, LayerSource.L6],
    ) is True


def test_has_layers_for_timeframe_returns_false_when_any_missing(tmp_path: Path) -> None:
    """has_layers_for_timeframe: 缺任一 layer 即回傳 False。"""
    from momentum.FeatureEngineering.core.column_group import LayerSource

    registry = ColumnGroupRegistry(work_dir=tmp_path)
    # 只註冊到 L5，缺 L6
    for layer in ("L1", "L2", "L3", "L4", "L5"):
        registry.register(_make_group(f"12h_{layer}_x", layer, "12h"))

    assert registry.has_layers_for_timeframe(
        "12h",
        [LayerSource.L1, LayerSource.L2, LayerSource.L3,
         LayerSource.L4, LayerSource.L5, LayerSource.L6],
    ) is False


def test_has_layers_for_timeframe_isolates_by_tf(tmp_path: Path) -> None:
    """has_layers_for_timeframe: 不同 TF 的 group 不應跨 TF 計算。"""
    from momentum.FeatureEngineering.core.column_group import LayerSource

    registry = ColumnGroupRegistry(work_dir=tmp_path)
    for layer in ("L1", "L2", "L3", "L4", "L5", "L6"):
        registry.register(_make_group(f"1h_{layer}_x", layer, "1h"))
    # 12h 只有 L1
    registry.register(_make_group("12h_L1_y", "L1", "12h"))

    layers_all = [LayerSource.L1, LayerSource.L2, LayerSource.L3,
                  LayerSource.L4, LayerSource.L5, LayerSource.L6]
    assert registry.has_layers_for_timeframe("1h", layers_all) is True
    assert registry.has_layers_for_timeframe("12h", layers_all) is False


def test_write_manifest_persists_register_only_groups(tmp_path: Path) -> None:
    """register() 不寫 manifest；呼叫 write_manifest() 後 manifest 須包含這些 group。

    這是 OOM resume 修正的核心：worker TF 走 register()，必須顯式 flush 才能 resume。
    """
    registry = ColumnGroupRegistry(work_dir=tmp_path)
    registry.save_state(
        symbol="BTCUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        config_hash="abc",
        config_snapshot={},
    )
    # 模擬 worker：透過 register() 加入 12h L1 group
    registry.register(_make_group("12h_L1_a", "L1", "12h", work_dir=tmp_path))
    registry.register(_make_group("12h_L2_a", "L2", "12h", work_dir=tmp_path))

    manifest_path = tmp_path / "manifest.json"
    # save_state 已寫過一次，但僅含初始狀態 (0 group)
    payload_before = json.loads(manifest_path.read_text())
    pre_ids = {g["group_id"] for g in payload_before.get("groups", [])}
    assert "12h_L1_a" not in pre_ids, "register() 不應觸發 manifest write"

    # 顯式 flush
    registry.write_manifest()
    payload_after = json.loads(manifest_path.read_text())
    post_ids = {g["group_id"] for g in payload_after.get("groups", [])}
    assert {"12h_L1_a", "12h_L2_a"}.issubset(post_ids)


def test_resume_from_manifest_round_trips_register_only_groups(tmp_path: Path) -> None:
    """write_manifest → resume_from_manifest 來回後，可重建出 register() 加入的 group。"""
    from momentum.FeatureEngineering.core.column_group import LayerSource

    work_dir = tmp_path / "rr"
    work_dir.mkdir()

    reg1 = ColumnGroupRegistry(work_dir=work_dir)
    reg1.save_state(
        symbol="BTCUSDT",
        primary_tf="1h",
        training_tfs=["1h", "12h"],
        config_hash="xyz",
        config_snapshot={},
    )
    for layer in ("L1", "L2", "L3", "L4", "L5", "L6"):
        reg1.register(_make_group(f"1h_{layer}_g", layer, "1h", work_dir=work_dir))
    reg1.register(_make_group("12h_L1_g", "L1", "12h", work_dir=work_dir))
    reg1.write_manifest()

    reg2 = ColumnGroupRegistry.resume_from_manifest(work_dir)
    layers_all = [LayerSource.L1, LayerSource.L2, LayerSource.L3,
                  LayerSource.L4, LayerSource.L5, LayerSource.L6]
    assert reg2.has_layers_for_timeframe("1h", layers_all) is True
    assert reg2.has_layers_for_timeframe("12h", layers_all) is False  # 只有 L1
    assert reg2.has_layers_for_timeframe("12h", [LayerSource.L1]) is True


def test_collect_layer_counts_from_registry(tmp_path: Path) -> None:
    """_collect_layer_counts_from_registry: 從 registry 重建各 layer 的欄位數。

    用於 resume：當 TF 被 skip 時，仍需正確回報 layer counts。
    """
    from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator

    registry = ColumnGroupRegistry(work_dir=tmp_path)
    registry.register(_make_group("1h_L1_a", "L1", "1h", n_cols=10))
    registry.register(_make_group("1h_L1_b", "L1", "1h", n_cols=5))   # 同 layer 多 group → 累加
    registry.register(_make_group("1h_L2_a", "L2", "1h", n_cols=20))
    registry.register(_make_group("1h_L3_a", "L3", "1h", n_cols=30))
    registry.register(_make_group("1h_L4_a", "L4", "1h", n_cols=4))
    registry.register(_make_group("1h_L5_a", "L5", "1h", n_cols=2))
    registry.register(_make_group("1h_L6_a", "L6", "1h", n_cols=1))
    # 不同 TF 不應被計入 1h
    registry.register(_make_group("12h_L1_a", "L1", "12h", n_cols=99))

    counts = MultiTFGenerator._collect_layer_counts_from_registry(registry, "1h")
    assert counts == {
        "layer1": 15,
        "layer2": 20,
        "layer3": 30,
        "layer4": 4,
        "layer5": 2,
        "layer6": 1,
    }
