"""pytest 外掛：逐測試（nodeid）記錄執行期間讀取之 repo 內檔案與所啟動之子行程命令（TEST_SELECTION §2 依賴之實測；
TESTSEL 上線前 §5 過渡期挑選受影響測試之依據：讀到本批改動檔、或啟動之 repo 腳本引用改動檔之測試＝受影響）。

用法：`READTRACE_OUT=<輸出.jsonl> venv/bin/python -m pytest -p scripts.readtrace_plugin [--trace-select <nodeid 清單檔>] <測試>`
輸出 JSONL（每行 {"nodeid", "files", "procs", "setup_files", "setup_procs", "shared"}，附加寫入；setup_* 為 setup 階段
〔含 fixture 建立〕之子集，shared 為非 function 範圍 fixture，供選取工具擴散共用 fixture 之依賴；fixture_setup_s 為本測試
觸發建置之非 function 範圍 fixture → 實測建置秒數，供估時計共用 fixture 成本）。`--trace-select` 只執行清單所列 nodeid（未收集到者即 UsageError）。
讀檔：攔截 builtins.open／io.open（pathlib.read_text／read_bytes 經 io.open）；只記讀取模式、只記 repo 內相對路徑。
子行程：PEP 578 audit hook 記 subprocess.Popen／os.system／os.posix_spawn／os.exec／os.spawn 之命令（子行程內讀檔追不到）。
盲區（須另以直接測試覆蓋）：import 之模組（importlib 不經 open）、C 函式庫直接開檔（h5py、pyarrow）。
估時：開跑前以 `scripts/ledger_durations.py` 依 TESTREG ledger 算總時並分快速層／重型（§4）。
"""
import builtins
import io
import json
import os
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
#: 於載入時轉絕對路徑：測試若切換 cwd（os.chdir／monkeypatch.chdir），相對路徑會寫到別處或失敗（2026-11-12 實踩：
#: INTERNALERROR FileNotFoundError 中止整跑）
_OUT = str(Path(os.environ.get("READTRACE_OUT", str(REPO / "runs" / "readtrace.jsonl"))).resolve())
_current = {"nodeid": None, "phase": None, "files": set(), "procs": [], "proc_cwds": [], "setup_files": set(),
            "setup_procs": [], "setup_proc_cwds": [], "fixture_setup_s": {}}
_real_open = builtins.open
_real_io_open = io.open


def _record(file, mode="r"):
    if _current["nodeid"] is None or not isinstance(file, (str, bytes, os.PathLike)):
        return
    if any(flag in str(mode) for flag in ("w", "a", "x", "+")):
        return
    try:
        path = Path(os.fsdecode(file)).resolve()
        rel = path.relative_to(REPO)
    except (ValueError, OSError):
        return
    _current["files"].add(str(rel))
    if _current["phase"] == "setup":
        _current["setup_files"].add(str(rel))


def _open(file, mode="r", *args, **kwargs):
    _record(file, mode)
    return _real_open(file, mode, *args, **kwargs)


def _io_open(file, mode="r", *args, **kwargs):
    _record(file, mode)
    return _real_io_open(file, mode, *args, **kwargs)


builtins.open = _open
io.open = _io_open

#: 子行程啟動之稽核事件（PEP 578）：子行程內之讀檔追不到，故記其命令，供以「被執行之 repo 腳本是否引用改動檔」補判
_SPAWN_EVENTS = ("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.spawn")


def _audit(event, args):
    if _current["nodeid"] is None or event not in _SPAWN_EVENTS:
        return
    try:
        if event == "subprocess.Popen":
            cmd = args[1]
        elif event == "os.system":
            cmd = args[0]
        else:
            cmd = args[1] if len(args) > 1 else args[0]
        if isinstance(cmd, (list, tuple)):
            cmd = " ".join(os.fsdecode(c) if isinstance(c, (bytes, os.PathLike)) else str(c) for c in cmd)
        elif isinstance(cmd, (bytes, os.PathLike)):
            cmd = os.fsdecode(cmd)
        cmd = str(cmd)[:2000]
    except Exception:  # noqa: BLE001 — 稽核 hook 不得使測試失敗
        cmd = f"<unparsed {event}>"
    # 子行程之工作目錄：subprocess.Popen 之稽核參數為 (executable, args, cwd, env)，cwd 為 None ⇒ 沿用當下 cwd；
    # 選取工具以此解析命令列中之相對目錄（如 cwd=scripts 而掃 ../docs）
    try:
        cwd = args[2] if event == "subprocess.Popen" and len(args) > 2 and args[2] is not None else None
        cwd = os.path.abspath(os.fsdecode(cwd)) if cwd is not None else os.getcwd()
    except Exception:  # noqa: BLE001
        cwd = None
    _current["procs"].append(cmd)
    _current["proc_cwds"].append(cwd)
    if _current["phase"] == "setup":
        _current["setup_procs"].append(cmd)
        _current["setup_proc_cwds"].append(cwd)


sys.addaudithook(_audit)


def pytest_addoption(parser):
    parser.addoption("--trace-select", default=None,
                     help="只執行此檔所列 nodeid（每行一個）；未列者 deselect（TEST_SELECTION §4 快速層／重型分流）")


def pytest_collection_modifyitems(config, items):
    path = config.getoption("--trace-select")
    if not path:
        return
    wanted = {line.strip() for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()}
    keep = [it for it in items if it.nodeid in wanted]
    drop = [it for it in items if it.nodeid not in wanted]
    missing = wanted - {it.nodeid for it in items}
    if missing:
        raise pytest.UsageError(f"--trace-select 有 {len(missing)} 個 nodeid 未收集到，例：{sorted(missing)[:3]}")
    if drop:
        config.hook.pytest_deselected(items=drop)
    items[:] = keep


def _shared_fixtures(item) -> list:
    """本測試所用之非 function 範圍 fixture（`<scope>:<定義位置 baseid>::<名稱>`）：此類 fixture 只在第一個使用者之
    setup 建立，其讀檔／子行程只記到該測試；選取工具據此把依賴擴散給共用同一 fixture 之其他測試。"""
    out = set()
    info = getattr(item, "_fixtureinfo", None)
    for name, defs in (getattr(info, "name2fixturedefs", None) or {}).items():
        for fd in defs:
            scope = getattr(fd, "scope", "function")
            scope = scope if isinstance(scope, str) else getattr(scope, "value", str(scope))
            if scope != "function":
                out.add(f"{scope}:{getattr(fd, 'baseid', '')}::{name}")
    return sorted(out)


def _fixture_id(fixturedef) -> str:
    scope = getattr(fixturedef, "scope", "function")
    scope = scope if isinstance(scope, str) else getattr(scope, "value", str(scope))
    return f"{scope}:{getattr(fixturedef, 'baseid', '')}::{fixturedef.argname}"


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    """非 function 範圍 fixture 之實測建置秒數（同 `shared` 之 id 格式），記於觸發建置之測試紀錄 `fixture_setup_s`：
    估時依實測成本、不靠耗時差距（審碼 r5 CODEX-R5-P1-03；docs/TEST_SELECTION.md §6 第 12 項之過渡）。"""
    t0 = time.perf_counter()
    yield
    fid = _fixture_id(fixturedef)
    if _current["nodeid"] is not None and not fid.startswith("function:"):
        _current["fixture_setup_s"][fid] = round(time.perf_counter() - t0, 6)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    _current["phase"] = "setup"
    yield
    _current["phase"] = "call"


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _current.update(nodeid=item.nodeid, phase=None, files=set(), procs=[], proc_cwds=[], setup_files=set(),
                    setup_procs=[], setup_proc_cwds=[], fixture_setup_s={})
    yield
    rec = {"nodeid": item.nodeid, "files": sorted(_current["files"]), "procs": _current["procs"],
           "proc_cwds": _current["proc_cwds"],
           "setup_files": sorted(_current["setup_files"]), "setup_procs": _current["setup_procs"],
           "setup_proc_cwds": _current["setup_proc_cwds"],
           "shared": _shared_fixtures(item), "fixture_setup_s": dict(_current["fixture_setup_s"])}
    with _real_open(_OUT, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _current["nodeid"] = None
