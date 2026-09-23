"""TODOFMT Task 0.2：`template_check.sh todofmt` 以 exec 轉呼叫 `scripts/todofmt_check.sh`（docs/TODOFMT_SPEC.md Task 0.2）。

邊界①–⑦ 以真實 repo 之兩支腳本判定（manifest 內路徑相對真實 repo 根）；
邊界⑧ 斷言轉呼叫與檢查器之 rc 與 stdout 逐一相等；邊界⑨ 與覆蓋風險斷言 `template_check.sh` 之改動恰為一行。
"""

from __future__ import annotations

import json
import re
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
    ctrl = json.loads(json.dumps(v))
    ctrl["test_files"] = ["tests/governance/test_template_check_todofmt.py\n../outside"]
    return {
        "valid": _write(tmp_path, "valid.json", v),
        "b1_missing": tmp_path / "absent.json",
        "b2_invalid_json": _write(tmp_path, "invalid.json", "{not json"),
        "b3_missing_category": _write(tmp_path, "no_cat.json", no_cat),
        "b4_exists_true_missing": _write(tmp_path, "missing_path.json", missing_path),
        "b5_no_owner": _write(tmp_path, "no_owner.json", no_owner),
        "b6_bad_expiry": _write(tmp_path, "bad_expiry.json", bad_expiry),
        "b7_exists_false_absent": _write(tmp_path, "later_absent.json", later_absent),
        "b4b_control_char_in_path": _write(tmp_path, "ctrl.json", ctrl),
    }


def test_boundary_04b_control_character_in_path_fails(tmp_path: Path) -> None:
    """b1 審碼：路徑值夾帶換行時，其後段不得逃過路徑規則（經 wrapper 亦同）。"""
    r = _tc(_inputs(tmp_path)["b4b_control_char_in_path"])
    assert r.returncode == 1 and "控制字元" in r.stdout, r.stdout


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
    assert direct.returncode == 0, direct.stdout
    # 前提：同佈局之未改壞複本與檢查器等價（排除「因別的理由而不等」之假綠）
    (scripts / "template_check_orig.sh").write_text(src, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "TEMPLATE_CHECK", scripts / "template_check_orig.sh")
    orig = _tc(mf)
    assert (orig.returncode, orig.stdout) == (direct.returncode, direct.stdout), orig.stdout + orig.stderr
    monkeypatch.setattr(sys.modules[__name__], "TEMPLATE_CHECK", scripts / "template_check.sh")
    via = _tc(mf)
    assert (via.returncode, via.stdout) != (direct.returncode, direct.stdout), "移除 exec 後仍等價 ⇒ 邊界⑧ 無鑑別力"


# ── C-2 實作期補強（產出端覆蓋鐵律）：manifest 寫入當下即以同一檢查器判定（PostToolUse）──────────────

GUARD = REPO_ROOT / "scripts" / "todofmt_manifest_guard.sh"
GUARD_CMD = "bash scripts/todofmt_manifest_guard.sh"


def _guard_repo(tmp_path: Path) -> tuple[Path, Path]:
    """迷你 repo：守衛（取自模組層級 GUARD，mutation 探針以 monkeypatch 換成改壞之複本）、檢查器與契約之複本；回（根, 守衛）。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    guard = scripts / "todofmt_manifest_guard.sh"
    guard.write_text(GUARD.read_text(encoding="utf-8"), encoding="utf-8")
    shutil.copy(CHECKER, scripts / "todofmt_check.sh")
    shutil.copy(REPO_ROOT / "scripts" / "todofmt_contract.json", scripts / "todofmt_contract.json")
    (root / "tests").mkdir()
    (root / "tests" / "t.py").write_text("x\n", encoding="utf-8")
    (root / "docs" / "manifests").mkdir(parents=True)
    return root, guard


def _mini_manifest(root: Path, **batch_card: object) -> str:
    """路徑相對迷你 repo 根之合法 manifest；以 batch_card 參數覆寫欄位可造出不合法者。"""
    digest = subprocess.run(["bash", str(root / "scripts" / "todofmt_check.sh"), "--digest"],
                            capture_output=True, text=True, check=True).stdout.strip()
    m = _valid()
    m.update(test_files=["tests/t.py"], spec_path="scripts/todofmt_contract.json", contract_digest=digest)
    m["batch_card"]["touches"] = ["tests/t.py"]
    m["batch_card"].update(batch_card)
    return json.dumps(m, ensure_ascii=False)


def _post(guard: Path, file_path: str, tool: str = "Write") -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": tool, "tool_input": {"file_path": file_path}})
    return subprocess.run(["bash", str(guard)], input=payload, capture_output=True, text=True, check=False)


def test_manifest_guard_mounted_post_tool_use() -> None:
    settings = json.loads((REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    cmds = [
        h.get("command")
        for e in settings.get("hooks", {}).get("PostToolUse", [])
        if all(re.fullmatch(f"(?:{e.get('matcher') or ''})", t) for t in ("Edit", "Write"))
        for h in e.get("hooks", [])
    ]
    assert GUARD_CMD in cmds, cmds


@pytest.mark.parametrize("name", ["TODOFMT.json", "FFTFMETA.json"])
def test_manifest_guard_real_manifests_pass(name: str) -> None:
    assert _post(GUARD, f"docs/manifests/{name}").returncode == 0


def test_manifest_guard_valid_manifest_passes(tmp_path: Path) -> None:
    root, guard = _guard_repo(tmp_path)
    mf = root / "docs" / "manifests" / "X.json"
    mf.write_text(_mini_manifest(root), encoding="utf-8")
    for tool in ("Write", "Edit"):
        r = _post(guard, str(mf), tool)
        assert r.returncode == 0, r.stderr


def test_manifest_guard_invalid_manifest_blocked(tmp_path: Path) -> None:
    root, guard = _guard_repo(tmp_path)
    (root / "docs" / "manifests" / "X.json").write_text(_mini_manifest(root, lifecycle="forever"), encoding="utf-8")
    for fp in (str(root / "docs" / "manifests" / "X.json"), "docs/manifests/X.json", "./docs/manifests/X.json"):
        r = _post(guard, fp)
        assert r.returncode == 2 and "未過 todofmt 機檢" in r.stderr, (fp, r.stderr)


def test_manifest_guard_alias_path_governed(tmp_path: Path) -> None:
    """經指向 repo 之符號連結寫入：所在目錄以 -ef 比對，與正規路徑同判。"""
    root, guard = _guard_repo(tmp_path)
    (root / "docs" / "manifests" / "X.json").write_text(_mini_manifest(root, lifecycle="forever"), encoding="utf-8")
    link = tmp_path / "repolink"
    link.symlink_to(root, target_is_directory=True)
    assert (link / "docs" / "manifests").samefile(root / "docs" / "manifests")
    r = _post(guard, str(link / "docs" / "manifests" / "X.json"))
    assert r.returncode == 2 and "未過 todofmt 機檢" in r.stderr, r.stderr


def test_manifest_guard_out_of_scope_not_checked(tmp_path: Path) -> None:
    """管轄外（子目錄、docs/ 他處、非 .json、不存在之檔）一律放行，即使內容不合法。"""
    root, guard = _guard_repo(tmp_path)
    bad = _mini_manifest(root, lifecycle="forever")
    for rel in ("docs/manifests/sub/X.json", "docs/X.json", "docs/manifests/X.txt"):
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(bad, encoding="utf-8")
        assert _post(guard, str(p)).returncode == 0, rel
    assert _post(guard, str(root / "docs" / "manifests" / "absent.json")).returncode == 0


def test_mutation_guard_without_checker_lets_invalid_through(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """守衛不呼叫檢查器 ⇒ 不合法 manifest 放行（證上述擋下之測試有鑑別力）。"""
    src = GUARD.read_text(encoding="utf-8")
    call = '_out="$(bash "${SCRIPT_DIR}/todofmt_check.sh" "${_abs}" 2>&1)" && exit 0'
    assert src.count(call) == 1
    # 前提：同佈局之未改壞複本擋下不合法 manifest（排除「因別的理由而放行」之假綠）
    root, guard = _guard_repo(tmp_path / "orig")
    (root / "docs" / "manifests" / "X.json").write_text(_mini_manifest(root, lifecycle="forever"), encoding="utf-8")
    assert _post(guard, str(root / "docs" / "manifests" / "X.json")).returncode == 2
    mutant = tmp_path / "mutant_guard.sh"
    mutant.write_text(src.replace(call, "exit 0"), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "GUARD", mutant)
    root2, guard2 = _guard_repo(tmp_path / "mut")
    (root2 / "docs" / "manifests" / "X.json").write_text(_mini_manifest(root2, lifecycle="forever"), encoding="utf-8")
    assert _post(guard2, str(root2 / "docs" / "manifests" / "X.json")).returncode == 0
