"""ICHC B4 診斷（臨時，不 commit）：兩次 absent-timestamps run 的逐鍵 diff。"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.momentum.helpers.ichc_run import run_analyze  # noqa: E402

a = run_analyze(config_override={"event_filter": {"enabled": True}})
b = run_analyze(config_override={"event_filter": {"enabled": True}}, event_timestamps=[])


def walk(x, y, path=""):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            walk(x.get(k), y.get(k), f"{path}.{k}")
    elif isinstance(x, list) and isinstance(y, list):
        if len(x) != len(y):
            print(f"LEN {path}: {len(x)} vs {len(y)}")
        else:
            for i, (xi, yi) in enumerate(zip(x, y)):
                walk(xi, yi, f"{path}[{i}]")
    else:
        if x != y and not (
            isinstance(x, float) and isinstance(y, float) and math.isnan(x) and math.isnan(y)
        ):
            print(f"DIFF {path}: {x!r} vs {y!r}")


walk(a, b)
print("done")
