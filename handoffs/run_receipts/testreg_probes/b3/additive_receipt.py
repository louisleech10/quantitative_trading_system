"""TESTREG Task 3.2：純增改寫收據（契約 receipts.additive_rewrite，SPEC v48）產生器。

前提：主工作樹已含改寫後之測試檔（只新增函式，未提交）；HEAD＝收據 head。
spec（JSON）：{"path": "<測試檔>", "approval_ref": "<含 path 之收斂檔>",
              "mutants": [{"id": "m_x", "file": "momentum/…py", "old": "<HEAD 版中恰出現一次之片段>", "new": "<替換>"}, ...]}
步驟：①compare_patch＝`git diff HEAD --binary -- <path>` ②乾淨 detached worktree 中逐一產生 mutant 補丁（只改
production_roots）③baseline＝head＋compare_patch 跑 path 全檔；每 mutant＝head＋compare_patch＋mutant 跑 path 全檔
（記錄器）④session 複製回主 ledger ⑤組收據寫至契約路徑，以 scripts.testreg.additive_rewrite_errors 自驗；不成立 ⇒
改名 .draft.json、rc 1。worktree 隔離同 mutation_receipt.py（NUMBA_CACHE_DIR 暫存、data_cache symlink 經
core.excludesFile 排除、每次 pytest 前 reset＋clean）。
用法：venv/bin/python handoffs/run_receipts/testreg_probes/b3/additive_receipt.py <spec.json> [--keep-worktree]
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_receipt import REPO, Sandbox, _git, _sha, tr  # noqa: E402

MUT_DIR = "handoffs/run_receipts/testreg-mutants"


def main(argv: List[str]) -> int:
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    keep = "--keep-worktree" in argv
    path = spec["path"]
    slug = path.replace("/", "__")
    head = _git(REPO, "rev-parse", "HEAD").strip()
    s = tr.load_schema(REPO)
    cdiff = _git(REPO, "diff", "HEAD", "--binary", "--", path)
    if not cdiff:
        raise SystemExit(f"{path} 相對 HEAD 無改動")
    adir = REPO / s["receipts"]["additive_rewrite"]["dir"]
    adir.mkdir(parents=True, exist_ok=True)
    cp_rel = f"{s['receipts']['additive_rewrite']['dir']}/{slug}.compare.patch"
    (REPO / cp_rel).write_text(cdiff, encoding="utf-8")
    (REPO / MUT_DIR / slug).mkdir(parents=True, exist_ok=True)
    ctx0 = tr.build_context(REPO)
    fp_, cp_, _f, _t = tr._collect_patterns(tr._tree(ctx0))
    head_src = tr._Tree(REPO, "HEAD").read(path) or ""
    cur_src = (REPO / path).read_text(encoding="utf-8")
    added = sorted(f"{path}::{q}" for q in set(tr._test_functions(cur_src, fp_, cp_))
                   - set(tr._test_functions(head_src, fp_, cp_)))
    sb = Sandbox(head)
    mutants: List[Dict[str, Any]] = []
    try:
        sb.reset()
        sb.apply(REPO / cp_rel)
        base = sb.run([path])
        for m in spec["mutants"]:
            sb.reset()
            f = sb.wt / m["file"]
            src = f.read_text(encoding="utf-8")
            if src.count(m["old"]) != 1:
                raise SystemExit(f"mutant {m['id']}：片段於 HEAD 版出現 {src.count(m['old'])} 次（須恰 1）")
            f.write_text(src.replace(m["old"], m["new"], 1), encoding="utf-8")
            ptext = _git(sb.wt, "diff", "--binary", "--", m["file"], env=sb.env)
            prel = f"{MUT_DIR}/{slug}/{m['id']}.patch"
            (REPO / prel).write_text(ptext, encoding="utf-8")
            sb.reset()
            sb.apply(REPO / cp_rel)
            sb.apply(REPO / prel)
            sid = sb.run([path])
            mutants.append({"id": m["id"], "patch_path": prel, "patch_sha256": _sha(ptext), "session_id": sid})
        sb.reset()
    finally:
        if not keep:
            sb.close()
    ctx = tr.build_context(REPO)
    dcs = {(tr._ledger_session(ctx, x)["session"] or {}).get("duration_class")
           for x in [base] + [m["session_id"] for m in mutants]}
    rcpt = {"path": path, "head": head, "approval_ref": spec["approval_ref"],
            "fingerprint": next(iter(dcs)) if len(dcs) == 1 else "", "compare_patch_path": cp_rel,
            "compare_patch_sha256": _sha(cdiff), "added_nodeids": added, "baseline_session_id": base,
            "mutants": mutants}
    rel = tr._receipt_rel(s, "additive_rewrite", path)
    (REPO / rel).write_text(json.dumps(rcpt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    errs = tr.additive_rewrite_errors(tr.build_context(REPO), path)
    summary = {}
    for m in mutants:
        recs = tr._ledger_session(ctx, m["session_id"])["tests"]
        summary[m["id"]] = {k.split("::", 1)[1]: v["outcome"] for k, v in recs.items() if v["outcome"] != "passed"}
    print(json.dumps({"added": added, "mutant_failures": summary}, ensure_ascii=False, indent=1))
    if errs:
        (REPO / rel).rename(REPO / rel.replace(".json", ".draft.json"))
        print("收據不成立（已改名 .draft.json）：\n  " + "\n  ".join(errs))
        return 1
    print(f"OK receipt={rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
