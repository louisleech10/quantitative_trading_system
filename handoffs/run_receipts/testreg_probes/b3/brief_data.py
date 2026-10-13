"""TESTREG 第 3 批 Task 3.1 委員輸入表（唯讀）：Phase 3 範圍逐檔之盤點、記錄器耗時與最近結果、複查訊號。

用法：venv/bin/python handoffs/run_receipts/testreg_probes/b3/brief_data.py <scope.txt> <inventory.json> <review.json> <out.tsv>
- 耗時與結果取 .testreg/summary.json：每 nodeid 取最近一筆（started 最大）之 outcome 與 duration_s；
  檔層「最近耗時合計」＝該檔有紀錄之 nodeid 最近一筆 duration_s 之和（無紀錄 nodeid 不估）。
- 不執行任何測試。
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def main(scope_p: str, inv_p: str, review_p: str, out_p: str) -> None:
    scope = [ln.strip() for ln in Path(scope_p).read_text().splitlines() if ln.strip()]
    inv = {f["path"]: f for f in json.loads(Path(inv_p).read_text())["files"]}
    review = json.loads(Path(review_p).read_text())
    summary = json.loads((REPO / ".testreg/summary.json").read_text())["nodes"]
    per_file = defaultdict(dict)
    for nodeid, recs in summary.items():
        path = nodeid.split("::", 1)[0]
        if not recs:
            continue
        latest = max(recs, key=lambda r: r["started"])
        per_file[path][nodeid] = latest
    rows = []
    for path in scope:
        f = inv.get(path, {})
        recs = per_file.get(path, {})
        outc = Counter(r["outcome"] for r in recs.values())
        dur = sum(r["duration_s"] for r in recs.values())
        sig = review.get(path, {})
        hot = [k for k, v in sorted(sig.items()) if v is True]
        rows.append([
            path,
            str(f.get("tests", "?")),
            str(f.get("lines", "?")),
            "Y" if f.get("real_kline") else "N",
            ",".join(f"{k}={v}" for k, v in sorted(f.get("markers", {}).items())) or "-",
            str(len(recs)),
            ",".join(f"{k}={v}" for k, v in sorted(outc.items())) or "-",
            f"{dur:.1f}" if recs else "unknown",
            ",".join(hot) or "-",
            f.get("first_commit", "?"),
            f.get("last_commit", "?"),
        ])
    head = ["path", "tests", "lines", "real_kline", "markers", "nodes_recorded", "latest_outcomes",
            "latest_dur_sum_s", "review_signals_true", "first_commit", "last_commit"]
    with open(out_p, "w", encoding="utf-8") as fh:
        fh.write("\t".join(head) + "\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    print(f"rows={len(rows)} recorded_files={sum(1 for p in scope if per_file.get(p))} → {out_p}")


if __name__ == "__main__":
    main(*sys.argv[1:5])
