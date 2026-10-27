"""NOCAP Task 0.2b③ pre-commit 掃描耗時實測（b1 審碼 r2 CODEX-R2-P1-02）：以既有提交之改動檔為代表樣本，
量 scan_text（暫存版）＋new_vs_head（HEAD 版重掃）之總耗時；寫收據 handoffs/run_receipts/20261027-nocap-precommit-scan-cost.json。

用法：`venv/bin/python handoffs/run_receipts/nocap_probes/precommit_scan_cost.py <提交>`（以 <提交>^ 為 HEAD、<提交> 為暫存版）。
"""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("ts_cost", REPO / "scripts" / "timeout_scan.py")
ts = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ts
spec.loader.exec_module(ts)


def show(rev: str, rel: str) -> str:
    out = subprocess.run(["git", "-C", str(REPO), "show", f"{rev}:{rel}"], capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else ""


def main() -> int:
    commit = sys.argv[1]
    names = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", f"{commit}^", commit],
                           capture_output=True, text=True, check=True).stdout.split()
    scoped = [n for n in names if ts._in_scope(n)]
    started = time.perf_counter()
    staged_hits = []
    for rel in scoped:  # 暫存版完整內容掃描（scan_staged 之等價成本）
        staged_hits += ts.scan_text(rel, show(commit, rel))
    for rel in {h.path for h in staged_hits}:  # new_vs_head 之 HEAD 版重掃（每檔一次）
        ts.scan_text(rel, show(f"{commit}^", rel))
    seconds = time.perf_counter() - started
    receipt = {"commit": commit, "changed_files": len(names), "scanned_files": len(scoped),
               "lines_scanned": sum(len(show(commit, r).splitlines()) for r in scoped),
               "staged_hits": len(staged_hits), "seconds": round(seconds, 3), "budget_seconds": 2.0,
               "within_budget": seconds < 2.0,
               "note": "不含 git show 之子行程啟動以外之 git 成本；scan_staged 另需一次 git diff --cached"}
    out = REPO / "handoffs" / "run_receipts" / "20261027-nocap-precommit-scan-cost.json"
    out.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
