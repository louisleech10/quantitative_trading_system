"""TODOFMT Task 1.2：產出端 hook——新票寫散文 TODO 即擋（docs/TODOFMT_SPEC.md Task 1.2、§P「生效之判定」）。

判定邊界①–⑬以 `--legacy-list` 傳入測試清單（同一判定函式；生產呼叫不傳即用腳本字面）；
⑭–⑱ 與掛載、§P 之 L 時序檢查以錨點模組對 L／X 驗證。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.governance import _todofmt_anchor as anchor

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "scripts" / "todofmt_write_guard.sh"
LIST_BEGIN = "TODOFMT LEGACY TODO LIST"
TEST_LIST = [
    "docs/gap2_marginal_ic_todo.md",
    "docs/gap3_event_todo.d-001.md",
    "docs/archived/old_todo.md",
]
_GEN_BLOCK = re.compile(r"^<!-- (BEGIN|END) GENERATED: [^>]+-->\s*$")


def _list_file(tmp_path: Path, entries: list[str] = TEST_LIST) -> Path:
    p = tmp_path / "legacy.txt"
    p.write_text("\n".join(entries) + "\n", encoding="utf-8")
    return p


def _guard(file_path: str, list_file: Path | None, script: Path | None = None) -> tuple[int, str]:
    script = script or GUARD
    args = ["bash", str(script)] + (["--legacy-list", str(list_file)] if list_file else [])
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path}})
    proc = subprocess.run(args, input=payload, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stderr


def _mini_repo(tmp_path: Path) -> Path:
    """迷你 repo：hook 之複本（repo 根由腳本位置推導）＋一個清單內之真實檔。"""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    shutil.copy(GUARD, root / "scripts" / "todofmt_write_guard.sh")
    (root / "docs").mkdir()
    (root / "docs" / "GAP2_MARGINAL_IC_TODO.md").write_text("x\n", encoding="utf-8")
    return root


# ── 判定邊界①–⑬（以參數傳入清單）──────────────────────────────────────────


def test_boundary_01_new_prose_todo_blocked(tmp_path: Path) -> None:
    rc, err = _guard("docs/X_TODO.md", _list_file(tmp_path))
    assert rc == 2 and "五類落點" in err, err


def test_boundary_02_editing_listed_todo_allowed(tmp_path: Path) -> None:
    assert _guard("docs/GAP2_MARGINAL_IC_TODO.md", _list_file(tmp_path))[0] == 0


def test_boundary_03_yaml_not_governed(tmp_path: Path) -> None:
    assert _guard("docs/X_TODO.yaml", _list_file(tmp_path))[0] == 0


def test_boundary_04_path_with_space_blocked(tmp_path: Path) -> None:
    assert _guard("docs/sub dir/X_TODO.md", _list_file(tmp_path))[0] == 2


@pytest.mark.parametrize("prefix", ["abs", "dot"])
def test_boundary_05_absolute_and_dot_prefix_normalized(tmp_path: Path, prefix: str) -> None:
    lf = _list_file(tmp_path)
    new = f"{REPO_ROOT}/docs/X_TODO.md" if prefix == "abs" else "./docs/X_TODO.md"
    old = f"{REPO_ROOT}/docs/GAP2_MARGINAL_IC_TODO.md" if prefix == "abs" else "./docs/GAP2_MARGINAL_IC_TODO.md"
    assert _guard(new, lf)[0] == 2
    assert _guard(old, lf)[0] == 0


def test_boundary_06_existing_or_staged_new_todo_still_blocked(tmp_path: Path) -> None:
    """已存在於工作區（例：已 git add 未 commit）之新散文 TODO 仍擋——判定不看 git 狀態。"""
    root = _mini_repo(tmp_path)
    (root / "docs" / "NEW_TODO.md").write_text("x\n", encoding="utf-8")
    rc, _ = _guard(str(root / "docs" / "NEW_TODO.md"), _list_file(tmp_path), root / "scripts" / "todofmt_write_guard.sh")
    assert rc == 2


def test_boundary_07_symlink_to_listed_file_allowed(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    (root / "docs" / "ALIAS_TODO.md").symlink_to(root / "docs" / "GAP2_MARGINAL_IC_TODO.md")
    rc, err = _guard(str(root / "docs" / "ALIAS_TODO.md"), _list_file(tmp_path), root / "scripts" / "todofmt_write_guard.sh")
    assert rc == 0, err


def test_boundary_08_case_variant_blocked(tmp_path: Path) -> None:
    assert _guard("Docs/X_Todo.md", _list_file(tmp_path))[0] == 2


def test_boundary_09_subdirectory_blocked(tmp_path: Path) -> None:
    assert _guard("docs/sub/X_TODO.md", _list_file(tmp_path))[0] == 2


def test_boundary_10_hardlink_alias_blocked(tmp_path: Path) -> None:
    root = _mini_repo(tmp_path)
    os.link(root / "docs" / "GAP2_MARGINAL_IC_TODO.md", root / "docs" / "HARD_TODO.md")
    rc, _ = _guard(str(root / "docs" / "HARD_TODO.md"), _list_file(tmp_path), root / "scripts" / "todofmt_write_guard.sh")
    assert rc == 2


def test_boundary_11_new_extension_file_blocked(tmp_path: Path) -> None:
    assert _guard("docs/NEWEPIC_TODO.D-001.md", _list_file(tmp_path))[0] == 2


def test_boundary_12_listed_extension_file_allowed(tmp_path: Path) -> None:
    assert _guard("docs/GAP3_EVENT_TODO.D-001.md", _list_file(tmp_path))[0] == 0


def test_boundary_13_listed_archived_todo_allowed(tmp_path: Path) -> None:
    assert _guard("docs/Archived/OLD_TODO.md", _list_file(tmp_path))[0] == 0


# ── ⑭–⑱ 與掛載、§P（L／X）────────────────────────────────────────────────


def _x_literal() -> list[str]:
    text = anchor.read_x("scripts/todofmt_write_guard.sh")
    assert text is not None, "X 版 hook 腳本不存在"
    return anchor.literal_block(text, LIST_BEGIN, LIST_BEGIN)


def test_boundary_14_production_call_uses_script_literal_only() -> None:
    src = GUARD.read_text(encoding="utf-8")
    reads = [ln.strip() for ln in src.splitlines() if re.search(r"\$\(cat\b", ln) and not ln.lstrip().startswith("#")]
    assert reads == ['_list="$(cat "${2}")"', '_payload="$(cat)"'], reads
    entry = _x_literal()[0]
    assert _guard(entry, None)[0] == 0, "生產呼叫未以腳本字面放行清單內之檔"


def test_boundary_15_literal_equals_l_tree_set() -> None:
    assert _x_literal() == anchor.legacy_todo_paths()


def test_boundary_16_late_new_todo_blocked_in_production() -> None:
    assert "docs/late_todo.md" not in _x_literal()
    assert _guard("docs/LATE_TODO.md", None)[0] == 2


def test_boundary_17_window_has_no_new_prose_todo() -> None:
    assert [p for p in anchor.window_additions() if anchor.is_legacy_todo_style(p)] == []


def _strip_generated(text: str) -> tuple[str, list[str]]:
    kept, markers, inside = [], [], False
    for ln in text.splitlines():
        m = _GEN_BLOCK.match(ln)
        if m:
            markers.append(ln)
            inside = m.group(1) == "BEGIN"
            kept.append(ln)
            continue
        if not inside:
            kept.append(ln)
    return "\n".join(kept), markers


def test_boundary_18_legacy_todo_content_unchanged_except_generated_blocks() -> None:
    lo = anchor.design_freeze_commit()
    changed = []
    for path in anchor._tree_paths(lo):
        if not anchor.is_legacy_todo_style(path):
            continue
        at_l = anchor.show(lo, path) or ""
        at_x = anchor.read_x(path)
        if at_x is None:
            changed.append(f"{path}：X 版不存在")
            continue
        (body_l, mk_l), (body_x, mk_x) = _strip_generated(at_l), _strip_generated(at_x)
        if mk_l != mk_x or body_l != body_x:
            changed.append(path)
    assert changed == [], changed


def test_hook_mounted_in_x_settings() -> None:
    assert anchor.hook_mounted(anchor.read_x(anchor.SETTINGS))


def _hook_pairs(settings_text: str | None) -> set[tuple[str, str, str]]:
    data = json.loads(settings_text or "{}")
    return {
        (event, entry.get("matcher") or "", h.get("command", ""))
        for event, entries in (data.get("hooks") or {}).items()
        for entry in entries
        for h in entry.get("hooks", [])
    }


def test_coverage_existing_hooks_subset_of_x() -> None:
    at_l = _hook_pairs(anchor.show(anchor.design_freeze_commit(), anchor.SETTINGS))
    at_x = _hook_pairs(anchor.read_x(anchor.SETTINGS))
    assert at_l <= at_x, sorted(at_l - at_x)


def _x_manifest() -> dict:
    text = anchor.read_x(anchor.MANIFEST)
    assert text is not None, "X 版本票 manifest 不存在"
    return json.loads(text)


def test_p_l_precedes_implementation_new_files() -> None:
    lo = anchor.design_freeze_commit()
    listed = anchor.manifest_paths(json.dumps(_x_manifest()))
    present = [p for p in (*listed, anchor.MANIFEST) if anchor.exists_at(lo, p)]
    assert present == [], present


def test_p_existing_touched_files_unchanged_between_a_and_l() -> None:
    lo, a = anchor.design_freeze_commit(), anchor.invariant_anchor_commit()
    touches = [
        p for p in _x_manifest()["batch_card"]["touches"]
        if p != anchor.SPEC and anchor.exists_at(lo, p)
    ]
    assert touches, "前提：本票 touches 中應有 L 已存在之既有檔"
    out = subprocess.run(["git", "log", "--format=%H", f"{a}..{lo}", "--", *touches],
                         cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert out == [], out


def test_mutation_dropping_list_membership_blocks_listed_edit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """移除「命中既有清單即放行」 ⇒ 編輯清單內之檔亦被擋（證邊界②之測試有鑑別力）。"""
    src = GUARD.read_text(encoding="utf-8")
    anchor_txt = '_in_list "${_norm}" && exit 0'
    assert src.count(anchor_txt) == 1
    # 前提：同位置之未改壞複本放行清單內之檔（排除「腳本因別的理由回 2」之假綠）
    orig = tmp_path / "orig_guard.sh"
    orig.write_text(src, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "GUARD", orig)
    assert _guard("docs/GAP2_MARGINAL_IC_TODO.md", _list_file(tmp_path))[0] == 0
    mutant = tmp_path / "mutant_guard.sh"
    mutant.write_text(src.replace(anchor_txt, ":"), encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "GUARD", mutant)
    rc, err = _guard("docs/GAP2_MARGINAL_IC_TODO.md", _list_file(tmp_path))
    assert rc == 2 and "五類落點" in err, err
