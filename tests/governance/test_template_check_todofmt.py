"""TODOFMT Task 0.2：`template_check.sh todofmt` 以 exec 轉呼叫 `scripts/todofmt_check.sh`（docs/TODOFMT_SPEC.md Task 0.2）。

邊界①–⑦ 以真實 repo 之兩支腳本判定（manifest 內路徑相對真實 repo 根）；
邊界⑧ 斷言轉呼叫與檢查器之 rc 與 stdout 逐一相等；邊界⑨ 與覆蓋風險斷言 `template_check.sh` 之改動恰為一行。
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_CHECK = REPO_ROOT / "scripts" / "template_check.sh"
CHECKER = REPO_ROOT / "scripts" / "todofmt_check.sh"
EXEC_LINE = '[ "${kind}" = "todofmt" ] && exec bash "${SCRIPT_DIR}/todofmt_check.sh" "${file}"'


def _digest() -> str:
    return subprocess.run(["bash", str(CHECKER), "--digest"], capture_output=True, text=True, check=True).stdout.strip()


def _valid() -> dict:
    return {
        "stub_modules": [],
        "test_files": ["tests/governance/test_template_check_todofmt.py"],
        "script_acceptance": [],
        "contract_jsons": ["scripts/todofmt_contract.json"],
        "spec_path": "docs/TODOFMT_SPEC.md",
        "contract_digest": _digest(),
        "run_receipts": [],
        "batch_card": {
            "depends": [], "touches": ["scripts/template_check.sh"], "callers_now": [], "callers_later": [],
            "gate_cmd": "bash scripts/template_check.sh todofmt docs/manifests/TODOFMT.json",
            "forbidden": [], "risk_mitigation": [], "coverage_risk": [], "lifecycle": "keep",
            "not_executable": [{"item": "stub_modules", "reason": "needs-research", "owner": "o", "expiry": "2099-01-01"}],
        },
    }


def _write(tmp_path: Path, name: str, content: dict | str) -> Path:
    p = tmp_path / name
    p.write_text(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False), encoding="utf-8")
    return p


def _tc(path: Path) -> subprocess.CompletedProcess[str]:
    """經 `template_check.sh todofmt` 判定；腳本取自模組層級 TEMPLATE_CHECK（mutation 探針以 monkeypatch 換成改壞之複本）。"""
    return subprocess.run(["bash", str(TEMPLATE_CHECK), "todofmt", str(path)], capture_output=True, text=True, check=False)


def _checker(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(CHECKER), str(path)], capture_output=True, text=True, check=False)


def _inputs(tmp_path: Path) -> dict[str, Path]:
    """邊界①–⑦ 之輸入各一，另加一份合法 manifest。"""
    v = _valid()
    no_cat = {k: v[k] for k in v if k != "contract_jsons"}
    missing_path = json.loads(json.dumps(v))
    missing_path["test_files"] = ["tests/governance/test_does_not_exist_todofmt.py"]
    no_owner = json.loads(json.dumps(v))
    no_owner["batch_card"]["not_executable"][0]["owner"] = ""
    bad_expiry = json.loads(json.dumps(v))
    bad_expiry["batch_card"]["not_executable"][0]["expiry"] = "2099/01/01"
    later_absent = json.loads(json.dumps(v))
    later_absent["batch_card"]["callers_later"] = ["api/not_yet_written.py"]
    return {
        "valid": _write(tmp_path, "valid.json", v),
        "b1_missing": tmp_path / "absent.json",
        "b2_invalid_json": _write(tmp_path, "invalid.json", "{not json"),
        "b3_missing_category": _write(tmp_path, "no_cat.json", no_cat),
        "b4_exists_true_missing": _write(tmp_path, "missing_path.json", missing_path),
        "b5_no_owner": _write(tmp_path, "no_owner.json", no_owner),
        "b6_bad_expiry": _write(tmp_path, "bad_expiry.json", bad_expiry),
        "b7_exists_false_absent": _write(tmp_path, "later_absent.json", later_absent),
    }


def test_valid_manifest_rc0(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["valid"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_boundary_01_manifest_missing(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b1_missing"])
    assert r.returncode == 1 and "manifest 不存在" in r.stdout, r.stdout


def test_boundary_02_invalid_json(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b2_invalid_json"])
    assert r.returncode == 1 and "JSON 不合法" in r.stdout, r.stdout


def test_boundary_03_missing_category(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b3_missing_category"])
    assert r.returncode == 1 and "缺必填鍵：contract_jsons" in r.stdout, r.stdout


def test_boundary_04_exists_check_true_path_missing(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b4_exists_true_missing"])
    assert r.returncode == 1 and "路徑不存在（exists_check）" in r.stdout, r.stdout


def test_boundary_05_not_executable_missing_owner(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b5_no_owner"])
    assert r.returncode == 1 and "缺 owner" in r.stdout, r.stdout


def test_boundary_06_expiry_format(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b6_bad_expiry"])
    assert r.returncode == 1 and "格式非 YYYY-MM-DD" in r.stdout, r.stdout


def test_boundary_07_exists_check_false_absent_passes(tmp_path: Path) -> None:
    r = _tc(_inputs(tmp_path)["b7_exists_false_absent"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_boundary_08_wrapper_equals_checker_rc_and_stdout(tmp_path: Path) -> None:
    for name, path in _inputs(tmp_path).items():
        via, direct = _tc(path), _checker(path)
        assert (via.returncode, via.stdout) == (direct.returncode, direct.stdout), name


def test_boundary_09_exec_line_appears_exactly_once() -> None:
    lines = TEMPLATE_CHECK.read_text(encoding="utf-8").splitlines()
    assert lines.count(EXEC_LINE) == 1


def test_coverage_template_check_diff_vs_l_is_exactly_the_exec_line() -> None:
    """覆蓋風險：`template_check.sh` 相對 L 之差異恰為新增轉呼叫行一行（比較端 X）。"""
    added, removed = anchor.diff_lines_vs_l("scripts/template_check.sh")
    assert (added, removed) == ([EXEC_LINE], [])


def test_mutation_removing_exec_breaks_equivalence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把轉呼叫行之 `exec` 移除 ⇒ 合法 manifest 之 rc 或 stdout 與檢查器不同（邊界⑧有鑑別力）。"""
    scripts = tmp_path / "repo" / "scripts"
    scripts.mkdir(parents=True)
    src = TEMPLATE_CHECK.read_text(encoding="utf-8")
    assert src.count(EXEC_LINE) == 1
    (scripts / "template_check.sh").write_text(
        src.replace(EXEC_LINE, EXEC_LINE.replace("&& exec bash", "&& bash")), encoding="utf-8"
    )
    shutil.copy(CHECKER, scripts / "todofmt_check.sh")
    shutil.copy(REPO_ROOT / "scripts" / "todofmt_contract.json", scripts / "todofmt_contract.json")
    # 迷你 repo 之 manifest：路徑相對迷你 repo 根
    root = tmp_path / "repo"
    (root / "tests").mkdir()
    (root / "tests" / "t.py").write_text("x\n", encoding="utf-8")
    digest = subprocess.run(["bash", str(scripts / "todofmt_check.sh"), "--digest"],
                            capture_output=True, text=True, check=True).stdout.strip()
    m = _valid()
    m.update(test_files=["tests/t.py"], spec_path="scripts/todofmt_contract.json", contract_digest=digest)
    m["batch_card"]["touches"] = ["tests/t.py"]
    mf = _write(tmp_path, "m.json", m)
    direct = subprocess.run(["bash", str(scripts / "todofmt_check.sh"), str(mf)], capture_output=True, text=True, check=False)
    monkeypatch.setattr(sys.modules[__name__], "TEMPLATE_CHECK", scripts / "template_check.sh")
    via = _tc(mf)
    assert direct.returncode == 0, direct.stdout
    assert (via.returncode, via.stdout) != (direct.returncode, direct.stdout), "移除 exec 後仍等價 ⇒ 邊界⑧ 無鑑別力"
