"""tests/hermetic 共用：於暫存專案（或指定 cwd）以子行程跑 pytest，取 rc 與輸出（TESTSEL I1a）。

暫存專案不在 repo 之下 ⇒ 不載入 repo 之 tests/conftest.py 與 pytest.ini；外掛以 `-p` 明載，`PYTHONPATH` 指 repo 根
使 `tests.fixtures.*`、`momentum.*` 可匯入。子行程輸出之 data_cache 只會是暫存專案自己的（或測試明給之符號連結）。
"""
from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Sequence

REPO = Path(__file__).resolve().parents[2]
GUARD_PLUGIN = "tests.fixtures.hermetic_guard_plugin"


@dataclass
class RunResult:
    rc: int
    out: str


def run_pytest(
    cwd: Path,
    args: Sequence[str],
    *,
    plugins: Sequence[str] = (GUARD_PLUGIN,),
    env_extra: Optional[Dict[str, str]] = None,
    rootdir: Optional[Path] = None,
) -> RunResult:
    """於 cwd 跑 `python -m pytest -p no:cacheprovider [-p 外掛…] args`；回 rc 與合併輸出。rootdir 預設＝cwd。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env.pop("PYTEST_ADDOPTS", None)
    if env_extra:
        env.update(env_extra)
    root = Path(rootdir) if rootdir is not None else Path(cwd)
    cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rA",
           "--rootdir", str(root), "--confcutdir", str(root)]
    if (root / "pytest.ini").is_file():
        cmd += ["-c", str(root / "pytest.ini")]
    for p in plugins:
        cmd += ["-p", p]
    cmd += list(args)
    proc = subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, errors="replace")
    return RunResult(proc.returncode, proc.stdout + proc.stderr)


def run_repo_nodeids_in_scratch_cwd(nodeids: Sequence[str], scratch: Path, env_extra: Optional[Dict[str, str]] = None) -> RunResult:
    """以 repo 之 pytest.ini／rootdir 跑 repo 測試，但 cwd＝scratch：產品「相對 cwd 之 data_cache」預設根即落
    `scratch/data_cache`，可觀測而不碰正式資料（TESTSEL I1a 實測：PatternStorage、build_cube、KlineStorageManager
    之預設根皆相對 cwd）。"""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(REPO), env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
    env.pop("PYTEST_ADDOPTS", None)
    if env_extra:
        env.update(env_extra)
    cmd = [sys.executable, "-m", "pytest", "-c", str(REPO / "pytest.ini"), "--rootdir", str(REPO),
           "-p", "no:cacheprovider", "-q", "-rA"]
    cmd += [str(REPO / n) for n in nodeids]
    proc = subprocess.run(cmd, cwd=str(scratch), env=env, capture_output=True, text=True, errors="replace")
    return RunResult(proc.returncode, proc.stdout + proc.stderr)


def files_under(root: Path) -> list[str]:
    """root 下全部檔（相對路徑，排序）；root 不存在 ⇒ 空。"""
    if not root.exists():
        return []
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file())
