"""TESTREG Task 4.2：E0（呼叫已刪符號）碑之收據產生器（只產收據，不動 catalog、不刪測試）。

用法：venv/bin/python handoffs/run_receipts/testreg_probes/b4/tomb_e0.py <nodeid> <deleted_module> <deleted_symbol> \
        <deleting_commit> <disposition_ref>
步驟：①於 HEAD 之乾淨 detached worktree（沿用 b3/mutation_receipt.py 之 Sandbox；NUMBA_CACHE_DIR 暫存、data_cache
symlink 並排除）只跑該 nodeid，session 複製回主 ledger（diff_digest＝clean）②取該紀錄之 exception_type／exception_origin
／exception_head 組 types.receipt_E0 ③以 `scripts.testreg._check_e0`（碑形 dict：nodeid、evidence_level=E0、
evidence_receipt、replaced_by=[]、disposition_ref）自驗；通過 ⇒ 寫 handoffs/run_receipts/testreg-retire/<slug>.json、rc 0；
不通過 ⇒ 不寫收據，草稿寫 handoffs/run_receipts/testreg_probes/b4/e0_drafts/<slug>.draft.json、rc 1。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
import scripts.testreg as tr  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "mutation_receipt", REPO / "handoffs/run_receipts/testreg_probes/b3/mutation_receipt.py")
mr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mr)

RDIR = "handoffs/run_receipts/testreg-retire"
DDIR = "handoffs/run_receipts/testreg_probes/b4/e0_drafts"


def main(argv):
    nodeid, modname, sym, dc, dref = argv[:5]
    head = mr._git(REPO, "rev-parse", "HEAD").strip()
    dc_full = mr._git(REPO, "rev-parse", f"{dc}^{{commit}}").strip()
    sb = mr.Sandbox(head)
    try:
        sb.reset()
        sid = sb.run([nodeid])
        sb.reset()
    finally:
        sb.close()
    ctx = tr.build_context(REPO)
    sess = tr._ledger_session(ctx, sid)
    rec = (sess or {}).get("tests", {}).get(nodeid) or {}
    info = (sess or {}).get("session") or {}
    print(json.dumps({"session_id": sid, "head": info.get("head"), "diff_digest": info.get("diff_digest"),
                      "outcome": rec.get("outcome"), "exception_type": rec.get("exception_type"),
                      "exception_origin": rec.get("exception_origin"),
                      "exception_head": rec.get("exception_head")}, ensure_ascii=False, indent=1))
    slug = nodeid.replace("/", "__").replace("::", "__")
    rel = f"{RDIR}/{slug}.json"
    rcpt = {"nodeid": nodeid, "head": head, "ledger_ref": {"session_id": sid, "nodeid": nodeid},
            "exception_type": rec.get("exception_type"), "exception_origin": rec.get("exception_origin"),
            "deleted_module": modname, "deleted_symbol": sym, "deleting_commit": dc_full}
    tomb = {"nodeid": nodeid, "evidence_level": "E0", "evidence_receipt": rel, "replaced_by": [],
            "disposition_ref": dref}
    errs = tr._check_e0(ctx, tomb, rcpt, rel)
    if errs:
        (REPO / DDIR).mkdir(parents=True, exist_ok=True)
        drel = f"{DDIR}/{slug}.draft.json"
        (REPO / drel).write_text(json.dumps(rcpt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("收據不成立（未寫）：\n  " + "\n  ".join(errs) + f"\n草稿：{drel}")
        return 1
    (REPO / RDIR).mkdir(parents=True, exist_ok=True)
    (REPO / rel).write_text(json.dumps(rcpt, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK receipt={rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
