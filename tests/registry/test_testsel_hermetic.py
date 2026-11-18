"""TESTSEL-HERMETIC：測試行程中「未給路徑時」之特徵 registry 與特徵儲存根預設值導向本 session 暫存；
明給之根與 `FFACT_FEATURE_REGISTRY_PATH` 覆寫語意不變；session 結束偵測正式寫入根之變動。

背景（2026-11-14 實查）：正式 `data_cache/features/registry.json` 90 筆中 57 筆指向已刪之 pytest 暫存目錄；
服務單例於模組匯入時即建 registry（早於 fixture），故導向須於 tests/conftest.py 載入時生效。
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import HERMETIC_ROOT
from tests.fixtures.hermetic_guard_plugin import prod_write_diff, prod_write_snapshot, resolve_prod_root

REPO = Path(__file__).resolve().parents[2]


def _under(path: Path, root: Path) -> bool:
    return Path(path).resolve().is_relative_to(root.resolve())


def test_default_registry_path_is_hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    """未給路徑、未設環境變數之 `FeatureRegistry()` 落在本 session 暫存，不在 repo（含 data_cache 符號連結）內。"""
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry

    monkeypatch.delenv("FFACT_FEATURE_REGISTRY_PATH", raising=False)
    path = FeatureRegistry()._path  # noqa: SLF001
    assert _under(path, HERMETIC_ROOT) and not _under(path, REPO), path


def test_explicit_root_and_env_override_semantics_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """明給之根與環境變數覆寫照產品語意：只改預設值，不改明給者（全域設環境變數之做法會破壞此條）。"""
    from momentum.factories import create_feature_library

    monkeypatch.delenv("FFACT_FEATURE_REGISTRY_PATH", raising=False)
    root = tmp_path / "features"
    root.mkdir()
    assert Path(create_feature_library(feature_root=root)._registry._path).resolve() == (root / "registry.json").resolve()
    monkeypatch.setenv("FFACT_FEATURE_REGISTRY_PATH", str(tmp_path / "ext.json"))
    assert Path(create_feature_library(feature_root=root)._registry._path).resolve() == (tmp_path / "ext.json").resolve()


def test_feature_storage_default_root_is_hermetic() -> None:
    """產品 `FeatureStorage()` 預設根（相對 cwd 之 data_cache/features）於測試行程導向暫存；明給者不變。"""
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    assert _under(FeatureStorage().base_path, HERMETIC_ROOT)
    assert FeatureStorage(str(HERMETIC_ROOT / "x")).base_path == HERMETIC_ROOT / "x"


def test_import_time_service_singleton_registry_is_hermetic() -> None:
    """匯入時即建之 IC 服務單例，其 registry 路徑在暫存下（本缺陷之實際寫入者）。"""
    if os.environ.get("FFACT_FEATURE_REGISTRY_PATH"):
        pytest.fail("本測試前提：行程未設 FFACT_FEATURE_REGISTRY_PATH（單例於匯入時讀取）")
    from api.services import ic_analysis_service as svc_mod

    path = svc_mod.ic_analysis_service._feature_library._registry._path  # noqa: SLF001
    assert _under(Path(path), HERMETIC_ROOT), path


def test_without_redirect_singleton_would_write_production_registry() -> None:
    """改壞對照：同一匯入於未載 conftest 之行程 ⇒ 單例 registry 為正式預設路徑（上一條即會轉紅）。"""
    env = {k: v for k, v in os.environ.items() if k != "FFACT_FEATURE_REGISTRY_PATH"}
    code = ("import api.services.ic_analysis_service as m;"
            "print(m.ic_analysis_service._feature_library._registry._path)")
    out = subprocess.run([sys.executable, "-c", code], cwd=REPO, env=env, capture_output=True, text=True, check=True)
    assert out.stdout.strip().splitlines()[-1] == "data_cache/features/registry.json"


def test_prod_write_detector_reports_added_and_changed(tmp_path: Path) -> None:
    """session 結束偵測（tests/fixtures/hermetic_guard_plugin.py，data_cache 全樹）：新增、變動、消失皆列出（含其所在
    目錄之 mtime 變動）；未變者（keep.h5）不列。"""
    base = tmp_path / "data_cache" / "features"
    base.mkdir(parents=True)
    (base / "keep.h5").write_bytes(b"a")
    (base / "registry.json").write_text("[]", encoding="utf-8")
    (base / "gone.h5").write_bytes(b"g")
    root = resolve_prod_root(tmp_path)
    before = prod_write_snapshot(root)
    (base / "registry.json").write_text('[{"x": 1}]', encoding="utf-8")
    (base / "ETHUSDT_1_1.h5").write_bytes(b"n")
    (base / "gone.h5").unlink()
    assert prod_write_diff(before, prod_write_snapshot(root)) == [
        "features", "features/ETHUSDT_1_1.h5", "features/gone.h5", "features/registry.json"]
    assert prod_write_diff(before, before) == []


_CGSA_HASH = "abcdef1234567890"
_CGSA_AID = "b" * 64


def _cgsa_factory(tmp_path: Path) -> Any:
    """只含 `_prepare_cgsa_registry` 所需欄位之 FeatureFactory（同 tests/test_cgsa_resume.py 之最小實例）。"""
    from unittest.mock import Mock

    from momentum.FeatureEngineering.feature_factory import FeatureFactory
    from momentum.FeatureEngineering.feature_registry import FeatureRegistry
    from momentum.FeatureEngineering.feature_storage import FeatureStorage

    factory = FeatureFactory.__new__(FeatureFactory)
    factory._config_manager = Mock()  # noqa: SLF001
    factory._storage = FeatureStorage(str(tmp_path / "features"))  # noqa: SLF001
    factory._registry = FeatureRegistry(tmp_path / "registry.json")  # noqa: SLF001
    factory._cgsa_registry = None  # noqa: SLF001
    factory._cgsa_force_fresh = False  # noqa: SLF001
    return factory


def test_default_cgsa_root_from_repo_cwd_is_hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """cwd＝repo、未給根、未設 FFACT_CGSA_WORK_DIR：工廠 CGSA 工作葉落 session 暫存，正式 data_cache/cgsa_work
    頂層不變（收尾 E6）。"""
    monkeypatch.chdir(REPO)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    prod_root = resolve_prod_root(REPO)
    before = prod_write_snapshot(prod_root)
    registry = _cgsa_factory(tmp_path)._prepare_cgsa_registry("ETHUSDT", "1h", _CGSA_HASH, algorithm_id=_CGSA_AID)
    assert registry is not None
    assert _under(registry.work_dir, HERMETIC_ROOT) and not _under(registry.work_dir, REPO), registry.work_dir
    assert registry.work_dir.is_dir()
    assert [k for k in prod_write_diff(before, prod_write_snapshot(prod_root)) if "cgsa_work" in k] == []


def test_default_cgsa_root_elsewhere_keeps_cwd_semantics(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """cwd 不在正式 data_cache 下：預設仍為依 cwd 之相對 `data_cache/cgsa_work`（產品語意不變）。"""
    from momentum.FeatureEngineering import run_paths

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("FFACT_CGSA_WORK_DIR", raising=False)
    assert run_paths.default_cgsa_root() == Path("data_cache") / "cgsa_work"
    registry = _cgsa_factory(tmp_path)._prepare_cgsa_registry("ETHUSDT", "1h", _CGSA_HASH, algorithm_id=_CGSA_AID)
    assert registry is not None
    assert registry.work_dir == run_paths.cgsa_work_dir(tmp_path / "data_cache" / "cgsa_work", "ETHUSDT", "1h",
                                                        _CGSA_HASH, _CGSA_AID)


def test_without_redirect_default_cgsa_root_is_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """對照：產品預設值（未經 conftest 重導）於 cwd＝repo 時解析進正式 data_cache——證明保護來自重導。"""
    import tests.conftest as cf
    from momentum.FeatureEngineering import run_paths

    monkeypatch.chdir(REPO)
    assert run_paths.DEFAULT_CGSA_WORK_ROOT == Path("data_cache") / "cgsa_work"
    raw = (REPO / cf._ORIG_DEFAULT_CGSA_ROOT()).resolve()  # noqa: SLF001
    assert raw == cf.PROD_DATA_CACHE / "cgsa_work"
    assert run_paths.default_cgsa_root is cf.hermetic_default_cgsa_root
