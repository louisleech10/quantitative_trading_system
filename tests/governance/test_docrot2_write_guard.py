"""DOCROT2 Task 2.1–2.4 — 活文件寫入守衛（scripts/live_doc_write_guard.sh）。

測什麼：`docs/DOCROT2_TODO.md` Task 2.1–2.4 驗證欄之 fixture 逐條 rc 對照，外加邊界。
fixture 形態：各測試於 tmp 建獨立 git repo，複製守衛、登記模組與生成器（判定碼唯一來源），
在其中執行；守衛以 cwd 之 git 根判定 repo，故不觸及本 repo 工作樹（同 Task 1.1 之具名偏離）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = ["_live_doc_registry.py", "live_doc_registry_check.sh", "_live_doc_write_guard.py",
           "live_doc_write_guard.sh", "gen_fact_key_blocks.sh", "governance_families.json"]
REAL_REGISTRY = json.loads((REPO / "scripts" / "live_doc_registry.json").read_text(encoding="utf-8"))
STATUS_ENUM = json.loads((REPO / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))["_schema"]["status_enum"]
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
COLS = ["序", "識別碼", "狀態", "權威路徑", "下一步"]

HANDOFF_OK = """# HANDOFF

## 現況

<!-- BEGIN GENERATED: handoff-current -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 01-001 | D2B | 進行中 | x | 做 D2B |
<!-- END GENERATED: handoff-current -->

## 待辦

<!-- BEGIN GENERATED: handoff-todo -->
| 序 | 識別碼 | 狀態 | 權威路徑 | 下一步 |
|---|---|---|---|---|
| 01-001 | D2B | 進行中 | x | 做 D2B |
<!-- END GENERATED: handoff-todo -->

## 坑

- 一般教訓 ANCHOR-PIT

## 進行中紀錄

<!-- HISTORY-BEGIN -->
<!-- ENTRY: B-63 -->
- 2026-09-15：B-63 → `docs/A_SPEC.md`
<!-- HISTORY-END -->
"""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV})


def _fact_keys() -> dict:
    return {
        "_schema": {
            "status_enum": STATUS_ENUM,
            "status_keys": ["st-a"],
            "status_scope": ["docs/"],
            "status_scope_grandfathered": ["docs/__none__.md"],
            "enforcement_completed_statuses": ["收案", "已落地", "已完成"],
            "docrot2_status_keys": ["d2-x"],
            "docrot2_status_values": ["未開工", "進行中", "部分完成", "待審", "停手", "狀態未確認", "已完成"],
        },
        "st-a": {"target": "docs/st.md", "columns": COLS,
                 "rows": [["010", "B-63", "部分完成", "x", "做"], ["020", "D2A", "已完成", "x", "—"]]},
        "d2-x": {"target": "docs/d2.md", "columns": COLS, "rows": [["010", "D2B", "進行中", "x", "做 D2B"]]},
        "handoff-current": {"target": "HANDOFF.md", "columns": COLS, "rows": []},
        "handoff-todo": {"target": "HANDOFF.md", "columns": COLS, "rows": []},
    }


def _repo(tmp_path: Path, files: dict, *, exact=(), flags: dict | None = None, commit: bool = True) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name in SCRIPTS:
        shutil.copy2(REPO / "scripts" / name, root / "scripts" / name)
    reg = json.loads(json.dumps(REAL_REGISTRY))
    reg["exact"] = [list(p) for p in exact]
    reg["prefix"] = [["docs/Archived/", "HIST"], ["docs/site/", "HIST"], ["templates/", "LIVE-CONTRACT"],
                     ["白話說明/", "LIVE-PLAIN"], ["白話說明/Archived/", "HIST"]]
    for cls, over in (flags or {}).items():
        reg["class_flags"][cls].update(over)
    (root / "scripts" / "live_doc_registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "scripts" / "fact_keys.json").write_text(json.dumps(_fact_keys(), ensure_ascii=False, indent=2), encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    if commit:
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", "base")
    return root


def _hook(root: Path, payload) -> subprocess.CompletedProcess:
    data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return subprocess.run(["bash", str(root / "scripts" / "live_doc_write_guard.sh")], cwd=str(root),
                          input=data, capture_output=True, text=True)


def _edit(root: Path, rel: str, old: str, new: str, replace_all: bool = False) -> dict:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(root / rel), "old_string": old,
                                                "new_string": new, "replace_all": replace_all}}


def _write(root: Path, rel: str, content: str) -> dict:
    return {"tool_name": "Write", "tool_input": {"file_path": str(root / rel), "content": content}}


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "scripts" / "live_doc_write_guard.sh"), *args], cwd=str(root),
                          capture_output=True, text=True)


SPEC = ("docs/A_SPEC.md", "LIVE-SPEC")
HANDOFF = ("HANDOFF.md", "LIVE-HANDOFF")
NO_ARCH = {"LIVE-SPEC": {"archaeology_check": False}}      # 隔離 Task 2.1：關閉 Task 2.2 旗標
NO_STATUS = {"LIVE-SPEC": {"new_line_status_check": False}}  # 隔離 Task 2.2


# ================================================================ Task 2.1 驗證欄


def test_handoff_edit_adds_id_with_status_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT\n- B-63 部分完成 待補"))
    assert r.returncode == 2 and "B-63" in r.stderr and "部分完成" in r.stderr, r.stderr


INSIDE = "# A\n\n正文\n\n<!-- HISTORY-BEGIN -->\nXYZ-SLOT\n<!-- HISTORY-END -->\n"
OUTSIDE = "# A\n\nXYZ-SLOT\n\n<!-- HISTORY-BEGIN -->\n<!-- HISTORY-END -->\n"


def test_same_new_string_old_string_inside_history_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": INSIDE}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "XYZ-SLOT", "D2B 進行中"))
    assert r.returncode == 0, r.stderr


def test_same_new_string_old_string_outside_history_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": OUTSIDE}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "XYZ-SLOT", "D2B 進行中"))
    assert r.returncode == 2 and "D2B" in r.stderr, r.stderr


def test_replace_all_true_two_occurrences_exit2(tmp_path):
    text = "# A\n\n<!-- HISTORY-BEGIN -->\nXYZ-SLOT\n<!-- HISTORY-END -->\n\nXYZ-SLOT\n"
    root = _repo(tmp_path, {"docs/A_SPEC.md": text}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "XYZ-SLOT", "D2B 進行中", replace_all=True))
    # 第二處（L7，歷史專區外）必報；第一處（L4，歷史專區內）必不報——只換第一處之實作兩者皆錯
    assert r.returncode == 2 and "L7" in r.stderr and "L4" not in r.stderr, r.stderr


@pytest.mark.parametrize("line", ["「B-63 部分完成」", "\"D2B\" 進行中", "`B-63`：部分完成"])
def test_quoted_id_with_status_exit2(tmp_path, line):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nANCHOR\n"}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "ANCHOR", f"ANCHOR\n{line}"))
    assert r.returncode == 2, r.stderr


def test_git_show_decoy_status_suffix_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nANCHOR\n"}, exact=[SPEC], flags=NO_ARCH)
    line = "樣本見 `git show 600c968b:HANDOFF.md`，其中 B-63 部分完成"
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "ANCHOR", f"ANCHOR\n{line}"))
    assert r.returncode == 2 and "B-63" in r.stderr, r.stderr


def test_stale_sample_in_fence_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nANCHOR\n"}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "ANCHOR", "ANCHOR\n```\nB-63 部分完成\n```"))
    assert r.returncode == 0, r.stderr


def test_edit_old_string_absent_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nANCHOR\n"}, exact=[SPEC])
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "NOT-THERE", "x"))
    assert r.returncode == 2 and "0 次" in r.stderr, r.stderr


def test_edit_old_string_nonunique_exit2(tmp_path):
    text = "# A\n\n<!-- HISTORY-BEGIN -->\nXYZ-SLOT\n<!-- HISTORY-END -->\n\nXYZ-SLOT\n"
    root = _repo(tmp_path, {"docs/A_SPEC.md": text}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "XYZ-SLOT", "一般文字"))
    assert r.returncode == 2 and "2 次" in r.stderr, r.stderr


# ---------------------------------------------------------------- Task 2.1 邊界


def test_write_new_file_all_lines_are_new_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/KEEP.md": "x\n"}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _write(root, "docs/A_SPEC.md", "# A\nD2B 進行中\n"))
    assert r.returncode == 2, r.stderr


def test_write_same_content_exit0(tmp_path):
    text = "# A\nD2B 進行中（既有行）\n"
    root = _repo(tmp_path, {"docs/A_SPEC.md": text}, exact=[SPEC], flags=NO_ARCH)
    assert _hook(root, _write(root, "docs/A_SPEC.md", text)).returncode == 0


def test_existing_status_line_new_line_clean_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nD2B 進行中（既有行）\nANCHOR\n"}, exact=[SPEC], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "ANCHOR", "ANCHOR\n一般新行"))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("raw", ["not json", "[]", json.dumps({"tool_name": "Edit", "tool_input": {}})])
def test_unparseable_payload_exit2(tmp_path, raw):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    assert _hook(root, raw).returncode == 2


@pytest.mark.parametrize("rel", ["scripts/x.py", "handoffs/x.md", "docs/UNREG.md"])
def test_out_of_scope_or_unregistered_exit0(tmp_path, rel):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    assert _hook(root, _write(root, rel, "D2B 進行中\n")).returncode == 0


def test_other_tool_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    assert _hook(root, {"tool_name": "Bash", "tool_input": {"command": "echo"}}).returncode == 0


def test_log_class_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/LOG.md": "# L\nANCHOR\n"}, exact=[("docs/LOG.md", "LOG")])
    r = _hook(root, _edit(root, "docs/LOG.md", "ANCHOR", "ANCHOR\nD2B 進行中 ~~舊~~ CODEX-R1-P1-01"))
    assert r.returncode == 0, r.stderr


def test_unclosed_generated_block_gives_no_exemption_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/st.md": "# S\nANCHOR\n"}, exact=[("docs/st.md", "LIVE-SPEC")], flags=NO_ARCH)
    r = _hook(root, _edit(root, "docs/st.md", "ANCHOR", "ANCHOR\n<!-- BEGIN GENERATED: st-a -->\nD2B 進行中"))
    assert r.returncode == 2, r.stderr


def test_block_of_key_not_targeting_file_gives_no_exemption_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\nANCHOR\n"}, exact=[SPEC], flags=NO_ARCH)
    fake = "ANCHOR\n<!-- BEGIN GENERATED: st-a -->\nD2B 進行中\n<!-- END GENERATED: st-a -->"
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "ANCHOR", fake))
    assert r.returncode == 2, r.stderr


def test_legal_generated_block_exempt_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/st.md": "# S\nANCHOR\n"}, exact=[("docs/st.md", "LIVE-SPEC")], flags=NO_ARCH)
    blk = "ANCHOR\n<!-- BEGIN GENERATED: st-a -->\n| 010 | D2B | 進行中 | x | 做 |\n<!-- END GENERATED: st-a -->"
    assert _hook(root, _edit(root, "docs/st.md", "ANCHOR", blk)).returncode == 0


# ================================================================ Task 2.2 驗證欄

SPEC_HIST = "# A\n\n正文 ANCHOR\n\n<!-- HISTORY-BEGIN -->\n- 2026-09-14：v1 → `docs/A_SPEC.md`\n<!-- HISTORY-END -->\n"


def test_spec_adds_strikethrough_outside_history_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "正文 ANCHOR", "正文 ~~舊寫法~~ 新寫法"))
    assert r.returncode == 2 and "~~" in r.stderr, r.stderr


def test_spec_adds_finding_id_outside_history_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "正文 ANCHOR", "正文（CODEX-R12-P1-03 修）"))
    assert r.returncode == 2 and "CODEX-R12-P1-03" in r.stderr, r.stderr


@pytest.mark.parametrize("lit", REAL_REGISTRY["archaeology_literals"])
def test_spec_adds_archaeology_literal_outside_history_exit2(tmp_path, lit):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "正文 ANCHOR", f"正文 {lit}"))
    assert r.returncode == 2, r.stderr


def _hist_add(root: Path, line: str) -> dict:
    return _edit(root, "docs/A_SPEC.md", "- 2026-09-14：v1 → `docs/A_SPEC.md`",
                 "- 2026-09-14：v1 → `docs/A_SPEC.md`\n" + line)


def test_spec_history_adds_pointer_line_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    assert _hook(root, _hist_add(root, "- 2026-09-15：v2 → `docs/A_SPEC.md`")).returncode == 0
    sha = _git(root, "rev-parse", "HEAD").stdout.strip()
    assert _hook(root, _hist_add(root, f"- 2026-09-15：B-63 → commit `{sha[:8]}`")).returncode == 0


def test_spec_history_adds_copied_old_text_exit2(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    r = _hook(root, _hist_add(root, "v1 原本規定：每批三家審碼，現改兩家"))
    assert r.returncode == 2 and "指標文法" in r.stderr, r.stderr


@pytest.mark.parametrize("line", ["- 2026-09-15：舊版說明 → `docs/A_SPEC.md`", "- 2026-09-15：NOT-AN-ID → `docs/A_SPEC.md`"])
def test_history_pointer_free_text_subject_exit2(tmp_path, line):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    assert _hook(root, _hist_add(root, line)).returncode == 2


@pytest.mark.parametrize("line", ["- 2026-09-15：v2 → `docs/MISSING.md`", "- 2026-09-15：v2 → commit `deadbeefdeadbeef`",
                                  "- 2026-09-15：v2 → `../outside.md`"])
def test_history_pointer_target_missing_exit2(tmp_path, line):
    root = _repo(tmp_path, {"docs/A_SPEC.md": SPEC_HIST}, exact=[SPEC], flags=NO_STATUS)
    assert _hook(root, _hist_add(root, line)).returncode == 2


def test_existing_history_pointer_target_absent_unrelated_edit_staged_rc0(tmp_path):
    text = SPEC_HIST.replace("`docs/A_SPEC.md`", "`handoffs/gone.md`")
    root = _repo(tmp_path, {"docs/A_SPEC.md": text}, exact=[SPEC])
    (root / "docs" / "A_SPEC.md").write_text(text.replace("正文 ANCHOR", "正文 改寫"), encoding="utf-8")
    _git(root, "add", "docs/A_SPEC.md")
    r = _run(root, "--staged")
    assert r.returncode == 0, r.stderr


def test_todo_unrelated_edit_legacy_strikethrough_elsewhere_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_TODO.md": "# T\n~~既有刪除線~~\nANCHOR\n"}, exact=[("docs/A_TODO.md", "LIVE-SPEC")])
    r = _hook(root, _edit(root, "docs/A_TODO.md", "ANCHOR", "ANCHOR 改寫"))
    assert r.returncode == 0, r.stderr


def test_body_paragraph_deletion_exit0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n~~舊~~ CODEX-R1-P1-01\nD2B 進行中\n"}, exact=[SPEC])
    r = _hook(root, _edit(root, "docs/A_SPEC.md", "~~舊~~ CODEX-R1-P1-01\nD2B 進行中\n", ""))
    assert r.returncode == 0, r.stderr


@pytest.mark.parametrize("flag_on, rc", [(True, 2), (False, 0)])
def test_templates_follow_class_flag(tmp_path, flag_on, rc):
    root = _repo(tmp_path, {"templates/T.md": "# T\nANCHOR\n"},
                 flags={"LIVE-CONTRACT": {"archaeology_check": flag_on}})
    assert _hook(root, _edit(root, "templates/T.md", "ANCHOR", "ANCHOR ~~舊~~")).returncode == rc


# ================================================================ Task 2.3 驗證欄


def test_bash_redirect_added_status_line_staged_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    with open(root / "docs" / "A_SPEC.md", "a", encoding="utf-8") as fh:
        fh.write("D2B 進行中\n")
    _git(root, "add", "docs/A_SPEC.md")
    r = _run(root, "--staged")
    assert r.returncode == 1 and "D2B" in r.stderr, r.stderr


def test_clean_staged_diff_rc0(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    (root / "docs" / "A_SPEC.md").write_text("# A\n一般新行\n", encoding="utf-8")
    _git(root, "add", "docs/A_SPEC.md")
    assert _run(root, "--staged").returncode == 0


def test_new_unregistered_md_staged_registry_rc1(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    (root / "docs" / "NEW.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "docs/NEW.md")
    r = subprocess.run(["bash", str(root / "scripts" / "live_doc_registry_check.sh"), "--staged"], cwd=str(root),
                       capture_output=True, text=True)
    assert r.returncode == 1 and "docs/NEW.md" in r.stderr, r.stderr


def test_staged_judges_index_not_worktree(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    (root / "docs" / "A_SPEC.md").write_text("# A\nD2B 進行中\n", encoding="utf-8")
    _git(root, "add", "docs/A_SPEC.md")
    (root / "docs" / "A_SPEC.md").write_text("# A\n", encoding="utf-8")          # 工作樹已乾淨，index 仍髒
    assert _run(root, "--staged").returncode == 1
    _git(root, "add", "docs/A_SPEC.md")
    (root / "docs" / "A_SPEC.md").write_text("# A\nD2B 進行中\n", encoding="utf-8")  # 反向：index 乾淨
    assert _run(root, "--staged").returncode == 0


def test_staged_deleted_file_not_judged(tmp_path):
    root = _repo(tmp_path, {"docs/A_SPEC.md": "# A\n"}, exact=[SPEC])
    _git(root, "rm", "-q", "docs/A_SPEC.md")
    assert _run(root, "--staged").returncode == 0


def test_handoff_tree_with_completed_entry_rc1(tmp_path):
    text = HANDOFF_OK.replace("<!-- ENTRY: B-63 -->", "<!-- ENTRY: D2A -->").replace("：B-63 →", "：D2A →")
    root = _repo(tmp_path, {"HANDOFF.md": text, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _run(root, "--tree", "HEAD", "--path", "HANDOFF.md")
    assert r.returncode == 1 and "D2A" in r.stderr, r.stderr


def test_pre_commit_calls_both_staged_guards():
    text = (REPO / "scripts" / "git_hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "bash scripts/live_doc_write_guard.sh --staged" in text
    assert "bash scripts/live_doc_registry_check.sh --staged" in text


# ================================================================ Task 2.4 驗證欄


def test_handoff_ok_baseline_exit0(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT 補充"))
    assert r.returncode == 0, r.stderr
    assert _run(root, "--tree", "HEAD", "--path", "HANDOFF.md").returncode == 0


def test_handoff_current_section_handwritten_line_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "## 現況\n", "## 現況\n手寫一句現況\n"))
    assert r.returncode == 2 and "只准生成區塊" in r.stderr, r.stderr


def test_handoff_unknown_h2_section_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "## 坑\n", "## 待辦分流\n\n## 坑\n"))
    assert r.returncode == 2 and "待辦分流" in r.stderr, r.stderr


def test_handoff_todo_row_missing_next_action_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    old = "| 01-001 | D2B | 進行中 | x | 做 D2B |\n<!-- END GENERATED: handoff-todo -->"
    new = "| 01-001 | D2B | 進行中 | x |  |\n<!-- END GENERATED: handoff-todo -->"
    r = _hook(root, _edit(root, "HANDOFF.md", old, new))
    assert r.returncode == 2 and "下一步」為空" in r.stderr, r.stderr


def test_handoff_history_line_before_first_marker_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "<!-- HISTORY-BEGIN -->\n<!-- ENTRY: B-63 -->",
                          "<!-- HISTORY-BEGIN -->\n- 2026-09-15：v2 → `docs/A_SPEC.md`\n<!-- ENTRY: B-63 -->"))
    assert r.returncode == 2 and "首個條目標記前" in r.stderr, r.stderr


def test_handoff_entry_marker_unregistered_id_exit2(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    r = _hook(root, _edit(root, "HANDOFF.md", "<!-- ENTRY: B-63 -->", "<!-- ENTRY: B-63,NOPE-1 -->"))
    assert r.returncode == 2 and "NOPE-1" in r.stderr, r.stderr


def _stage_handoff(root: Path, text: str) -> None:
    (root / "HANDOFF.md").write_text(text, encoding="utf-8")
    _git(root, "add", "HANDOFF.md")


def test_handoff_entry_any_id_completed_staged_rc1(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    _stage_handoff(root, HANDOFF_OK.replace("<!-- ENTRY: B-63 -->", "<!-- ENTRY: B-63,D2A -->"))
    r = _run(root, "--staged")
    assert r.returncode == 1 and "D2A" in r.stderr, r.stderr


def test_handoff_entry_pointer_subject_completed_staged_rc1(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    _stage_handoff(root, HANDOFF_OK.replace("：B-63 → `docs/A_SPEC.md`", "：D2A → `docs/A_SPEC.md`"))
    assert _run(root, "--staged").returncode == 1


def test_handoff_entry_all_ids_open_staged_rc0(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    _stage_handoff(root, HANDOFF_OK.replace("<!-- ENTRY: B-63 -->", "<!-- ENTRY: B-63,D2B -->"))
    r = _run(root, "--staged")
    assert r.returncode == 0, r.stderr


def test_handoff_entry_completed_and_moved_out_same_commit_rc0(tmp_path):
    text = HANDOFF_OK.replace("<!-- ENTRY: B-63 -->", "<!-- ENTRY: B-63 -->")
    root = _repo(tmp_path, {"HANDOFF.md": text, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    fk = _fact_keys()
    fk["st-a"]["rows"][0][2] = "已完成"                                   # B-63 轉完成
    (root / "scripts" / "fact_keys.json").write_text(json.dumps(fk, ensure_ascii=False), encoding="utf-8")
    moved = text.replace("<!-- ENTRY: B-63 -->\n- 2026-09-15：B-63 → `docs/A_SPEC.md`\n", "<!-- ENTRY: D2B -->\n")
    _stage_handoff(root, moved)
    _git(root, "add", "scripts/fact_keys.json")
    r = _run(root, "--staged")
    assert r.returncode == 0, r.stderr


def test_handoff_pit_referencing_finished_work_not_lifecycle(tmp_path):
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    _stage_handoff(root, HANDOFF_OK.replace("- 一般教訓 ANCHOR-PIT", "- 一般教訓 ANCHOR-PIT（D2A 時學到）"))
    r = _run(root, "--staged")
    assert r.returncode == 0, r.stderr


def test_efcafc63_handoff_status_lines_in_current_section_staged_rc1(tmp_path):
    old = subprocess.run(["git", "-C", str(REPO), "show", "efcafc63:HANDOFF.md"], capture_output=True,
                         text=True, check=True).stdout
    root = _repo(tmp_path, {"HANDOFF.md": HANDOFF_OK, "docs/A_SPEC.md": "# A\n"}, exact=[HANDOFF, SPEC])
    _stage_handoff(root, old)
    r = _run(root, "--staged")
    assert r.returncode == 1 and "只准生成區塊" in r.stderr, r.stderr


def test_real_handoff_conforms_and_inject_carries_generated_blocks():
    r = subprocess.run(["bash", str(REPO / "scripts" / "live_doc_write_guard.sh"), "--tree", "HEAD", "--path", "HANDOFF.md"],
                       cwd=str(REPO), capture_output=True, text=True)
    work = (REPO / "HANDOFF.md").read_text(encoding="utf-8")
    assert "<!-- BEGIN GENERATED: handoff-current -->" in work and "<!-- BEGIN GENERATED: handoff-todo -->" in work
    inj = subprocess.run(["bash", str(REPO / "scripts" / "inject_handoff.sh")], cwd=str(REPO), capture_output=True, text=True)
    msg = json.loads(inj.stdout)["systemMessage"]
    assert "BEGIN GENERATED: handoff-current" in msg and "BEGIN GENERATED: handoff-todo" in msg
    assert r.returncode in (0, 1)       # HEAD 版於遷移 commit 前可能未合規；遷移後由 --staged 與下一條承接


def test_real_worktree_handoff_grammar_rc0():
    """工作樹之 HANDOFF.md 以 hook 模式之「寫入與現檔相同」判定——文法全文判定仍執行。"""
    text = (REPO / "HANDOFF.md").read_text(encoding="utf-8")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(REPO / "HANDOFF.md"), "content": text + "\n"}}
    r = subprocess.run(["bash", str(REPO / "scripts" / "live_doc_write_guard.sh")], cwd=str(REPO),
                       input=json.dumps(payload, ensure_ascii=False), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
