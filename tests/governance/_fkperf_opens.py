"""FKPERF 核心開檔與子程序計數（docs/FKPERF_SPEC.md Task 0.2）。

以子程序 python3 啟動：先 `sys.addaudithook` 計 `open` 與子程序事件，再以 `runpy.run_path` 執行核心；
開檔只計 ROOT 之下的路徑（註冊表所在 repo＝ROOT），不計核心腳本檔自身。子程序事件（`subprocess.Popen`、
`os.posix_spawn`、`os.exec`、`os.system`、`os.spawn`、`os.fork`）不論以裸名或絕對路徑啟動皆計——
PATH shim（`_fkperf_spawn`）只攔得到經 PATH 解析之命令（r1 codex P2-05），核心側之「全部子程序數」以本計數為準。
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Sequence, Tuple

SPAWN_EVENTS = ("subprocess.Popen", "os.posix_spawn", "os.exec", "os.system", "os.spawn", "os.fork", "os.forkpty")

_DRIVER = r"""
import json, os, runpy, sys
root, core, out = os.path.realpath(sys.argv[1]), os.path.realpath(sys.argv[2]), sys.argv[3]
spawn_events = set(sys.argv[4].split(","))
hits, spawns = [], []
def hook(event, args):
    if event in spawn_events:
        spawns.append(event)
        return
    if event != "open" or not args or not isinstance(args[0], (str, bytes, os.PathLike)):
        return
    p = args[0]
    p = os.fsdecode(p)
    p = os.path.realpath(p if os.path.isabs(p) else os.path.join(os.getcwd(), p))
    if p != core and (p == root or p.startswith(root + os.sep)):
        hits.append(p)
sys.argv = [core] + sys.argv[5:]
code = 0
sys.addaudithook(hook)
try:
    runpy.run_path(core, run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException as exc:
    code = 99
with open(out, "w", encoding="utf-8") as fh:
    json.dump({"code": code, "hits": hits, "spawns": spawns}, fh)
"""


def _audit(root: Path, args: Sequence[str], core: Path) -> dict:
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "audit.json"
        argv = [sys.executable, "-c", _DRIVER, str(root), str(core), str(out), ",".join(SPAWN_EVENTS), *args]
        r = subprocess.run(argv, cwd=str(root), capture_output=True)
        data = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {"code": r.returncode or 98}
        if r.returncode != 0 or data["code"] != 0:
            raise subprocess.CalledProcessError(data.get("code") or r.returncode, argv, r.stdout, r.stderr)
        return data


def count_opens(root: Path, args: Sequence[str], core: Path) -> Tuple[int, List[str]]:
    """回傳核心於 `args` 下之開檔次數與路徑清單；不計 `core` 腳本檔自身之開檔（runpy 讀原始碼；r5 grok 實測）。
    核心以非零碼 `SystemExit` 或例外結束 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗不得充當不變；r5 三家 P1）。"""
    data = _audit(root, args, core)
    return len(data["hits"]), list(data["hits"])


def count_core_spawns(root: Path, args: Sequence[str], core: Path) -> Tuple[int, List[str]]:
    """回傳核心於 `args` 下啟動之子程序事件數與事件名清單（含絕對路徑啟動；r1 codex P2-05）；rc 契約同 `count_opens`。"""
    data = _audit(root, args, core)
    return len(data["spawns"]), list(data["spawns"])
