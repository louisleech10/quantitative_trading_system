"""SPEC v25 D16：測試行程之執行期檔案讀取記錄（受影響閘結果沿用之輸入集合）。

環境變數 `FRAMEPATH_TRACE_DIR` 已設時，`install()` 於本 Python 行程裝 audit hook（`sys.addaudithook`），記錄：
- `open` 事件之讀取路徑（built-in open／io.open_code／os.open；寫入模式不記）；
- `os.listdir`／`os.scandir` 之目錄（glob／os.walk 經 scandir）；
- `subprocess.Popen`：可執行檔非本行程之 Python、或明給之 env 未帶 `FRAMEPATH_TRACE_DIR` ⇒ 標記 untraced
  （該子行程之讀取無從記錄）；
- 行程結束時 `sys.modules` 內各模組之 `__file__`（模組自 .pyc 載入時 .py 本身不經 open）。
啟動即寫 `<dir>/<pid>.json`（complete=false），結束（atexit）覆寫為 complete=true；未正常結束之子行程留 complete=false
⇒ 閘視為不可沿用（偏多跑）。
由 `scripts/framepath_trace_site/sitecustomize.py` 於每個 Python 行程啟動時呼叫（閘把該目錄置於 PYTHONPATH 首位），
故 pytest 本身、multiprocessing worker、測試以 sys.executable 啟動之子行程皆記錄；本模組不改任何測試行為。"""
from __future__ import annotations

import atexit
import json
import os
import sys

TRACE_DIR_ENV = "FRAMEPATH_TRACE_DIR"
_STATE: dict = {}
# 不改測試結果之記錄器（TESTREG SPEC §C：不改 outcome、執行順序、rc）：呼叫堆疊含此檔之事件不記
_IGNORED_CALLERS = ("tests/fixtures/testreg_recorder_plugin.py",)
# 平台探測指令（platform 模組；不讀專案檔）
_IGNORED_PROGS = frozenset({"uname", "file", "sysctl", "sw_vers", "diskutil"})


def _from_ignored_caller() -> bool:
    f = sys._getframe(1)  # 堆疊可能很淺（例：模組頂層之 open），不得假設深度
    while f is not None:
        fn = f.f_code.co_filename.replace(os.sep, "/")
        if fn.endswith(_IGNORED_CALLERS):
            return True
        f = f.f_back
    return False


def _norm(p) -> str | None:
    if isinstance(p, bytes):
        p = os.fsdecode(p)
    if not isinstance(p, str) or not p:
        return None
    return os.path.abspath(p)


def _hook(event: str, args: tuple) -> None:
    st = _STATE
    if not st or st.get("busy"):
        return
    if event not in ("open", "os.listdir", "os.scandir", "subprocess.Popen"):
        return
    st["busy"] = True
    try:
        if _from_ignored_caller():
            return
        if event == "open":
            path, mode = args[0], args[1] if len(args) > 1 else None
            flags = args[2] if len(args) > 2 else 0
            if isinstance(mode, str):
                reading = ("r" in mode) or ("+" in mode)
            else:
                reading = isinstance(flags, int) and (flags & (os.O_WRONLY | os.O_RDWR)) != os.O_WRONLY
            p = _norm(path)
            if p and reading:
                st["files"].add(p)
        elif event in ("os.listdir", "os.scandir"):
            p = _norm(args[0] if args and args[0] is not None else ".")
            if p:
                st["dirs"].add(p)
        elif event == "subprocess.Popen":
            exe, argv, _cwd, env = (list(args) + [None] * 4)[:4]
            prog = exe or (argv[0] if isinstance(argv, (list, tuple)) and argv else argv)
            prog = os.fsdecode(prog) if isinstance(prog, bytes) else str(prog or "")
            is_py = os.path.realpath(prog) == os.path.realpath(sys.executable) or os.path.basename(prog).startswith("python")
            env_ok = env is None or TRACE_DIR_ENV in env or os.fsencode(TRACE_DIR_ENV) in env
            if os.path.basename(prog) in _IGNORED_PROGS:
                pass
            elif not (is_py and env_ok):
                argv_l = [os.fsdecode(a) if isinstance(a, bytes) else str(a) for a in
                          (argv if isinstance(argv, (list, tuple)) else [argv])][:8]
                st["untraced"].append({"prog": prog, "argv": argv_l, "cwd": str(_cwd) if _cwd else None})
    except Exception:  # noqa: BLE001 — 記錄器不得改變測試行為
        st["errors"] = st.get("errors", 0) + 1
    finally:
        st["busy"] = False


def _flush(complete: bool) -> None:
    st = _STATE
    if not st:
        return
    mods = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if isinstance(f, str) and f.endswith(".py"):
            mods.add(os.path.abspath(f))
    payload = {"pid": os.getpid(), "complete": complete, "files": sorted(st["files"] | mods),
               "dirs": sorted(st["dirs"]), "untraced": st["untraced"], "errors": st.get("errors", 0)}
    tmp = os.path.join(st["dir"], f"{os.getpid()}.json.tmp")
    st["busy"] = True
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        os.replace(tmp, os.path.join(st["dir"], f"{os.getpid()}.json"))
    finally:
        st["busy"] = False


def install() -> None:
    d = os.environ.get(TRACE_DIR_ENV, "").strip()
    if not d or _STATE:
        return
    os.makedirs(d, exist_ok=True)
    _STATE.update({"dir": d, "files": set(), "dirs": set(), "untraced": [], "busy": False})
    _flush(False)
    sys.addaudithook(_hook)
    atexit.register(_flush, True)
    # SIGTERM（multiprocessing terminate、記憶體守護被父行程結束）不跑 atexit：僅當目前為預設處理時，改為「先寫完記錄
    # 再以預設處理重新送出同一訊號」——終止語意不變；行程日後自行改設處理者覆蓋本處理（記錄可能未完成 ⇒ 閘偏多跑）
    import signal

    if signal.getsignal(signal.SIGTERM) == signal.SIG_DFL:
        def _on_term(signum, _frame):
            try:
                _flush(True)
            finally:
                signal.signal(signum, signal.SIG_DFL)
                os.kill(os.getpid(), signum)

        try:
            signal.signal(signal.SIGTERM, _on_term)
        except ValueError:  # 非主執行緒
            pass
