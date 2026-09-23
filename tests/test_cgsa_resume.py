import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from momentum.FeatureEngineering.feature_factory import FeatureFactory
from momentum.FeatureEngineering.feature_registry import FeatureRegistry
from momentum.FeatureEngineering.feature_storage import FeatureStorage


@pytest.fixture
def feature_factory(tmp_path: Path) -> FeatureFactory:
    """建立最小 FeatureFactory 實例供 CGSA 測試使用。"""
    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()
    factory._adapter_registry = Mock()
    factory._progress_callback = None
    factory._storage = FeatureStorage(str(tmp_path / "features"))
    factory._registry = FeatureRegistry(tmp_path / "registry.json")
    factory._validator = Mock()
    factory._current_symbol = None
    factory._current_timeframe = None
    factory._current_config_hash = None
    factory._current_raw_data = None
    factory._reference_data_cache = {}
    factory._cgsa_registry = None
    factory._cgsa_force_fresh = False
    factory.layer_results = {}
    return factory


def _write_complete_l7_manifest(
    factory: FeatureFactory,
    symbol: str,
    timeframe: str,
    config_hash: str,
) -> None:
    run_dir = factory._storage.feature_run_dir(symbol, timeframe, config_hash)
    run_dir.mkdir(parents=True, exist_ok=True)
    completeness = {
        "expected_layers": ["L1"],
        "present_layers": ["L1"],
        "failed_layers": [],
        "expected_timeframes": [timeframe],
        "present_timeframes": [timeframe],
        "failed_timeframes": [],
        "quality_status": "complete",
    }
    (run_dir / factory._storage.L7_V2_MANIFEST_NAME).write_text(
        json.dumps({"artifacts": {"raw": {"schema_version": "raw_v2", **completeness}}}),
        encoding="utf-8",
    )


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
    _write_complete_l7_manifest(feature_factory, "ETHUSDT", "1h", "1234567890abcdef")

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


# ---------------------------------------------------------------------------
# FF-TFMETA（docs/FFTFMETA_SPEC.md）Task 1.3：resume 保存逐週期層狀態
# ---------------------------------------------------------------------------

import dataclasses  # noqa: E402
import inspect  # noqa: E402
import logging  # noqa: E402

import pandas as pd  # noqa: E402

from momentum.core.contracts import LayerStatus  # noqa: E402
from momentum.FeatureEngineering.feature_config import AlignmentMode  # noqa: E402
from momentum.FeatureEngineering.feature_storage import resolve_completeness_meta  # noqa: E402
from momentum.FeatureEngineering.timeframe.multi_tf_generator import MultiTFGenerator  # noqa: E402
from tests.feature_engineering.test_failopen_producer import (  # noqa: E402
    _CgsaStubFactory,
    _ThreadPoolAsProcessPool,
)

_SIX_OK = {f"L{i}": ("ok", "") for i in range(1, 7)}
_CFG_HASH = "fftfmeta0resume0"
# 改前 registry 工作 manifest 之頂層鍵（Task 1.3 新欄之外者；用以造「舊 checkpoint」）
_PRE_FFTFMETA_WORK_KEYS = {
    "schema_version", "symbol", "primary_tf", "training_tfs", "config_hash", "config_snapshot",
    "total_features", "total_groups", "created_at", "groups",
}


class _ResumeTfs:
    primary = "1h"
    training = ["1h", "12h"]
    alignment_mode = AlignmentMode.OPEN_MINUS


class _ResumeConfig:
    def __init__(self) -> None:
        self.timeframes = _ResumeTfs()
        self.preprocessing = SimpleNamespace(enabled=False)
        self.allow_partial_timeframes = True
        self.allow_partial_layers = True


class _CanonicalStubFactory(_CgsaStubFactory):
    """L7 persist 樁：把 generator 傳入之 canonical 參數原樣交 `resolve_completeness_meta`（比照 Task 2.2 之 factory）。"""

    def __init__(self, data_by_tf: dict, registry: ColumnGroupRegistry) -> None:
        super().__init__(data_by_tf, registry)
        self.captured: dict = {}
        self.layer_results: dict = {}

    def _layer7_raw_from_cgsa_pipeline(self, symbol, timeframe, raw_data, config, elapsed, config_hash,
                                       compute_warnings=None, persist=True, batch_id=None, **canonical):
        result = super()._layer7_raw_from_cgsa_pipeline(
            symbol, timeframe, raw_data, config, elapsed, config_hash, compute_warnings, persist, batch_id
        )
        self.captured = dict(canonical)
        accepted = set(inspect.signature(resolve_completeness_meta).parameters)
        meta = resolve_completeness_meta(
            self.layer_results, timeframe, **{k: v for k, v in canonical.items() if k in accepted}
        )
        result.metadata.update(meta)
        result.metadata["run_status"] = meta["quality_status"]
        return result


def _resume_frames() -> dict:
    hourly = pd.DataFrame({"timestamp": [i * 3600 * 1000 for i in range(48)], "value": list(range(48))})
    half_day = pd.DataFrame({"timestamp": [i * 12 * 3600 * 1000 for i in range(4)], "value": [10, 11, 12, 13]})
    return {"1h": hourly, "12h": half_day}


def _generator(factory: object, monkeypatch: pytest.MonkeyPatch, *, parallel: bool, fail_12h_l2: bool) -> tuple:
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_MULTI_TF_PARALLEL", "1" if parallel else "0")
    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", _ThreadPoolAsProcessPool)
    gen = MultiTFGenerator(factory, _ResumeConfig())
    orig = gen._run_tf_l1_l6_results
    calls: list = []

    def run_layers(raw_data):
        calls.append(str(factory._current_timeframe))
        results = orig(raw_data)
        if fail_12h_l2 and factory._current_timeframe == "12h":
            results[1] = dataclasses.replace(results[1], status=LayerStatus.dependency_failed, reason="L1 missing")
        return results

    monkeypatch.setattr(gen, "_run_tf_l1_l6_results", run_layers)
    return gen, calls


def _checkpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, fail_12h_l2: bool = True) -> Path:
    """第一次（循序）run：於 work_dir 留下兩週期之 L1 群組與（實作後）逐週期層狀態。"""
    work_dir = (tmp_path / "work").resolve()
    factory = _CanonicalStubFactory(_resume_frames(), ColumnGroupRegistry(work_dir))
    gen, calls = _generator(factory, monkeypatch, parallel=False, fail_12h_l2=fail_12h_l2)
    gen.generate_multi_tf("BTCUSDT")
    assert calls == ["1h", "12h"]
    return work_dir


def _resume_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, feature_factory: FeatureFactory, work_dir: Path,
                *, parallel: bool, write_l7: bool = True) -> tuple:
    """第二次 run：經真實 `_prepare_cgsa_registry` 之 resume 閘取得 registry，再走 MultiTF（spy resume 與逐層執行）。"""
    monkeypatch.setenv("FFACT_USE_CGSA", "1")
    monkeypatch.setenv("FFACT_CGSA_WORK_DIR", str(work_dir))
    if write_l7:
        _write_complete_l7_manifest(feature_factory, "BTCUSDT", "1h", _CFG_HASH)
    spy = Mock(wraps=ColumnGroupRegistry.resume_from_manifest)
    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", spy)
    registry = feature_factory._prepare_cgsa_registry("BTCUSDT", "1h", _CFG_HASH)
    factory = _CanonicalStubFactory(_resume_frames(), registry)
    gen, calls = _generator(factory, monkeypatch, parallel=parallel, fail_12h_l2=True)
    gen.generate_multi_tf("BTCUSDT")
    return spy, calls, factory, registry


def _canonical(factory: _CanonicalStubFactory) -> dict:
    accepted = set(inspect.signature(resolve_completeness_meta).parameters)
    return resolve_completeness_meta(
        {}, "1h", **{k: v for k, v in factory.captured.items() if k in accepted}
    )


def test_layer_status_roundtrip_through_manifest_flushes(tmp_path: Path) -> None:
    """① 記憶體欄隨 write_manifest 落盤、resume 讀回同一欄；再 flush 一次後仍在（r2 grok P1-02）。"""
    statuses = {**_SIX_OK, "L2": ("dependency_failed", "L1 missing"), "L5": ("empty_disabled", "")}
    reg = ColumnGroupRegistry(tmp_path / "w")
    reg.record_layer_status("12h", statuses)
    reg.write_manifest()
    resumed = ColumnGroupRegistry.resume_from_manifest(tmp_path / "w")
    assert resumed.layer_status_by_tf == {"12h": statuses}
    resumed.write_manifest()
    again = ColumnGroupRegistry.resume_from_manifest(tmp_path / "w")
    assert again.layer_status_by_tf == {"12h": statuses}


def test_layer_status_record_replaces_whole_timeframe_entry(tmp_path: Path) -> None:
    """① 整組取代該週期舊條目；④ stale alignment 重跑以新六層取代舊條目。"""
    reg = ColumnGroupRegistry(tmp_path / "w")
    reg.record_layer_status("12h", {**_SIX_OK, "L3": ("layer_failed", "old")})
    reg.record_layer_status("12h", _SIX_OK)
    reg.record_layer_status("1h", _SIX_OK)
    assert reg.layer_status_by_tf == {"12h": _SIX_OK, "1h": _SIX_OK}


@pytest.mark.parametrize("parallel", [False, True], ids=["serial", "parallel"])
def test_layer_status_skip_branch_reads_back_failures(
    parallel: bool, feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """驗證①跳過分支：resume_from_manifest 被呼叫、兩週期皆跳過（不再執行 L1–L6），canonical 含讀回之 L2:12h 失敗。"""
    work_dir = _checkpoint(tmp_path, monkeypatch)
    spy, calls, factory, registry = _resume_run(tmp_path, monkeypatch, feature_factory, work_dir, parallel=parallel)
    assert spy.call_count == 1
    assert calls == []
    meta = _canonical(factory)
    assert meta["failed_layers"] == ["L2:12h"]
    assert any(reason.startswith("L2:12h:") for reason in meta["failure_reasons"])
    assert meta["quality_status"] == "partial"
    assert meta["expected_timeframes"] == ["1h", "12h"]
    assert "L1" in meta["expected_layers"] and "L1" in meta["present_layers"]
    registry.write_manifest()
    reread = json.loads((work_dir / "manifest.json").read_text(encoding="utf-8"))
    assert set(reread) - _PRE_FFTFMETA_WORK_KEYS, "再 flush 後工作 manifest 須仍帶逐週期層狀態欄"
    assert set(ColumnGroupRegistry.resume_from_manifest(work_dir).layer_status_by_tf) == {"1h", "12h"}


def test_layer_status_old_checkpoint_without_field_is_unknown(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """驗證①：無逐週期層狀態之同形 checkpoint ⇒ 缺證據 ⇒ quality_status == unknown（不得解為無失敗）。"""
    work_dir = _checkpoint(tmp_path, monkeypatch)
    manifest_path = work_dir / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_path.write_text(
        json.dumps({k: v for k, v in payload.items() if k in _PRE_FFTFMETA_WORK_KEYS}, ensure_ascii=False),
        encoding="utf-8",
    )
    _spy, calls, factory, _registry = _resume_run(tmp_path, monkeypatch, feature_factory, work_dir, parallel=False)
    assert calls == []
    meta = _canonical(factory)
    assert meta["quality_status"] == "unknown"
    assert meta["expected_timeframes"] == ["1h", "12h"] and meta["present_timeframes"] == ["1h", "12h"]


def test_layer_status_gate_refusal_recomputes(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """驗證②閘拒絕分支（對照）：無 L7 manifest ⇒ resume_from_manifest 未被呼叫、兩週期層重算，completeness 為重算結果。"""
    work_dir = _checkpoint(tmp_path, monkeypatch)
    spy, calls, factory, _registry = _resume_run(
        tmp_path, monkeypatch, feature_factory, work_dir, parallel=False, write_l7=False
    )
    assert spy.call_count == 0
    assert calls == ["1h", "12h"]
    meta = _canonical(factory)
    assert meta["failed_layers"] == ["L2:12h"]
    assert meta["quality_status"] == "partial"


def test_boundary_08_layer_status_all_skipped_healthy_complete(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """邊界①：全部週期皆由 checkpoint 跳過、層狀態全數讀回，健康者 quality_status == complete。"""
    work_dir = _checkpoint(tmp_path, monkeypatch, fail_12h_l2=False)
    spy, calls, factory, _registry = _resume_run(tmp_path, monkeypatch, feature_factory, work_dir, parallel=False)
    assert spy.call_count == 1 and calls == []
    meta = _canonical(factory)
    assert meta["quality_status"] == "complete"
    assert meta["failed_layers"] == []


def test_boundary_09_layer_status_foreign_timeframe_ignored_with_warning(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """邊界②：checkpoint 之逐週期層狀態含 training 以外之週期 ⇒ 忽略並記 warning。"""
    work_dir = _checkpoint(tmp_path, monkeypatch, fail_12h_l2=False)
    reg = ColumnGroupRegistry.resume_from_manifest(work_dir)
    reg.record_layer_status("4h", {**_SIX_OK, "L3": ("layer_failed", "foreign")})
    reg.write_manifest()
    with caplog.at_level(logging.WARNING):
        _spy, calls, factory, _registry = _resume_run(tmp_path, monkeypatch, feature_factory, work_dir, parallel=False)
    meta = _canonical(factory)
    assert calls == []
    assert meta["quality_status"] == "complete"
    assert all("4h" not in item for item in meta["failed_layers"] + meta["failure_reasons"])
    assert any("4h" in record.getMessage() for record in caplog.records if record.levelno >= logging.WARNING)


def test_boundary_10_layer_status_partial_entry_is_unknown(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """邊界③：條目只涵蓋部分層（12h 只記 L1）⇒ quality_status == unknown。"""
    work_dir = _checkpoint(tmp_path, monkeypatch, fail_12h_l2=False)
    reg = ColumnGroupRegistry.resume_from_manifest(work_dir)
    reg.record_layer_status("12h", {"L1": ("ok", "")})
    reg.write_manifest()
    _spy, calls, factory, _registry = _resume_run(tmp_path, monkeypatch, feature_factory, work_dir, parallel=False)
    assert calls == []
    assert _canonical(factory)["quality_status"] == "unknown"


@pytest.mark.requires_kline
def test_layer_status_parallel_rollback_clears_entry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """驗證①：parallel 路徑 12h 群組註冊失敗 rollback ⇒ 該週期無層狀態條目；primary 仍有六層（真實 kline 輕量 run）。"""
    from tests.feature_engineering import fftfmeta_golden_helpers as fg

    fg.prepare_env(monkeypatch, tmp_path, FFACT_USE_CGSA="1", FFACT_MULTI_TF_PARALLEL="1")
    monkeypatch.setattr("concurrent.futures.ProcessPoolExecutor", _ThreadPoolAsProcessPool)

    def _fail_register(self, registry, groups_data, tf, *args, **kwargs):
        raise RuntimeError(f"injected registration failure for {tf}")

    monkeypatch.setattr(MultiTFGenerator, "_register_worker_groups", _fail_register)
    payload = fg.fast_payload(["1h", "12h"], **fg.HEALTHY, allow_partial_timeframes=True)
    _root, factory, result = fg.generate(tmp_path, payload)
    statuses = factory._cgsa_registry.layer_status_by_tf
    assert "12h" not in statuses
    assert set(statuses.get("1h", {})) == {f"L{i}" for i in range(1, 7)}
    assert result.metadata["failed_timeframes"] == ["12h"]


def test_mutation_layer_status_dropped_on_resume_is_caught(
    feature_factory: FeatureFactory, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """改壞：resume 只讀進區域變數（記憶體欄為空）⇒ 跳過分支之讀回失敗必紅（r2 grok P1-02 之形）。"""
    real_resume = ColumnGroupRegistry.resume_from_manifest.__func__

    def _mutant(cls, work_dir):
        registry = real_resume(cls, work_dir)
        registry.record_layer_status("1h", {})
        registry.record_layer_status("12h", {})
        return registry

    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(_mutant))
    with pytest.raises(AssertionError):
        test_layer_status_skip_branch_reads_back_failures(False, feature_factory, monkeypatch, tmp_path)
