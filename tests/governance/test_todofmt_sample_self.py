"""TODOFMT Task 3.1：本票以新格式產出之 manifest 與其 promotion 樣本（docs/TODOFMT_SPEC.md Task 3.1）。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "docs" / "manifests" / "TODOFMT.json"
SAMPLE = REPO_ROOT / "tests" / "governance" / "fixtures" / "todofmt_sample_self.json"
CHECKER = REPO_ROOT / "scripts" / "todofmt_check.sh"
CONTRACT = REPO_ROOT / "scripts" / "todofmt_contract.json"
REASONS = {"blocked-by", "user-ruling", "needs-research"}


def _m() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _current_digest() -> str:
    return subprocess.run(["bash", str(CHECKER), "--digest"], capture_output=True, text=True, check=True).stdout.strip()


def test_boundary_01_no_production_module_declared_not_executable() -> None:
    m = _m()
    assert m["stub_modules"] == []
    items = {n["item"]: n for n in m["batch_card"]["not_executable"]}
    assert "stub_modules" in items and items["stub_modules"]["reason"] in REASONS


def test_boundary_02_contract_json_landing() -> None:
    assert "scripts/todofmt_contract.json" in _m()["contract_jsons"]


def test_boundary_03_batch_card_fields_complete() -> None:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    required = {k for k, v in contract["batch_card"].items() if v["required"]}
    assert required <= set(_m()["batch_card"])


def test_boundary_04_receipt_landing_under_run_receipts() -> None:
    assert all(r["path"].startswith("handoffs/run_receipts/") for r in _m()["run_receipts"])


@pytest.mark.parametrize("path", [MANIFEST, SAMPLE], ids=["manifest", "promoted_sample"])
def test_boundary_05_06_template_check_todofmt_rc0(path: Path) -> None:
    r = subprocess.run(["bash", "scripts/template_check.sh", "todofmt", str(path)], cwd=REPO_ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout


def test_promotion_artifact_is_byte_copy_of_manifest() -> None:
    assert SAMPLE.read_bytes() == MANIFEST.read_bytes()


def test_invalidation_sample_digest_equals_current() -> None:
    assert json.loads(SAMPLE.read_text(encoding="utf-8"))["contract_digest"] == _current_digest()


def test_mutation_contract_change_invalidates_sample(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """契約之 exists_check 改一格 ⇒ 現行 digest 改變、樣本記錄值不再相等（invalidation 有效）。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(CHECKER, scripts / "todofmt_check.sh")
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    data["batch_card"]["callers_later"]["exists_check"] = True
    (scripts / "todofmt_contract.json").write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "CHECKER", scripts / "todofmt_check.sh")
    assert json.loads(SAMPLE.read_text(encoding="utf-8"))["contract_digest"] != _current_digest()
