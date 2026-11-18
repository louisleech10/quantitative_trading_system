"""TESTSEL I4g 驗收（docs/TESTSEL_I4G_SPEC.md Task 1.1／1.2）：`momentum.FeatureEngineering` 套件改 PEP 562 延遲匯出、
conftest 重依賴改用到才載入；匯入後物件與 `pd.read_hdf` 相容補丁時點不變。

延遲載入一律以子行程之 `sys.modules` 斷言（不受本測試行程已載入模組之干擾）。
開 SPEC 前原型（runs/testsel_route/i4g/i4g_facts.md，3 次中位）：S2 改前 4.25 秒、原型 2.58 秒。
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HEAVY = ("momentum.FeatureEngineering.feature_factory", "momentum.FeatureEngineering.feature_validator", "statsmodels")


def _py(code: str) -> str:
    proc = subprocess.run([sys.executable, "-c", code], cwd=REPO, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stdout[-2000:] + proc.stderr[-2000:]
    return proc.stdout.strip().splitlines()[-1]


def test_i4g_submodule_import_does_not_load_heavy_chain() -> None:
    """只匯入 `feature_registry` 子模組 ⇒ 不載入 feature_factory／feature_validator／statsmodels。"""
    out = _py("import json, sys\nimport momentum.FeatureEngineering.feature_registry\n"
              f"print(json.dumps([m for m in {list(HEAVY)!r} if m in sys.modules]))")
    assert json.loads(out) == []


def test_i4g_package_names_identical_to_submodule_objects() -> None:
    """`__all__` 每名經套件取得者與子模組中同名物件為同一物件；套件層級 from-import 可用。"""
    pkg = importlib.import_module("momentum.FeatureEngineering")
    where = {"FeatureExtractor": "feature_extractor", "StrategyParams": "feature_extractor",
             "FeatureValidator": "feature_validator", "FeatureStorage": "feature_storage",
             "FeatureFactory": "feature_factory", "FeatureGenerationResult": "feature_factory",
             "ConfigManager": "config_manager"}
    assert sorted(pkg.__all__) == sorted(where)
    for name, sub in where.items():
        mod = importlib.import_module(f"momentum.FeatureEngineering.{sub}")
        assert getattr(pkg, name) is getattr(mod, name), name
    from momentum.FeatureEngineering import FeatureExtractor, StrategyParams  # noqa: F401
    assert set(pkg.__all__) <= set(dir(pkg))


def test_i4g_first_access_via_package_then_cached() -> None:
    """新子行程：匯入套件後、取用任一名前 `dir()` 已含 `__all__` 且未載重鏈；先由套件取得每名 ⇒ 與其後子模組物件同一，
    且已快取於模組全域（`vars(pkg)`）。"""
    code = ("import importlib, json, sys\n"
            "import momentum.FeatureEngineering as pkg\n"
            f"heavy = {list(HEAVY)!r}\n"
            "before = {'dir_ok': set(pkg.__all__) <= set(dir(pkg)), 'heavy': [m for m in heavy if m in sys.modules],\n"
            "          'cached': [n for n in pkg.__all__ if n in vars(pkg)]}\n"
            "objs = {n: getattr(pkg, n) for n in pkg.__all__}\n"
            "where = {'FeatureExtractor': 'feature_extractor', 'StrategyParams': 'feature_extractor',\n"
            "         'FeatureValidator': 'feature_validator', 'FeatureStorage': 'feature_storage',\n"
            "         'FeatureFactory': 'feature_factory', 'FeatureGenerationResult': 'feature_factory',\n"
            "         'ConfigManager': 'config_manager'}\n"
            "same = all(objs[n] is getattr(importlib.import_module('momentum.FeatureEngineering.' + w), n)\n"
            "           for n, w in where.items())\n"
            "after = sorted(n for n in pkg.__all__ if vars(pkg).get(n) is objs[n])\n"
            "print(json.dumps({'before': before, 'same': same, 'after': after}))")
    out = json.loads(_py(code))
    pkg = importlib.import_module("momentum.FeatureEngineering")
    assert out == {"before": {"dir_ok": True, "heavy": [], "cached": []}, "same": True, "after": sorted(pkg.__all__)}


def test_i4g_mock_patch_package_name_enter_and_restore() -> None:
    """`unittest.mock.patch("momentum.FeatureEngineering.FeatureFactory")`：進入時替換、退出時恢復同一物件。"""
    from unittest import mock

    pkg = importlib.import_module("momentum.FeatureEngineering")
    orig = pkg.FeatureFactory
    with mock.patch("momentum.FeatureEngineering.FeatureFactory") as fake:
        assert pkg.FeatureFactory is fake
    assert pkg.FeatureFactory is orig


def test_i4g_read_hdf_patch_applied_on_any_submodule_import() -> None:
    """只匯入一個子模組 ⇒ `pandas.read_hdf` 已為相容補丁（副作用時點不變）。"""
    out = _py("import momentum.FeatureEngineering.feature_registry\nimport pandas\nprint(pandas.read_hdf.__name__)")
    assert out == "_read_hdf_compat"


def test_i4g_unknown_attribute_raises() -> None:
    pkg = importlib.import_module("momentum.FeatureEngineering")
    with pytest.raises(AttributeError):
        getattr(pkg, "NoSuchExport")


def test_i4g_conftest_collect_does_not_import_factories() -> None:
    """子行程對輕量測試檔 `--collect-only`（經根 conftest）⇒ 收集完成時未載入 momentum.factories 與 statsmodels。"""
    code = ("import json, sys, pytest\n"
            "class Rec:\n"
            "    seen = None\n"
            "    def pytest_collection_finish(self, session):\n"
            "        Rec.seen = [m for m in ('momentum.factories', 'statsmodels') if m in sys.modules]\n"
            "rc = pytest.main(['--co', '-q', '-p', 'no:cacheprovider', 'tests/registry/test_conftest_seed.py'],"
            " plugins=[Rec()])\n"
            "print(json.dumps({'rc': int(rc), 'seen': Rec.seen}))")
    out = json.loads(_py(code))
    assert out == {"rc": 0, "seen": []}
