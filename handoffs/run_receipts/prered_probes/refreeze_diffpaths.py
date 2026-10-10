"""列出兩份 baseline 之同一單元投影中不相等之 JSON 路徑。用法：python refreeze_diffpaths.py <A> <B> <SYM/TF>"""

import json
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from refreeze_compare import projection  # noqa: E402


def walk(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            yield from walk(a.get(k), b.get(k), f"{path}.{k}")
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            yield from walk(x, y, f"{path}[{i}]")
    elif a != b:
        yield path, str(a)[:60], str(b)[:60]


A, B = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
sym, tf = sys.argv[3].split("/")
diffs = list(walk(projection(A["single_tf"][sym][tf]), projection(B["single_tf"][sym][tf])))
print(len(diffs))
for d in diffs[:30]:
    print(d)
