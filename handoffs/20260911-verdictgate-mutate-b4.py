#!/usr/bin/env python3
"""VERDICTGATE B4 mutation（每閘一條；UNCOVERED 須為 0）。用法：venv/bin/python handoffs/20260911-verdictgate-mutate-b4.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P4 = "tests/governance/test_verdictgate_p4.py"
DC = "tests/governance/test_debt_clear.py"
MOD = "scripts/_synth_attr.py"
MUTATIONS = [
    ("M14 attribution 引用 20 字不比對", MOD,
     'if not any(q in nfc_strip(" ".join(r.cells)) for r in cands):', "if False:",
     f"{P4}::test_41_quote20_mismatch_rc_nonzero"),
    ("M15 attribution 延後目標不查 TODO", MOD,
     "elif tgt not in todo_text:", "elif False:",
     f"{P4}::test_41_defer_target_missing_in_todo_rc_nonzero"),
    ("M15b 缺 --todo 有延後不擋", MOD,
     "if todo_text is None:\n                        errs.append", "if False:\n                        errs.append",
     f"{P4}::test_41_defer_without_todo_flag_rc_nonzero"),
    ("M15c 延後目標被空白截斷（主委自查之原 bug）", MOD,
     'r"延後→([^|，。；、）)]*)"', 'r"延後→([^\\s|，。；、）)]*)"',
     f"{P4}::test_41_defer_target_with_space_is_whole_token"),
    ("M16 ID 不在表不擋", MOD,
     "miss = [f.id for f in doc.findings if not rows_for(doc, f.id)]", "miss = []",
     f"{P4}::test_41_id_in_table_absent_rc_nonzero"),
    ("M17 處置 token 缺不擋", MOD,
     "if not done:\n            errs.append", "if False:\n            errs.append",
     f"{P4}::test_41_disposition_absent_rc_nonzero"),
    ("M18 hook 對已完成列也不驗引用（completed_only 全部略過）", MOD,
     "cands = [r for r in cands if _row_done(r, values or [])]", "cands = []",
     f"{P4}::test_41_hook_completed_row_bad_quote_blocks"),
    ("M19 引用只取 5 字（放寬）", MOD, "QUOTE_N = 20", "QUOTE_N = 5",
     f"{P4}::test_41_quote20_mismatch_rc_nonzero"),
    ("M20 debt_clear 不呼叫群集歸戶閘", "scripts/debt_clear.sh",
     '  _run_attribution "${lock}" || return 1', "  true",
     f"{DC}::test_clear_attribution_gate_blocks_bad_synth"),
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
