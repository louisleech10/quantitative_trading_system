"""生成記憶體之獨立守護行程（docs/ICFIRSTALIGN_SPEC.md v27 Task 4.2「執行中守護（獨立行程）」與「子行程（預算域）」）。

以檔案路徑執行（`python <本檔> --pid <域根行程> --run-dir <域目錄> --run-id <lease key> --budget <bytes>`），
**只用標準函式庫與 ctypes**，不 import `momentum`、pandas、numpy、psutil（避免載入套件 `__init__`）。
每 0.5 秒讀：核心壓力等級、換頁卷剩餘空間、域成員之實測 footprint 合計——成員＝根＋遞迴子行程
（ctypes 呼叫 libproc `proc_listchildpids`；逐 pid `proc_pid_rusage`；以 (pid, 行程啟動時間) 去重，
守護自身與 resource tracker 已在其中、不另加）。只以實測判定，不以承諾量判終止。
第一段：壓力危急、或換頁卷剩餘 < 磁碟保留量、或全樹 footprint > 上限 ⇒ 於域目錄寫停止旗標。
第二段：旗標寫下後同一條件連續 2 次仍成立 ⇒ 寫 `memory_guard_abort.json`（各 pid 讀數）後，
依序對本域生成子行程、再對根行程 SIGKILL。收到停止訊號或根行程不存在 ⇒ 結束。
"""

from __future__ import annotations

import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    """守護主迴圈。Task 4.2。"""
    raise NotImplementedError("ICFIRSTALIGN Task 4.2")


if __name__ == "__main__":
    sys.exit(main())
