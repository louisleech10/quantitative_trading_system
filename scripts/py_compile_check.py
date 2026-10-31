#!/usr/bin/env python3
"""py_compile 指定檔（語法檢查，不執行）。用法：venv/bin/python scripts/py_compile_check.py <檔>...

重型入口（如 `scripts/icperf_freeze_baseline.py`）之檔名會被 heavy_run_guard 以命令列樣式比對；以 glob 傳入檔名即可。
"""

from __future__ import annotations

import py_compile
import sys


def main(paths: list) -> int:
    for p in paths:
        py_compile.compile(p, doraise=True)
        print("compile_ok", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
