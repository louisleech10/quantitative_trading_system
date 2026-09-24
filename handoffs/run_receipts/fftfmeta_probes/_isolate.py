"""FF-TFMETA 直接執行之探針共用隔離（r7 codex P1-01）：須在匯入任何 momentum／helper 之前呼叫。

把 Numba 編譯快取、feature registry、CGSA 工作目錄導向本次之系統 tmp 根，使直接執行（不經 pytest 之根 conftest.py）
亦不寫入 repo 樹（data_cache／原始碼旁 __pycache__）。kline 仍自 repo 唯讀讀取（cwd 不變，相對 kline 路徑照舊可用）。
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile
from pathlib import Path


def isolate(prefix: str = "fftfmeta_probe_") -> Path:
    """建立本次 tmp 根並設定三個環境變數；回傳 tmp 根。已由呼叫端指定之 Numba 快取目錄不覆寫。"""
    root = Path(tempfile.mkdtemp(prefix=prefix))
    os.environ.setdefault("NUMBA_CACHE_DIR", str(Path(tempfile.gettempdir()) / "qts_numba_cache"))
    os.environ["FFACT_FEATURE_REGISTRY_PATH"] = str(root / "registry" / "registry.json")
    os.environ["FFACT_CGSA_WORK_DIR"] = str(root / "cgsa_work")
    # 探針其後之 mkdtemp（每個真實 run 數百 MB）一律落在本根下，程序結束整根刪除
    # （2026-09-24：探針 run 目錄未刪，與測試沙箱合計佔滿磁碟）
    tempfile.tempdir = str(root)
    atexit.register(shutil.rmtree, str(root), True)
    return root
