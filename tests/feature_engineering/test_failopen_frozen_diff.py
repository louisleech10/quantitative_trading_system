"""Task 6.1 [V-8]：既有 tests/ 斷言變更須登記於 FF_FAILOPEN_FROZEN_TESTS.md。"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FROZEN_DOC = ROOT / "docs/FF_FAILOPEN_FROZEN_TESTS.md"
BASELINE_COMMIT = "d654237"
ASSERTION_LINE_RE = re.compile(
    r"^\s*(assert\b|pytest\.raises|with pytest\.raises|assert_frame_equal|assert_series_equal)",
    re.MULTILINE,
)


def _git_output(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"git {' '.join(args)} failed")
    return proc.stdout


def _existing_test_files_at_baseline() -> set[str]:
    output = _git_output("ls-tree", "-r", "--name-only", BASELINE_COMMIT, "tests/")
    return {line.strip() for line in output.splitlines() if line.strip()}


def _parse_diff_paths(diff_text: str) -> dict[str, list[tuple[str, str]]]:
    """回傳 path -> [(sign, line), ...] 僅含 assertion 相關行。"""
    per_file: dict[str, list[tuple[str, str]]] = {}
    current: str | None = None
    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            current = raw[6:].strip()
            if current == "/dev/null":
                current = None
            continue
        if current is None or not raw or raw.startswith("@@"):
            continue
        if raw[0] not in {"+", "-"} or raw.startswith("+++") or raw.startswith("---"):
            continue
        line = raw[1:]
        if ASSERTION_LINE_RE.search(line):
            per_file.setdefault(current, []).append((raw[0], line))
    return per_file


def test_v8_frozen_list_covers_existing_test_assertion_changes() -> None:
    """[V-8] d654237..HEAD 既有測試檔的 assertion 變更須出現在 frozen list。"""
    if not FROZEN_DOC.is_file():
        pytest.skip("missing frozen assertion doc")

    frozen_text = FROZEN_DOC.read_text(encoding="utf-8")
    existing_files = _existing_test_files_at_baseline()
    diff_text = _git_output("diff", f"{BASELINE_COMMIT}..HEAD", "-U0", "--", "tests/")
    changes = _parse_diff_paths(diff_text)

    undocumented: list[str] = []
    for path, hunks in sorted(changes.items()):
        if path not in existing_files:
            continue
        if not hunks:
            continue
        if path not in frozen_text:
            undocumented.append(f"{path}: assertion change not listed in {FROZEN_DOC.name}")

    assert not undocumented, "undocumented assertion changes:\n" + "\n".join(undocumented)
