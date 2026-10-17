"""FF-NAME Task 4.1 — config hash 命名版本鹽與 manifest 根鍵（docs/FFNAME_SPEC.md Task 4.1）。

`feature_factory._compute_config_hash` 納 `_feature_naming_version`；`feature_storage` manifest 根寫 `feature_naming_version`。
驗證：同設定 hash 改前 != 改後、改後重跑 ==；舊 run 在場時新 run 不命中續跑（spy 斷言 0 次）。
「改前」以「hash payload 去掉版本鹽」模擬（改前碼與改後碼之 hash 差異恰為此鹽）。
邊界：`force_regenerate` 寫新 hash 目錄（舊 run 目錄不刪）。真實 kline 輕量 run（隔離於 tmp）。mutation：§V ⑦移除版本鹽。
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any, Dict, Iterator, List

import pytest

import momentum.FeatureEngineering.feature_factory as ff_mod
import momentum.FeatureEngineering.feature_naming as fn
from momentum.factories import create_feature_factory
from momentum.FeatureEngineering.core.column_group_registry import ColumnGroupRegistry
from tests.feature_engineering.ffname_helpers import GATE_KEY
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, fast_payload, l7_manifest, prepare_env
from tests.feature_engineering.ffstat_helpers import HEALTHY, PRIMARY_TF, SYMBOL, run_stat

TF = PRIMARY_TF
SALT_KEY = "_feature_naming_version"
_REAL_DUMPS = json.dumps


def _strip_salt(obj, *a, **k):
    if isinstance(obj, dict) and SALT_KEY in obj:
        obj = {key: v for key, v in obj.items() if key != SALT_KEY}
    return _REAL_DUMPS(obj, *a, **k)


@contextlib.contextmanager
def pre_change_hash() -> Iterator[None]:
    """模擬改前碼之 hash：payload 去掉版本鹽。"""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(ff_mod.json, "dumps", _strip_salt)
        yield


def _payload() -> Dict[str, Any]:
    return fast_payload([TF], **HEALTHY)


def _identity() -> str:
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    return factory.config_identity(SYMBOL, TF, _payload())


def _pre_post_differ() -> bool:
    post = _identity()
    with pre_change_hash():
        pre = _identity()
    return post != pre


# ---------------------------------------------------------------- 單元

def test_hash_payload_contains_naming_salt(monkeypatch):
    seen: List[str] = []

    def spy(obj, *a, **k):
        out = _REAL_DUMPS(obj, *a, **k)
        if isinstance(obj, dict) and "_mtf_align_version" in obj:
            seen.append(out)
        return out

    monkeypatch.setattr(ff_mod.json, "dumps", spy)
    _identity()
    assert seen and f'"{SALT_KEY}": {fn.CURRENT_FEATURE_NAMING_VERSION}' in seen[-1]


def test_hash_pre_differs_post_and_rerun_equal():
    assert _identity() == _identity()
    assert _pre_post_differ()


# ---------------------------------------------------------------- 真實 kline 輕量 run

def test_old_run_present_new_run_does_not_resume(tmp_path, monkeypatch):
    prepare_env(monkeypatch, tmp_path)
    with pre_change_hash():
        _root, _f, old = run_stat(tmp_path, _payload(), force_regenerate=True)
    calls: List[Any] = []
    real = ColumnGroupRegistry.resume_from_manifest.__func__

    def spy(cls, work_dir):
        calls.append(work_dir)
        return real(cls, work_dir)

    monkeypatch.setattr(ColumnGroupRegistry, "resume_from_manifest", classmethod(spy))
    root, _f2, new = run_stat(tmp_path, _payload(), force_regenerate=False)
    assert new.metadata["config_hash"] != old.metadata["config_hash"]
    assert len(calls) == 0
    assert l7_manifest(root, TF, new)[GATE_KEY] == fn.CURRENT_FEATURE_NAMING_VERSION


def test_boundary_01_force_regenerate_writes_new_hash_dir(tmp_path, monkeypatch):
    prepare_env(monkeypatch, tmp_path)
    with pre_change_hash():
        root, _f, old = run_stat(tmp_path, _payload(), force_regenerate=True)
    root, _f2, new = run_stat(tmp_path, _payload(), force_regenerate=True)
    old_dir = root / SYMBOL / TF / str(old.metadata["config_hash"])
    new_dir = root / SYMBOL / TF / str(new.metadata["config_hash"])
    assert old_dir != new_dir
    assert new_dir.is_dir() and old_dir.is_dir()  # 不刪舊 run 目錄
    assert json.loads((new_dir / "feature_manifest.json").read_text(encoding="utf-8"))[GATE_KEY] == fn.CURRENT_FEATURE_NAMING_VERSION


# ---------------------------------------------------------------- mutation

def test_mutation_salt_removed_is_caught(monkeypatch):
    """§V mutation ⑦：生產 hash payload 移除版本鹽 ⇒ 改前改後 hash 相同。"""
    monkeypatch.setattr(ff_mod.json, "dumps", _strip_salt)
    assert _pre_post_differ() is False
