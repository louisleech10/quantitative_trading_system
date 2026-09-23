"""FKPERF 核心開檔計數（docs/FKPERF_SPEC.md Task 0.2）——**空殼，尚未實作**。

以子程序 python3 啟動：先 `sys.addaudithook` 計 `open` 事件，再以 `runpy.run_path` 執行核心；
只計 ROOT 與註冊表所在 repo 之下的路徑。
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple


def count_opens(root: Path, args: Sequence[str], core: Path) -> Tuple[int, List[str]]:
    """回傳核心於 `args` 下之開檔次數與路徑清單；不計 `core` 腳本檔自身之開檔（runpy 讀原始碼；r5 grok 實測）。
    核心以非零碼 `SystemExit` 或例外結束 ⇒ 拋 `subprocess.CalledProcessError`（快速失敗不得充當不變；r5 三家 P1）。"""
    raise NotImplementedError("FKPERF Task 0.2")
