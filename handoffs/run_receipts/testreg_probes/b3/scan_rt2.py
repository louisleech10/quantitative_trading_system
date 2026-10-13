"""掃 catalog 全部 rewrite entry 之目標：R(t) 為空者（試作 _prod_symbols；以 HEAD 樹）。cwd＝含試作 testreg.py 之樹。"""
import sys
sys.path.insert(0, ".")
import scripts.testreg as tr
ctx = tr.build_context(tr.Path(".").resolve()) if hasattr(tr, "Path") else tr.build_context(__import__("pathlib").Path(".").resolve())
roots = tuple(ctx.schema["receipts"]["E0"]["production_roots"])
eng = tr._engine_for(ctx, "rev:HEAD")
fp_, cp_, _f, _t = tr._collect_patterns(tr._tree(ctx))
n_files = n_targets = 0
for path, e in sorted(tr._entries(ctx).items()):
    if not isinstance(e, dict) or e.get("disposition") != "rewrite":
        continue
    src = eng.tree.read(path)
    if src is None:
        continue
    fns = tr._test_functions(src, fp_, cp_)
    n_files += 1
    if not fns:
        print(f"G-c\t{path}\t(0 函式)")
        continue
    cov = tr._covered(ctx, e) if e.get("rewrite_targets") else [f"{path}::{q}" for q in fns]
    for tg in cov:
        q = tr._split_nodeid(tg)[1]
        if q not in fns:
            continue
        n_targets += 1
        if not (tr._scenario_symbols(eng, path, q, fns[q], roots) if hasattr(tr, "_scenario_symbols") else tr._prod_symbols(eng, path, fns[q], roots)):
            print(f"EMPTY\t{tg}")
print(f"files={n_files} targets={n_targets}", file=sys.stderr)
