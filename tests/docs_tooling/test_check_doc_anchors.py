from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER = REPO_ROOT / "scripts" / "check_doc_anchors.sh"
FIXTURES = Path(__file__).parent / "fixtures"


def load_checker_functions() -> tuple[Callable[[str], str], Callable[[str], set[str]]]:
    """載入 checker heredoc 中的純函式，直接驗證 slug，不經 delta gate。"""
    script = CHECKER.read_text(encoding="utf-8")
    python_source = script.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    definitions = python_source.split("\nparser = argparse.ArgumentParser", 1)[0]
    namespace: dict[str, object] = {"__name__": "check_doc_anchors_test"}
    exec(compile(definitions, str(CHECKER), "exec"), namespace)
    return namespace["slug"], namespace["anchors"]  # type: ignore[return-value]


@pytest.mark.parametrize(
    ("heading", "expected"),
    [
        ("foo_bar", "foo_bar"),
        ("foo   bar", "foo---bar"),
        ("C++ 使用指南", "c-使用指南"),
        ("API（生命週期）", "api生命週期"),
        ("中文標題", "中文標題"),
        ("  padded  ", "padded"),
        ("*bold* and _emphasis_", "bold-and-emphasis"),
        ("literal_under_score", "literal_under_score"),
    ],
)
def test_slug_matches_github_boundaries(heading: str, expected: str) -> None:
    """GitHub heading slug 邊界表：字面底線與 emphasis delimiter 必須有別。"""
    slug, _ = load_checker_functions()
    assert slug(heading) == expected


def test_anchors_have_exact_expected_set() -> None:
    """直接比對完整集合，使 duplicate suffix 或任一 slug mutation 可證偽。"""
    _, anchors = load_checker_functions()
    headings = FIXTURES.joinpath("headings.md").read_text(encoding="utf-8")
    assert anchors(headings) == {
        "中文標題",
        "c-使用指南",
        "api生命週期",
        "重複標題",
        "重複標題-1",
        "重複標題-2",
        "foo_bar",
        "強調-與-emphasis",
    }


@pytest.fixture()
def fixture_repo(tmp_path: Path) -> Path:
    """建立隔離 git repo，讓 checker 的 HEAD baseline 可被驗證。"""
    shutil.copytree(FIXTURES, tmp_path / "fixtures")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "fixtures/headings.md", "fixtures/nested/source.md"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "test fixture baseline"], cwd=tmp_path, check=True)
    return tmp_path


def run_checker(repo: Path, files: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(CHECKER), "--files", files],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


def test_required_anchor_cases_pass(fixture_repo: Path) -> None:
    """各 slug 邊界、相對路徑與 reference-style 在 e2e 均有效。"""
    result = run_checker(fixture_repo, "fixtures/nested/source.md")
    assert result.returncode == 0, result.stdout
    assert "New dead links: 0" in result.stdout


def test_missing_anchor_is_a_falsifiable_failure(fixture_repo: Path) -> None:
    """缺 anchor 必須令 checker exit 1；若誤放行，此測試會紅。"""
    shutil.copy(FIXTURES / "missing.md.fixture", fixture_repo / "fixtures/missing.md")
    result = run_checker(fixture_repo, "fixtures/missing.md")
    assert result.returncode == 1, result.stdout
    assert "New dead links: 1" in result.stdout
    assert "fixtures/missing.md:1" in result.stdout
