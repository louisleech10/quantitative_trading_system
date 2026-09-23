"""TODOFMT Task 3.3：收案聚合入口 `scripts/todofmt_freeze_check.sh`（docs/TODOFMT_SPEC.md Task 3.3）。

以 `--items-file` 傳入 stub 陣列（生產呼叫不傳參數即用腳本字面，同一判定路徑）；本測試**不經聚合器執行**，無自我參照。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE = REPO_ROOT / "scripts" / "todofmt_freeze_check.sh"
_BLOCK = re.compile(r"^_ITEMS='\n(.*?)^'\n", re.S | re.M)


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(FREEZE), *args], capture_output=True, text=True, check=False)


def _items(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "items.txt"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _stub(tmp_path: Path, name: str, body: str) -> str:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return str(p)


def _pytest_item(tmp_path: Path, name: str, body: str) -> str:
    return f"venv/bin/python -m pytest -q -p no:cacheprovider {_stub(tmp_path, name, body)}"


def _production_items() -> list[str]:
    m = _BLOCK.search(FREEZE.read_text(encoding="utf-8"))
    assert m, "找不到腳本內之字面陣列"
    return [ln for ln in m.group(1).splitlines() if ln.strip()]


def test_boundary_01_second_item_never_starts(tmp_path: Path) -> None:
    ok = _stub(tmp_path, "ok.sh", "exit 0\n")
    r = _run("--items-file", str(_items(tmp_path, [f"bash {ok}", "no_such_executable_todofmt_xyz"])))
    assert r.returncode != 0, r.stdout


def test_boundary_02_all_items_pass(tmp_path: Path) -> None:
    ok = _stub(tmp_path, "ok.sh", "exit 0\n")
    r = _run("--items-file", str(_items(tmp_path, [f"bash {ok}", f"bash {ok}"])))
    assert r.returncode == 0 and "TODOFMT FREEZE PASS" in r.stdout, r.stdout


def test_boundary_03_skip_counts_as_failure(tmp_path: Path) -> None:
    item = _pytest_item(tmp_path, "test_s.py", "import pytest\n\ndef test_a():\n    pytest.skip('x')\n\ndef test_b():\n    assert 1\n")
    r = _run("--items-file", str(_items(tmp_path, [item])))
    assert r.returncode != 0 and "skipped" in r.stdout, r.stdout


def test_boundary_03b_skip_detected_even_when_output_follows_summary(tmp_path: Path) -> None:
    """b2 審碼 codex／grok：pytest 摘要之後另有輸出（此處以 pytest_unconfigure 印四行）時，skip 仍須被判未通過。"""
    d = tmp_path / "suite"
    d.mkdir()
    (d / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (d / "conftest.py").write_text(
        "def pytest_unconfigure(config):\n    for i in range(4):\n        print(f'FOOTER-{i}')\n", encoding="utf-8"
    )
    (d / "test_f.py").write_text(
        "import pytest\n\ndef test_a():\n    pytest.skip('x')\n\ndef test_b():\n    assert 1\n", encoding="utf-8"
    )
    item = f"venv/bin/python -m pytest -q -p no:cacheprovider -c {d}/pytest.ini --rootdir {d} {d}/test_f.py"
    r = _run("--items-file", str(_items(tmp_path, [item])))
    assert r.returncode != 0 and "skipped" in r.stdout, r.stdout


def test_boundary_04_xfail_counts_as_failure(tmp_path: Path) -> None:
    item = _pytest_item(tmp_path, "test_x.py", "import pytest\n\n@pytest.mark.xfail\ndef test_a():\n    assert 0\n")
    r = _run("--items-file", str(_items(tmp_path, [item])))
    assert r.returncode != 0 and "xfailed" in r.stdout, r.stdout


def test_boundary_05_nonzero_item_fails_aggregate(tmp_path: Path) -> None:
    ok = _stub(tmp_path, "ok.sh", "exit 0\n")
    bad = _stub(tmp_path, "bad.sh", "exit 3\n")
    r = _run("--items-file", str(_items(tmp_path, [f"bash {ok}", f"bash {bad}"])))
    assert r.returncode != 0 and "rc=3" in r.stdout, r.stdout


def test_boundary_06_production_array_is_script_literal_and_spec_not_read() -> None:
    items = _production_items()
    assert len(items) == 12
    code = [ln for ln in FREEZE.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#")]
    assert not any("TODOFMT_SPEC" in ln for ln in code), "聚合器不得讀 SPEC"


def test_boundary_07_production_items_are_complete_argv() -> None:
    for item in _production_items():
        argv = item.split()
        assert argv[0] in {"bash", "venv/bin/python"}, item
        assert not re.search(r"[*?\[]", item), item
        assert "gate.sh" not in item, item


def test_boundary_08_record_uses_final_rc_not_start(tmp_path: Path) -> None:
    late = _stub(tmp_path, "late.sh", "echo '1 passed in 0.01s'\nsleep 0.2\nexit 7\n")
    r = _run("--items-file", str(_items(tmp_path, [f"bash {late}"])))
    assert r.returncode != 0 and "rc=7" in r.stdout, r.stdout


@pytest.mark.parametrize(
    "record",
    [["a", "b"], ["a", "b", "c", "d"], ["a", "c", "b"]],
    ids=["missing", "extra", "reordered"],
)
def test_boundary_09_record_not_equal_to_array_fails(tmp_path: Path, record: list[str]) -> None:
    exp = tmp_path / "exp.txt"
    exp.write_text("a\nb\nc\n", encoding="utf-8")
    rec = tmp_path / "rec.txt"
    rec.write_text("\n".join(record) + "\n", encoding="utf-8")
    assert _run("--compare", str(exp), str(rec)).returncode == 1
    assert _run("--compare", str(exp), str(exp)).returncode == 0


def test_stdin_consuming_item_does_not_swallow_remaining_items(tmp_path: Path) -> None:
    ok = _stub(tmp_path, "ok.sh", "exit 0\n")
    r = _run("--items-file", str(_items(tmp_path, ["cat", f"bash {ok}"])))
    item_lines = [ln for ln in r.stdout.splitlines() if ln.startswith("PASS：")]
    assert r.returncode == 0 and len(item_lines) == 2, r.stdout


def test_mutation_disabling_record_comparison_is_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """把「紀錄＝陣列」之比對改為恆真 ⇒ 不等之紀錄亦判通過（證邊界⑨之測試有鑑別力）。"""
    src = FREEZE.read_text(encoding="utf-8")
    anchor = '[ "$(_nonblank "$1")" = "$(_nonblank "$2")" ]'
    assert src.count(anchor) == 1
    mutant = tmp_path / "mutant_freeze.sh"
    mutant.write_text(src.replace(anchor, "true"), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "FREEZE", mutant)
    exp = tmp_path / "exp.txt"
    exp.write_text("a\nb\n", encoding="utf-8")
    rec = tmp_path / "rec.txt"
    rec.write_text("a\n", encoding="utf-8")
    assert _run("--compare", str(exp), str(rec)).returncode == 0, "mutation 未生效"
