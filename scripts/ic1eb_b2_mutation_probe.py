"""IC1EB B2 mutation 探針:注入 t_stat×2 → 主同判測試必轉紅 → 還原 → 復綠。

整體 exit 0 = mutation 行為符合預期(紅得起來且還原乾淨);任何一步不符 → exit 1。
供 run_with_receipt 包裝產 mutation_runtime 類收據。
"""
from __future__ import annotations

import hashlib
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TARGET = REPO / "momentum/Analysis/statistical_validator.py"
ORIG = "t_stat = float(mean_z / se)"
MUT = "t_stat = float(mean_z / se) * 2  # TEMP-MUTANT"
TEST = "tests/momentum/test_statistical_validator.py::test_t13_block_bootstrap_agrees_with_kernel"


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_pytest() -> int:
    return subprocess.run(
        [sys.executable, "-m", "pytest", TEST, "-q"], cwd=REPO
    ).returncode


def main() -> int:
    src = TARGET.read_text()
    if src.count(ORIG) != 1:
        print(f"PROBE FAIL: expected exactly one occurrence of target line")
        return 1
    pre_sha = sha(TARGET)
    if run_pytest() != 0:
        print("PROBE FAIL: baseline test not green before mutation")
        return 1
    TARGET.write_text(src.replace(ORIG, MUT))
    try:
        red = run_pytest()
    finally:
        TARGET.write_text(src)
    if sha(TARGET) != pre_sha:
        print("PROBE FAIL: restore did not return file to original bytes")
        return 1
    if red == 0:
        print("PROBE FAIL: mutation did NOT turn test red (fake-green risk)")
        return 1
    if run_pytest() != 0:
        print("PROBE FAIL: test not green after restore")
        return 1
    print(f"MUTATION PROBE PASS: red exit={red}, restore sha match, re-green ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
