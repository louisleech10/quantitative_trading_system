"""SPEC v25 D16：受影響閘之 pytest 呼叫把本目錄置於 PYTHONPATH 首位；FRAMEPATH_TRACE_DIR 已設時裝讀取記錄器。
以檔案路徑載入記錄器模組（不改 sys.path，不影響測試之匯入解析）。"""
import os

if os.environ.get("FRAMEPATH_TRACE_DIR"):
    import importlib.util

    _p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "framepath_trace.py")
    _spec = importlib.util.spec_from_file_location("_framepath_trace", _p)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    _mod.install()
