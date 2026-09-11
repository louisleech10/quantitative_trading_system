#!/usr/bin/env python3
"""VERDICTGATE B3 mutation（每閘一條；UNCOVERED 須為 0）。用法：venv/bin/python handoffs/20260911-verdictgate-mutate-b3.py"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEST = "tests/governance/test_verdictgate_p3.py"
TB = "scripts/ticket_batch_check.sh"
MUTATIONS = [
    ("M8 impl-self 不驗家族尾碼", "scripts/gate.sh",
     'm=re.match(r"^(?P<root>.+)-impl-b(?P<n>\\d+)-claude$", t)', 'm=re.match(r"^(?P<root>.+)-impl-b(?P<n>\\d+)-[a-z]+$", t)',
     f"{TEST}::test_31_impl_self_family_not_claude_rejected"),
    ("M9 small 檔數上限改 99", TB, '[ "${n}" -le 3 ] ||', '[ "${n}" -le 99 ] ||',
     f"{TEST}::test_32_small_five_files_rejected"),
    ("M9b 生產檔判定關掉（staged 生產碼視同 docs-only）", TB, '[ -n "${prod}" ] || exit 0', 'exit 0 || exit 0',
     f"{TEST}::test_32_prod_without_trailer_rejected"),
    ("M10 post-commit token_fresh 恆 true", TB, 'fresh="$(_token_fresh "${root}" "${batch}")"; fi', 'fresh="true"; fi',
     f"{TEST}::test_33_no_verify_then_token_not_ratified"),
    ("M11 任一 token 即錨（不要求消費）", TB, "    if consumed:\n        anchor = i", "    if True:\n        anchor = i",
     f"{TEST}::test_33_unconsumed_token_not_anchor"),
    ("M11b 消費不要求生產檔", TB, "and any(PROD.match(p) for p in (o.get(\"prod_files\") or []))", "and True",
     f"{TEST}::test_33_docs_only_batch_commit_does_not_consume"),
    ("M12 幽靈不過濾", TB, "    if not reachable(r.get(\"sha\") or \"\"):\n        ghosts += 1; continue", "    if False:\n        ghosts += 1; continue",
     f"{TEST}::test_33_ghost_sha_filtered"),
    ("M13 pre-push 不跳過 delete 行", "scripts/git_hooks/pre-push", '  [ "${_lsha}" = "${_pp_zero}" ] && continue', '  :',
     f"{TEST}::test_33_pre_push_all_delete_lines_ok"),
    ("M14 有 trailer 無事件不擋", TB, '      if [ -z "${ev}" ]; then', '      if false; then',
     f"{TEST}::test_33_trailer_without_event_rejected"),
    ("M15 range 內無 trailer 生產 commit 不擋", TB, 'if [ -n "${prod}" ] && [ -z "${trailer}" ]; then', 'if false; then',
     f"{TEST}::test_33_prod_commit_without_trailer_in_range_rejected"),
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
