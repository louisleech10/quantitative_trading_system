"""pytest 外掛：逐測試（nodeid）記錄執行期間讀取之 repo 內檔案與所啟動之子行程命令（TEST_SELECTION §2 依賴之實測；
TESTSEL 上線前 §5 過渡期挑選受影響測試之依據：讀到本批改動檔、或啟動之 repo 腳本引用改動檔之測試＝受影響）。

用法：`READTRACE_OUT=<輸出.jsonl> venv/bin/python -m pytest -p scripts.readtrace_plugin [--trace-select <nodeid 清單檔>] <測試>`
輸出 JSONL（每行 {"nodeid", "files", "procs", "setup_files", "setup_procs", "shared", "import_files", "import_procs",
"import_proc_cwds"}，附加寫入；import_* 見下「收集期」；setup_* 為 setup 階段
〔含 fixture 建立〕之子集，shared 為非 function 範圍 fixture，供選取工具擴散共用 fixture 之依賴；fixture_setup_s 為本測試
觸發建置之非 function 範圍 fixture → 實測建置秒數，供估時計共用 fixture 成本）。`--trace-select` 只執行清單所列 nodeid（未收集到者即 UsageError）。
讀檔：PEP 578 audit hook 之 `open` 事件（builtins.open／io.open／pathlib／os.open／io.open_code 皆經此；import 之原始碼
與位元組碼讀取亦然，`__pycache__/*.pyc` 換算回其原始碼檔）；只記讀取模式、只記 repo 內相對路徑。
子行程：同一 audit hook 記 subprocess.Popen／os.system／os.posix_spawn／os.exec／os.spawn 之命令（子行程內讀檔追不到）。
收集期（無 nodeid；自外掛載入至 `pytest_collection_finish`）之讀檔與子行程亦記，依當下呼叫堆疊歸屬：堆疊上有測試
模組之 frame（模組頂層 import、參數化資料、模組內 pytest_generate_tests）⇒ 歸該模組全部 item；有 conftest.py／
`__init__.py` 之 frame（載入期與其收集期 hook）⇒ 歸該檔所在目錄下全部 item；另以「收集中之模組」（Module 收集期間）
兜底。每筆紀錄因此另帶 `import_files`、`import_procs`、`import_proc_cwds`（同模組／目錄之 item 共用，不分先後）。
import 一次性（模組只在第一個 import 者執行）：收集期讀檔另記於堆疊上每個執行中之專案模組（`<module>` frame）；收集結束
時對每個測試模組算 import 閉包（自模組 globals 出發，遞迴走訪所引用之專案模組、及 `__module__` 屬專案之物件所屬
模組，含父套件）；item 所用之外部 fixture（conftest 等）只取該 fixture 程式碼實際引用之模組之閉包（不取整個 conftest：
根 conftest 之閉包含整個 api 套件）。item 之 `import_files` 併入閉包內各模組 import 期間之讀檔與子行程，`import_modules`
＝閉包內各專案模組之原始碼檔（測試模組本身除外；repo 外者記絕對路徑）。
執行期快取（lru_cache、模組層 dict 快取、呼叫端快取等只在第一個呼叫者讀檔）：讀檔／子行程當下堆疊上之專案函式皆記為
「讀者」（`reader_files`／`reader_procs`／`reader_proc_cwds`，id＝`<檔>:<首行>:<函式名>`；收集期者另以 `{"readers": ...}`
行輸出）；執行期以 `sys.setprofile` 記本測試呼叫到之讀者（`calls`、setup 階段 `setup_calls`），lru_cache 命中（不進入
被包函式）以 `cache_info()` 計數差補判；選取工具令呼叫者繼承讀者讀過之全部檔。`READTRACE_CALLS=0` 關閉呼叫記錄（量測用）。
執行判定（呼叫記錄開啟時）：每筆紀錄另帶 `executed_files`（本測試 setup／call／teardown 執行到之 repo .py）與
`accessed_modules`（本測試期間被讀屬性之專案模組：專案模組之類別於模組本體開始執行時〔audit `exec`〕即換成
`_TracingModule`，涵蓋 `from M import X`、`getattr`、`import *`、函式內區域別名；雙底線屬性除 `__dict__`／`__all__` 不記）；
另輸出 `{"mod_own": ...}`（模組本身 import 期讀檔，只歸最內層執行中之模組）、`{"mod_access": ...}`（模組 import 期存取
其他專案模組之資料／類別之邊，追再匯出鏈）表行，收集結束與 session 結束各一。執行緒：其他執行緒之 profile 於外掛載入
時以 threading.setprofile 常駐（含其後建立之執行緒池 worker），測試期間任一執行緒之呼叫與存取一律歸當前測試（寧多選）；
主執行緒之讀者呼叫另須堆疊上有測試／fixture 入口（排除 pytest hook 外掛）。
只收集：`READTRACE_COLLECT_OUT=<檔> venv/bin/python -m pytest --collect-only -q -p scripts.readtrace_plugin` ⇒ 於
`pytest_collection_finish` 寫 JSONL（每行 {"nodeid", "shared", "import_files", "import_procs", "import_proc_cwds",
"import_modules", "import_direct_*"}，其後 mod_own、mod_access、readers 表行；覆寫），供選取工具 `--collect` 補舊追蹤
紀錄缺之 shared 與 import 期依賴。
盲區（須另以直接測試覆蓋）：C 函式庫直接開檔（h5py、pyarrow）；子行程內讀檔；非專案碼（site-packages）之快取；以非
Python 函式呼叫進入之快取（如 C 擴充回呼）。
估時：開跑前以 `scripts/ledger_durations.py` 依 TESTREG ledger 算總時並分快速層／重型（§4）。
"""
import builtins
import dis
import importlib
import importlib.util
import io
import json
import os
import sys
import threading
import time
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
#: 於載入時轉絕對路徑：測試若切換 cwd（os.chdir／monkeypatch.chdir），相對路徑會寫到別處或失敗（2026-11-12 實踩：
#: INTERNALERROR FileNotFoundError 中止整跑）
#: 路徑含 `{pid}` 時代入本行程 pid：分批平行跑時每個 pytest 行程各寫一檔（同檔併寫時長行會被拆成多次寫入而交錯）
_OUT = str(Path(os.environ.get("READTRACE_OUT", str(REPO / "runs" / "readtrace.jsonl"))
                .replace("{pid}", str(os.getpid()))).resolve())
_COLLECT_OUT = os.environ.get("READTRACE_COLLECT_OUT")
_COLLECT_OUT = str(Path(_COLLECT_OUT).resolve()) if _COLLECT_OUT else None
_current = {"nodeid": None, "phase": None, "files": set(), "procs": [], "proc_cwds": [], "setup_files": set(),
            "setup_procs": [], "setup_proc_cwds": [], "fixture_setup_s": {}, "reader_files": {}, "reader_procs": {}}
#: 收集期狀態：active＝尚未 collection_finish；module＝收集中之測試模組（絕對路徑）；files／procs＝歸屬鍵（呼叫堆疊上之
#: 原始碼檔絕對路徑）→ 讀取之 repo 檔／(子行程命令, cwd)；deps＝collection_finish 後 nodeid → import 期依賴
#: mod_files／mod_procs＝專案模組（絕對路徑）→ 其 import 執行期間（`<module>` frame 在堆疊上）之讀檔／子行程
#: mod_own＝專案模組 → 其為最內層執行中模組時之讀檔／子行程（即該模組本身 import 期所做，不含其 import 之子模組所做）；
#: files_inner／procs_inner＝歸屬鍵 → (讀檔或子行程, 最內層執行中之專案模組或空字串)，供區分測試模組／conftest 自身之讀檔
_collect = {"active": True, "module": None, "files": {}, "procs": {}, "deps": {}, "mod_files": {}, "mod_procs": {},
            "mod_own": {}, "files_inner": {}, "procs_inner": {}}
_real_open = builtins.open
_real_io_open = io.open
_KEY_CACHE: dict = {}
#: 歸屬至整個目錄（其下全部 item）之原始碼檔名
_DIR_KEYS = ("conftest.py", "__init__.py")
_SELF = str(Path(__file__).resolve())
#: 專案根（repo；pytest rootdir 於 pytest_load_initial_conftests 加入）：其下 .py 才算專案碼（site-packages、venv 除外）
_ROOTS = [str(REPO) + os.sep]
_PROJ_CACHE: dict = {}
#: id(code) → (code, 讀者 id)；保留 code 參照使 id 不被重用
_CODE_RID: dict = {}
#: 讀過檔或啟動過子行程之專案函式（id(code)）；profile 以此判本測試是否呼叫到讀者
_reader_ids: set = set()
#: 收集期之讀者 → 讀檔／(子行程, cwd)（執行期者記於各測試紀錄之 reader_*）
_readers = {"files": {}, "procs": {}}
_calls: set = set()
_setup_calls: set = set()
_CALLS_ON = os.environ.get("READTRACE_CALLS", "1") != "0"
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
_busy = [False]
#: lru_cache 包裝器：命中時不進入被包函式（profile 看不到），以 cache_info 計數差判呼叫
_lru = {"n": -1, "wrappers": [], "seen": set(), "counts": {}}


def _key_of(filename: str) -> str:
    """frame 之原始碼檔 → 絕對路徑（非 .py 者空字串；快取）。"""
    key = _KEY_CACHE.get(filename)
    if key is None:
        key = ""
        if filename.endswith(".py"):
            try:
                key = str(Path(filename).resolve())
            except (OSError, RuntimeError):
                key = ""
        _KEY_CACHE[filename] = key
    return key


def _proj_file(filename) -> str:
    """專案 .py 原始碼檔 → 絕對路徑；非專案（site-packages、repo 內 venv、本外掛、專案根外、非 .py）⇒ 空字串。"""
    if not isinstance(filename, str):
        return ""
    key = _PROJ_CACHE.get(filename)
    if key is None:
        key = _key_of(filename)
        if key and (key == _SELF or "site-packages" in key or "dist-packages" in key
                    or key.startswith(str(REPO / "venv") + os.sep) or not any(key.startswith(r) for r in _ROOTS)):
            key = ""
        _PROJ_CACHE[filename] = key
    return key


def _rel_or_abs(key: str) -> str:
    try:
        return str(Path(key).relative_to(REPO))
    except ValueError:
        return key


def _rid(code) -> str:
    """專案函式之讀者 id（`<repo 相對或絕對路徑>:<首行>:<函式名>`）；模組本體與非專案碼 ⇒ 空字串。"""
    ent = _CODE_RID.get(id(code))
    if ent is None or ent[0] is not code:
        key = _proj_file(code.co_filename)
        rid = f"{_rel_or_abs(key)}:{code.co_firstlineno}:{code.co_name}" if key and code.co_name != "<module>" else ""
        ent = (code, rid)
        _CODE_RID[id(code)] = ent
    return ent[1]


def _repo_rel(file):
    """讀取對象 → (repo 相對路徑, 絕對路徑)；`__pycache__/*.pyc` 換算回原始碼檔；repo 外 ⇒ None。"""
    try:
        path = Path(os.fsdecode(file)).resolve()
        rel = path.relative_to(REPO)
    except (ValueError, OSError, TypeError):
        return None
    if "__pycache__" in rel.parts:
        try:
            path = Path(importlib.util.source_from_cache(str(path)))
            rel = path.relative_to(REPO)
        except (ValueError, NotImplementedError):
            return None
    return str(rel), str(path)


def _attribute(frame, rel=None, path=None, proc=None) -> None:
    """依呼叫堆疊歸屬一次讀檔（rel）或子行程（proc＝(cmd, cwd)）：收集期歸測試模組／conftest 鍵（_collect files／procs）、
    執行中之專案模組（mod_*）與專案函式（收集期讀者）；執行期歸本測試與堆疊上之專案函式（本測試紀錄之 reader_*）。"""
    collecting = _current["nodeid"] is None
    keys = {_collect["module"]} if collecting and _collect["module"] else set()
    rids = set()
    inner = ""  # 最內層執行中之專案模組（實際做此讀檔之 import）
    while frame is not None:
        code = frame.f_code
        if collecting:
            key = _key_of(code.co_filename)
            if key:
                keys.add(key)
        if code.co_name == "<module>":  # 執行中之專案模組（import 期間；收集期與執行期之延遲 import 皆記）
            key = _proj_file(code.co_filename)
            if key and key != path:
                if proc is None:
                    _collect["mod_files"].setdefault(key, set()).add(rel)
                elif proc not in _collect["mod_procs"].setdefault(key, []):
                    _collect["mod_procs"][key].append(proc)
                if not inner:
                    inner = key
                    own = _collect["mod_own"].setdefault(key, {"files": set(), "procs": []})
                    if proc is None:
                        own["files"].add(rel)
                    elif proc not in own["procs"]:
                        own["procs"].append(proc)
        rid = _rid(code)
        if rid:
            rids.add(rid)
            _reader_ids.add(id(code))
        frame = frame.f_back
    if collecting:
        for key in keys:
            if proc is None:
                if key != path:
                    _collect["files"].setdefault(key, set()).add(rel)
                    _collect["files_inner"].setdefault(key, set()).add((rel, inner))
            else:
                _collect["procs"].setdefault(key, []).append(proc)
                _collect["procs_inner"].setdefault(key, []).append((proc, inner))
        store = _readers
    else:
        if proc is None:
            _current["files"].add(rel)
            if _current["phase"] == "setup":
                _current["setup_files"].add(rel)
        store = {"files": _current["reader_files"], "procs": _current["reader_procs"]}
    for rid in rids:
        if proc is None:
            store["files"].setdefault(rid, set()).add(rel)
        else:
            lst = store["procs"].setdefault(rid, [])
            if proc not in lst:
                lst.append(proc)


def _on_open(args, frame) -> None:
    try:
        path, mode, flags = args
    except (TypeError, ValueError):
        return
    if path is None or isinstance(path, int):
        return
    if isinstance(mode, str):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            return
    elif isinstance(flags, int) and flags & _WRITE_FLAGS:
        return
    r = _repo_rel(path)
    if r is not None:
        _attribute(frame, rel=r[0], path=r[1])


#: 子行程啟動之稽核事件（PEP 578）：子行程內之讀檔追不到，故記其命令，供以「被執行之 repo 腳本是否引用改動檔」補判
_SPAWN_EVENTS = ("subprocess.Popen", "os.system", "os.posix_spawn", "os.exec", "os.spawn")


def _audit(event, args):
    if event == "exec" and _CALLS_ON:  # 模組本體開始執行（import）⇒ 立即換成可記屬性存取之模組類別
        try:
            _on_exec()
        except Exception:  # noqa: BLE001
            pass
        return
    if _busy[0] or (_current["nodeid"] is None and not _collect["active"]):
        return
    if event == "open":  # builtins.open／io.open／os.open／io.open_code（import 之原始碼與 .pyc）
        _busy[0] = True
        try:
            _on_open(args, sys._getframe(1))
        except Exception:  # noqa: BLE001 — 稽核 hook 不得使測試失敗
            pass
        finally:
            _busy[0] = False
        return
    if event not in _SPAWN_EVENTS:
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
    if _current["nodeid"] is not None:
        _current["procs"].append(cmd)
        _current["proc_cwds"].append(cwd)
        if _current["phase"] == "setup":
            _current["setup_procs"].append(cmd)
            _current["setup_proc_cwds"].append(cwd)
    _busy[0] = True
    try:
        _attribute(sys._getframe(1), proc=(cmd, cwd))
    except Exception:  # noqa: BLE001
        pass
    finally:
        _busy[0] = False


#: 模組屬性存取記錄（TracingModule）：開關、本測試被存取屬性之專案模組、模組 import 期存取邊
_ACC_ON = [False]
_accessed: set = set()
_MOD_KEY_BY_ID: dict = {}
#: 匯入端模組（絕對路徑）→ 其 import 期間（模組本體執行中）存取其資料或類別之其他專案模組：再匯出鏈之邊
_mod_access: dict = {}
_MAIN_IDENT = threading.get_ident()


def _acc_key(mod) -> str:
    ent = _MOD_KEY_BY_ID.get(id(mod))
    if ent is None or ent[0] is not mod:
        try:
            f = object.__getattribute__(mod, "__dict__").get("__file__")
        except Exception:  # noqa: BLE001
            f = None
        ent = (mod, _proj_file(f) if isinstance(f, str) else "")
        _MOD_KEY_BY_ID[id(mod)] = ent
    return ent[1]


def _on_access(mod, value, caller) -> None:
    """專案模組之屬性被讀：測試期間（任一執行緒）記入本測試 accessed；值非模組（資料、類別、函式皆是）且存取發生於某
    專案模組之本體執行中（import 期）⇒ 記該模組 → 被存取模組之邊（收集期沿專案 frame 找；執行期只認直接位於模組本體者）。"""
    key = _acc_key(mod)
    if not key:
        return
    collecting = _current["nodeid"] is None
    if not collecting:
        _accessed.add(key)
    if isinstance(value, types.ModuleType):  # 子模組之取用不構成資料依賴（其本身另有存取紀錄）
        return
    # 函式亦記邊（審碼 r17 CODEX-R17-P1-01）：b 於 import 時 `from a import get_table; TABLE = get_table()`，
    # b 之常數取自 a 之 import 期資料；只讀 b.TABLE 之測試須經 b→a 邊選入——寧多選不漏選
    f = caller
    while f is not None:
        code = f.f_code
        k = _proj_file(code.co_filename)
        if not k:
            return
        if code.co_name == "<module>":
            if k != key:
                _mod_access.setdefault(k, set()).add(key)
            return
        if not collecting:
            return
        f = f.f_back


class _TracingModule(types.ModuleType):
    """專案模組之類別（`mod.__class__ = _TracingModule`）：讀屬性時記錄被存取之模組。涵蓋 `M.X`、`from M import X`
    （IMPORT_FROM 經 getattr）、`getattr(M, name)`、`from M import *`（讀 `__all__`／`__dict__`）、函式內區域別名；
    其他雙底線屬性（import 機制、inspect 之 `__file__`、`__spec__` 等）不記。"""
    __slots__ = ()

    def __getattribute__(self, name):
        value = types.ModuleType.__getattribute__(self, name)
        if _ACC_ON[0] and (name[:2] != "__" or name in ("__dict__", "__all__")):
            try:
                _on_access(self, value, sys._getframe(1))
            except Exception:  # noqa: BLE001
                pass
        return value


def _trace_module(mod) -> None:
    if type(mod) is types.ModuleType and _acc_key(mod):
        try:
            mod.__class__ = _TracingModule
        except TypeError:
            pass


_traced_n = [-1]


def _trace_all() -> None:
    """sys.modules 中尚未換類別之專案模組補換（sys.modules 有增才掃）。"""
    if not _CALLS_ON or len(sys.modules) == _traced_n[0]:
        return
    _traced_n[0] = len(sys.modules)
    for mod in list(sys.modules.values()):
        if isinstance(mod, types.ModuleType):
            _trace_module(mod)


def _on_exec() -> None:
    """audit `exec`：importlib 之 `_call_with_frames_removed(exec, code, module.__dict__)`；由其 frame 取被執行之
    globals，再由上一層 `exec_module(self, module)` 取模組物件（未入 sys.modules 之 spec 載入亦可）。"""
    f1 = sys._getframe(2)  # 0=_on_exec、1=_audit、2=_call_with_frames_removed、3=exec_module
    args = f1.f_locals.get("args")
    if not (isinstance(args, tuple) and len(args) >= 2 and isinstance(args[1], dict)):
        return
    f2 = f1.f_back
    glb = args[1]
    mod = f2.f_locals.get("module") if f2 is not None else None
    if not (isinstance(mod, types.ModuleType) and object.__getattribute__(mod, "__dict__") is glb):
        mod = sys.modules.get(glb.get("__name__") or "")
        if not (isinstance(mod, types.ModuleType) and object.__getattribute__(mod, "__dict__") is glb):
            return
    _trace_module(mod)


sys.addaudithook(_audit)


#: 本測試之入口函式（測試函式與其所用 fixture 函式之 id(code)）：只記由入口（直接或間接）呼叫之讀者——pytest hook
#: 外掛（如 tests/fixtures/testreg_recorder_plugin.py:77 `safe` 於 pytest_runtest_makereport 每測試呼叫，其收集期曾
#: 啟動 `git -C <repo> diff`）之呼叫非測試依賴，若記則每條測試皆繼承「掃整個 repo」之子行程 ⇒ 全選
_entry_ids: set = set()
#: 本測試執行到之 code（id 集合＋參照，參照使 id 於本測試內不被重用）→ 紀錄之 executed_files
_exec_ids: set = set()
_exec_codes: list = []


def _profile(frame, event, arg, _ids=_reader_ids, _calls=_calls, _setup=_setup_calls, _entry=_entry_ids,
             _exec=_exec_ids, _codes=_exec_codes):
    """執行期呼叫記錄（主執行緒於測試期間以 sys.setprofile 安裝；其他執行緒以 threading.setprofile 於外掛載入即常駐，
    含之後建立之執行緒池 worker）：測試期間（nodeid 已設）任一執行緒之呼叫皆歸本測試（寧多選）——記執行到之 code
    （executed_files）；進入讀者函式 ⇒ 記入 calls（setup 階段另記 setup_calls）。主執行緒另須堆疊上有本測試之入口
    函式（排除 pytest hook 外掛之呼叫）；非主執行緒無入口可循，不設此限。"""
    if event == "call" and _current["nodeid"] is not None:
        code = frame.f_code
        cid = id(code)
        if cid not in _exec:
            _exec.add(cid)
            _codes.append(code)
        if cid in _ids:
            if threading.get_ident() == _MAIN_IDENT:
                f = frame
                while f is not None and id(f.f_code) not in _entry:
                    f = f.f_back
                if f is None:
                    return
            _calls.add(cid)
            if _current["phase"] == "setup":
                _setup.add(cid)


def _entry_codes(item) -> set:
    out = set()
    for func in [getattr(item, "obj", None)] + [getattr(fd, "func", None) for defs in
                                               (getattr(getattr(item, "_fixtureinfo", None), "name2fixturedefs", None)
                                                or {}).values() for fd in defs]:
        try:
            code = getattr(func, "__code__", None)
        except Exception:  # noqa: BLE001
            code = None
        if isinstance(code, types.CodeType):
            out.add(id(code))
    return out


def _lru_total(wrapper):
    try:
        info = wrapper.cache_info()
        return info.hits + info.misses
    except Exception:  # noqa: BLE001
        return None


def _lru_scan() -> None:
    """登錄專案模組（含其 globals 所引用之未入 sys.modules 者）與其類別中之 lru_cache 包裝器；sys.modules 有增才重掃。"""
    if len(sys.modules) == _lru["n"]:
        return
    _lru["n"] = len(sys.modules)
    mods = [m for m in list(sys.modules.values()) if isinstance(m, types.ModuleType)]
    seen_mods = set()
    while mods:
        mod = mods.pop()
        if id(mod) in seen_mods:
            continue
        seen_mods.add(id(mod))
        try:
            if not _proj_file(mod.__dict__.get("__file__")):
                continue
            values = list(vars(mod).values())
        except Exception:  # noqa: BLE001
            continue
        for v in values:
            cands = [v]
            if isinstance(v, types.ModuleType):
                mods.append(v)
                continue
            if isinstance(v, type):
                try:
                    cands += list(v.__dict__.values())
                except Exception:  # noqa: BLE001
                    pass
            for c in cands:
                if type(c).__name__ == "_lru_cache_wrapper" and id(c) not in _lru["seen"]:
                    code = getattr(getattr(c, "__wrapped__", None), "__code__", None)
                    if code is not None:
                        _lru["seen"].add(id(c))
                        _lru["wrappers"].append((c, code))
                        _lru["counts"][id(c)] = _lru_total(c)


def _lru_check(setup: bool = False) -> None:
    """lru_cache 計數自上次檢查後有變且被包函式為讀者 ⇒ 本測試呼叫過該讀者（含命中）。"""
    _lru_scan()
    for wrapper, code in _lru["wrappers"]:
        total = _lru_total(wrapper)
        prev = _lru["counts"].get(id(wrapper))
        _lru["counts"][id(wrapper)] = total
        if total is not None and prev is not None and total != prev and id(code) in _reader_ids:
            _rid(code)
            _calls.add(id(code))
            if setup:
                _setup_calls.add(id(code))


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config, parser, args):
    """pytest rootdir 亦為專案根（repo 外之測試樹，如以 --rootdir 指定之暫存樹，其模組亦算專案碼）。"""
    root = getattr(early_config, "rootpath", None)
    if root is not None:
        r = str(Path(root).resolve()) + os.sep
        if r not in _ROOTS:
            _ROOTS.append(r)
            _PROJ_CACHE.clear()
            _CODE_RID.clear()
            _MOD_KEY_BY_ID.clear()
            _traced_n[0] = -1
            _trace_all()


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


@pytest.hookimpl(hookwrapper=True)
def pytest_make_collect_report(collector):
    """收集中之模組：Module 收集（含 import 測試模組）期間之讀檔，即使堆疊上無該模組 frame 亦歸之（兜底）。"""
    prev = _collect["module"]
    if isinstance(collector, pytest.Module):
        _collect["module"] = _key_of(str(collector.path)) or None
    try:
        yield
    finally:
        _collect["module"] = prev


def _mod_key(mod) -> str:
    try:
        return _proj_file(mod.__dict__.get("__file__"))
    except Exception:  # noqa: BLE001
        return ""


_EDGES: dict = {}


def _edges(mod) -> list:
    """專案模組之直接引用：globals 中之模組、類別／函式之 `__module__`、其他物件之型別所屬模組、父套件（只留專案模組）。
    產品函式內之延遲 import 不在此列：其 import 期讀檔發生於該函式之堆疊下，由讀者機制繼承。快取以 sys.modules 大小
    為版本（子模組載入後父套件 globals 會多出該子模組）。"""
    ent = _EDGES.get(id(mod))
    if ent is not None and ent[0] is mod and ent[2] == len(sys.modules):
        return ent[1]
    out, seen = [], set()
    try:
        values = list(vars(mod).values())
        name = mod.__dict__.get("__name__") or ""
    except Exception:  # noqa: BLE001
        values, name = [], ""
    cands = []
    for v in values:
        if isinstance(v, types.ModuleType):
            cands.append(v)
            continue
        try:
            mname = v.__module__ if isinstance(v, (type, types.FunctionType)) else type(v).__module__
        except Exception:  # noqa: BLE001
            continue
        if isinstance(mname, str) and mname in sys.modules:
            cands.append(sys.modules[mname])
    parts = name.split(".") if isinstance(name, str) else []
    cands += [sys.modules[".".join(parts[:i])] for i in range(1, len(parts)) if ".".join(parts[:i]) in sys.modules]
    for m in cands:
        if id(m) not in seen and m is not mod and _mod_key(m):
            seen.add(id(m))
            out.append(m)
    _EDGES[id(mod)] = (mod, out, len(sys.modules))
    return out


_CLOSURE: dict = {}


def _closure(mod) -> frozenset:
    """模組之 import 閉包（專案模組之絕對路徑集合，含自身）；快取版本同 `_edges`。"""
    ent = _CLOSURE.get(id(mod))
    if ent is not None and ent[0] is mod and ent[2] == len(sys.modules):
        return ent[1]
    keys, seen, stack = set(), set(), [mod]
    while stack:
        m = stack.pop()
        if id(m) in seen:
            continue
        seen.add(id(m))
        key = _mod_key(m)
        if not key:
            continue
        keys.add(key)
        stack.extend(_edges(m))
    res = frozenset(keys)
    _CLOSURE[id(mod)] = (mod, res, len(sys.modules))
    return res


def _import_names(code, glb: dict) -> list:
    """程式碼（不含巢狀）之 import 敘述 → 絕對模組名（`import a.b`→a.b；`from a import b`→a 與 a.b；相對 import 依
    globals 之 `__package__` 解析）。"""
    out = []
    try:
        ins = list(dis.get_instructions(code))
    except Exception:  # noqa: BLE001
        return out
    pkg = glb.get("__package__") or (glb.get("__name__") or "").rpartition(".")[0]
    for i, inst in enumerate(ins):
        if inst.opname != "IMPORT_NAME":
            continue
        level = ins[i - 2].argval if i >= 2 and ins[i - 2].opname == "LOAD_CONST" else 0
        fromlist = ins[i - 1].argval if i >= 1 and ins[i - 1].opname == "LOAD_CONST" else None
        name = inst.argval or ""
        try:
            base = importlib.util.resolve_name("." * level + name, pkg) if isinstance(level, int) and level > 0 \
                else name
        except (ImportError, ValueError):
            continue
        if base:
            out.append(base)
        for sub in (fromlist or ()):
            if isinstance(sub, str) and sub != "*":
                out.append(f"{base}.{sub}" if base else sub)
    return out


_FUNC_ROOTS: dict = {}


def _func_roots(func) -> list:
    """函式（含其遞迴呼叫之同模組函式與巢狀函式）程式碼所引用之全域名稱 → 其模組（globals 中之模組物件、類別／函式之
    `__module__`、其他物件型別之模組），及其函式內 import 之模組（延遲 import：已 import 者只在第一次讀檔，故須以閉包
    補）。供測試函式與 fixture：conftest 等外部 fixture 只取其實際引用者，不取整個 conftest 之閉包（根 conftest 之閉包
    含整個 api 套件，取整個 ⇒ 任一契約檔改動即全選）。回傳模組物件與模組名（名稱於使用時才解析，未 import 者略過）。"""
    code0 = getattr(func, "__code__", None)
    glb = getattr(func, "__globals__", None)
    if code0 is None or not isinstance(glb, dict):
        return []
    ent = _FUNC_ROOTS.get(id(code0))
    if ent is not None and ent[0] is code0:
        return [sys.modules[x] if isinstance(x, str) else x for x in ent[1] if not isinstance(x, str) or x in sys.modules]
    out, seen, stack = [], set(), [code0]
    while stack:
        code = stack.pop()
        if id(code) in seen:
            continue
        seen.add(id(code))
        stack.extend(c for c in code.co_consts if isinstance(c, types.CodeType))
        out += _import_names(code, glb)
        for name in code.co_names:
            v = glb.get(name)
            if v is None:
                continue
            if isinstance(v, types.ModuleType):
                out.append(v)
                continue
            if isinstance(v, types.FunctionType) and v.__globals__ is glb:
                stack.append(v.__code__)  # 同模組輔助函式：遞迴取其引用
                continue
            try:
                mname = v.__module__ if isinstance(v, (type, types.FunctionType)) else type(v).__module__
            except Exception:  # noqa: BLE001
                continue
            mod = sys.modules.get(mname) if isinstance(mname, str) else None
            if mod is not None and mod.__dict__ is not glb:
                out.append(mod)
    _FUNC_ROOTS[id(code0)] = (code0, out)
    return [sys.modules[x] if isinstance(x, str) else x for x in out if not isinstance(x, str) or x in sys.modules]


def _item_funcs(item) -> list:
    """item 之測試函式與其所用之全部專案 fixture 函式（含同模組者：其函式內延遲 import）。"""
    funcs = [getattr(item, "obj", None)]
    info = getattr(item, "_fixtureinfo", None)
    for defs in (getattr(info, "name2fixturedefs", None) or {}).values():
        for fd in defs:
            func = getattr(fd, "func", None)
            glb = getattr(func, "__globals__", None)
            if isinstance(glb, dict) and _proj_file(glb.get("__file__")):
                funcs.append(func)
    return [f for f in funcs if f is not None]


def _lazy_names(items) -> set:
    """各 item 函式內 import、尚未載入、且頂層套件為專案模組者（只收集時強制載入以取其 import 期讀檔）。"""
    names, tops = set(), {}
    for item in items:
        for func in _item_funcs(item):
            code0 = getattr(func, "__code__", None)
            ent = _FUNC_ROOTS.get(id(code0)) if code0 is not None else None
            for x in (ent[1] if ent else []):
                if not isinstance(x, str) or x in sys.modules:
                    continue
                top = x.split(".", 1)[0]
                if top not in tops:
                    mod = sys.modules.get(top)
                    if mod is not None:
                        tops[top] = bool(_mod_key(mod))
                    else:
                        try:
                            spec = importlib.util.find_spec(top)
                        except (ImportError, ValueError):
                            spec = None
                        tops[top] = bool(spec is not None and _proj_file(getattr(spec, "origin", None)))
                if tops[top]:
                    names.add(x)
    return names


def _deps_of(item, dir_keys, keys) -> dict:
    """item 之 import 期依賴：(1) 鍵＝item 所在模組者、及其所在目錄（含祖先）之 conftest.py／`__init__.py` 者之讀檔與
    子行程；(2) 測試模組之 import 閉包、及測試函式／所用 fixture 實際引用（含函式內 import）之模組之閉包內，各專案模組
    import 期間之讀檔與子行程；import_modules＝閉包內模組之原始碼檔（測試模組本身除外）。"""
    own = _key_of(str(getattr(item, "path", "") or ""))
    dirs = [k for d, k in dir_keys if own.startswith(d)]
    mine = dirs + ([own] if own in keys else [])
    files = set()
    procs = []
    # 直接（只算測試模組本身、所屬 conftest／__init__ 本身、或無專案模組執行中〔hook〕之讀檔；他模組 import 期所做者
    # 歸該模組之 mod_own，由選取工具依 executed_files 判）
    selfish = set(dirs) | {own, ""}
    dfiles, dprocs = set(), []
    for k in mine:
        files |= _collect["files"].get(k, set())
        for pair in _collect["procs"].get(k, []):
            if pair not in procs:
                procs.append(pair)
        dfiles |= {r for r, inner in _collect["files_inner"].get(k, set()) if inner in selfish}
        for pair, inner in _collect["procs_inner"].get(k, []):
            if inner in selfish and pair not in dprocs:
                dprocs.append(pair)
    try:
        module = getattr(item, "module", None)
    except Exception:  # noqa: BLE001
        module = None
    roots = [module] if isinstance(module, types.ModuleType) else []
    for func in _item_funcs(item):
        try:
            roots += _func_roots(func)
        except Exception:  # noqa: BLE001
            continue
    clos = set()
    for root in roots:
        clos |= _closure(root)
    for k in clos:
        files |= _collect["mod_files"].get(k, set())
        for pair in _collect["mod_procs"].get(k, []):
            if pair not in procs:
                procs.append(pair)
    return {"import_files": sorted(files), "import_procs": [c for c, _ in procs],
            "import_proc_cwds": [w for _, w in procs],
            "import_modules": sorted(_rel_or_abs(k) for k in clos if k != own),
            "import_direct_files": sorted(dfiles), "import_direct_procs": [c for c, _ in dprocs],
            "import_direct_proc_cwds": [w for _, w in dprocs]}


def _dir_keys():
    keys = set(_collect["files"]) | set(_collect["procs"])
    return [(os.path.dirname(k) + os.sep, k) for k in keys if os.path.basename(k) in _DIR_KEYS], keys


def _import_deps(session, items) -> dict:
    """nodeid → 收集期依賴（見 `_deps_of`）。"""
    dir_keys, keys = _dir_keys()
    return {item.nodeid: _deps_of(item, dir_keys, keys) for item in items}


def _readers_record(store: dict) -> dict:
    """讀者 → {"files", "procs", "proc_cwds"}（JSON 可序列化）。"""
    out = {}
    for rid in sorted(set(store["files"]) | set(store["procs"])):
        procs = store["procs"].get(rid, [])
        out[rid] = {"files": sorted(store["files"].get(rid, set())), "procs": [c for c, _ in procs],
                    "proc_cwds": [w for _, w in procs]}
    return out


def pytest_collection_finish(session):
    """收集結束：結算每 item 之 import 期依賴、停止收集期記錄；設 READTRACE_COLLECT_OUT 者寫出只收集之 JSONL（末行為收集期
    讀者表）；會執行測試者另把收集期讀者表附加至追蹤輸出。"""
    if getattr(session.config.option, "collectonly", False):
        # 只收集：測試／fixture 函式內延遲 import 之專案模組於收集期尚未載入 ⇒ 強制載入以記其 import 期讀檔（追蹤跑則於
        # 每筆紀錄寫出時重算依賴，屆時已由測試本身載入）
        acc, _ACC_ON[0] = _ACC_ON[0], False
        _import_deps(session, session.items)  # 先建 _FUNC_ROOTS
        names = sorted(_lazy_names(session.items))
        _ACC_ON[0] = acc  # 強制載入期間記其 import 期存取邊
        for name in names:
            _collect["module"] = None
            try:
                importlib.import_module(name)
            except BaseException:  # noqa: BLE001 — 延遲 import 失敗（含 SystemExit、缺選用套件）不影響收集
                pass
    _ACC_ON[0] = False  # 收集期存取邊至此；外掛自身走訪模組不記
    _collect["active"] = False
    _collect["module"] = None
    _collect["deps"] = _import_deps(session, session.items)
    _lru_scan()
    readers = _readers_record(_readers)
    if _COLLECT_OUT:
        with _real_open(_COLLECT_OUT, "w", encoding="utf-8") as handle:
            for item in session.items:
                rec = {"nodeid": item.nodeid, "shared": _shared_fixtures(item), **_collect["deps"][item.nodeid]}
                handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
            handle.write(_tables_lines())
            handle.write(json.dumps({"readers": readers}, ensure_ascii=False) + "\n")
    if not getattr(session.config.option, "collectonly", False):
        with _real_open(_OUT, "a", encoding="utf-8") as handle:
            # 收集期之模組 import 期讀檔表與存取邊表（執行中斷亦已留存；session 結束時另附含執行期延遲 import 之完整表）
            handle.write(_tables_lines())
            if readers:
                handle.write(json.dumps({"readers": readers}, ensure_ascii=False) + "\n")


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
    if _CALLS_ON:
        acc, _ACC_ON[0] = _ACC_ON[0], False  # 外掛自身走訪模組不算測試之存取
        try:
            _lru_check(setup=True)
        finally:
            _ACC_ON[0] = acc
    _current["phase"] = "call"


def _rids(ids) -> list:
    return sorted({_CODE_RID[i][1] for i in ids if i in _CODE_RID and _CODE_RID[i][1]})


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _current.update(nodeid=item.nodeid, phase=None, files=set(), procs=[], proc_cwds=[], setup_files=set(),
                    setup_procs=[], setup_proc_cwds=[], fixture_setup_s={}, reader_files={}, reader_procs={})
    _calls.clear()
    _setup_calls.clear()
    _entry_ids.clear()
    _entry_ids.update(_entry_codes(item))
    _exec_ids.clear()
    del _exec_codes[:]
    _accessed.clear()
    _trace_all()
    # setprofile（不用 settrace：不與 coverage／除錯器之 tracer 衝突、不改變 sys.gettrace() 之觀察值；實測 settrace 只快
    # 約 15%，2026-11-12 微基準 2M 次 Python 呼叫：無記錄 0.213s、setprofile 2.241s、settrace 1.903s）。其他執行緒之
    # profile 於外掛載入時以 threading.setprofile 常駐（見檔末），此處只管主執行緒
    prev = sys.getprofile()
    if _CALLS_ON:
        _ACC_ON[0] = True
        sys.setprofile(_profile)
    try:
        yield
    finally:
        if _CALLS_ON:
            sys.setprofile(prev)
            _ACC_ON[0] = False
    if _CALLS_ON:
        _lru_check()
    readers = _readers_record({"files": _current["reader_files"], "procs": _current["reader_procs"]})
    rec = {"nodeid": item.nodeid, "files": sorted(_current["files"]), "procs": _current["procs"],
           "proc_cwds": _current["proc_cwds"],
           "setup_files": sorted(_current["setup_files"]), "setup_procs": _current["setup_procs"],
           "setup_proc_cwds": _current["setup_proc_cwds"],
           "shared": _shared_fixtures(item), "fixture_setup_s": dict(_current["fixture_setup_s"]),
           **_deps_of(item, *_dir_keys()),  # 寫出時重算：含本測試及先前測試之延遲 import
           "calls": _rids(_calls), "setup_calls": _rids(_setup_calls),
           "reader_files": {r: v["files"] for r, v in readers.items() if v["files"]},
           "reader_procs": {r: v["procs"] for r, v in readers.items() if v["procs"]},
           "reader_proc_cwds": {r: v["proc_cwds"] for r, v in readers.items() if v["procs"]}}
    if _CALLS_ON:  # 呼叫記錄關閉時不帶此二欄 ⇒ 選取工具退回 import 閉包
        rec["executed_files"] = sorted({_rel_or_abs(k) for k in (_proj_file(c.co_filename) for c in _exec_codes) if k})
        rec["accessed_modules"] = sorted(_rel_or_abs(k) for k in _accessed)
    _accessed.clear()
    _exec_ids.clear()
    del _exec_codes[:]
    with _real_open(_OUT, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    _current["nodeid"] = None


def _mod_own_record() -> dict:
    out = {}
    for key, ent in sorted(_collect["mod_own"].items()):
        out[_rel_or_abs(key)] = {"files": sorted(ent["files"]), "procs": [c for c, _ in ent["procs"]],
                                 "proc_cwds": [w for _, w in ent["procs"]]}
    return out


def _tables_lines() -> str:
    """模組本身 import 期讀檔表行與模組 import 期存取邊表行（`{"mod_access": {匯入端: [被存取模組...]}}`）。"""
    access = {_rel_or_abs(k): sorted(_rel_or_abs(v) for v in vs) for k, vs in sorted(_mod_access.items())}
    return (json.dumps({"mod_own": _mod_own_record()}, ensure_ascii=False) + "\n"
            + json.dumps({"mod_access": access}, ensure_ascii=False) + "\n")


def pytest_sessionfinish(session, exitstatus):
    """追蹤跑結束：附加各專案模組本身 import 期讀檔表與存取邊表（含執行期之延遲 import），供選取工具依執行判定。"""
    _ACC_ON[0] = False
    if getattr(session.config.option, "collectonly", False):
        return
    with _real_open(_OUT, "a", encoding="utf-8") as handle:
        handle.write(_tables_lines())


if _CALLS_ON:
    # 其他執行緒之呼叫記錄常駐（之後建立之執行緒、含 session 期間建立之執行緒池 worker 皆帶；_profile 只在測試期間記）
    threading.setprofile(_profile)
    _trace_all()
    _ACC_ON[0] = True  # 收集期：記模組 import 期存取邊
