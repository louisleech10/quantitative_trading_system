"""PRE-RED Task 1.1 實作期查證：列出現行靜態器量化層 fatal 中，W 時已存在但不在 QUANT_FATAL 之名稱，
並判斷其於 W 版與現行版之函式本體是否不同（W 後被改寫）。用法：venv/bin/python <本檔>"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
from tests.governance import _todofmt_anchor as anchor  # noqa: E402
from tests.governance.test_mutation_scope_extension import QUANT_FATAL, _run_entry  # noqa: E402

W = anchor.effective_commit()
_, names, _ = _run_entry()
quant = {n for n in names if not n.startswith("tests/governance/")}


def body(src: str, func: str) -> str:
    m = re.search(rf"^def {re.escape(func)}\(.*?(?=^def |^class |\Z)", src, re.M | re.S)
    return m.group(0) if m else ""


for n in sorted(quant - QUANT_FATAL):
    path, func = n.split("::", 1)
    w_src = anchor.show(W, path) or ""
    now_src = (REPO / path).read_text(encoding="utf-8")
    bw, bn = body(w_src, func), body(now_src, func)
    last = subprocess.run(["git", "log", "-1", "--format=%h %ad", "--date=short", "--", path], cwd=REPO,
                          capture_output=True, text=True).stdout.strip()
    print(f"{n}  existed_at_W={bool(bw)}  body_changed_since_W={bool(bw) and bw != bn}  file_last={last}")
