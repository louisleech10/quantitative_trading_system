"""FF-NAME Task 4.2 — 死碼刪除（docs/FFNAME_SPEC.md Task 4.2）。

刪 `utils/adf_safe_skip.py`、`tests/feature_engineering/test_adf_safe_skip.py`、`test_ffstat_all_tested.py` 對其之 mutant 引用；
`feature_storage.py`、`feature_factory.py` 過時註解。
驗證：`grep -rn "adf_safe_skip" momentum api` 只剩 `feature_config.py` 拒收；設定拒收測試仍綠。
邊界：`handoffs/` 探針引用不受版控、不處理（不計入檢查）。
v13：平穩化決策鍵與決策值經 Task 0.1 凍結之身分映射後與 baseline 相等（與改名之值驗收分開歸因；
本項以真實 kline reference run 驗，重型、單組串行）。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

from momentum.factories import create_feature_factory
from tests.feature_engineering.ffname_helpers import BASELINE_PATH, CONTRACT, REPO, load_freeze_module
from tests.feature_engineering.fftfmeta_golden_helpers import KLINE_DIR, prepare_env

DEAD = CONTRACT["dead_code"]
SCAN_REPO = REPO
SCAN_ROOTS = ("momentum", "api")


def _dead_refs() -> List[str]:
    """`grep -rln <token>` 於 SCAN_ROOTS（相對 SCAN_REPO）之命中檔（不含 __pycache__）。"""
    proc = subprocess.run(["grep", "-rln", "--include=*.py", DEAD["token"], *SCAN_ROOTS], cwd=str(SCAN_REPO),
                          capture_output=True, text=True)
    return sorted(line for line in proc.stdout.splitlines() if "__pycache__" not in line)


def test_only_config_rejection_remains():
    assert _dead_refs() == [DEAD["allowed_reference"]]


def test_dead_module_and_its_test_deleted():
    assert not (REPO / DEAD["module"]).exists()
    assert not (REPO / "tests/feature_engineering/test_adf_safe_skip.py").exists()
    src = (REPO / "tests/feature_engineering/test_ffstat_all_tested.py").read_text(encoding="utf-8")
    assert "utils.adf_safe_skip" not in src


def test_config_rejection_still_raises():
    factory = create_feature_factory(cache_dir=KLINE_DIR, validate_continuity=False)
    with pytest.raises(ValueError, match=DEAD["token"]):
        factory._resolve_config({"preprocessing": {"adf_safe_skip": {"enabled": True}}})


def test_stale_comments_removed():
    for rel in ("momentum/FeatureEngineering/feature_storage.py", "momentum/FeatureEngineering/feature_factory.py"):
        src = (REPO / rel).read_text(encoding="utf-8")
        assert "_apply_timeframe_tag" not in src, rel


def test_boundary_01_handoffs_probe_references_not_counted():
    assert "handoffs" not in SCAN_ROOTS
    assert all(not ref.startswith("handoffs/") for ref in _dead_refs())


# ---------------------------------------------------------------- v13：平穩化決策比對基準（真實 kline reference run，重型）

freeze = load_freeze_module()


@pytest.fixture(scope="module")
def baseline() -> Dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def reference_after(tmp_path_factory) -> Dict[str, Any]:
    tmp = tmp_path_factory.mktemp("ffname_dead_code_reference")
    with pytest.MonkeyPatch.context() as mp:
        prepare_env(mp, tmp, FFACT_MULTI_TF_PARALLEL="0")
        return freeze.run_reference(tmp, record_parts=False)


def _mapping(baseline: Dict[str, Any]) -> Dict[str, str]:
    parts = {row["old_name"]: freeze.NamingPart(**{**row, "params": tuple(tuple(m) for m in (row.get("params") or ())),
                                                   "ops": tuple(row.get("ops") or ())})
             for row in baseline["parts"]}
    return freeze.derive_mapping(parts, {k: p.tf for k, p in parts.items()})


def stationarity_mismatches(baseline: Dict[str, Any], current: Dict[str, Any]) -> List[str]:
    """平穩化決策鍵與決策值經 Task 0.1 身分映射後與 baseline 相等（SPEC v13 Task 4.2）。"""
    mapping = _mapping(baseline)
    expected = {mapping.get(k, f"<unmapped:{k}>"): v for k, v in baseline["stationarity_decisions"].items()}
    got = current["stationarity_decisions"]
    keys = set(expected) | set(got)
    return sorted(k for k in keys if expected.get(k, "<missing>") != got.get(k, "<missing>"))


def test_stationarity_decisions_equal_baseline_after_identity_mapping(baseline, reference_after):
    assert baseline["stationarity_decisions"]
    assert stationarity_mismatches(baseline, reference_after) == []


def test_mutation_unmapped_stationarity_keys_detected(baseline, reference_after, monkeypatch):
    """mutant：比對不經身分映射（舊名直比新名）⇒ 鍵不符（改名數 > 0 時必紅）。"""
    monkeypatch.setattr(freeze, "derive_mapping", lambda parts, tf_of: {k: k for k in parts})
    assert stationarity_mismatches(baseline, reference_after) != []


def test_mutation_new_reference_detected(tmp_path, monkeypatch):
    """mutant：momentum 下新增一處 `adf_safe_skip` 引用 ⇒ 檢查翻紅（以 tmp 鏡像 repo 驗檢查器鑑別力）。"""
    (tmp_path / "momentum").mkdir()
    (tmp_path / "api").mkdir()
    (tmp_path / "momentum" / "revived.py").write_text(f"from momentum.FeatureEngineering.utils.{DEAD['token']} import x\n",
                                                      encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "SCAN_REPO", tmp_path)
    assert _dead_refs() == ["momentum/revived.py"]
    assert _dead_refs() != [DEAD["allowed_reference"]]
