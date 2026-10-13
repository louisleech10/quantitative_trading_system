#!/usr/bin/env python3
"""TESTREG v41：以契約 receipts.literal_fix 之代換產生 test_testreg_gate_wiring.py 之改名版（不寫入原檔）。

用法（cwd＝repo 根）：venv/bin/python handoffs/run_receipts/testreg_probes/literal_fix_rename.py <輸出檔>
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
REL = "tests/registry/test_testreg_gate_wiring.py"
MAP = {"tests/t.py": "tests/test_qt.py", "tests.t": "tests.test_qt"}


def main(out: str) -> int:
    lf = json.loads((REPO / "tests/registry/testreg_schema.json").read_text(encoding="utf-8"))["receipts"]["literal_fix"]
    alt = "|".join(re.escape(k) for k in sorted(MAP, key=lambda k: (-len(k), k)))
    rx = re.compile(f"(?<![{lf['boundary_chars']}])(?:{alt})(?![{lf['boundary_chars']}])")
    src = (REPO / REL).read_text(encoding="utf-8")
    new, n = rx.subn(lambda m: MAP[m.group(0)], src)
    Path(out).write_text(new, encoding="utf-8")
    print(f"replaced={n} -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
