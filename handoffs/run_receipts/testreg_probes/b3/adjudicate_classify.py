"""TESTREG b3 Task 3.1：四版分類表（主委＋三家）之機械裁決，產出寫入 catalog 用之最終表（唯讀；不寫 catalog）。

裁決規則（諮詢 r3 定案之收斂法；人工覆寫須於覆寫檔逐列寫理由與碼證，並列入該組 synth）：
- disposition：≥3 版相同即採；否則須有覆寫，缺覆寫 ⇒ rc 1。
- rewrite_targets：最終 disposition=rewrite 時，取各版所列函式層 nodeid 之聯集，扣除覆寫之 drop_targets、加 add_targets；
  最終 keep ⇒ 空。（聯集＝改寫面只增不減；單一家獨列之目標須於 synth 載其碼證，否則以 drop_targets 排除）
- tombstones：≥3 版同列方採；其餘須覆寫（淘汰須有證據等級，不以多數換取）。
- guarantee／oracle／claim：各值得 ≥2 版即採；若無任何值達 2 版 ⇒ 取聯集；覆寫可直接指定。
覆寫檔：tab 分隔，欄＝path、field（disposition|add_targets|drop_targets|tombstones|guarantee|oracle|claim）、value、reason。
用法：venv/bin/python adjudicate_classify.py <scope.txt> <overrides.tsv|-> <out.tsv> <名稱=交件檔> …（至少 4 份）
輸出 out.tsv：path、guarantee、oracle、claim、disposition、rewrite_targets、tombstones、basis（majority|override:<欄>）。
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_classify as cc  # noqa: E402  同目錄之 fail-closed 比對器（解析與逐列驗證共用）

LABEL_COLS = ("guarantee", "oracle", "claim")


def main(scope_p: str, ov_p: str, out_p: str, *pairs: str) -> int:
    scope = [ln.strip() for ln in Path(scope_p).read_text().splitlines() if ln.strip()]
    enums = cc.load_enums()
    errs: list = []
    tables = {}
    for p in pairs:
        name, _, fp = p.partition("=")
        rows = cc.parse(Path(fp), errs)
        if set(rows) != set(scope):
            errs.append(f"{name}: 列集合 ≠ 範圍")
        for path, rec in rows.items():
            if path in scope:
                cc.validate_row(rec, enums, f"{name}:{fp}:{rec['_line']}", errs)
        tables[name] = rows
    if len(tables) < 4:
        errs.append(f"交件數 {len(tables)} < 4")
    ov: dict = collections.defaultdict(dict)
    if ov_p != "-":
        for ln in Path(ov_p).read_text(encoding="utf-8").splitlines():
            if not ln.strip() or ln.startswith("#"):
                continue
            cells = ln.split("\t")
            if len(cells) != 4 or cells[0] not in scope or cells[1] not in (
                    "disposition", "add_targets", "drop_targets", "tombstones", *LABEL_COLS) or not cells[3].strip():
                errs.append(f"覆寫列不合：{ln[:120]}")
                continue
            ov[cells[0]][cells[1]] = cells[2].strip()
    if errs:
        print(f"FAIL: {len(errs)} 個錯誤")
        for e in errs:
            print(f"  {e}")
        return 1
    names = list(tables)
    out_rows, stats = [], collections.Counter()
    for path in scope:
        recs = [tables[n][path] for n in names]
        basis = []
        if "disposition" in ov[path]:
            disp = ov[path]["disposition"]
            basis.append("override:disposition")
        else:
            cnt = collections.Counter(r["disposition"].strip() for r in recs)
            disp, k = cnt.most_common(1)[0]
            if k < 3:
                errs.append(f"{path}: disposition 未達 3 版一致（{dict(cnt)}）且無覆寫")
                continue
        targets: set = set()
        if disp == "rewrite":
            for r in recs:
                targets |= set(cc.split_vals(r["rewrite_targets"]))
            targets -= set(cc.split_vals(ov[path].get("drop_targets", "-")))
            targets |= set(cc.split_vals(ov[path].get("add_targets", "-")))
            if "add_targets" in ov[path] or "drop_targets" in ov[path]:
                basis.append("override:targets")
        if "tombstones" in ov[path]:
            tombs = cc.split_vals(ov[path]["tombstones"])
            basis.append("override:tombstones")
        else:
            cnt = collections.Counter(t for r in recs for t in set(cc.split_vals(r["tombstones"])))
            tombs = sorted(t for t, k in cnt.items() if k >= 3)
            if any(k < 3 for k in cnt.values()):
                errs.append(f"{path}: 有未達 3 版之擬立碑且無覆寫：{sorted(t for t, k in cnt.items() if k < 3)[:3]}")
                continue
        labels = {}
        for col in LABEL_COLS:
            if col in ov[path]:
                labels[col] = cc.split_vals(ov[path][col])
                basis.append(f"override:{col}")
                continue
            cnt = collections.Counter(v for r in recs for v in set(cc.split_vals(r[col])))
            chosen = sorted(v for v, k in cnt.items() if k >= 2) or sorted(cnt)
            labels[col] = chosen
        for col in LABEL_COLS:
            bad = [x for x in labels[col] if x not in enums[col]]
            if bad or not labels[col]:
                errs.append(f"{path}: {col} 裁決值不合 {labels[col]}")
        for t in targets:
            cc.check_nodeid(t, path, f"{path} 裁決目標", errs, must_exist=True)
        stats[disp] += 1
        out_rows.append([path, ",".join(labels["guarantee"]), ",".join(labels["oracle"]), ",".join(labels["claim"]),
                         disp, ",".join(sorted(targets)) or "-", ",".join(sorted(tombs)) or "-",
                         ";".join(basis) or "majority"])
    if errs:
        print(f"FAIL: {len(errs)} 個錯誤（未寫 {out_p}）")
        for e in errs:
            print(f"  {e}")
        return 1
    with open(out_p, "w", encoding="utf-8") as fh:
        fh.write("path\tguarantee\toracle\tclaim\tdisposition\trewrite_targets\ttombstones\tbasis\n")
        for row in out_rows:
            fh.write("\t".join(row) + "\n")
    print(f"PASS: files={len(out_rows)} keep={stats['keep']} rewrite={stats['rewrite']} → {out_p}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
