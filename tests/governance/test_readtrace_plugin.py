"""scripts/readtrace_plugin.py：逐 nodeid 記錄讀取之 repo 內檔案、`--trace-select` 只跑所列 nodeid（TEST_SELECTION §5 過渡工具）。"""
from __future__ import annotations

import importlib.util
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
    lines = [json.loads(x) for x in (tmp_path / "rt.jsonl").read_text(encoding="utf-8").splitlines()]
    return {x["nodeid"].split("::")[-1]: x[key] for x in lines if "nodeid" in x}  # 略過收集期讀者表行


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


_CONFTEST_A = '''
from pathlib import Path
(Path(r"{repo}") / "scripts" / "affected_from_trace.py").read_text(encoding="utf-8")  # conftest 載入期讀檔
'''

_MOD_READS = '''
import subprocess
from pathlib import Path
import pytest
REPO = Path(r"{repo}")
_CFG = (REPO / "pytest.ini").read_text(encoding="utf-8")  # 模組頂層（import 期）讀檔
subprocess.run(["/bin/echo", "import-probe"], check=True, capture_output=True, cwd=str(REPO / "scripts"))

@pytest.fixture(scope="module")
def modfx():
    return 1

def test_one(modfx):
    assert modfx == 1

def test_two():
    assert _CFG
'''


def _tree(tmp_path: Path) -> Path:
    """pkg_a/{conftest.py（載入期讀檔）, test_mod_reads.py（頂層讀檔＋子行程）, test_plain.py}、pkg_b/test_other.py。"""
    root = tmp_path / "suite"
    (root / "pkg_a").mkdir(parents=True)
    (root / "pkg_b").mkdir()
    (root / "pkg_a" / "conftest.py").write_text(_CONFTEST_A.format(repo=REPO), encoding="utf-8")
    (root / "pkg_a" / "test_mod_reads.py").write_text(_MOD_READS.format(repo=REPO), encoding="utf-8")
    (root / "pkg_a" / "test_plain.py").write_text("def test_plain():\n    assert True\n", encoding="utf-8")
    (root / "pkg_b" / "test_other.py").write_text("def test_other():\n    assert True\n", encoding="utf-8")
    return root


def _run_tree(tmp_path: Path, *extra: str, collect_out: Path = None) -> subprocess.CompletedProcess:
    env = {"READTRACE_OUT": str(tmp_path / "rt.jsonl"), "PATH": "/usr/bin:/bin"}
    if collect_out is not None:
        env["READTRACE_COLLECT_OUT"] = str(collect_out)
    root = _tree(tmp_path)
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "--import-mode=importlib", "--rootdir", str(root),
                           *extra, str(root)], cwd=REPO, env=env, capture_output=True, text=True)


def test_module_import_reads_and_procs_recorded(tmp_path: Path) -> None:
    """測試模組頂層（import 期）讀檔與子行程（含 cwd）歸該模組全部 item 之 import_*，不混入執行期 files／procs；同目錄
    他模組不得該模組之 import 讀檔。"""
    proc = _run_tree(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    imp, files = _records(tmp_path, "import_files"), _records(tmp_path, "files")
    procs, cwds = _records(tmp_path, "import_procs"), _records(tmp_path, "import_proc_cwds")
    for name in ("test_one", "test_two"):
        assert imp[name] == ["pytest.ini", "scripts/affected_from_trace.py"]
        assert procs[name] == ["/bin/echo import-probe"]
        assert cwds[name] == [str((REPO / "scripts").resolve())]
        assert files[name] == [] and _records(tmp_path, "procs")[name] == []
    assert "pytest.ini" not in imp["test_plain"] and procs["test_plain"] == []


def test_conftest_load_reads_scoped_to_its_directory(tmp_path: Path) -> None:
    """conftest 載入期讀檔 ⇒ 歸該 conftest 目錄下全部 item（含同目錄未讀檔之模組）；他目錄之 item 不得之。"""
    proc = _run_tree(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    imp = _records(tmp_path, "import_files")
    assert imp["test_plain"] == ["scripts/affected_from_trace.py"]
    assert imp["test_other"] == []
    assert _records(tmp_path, "import_procs")["test_other"] == []


def test_collecting_module_fallback_without_module_frame(tmp_path: Path) -> None:
    """Module 收集期間、堆疊上無測試模組／conftest frame 之讀檔（外部外掛之 pytest_pycollect_makeitem）⇒ 以「收集中
    之模組」歸該模組之 item；他模組不得之。"""
    plug = tmp_path / "plugdir"
    plug.mkdir()
    (plug / "rt_probe_plugin.py").write_text(
        "from pathlib import Path\n\ndef pytest_pycollect_makeitem(collector, name, obj):\n"
        f"    if name == 'test_plain':\n        (Path(r'{REPO}') / 'pytest.ini').read_text(encoding='utf-8')\n",
        encoding="utf-8")
    root = _tree(tmp_path)
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "-p", "rt_probe_plugin", "--import-mode=importlib",
                           "--rootdir", str(root), str(root)], cwd=REPO,
                          env={"READTRACE_OUT": str(tmp_path / "rt.jsonl"), "PATH": "/usr/bin:/bin",
                               "PYTHONPATH": str(plug)}, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    imp = _records(tmp_path, "import_files")
    assert imp["test_plain"] == ["pytest.ini", "scripts/affected_from_trace.py"]
    assert imp["test_other"] == []


def test_collect_only_output_format(tmp_path: Path) -> None:
    """READTRACE_COLLECT_OUT ⇒ 只收集（不執行）即寫出每 item 一行 {nodeid, shared, import_files, import_procs,
    import_proc_cwds}；shared 同執行期格式（含 module fixture）；不執行故無追蹤紀錄。"""
    out = tmp_path / "collect.jsonl"
    proc = _run_tree(tmp_path, "--collect-only", collect_out=out)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines()]
    # 末三行＝模組 import 期讀檔表、模組 import 期存取邊表、讀者表
    assert [set(x) for x in lines[-3:]] == [{"mod_own"}, {"mod_access"}, {"readers"}]
    rows = {x["nodeid"].split("::")[-1]: x for x in lines[:-3]}
    assert set(rows) == {"test_one", "test_two", "test_plain", "test_other"}
    for row in rows.values():
        assert set(row) == {"nodeid", "shared", "import_files", "import_procs", "import_proc_cwds", "import_modules",
                            "import_direct_files", "import_direct_procs", "import_direct_proc_cwds"}
    assert any(x.endswith("::modfx") and x.startswith("module:") for x in rows["test_one"]["shared"])
    assert rows["test_two"]["import_files"] == ["pytest.ini", "scripts/affected_from_trace.py"]
    assert rows["test_two"]["import_procs"] == ["/bin/echo import-probe"]
    assert rows["test_other"]["import_files"] == [] and rows["test_plain"]["import_procs"] == []
    assert not (tmp_path / "rt.jsonl").exists()


_LIB = {
    "prod_reader.py": 'from pathlib import Path\n_CFG = (Path(r"{repo}") / "pytest.ini").read_text(encoding="utf-8")\n\n'
                      'class Thing:\n    pass\n\n\ndef cfg():\n    return _CFG\n',
    # 模組層資料（讀檔衍生之常數）：測試只讀常數、不呼叫其函式
    "prod_const.py": 'from pathlib import Path\nTABLE = (Path(r"{repo}") / "scripts" / "fact_keys.json").read_text()\n',
    # 轉手再匯出（r16 CODEX-R16-P1-01／GROK-R16-P1-01）與純 .py 常數模組（CODEX-R16-P1-02）
    "prod_reexport.py": "from prod_const import TABLE\n\n\ndef value():\n    return TABLE\n",
    "prod_limit.py": "LIMIT = 1\n",
    # import 期呼叫他模組函式取資料存成常數（r17 CODEX-R17-P1-01）：b 之常數經 a 之函式取自 a 之 import 期讀檔
    "prod_getter.py": 'from pathlib import Path\nTABLE = (Path(r"{repo}") / "scripts" / "live_doc_registry.json").read_text()'
                      '\n\n\ndef get_table():\n    return TABLE\n',
    "prod_viafunc.py": "from prod_getter import get_table\n\nTABLE = get_table()\n",
    "prod_mid.py": "from prod_reader import Thing\n\n\ndef use():\n    return Thing\n",
    "helper_plain.py": "def h():\n    return 1\n",
    "prod_lazy.py": 'from pathlib import Path\nX = (Path(r"{repo}") / "scripts" / "heavy_commands.json").read_text()\n',
}

_CACHE_MOD = '''
import functools
import subprocess
from pathlib import Path
REPO = Path(r"{repo}")
_C = {{}}
_P = {{}}


def _load():
    if "x" not in _C:
        _C["x"] = (REPO / "pytest.ini").read_text(encoding="utf-8")
    return _C["x"]


@functools.lru_cache(maxsize=None)
def _lru_load():
    return (REPO / "scripts" / "affected_from_trace.py").read_text(encoding="utf-8")


def _proc():
    if "p" not in _P:
        _P["p"] = subprocess.run(["/bin/echo", "cached-proc"], capture_output=True).stdout
    return _P["p"]


def _load_early():
    if "e" not in _C:
        _C["e"] = (REPO / "scripts" / "ledger_durations.py").read_text(encoding="utf-8")
    return _C["e"]


_EARLY = _load_early()  # 收集期即讀並快取


def test_c1():
    _load(); _lru_load(); _proc()


def test_c2():
    _load(); _lru_load(); _proc(); _load_early()


def test_c3():
    assert True


def test_open_code():
    import io
    io.open_code(str(REPO / "pytest.ini")).read()


def test_spec_load():
    import importlib.util
    spec = importlib.util.spec_from_file_location("rt_probe_ld", REPO / "scripts" / "ledger_durations.py")
    spec.loader.exec_module(importlib.util.module_from_spec(spec))


import importlib.util as _ilu  # noqa: E402
import py_compile as _pyc  # noqa: E402
_SRC = str(REPO / "scripts" / "ledger_durations.py")
_PYC = _pyc.compile(_SRC, cfile=_ilu.cache_from_source(_SRC), doraise=True)  # 收集期備妥 .pyc


def test_pyc_read():
    with open(_PYC, "rb") as fh:  # 只讀 .pyc ⇒ 記為其原始碼檔
        fh.read()


# 執行緒（r16 CODEX-R16-P1-03／GROK-R16-P2-01）：第一個測試於主執行緒讀並快取；之後於新執行緒、既有執行緒池命中快取
import pytest  # noqa: E402
_T = {{}}


def _tload():
    if "t" not in _T:
        _T["t"] = (REPO / "scripts" / "governance_families.json").read_text(encoding="utf-8")
    return _T["t"]


def test_t1_main():
    _tload()


def test_t2_new_thread():
    import threading
    th = threading.Thread(target=_tload)
    th.start()
    th.join()


@pytest.fixture(scope="module")
def pool():
    from concurrent.futures import ThreadPoolExecutor
    ex = ThreadPoolExecutor(max_workers=1)
    ex.submit(lambda: None).result()  # worker 於此（前一測試之 setup）即建立
    yield ex
    ex.shutdown()


def test_t3_pool_warm(pool):
    assert pool


def test_t4_existing_pool(pool):
    assert pool.submit(_tload).result()
'''


def _empty_git(tmp_path: Path) -> Path:
    root = tmp_path / "gitroot"
    root.mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _tree2(tmp_path: Path, calls: bool = True, collect_out: Path = None) -> subprocess.CompletedProcess:
    """lib/（產品模組：prod_reader 頂層讀檔、prod_mid 間接引用之、helper_plain、prod_lazy）、t1/test_first（直接 import）、
    t2/test_second（經 prod_mid 間接）、t2/test_unrelated、t4/test_cache（執行期快取與 open_code）、t5（conftest
    fixture）、t6（測試函式內延遲 import prod_lazy，兩檔）。"""
    root = tmp_path / "suite2"
    for d in ("lib", "t1", "t2", "t3", "t4", "t5", "t6", "t7"):
        (root / d).mkdir(parents=True)
    # r16 各 MUTATION：轉手再匯出、getattr、import *、函式內區域別名、兩模組依序 import 後只呼叫 b.value()、常數模組
    t3 = {
        "test_limit_a.py": "from prod_limit import LIMIT\n\n\ndef test_limit_a():\n    assert LIMIT == 1\n",
        "test_limit_b.py": "from prod_limit import LIMIT\n\n\ndef test_limit_b():\n    assert LIMIT == 1\n",
        "test_re_from.py": "from prod_reexport import TABLE\n\n\ndef test_re_from():\n    assert TABLE\n",
        "test_re_getattr.py": "def test_re_getattr():\n    import prod_reexport\n"
                              "    assert getattr(prod_reexport, 'TABLE')\n",
        "test_re_star.py": "from prod_reexport import *  # noqa: F403\n\n\ndef test_re_star():\n"
                           "    assert TABLE  # noqa: F405\n",
        "test_re_local.py": "def test_re_local():\n    import prod_const as local\n    assert local.TABLE\n",
        "test_re_vars.py": "def test_re_vars():\n    import prod_reexport\n    assert vars(prod_reexport)['TABLE']\n",
        "test_value_a.py": "import prod_reexport\n\n\ndef test_value_a():\n    assert prod_reexport.value()\n",
        "test_value_b.py": "import prod_reexport\n\n\ndef test_value_b():\n    assert prod_reexport.value()\n",
        "test_vf_a.py": "from prod_viafunc import TABLE\n\n\ndef test_vf_a():\n    assert TABLE\n",
        "test_vf_b.py": "from prod_viafunc import TABLE\n\n\ndef test_vf_b():\n    assert TABLE\n",
    }
    for name, body in t3.items():
        (root / "t3" / name).write_text(body, encoding="utf-8")
    # 根 conftest 之 hook 每測試呼叫快取讀者（同 testreg_recorder_plugin 之 safe）：非測試依賴，不得記入 calls
    (root / "conftest.py").write_text(
        f"from pathlib import Path\n_M = {{}}\n\n\ndef _meta():\n    if 'm' not in _M:\n"
        f"        _M['m'] = (Path(r'{REPO}') / 'docs' / 'TEST_SELECTION.md').read_text(encoding='utf-8')\n"
        "    return _M['m']\n\n\n_meta()\n\n\ndef pytest_runtest_makereport(item, call):\n    _meta()\n",
        encoding="utf-8")
    # conftest 模組層 dict 快取（同 tests/feature_engineering/conftest.py:_DIGEST_CACHE 之寫法）經 function fixture 取用
    (root / "t7" / "conftest.py").write_text(
        f"import pytest\nfrom pathlib import Path\n_C = {{}}\n\n\ndef _cfg():\n    if 'c' not in _C:\n"
        f"        _C['c'] = (Path(r'{REPO}') / 'docs' / 'TEST_SELECTION.md').read_text(encoding='utf-8')\n"
        "    return _C['c']\n\n\n@pytest.fixture\ndef cfg():\n    return _cfg()\n", encoding="utf-8")
    (root / "t7" / "test_cfx.py").write_text("def test_cfg_first(cfg):\n    assert cfg\n\n\n"
                                             "def test_cfg_second(cfg):\n    assert cfg\n", encoding="utf-8")
    for name in ("a", "b"):
        (root / "t6" / f"test_lazy_{name}.py").write_text(
            f"def test_lazy_{name}():\n    from prod_lazy import X\n    assert X\n", encoding="utf-8")
    # conftest 頂層 import；只有引用 prod_mid 之 fixture 的使用者才得其閉包
    (root / "t5" / "conftest.py").write_text(
        "import pytest\nimport prod_mid\nimport helper_plain\n\n\n@pytest.fixture\ndef cfx():\n    return prod_mid.use()\n"
        "\n\n@pytest.fixture\ndef plainfx():\n    return 1\n\n\n"
        "def pytest_collection_modifyitems(items):  # conftest 收集期 hook 之子行程（非模組本體）\n"
        "    import subprocess\n    subprocess.run(['/bin/echo', 'conftest-hook-probe'], capture_output=True)\n",
        encoding="utf-8")
    (root / "t5" / "test_fx.py").write_text("def test_uses_cfx(cfx):\n    assert cfx\n\n\n"
                                            "def test_uses_plain(plainfx):\n    assert plainfx\n", encoding="utf-8")
    for name, body in _LIB.items():
        (root / "lib" / name).write_text(body.format(repo=REPO), encoding="utf-8")
    (root / "t1" / "test_first.py").write_text("import prod_reader\nimport helper_plain\n\n\ndef test_a():\n"
                                                "    assert prod_reader.Thing and helper_plain.h() == 1\n",
                                                encoding="utf-8")
    (root / "t2" / "test_second.py").write_text(
        "from prod_mid import use\n\n\ndef test_b():\n    assert use()\n\n\n"
        "def test_b2():\n    import prod_reader\n    assert prod_reader.cfg()\n", encoding="utf-8")
    (root / "t2" / "test_const.py").write_text(
        "from prod_const import TABLE\n\n\ndef test_k():\n    assert TABLE\n", encoding="utf-8")
    (root / "t2" / "test_const_attr.py").write_text(
        "import prod_const as pc\n\n\ndef test_k2():\n    assert pc.TABLE\n", encoding="utf-8")
    (root / "t2" / "test_unrelated.py").write_text("def test_u():\n    assert True\n", encoding="utf-8")
    (root / "t4" / "test_cache.py").write_text(_CACHE_MOD.format(repo=REPO), encoding="utf-8")
    env = {"READTRACE_OUT": str(tmp_path / "rt.jsonl"), "PATH": "/usr/bin:/bin", "PYTHONPATH": str(root / "lib"),
           "PYTHONDONTWRITEBYTECODE": "1"}
    if not calls:
        env["READTRACE_CALLS"] = "0"
    extra = []
    if collect_out is not None:
        env["READTRACE_COLLECT_OUT"] = str(collect_out)
        extra = ["--collect-only"]
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-o", "addopts=", "-p", "no:cacheprovider",
                           "-p", "scripts.readtrace_plugin", "--import-mode=importlib", "--rootdir", str(root),
                           *extra, str(root)], cwd=REPO, env=env, capture_output=True, text=True)


def test_import_closure_covers_second_importer(tmp_path: Path) -> None:
    """產品模組頂層讀檔只在第一個 import 者執行；第二個（經他模組間接引用）之測試模組亦須得其 import_files；
    import_modules 列閉包內模組之原始碼；無引用者兩者皆無。"""
    proc = _tree2(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    imp, mods = _records(tmp_path, "import_files"), _records(tmp_path, "import_modules")
    lib = (tmp_path / "suite2" / "lib").resolve()
    assert "pytest.ini" in imp["test_a"] and "pytest.ini" in imp["test_b"]
    assert "pytest.ini" not in imp["test_u"] and mods["test_u"] == []
    assert {str(lib / "prod_reader.py"), str(lib / "helper_plain.py")} <= set(mods["test_a"])
    assert {str(lib / "prod_mid.py"), str(lib / "prod_reader.py")} <= set(mods["test_b"])
    assert str(lib / "helper_plain.py") not in mods["test_b"]
    # conftest fixture：只取該 fixture 實際引用之模組（prod_mid → prod_reader），不取整個 conftest 之閉包
    assert "pytest.ini" in imp["test_uses_cfx"] and str(lib / "prod_mid.py") in mods["test_uses_cfx"]
    assert "pytest.ini" not in imp["test_uses_plain"] and mods["test_uses_plain"] == []
    # conftest 收集期 hook（非模組本體）之子行程 ⇒ 歸該 conftest 目錄下 item
    iprocs = _records(tmp_path, "import_procs")
    assert "/bin/echo conftest-hook-probe" in iprocs["test_uses_plain"]
    assert "/bin/echo conftest-hook-probe" not in iprocs["test_a"]
    # executed_files／accessed_modules／import_direct_files／mod_own／mod_access，及選取工具之執行判定（端到端）
    exe, direct = _records(tmp_path, "executed_files"), _records(tmp_path, "import_direct_files")
    acc = _records(tmp_path, "accessed_modules")
    assert str(lib / "prod_mid.py") in exe["test_b"] and str(lib / "prod_reader.py") not in exe["test_b"]
    assert str(lib / "prod_reader.py") in exe["test_b2"] and str(lib / "prod_mid.py") not in exe["test_u"]
    assert "pytest.ini" in imp["test_a"] and "pytest.ini" not in direct["test_a"]  # 他模組 import 期所做 ⇒ 非直接
    # 動態屬性存取：區域別名與 getattr 於執行期記到被讀模組；只在 import 期讀常數者不在 accessed（由存取邊表承接）
    assert str(lib / "prod_const.py") in acc["test_re_local"] and str(lib / "prod_reexport.py") in acc["test_re_getattr"]
    assert str(lib / "prod_const.py") in acc["test_k2"] and acc["test_u"] == []
    assert str(lib / "prod_const.py") not in exe["test_k"] and str(lib / "prod_const.py") not in acc["test_k"]
    lines = [json.loads(x) for x in (tmp_path / "rt.jsonl").read_text(encoding="utf-8").splitlines()]
    own = [x["mod_own"] for x in lines if "mod_own" in x]
    edges = [x["mod_access"] for x in lines if "mod_access" in x]
    assert len(own) == 2 and len(edges) == 2  # 收集結束與 session 結束各一
    assert own[-1][str(lib / "prod_reader.py")]["files"] == ["pytest.ini"]
    assert "pytest.ini" not in own[-1].get(str(lib / "prod_mid.py"), {"files": []})["files"]  # 只歸最內層模組
    t3 = (tmp_path / "suite2" / "t3").resolve()
    assert str(lib / "prod_const.py") in edges[-1][str(lib / "prod_reexport.py")]  # 再匯出鏈：b 於 import 時讀 a.TABLE
    assert str(lib / "prod_reexport.py") in edges[-1][str(t3 / "test_re_star.py")]  # import * 經 __dict__
    assert str(lib / "prod_limit.py") in edges[-1][str(t3 / "test_limit_b.py")]  # 已 import 後之 from-import 仍記
    spec = importlib.util.spec_from_file_location("aft_rt2", REPO / "scripts" / "affected_from_trace.py")
    aft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aft)
    trace = tmp_path / "rt.jsonl"
    recs = aft.latest_records([trace])
    by = {n.split("::")[-1]: n for n in recs}
    groot = _empty_git(tmp_path)  # 選取工具之腳本掃描範圍（空版控樹：本案無子行程判定，免掃整個 repo 之秒數）
    res = aft.affected(recs, {"pytest.ini"}, groot, readers=aft.reader_tables([trace]),
                       mod_tables=aft.mod_tables([trace]))
    assert res[by["test_b2"]] == f"import-read-exec:pytest.ini←{lib / 'prod_reader.py'}"
    # test_b 只執行 prod_mid，但 prod_mid 於 import 時取 prod_reader 之類別 ⇒ 經存取邊保守選入；不相干者不選
    assert res[by["test_b"]] == f"import-read-exec:pytest.ini←{lib / 'prod_reader.py'}"
    assert by["test_u"] not in res and by["test_uses_plain"] not in res
    res = aft.affected(recs, {"scripts/fact_keys.json"}, groot, mod_tables=aft.mod_tables([trace]))
    want = f"import-read-exec:scripts/fact_keys.json←{lib / 'prod_const.py'}"
    for name in ("test_k", "test_k2", "test_re_from", "test_re_getattr", "test_re_star", "test_re_local",
                 "test_re_vars", "test_value_a", "test_value_b"):
        assert res.get(by[name]) == want, (name, res.get(by[name]))
    assert by["test_u"] not in res and by["test_limit_a"] not in res
    # 純 .py 常數模組自身改動：兩個只讀 LIMIT 之測試皆選
    res = aft.affected(recs, {str(lib / "prod_limit.py")}, groot, mod_tables=aft.mod_tables([trace]))
    for name in ("test_limit_a", "test_limit_b"):
        assert res.get(by[name]) == f"accessed:{lib / 'prod_limit.py'}", (name, res.get(by[name]))
    assert by["test_k"] not in res
    # r17：b 於 import 時呼叫 a.get_table() 存成常數；只讀 b.TABLE 之兩測試於來源 JSON 或 a 之原始碼改動時皆選
    res = aft.affected(recs, {"scripts/live_doc_registry.json"}, groot, mod_tables=aft.mod_tables([trace]))
    for name in ("test_vf_a", "test_vf_b"):
        assert res.get(by[name]) == f"import-read-exec:scripts/live_doc_registry.json←{lib / 'prod_getter.py'}", (
            name, res.get(by[name]))
    assert by["test_u"] not in res and by["test_k"] not in res
    res = aft.affected(recs, {str(lib / "prod_getter.py")}, groot, mod_tables=aft.mod_tables([trace]))
    for name in ("test_vf_a", "test_vf_b"):
        assert res.get(by[name]) == f"accessed:{lib / 'prod_getter.py'}", (name, res.get(by[name]))
    # 測試函式內延遲 import：第一個 import 者執行期讀到（files）；第二個（已 import，無讀檔）由紀錄寫出時之閉包補上
    assert "scripts/heavy_commands.json" in _records(tmp_path)["test_lazy_a"]
    assert "scripts/heavy_commands.json" in imp["test_lazy_b"] and str(lib / "prod_lazy.py") in mods["test_lazy_b"]
    assert "scripts/heavy_commands.json" not in imp["test_u"]


def test_collect_only_forces_lazy_imports(tmp_path: Path) -> None:
    """只收集：測試函式內延遲 import 之專案模組於收集期強制載入，兩個 import 者皆得其 import 期讀檔；收集檔亦帶閉包。"""
    out = tmp_path / "c.jsonl"
    proc = _tree2(tmp_path, collect_out=out)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rows = {json.loads(x)["nodeid"].split("::")[-1]: json.loads(x)
            for x in out.read_text(encoding="utf-8").splitlines() if "nodeid" in json.loads(x)}
    for name in ("test_lazy_a", "test_lazy_b"):
        assert "scripts/heavy_commands.json" in rows[name]["import_files"]
    assert "pytest.ini" in rows["test_b"]["import_files"] and "pytest.ini" not in rows["test_u"]["import_files"]


def test_open_code_and_spec_loaded_sources_recorded(tmp_path: Path) -> None:
    """io.open_code 與以 spec 載入 repo 腳本（原始碼／位元組碼經 io.open_code）之讀取皆記為讀檔。"""
    proc = _tree2(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    files = _records(tmp_path)
    assert files["test_open_code"] == ["pytest.ini"]
    assert "scripts/ledger_durations.py" in files["test_spec_load"]
    assert files["test_pyc_read"] == ["scripts/ledger_durations.py"]


def test_cached_readers_inherited_by_later_callers(tmp_path: Path) -> None:
    """模組層 dict 快取、lru_cache、快取之子行程、收集期即快取者：第一個呼叫者記讀檔與讀者表，後續呼叫者（快取命中、
    自身無讀檔）之 calls 列該讀者；未呼叫者不列。READTRACE_CALLS=0 ⇒ 不記 calls。"""
    proc = _tree2(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    files, calls = _records(tmp_path), _records(tmp_path, "calls")
    readers = _records(tmp_path, "reader_files")
    rprocs = _records(tmp_path, "reader_procs")
    early = [json.loads(x) for x in (tmp_path / "rt.jsonl").read_text(encoding="utf-8").splitlines()
             if "readers" in json.loads(x)]

    def rid(name: str, table: dict) -> str:
        return next(r for r in table if r.endswith(":" + name))

    assert files["test_c2"] == [] and files["test_c1"] == ["pytest.ini", "scripts/affected_from_trace.py"]
    assert readers["test_c1"][rid("_load", readers["test_c1"])] == ["pytest.ini"]
    assert readers["test_c1"][rid("_lru_load", readers["test_c1"])] == ["scripts/affected_from_trace.py"]
    assert rprocs["test_c1"][rid("_proc", rprocs["test_c1"])] == ["/bin/echo cached-proc"]
    early_rid = rid("_load_early", early[0]["readers"])
    assert early[0]["readers"][early_rid]["files"] == ["scripts/ledger_durations.py"]
    for name in ("_load", "_lru_load", "_proc"):
        assert rid(name, readers["test_c1"] if name != "_proc" else rprocs["test_c1"]) in calls["test_c2"]
    assert early_rid in calls["test_c2"]
    assert not any(r.endswith((":_load", ":_lru_load", ":_proc", ":_load_early")) for r in calls["test_c3"])
    # 執行緒：新執行緒與既有執行緒池 worker 中命中快取 ⇒ calls 含讀者（非主執行緒不設入口限制）
    assert files["test_t1_main"] == ["scripts/governance_families.json"]
    for name in ("test_t2_new_thread", "test_t4_existing_pool"):
        assert files[name] == [] and any(r.endswith(":_tload") for r in calls[name]), (name, calls[name])
    assert not any(r.endswith(":_tload") for r in calls["test_t3_pool_warm"])
    # hook（非測試／fixture 呼叫鏈）呼叫之讀者不記：否則每條測試皆繼承
    assert any(r.endswith(":_meta") for r in early[0]["readers"])
    assert not any(r.endswith(":_meta") for c in calls.values() for r in c)
    # conftest 快取經 fixture：第二個測試自身無讀檔，以選取工具端到端判定仍受影響
    assert "docs/TEST_SELECTION.md" in files["test_cfg_first"] and files["test_cfg_second"] == []
    spec = importlib.util.spec_from_file_location("aft_rt", REPO / "scripts" / "affected_from_trace.py")
    aft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aft)
    trace = tmp_path / "rt.jsonl"
    res = aft.affected(aft.latest_records([trace]), {"docs/TEST_SELECTION.md"}, _empty_git(tmp_path),
                       readers=aft.reader_tables([trace]))
    second = next(n for n in res if n.endswith("::test_cfg_second"))
    assert res[second].startswith("cached-read:docs/TEST_SELECTION.md←")
    assert res[second].endswith(("t7/conftest.py:12:cfg", ":_cfg"))  # 讀者＝fixture 或其快取函式
    off = tmp_path / "off"
    off.mkdir()
    proc = _tree2(off, calls=False)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert _records(off, "calls")["test_c2"] == []


def test_trace_select_runs_only_listed(tmp_path: Path) -> None:
    """`--trace-select` ⇒ 只執行所列 nodeid；所列 nodeid 未收集到 ⇒ UsageError（rc 4）不靜默略過。"""
    sel = tmp_path / "sel.txt"
    sel.write_text("test_probe_rt.py::test_reads_nothing\n", encoding="utf-8")
    proc = _run(tmp_path, "--trace-select", str(sel))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert set(_records(tmp_path)) == {"test_reads_nothing"}
    sel.write_text("test_probe_rt.py::test_missing\n", encoding="utf-8")
    assert _run(tmp_path, "--trace-select", str(sel)).returncode == 4
