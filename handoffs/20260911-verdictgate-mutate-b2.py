#!/usr/bin/env python3
"""VERDICTGATE B2 mutation（每閘一條；UNCOVERED 須為 0）。用法：venv/bin/python handoffs/20260911-verdictgate-mutate-b2.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/governance/test_verdictgate_p2.py"
MUTATIONS = [
    ("M4 helper 排除 regex 永不命中", "scripts/prev_review_resolve.sh",
     'is_review = (bk == "review") if bk else (not EXCL.search(t))', 'is_review = True',
     f"{TEST}::test_helper_excludes_stamp_suffix_form"),
    ("M5 proceed 視同解除", "scripts/verdictgate_check.sh",
     "closed_later = any(o[0] > idx and o[1] == fam and o[6] in (\"review\", \"closure\") and i in o[4] for o in outputs)",
     "closed_later = True",
     f"{TEST}::test_check_proceed_does_not_release"),
    ("M5b 他家 CLOSED 也算", "scripts/verdictgate_check.sh",
     "o[0] > idx and o[1] == fam and", "o[0] > idx and",
     f"{TEST}::test_check_closed_by_other_family_does_not_release"),
    ("M6 C-9 roster 改讀 family_result（無 output 不擋）", "scripts/verdictgate_check.sh",
     "        if fam not in has_v:", "        if False:",
     f"{TEST}::test_check_no_output_family_blocks_and_names"),
    ("M7 stamp 之 CLOSED 也解除", "scripts/verdictgate_check.sh",
     "o[6] in (\"review\", \"closure\") and i in o[4]", "i in o[4]",
     f"{TEST}::test_check_stamp_closed_does_not_release"),
    ("M8 abandon 收窄關掉", "scripts/debt_clear.sh",
     'if [ "${kind}" = "collection-failed" ]; then', 'if false; then',
     f"{TEST}::test_abandon_collection_failed_rejected_when_family_result_exists"),
    ("M9 report stamp 計入 unknown", "scripts/verdictgate_baseline.sh",
     'elif all(o.get("verdict") == "null" for o in fam_outs):', 'elif False:',
     f"{TEST}::test_report_stamp_not_counted_unknown"),
    ("M10 checker 第三參數降為 optional", "scripts/verdictgate_check.sh",
     '[ $# -eq 3 ] || {', '[ $# -ge 2 ] || {',
     f"{TEST}::test_check_usage_two_args"),
]


def run(node: str) -> int:
    return subprocess.run([str(ROOT / "venv" / "bin" / "python"), "-m", "pytest", node, "-q", "-x"],
                          cwd=ROOT, capture_output=True, text=True, check=False).returncode


def main() -> int:
    uncovered = 0
    for mid, rel, old, new, node in MUTATIONS:
        p = ROOT / rel; src = p.read_text(encoding="utf-8")
        if old not in src:
            print(f"UNCOVERED {mid}: 錨點不存在（{rel}）"); uncovered += 1; continue
        try:
            p.write_text(src.replace(old, new, 1), encoding="utf-8"); rc = run(node)
        finally:
            p.write_text(src, encoding="utf-8")
        print(("COVERED   " if rc != 0 else "UNCOVERED ") + f"{mid}: rc={rc}")
        uncovered += 0 if rc != 0 else 1
    print(f"UNCOVERED={uncovered}")
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
