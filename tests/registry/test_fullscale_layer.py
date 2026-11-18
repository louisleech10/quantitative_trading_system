"""TESTSEL I4f 全規模層驗收（docs/TESTSEL_I4F_SPEC.md Task 1.1）。

pytest 官方範例寫法（測試函式上 `@pytest.mark.fullscale`＋`--run-fullscale` 開關），延後採 deselect。暫存 repo＋子行程 pytest：
複製 `tests/fixtures/fullscale_layer_plugin.py`，`tests/test_a.py::test_full`（參數化）帶標記；驗收預設層具名延後、`--run-fullscale`
照跑、`-m` 篩選、既有手寫 `slow` 不受影響、登記檔未收集、collect-only、testmon 共存、與硬體閘重疊；正式 conftest 註冊、pytest.ini
宣告、addopts 無 `-m`、d1f57180 全規模清單 23 條皆帶標記。
"""
from __future__ import annotations

import ast
import configparser
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PLUGIN_REL = "tests/fixtures/fullscale_layer_plugin.py"
PLUGIN_MOD = "tests.fixtures.fullscale_layer_plugin"
OPT = "--run-fullscale"
HW_MODULE_REL = "scripts/hardware_requirements.py"
HW_PLUGIN_MOD = "tests.fixtures.hardware_gate_plugin"
HW_MEM_LINE = '    return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))'
FULL = ("tests/test_a.py::test_full[1]", "tests/test_a.py::test_full[2]")
FAST = "tests/test_a.py::test_fast"
OTHER = "tests/test_b.py::test_other"
A_SRC = ("import pytest\n\n\n@pytest.mark.fullscale\n@pytest.mark.parametrize('x', [1, 2])\ndef test_full(x):\n"
         "    assert x\n\n\ndef test_fast():\n    assert True\n")
FILES = ["tests/test_a.py", "tests/test_b.py"]


def _fs_repo(tmp_path: Path, *, plugin: bool = True, hw_mem_gib: object = None) -> Path:
    r = tmp_path / "repo"
    (r / "tests" / "fixtures").mkdir(parents=True)
    (r / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (r / "tests" / "fixtures" / "__init__.py").write_text("", encoding="utf-8")
    (r / PLUGIN_REL).write_text((REPO / PLUGIN_REL).read_text(encoding="utf-8"), encoding="utf-8")
    plugins = [PLUGIN_MOD] if plugin else []
    if hw_mem_gib is not None:
        (r / "scripts").mkdir()
        src = (REPO / HW_MODULE_REL).read_text(encoding="utf-8")
        assert HW_MEM_LINE in src, "硬體共用模組之記憶體讀取行已變（I4e SPEC §C 錨點契約）"
        (r / HW_MODULE_REL).write_text(src.replace(HW_MEM_LINE, f"    return {hw_mem_gib} * (1 << 30)"),
                                       encoding="utf-8")
        hw_rel = "tests/fixtures/hardware_gate_plugin.py"
        (r / hw_rel).write_text((REPO / hw_rel).read_text(encoding="utf-8"), encoding="utf-8")
        hw = {"entries": [{"path": "tests/test_a.py", "ticket": "RM-FULLSCALE", "item": "④", "min_memory_gib": 24,
                           "reason": "全規模記憶體需求"}]}
        (r / "tests" / "hardware_requirements.json").write_text(json.dumps(hw, ensure_ascii=False), encoding="utf-8")
        plugins.append(HW_PLUGIN_MOD)
    (r / "tests" / "conftest.py").write_text(f"pytest_plugins = {plugins!r}\n", encoding="utf-8")
    (r / "pytest.ini").write_text("[pytest]\ntestpaths = tests\nmarkers =\n    slow: 模組內偏慢\n"
                                  "    fullscale: 全規模層\n", encoding="utf-8")
    (r / "tests" / "test_a.py").write_text(A_SRC, encoding="utf-8")
    (r / "tests" / "test_b.py").write_text("def test_other():\n    assert True\n", encoding="utf-8")
    return r


def _pytest(r: Path, *args: str, cache: bool = False) -> subprocess.CompletedProcess:
    base = [sys.executable, "-m", "pytest", "-rA"] + ([] if cache else ["-p", "no:cacheprovider"])
    return subprocess.run(base + list(args), cwd=r, capture_output=True, text=True)


def _passed(p: subprocess.CompletedProcess) -> set:
    return {ln.split(" ", 1)[1].strip() for ln in p.stdout.splitlines() if ln.startswith("PASSED ")}


def _out(p: subprocess.CompletedProcess) -> str:
    return p.stdout + p.stderr


def _defer_lines(p: subprocess.CompletedProcess) -> list:
    return [ln for ln in p.stdout.splitlines() if "延後" in ln and "條" in ln]


# ---------------------------------------------------------------- 預設延後與開關
def test_default_defers_marked_named(tmp_path):
    """無 `--run-fullscale` ⇒ 帶 fullscale 之參數化 2 條 deselect、同檔未標記者照跑；摘要同一行含檔路徑與「延後 2 條」，並提示
    `--run-fullscale`（改壞：不載外掛 ⇒ 紅）。"""
    p = _pytest(_fs_repo(tmp_path), *FILES)
    assert p.returncode == 0 and "2 deselected" in p.stdout, _out(p)
    assert _passed(p) == {FAST, OTHER}, _out(p)
    lines = _defer_lines(p)
    assert len(lines) == 1 and "tests/test_a.py" in lines[0] and "延後 2 條" in lines[0], p.stdout
    assert OPT in p.stdout, p.stdout


def test_plugin_absent_runs_marked(tmp_path):
    """改壞對照：不載外掛 ⇒ 帶標記者照跑（對照上條之延後）。"""
    p = _pytest(_fs_repo(tmp_path, plugin=False), *FILES)
    assert p.returncode == 0 and set(FULL) <= _passed(p), _out(p)


def test_run_fullscale_runs_marked(tmp_path):
    """`--run-fullscale` ⇒ 帶標記者照常執行、無延後摘要。"""
    p = _pytest(_fs_repo(tmp_path), OPT, *FILES)
    assert p.returncode == 0 and _passed(p) == set(FULL) | {FAST, OTHER}, _out(p)
    assert "deselected" not in p.stdout and not _defer_lines(p), p.stdout


def test_marker_filter_with_run_fullscale(tmp_path):
    """`--run-fullscale -m fullscale` 只跑帶標記者；`-m "not fullscale"` 只跑未帶者。"""
    r = _fs_repo(tmp_path)
    p = _pytest(r, OPT, "-m", "fullscale", *FILES)
    assert p.returncode == 0 and _passed(p) == set(FULL), _out(p)
    q = _pytest(r, OPT, "-m", "not fullscale", *FILES)
    assert q.returncode == 0 and _passed(q) == {FAST, OTHER}, _out(q)


def test_handwritten_slow_untouched(tmp_path):
    """既有手寫 `slow`（模組內偏慢；重型守衛與 gate_cmd 依 `-m "not slow"`）不受影響：`-m "not slow"` 仍篩除、`-m slow` 仍選中，
    且不含 fullscale 測試（改壞為延後條件改看 slow ⇒ 紅）。"""
    r = _fs_repo(tmp_path)
    (r / "tests" / "test_s.py").write_text("import pytest\n\n\n@pytest.mark.slow\ndef test_hand():\n    assert True\n",
                                           encoding="utf-8")
    files = FILES + ["tests/test_s.py"]
    p = _pytest(r, OPT, "-m", "not slow", *files)
    assert p.returncode == 0 and _passed(p) == set(FULL) | {FAST, OTHER}, _out(p)
    q = _pytest(r, "-m", "slow", *files)
    assert q.returncode == 0 and _passed(q) == {"tests/test_s.py::test_hand"}, _out(q)


def test_marked_not_collected_no_effect(tmp_path):
    """帶標記之檔未被收集（只指定他檔，或 `-k` 篩掉）⇒ 無 deselect、無延後摘要。"""
    r = _fs_repo(tmp_path)
    p = _pytest(r, "tests/test_b.py")
    assert p.returncode == 0 and _passed(p) == {OTHER} and "deselected" not in p.stdout and not _defer_lines(p), _out(p)
    q = _pytest(r, "-k", "test_fast", *FILES)
    assert q.returncode == 0 and _passed(q) == {FAST} and not _defer_lines(q), _out(q)


def test_collect_only_lists_all(tmp_path):
    """`--collect-only` 不延後：帶標記之 nodeid 照列、無 deselect（改壞為 collect-only 亦延後 ⇒ 紅）。"""
    p = _pytest(_fs_repo(tmp_path), "--collect-only", "-q", *FILES)
    assert p.returncode == 0 and all(n in p.stdout for n in FULL) and "deselected" not in p.stdout, _out(p)


def test_testmon_coexist(tmp_path):
    """testmon 共存：`--run-fullscale` 記錄後改動 test_a、test_b（帶標記之 test_d 未改），`--testmon` 無 `--run-fullscale` ⇒ 只未
    帶標記之改動者執行、改動之帶標記者延後且摘要不列未改之 test_d（延後晚於 testmon；改壞為先於 testmon ⇒ 紅）；再
    `--testmon --testmon-forceselect --run-fullscale -m fullscale` ⇒ 被延後者仍被選中執行（deselect 不被 testmon 誤記為已驗；
    改壞為 skip ⇒ 紅）。"""
    r = _fs_repo(tmp_path)
    (r / "tests" / "test_d.py").write_text("import pytest\n\n\n@pytest.mark.fullscale\ndef test_d():\n    assert True\n",
                                           encoding="utf-8")
    files = FILES + ["tests/test_d.py"]
    p0 = _pytest(r, "--testmon", OPT, *files, cache=True)
    assert p0.returncode == 0 and len(_passed(p0)) == 5, _out(p0)
    (r / "tests" / "test_a.py").write_text(A_SRC.replace("assert True", "assert 1").replace("assert x\n", "assert x == x\n"),
                                           encoding="utf-8")
    (r / "tests" / "test_b.py").write_text("def test_other():\n    assert 1\n", encoding="utf-8")
    p1 = _pytest(r, "--testmon", *files, cache=True)
    assert p1.returncode == 0 and _passed(p1) == {FAST, OTHER}, _out(p1)
    lines = _defer_lines(p1)
    assert len(lines) == 1 and "tests/test_a.py" in lines[0] and "延後 2 條" in lines[0], p1.stdout
    p2 = _pytest(r, "--testmon", "--testmon-forceselect", OPT, "-m", "fullscale", *files, cache=True)
    assert p2.returncode == 0 and _passed(p2) == set(FULL), _out(p2)


def test_hardware_and_fullscale_both_registered(tmp_path):
    """硬體登記整檔 test_a.py（24 GiB）與 fullscale 標記重疊、8 GiB：有無 `--run-fullscale` 皆排除 3 條一次、無錯誤。"""
    r = _fs_repo(tmp_path, hw_mem_gib=8)
    for extra in ([], [OPT]):
        p = _pytest(r, *extra, *FILES)
        assert "INTERNALERROR" not in _out(p) and p.returncode == 0, _out(p)
        assert "3 deselected" in p.stdout and _passed(p) == {OTHER}, _out(p)


# ---------------------------------------------------------------- 正式掛載與遷移
def _ini() -> configparser.SectionProxy:
    cp = configparser.ConfigParser()
    cp.read(REPO / "pytest.ini", encoding="utf-8")
    return cp["pytest"]


def test_conftest_registers_fullscale_plugin():
    """正式 `tests/conftest.py` 之頂層 `pytest_plugins` 字面 list 含本外掛。"""
    tree = ast.parse((REPO / "tests" / "conftest.py").read_text(encoding="utf-8"))
    plugins = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets)]
    assert plugins and PLUGIN_MOD in plugins[-1], plugins


def test_pytest_ini_declares_fullscale():
    """正式 `pytest.ini` 之 markers 宣告 `fullscale`。"""
    names = [ln.split(":", 1)[0].strip() for ln in _ini()["markers"].splitlines() if ln.strip()]
    assert "fullscale" in names, names


def test_pytest_ini_addopts_has_no_markexpr():
    """正式 `pytest.ini` addopts 不含 `-m`（帶 `-m` 使 testmon 停用選取；預設延後由外掛依 `--run-fullscale` 決定）。"""
    toks = _ini().get("addopts", "").split()
    assert not any(t == "-m" or t.startswith("-m=") or (t.startswith("-m") and not t.startswith("--")) for t in toks), toks


def test_d1f57180_fullscale_list_all_marked():
    """d1f57180 `tests/duration_budget_exempt.json` 之 23 條全規模測試，於現行檔皆直接帶 `@pytest.mark.fullscale`（AST 查裝飾器；
    遷移完整、無漏）。"""
    old = subprocess.run(["git", "-C", str(REPO), "show", "d1f57180:tests/duration_budget_exempt.json"],
                         capture_output=True, text=True, check=True).stdout
    nodeids = [e["nodeid"] for e in json.loads(old)["exempt"]]
    assert len(nodeids) == 23

    def marked(fn: ast.AST) -> bool:
        return any(isinstance(d, ast.Attribute) and d.attr == "fullscale" for d in fn.decorator_list)

    missing = []
    for nid in nodeids:
        rel, rest = nid.split("::", 1)
        parts = rest.split("::")
        body = ast.parse((REPO / rel).read_text(encoding="utf-8")).body
        if len(parts) == 2:
            body = next((n.body for n in body if isinstance(n, ast.ClassDef) and n.name == parts[0]), [])
        fn = next((n for n in body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == parts[-1]),
                  None)
        if fn is None or not marked(fn):
            missing.append(nid)
    assert missing == [], missing
