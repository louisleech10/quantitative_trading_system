#!/usr/bin/env python3
"""VERDICTGATE B1 mutation（SPEC §V：每閘一條；UNCOVERED 須為 0）。

對每個 mutation：就地改 scripts/<file>（備份→改→跑指定測試→還原）；
指定測試必須翻紅（rc≠0）才算 COVERED。紅只認 pytest rc≠0，不認 stdout 字樣。
用法：venv/bin/python handoffs/20260911-verdictgate-mutate-b1.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/governance/test_verdictgate_p1.py"

# (mutation id, file, old, new, test node)
MUTATIONS = [
    ("M1 雙 VERDICT 不報歧義", "scripts/verdict_parse.sh",
     "elif len(vlines) >= 2:", "elif False:",
     f"{TEST}::test_12_two_verdict_lines_rejected"),
    ("M1b 全形冒號不指名", "scripts/verdict_parse.sh",
     'if fullwidth:', 'if False:',
     f"{TEST}::test_12_fullwidth_colon_rejected_and_named"),
    ("M2 expected path 不驗", "scripts/gate.sh",
     "if expected != out_rel:", "if False:",
     f"{TEST}::test_12_path_not_expected_output_rejected"),
    ("M2b roster 不驗", "scripts/gate.sh",
     "if family not in roster:", "if False:",
     f"{TEST}::test_12_family_not_in_roster_rejected"),
    ("M2c CLOSED 同 root 不驗", "scripts/verdict_parse.sh",
     "if ID_RE.match(i) and i.split(\"-\", 1)[0] == fam_up and i not in corpus_ids:", "if False:",
     f"{TEST}::test_12_closed_id_found_only_in_other_root_rejected"),
    ("M2e 語料不含舊輪 expected_outputs（收票前自查：補裁決輪關不了舊 ID）", "scripts/gate.sh",
     '    elif ev == "committee_round_open":', '    elif False:',
     f"{TEST}::test_12_closed_id_in_legacy_round_expected_output_accepted"),
    ("M2f 語料 root 不去日期前綴（收票審 R12：同票跨日互不相認）", "scripts/gate.sh",
     '    return re.sub(r"^\\d{8}-", "", r)', "    return r",
     f"{TEST}::test_12_closed_id_same_epic_different_date_prefix_accepted"),
    ("M2d blocked 無 BLOCKED-BY 不擋", "scripts/verdict_parse.sh",
     'if verdict == "blocked" and (not has_blocked_line or not blocked_by):', "if False:",
     f"{TEST}::test_12_blocked_without_blocked_by_rejected"),
    ("M3 cx_run 自動註冊直接 return", "scripts/cx_run.sh",
     "  case \"${_bk}\" in review|closure) : ;; *) return 0 ;; esac", "  return 0",
     f"{TEST}::test_12_cx_run_review_done_with_verdict_auto_registers"),
    ("M3b 拒收不留 verdict_rejected", "scripts/cx_run.sh",
     '--field "result_state=verdict_rejected"', '--field "result_state=failed"',
     f"{TEST}::test_12_cx_run_review_done_without_verdict_marks_rejected_rc_unchanged"),
    ("M4 帳本對 sequence_since 後之無 seq 列也放行", "scripts/_debt_ledger_core.py",
     "if ts_pre is not None and ts_pre < ss_dt:", "if True:",
     f"{TEST}::test_12_ledger_rejects_post_v3_committee_output_without_sequence"),
    ("M5 帳本忽略 round_scoped:false（對非輪級事件仍要 round_id）", "scripts/_debt_ledger_core.py",
     'get(ev, {}).get("round_scoped", True) is False:', 'get(ev, {}).get("round_scoped", True) is None:',
     f"{TEST}::test_12_ledger_tolerates_round_unscoped_events_and_output_carries_round_id"),
    ("M3c 自動註冊只認 STATUS: DONE（漏 VERDICT 訊號）", "scripts/cx_run.sh",
     "if ! grep -qE '^STATUS: DONE' \"${out}\" && ! grep -qE '^VERDICT:' \"${out}\"; then",
     "if ! grep -qE '^STATUS: DONE' \"${out}\"; then",
     f"{TEST}::test_12_cx_run_review_verdict_without_status_done_still_registers"),
    ("M1c template_check 雙格式不擋", "scripts/template_check.sh",
     "if grep -qE '^## Verdict[:：]' \"${file}\"; then", "if false; then",
     f"{TEST}::test_11_template_check_rejects_dual_format"),
]


def run(node: str) -> int:
    r = subprocess.run([str(ROOT / "venv" / "bin" / "python"), "-m", "pytest", node, "-q", "-x"],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    return r.returncode


def main() -> int:
    uncovered = 0
    for mid, rel, old, new, node in MUTATIONS:
        p = ROOT / rel
        src = p.read_text(encoding="utf-8")
        if old not in src:
            print(f"UNCOVERED {mid}: 錨點不存在（{rel}: {old[:50]!r}）")
            uncovered += 1
            continue
        try:
            p.write_text(src.replace(old, new, 1), encoding="utf-8")
            rc = run(node)
        finally:
            p.write_text(src, encoding="utf-8")
        if rc != 0:
            print(f"COVERED   {mid}: 測試翻紅 rc={rc}")
        else:
            print(f"UNCOVERED {mid}: mutation 後測試仍綠")
            uncovered += 1
    print(f"UNCOVERED={uncovered}")
    return 1 if uncovered else 0


if __name__ == "__main__":
    sys.exit(main())
