"""TODOFMT Task 1.3：`gate.sh --todo` 之機械判型路由（docs/TODOFMT_SPEC.md Task 1.3）。

判型由 `gate.sh` 內同一函式執行：`todofmt-route` 入口（不發 token、不寫 audit）直接呼叫之；
dispatch 路徑以既有治理測試隔離（`GATE_DIR_OVERRIDE`＋`GOVERNANCE_TEST_HARNESS=1`＋conftest 債務隔離）實跑。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE = REPO_ROOT / "scripts" / "gate.sh"
LEGACY_CALL = 'bash scripts/template_check.sh todo "${todo}"'


def _route(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(GATE), "todofmt-route", *args], cwd=REPO_ROOT,
                          capture_output=True, text=True, check=False)


def _manifest(tmp_path: Path, name: str = "m.json", **over: object) -> Path:
    data: dict = {"stub_modules": [], "spec_path": "docs/TODOFMT_SPEC.md"}
    data.update(over)
    p = tmp_path / name
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def _dispatch(gate_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    cmd = ["bash", str(GATE), "dispatch", "--intent", "TODOFMT 路由單元測試", "--risk", "low",
           "--facts-asked", "none-needed:unit-test", "--review-role", "single-executor:n/a",
           "--template", "n/a: todofmt routing unit test", *extra]
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False, env=env)


def test_boundary_01_md_goes_legacy_and_rc_semantics_unchanged(tmp_path: Path) -> None:
    good = "docs/GAP2_MARGINAL_IC_TODO.md"
    bad = tmp_path / "BAD_TODO.md"
    bad.write_text("# 沒有任何錨點\n", encoding="utf-8")
    assert _route("--todo", good).returncode == 0
    for todo in (good, str(bad)):
        tc = subprocess.run(["bash", "scripts/template_check.sh", "todo", todo], cwd=REPO_ROOT,
                            capture_output=True, text=True, check=False)
        via = _dispatch(tmp_path / f"gate_{Path(todo).stem}", "--todo", todo)
        assert (via.returncode == 0) == (tc.returncode == 0), (todo, via.stdout, tc.stdout)


def test_boundary_02_valid_manifest_goes_new_path(tmp_path: Path) -> None:
    assert _route("--todo", str(_manifest(tmp_path))).returncode == 0


def test_boundary_03_json_without_stub_modules_rejected(tmp_path: Path) -> None:
    p = tmp_path / "x.json"
    p.write_text(json.dumps({"spec_path": "docs/TODOFMT_SPEC.md"}), encoding="utf-8")
    r = _route("--todo", str(p))
    assert r.returncode == 1 and "判型失敗" in r.stdout, r.stdout


def test_boundary_04_yaml_rejected(tmp_path: Path) -> None:
    p = tmp_path / "x.yaml"
    p.write_text("stub_modules: []\n", encoding="utf-8")
    r = _route("--todo", str(p))
    assert r.returncode == 1 and "判型失敗" in r.stdout, r.stdout


@pytest.mark.parametrize("name", ["ABSENT_TODO.md", "absent.json"])
def test_boundary_05_missing_file_fails_closed(tmp_path: Path, name: str) -> None:
    r = _dispatch(tmp_path / "gate", "--todo", str(tmp_path / name))
    assert r.returncode != 0, r.stdout


def test_boundary_06_duplicate_todo_rejected(tmp_path: Path) -> None:
    r = _route("--todo", "docs/GAP2_MARGINAL_IC_TODO.md", "--todo", str(_manifest(tmp_path)))
    assert r.returncode == 1 and "重複" in r.stdout, r.stdout


def test_boundary_07_uppercase_md_extension_goes_legacy(tmp_path: Path) -> None:
    p = tmp_path / "X_TODO.MD"
    p.write_text("x\n", encoding="utf-8")
    assert _route("--todo", str(p)).returncode == 0


def test_coverage_legacy_call_literal_in_l_and_x() -> None:
    at_l = anchor.show(anchor.design_freeze_commit(), "scripts/gate.sh") or ""
    at_x = anchor.read_x("scripts/gate.sh") or ""
    assert LEGACY_CALL in at_l and LEGACY_CALL in at_x


def test_coverage_other_kinds_unchanged() -> None:
    r = subprocess.run(["bash", str(GATE), "no-such-kind"], cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 1 and "kind 必須是 dispatch|artifact|register-output" in r.stdout, r.stdout


def _gate_copy(tmp_path: Path, name: str, text: str) -> Path:
    """gate.sh 之複本（同佈局）：一併複製其開頭 source 之家族 SoT，免因缺相依而早退（b3 自查：原探針因此假綠）。"""
    scripts = tmp_path / name / "scripts"
    scripts.mkdir(parents=True)
    for dep in ("governance_families.sh", "governance_families.json"):
        shutil.copy(REPO_ROOT / "scripts" / dep, scripts / dep)
    (scripts / "gate.sh").write_text(text, encoding="utf-8")
    return scripts / "gate.sh"


def test_mutation_removing_casefold_breaks_uppercase_routing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """判型不做 casefold ⇒ `X_TODO.MD` 判型失敗（證邊界⑦之測試有鑑別力）。"""
    src = GATE.read_text(encoding="utf-8")
    anchor_txt = '_tk_l="$(printf \'%s\' "$1" | tr \'[:upper:]\' \'[:lower:]\')"'
    assert src.count(anchor_txt) == 1
    p = tmp_path / "X_TODO.MD"
    p.write_text("x\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "GATE", _gate_copy(tmp_path, "orig", src))
    assert _route("--todo", str(p)).returncode == 0, "前提：同佈局之未改壞複本應放行"
    monkeypatch.setattr(sys.modules[__name__], "GATE", _gate_copy(tmp_path, "mut", src.replace(anchor_txt, '_tk_l="$1"')))
    r = _route("--todo", str(p))
    assert r.returncode == 1 and "判型失敗" in r.stdout, r.stdout + r.stderr
