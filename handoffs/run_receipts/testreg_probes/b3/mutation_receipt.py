"""TESTREG Task 3.2：rewrite 收據（契約 receipts.mutation）產生器。

前提：主工作樹已含改寫後之測試檔（未提交）；HEAD＝收據 head。
spec（JSON）：{"slug": "<收據檔名，通常為檔路徑 / → __>", "target": "<head 之函式層 nodeid>",
              "compare": ["<改寫後全部 rewrite_targets 涵蓋之函式層 nodeid>", ...],
              "mutants": [{"id": "m_x", "file": "momentum/…py", "old": "<HEAD 版中恰出現一次之片段>", "new": "<替換>"}, ...]}
步驟：①compare_patch＝`git diff HEAD --binary -- <compare 所在檔>`（空 ⇒ null）②於 HEAD 之乾淨 detached worktree 逐一
產生 mutant 補丁（只改 production_roots）③每 mutant：乾淨樹＋mutant 跑 target（記錄器）、乾淨樹＋compare_patch＋mutant
跑全部 compare（compare_patch 為 null 時與 target 同一 session）④session 複製回主 ledger ⑤組收據並以
`scripts.testreg._check_mutation` 自驗；不通過 ⇒ 不寫收據、rc 1。
worktree 隔離：NUMBA_CACHE_DIR 指向暫存目錄（不改寫已追蹤之 numba 快取）、data_cache 以 symlink 指回主工作樹並經
GIT_CONFIG_* 之 core.excludesFile 排除（記錄器之 diff_digest 與 validate 之重算皆不含之）；每次 pytest 前
`reset --hard`＋`clean -fd` 還原為 HEAD。
用法：venv/bin/python handoffs/run_receipts/testreg_probes/b3/mutation_receipt.py <spec.json> [--keep-worktree]
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
import scripts.testreg as tr  # noqa: E402

PY = str(REPO / "venv" / "bin" / "python")
MUT_DIR = "handoffs/run_receipts/testreg-mutants"
RW_DIR = "handoffs/run_receipts/testreg-rewrite"
PYTEST = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "log_cli=false", "--log-level=WARNING",
          "--tb=short"]


def _git(cwd: Path, *args: str, env: Optional[Dict[str, str]] = None, check: bool = True) -> str:
    p = subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(cwd), *args], capture_output=True, text=True,
                       env=env)
    if check and p.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])} rc={p.returncode}: {p.stderr[-400:]}")
    return p.stdout


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Sandbox:
    def __init__(self, head: str):
        self.tmp = Path(tempfile.mkdtemp(prefix="testreg_mut_"))
        self.wt = self.tmp / "wt"
        excl = self.tmp / "exclude"
        excl.write_text("/data_cache\n", encoding="utf-8")
        self.env = {k: v for k, v in os.environ.items() if k != "TESTREG_PARENT_SESSION"}
        self.env.update(GIT_CONFIG_COUNT="1", GIT_CONFIG_KEY_0="core.excludesFile", GIT_CONFIG_VALUE_0=str(excl),
                        NUMBA_CACHE_DIR=str(self.tmp / "numba"), PYTHONPATH=str(self.wt))
        _git(REPO, "worktree", "add", "-q", "--detach", str(self.wt), head)
        if (REPO / "data_cache").exists():
            (self.wt / "data_cache").symlink_to(REPO / "data_cache")

    def reset(self) -> None:
        _git(self.wt, "reset", "-q", "--hard", env=self.env)
        _git(self.wt, "clean", "-q", "-fd", env=self.env)
        if _git(self.wt, "status", "--porcelain", env=self.env).strip():
            raise SystemExit(f"暫存樹還原後仍不乾淨：{_git(self.wt, 'status', '--porcelain', env=self.env)[:300]}")

    def apply(self, patch_abs: Path) -> None:
        _git(self.wt, "apply", str(patch_abs), env=self.env)

    def run(self, nodeids: List[str]) -> str:
        led = self.wt / ".testreg" / "ledger"
        before = {p.name for p in led.glob("*.jsonl")} if led.is_dir() else set()
        subprocess.run([PY, *PYTEST, *nodeids], cwd=str(self.wt), env=self.env, capture_output=True, text=True)
        new = sorted({p.name for p in led.glob("*.jsonl")} - before) if led.is_dir() else []
        if len(new) != 1:
            raise SystemExit(f"pytest 未產生恰一個 session：{new}")
        dst = REPO / ".testreg" / "ledger"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(led / new[0], dst / new[0])
        return new[0][:-len(".jsonl")]

    def close(self) -> None:
        _git(REPO, "worktree", "remove", "--force", str(self.wt), check=False)
        shutil.rmtree(self.tmp, ignore_errors=True)


def main(argv: List[str]) -> int:
    spec = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    keep = "--keep-worktree" in argv
    head = _git(REPO, "rev-parse", "HEAD").strip()
    target, compare, slug = spec["target"], list(spec["compare"]), spec["slug"]
    files = sorted({c.split("::", 1)[0] for c in compare})
    cdiff = _git(REPO, "diff", "HEAD", "--binary", "--", *files)
    rw_dir = REPO / RW_DIR
    rw_dir.mkdir(parents=True, exist_ok=True)
    cpatch_rel = f"{RW_DIR}/{slug}.compare.patch" if cdiff else None
    if cpatch_rel:
        (REPO / cpatch_rel).write_text(cdiff, encoding="utf-8")
    mut_dir = REPO / MUT_DIR / slug
    mut_dir.mkdir(parents=True, exist_ok=True)
    sb = Sandbox(head)
    try:
        mutants: List[Dict[str, Any]] = []
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
            sb.apply(REPO / prel)
            sid = sb.run([target] + ([] if cpatch_rel else [c for c in compare if c != target]))
            csid = sid
            if cpatch_rel:
                sb.reset()
                sb.apply(REPO / cpatch_rel)
                sb.apply(REPO / prel)
                csid = sb.run(compare)
            mutants.append({"id": m["id"], "patch_path": prel, "patch_sha256": _sha(ptext), "session_id": sid,
                            "compare_session_id": csid})
        sb.reset()
    finally:
        if not keep:
            sb.close()
    ctx = tr.build_context(REPO)
    eng = tr._engine_for(ctx, f"rev:{head}")
    lines = sorted({f"{e['prov'][0]}:{e['prov'][1]}" for e in eng.elements(target) if e.get("prov")})
    lfiles = {l.rsplit(":", 1)[0] for l in lines} or {target.split("::", 1)[0]}
    dcs = set()
    for m in mutants:
        s, cs = tr._ledger_session(ctx, m["session_id"]), tr._ledger_session(ctx, m["compare_session_id"])
        dcs |= {(s["session"] or {}).get("duration_class"), (cs["session"] or {}).get("duration_class")}
        rec = tr._fn_record(s, target) or {}
        m["target_outcome"] = rec.get("outcome", "error")
        m["target_fail_loc"] = next((x for x in rec.get("fail_frames", []) if x.rsplit(":", 1)[0] in lfiles), None)
        m["compare_outcomes"] = {c: (tr._fn_record(cs, c) or {}).get("outcome", "error") for c in compare}
    rcpt = {"target_nodeid": target, "compare_nodeids": compare, "head": head,
            "fingerprint": next(iter(dcs)) if len(dcs) == 1 else "", "target_assertion_lines": lines,
            "mutants": mutants, "compare_patch_path": cpatch_rel,
            "compare_patch_sha256": _sha(cdiff) if cpatch_rel else None}
    out_rel = f"{RW_DIR}/{slug}.json"
    errs = tr._check_mutation(ctx, rcpt, out_rel, target, compare)
    summary = {m["id"]: (m["target_outcome"], m["target_fail_loc"], m["compare_outcomes"]) for m in mutants}
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    if errs:
        print("收據不成立（未寫）：\n  " + "\n  ".join(errs))
        (REPO / f"{RW_DIR}/{slug}.draft.json").write_text(json.dumps(rcpt, ensure_ascii=False, indent=1) + "\n",
                                                           encoding="utf-8")
        return 1
    (REPO / out_rel).write_text(json.dumps(rcpt, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK receipt={out_rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
