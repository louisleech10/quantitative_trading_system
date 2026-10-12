"""V-6 cProfile 子行程注入（見同目錄 v6_prof_core.py）：只在 V6_PROF_DIR 已設時生效。

父行程（v6_prof_core.py 本身）啟動時尚未設此變數 ⇒ 不經此；其後啟動之 Python 子行程（multiprocessing spawn worker、
resource tracker 等）繼承環境而以 tag child 開 profiler，atexit 寫完整檔；被強制終止者只留定期 partial。
"""
import os

if os.environ.get("V6_PROF_DIR"):
    import atexit

    import v6_prof_core

    v6_prof_core.start(os.environ["V6_PROF_DIR"], "child")
    atexit.register(v6_prof_core.finish)
