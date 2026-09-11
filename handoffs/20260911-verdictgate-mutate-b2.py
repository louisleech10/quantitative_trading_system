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
    ("M4b 已進入批次判定恆真（任何批皆跳過前批驗證；B4 收票前主委自查）", "scripts/verdictgate_check.sh",
     'if r.get("event") == "committee_round_open" and (r.get("task_id") or "").lower().startswith(pfx):', "if True:",
     f"{TEST}::test_check_batch_already_entered_skips_prev_verdicts"),
    ("M4c 已進入批次判定恆假（閉合輪也重驗前批 ⇒ 補裁決輪連鎖回溯）", "scripts/verdictgate_check.sh",
     '    if r.get("event") == "committee_round_open" and (r.get("task_id") or "").lower().startswith(pfx):\n        sys.exit(0)', '    if False:\n        sys.exit(0)',
     f"{TEST}::test_check_batch_already_entered_skips_prev_verdicts"),
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
    ("M11 quorum 不認 committee_output（只認 dispatch 尾碼）", "scripts/review_quorum_check.sh",
     '    elif ev == "committee_output":', '    elif False:',
     f"{TEST}::test_quorum_counts_committee_output_families_case_insensitive"),
    ("M12 helper 同 K 只留最早 prefix", "scripts/prev_review_resolve.sh",
     "    if prefix not in lst:\n        lst.append(prefix)", "    if not lst:\n        lst.append(prefix)",
     f"{TEST}::test_helper_returns_all_prefixes_of_same_batch_and_checker_checks_each"),
    ("M13 report 忽略 debt_clear（已清仍 live）", "scripts/verdictgate_baseline.sh",
     'closed_rids = {r.get("round_id") for r in rows if r.get("event") in ("committee_debt_clear", "debt_abandon")}',
     'closed_rids = set()',
     f"{TEST}::test_report_cleared_root_not_live"),
    ("M14 committee_run 前置 verdictgate 拿掉", "scripts/committee_run.sh",
     'if [ -n "${_vg_parsed}" ] && [ "${_cr_brief_kind}" != "closure" ]; then', 'if false; then',
     f"{TEST}::test_committee_run_verdictgate_fail_rc_nonzero_zero_audit"),
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
