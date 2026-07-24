"""治理測試共用:python 直譯器定位(CI 無 venv 相容)。

事故(2026-07-24 P1-5):11 個治理測試檔寫死 `REPO/venv/bin/python`,本機有 venv → 綠,
CI 輕量環境無 venv → `FileNotFoundError` → 79 failed。本機模擬(venv 仍在)掩蓋此問題,
是 gh 登入看真實 CI 才抓到。

修:PYTHON 找不到 venv 就 fallback 到 `sys.executable`(跑 pytest 的直譯器,必存在)。
link_python_env:建臨時 repo 時,有 venv 才 symlink(讓臨時 repo 內腳本用 venv);
  無 venv(CI)則跳過——被測腳本(gate.sh/verify_pretooluse.sh 等)自身有 `venv/bin/python||python3` fallback。
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_VENV_PY = REPO_ROOT / "venv" / "bin" / "python"
# venv 優先(本機);缺則用當前直譯器(CI)。回傳 Path,呼叫端 str() 給 subprocess。
PYTHON: Path = _VENV_PY if _VENV_PY.exists() else Path(sys.executable)


def link_python_env(repo: Path) -> None:
    """臨時 repo 需要 python 環境時呼叫:有 venv 才 symlink;無則跳過(腳本自會 fallback python3)。"""
    src = REPO_ROOT / "venv"
    if src.exists():
        (repo / "venv").symlink_to(src, target_is_directory=True)
