"""TESTREG Task 1.4 驗收：`pytest.ini` 註冊 flaky_quarantine 與 timeout；`scripts/testreg.py markers` 對未註冊標記 rc≠0
（docs/TESTREG_SPEC.md）。9 處 `pytest.mark.timeout` 宣告保留不動。實作前（空殼）為紅。"""
from __future__ import annotations

import configparser
import subprocess

from tests.registry.testreg_helpers import PY, REPO, TESTREG, clean_env, make_repo

INI_HEAD = "[pytest]\ntestpaths = tests\nmarkers =\n    slow: s\n"


def _registered(ini_text: str):
    cp = configparser.ConfigParser()
    cp.read_string(ini_text)
    return {l.split(":", 1)[0].strip() for l in cp["pytest"]["markers"].splitlines() if l.strip()}


def test_pytest_ini_registers_flaky_quarantine_and_timeout():
    text = (REPO / "pytest.ini").read_text(encoding="utf-8")
    assert {"flaky_quarantine", "timeout"} <= _registered(text)
    timeout_line = next(l for l in text.splitlines() if l.strip().startswith("timeout:"))
    assert "pytest-timeout" in timeout_line and "未安裝" in timeout_line


def test_timeout_declarations_untouched():
    out = subprocess.run(["git", "-C", str(REPO), "grep", "-c", "pytest.mark.timeout", "--", "tests"],
                         capture_output=True, text=True).stdout
    total = sum(int(l.rsplit(":", 1)[1]) for l in out.splitlines() if l.strip())
    test_self = sum(int(l.rsplit(":", 1)[1]) for l in out.splitlines() if l.startswith("tests/registry/"))
    assert total - test_self == 9


def test_real_tree_markers_rc0():
    proc = subprocess.run([PY, str(TESTREG), "markers"], capture_output=True, text=True, env=clean_env(), cwd=str(REPO))
    assert proc.returncode == 0, proc.stderr


def test_unregistered_marker_rc_nonzero(tmp_path):
    r = make_repo(tmp_path, {"tests/test_m.py": "import pytest\n\n\n@pytest.mark.mystery\ndef test_x():\n    assert True\n"},
                  catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    assert proc.returncode != 0
    assert any(l.startswith("MARKER ") and "tests/test_m.py:4" in l and "mystery" in l for l in proc.stderr.splitlines())


def test_comment_and_string_not_counted(tmp_path):
    src = ('import pytest\n\n# pytest.mark.mystery in a comment\nDOC = "pytest.mark.mystery in a string"\n\n\n'
           "@pytest.mark.slow\ndef test_x():\n    assert True\n")
    r = make_repo(tmp_path, {"tests/test_m.py": src}, catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    assert proc.returncode == 0, proc.stderr


def test_plugin_registered_marker_allowed(tmp_path):
    """外掛／conftest 以 `config.addinivalue_line("markers", "<名>: …")` 註冊之標記視同已註冊（真實樹之
    ic_persist_redirect 即此形態）；同檔未註冊者仍報。"""
    conftest = 'def pytest_configure(config):\n    config.addinivalue_line("markers", "custom_reg: by plugin")\n'
    test = ("import pytest\n\n\n@pytest.mark.custom_reg\ndef test_x():\n    assert True\n\n\n"
            "@pytest.mark.not_registered_anywhere\ndef test_y():\n    assert True\n")
    r = make_repo(tmp_path, {"tests/conftest.py": conftest, "tests/test_m.py": test}, catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    lines = [l for l in proc.stderr.splitlines() if l.startswith("MARKER ")]
    assert proc.returncode != 0 and len(lines) == 1 and "not_registered_anywhere" in lines[0], proc.stderr


def test_registration_only_from_loaded_conftest_or_plugins(tmp_path):
    """承認範圍限 conftest.py 與其 pytest_plugins 所列外掛：未被載入之 helper 檔中之 addinivalue_line 不算註冊。"""
    plugin = 'def pytest_configure(config):\n    config.addinivalue_line("markers", "via_plugin: listed plugin")\n'
    helper = 'def pytest_configure(config):\n    config.addinivalue_line("markers", "via_helper: not loaded")\n'
    test = ("import pytest\n\n\n@pytest.mark.via_plugin\ndef test_x():\n    assert True\n\n\n"
            "@pytest.mark.via_helper\ndef test_y():\n    assert True\n")
    r = make_repo(tmp_path, {"tests/__init__.py": "", "tests/conftest.py": 'pytest_plugins = ["tests.my_plugin"]\n',
                             "tests/my_plugin.py": plugin, "tests/helper_reg.py": helper, "tests/test_m.py": test},
                  catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    lines = [l for l in proc.stderr.splitlines() if l.startswith("MARKER ")]
    assert proc.returncode != 0 and len(lines) == 1 and "via_helper" in lines[0], proc.stderr


def test_repo_root_conftest_and_its_plugins_registration_allowed(tmp_path):
    """repo 根之 conftest.py 及其 pytest_plugins 所列外掛之字面註冊亦承認（忽略根層之掃描器即紅）。"""
    root_conftest = ('pytest_plugins = ["rootplug"]\n\n\ndef pytest_configure(config):\n'
                     '    config.addinivalue_line("markers", "root_reg: root conftest")\n')
    rootplug = 'def pytest_configure(config):\n    config.addinivalue_line("markers", "rootplug_reg: root plugin")\n'
    test = ("import pytest\n\n\n@pytest.mark.root_reg\ndef test_x():\n    assert True\n\n\n"
            "@pytest.mark.rootplug_reg\ndef test_y():\n    assert True\n")
    r = make_repo(tmp_path, {"conftest.py": root_conftest, "rootplug.py": rootplug, "tests/test_m.py": test},
                  catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    assert proc.returncode == 0, proc.stderr


def test_builtin_markers_allowed(tmp_path):
    src = ("import pytest\n\n\n@pytest.mark.parametrize('a', [1])\n@pytest.mark.skipif(False, reason='r')\n"
           "@pytest.mark.xfail(reason='r')\n@pytest.mark.usefixtures('tmp_path')\n@pytest.mark.filterwarnings('ignore')\n"
           "def test_x(a):\n    pytest.mark.skip\n")
    r = make_repo(tmp_path, {"tests/test_m.py": src}, catalog=False)
    r.write("pytest.ini", INI_HEAD)
    assert r.run("markers").returncode == 0


def test_boundary_01_pytestmark_list_form_both_scanned(tmp_path):
    src = "import pytest\n\npytestmark = [pytest.mark.slow, pytest.mark.timeout(10)]\n\n\ndef test_x():\n    assert True\n"
    r = make_repo(tmp_path, {"tests/test_m.py": src}, catalog=False)
    r.write("pytest.ini", INI_HEAD)
    proc = r.run("markers")
    lines = [l for l in proc.stderr.splitlines() if l.startswith("MARKER ")]
    assert proc.returncode != 0 and len(lines) == 1 and "timeout" in lines[0], proc.stderr
    r.write("pytest.ini", INI_HEAD + "    timeout: t\n")
    assert r.run("markers").returncode == 0


def test_mutation_markers_ignores_list_form(tmp_path, monkeypatch):
    """mutant：掃描器只看 decorator（不看清單形式 pytestmark）⇒ 邊界案之未註冊 timeout 漏報。"""
    import ast
    import importlib
    testreg = importlib.import_module("scripts.testreg")
    src = "import pytest\n\npytestmark = [pytest.mark.slow, pytest.mark.timeout(10)]\n\n\ndef test_x():\n    assert True\n"
    r = make_repo(tmp_path, {"tests/test_m.py": src}, catalog=False)
    r.write("pytest.ini", INI_HEAD)
    assert [n for _, _, n in testreg.unregistered_markers(r.root)] == ["timeout"]

    def decorators_only(repo_root):
        out = []
        for p in sorted((repo_root / "tests").rglob("test_*.py")):
            for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
                if isinstance(node, ast.FunctionDef):
                    for d in node.decorator_list:
                        f = d.func if isinstance(d, ast.Call) else d
                        if isinstance(f, ast.Attribute) and f.attr not in {"slow"}:
                            out.append((str(p.relative_to(repo_root)), d.lineno, f.attr))
        return out

    monkeypatch.setattr(testreg, "unregistered_markers", decorators_only)
    assert testreg.main(["--repo", str(r.root), "markers"]) == 0
