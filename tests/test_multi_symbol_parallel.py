"""Phase 5 tests — V7 storage infrastructure, multi-symbol parallel, Arrow IPC.

Test IDs from FEATURE_FACTORY_OPTIMIZATION_TODO.md Phase 5 test matrix:
  T5.0a ~ T5.0g: V7 P0 storage infrastructure
  T5.1 ~ T5.2: Multi-symbol parallel correctness
  T5.3a ~ T5.3d: FeatureReader 4-mode validation
  T5.B1 ~ T5.B3: Boundary conditions
"""

from __future__ import annotations

import gzip
import json
import os
from unittest.mock import patch

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_output_dir(tmp_path):
    """Temporary output directory for persist tests."""
    return tmp_path / "features"


@pytest.fixture()
def sample_registry(tmp_path):
    """Create a mock ColumnGroupRegistry with synthetic groups for testing."""
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    registry = ColumnGroupRegistry(work_dir=work_dir)

    rng = np.random.default_rng(42)
    n_rows = 100

    # Group with 10 columns
    data_small = rng.standard_normal((n_rows, 10)).astype(np.float32)
    cols_small = tuple(f"feat_small_{i}" for i in range(10))
    npy_path = work_dir / "small.npy"
    np.save(npy_path, data_small)
    group_small = ColumnGroup(
        group_id="small",
        layer=LayerSource.L1,
        timeframe="1h",
        data_source="close",
        indicator="test",
        columns=cols_small,
        shape=data_small.shape,
        dtype="float32",
        disk_path=npy_path,
    )
    registry.register(group_small)

    # Group with 20 columns
    data_medium = rng.standard_normal((n_rows, 20)).astype(np.float32)
    cols_medium = tuple(f"feat_medium_{i}" for i in range(20))
    npy_path2 = work_dir / "medium.npy"
    np.save(npy_path2, data_medium)
    group_medium = ColumnGroup(
        group_id="medium",
        layer=LayerSource.L2,
        timeframe="1h",
        data_source="close",
        indicator="test2",
        columns=cols_medium,
        shape=data_medium.shape,
        dtype="float32",
        disk_path=npy_path2,
    )
    registry.register(group_medium)

    return registry, data_small, data_medium


@pytest.fixture()
def large_registry(tmp_path):
    """Registry with a group exceeding MAX_GROUP_COLUMNS (5000+)."""
    from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
    from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry

    work_dir = tmp_path / "work_large"
    work_dir.mkdir()
    registry = ColumnGroupRegistry(work_dir=work_dir)

    rng = np.random.default_rng(99)
    n_rows = 50
    n_cols = 5003  # Exceeds MAX_GROUP_COLUMNS (5000)

    data = rng.standard_normal((n_rows, n_cols)).astype(np.float32)
    cols = tuple(f"feat_huge_{i}" for i in range(n_cols))
    npy_path = work_dir / "huge.npy"
    np.save(npy_path, data)
    group = ColumnGroup(
        group_id="huge",
        layer=LayerSource.L3,
        timeframe="1h",
        data_source="close",
        indicator="test_huge",
        columns=cols,
        shape=data.shape,
        dtype="float32",
        disk_path=npy_path,
    )
    registry.register(group)

    return registry, data




# ===========================================================================
# T5.0a: manifest.json + columns.json.gz written after persist
# ===========================================================================



# ===========================================================================
# T5.0b: float16 storage precision
# ===========================================================================

class TestT50bFloat16Precision:
    """T5.0b — float16 與 float32 差異 + NaN 保留"""

    def test_relative_diff_within_tolerance(self, tmp_output_dir, sample_registry):
        """FRAMEPATH Task 2.5：V1 版面寫讀已刪；改以 V2 串流寫入（write_raw_from_registry_stream）寫、load_columns_v2 讀回，驗 float16 精度。"""
        from momentum.FeatureEngineering.feature_reader import FeatureReader
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data_small, _ = sample_registry
        symbol, tf, config_hash = "TESTUSDT", "1h", "abc123"
        storage = FeatureStorage(base_path=str(tmp_output_dir))
        storage.write_raw_from_registry_stream(symbol, tf, config_hash, registry)

        reader = FeatureReader(str(tmp_output_dir))
        selected = [f"feat_small_{index}" for index in range(data_small.shape[1])]
        loaded = reader.load_columns_v2(symbol, tf, config_hash, selected).values.astype(np.float32)

        assert loaded.shape == data_small.shape
        expected_f16 = data_small.astype(np.float16).astype(np.float32)
        np.testing.assert_allclose(
            loaded,
            expected_f16,
            atol=np.finfo(np.float16).eps * 10,
            rtol=0,
        )

    def test_nan_preserved(self, tmp_path):
        """NaN positions must be preserved through float16 round-trip. FRAMEPATH Task 2.5：V1 版面寫入已刪；改走 V2 串流寫入 write_raw_from_registry_stream。"""
        from momentum.FeatureEngineering.core.column_group import ColumnGroup, LayerSource
        from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        work_dir = tmp_path / "nan_test"
        work_dir.mkdir()
        registry = ColumnGroupRegistry(work_dir=work_dir)

        data = np.array([[1.0, np.nan, 3.0], [np.nan, 5.0, 6.0]], dtype=np.float32)
        npy_path = work_dir / "nan_group.npy"
        np.save(npy_path, data)
        group = ColumnGroup(
            group_id="nan_group",
            layer=LayerSource.L1,
            timeframe="1h",
            data_source="close",
            indicator="nan_test",
            columns=("a", "b", "c"),
            shape=data.shape,
            dtype="float32",
            disk_path=npy_path,
        )
        registry.register(group)

        output_dir = tmp_path / "out"
        storage = FeatureStorage(base_path=str(output_dir))
        raw_dir, _summary = storage.write_raw_from_registry_stream("TEST", "1h", "h1", registry)

        loaded = pq.read_table(raw_dir / "nan_group.parquet").to_pandas()
        original_nan_mask = np.isnan(data)
        loaded_nan_mask = loaded.isna().values
        np.testing.assert_array_equal(original_nan_mask, loaded_nan_mask)


# ===========================================================================
# T5.0c: max_group_split
# ===========================================================================

class TestT50cMaxGroupSplit:
    """T5.0c — >5000 columns 自動拆分"""

    def test_split_creates_parts(self, tmp_path, large_registry):
        """FRAMEPATH Task 2.5：V1 版面寫入已刪；改驗 V2 串流寫入（共用 _split_large_group）之拆分結果。"""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out"
        storage = FeatureStorage(base_path=str(output_dir))
        raw_dir, _summary = storage.write_raw_from_registry_stream("SPLITUSDT", "1h", "s1", registry)

        out = raw_dir.parent
        with open(out / "feature_manifest.json") as f:
            manifest = json.load(f)

        # Should have 2 parts: 5000 + 3
        assert len(manifest["groups"]) == 2
        group_ids = sorted(manifest["groups"].keys())
        assert "huge_part1" in group_ids[0]
        assert "huge_part2" in group_ids[1]
        assert (raw_dir / "huge_part1.parquet").exists()
        assert (raw_dir / "huge_part2.parquet").exists()

    def test_split_column_count_correct(self, tmp_path, large_registry):
        """FRAMEPATH Task 2.5：V1 版面寫入已刪；改驗 V2 串流寫入（共用 _split_large_group）之逐 part 欄數。"""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, data = large_registry
        output_dir = tmp_path / "split_out2"
        storage = FeatureStorage(base_path=str(output_dir))
        raw_dir, _summary = storage.write_raw_from_registry_stream("SPLITUSDT", "1h", "s2", registry)

        out = raw_dir.parent
        with open(out / "feature_manifest.json") as f:
            manifest = json.load(f)

        part1 = manifest["groups"]["huge_part1"]
        part2 = manifest["groups"]["huge_part2"]
        assert part1["column_count"] == 5000
        assert part2["column_count"] == 3
        assert manifest["total_features"] == 5003

    def test_no_split_at_boundary(self):
        """Exactly 5000 columns should NOT be split."""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        columns = [f"c_{i}" for i in range(5000)]
        data = np.zeros((10, 5000), dtype=np.float32)
        parts = FeatureStorage._split_large_group("g", columns, data)
        assert len(parts) == 1
        assert parts[0][0] == "g"


# ===========================================================================
# T5.0d / T5.3a: FeatureReader metadata-only
# ===========================================================================



# ===========================================================================
# T5.0e / T5.3b: FeatureReader column projection
# ===========================================================================



# ===========================================================================
# T5.0f / T5.3c: FeatureReader stream_groups
# ===========================================================================



# ===========================================================================
# T5.0g: FeatureLibrary uses FeatureReader (no h5py import)
# ===========================================================================

class TestT50gLibraryUsesReader:
    """T5.0g — FeatureLibrary.load() delegates to FeatureReader"""

    def test_no_h5py_in_library(self):
        """feature_library.py should NOT import h5py."""
        import inspect
        from momentum.FeatureEngineering import feature_library

        source = inspect.getsource(feature_library)
        assert "import h5py" not in source


# ===========================================================================
# T5.1: Multi-symbol parallel correctness (unit-level mock test)
# ===========================================================================

class TestT51MultiSymbolParallel:
    """T5.1 — multi-symbol parallel golden comparison (mocked)."""

    def test_warmup_numba_functions(self):
        """Numba warmup runs without error."""
        from momentum.FeatureEngineering.feature_factory import _warmup_numba_functions
        # Should not raise
        _warmup_numba_functions()

    def test_split_large_group_util(self):
        """_split_large_group correctly splits > 5000 columns."""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        cols = [f"c{i}" for i in range(7500)]
        data = np.zeros((10, 7500), dtype=np.float32)
        parts = FeatureStorage._split_large_group("big", cols, data)
        assert len(parts) == 2
        assert parts[0][0] == "big_part1"
        assert len(parts[0][1]) == 5000
        assert parts[1][0] == "big_part2"
        assert len(parts[1][1]) == 2500


class TestMultiSymbolReferenceIpcCleanup:
    """FFSTAT b3 r5（CODEX-R5-P2-01）：run_multi_symbol 之參考資料 IPC 暫存目錄（ffact_multi_*）於所有出口皆刪。
    參考資料取自真實 kline；只以假 pool 取代子程序（驗資源生命週期，不驗特徵值）。拿掉 finally 清理 ⇒ 紅。"""

    @staticmethod
    def _run(monkeypatch, tmp_path, pool_cls):
        import concurrent.futures as cf
        import tempfile

        from momentum.factories import create_feature_factory
        from momentum.FeatureEngineering import arrow_ipc_utils
        from momentum.FeatureEngineering import feature_factory as ff_mod

        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))  # 失敗時殘留只落在本測試目錄
        monkeypatch.setattr(ff_mod, "_warmup_numba_functions", lambda: None)
        monkeypatch.setattr(cf, "ProcessPoolExecutor", pool_cls)
        # ICFIRSTALIGN Task 4.2：run_multi_symbol 經預算域排程器；完整預設設定之全史 E 不可准入（走串行臂、不經 pool）
        # ⇒ 注入固定 E 使任務准入假 pool（本類只驗 IPC 目錄生命週期，不驗估算）
        monkeypatch.setattr(ff_mod.FeatureFactory, "_estimate_symbol_envelope",
                            lambda self, symbol, config, end_date=None: 64 * 1024 * 1024)
        # SPEC v37：准入另判同容器檔案寫入上界 D（完整預設設定之全史 D 遠超可用磁碟 ⇒ 不准入）；本類不驗估算 ⇒ 注入 0
        monkeypatch.setattr(ff_mod.FeatureFactory, "_estimate_symbol_disk",
                            lambda self, symbol, config, end_date=None: 0)
        created: list = []
        real_write = arrow_ipc_utils.write_reference_data_ipc

        def _spy_write(ref_df, work_dir, ref_symbol):
            created.append(work_dir)
            return real_write(ref_df, work_dir, ref_symbol)

        monkeypatch.setattr(arrow_ipc_utils, "write_reference_data_ipc", _spy_write)
        factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
        payload = {"timeframes": {"primary": "1h", "training": ["1h"]},
                   "cross_sectional": {"enabled": True, "reference_symbol": "ETHUSDT"}}
        try:
            out = factory.run_multi_symbol(["ADAUSDT"], config_override=payload, max_workers=1)
        finally:
            assert len(created) == 1, created
            assert created[0].name.startswith("ffact_multi_")
        return out, created[0]

    @pytest.mark.requires_kline
    def test_ipc_workdir_removed_after_success(self, monkeypatch, tmp_path):
        import concurrent.futures as cf

        class _DonePool:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def shutdown(self, wait=True):
                pass

            def submit(self, fn, descriptor, worker_fn, payload, identity):
                # 排程器以 `_trampoline(descriptor, worker_fn, payload, identity)` 派工；payload 同改前之 worker 參數
                ref_ipc_path = payload["ref_ipc_path"]
                assert ref_ipc_path and os.path.exists(ref_ipc_path)  # 派工當下 IPC 仍在
                future = cf.Future()
                future.set_result({"ok": True})
                return future

        (results, errors), work_dir = self._run(monkeypatch, tmp_path, _DonePool)
        assert results == {"ADAUSDT": {"ok": True}} and errors == {}
        assert not work_dir.exists()

    @pytest.mark.requires_kline
    def test_ipc_workdir_removed_when_pool_raises(self, monkeypatch, tmp_path):
        class _BrokenPool:
            def __init__(self, *args, **kwargs):
                raise RuntimeError("pool start failed")

        created: list = []
        with pytest.raises(RuntimeError, match="pool start failed"):
            try:
                self._run(monkeypatch, tmp_path, _BrokenPool)
            finally:
                created.extend(p for p in tmp_path.iterdir() if p.name.startswith("ffact_multi_"))
        assert created == [], created


# ===========================================================================
# T5.2: No crosstalk between workers (unit-level)
# ===========================================================================

class TestT52NoCrosstalk:
    """T5.2 — symbol isolation: each worker has independent registry."""

    def test_worker_entry_isolation(self, tmp_path, monkeypatch):
        """_worker_entry is module-level and importable (picklable).

        TESTREG Task 4.4：原只斷言 callable，未驗類別所宣稱之「每個 worker 有獨立 registry」。補：
        ①pickle 往返後仍為同一模組層函式（spawn 派工之前提）；②連續兩次呼叫真實 _worker_entry（只 stub 下游
        generate_features）⇒ 各自建立不同之 factory、registry 與參考快取物件，且第一個標的注入之參考資料
        不外溢至第二個標的（無跨標的串擾）。
        """
        from momentum.FeatureEngineering.feature_factory import _worker_entry
        assert callable(_worker_entry)

        import pickle
        from types import SimpleNamespace

        from momentum.FeatureEngineering import feature_factory as ff_mod
        from momentum.FeatureEngineering.arrow_ipc_utils import write_reference_data_ipc

        assert pickle.loads(pickle.dumps(_worker_entry)) is _worker_entry

        seen: list = []

        def _stub_generate_features(self, **kwargs):
            seen.append({
                "symbol": kwargs["symbol"],
                "factory": self,
                "registry": self._registry,
                "ref_cache": self._reference_data_cache,
                "ref_keys": sorted(self._reference_data_cache.keys(), key=repr),
            })
            return SimpleNamespace(metadata={"symbol": kwargs["symbol"]})

        monkeypatch.setattr(ff_mod.FeatureFactory, "generate_features", _stub_generate_features)
        ref_df = pd.DataFrame({"close": np.arange(16, dtype=float), "volume": np.ones(16)})
        ipc_path = write_reference_data_ipc(ref_df, tmp_path, "ETHUSDT")
        payload = {"timeframes": {"training": ["1h"]}, "cross_sectional": {"reference_symbol": "ETHUSDT"}}

        out_a = ff_mod._worker_entry(symbol="ADAUSDT", config_payload=payload, cache_dir=None,
                                     ref_ipc_path=str(ipc_path))
        out_b = ff_mod._worker_entry(symbol="SOLUSDT", config_payload=payload, cache_dir=None,
                                     ref_ipc_path=None)

        assert out_a == {"symbol": "ADAUSDT"} and out_b == {"symbol": "SOLUSDT"}
        assert [entry["symbol"] for entry in seen] == ["ADAUSDT", "SOLUSDT"]
        first, second = seen
        assert first["factory"] is not second["factory"]
        assert first["registry"] is not second["registry"]
        assert first["ref_cache"] is not second["ref_cache"]
        assert first["ref_keys"] == [("ETHUSDT", "1h", None, None)]
        assert second["ref_keys"] == []

    def test_worker_entry_ref_cache_key_matches_config(self, tmp_path, monkeypatch):
        """Regression (:4109): worker 注入參考資料的 cache key 必須取自
        config.cross_sectional.reference_symbol（讀取端用的同一來源），
        而非硬編碼 "BTCUSDT"。否則參考標的非 BTC 時讀取端會靜默用錯標的。

        真碰路徑：呼叫真實 _worker_entry、寫/讀真實 Arrow IPC；只 stub 下游
        generate_features 以攔截 worker 內部 factory 的 _reference_data_cache。
        """
        from types import SimpleNamespace

        from momentum.FeatureEngineering import feature_factory as ff_mod
        from momentum.FeatureEngineering.arrow_ipc_utils import write_reference_data_ipc

        # 真實 IPC：參考標的刻意設為非 BTC，才能抓出硬編碼 bug
        ref_symbol = "ETHUSDT"
        ref_df = pd.DataFrame(
            {"close": np.random.randn(64), "volume": np.random.randn(64)}
        )
        ipc_path = write_reference_data_ipc(ref_df, tmp_path, ref_symbol)

        captured: dict = {}

        def _stub_generate_features(self, **kwargs):
            # 攔截 worker 內部 factory 的參考 cache 狀態
            captured["cache_keys"] = list(self._reference_data_cache.keys())
            return SimpleNamespace(metadata={"ok": True})

        monkeypatch.setattr(
            ff_mod.FeatureFactory, "generate_features", _stub_generate_features
        )

        config_payload = {
            "timeframes": {"training": ["1h"]},
            "cross_sectional": {"reference_symbol": ref_symbol},
        }

        ff_mod._worker_entry(
            symbol="ADAUSDT",
            config_payload=config_payload,
            cache_dir=None,
            ref_ipc_path=str(ipc_path),
        )

        # FFSTAT b3 r4：快取鍵含載入時間窗；預載為全歷史 ⇒ (參考標的, 週期, None, None)
        assert (ref_symbol, "1h", None, None) in captured["cache_keys"], (
            f"參考資料應以 config 的 reference_symbol={ref_symbol} 為 cache key，"
            f"實際: {captured['cache_keys']}"
        )
        assert not any(key[:2] == ("BTCUSDT", "1h") for key in captured["cache_keys"]), (
            "不得把參考資料寫進硬編碼的 BTCUSDT key（:4109 bug）"
        )


# ===========================================================================
# T5.3d: FeatureReader cross-symbol
# ===========================================================================



# ===========================================================================
# T5.B1: Single symbol failure
# ===========================================================================

class TestT5B1SingleFailure:
    """T5.B1 — one symbol failure doesn't block others."""

    def test_partial_failure(self, tmp_path, monkeypatch):
        """If _worker_entry raises, other symbols should still succeed.

        TESTREG Task 4.4：原只驗屬性與簽章。補：呼叫真實 run_multi_symbol（真實預算域排程器），以假 pool
        於派工當下呼叫模組層 _worker_entry（stub：BADUSDT 拋錯、其餘回傳 metadata）⇒ 失敗標的進 errors、
        其餘標的照常進 results，回傳 (results, errors)。不讀 kline（參考資料載入 stub 為 None）。
        """
        from momentum.FeatureEngineering.feature_factory import FeatureFactory
        assert hasattr(FeatureFactory, "run_multi_symbol")
        # run_multi_symbol returns (results, errors) tuple
        import inspect
        sig = inspect.signature(FeatureFactory.run_multi_symbol)
        assert "symbols" in sig.parameters

        import concurrent.futures as cf
        import tempfile

        from momentum.FeatureEngineering import feature_factory as ff_mod

        def _stub_worker_entry(symbol, config_payload, cache_dir, ref_ipc_path):
            if symbol == "BADUSDT":
                raise RuntimeError("injected worker failure for BADUSDT")
            return {"symbol": symbol}

        class _InlinePool:
            def __init__(self, *args, **kwargs):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def shutdown(self, wait=True):
                pass

            def submit(self, fn, descriptor, worker_fn, payload, identity):
                future = cf.Future()
                try:
                    future.set_result(ff_mod._worker_entry(**payload))
                except Exception as exc:  # noqa: BLE001 — 轉交 future，同真實 pool 之語意
                    future.set_exception(exc)
                return future

        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
        monkeypatch.setattr(ff_mod, "_warmup_numba_functions", lambda: None)
        monkeypatch.setattr(ff_mod, "_worker_entry", _stub_worker_entry)
        monkeypatch.setattr(cf, "ProcessPoolExecutor", _InlinePool)
        monkeypatch.setattr(ff_mod.FeatureFactory, "_load_reference_if_available",
                            lambda self, symbol, config: None)
        # 排程器准入：固定小 E 與 0 磁碟上界，使任務派入假 pool（本測試不驗估算）
        monkeypatch.setattr(ff_mod.FeatureFactory, "_estimate_symbol_envelope",
                            lambda self, symbol, config, end_date=None: 64 * 1024 * 1024)
        monkeypatch.setattr(ff_mod.FeatureFactory, "_estimate_symbol_disk",
                            lambda self, symbol, config, end_date=None: 0)

        from momentum.factories import create_feature_factory

        factory = create_feature_factory(cache_dir="data_cache/feature_klines", validate_continuity=False)
        outcome = factory.run_multi_symbol(
            ["ADAUSDT", "BADUSDT", "SOLUSDT"],
            config_override={"timeframes": {"primary": "1h", "training": ["1h"]}},
            max_workers=2,
        )
        results, errors = outcome
        assert sorted(results) == ["ADAUSDT", "SOLUSDT"]
        assert results["ADAUSDT"]["symbol"] == "ADAUSDT"
        assert results["SOLUSDT"]["symbol"] == "SOLUSDT"
        assert sorted(errors) == ["BADUSDT"]
        assert "injected worker failure for BADUSDT" in errors["BADUSDT"]


# ===========================================================================
# T5.B3: Disk full mid-persist (staging cleanup)
# ===========================================================================

class TestT5B3DiskFullMidPersist:
    """T5.B3 — staging directory cleaned up on failure."""

    def test_staging_cleanup_on_error(self, tmp_path, sample_registry):
        """FRAMEPATH Task 2.5：V1 版面寫入（.staging_*）已刪；改驗 V2 串流寫入 write_raw_from_registry_stream 於寫入中途失敗（尚未刪任何來源 .npy，cleanup_intermediate=False）時清除暫存根 .tmp-raw-*，且不安裝 raw／manifest。"""
        from momentum.FeatureEngineering.feature_storage import FeatureStorage

        registry, _, _ = sample_registry
        output_dir = tmp_path / "fail_out"
        storage = FeatureStorage(base_path=str(output_dir))

        # Patch os.replace to simulate write failure
        original_replace = os.replace

        call_count = [0]

        def failing_replace(src, dst):
            call_count[0] += 1
            if call_count[0] > 1:
                raise OSError("No space left on device")
            return original_replace(src, dst)

        with patch("momentum.FeatureEngineering.feature_storage.os.replace", side_effect=failing_replace):
            with pytest.raises(OSError, match="No space"):
                storage.write_raw_from_registry_stream("FAILSYM", "1h", "f1", registry, cleanup_intermediate=False)

        # Staging directory should have been cleaned up
        run_dir = output_dir / "FAILSYM" / "1h" / "f1"
        assert call_count[0] == 2
        assert run_dir.exists()
        staging_dirs = [d for d in run_dir.iterdir() if d.is_dir() and d.name.startswith(".tmp-raw-")]
        assert len(staging_dirs) == 0, "Staging directory should be cleaned up"
        assert not (run_dir / "raw").exists()
        assert not (run_dir / "feature_manifest.json").exists()


# ===========================================================================
# Arrow IPC utils tests (Task 5.2)
# ===========================================================================

class TestArrowIPC:
    """Arrow IPC read/write round-trip tests."""

    def test_write_read_roundtrip(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import read_arrow_ipc, write_arrow_ipc

        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        ipc_path = tmp_path / "test.arrow"
        write_arrow_ipc(df, ipc_path)
        loaded = read_arrow_ipc(ipc_path)
        pd.testing.assert_frame_equal(df, loaded)

    def test_reference_data_roundtrip(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import (
            read_reference_data_ipc,
            write_reference_data_ipc,
        )

        df = pd.DataFrame({"close": np.random.randn(100), "volume": np.random.randn(100)})
        ipc_path = write_reference_data_ipc(df, tmp_path, "BTCUSDT")
        loaded = read_reference_data_ipc(ipc_path)
        pd.testing.assert_frame_equal(df, loaded)

    def test_read_missing_raises(self, tmp_path):
        from momentum.FeatureEngineering.arrow_ipc_utils import read_arrow_ipc

        with pytest.raises(FileNotFoundError):
            read_arrow_ipc(tmp_path / "nonexistent.arrow")
