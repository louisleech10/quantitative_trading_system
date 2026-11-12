"""scripts/readtrace_plugin.py：逐 nodeid 記錄讀取之 repo 內檔案、`--trace-select` 只跑所列 nodeid（TEST_SELECTION §5 過渡工具）。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_BODY = '''
from pathlib import Path
REPO = Path(r"{repo}")

def test_reads_ini():
    (REPO / "pytest.ini").read_text(encoding="utf-8")

def test_reads_nothing():
    assert True

def test_writes_only(tmp_path):
    (tmp_path / "x.txt").write_text("x")

def test_spawns():
    import subprocess
    subprocess.run(["/bin/echo", "readtrace-probe"], check=True, capture_output=True)

def test_spawns_in_subdir():
    import subprocess
    subprocess.run(["/bin/echo", "cwd-probe"], check=True, capture_output=True, cwd=str(REPO / "scripts"))
'''


def _run(tmp_path: Path, *extra: str) -> subprocess.CompletedProcess:
    test = tmp_path / "test_probe_rt.py"
    test.write_text(_BODY.format(repo=REPO), encoding="utf-8")
    out = tmp_path / "rt.jsonl"
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "--rootdir", str(tmp_path), *extra, str(test)],
                          cwd=REPO, env={"READTRACE_OUT": str(out), "PATH": "/usr/bin:/bin"},
                          capture_output=True, text=True)


def _records(tmp_path: Path, key: str = "files") -> dict:
    lines = (tmp_path / "rt.jsonl").read_text(encoding="utf-8").splitlines()
    return {json.loads(x)["nodeid"].split("::")[-1]: json.loads(x)[key] for x in lines}


def test_records_repo_reads_per_nodeid(tmp_path: Path) -> None:
    """讀 repo 檔之測試記該檔；未讀者空；寫入不記。"""
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = _records(tmp_path)
    assert rec["test_reads_ini"] == ["pytest.ini"]
    assert rec["test_reads_nothing"] == [] and rec["test_writes_only"] == []


def test_records_spawned_commands_per_nodeid(tmp_path: Path) -> None:
    """子行程命令逐 nodeid 記錄；未啟動子行程者空。"""
    proc = _run(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    procs = _records(tmp_path, "procs")
    assert procs["test_spawns"] == ["/bin/echo readtrace-probe"]
    assert procs["test_reads_ini"] == []
    cwds = _records(tmp_path, "proc_cwds")  # 子行程工作目錄：指定 cwd 者記該目錄、未指定者記當下 cwd
    assert cwds["test_spawns_in_subdir"] == [str((REPO / "scripts").resolve())]
    assert cwds["test_spawns"] == [str(REPO)]


def test_fixture_setup_cost_recorded_on_first_user_only(tmp_path: Path) -> None:
    """非 function 範圍 fixture 之實測建置秒數記於觸發建置之第一個使用者（`fixture_setup_s`，id 同 `shared`）；後續
    使用者不重記；function 範圍不記（審碼 r5 CODEX-R5-P1-03：估時依實測成本而非耗時差距）。"""
    test = tmp_path / "test_probe_fx.py"
    test.write_text("import time\nimport pytest\n\n@pytest.fixture(scope='module')\ndef heavy_fx():\n"
                    "    time.sleep(0.3)\n    return 1\n\n@pytest.fixture\ndef light_fx():\n    return 2\n\n"
                    "def test_first(heavy_fx, light_fx):\n    assert heavy_fx == 1\n\n"
                    "def test_second(heavy_fx):\n    assert heavy_fx == 1\n", encoding="utf-8")
    out = tmp_path / "rt.jsonl"
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "--rootdir", str(tmp_path), str(test)],
                          cwd=REPO, env={"READTRACE_OUT": str(out), "PATH": "/usr/bin:/bin"},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    costs = _records(tmp_path, "fixture_setup_s")
    shared = _records(tmp_path, "shared")
    fid = next(x for x in shared["test_first"] if x.endswith("::heavy_fx"))
    assert costs["test_first"][fid] >= 0.3
    assert not any(k.startswith("function:") or k.endswith("::light_fx") for k in costs["test_first"])
    assert fid not in costs["test_second"] and fid in shared["test_second"]


def test_relative_out_survives_chdir(tmp_path: Path) -> None:
    """READTRACE_OUT 為相對路徑、測試中途切換 cwd 未還原 ⇒ 仍寫入啟動時 cwd 下之同一檔，不 INTERNALERROR。"""
    test = tmp_path / "test_probe_cd.py"
    test.write_text("import os\n\ndef test_a_chdir():\n    os.chdir('/')\n\ndef test_b_after():\n    assert True\n",
                    encoding="utf-8")
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "--rootdir", str(tmp_path), str(test)],
                          cwd=tmp_path, env={"READTRACE_OUT": "rt.jsonl", "PATH": "/usr/bin:/bin",
                                             "PYTHONPATH": str(REPO)},
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert set(_records(tmp_path)) == {"test_a_chdir", "test_b_after"}


def test_trace_select_runs_only_listed(tmp_path: Path) -> None:
    """`--trace-select` ⇒ 只執行所列 nodeid；所列 nodeid 未收集到 ⇒ UsageError（rc 4）不靜默略過。"""
    sel = tmp_path / "sel.txt"
    sel.write_text("test_probe_rt.py::test_reads_nothing\n", encoding="utf-8")
    proc = _run(tmp_path, "--trace-select", str(sel))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert set(_records(tmp_path)) == {"test_reads_nothing"}
    sel.write_text("test_probe_rt.py::test_missing\n", encoding="utf-8")
    assert _run(tmp_path, "--trace-select", str(sel)).returncode == 4
