"""scripts/affected_from_coverage.py：依逐測試覆蓋算執行到改動 Python 程式之 nodeid（TEST_SELECTION §5 過渡工具）。"""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

from coverage import CoverageData

REPO = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("affected_from_coverage_t", REPO / "scripts" / "affected_from_coverage.py")
afc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(afc)  # type: ignore[union-attr]

_BEFORE = "X = 1\n\n\ndef f(a):\n    y = a + 1\n    return y\n\n\ndef g(b):\n    return b\n"
#: 只改 f 之簽名（預設值）——簽名只在 import 期執行；f 函式體未改
_AFTER = "X = 2\n\n\ndef f(a=0):\n    y = a + 1\n    return y\n\n\ndef g(b):\n    return b\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _setup(tmp_path: Path) -> Path:
    root = tmp_path / "r"
    root.mkdir()
    (root / "m.py").write_text(_BEFORE, encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    (root / "m.py").write_text(_AFTER, encoding="utf-8")
    (root / "new.py").write_text("def h():\n    return 3\n", encoding="utf-8")
    return root


def _data(root: Path, tmp_path: Path) -> str:
    path = str(tmp_path / ".cov")
    cd = CoverageData(basename=path)
    m, new = str((root / "m.py").resolve()), str((root / "new.py").resolve())
    for ctx, lines in [("", {m: [1, 4, 9], new: [1]}), ("tests/t_a.py::test_a|run", {m: [5, 6]}),
                       ("tests/t_b.py::test_b|run", {m: [10]}), ("tests/t_c.py::test_c|setup", {m: [5]}),
                       ("tests/t_d.py::test_d|run", {new: [2]})]:
        cd.set_context(ctx)
        cd.add_lines(lines)
    cd.write()
    return path


def test_function_level_dependency_setup_and_import_only(tmp_path: Path) -> None:
    """簽名改動 ⇒ 執行函式體之測試受影響（函式級依賴）；他函式不選；setup 命中列檔；模組層級只在 import 期執行之
    改動行另列；未追蹤新檔全部行算改動。"""
    root = _setup(tmp_path)
    hits, setup_files, import_lines, missing = afc.affected(_data(root, tmp_path), ["m.py", "new.py", "gone.py"], root)
    assert set(hits) == {"tests/t_a.py::test_a", "tests/t_c.py::test_c", "tests/t_d.py::test_d"}
    assert set(setup_files) == {"tests/t_c.py"}
    assert import_lines == {"m.py": {1, 4}, "new.py": {1}}
    assert missing == ["gone.py"]


def test_continuation_import_only_and_shared_fixture(tmp_path: Path) -> None:
    """模組層多行敘述只改續行、只在 import 期執行 ⇒ 列入 import_lines（敘述首行）；setup 命中者依 shared 擴散至他檔
    共用同一 fixture 之 nodeid。"""
    root = tmp_path / "r"
    root.mkdir()
    (root / "m.py").write_text("X = (1,\n     2)\n\n\ndef f():\n    return X\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    (root / "m.py").write_text("X = (1,\n     3)\n\n\ndef f():\n    return X\n", encoding="utf-8")
    path = str(tmp_path / ".cov2")
    cd = CoverageData(basename=path)
    m = str((root / "m.py").resolve())
    for ctx, lines in [("", {m: [1, 5]}), ("tests/a.py::first|setup", {m: [1]})]:
        cd.set_context(ctx)
        cd.add_lines(lines)
    cd.write()
    shared = {"tests/a.py::first": {"session:tests::db"}, "tests/b.py::later": {"session:tests::db"},
              "tests/c.py::unrelated": {"module:tests/c.py::x"}}
    hits, _setup, import_lines, _missing = afc.affected(path, ["m.py"], root, shared=shared)
    assert import_lines == {"m.py": {1}}
    assert "shared-fixture:tests/a.py::first" in hits["tests/b.py::later"]
    assert "tests/c.py::unrelated" not in hits


def test_changed_lines_pure_deletion_and_continuation(tmp_path: Path) -> None:
    """純刪除 hunk 取前後各一行；多行敘述之續行改動映射至敘述首行。"""
    root = tmp_path / "r"
    root.mkdir()
    (root / "m.py").write_text("a = 1\nb = 2\nc = (1,\n     2)\nd = 4\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    (root / "m.py").write_text("a = 1\nc = (1,\n     3)\nd = 4\n", encoding="utf-8")
    raw = afc.changed_lines(root, "m.py")
    assert {1, 2} <= raw and 3 in raw
    assert afc.dependency_lines(root / "m.py", {3}) == {2}
