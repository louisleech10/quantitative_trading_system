"""ICPERF SPEC §G ①：凍結重型子命令於固定提交之 git worktree 副本執行（`scripts/icperf_isolated_run.py`）與凍結腳本之
隔離守門（`scripts/icperf_freeze_baseline.py` 之 `isolation_problems`／CLI 拒跑）。

以暫存 git repo 驗證，不讀 data_cache、不跑產品計算（秒級）。"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[3]
RUNNER = REPO / "scripts" / "icperf_isolated_run.py"
FREEZE = REPO / "scripts" / "icperf_freeze_baseline.py"

_FAKE_FREEZE = '''import json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
MARKER = "{marker}"
cmd = sys.argv[1]
if cmd == "isolated-inputs":
    print(json.dumps(["data_cache/inp"]))
elif cmd == "where":
    Path(sys.argv[2]).write_text(json.dumps({{"file": str(Path(__file__).resolve()), "marker": MARKER,
        "env": os.environ.get("ICPERF_ISOLATED_COMMIT"), "cwd": os.path.realpath(os.getcwd()),
        "inp_link": os.path.islink(str(REPO / "data_cache" / "inp"))}}))
elif cmd == "write-input":
    (REPO / "data_cache" / "inp" / "a.txt").write_text("changed")
elif cmd == "fail":
    sys.exit(3)
'''


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


@pytest.fixture(scope="module")
def fb() -> Any:
    return _load("icperf_freeze_baseline_isotest", FREEZE)


def _git(cwd: Path, *args: str) -> str:
    res = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(cwd), *args],
                         capture_output=True, text=True, check=True)
    return res.stdout.strip()


def _commit_all(cwd: Path, msg: str) -> str:
    _git(cwd, "add", "-A")
    _git(cwd, "commit", "-q", "-m", msg)
    return _git(cwd, "rev-parse", "HEAD")


@pytest.fixture()
def main_repo(tmp_path: Path) -> Path:
    """暫存主 repo：執行器本體＋假凍結腳本（MARKER v1 已提交）＋ data_cache/inp 唯讀輸入（不入版控）。"""
    main = (tmp_path / "main").resolve()
    (main / "scripts").mkdir(parents=True)
    shutil.copy2(RUNNER, main / "scripts" / RUNNER.name)
    (main / "scripts" / "icperf_freeze_baseline.py").write_text(_FAKE_FREEZE.format(marker="v1"), encoding="utf-8")
    (main / ".gitignore").write_text("data_cache/\nruns/\n", encoding="utf-8")
    (main / "data_cache" / "inp").mkdir(parents=True)
    (main / "data_cache" / "inp" / "a.txt").write_text("orig", encoding="utf-8")
    _git(main, "init", "-q")
    _commit_all(main, "init")
    return main


def _run(main: Path, receipt: Path, *freeze_args: str, commit: str = "HEAD") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(main / "scripts" / RUNNER.name), "--commit", commit, "--batch", "b1",
                           "--receipt", str(receipt), "--", *freeze_args], capture_output=True, text=True, cwd=str(main))


def test_runner_loads_code_from_worktree_at_commit(main_repo: Path, tmp_path: Path) -> None:
    """副本執行：程式碼自 `runs/b1/wt-<sha12>` 載入（主 repo 之未提交改動不影響）、cwd＝副本、環境變數＝宣告提交、
    唯讀輸入為 symlink；收據 pass 且 HEAD 前後等於宣告提交。"""
    sha = _git(main_repo, "rev-parse", "HEAD")
    (main_repo / "scripts" / "icperf_freeze_baseline.py").write_text(_FAKE_FREEZE.format(marker="v2"), encoding="utf-8")
    out, receipt = tmp_path / "where.json", tmp_path / "r.json"
    res = _run(main_repo, receipt, "where", str(out))
    assert res.returncode == 0, res.stderr
    wt = main_repo / "runs" / "b1" / f"wt-{sha[:12]}"
    got = json.loads(out.read_text())
    assert got["marker"] == "v1"
    assert got["file"] == str((wt / "scripts" / "icperf_freeze_baseline.py").resolve())
    assert got["cwd"] == str(wt.resolve()) and got["env"] == sha and got["inp_link"] is True
    rec = json.loads(receipt.read_text())
    assert rec["pass"] is True and rec["commit"] == sha and rec["head_before"] == sha and rec["head_after"] == sha
    assert rec["inputs_unchanged"] is True and rec["inputs"]["data_cache/inp"]["n_files"] == 1


def test_runner_fails_when_readonly_input_written(main_repo: Path, tmp_path: Path) -> None:
    """唯讀輸入經 symlink 被寫 ⇒ 跑前跑後逐檔 sha256 不同 ⇒ 收據 pass＝false、rc≠0、差異具名。"""
    receipt = tmp_path / "r.json"
    res = _run(main_repo, receipt, "write-input")
    assert res.returncode != 0
    rec = json.loads(receipt.read_text())
    assert rec["pass"] is False and rec["inputs_unchanged"] is False
    assert rec["input_changes"] == ["改變 data_cache/inp/a.txt"]


def test_runner_propagates_child_failure(main_repo: Path, tmp_path: Path) -> None:
    receipt = tmp_path / "r.json"
    res = _run(main_repo, receipt, "fail")
    assert res.returncode == 3
    assert json.loads(receipt.read_text())["pass"] is False


def test_runner_rejects_existing_worktree_at_other_commit(main_repo: Path, tmp_path: Path) -> None:
    """既有副本路徑之 HEAD ≠ 宣告提交 ⇒ 拒跑（不沿用他提交之副本）。"""
    sha1 = _git(main_repo, "rev-parse", "HEAD")
    (main_repo / "x.txt").write_text("x", encoding="utf-8")
    sha2 = _commit_all(main_repo, "second")
    wt = main_repo / "runs" / "b1" / f"wt-{sha1[:12]}"
    _git(main_repo, "worktree", "add", "-q", "--detach", str(wt), sha2)
    res = _run(main_repo, tmp_path / "r.json", "where", str(tmp_path / "w.json"), commit=sha1)
    assert res.returncode == 1 and "IsolationError" in res.stderr and not (tmp_path / "w.json").exists()


@pytest.fixture()
def linked_wt(tmp_path: Path, fb: Any) -> Dict[str, Any]:
    """合格副本：暫存主 repo 之 linked worktree，`ISOLATED_INPUTS` 皆以 symlink 指向副本外目錄。"""
    main = (tmp_path / "m").resolve()
    main.mkdir()
    (main / ".gitignore").write_text("data_cache/\n", encoding="utf-8")
    (main / "pkg").mkdir()
    (main / "pkg" / "__pycache__").mkdir()
    (main / "pkg" / "code.py").write_text("x = 1\n", encoding="utf-8")
    (main / "pkg" / "__pycache__" / "k.nbi").write_text("cache", encoding="utf-8")
    _git(main, "init", "-q")
    sha = _commit_all(main, "init")
    wt = (tmp_path / "wt").resolve()
    _git(main, "worktree", "add", "-q", "--detach", str(wt), sha)
    ext = (tmp_path / "ext").resolve()
    for rel in fb.ISOLATED_INPUTS:
        (ext / rel).mkdir(parents=True)
        (wt / rel).parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(ext / rel), str(wt / rel))
    return {"main": main, "wt": wt, "sha": sha, "env": {fb.ISOLATED_COMMIT_ENV: sha}}


def test_isolation_ok_in_linked_worktree(fb: Any, linked_wt: Dict[str, Any], tmp_path: Path) -> None:
    wt = linked_wt["wt"]
    (wt / "pkg" / "__pycache__" / "k.nbi").write_text("rewritten by numba", encoding="utf-8")
    assert fb.isolation_problems(wt, env=linked_wt["env"], outside_paths=[tmp_path / "golden.json.gz"]) == []


@pytest.mark.parametrize("case", ["no_env", "env_mismatch", "main_repo", "tracked_dirty", "input_not_symlink",
                                  "input_points_inside", "golden_inside"])
def test_isolation_problems_each_condition(fb: Any, linked_wt: Dict[str, Any], case: str) -> None:
    """每一合格條件單獨破壞 ⇒ 恰列出問題（反例腿）。"""
    root, env, outside = linked_wt["wt"], dict(linked_wt["env"]), []
    if case == "no_env":
        env = {}
    elif case == "env_mismatch":
        env = {fb.ISOLATED_COMMIT_ENV: "0" * 40}
    elif case == "main_repo":
        root = linked_wt["main"]
        for rel in fb.ISOLATED_INPUTS:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            os.symlink(str((linked_wt["wt"] / rel).resolve()), str(root / rel))
    elif case == "tracked_dirty":
        (root / "pkg" / "code.py").write_text("x = 2\n", encoding="utf-8")
    elif case == "input_not_symlink":
        rel = fb.ISOLATED_INPUTS[0]
        os.unlink(str(root / rel))
        (root / rel).mkdir()
    elif case == "input_points_inside":
        rel = fb.ISOLATED_INPUTS[0]
        os.unlink(str(root / rel))
        (root / "inside").mkdir()
        os.symlink(str(root / "inside"), str(root / rel))
    elif case == "golden_inside":
        outside = [root / "tests" / "_golden" / "g.json.gz"]
    probs = fb.isolation_problems(root, env=env, outside_paths=outside)
    assert len(probs) == 1, probs


@pytest.mark.parametrize("argv", [["freeze", "--out", "/nonexistent/g.json.gz"],
                                  ["repro", "--golden", "/nonexistent/g.json.gz"],
                                  ["volatile-probe", "--out", "/nonexistent/p.json", "--golden", "/nonexistent/g.json.gz"]])
def test_cli_refuses_heavy_cmd_outside_isolated_copy(fb: Any, monkeypatch: pytest.MonkeyPatch, argv: list,
                                                     capsys: pytest.CaptureFixture) -> None:
    """主 repo（非副本、未設宣告提交）下 freeze／repro／volatile-probe ⇒ rc 1 且未啟動任何工作。"""
    monkeypatch.delenv(fb.ISOLATED_COMMIT_ENV, raising=False)
    for fn in ("freeze", "repro", "volatile_probe", "preflight"):
        monkeypatch.setattr(fb, fn, lambda *a, **k: pytest.fail("隔離檢查前即啟動工作"))
    assert fb.main(argv) == 1
    assert "SPEC §G ①" in capsys.readouterr().err


def test_isolated_inputs_cover_spec_list(fb: Any) -> None:
    """SPEC §G ① 所列唯讀輸入（feature_klines、feature_klines_longhist、numview_freeze_runs、icperf_inputs、events）。"""
    spec = (REPO / "docs" / "ICPERF_SPEC.md").read_text(encoding="utf-8")
    line = next(ln for ln in spec.splitlines() if ln.lstrip().startswith("- ① 隔離副本"))
    for rel in fb.ISOLATED_INPUTS:
        assert f"`{rel.split('/', 1)[1]}`" in line, rel
