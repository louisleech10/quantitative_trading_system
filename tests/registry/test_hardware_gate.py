"""TESTSEL I4e 硬體閘驗收（docs/TESTSEL_I4E_SPEC.md Task 1.1／1.2）。

暫存 repo＋子行程 pytest：複製 `scripts/hardware_requirements.py`（唯一實作；以改寫副本之 `machine_memory_bytes` 注入本機記憶體，
生產碼不加測試用旗標；錨點契約見 SPEC §C）與 `tests/fixtures/hardware_gate_plugin.py`，登記 `tests/test_big.py` 需 24 GiB；驗收
收集期具名 deselect、記憶體足夠／相等不排除、登記表缺／空／錯之行為、正式 conftest 註冊與真實 repo 整合，及 framepath 閘委派
唯一實作，及與 testmon 選取共存（外掛於其他選取之後才排除）。改壞對照：不載外掛 ⇒ 登記檔照跑；正式 conftest 移除註冊
⇒ `test_conftest_registers_hardware_gate_plugin` 紅；外掛改 trylast ⇒ `test_testmon_coexist_excludes_only_would_run` 紅。
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
MODULE_REL = "scripts/hardware_requirements.py"
PLUGIN_REL = "tests/fixtures/hardware_gate_plugin.py"
PLUGIN_MOD = "tests.fixtures.hardware_gate_plugin"
MEM_LINE = '    return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))'
BIG = ("tests/test_big.py::test_big_a", "tests/test_big.py::test_big_b")
SMALL = "tests/test_small.py::test_s"
BIG_SRC = "def test_big_a():\n    assert True\n\n\ndef test_big_b():\n    assert True\n"
ENTRY = {"path": "tests/test_big.py", "ticket": "RM-FULLSCALE", "item": "④", "min_memory_gib": 24,
         "reason": "全規模記憶體需求"}


def _load(rel: str, name: str):
    spec = importlib.util.spec_from_file_location(name, str(REPO / rel))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _set_mem(r: Path, mem_gib: int) -> None:
    """暫存 repo 之共用模組副本改寫 `machine_memory_bytes` 為固定值（SPEC §C 錨點契約）。"""
    src = (REPO / MODULE_REL).read_text(encoding="utf-8")
    assert MEM_LINE in src, "共用模組之記憶體讀取行已變（SPEC §C 錨點契約），測試注入錨點須同步"
    (r / MODULE_REL).write_text(src.replace(MEM_LINE, f"    return {mem_gib} * (1 << 30)"), encoding="utf-8")


def _hw_repo(tmp_path: Path, mem_gib: int, *, plugin: bool = True, table: object = "default",
             big_src: str = BIG_SRC) -> Path:
    r = tmp_path / "repo"
    (r / "scripts").mkdir(parents=True)
    (r / "tests" / "fixtures").mkdir(parents=True)
    _set_mem(r, mem_gib)
    (r / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (r / "tests" / "fixtures" / "__init__.py").write_text("", encoding="utf-8")
    (r / PLUGIN_REL).write_text((REPO / PLUGIN_REL).read_text(encoding="utf-8"), encoding="utf-8")
    plugins = f'["{PLUGIN_MOD}"]' if plugin else "[]"
    (r / "tests" / "conftest.py").write_text(f"pytest_plugins = {plugins}\n", encoding="utf-8")
    (r / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (r / "tests" / "test_big.py").write_text(big_src, encoding="utf-8")
    (r / "tests" / "test_small.py").write_text("def test_s():\n    assert True\n", encoding="utf-8")
    if table == "default":
        table = {"entries": [ENTRY]}
    if table is not None:
        text = table if isinstance(table, str) else json.dumps(table, ensure_ascii=False)
        (r / "tests" / "hardware_requirements.json").write_text(text, encoding="utf-8")
    return r


def _pytest(r: Path, *args: str, cache: bool = False) -> subprocess.CompletedProcess:
    """暫存 repo 內子行程 pytest；`cache=True` 保留 cacheprovider（testmon 需之：停用即 INTERNALERROR，i4e_facts r2 補測）。"""
    base = [sys.executable, "-m", "pytest", "-rA"] + ([] if cache else ["-p", "no:cacheprovider"])
    return subprocess.run(base + list(args), cwd=r, capture_output=True, text=True)


def _passed(p: subprocess.CompletedProcess) -> set:
    return {ln.split(" ", 1)[1].strip() for ln in p.stdout.splitlines() if ln.startswith("PASSED ")}


def _out(p: subprocess.CompletedProcess) -> str:
    return p.stdout + p.stderr


# ---------------------------------------------------------------- Task 1.2 收集期排除
def test_enough_memory_not_excluded(tmp_path):
    """注入 32 GiB ⇒ 登記檔照常收集執行，無 deselect。"""
    p = _pytest(_hw_repo(tmp_path, 32))
    assert p.returncode == 0, _out(p)
    assert set(BIG) <= _passed(p) and "deselected" not in p.stdout


def test_equal_memory_not_excluded(tmp_path):
    """本機記憶體恰等於需求（24 GiB）⇒ 不排除（判定為嚴格小於；改壞 `<` 為 `<=` 即紅）。"""
    p = _pytest(_hw_repo(tmp_path, 24))
    assert p.returncode == 0 and set(BIG) <= _passed(p) and "deselected" not in p.stdout, _out(p)


def test_insufficient_memory_excluded_named(tmp_path):
    """注入 8 GiB ⇒ 登記檔 2 條於收集後 deselect；摘要同一行具名列路徑、ticket、item、需求 24、本機 8.0、排除 2 條；
    登記檔測試未執行、其他照跑；未登記檔不出現在摘要。"""
    p = _pytest(_hw_repo(tmp_path, 8))
    assert p.returncode == 0, _out(p)
    assert "2 deselected" in p.stdout
    assert not set(BIG) & _passed(p) and SMALL in _passed(p)
    lines = [ln for ln in p.stdout.splitlines() if "RM-FULLSCALE" in ln]
    assert len(lines) == 1, p.stdout
    ln = lines[0]
    assert all(s in ln for s in ("tests/test_big.py", "④", "24", "8.0", "排除 2 條")), ln
    assert "tests/test_small.py" not in ln


def test_mutation_plugin_absent_runs_blocked(tmp_path):
    """改壞對照：不載外掛、8 GiB ⇒ 登記檔 2 條照跑（對照上條之具名排除）。"""
    p = _pytest(_hw_repo(tmp_path, 8, plugin=False))
    assert p.returncode == 0 and set(BIG) <= _passed(p), _out(p)


def test_registered_file_not_collected_no_summary(tmp_path):
    """登記檔未被收集（只指定 small 檔，或 `-k test_s`）⇒ 不報錯、無 deselect 來自硬體閘、摘要不出現。"""
    r = _hw_repo(tmp_path, 8)
    p = _pytest(r, "tests/test_small.py")
    assert p.returncode == 0 and _passed(p) == {SMALL} and "RM-FULLSCALE" not in p.stdout, _out(p)
    q = _pytest(r, "-k", "test_s")
    assert q.returncode == 0 and SMALL in _passed(q) and "RM-FULLSCALE" not in q.stdout, _out(q)


def test_parametrized_nodeid_excluded_by_file(tmp_path):
    """參數化 nodeid（`file::test[x]`）以檔案部分比對亦排除（改壞為整個 nodeid 比對即紅）；未登記檔照跑。"""
    src = "import pytest\n\n\n@pytest.mark.parametrize('x', [1, 2, 3])\ndef test_big_p(x):\n    assert x\n"
    p = _pytest(_hw_repo(tmp_path, 8, big_src=src))
    assert p.returncode == 0 and "3 deselected" in p.stdout and SMALL in _passed(p), _out(p)


def test_missing_table_excludes_nothing(tmp_path):
    """登記表不存在 ⇒ 不排除（偏多跑之安全方向）。"""
    p = _pytest(_hw_repo(tmp_path, 8, table=None))
    assert p.returncode == 0 and set(BIG) <= _passed(p), _out(p)


def test_empty_table_excludes_nothing(tmp_path):
    """登記表 entries 為空 ⇒ 不排除。"""
    p = _pytest(_hw_repo(tmp_path, 8, table={"entries": []}))
    assert p.returncode == 0 and set(BIG) <= _passed(p) and "deselected" not in p.stdout, _out(p)


@pytest.mark.parametrize("table", ["{not json", {"entries": [dict(ENTRY, ticket="OTHER")]}])
def test_malformed_table_fails_collection(tmp_path, table):
    """登記表格式錯（非 JSON／ticket 不符）⇒ 外掛把 HardwareTableError 轉為 pytest.UsageError：rc=4（USAGE_ERROR）、
    訊息含「硬體閘」與登記表路徑、無 INTERNALERROR、無任何測試執行。"""
    p = _pytest(_hw_repo(tmp_path, 8, table=table))
    out = _out(p)
    assert p.returncode == 4, out
    assert "ERROR: 硬體閘" in out and "tests/hardware_requirements.json" in out and "INTERNALERROR" not in out
    assert not _passed(p)


def test_testmon_coexist_excludes_only_would_run(tmp_path):
    """與 testmon 選取共存（審 r2 CODEX-R2-P2-01）：32 GiB 記錄後改動登記檔 test_big 與未登記檔 test_small，8 GiB 再跑
    `--testmon` ⇒ 只 test_small 執行；改動之登記檔被硬體閘排除；未改動之登記檔 test_bigstable 由 testmon 排除、不列入
    硬體閘摘要（外掛於其他選取之後才排除；改壞為 trylast ⇒ 摘要多列 test_bigstable 即紅）。再以 32 GiB 跑 ⇒ 被硬體
    排除之 test_big 仍待跑而被選中（硬體排除不使 testmon 誤記為已驗）。"""
    table = {"entries": [ENTRY, dict(ENTRY, path="tests/test_bigstable.py", item="⑤")]}
    r = _hw_repo(tmp_path, 32, table=table)
    (r / "tests" / "test_bigstable.py").write_text("def test_h():\n    assert True\n", encoding="utf-8")
    (r / "tests" / "test_stable.py").write_text("def test_st():\n    assert True\n", encoding="utf-8")
    files = ["tests/test_big.py", "tests/test_small.py", "tests/test_stable.py", "tests/test_bigstable.py"]
    p0 = _pytest(r, "--testmon", *files, cache=True)
    assert p0.returncode == 0 and len(_passed(p0)) == 5, _out(p0)
    _set_mem(r, 8)
    (r / "tests" / "test_big.py").write_text(BIG_SRC.replace("assert True", "assert 1"), encoding="utf-8")
    (r / "tests" / "test_small.py").write_text("def test_s():\n    assert 1\n", encoding="utf-8")
    p1 = _pytest(r, "--testmon", *files, cache=True)
    assert p1.returncode == 0 and _passed(p1) == {SMALL} and "4 deselected" in p1.stdout, _out(p1)
    lines = [ln for ln in p1.stdout.splitlines() if "RM-FULLSCALE" in ln]
    assert len(lines) == 1 and "tests/test_big.py" in lines[0] and "排除 2 條" in lines[0], p1.stdout
    _set_mem(r, 32)
    p2 = _pytest(r, "--testmon", *files, cache=True)
    assert p2.returncode == 0 and _passed(p2) == set(BIG), _out(p2)


# ---------------------------------------------------------------- Task 1.1 唯一實作
@pytest.mark.parametrize("bad", [
    {"entries": [ENTRY, ENTRY]},                                  # 路徑重複
    {"entries": [dict(ENTRY, path="tests/test_missing.py")]},    # 路徑不存在
    {"entries": [dict(ENTRY, min_memory_gib=0)]},                # 需求非正整數
])
def test_table_validation_rejects(tmp_path, bad):
    """共用模組驗表：重複路徑／路徑不存在／需求非正整數 ⇒ HardwareTableError。"""
    r = _hw_repo(tmp_path, 8, table=bad)
    hw = _load(MODULE_REL, "_i4e_hw_v")
    with pytest.raises(hw.HardwareTableError):
        hw.load_hardware_requirements(r)


def test_framepath_delegates_single_impl():
    """framepath 閘之讀表與判斷委派唯一實作：結果與共用模組逐值相等，且 framepath 檔內無記憶體讀取之第二份實作。"""
    hw = _load(MODULE_REL, "_i4e_hw")
    fg = _load("scripts/framepath_affected_gate.py", "_i4e_fg")
    entries = hw.load_hardware_requirements(REPO)
    assert fg.load_hardware_requirements(REPO) == entries
    for gib in (8, 24, 64):
        assert fg.hardware_blocked(entries, gib << 30) == hw.hardware_blocked(entries, gib << 30)
    assert "os.sysconf" not in (REPO / "scripts" / "framepath_affected_gate.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------- 正式掛載與真實 repo 整合
def test_conftest_registers_hardware_gate_plugin():
    """正式 `tests/conftest.py` 之頂層 `pytest_plugins` 字面 list 含本外掛（漏一行註冊 ⇒ 一般 pytest 不受保護）。"""
    tree = ast.parse((REPO / "tests" / "conftest.py").read_text(encoding="utf-8"))
    plugins = [ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "pytest_plugins" for t in n.targets)]
    assert plugins and PLUGIN_MOD in plugins[-1], plugins


def test_foreign_rootdir_uses_plugin_repo(tmp_path):
    """rootdir 為另一暫存目錄（無 scripts/ 與登記表）、外掛經 `-p` 自所屬 repo 載入（同 tests/hermetic 以 `-p tests.conftest`
    於暫存根跑子行程之用法）⇒ 共用模組與登記表取自外掛所屬 repo：無 INTERNALERROR；暫存目錄之檔在 repo 外，即使相對路徑
    與登記檔同名亦非登記檔、照常執行（改壞為取 `config.rootpath` ⇒ FileNotFoundError INTERNALERROR 即紅）。"""
    r = _hw_repo(tmp_path, 8)
    scratch = tmp_path / "scratch"
    (scratch / "tests").mkdir(parents=True)
    (scratch / "tests" / "test_big.py").write_text(BIG_SRC, encoding="utf-8")
    (scratch / "tests" / "test_small.py").write_text("def test_s():\n    assert True\n", encoding="utf-8")
    env = dict(os.environ, PYTHONPATH=str(r))
    p = subprocess.run([sys.executable, "-m", "pytest", "-rA", "-p", "no:cacheprovider", "-p", PLUGIN_MOD,
                        "--rootdir", str(scratch), "tests/test_big.py", "tests/test_small.py"],
                       cwd=scratch, capture_output=True, text=True, env=env)
    out = _out(p)
    assert "INTERNALERROR" not in out and p.returncode == 0, out
    assert _passed(p) == set(BIG) | {SMALL} and "deselected" not in p.stdout and "RM-FULLSCALE" not in p.stdout, out


@pytest.mark.parametrize("rootdir", ["tests", ".."])
def test_rootdir_variants_still_exclude(tmp_path, rootdir):
    """比對鍵＝檔案相對外掛所屬 repo 之路徑，不隨 rootdir 而變：`--rootdir tests`（nodeid 成 `test_big.py::…`）與 repo 父目錄
    （nodeid 成 `repo/tests/test_big.py::…`）下 8 GiB 仍排除登記檔 2 條、摘要列 repo 相對路徑（改壞為以 nodeid 檔案部分
    比對 ⇒ 漏排即紅）。"""
    r = _hw_repo(tmp_path, 8)
    p = _pytest(r, "--rootdir", str((r / rootdir).resolve()), "tests/test_big.py", "tests/test_small.py")
    out = _out(p)
    assert "INTERNALERROR" not in out and p.returncode == 0, out
    assert "2 deselected" in p.stdout and not any("test_big" in n for n in _passed(p)), out
    lines = [ln for ln in p.stdout.splitlines() if "RM-FULLSCALE" in ln]
    assert len(lines) == 1 and lines[0].startswith("tests/test_big.py") and "排除 2 條" in lines[0], p.stdout


def test_collect_only_not_excluded(tmp_path):
    """`--collect-only` 不執行測試 ⇒ 硬體閘不排除（8 GiB 下登記檔 nodeid 照列、無 deselect、無摘要），使 nodeid 清單不隨
    本機記憶體而異（改壞為 collect-only 亦排除 ⇒ 紅；施工時 test_mutation_d11_7_inventory_hand_edit_is_red 實測轉紅）。"""
    p = _pytest(_hw_repo(tmp_path, 8), "--collect-only", "-q")
    assert p.returncode == 0 and all(n in p.stdout for n in BIG) and SMALL in p.stdout, _out(p)
    assert "deselected" not in p.stdout and "RM-FULLSCALE" not in p.stdout, _out(p)


def test_real_repo_collect_lists_all_and_run_applies_gate():
    """真實 repo（正式 conftest 全部外掛＋pytest 收集鏈）對一個登記檔：`--collect-only` 照列全部 nodeid、不排除；本機記憶體
    低於其需求時以 `--setup-plan`（收集＋排除、不執行）⇒ 全部 deselect（rc=5）並具名列出。本機達標時不跑此段（無排除可驗），
    只驗收集不排除。"""
    hw = _load(MODULE_REL, "_i4e_hw_r")
    entries = hw.load_hardware_requirements(REPO)
    assert entries, "登記表為空，無可驗之登記檔"
    path = str(entries[0]["path"])
    blocked = path in hw.hardware_blocked(entries, hw.machine_memory_bytes())
    p = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", path],
                       cwd=REPO, capture_output=True, text=True)
    out = _out(p)
    assert "INTERNALERROR" not in out and p.returncode == 0, out  # rc=0 ⇒ 有收集到（全排除時為 5）
    assert "deselected" not in p.stdout and "RM-FULLSCALE" not in p.stdout, out
    if blocked:
        # --setup-plan：走完收集與排除但不執行任何測試或 fixture（外掛若被改壞亦不會在小機器上真跑重型測試）
        q = subprocess.run([sys.executable, "-m", "pytest", "--setup-plan", "-q", "-p", "no:cacheprovider", path],
                           cwd=REPO, capture_output=True, text=True)
        out = _out(q)
        assert "INTERNALERROR" not in out, out
        assert q.returncode == 5 and "deselected" in q.stdout and path in q.stdout and "RM-FULLSCALE" in q.stdout, out
