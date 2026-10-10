"""PRE-RED Task 2.0（大單元兩段式）：比較兩版逐欄雜湊，產出第二段需存陣列之欄名單，並於第二段後合併分類。

用法：
  python ablation_hash.py plan <new_meta.json> <old_meta.json> <cols_out.txt> <plan_out.json>
      全窗雜湊相同 ⇒ C1-full（嚴格：值與 NaN 皆同）；其餘共同欄＋其 L3 上游 ⇒ 寫入 cols_out（第二段存陣列）。
  python ablation_hash.py merge <plan.json> <subset_classify.json> <merged_out.json>
      合併為與 ablation_classify.py 同格式之 classify.json（供 ablation_c2.py／ablation_c3.py）。
"""

import json
import re
import sys

NAME_RX = re.compile(r"^(?P<up>.+)_(Mean|Std|ZScore|Skew|Kurt|Slope|Min|Max|Range|Rank)_W\d+$")

mode = sys.argv[1]
if mode == "plan":
    nm, om = json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    if nm["ingest_ts"] != om["ingest_ts"] or nm["public_rows"] != om["public_rows"]:
        raise RuntimeError("兩版 ingest 時間戳或公開列位置不等")
    nh, oh = nm["hashes"], om["hashes"]
    common = sorted(set(nh) & set(oh))
    # 尾段雜湊：[fv_full, sha_full_suffix, fv_pub, sha_pub_suffix]；舊版以新版之 fv 計算（PRERED_REF_META）
    full_eq = [c for c in common if nh[c][1] == oh[c][1]]
    mism = [c for c in common if nh[c][1] != oh[c][1]]
    need = set(mism)
    for c in mism + sorted(set(oh) - set(nh)):
        m = NAME_RX.match(c)
        if m and m["up"] in nh:
            need.add(m["up"])
    open(sys.argv[4], "w").write("\n".join(sorted(need)) + "\n")
    plan = {"C1-full-hash": full_eq, "mismatch": mism,
            "only_new": sorted(set(nh) - set(oh)), "only_old": sorted(set(oh) - set(nh))}
    json.dump(plan, open(sys.argv[5], "w"))
    print(json.dumps({k: len(v) for k, v in plan.items()} | {"arrays_needed": len(need)}, ensure_ascii=False))
elif mode == "merge":
    plan, sub = json.load(open(sys.argv[2])), json.load(open(sys.argv[3]))
    sc = sub["classes"]
    mism = set(plan["mismatch"])
    classes = {"C1-full": sorted(set(plan["C1-full-hash"]) | (set(sc["C1-full"]) & mism)),
               "C1-public": sorted(set(sc["C1-public"]) & mism),
               "D": sorted(set(sc["D"]) & mism),
               "only_new": plan["only_new"], "only_old": plan["only_old"]}
    summary = {k: len(v) for k, v in classes.items()}
    json.dump({"summary": summary, "classes": classes, "D_detail": {k: v for k, v in sub["D_detail"].items() if k in mism}},
              open(sys.argv[4], "w"), ensure_ascii=False)
    print(json.dumps(summary, ensure_ascii=False))
