"""scripts/temp_output_guard.py：要再用之檔不得落在系統暫存（秒級；每條規則附改壞對照——放行樣式與擋下樣式並列）。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "temp_output_guard.py"


@pytest.fixture(scope="module")
def guard():
    spec = importlib.util.spec_from_file_location("temp_output_guard", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _bash(guard, cmd: str):
    return guard.check({"tool_name": "Bash", "tool_input": {"command": cmd}})


@pytest.mark.parametrize("cmd", [
    "venv/bin/python scripts/icperf_correctness_receipt.py capture --out-dir /private/tmp/claude-501/x",
    "venv/bin/python scripts/x.py --out=/tmp/a.json",
    "venv/bin/python scripts/x.py --work-root /var/folders/_c/abc/T/run",
    "python3 /private/tmp/claude-501/s/est_match.py icperf_freeze cmd.txt",
    "bash /tmp/helper.sh",
    "echo hi && venv/bin/python scripts/x.py --receipt /private/var/folders/aa/T/r.json",
])
def test_bash_blocks_temp_outputs_and_temp_scripts(guard, cmd: str) -> None:
    assert _bash(guard, cmd), cmd


@pytest.mark.parametrize("cmd", [
    "venv/bin/python scripts/icperf_correctness_receipt.py capture --out-dir data_cache/icperf_inputs/cap",
    "venv/bin/python scripts/run_watched.py --log /private/tmp/claude-501/a.log -- pytest tests/x.py",
    "pytest tests/x.py -q > /private/tmp/claude-501/x.log 2>&1",
    "cat /private/tmp/claude-501/s/est_match.py",
    "git commit -F /private/tmp/claude-501/s/msg.txt",
    "ls /tmp/",
])
def test_bash_allows_logs_reads_and_repo_outputs(guard, cmd: str) -> None:
    assert _bash(guard, cmd) == [], cmd


def _edit(guard, path: str, new: str):
    return guard.check({"tool_name": "Edit", "tool_input": {"file_path": str(REPO / path), "new_string": new}})


@pytest.mark.parametrize("new", [
    'DEFAULT_WORK_ROOT = Path(os.environ.get("TMPDIR", "/tmp")) / "x"',
    "root = Path(tempfile.gettempdir()) / 'x'",
    'OUT = Path("/tmp/dstar")',
    "work = Path(tempfile.mkdtemp(prefix='x-'))",
])
def test_code_blocks_temp_defaults(guard, new: str) -> None:
    assert _edit(guard, "scripts/some_tool.py", new), new
    assert _edit(guard, "momentum/Analysis/some_mod.py", new), new


@pytest.mark.parametrize("new", [
    "with tempfile.TemporaryDirectory() as d:",
    "work = Path(tempfile.mkdtemp(prefix='x-', dir=str(base)))",
    'OUT = REPO / "data_cache" / "profiles" / "x"',
    'env["TMPDIR"] = str(iso / "tmp")',
])
def test_code_allows_self_deleting_scratch_and_repo_paths(guard, new: str) -> None:
    assert _edit(guard, "scripts/some_tool.py", new) == [], new


def test_code_scope_shell_and_outside_paths(guard) -> None:
    assert _edit(guard, "scripts/x.sh", 'LOG=/tmp/x.log') and _edit(guard, "scripts/x.sh", 'f=$(mktemp); trap "rm -f $f" EXIT') == []
    assert _edit(guard, "docs/X.md", 'OUT = Path("/tmp/x")') == [], "文件不在檢查範圍"
    assert guard.check({"tool_name": "Write", "tool_input": {"file_path": "/private/tmp/claude-501/s/a.py",
                                                             "content": 'Path("/tmp/x")'}}) == [], "repo 外檔不查"
    multi = {"tool_name": "MultiEdit", "tool_input": {"file_path": str(REPO / "api/x.py"),
                                                      "edits": [{"new_string": "ok = 1"}, {"new_string": "p = '/tmp/a'"}]}}
    assert guard.check(multi)


def test_cli_rc_and_message(guard) -> None:
    bad = json.dumps({"tool_name": "Bash", "tool_input": {"command": "python3 scripts/x.py --out /tmp/a"}})
    good = json.dumps({"tool_name": "Bash", "tool_input": {"command": "python3 scripts/x.py --out data_cache/a"}})
    r = subprocess.run([sys.executable, str(SCRIPT)], input=bad, capture_output=True, text=True)
    assert r.returncode == 2 and "data_cache/" in r.stderr
    assert subprocess.run([sys.executable, str(SCRIPT)], input=good, capture_output=True, text=True).returncode == 0
    assert subprocess.run([sys.executable, str(SCRIPT)], input="not json", capture_output=True, text=True).returncode == 0
