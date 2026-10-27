"""timeout_scan.scan_text 之耗時分解（b1 審碼 r3：pre-commit 壓力情境 2.0 秒之來源）。"""
import cProfile
import importlib.util
import pstats
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("ts_prof", REPO / "scripts" / "timeout_scan.py")
ts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ts
spec.loader.exec_module(ts)
FILES = ["scripts/ffprod_measure.py", "scripts/framepath_affected_gate.py", "scripts/testreg.py",
         "api/services/ic_analysis_service.py", "momentum/Analysis/ic_filter_orchestrator.py"]
texts = [(f, (REPO / f).read_text(encoding="utf-8")) for f in FILES]
prof = cProfile.Profile()
prof.enable()
for f, t in texts:
    ts.scan_text(f, t)
prof.disable()
pstats.Stats(prof).sort_stats("cumulative").print_stats(12)
