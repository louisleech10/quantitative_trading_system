"""TESTREG Task 4.2 前篩（唯讀）：對 rewrite 檔逐目標算情境綁定 R(t)，並併入輕量實跑之紅／skip／逾時。

用法：venv/bin/python handoffs/run_receipts/testreg_probes/b4/rt_screen.py <rewrite 檔清單> <light-sweep tsv…> > out.tsv
輸出欄：path、target、rt_n（R(t) 符號數）、head_state（green／red／file-skip／timeout／unknown）
- red：目標 nodeid 列於該檔輕量實跑之失敗清單
- file-skip：該檔輕量實跑摘要含 skipped（逐目標是否 skip 須再查）
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))
import testreg as tr  # noqa: E402


def main(argv):
    files = [ln.strip() for ln in Path(argv[0]).read_text(encoding="utf-8").splitlines() if ln.strip()]
    sweep = {}
    for p in argv[1:]:
        for ln in Path(p).read_text(encoding="utf-8").splitlines():
            c = ln.split("\t")
            if len(c) >= 5 and c[0].startswith("tests/"):
                sweep[c[0]] = (c[1], c[3], set(x for x in c[4].split(",") if x and x != "-"))
    ctx = tr.build_context(REPO)
    roots = tuple(ctx.schema["receipts"]["E0"]["production_roots"])
    eng = tr._engine_for(ctx, "HEAD")
    fp_, cp_, _f, _t = tr._collect_patterns(tr._tree(ctx))
    ents = tr._entries(ctx)
    print("path\ttarget\trt_n\thead_state")
    for path in files:
        src = eng.tree.read(path) or ""
        fns = tr._test_functions(src, fp_, cp_)
        e = ents.get(path) or {}
        targets = e.get("rewrite_targets") or [f"{path}::{q}" for q in fns]
        rc, summ, red = sweep.get(path, ("?", "", set()))
        for t in targets:
            q = t.split("::", 1)[1]
            fn = fns.get(q)
            n = len(tr._scenario_symbols(eng, path, q, fn, roots)) if fn is not None else -1
            if rc == "timeout":
                st = "timeout"
            elif t in red:
                st = "red"
            elif "skipped" in summ:
                st = "file-skip"
            elif rc == "0" or rc == "1":
                st = "green"
            else:
                st = "unknown"
            print(f"{path}\t{t}\t{n}\t{st}")


if __name__ == "__main__":
    main(sys.argv[1:])
