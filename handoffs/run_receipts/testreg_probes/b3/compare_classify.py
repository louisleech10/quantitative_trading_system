"""TESTREG b3 Task 3.1：逐檔比對主委與三家之分類機讀表（唯讀；不寫 catalog）。

每份交件檔內以 fenced block 標記 ```testreg-classify 開頭、``` 結尾；表頭固定為
path, guarantee, oracle, claim, disposition, rewrite_targets, tombstones, evidence, note（tab 分隔）。
多值欄以半形逗號分隔；空值寫 `-`。tombstones 每項 `nodeid:等級:replaced_by1|replaced_by2`（無 replaced_by 寫 `-`）。

用法：venv/bin/python compare_classify.py <scope.txt> <out.tsv> <名稱=交件檔> [<名稱=交件檔> ...]
輸出：每檔一列——各家各欄之值、各比較欄是否一致（agree_<欄>）、缺交件之家；stdout 印彙總計數。
比較欄：guarantee、oracle、claim（集合）、disposition、rewrite_targets、tombstones（集合）。
"""
import re
import sys
from pathlib import Path

HEAD = ["path", "guarantee", "oracle", "claim", "disposition", "rewrite_targets", "tombstones", "evidence", "note"]
SET_COLS = {"guarantee", "oracle", "claim", "rewrite_targets", "tombstones"}
CMP_COLS = ["guarantee", "oracle", "claim", "disposition", "rewrite_targets", "tombstones"]
FENCE = re.compile(r"^```testreg-classify\s*$")


def parse(path: Path) -> dict:
    rows, inside, header_seen = {}, False, False
    for ln in path.read_text(encoding="utf-8").splitlines():
        if not inside:
            inside = bool(FENCE.match(ln))
            continue
        if ln.strip() == "```":
            inside = False
            continue
        if not ln.strip():
            continue
        cells = ln.split("\t")
        if cells[0] == "path":
            if cells != HEAD:
                raise SystemExit(f"{path}: 表頭不符 {cells}")
            header_seen = True
            continue
        if len(cells) != len(HEAD):
            raise SystemExit(f"{path}: 欄數 {len(cells)} ≠ {len(HEAD)}：{ln[:120]}")
        rec = dict(zip(HEAD, cells))
        if rec["path"] in rows:
            raise SystemExit(f"{path}: 重複列 {rec['path']}")
        rows[rec["path"]] = rec
    if not header_seen:
        raise SystemExit(f"{path}: 找不到 testreg-classify 表")
    return rows


def norm(col: str, val: str):
    val = val.strip()
    if col in SET_COLS:
        return frozenset() if val in ("", "-") else frozenset(v.strip() for v in val.split(",") if v.strip())
    return val


def main(scope_p: str, out_p: str, *pairs: str) -> None:
    scope = [ln.strip() for ln in Path(scope_p).read_text().splitlines() if ln.strip()]
    tables = {}
    for p in pairs:
        name, _, fp = p.partition("=")
        tables[name] = parse(Path(fp))
    names = list(tables)
    out_head = ["path", "missing"] + [f"agree_{c}" for c in CMP_COLS]
    for n in names:
        out_head += [f"{n}.{c}" for c in CMP_COLS]
    agree_all = 0
    with open(out_p, "w", encoding="utf-8") as fh:
        fh.write("\t".join(out_head) + "\n")
        for path in scope:
            missing = [n for n in names if path not in tables[n]]
            present = [n for n in names if path in tables[n]]
            flags = []
            for c in CMP_COLS:
                vals = {norm(c, tables[n][path][c]) for n in present}
                flags.append("Y" if len(vals) == 1 and not missing else "N")
            if all(f == "Y" for f in flags):
                agree_all += 1
            row = [path, ",".join(missing) or "-"] + flags
            for n in names:
                rec = tables[n].get(path)
                row += [rec[c] if rec else "MISSING" for c in CMP_COLS]
            fh.write("\t".join(row) + "\n")
    extra = {n: sorted(set(tables[n]) - set(scope)) for n in names}
    print(f"files={len(scope)} all_agree={agree_all} → {out_p}")
    for n, ex in extra.items():
        if ex:
            print(f"{n}: 範圍外列 {len(ex)}：{ex[:5]}")


if __name__ == "__main__":
    main(*sys.argv[1:])
