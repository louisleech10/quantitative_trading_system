"""比較兩版直跑 L3 欄集合：只舊欄須於新版 dead_reasons 有原因，或其上游為低基數（skew／kurt 閘）。
用法：python mtf_l3_diff.py <old.json> <new.json>"""

import json
import re
import sys
from collections import Counter

o, n = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
old, new = set(o["cols"]), set(n["cols"])
dead = n["dead_reasons"]
only_old, only_new = sorted(old - new), sorted(new - old)
explained = [c for c in only_old if c in dead]
rest = [c for c in only_old if c not in dead]
skewkurt = [c for c in rest if re.search(r"_(Skew|Kurt)_W\d+$", c)]
nu = n.get("l1_nunique", {})
up = lambda c: re.sub(r"_(Skew|Kurt)_W\d+$", "", c)  # noqa: E731
lowcard_ok = [c for c in skewkurt if up(c) in nu and nu[up(c)] <= 2]
print(json.dumps({"skew_kurt_upstream_lowcard_le2": len(lowcard_ok), "skew_kurt_unverified": len(skewkurt) - len(lowcard_ok),
                  "only_new_names": only_new}, ensure_ascii=False))
print(json.dumps({"old": len(old), "new": len(new), "only_old": len(only_old), "only_new": len(only_new),
                  "with_dead_reason": len(explained), "reason_kinds": dict(Counter(dead[c].split(":")[0] for c in explained)),
                  "no_reason": len(rest), "no_reason_skew_kurt": len(skewkurt), "no_reason_other_sample": [c for c in rest if c not in skewkurt][:10]},
                 ensure_ascii=False, indent=1))
