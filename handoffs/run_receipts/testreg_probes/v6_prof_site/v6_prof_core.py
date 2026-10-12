#!/usr/bin/env python3
"""TESTREG Task 2.4：V-6 最慢項之 cProfile 包裝（docs/TESTREG_SPEC.md Task 2.4「最慢項以 cProfile 單項執行」）。

以 `python v6_prof_core.py <outdir> -- <pytest 參數…>` 執行（由 v6_profile.py profile 呼叫）：
  - 主執行緒：與 `python -m cProfile -o … -m pytest …` 同義（sys.path[0]＝cwd、cProfile 包 pytest.main），完整結束時寫
    `<outdir>/main-<pid>-t0.prof`——收據之前 30 累計熱點只取此檔（＝SPEC 所指之單項 cProfile）。
  - 補充（供判讀，不進收據熱點）：threading.setprofile 使之後新建之執行緒各開一個 cProfile（-t1、-t2…）；
    設環境變數 V6_PROF_DIR 後，Python 子行程（multiprocessing spawn 之 worker）經同目錄 sitecustomize.py 以 tag child 開同一機制。
  - 背景工作 2 小時上限：每 V6_PROF_EVERY 秒（預設 600）由計時執行緒送 SIGUSR1（SA_RESTART，不中斷系統呼叫），
    主執行緒於訊號處理中把各 profiler 之「已結束呼叫」統計寫 `*.partial.prof`（不停用 profiler，不影響累計歸屬）；
    正常結束寫完整檔並刪 partial。被截斷時只剩 partial（仍在執行中之外層呼叫不含其累計）＝誠實邊界，status.json 記 complete。
"""
import atexit
import cProfile
import gc
import json
import marshal
import os
import signal
import sys
import threading
import time

_S = {"profs": [], "lock": threading.Lock(), "stop": threading.Event(), "snaps": 0, "done": False}


def _path(i: int, partial: bool) -> str:
    return os.path.join(_S["dir"], f"{_S['tag']}-{os.getpid()}-t{i}{'.partial' if partial else ''}.prof")


def _write(p: cProfile.Profile, path: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        marshal.dump(p.stats, f)
    os.replace(tmp, path)


def _snapshot(signum=None, frame=None) -> None:
    if _S["done"]:
        return
    gc_on = gc.isenabled()
    gc.disable()  # getstats 期間不跑任何 Python 碼（GC 回呼）⇒ 他執行緒不會於列舉中改動其統計樹
    try:
        with _S["lock"]:
            profs = list(_S["profs"])
        for i, p in enumerate(profs):
            p.snapshot_stats()  # 不 disable：只收已結束之呼叫
            _write(p, _path(i, True))
        _S["snaps"] += 1
    finally:
        if gc_on:
            gc.enable()


def _tick(every: float) -> None:
    while not _S["stop"].wait(every):
        os.kill(os.getpid(), signal.SIGUSR1)


def _thread_boot(frame, event, arg) -> None:
    p = cProfile.Profile()
    with _S["lock"]:
        _S["profs"].append(p)
    p.enable()  # 取代本執行緒之 setprofile 鉤子


def start(outdir: str, tag: str) -> None:
    os.makedirs(outdir, exist_ok=True)
    _S.update(dir=outdir, tag=tag, t0=time.time())
    signal.signal(signal.SIGUSR1, _snapshot)
    signal.siginterrupt(signal.SIGUSR1, False)
    threading.Thread(target=_tick, args=(float(os.environ.get("V6_PROF_EVERY", "600")),), daemon=True).start()
    threading.setprofile(_thread_boot)
    p = cProfile.Profile()
    _S["profs"].append(p)
    p.enable()


def finish() -> None:
    if _S["done"]:
        return
    _S["profs"][0].disable()
    _S["done"] = True
    _S["stop"].set()
    threading.setprofile(None)
    with _S["lock"]:
        profs = list(_S["profs"])
    for i, p in enumerate(profs):
        p.snapshot_stats()
        _write(p, _path(i, False))
        if os.path.exists(_path(i, True)):
            os.remove(_path(i, True))


if __name__ == "__main__":
    out, sep, pyargs = sys.argv[1], sys.argv[2], sys.argv[3:]
    if sep != "--":
        raise SystemExit("用法：v6_prof_core.py <outdir> -- <pytest 參數…>")
    sys.path[0] = os.getcwd()  # 同 python -m 之 sys.path[0]
    import pytest

    status = os.path.join(out, "status.json")
    os.makedirs(out, exist_ok=True)
    with open(status, "w", encoding="utf-8") as f:
        json.dump({"complete": False, "pid": os.getpid(), "started_at": time.time()}, f)
    os.environ["V6_PROF_DIR"] = out  # 之後啟動之 Python 子行程經 sitecustomize 開 profiler
    start(out, "main")
    t0 = time.time()
    rc = None
    try:
        rc = int(pytest.main(pyargs))
    finally:
        finish()
        with open(status, "w", encoding="utf-8") as f:
            json.dump({"complete": rc is not None, "pid": os.getpid(), "rc": rc,
                       "elapsed_s": round(time.time() - t0, 1), "snapshots": _S["snaps"]}, f)
    raise SystemExit(rc)
