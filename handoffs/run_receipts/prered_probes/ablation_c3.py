"""PRE-RED Task 2.0：單側欄（C3 候選）逐欄附新版剔除原因；無原因者計 U。

用法：python ablation_c3.py <new_prefix> <classify.json> <out.json>
only_old（新版無）須於新版 dead_reasons 有原因；only_new（舊版無）一律計 U（舊版剔除原因未記錄）。
"""

import json
import sys
from collections import Counter

new_p, cls_p, out_p = sys.argv[1:4]
meta = json.load(open(new_p + ".json"))
cls = json.load(open(cls_p))
dead = meta.get("dead_reasons") or {}
only_old, only_new = cls["classes"]["only_old"], cls["classes"]["only_new"]
c3 = {c: dead[c] for c in only_old if c in dead}
u = [c for c in only_old if c not in dead] + list(only_new)
reason_kind = Counter(str(v).split(":")[0].split("（")[0][:40] for v in c3.values())
json.dump({"summary": {"only_old": len(only_old), "only_new": len(only_new), "C3": len(c3), "U": len(u)},
           "reason_kinds": dict(reason_kind), "U": u, "C3": c3}, open(out_p, "w"), ensure_ascii=False)
print(json.dumps({"summary": {"only_old": len(only_old), "only_new": len(only_new), "C3": len(c3), "U": len(u)},
                  "reason_kinds": dict(reason_kind.most_common(12)), "U_sample": u[:8]}, ensure_ascii=False, indent=1))
