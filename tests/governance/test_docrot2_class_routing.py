"""DOCROT2 Task 2.5 — 既有檢查依類別適用、宣稱與規則同步、掛載。

測什麼：`docs/DOCROT2_TODO.md` Task 2.5 驗證欄逐條，外加掛載與登記表對證。
fixture 形態：tmp 內建獨立 git repo 並複製受測腳本（同 Task 1.1 之具名偏離），不觸及本 repo 工作樹。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
REAL_REGISTRY = json.loads((REPO / "scripts" / "live_doc_registry.json").read_text(encoding="utf-8"))
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
XREF_SCRIPTS = ["spec_xref_hook.sh", "spec_xref_check.sh", "_live_doc_registry.py", "live_doc_registry_check.sh"]
PLAIN_SCRIPTS = ["plain_docs_sync_check.sh", "_live_doc_registry.py", "live_doc_registry_check.sh"]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, env={**os.environ, **GIT_ENV})


def _repo(tmp_path: Path, scripts, files: dict, *, exact=(), prefix=None) -> Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for name in scripts:
        shutil.copy2(REPO / "scripts" / name, root / "scripts" / name)
    reg = json.loads(json.dumps(REAL_REGISTRY))
    reg["exact"] = [list(p) for p in exact]
    reg["prefix"] = prefix if prefix is not None else [
        ["docs/Archived/", "HIST"], ["docs/site/", "HIST"], ["templates/", "LIVE-CONTRACT"],
        ["白話說明/", "LIVE-PLAIN"], ["白話說明/Archived/", "HIST"]]
    (root / "scripts" / "live_doc_registry.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def _xref_hook(root: Path, rel: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "GOVERNANCE_TEST_HARNESS": "1", "SPEC_XREF_HOOK_TARGET": rel}
    return subprocess.run(["bash", str(root / "scripts" / "spec_xref_hook.sh")], cwd=str(root),
                          capture_output=True, text=True, env=env)


BEFORE = "# H\n\n## 現況\n\n- `CONCEPT_ALPHA` 之現況描述\n\n## 坑\n\n- 參考 `CONCEPT_ALPHA` 的教訓\n"
AFTER = "# H\n\n## 現況\n\n## 坑\n\n- 參考 `CONCEPT_ALPHA` 的教訓\n"
SYNTH = "# Reconcile\n\n**修訂標的**：HANDOFF.md\n\n| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n\n## 附錄\n"


@pytest.mark.parametrize("cls, rc", [("LIVE-HANDOFF", 0), ("LIVE-SPEC", 2)])
def test_handoff_remove_current_lines_history_keeps_concept(tmp_path, cls, rc):
    """交接檔改寫現況：LIVE-HANDOFF 不做概念移除檢查（rc=0）；同一內容若登記為 LIVE-SPEC 則照舊擋（rc=2）。"""
    root = _repo(tmp_path, XREF_SCRIPTS, {"HANDOFF.md": BEFORE, "handoffs/reconcile/r1/synth.md": SYNTH},
                 exact=[("HANDOFF.md", cls)])
    (root / "HANDOFF.md").write_text(AFTER, encoding="utf-8")
    r = _xref_hook(root, "HANDOFF.md")
    assert r.returncode == rc, r.stdout + r.stderr


def test_spec_remove_concept_live_reference_remains_rc2(tmp_path):
    before = "# S\n\n- `CONCEPT_BETA` 規定甲\n- 另見 `CONCEPT_BETA`\n"
    root = _repo(tmp_path, XREF_SCRIPTS, {"docs/X_SPEC.md": before}, exact=[("docs/X_SPEC.md", "LIVE-SPEC")])
    (root / "docs" / "X_SPEC.md").write_text("# S\n\n- 另見 `CONCEPT_BETA`\n", encoding="utf-8")
    r = _xref_hook(root, "docs/X_SPEC.md")
    assert r.returncode == 2 and "CONCEPT_BETA" in r.stderr, r.stdout + r.stderr


def test_unregistered_spec_path_behavior_unchanged_rc2(tmp_path):
    before = "# S\n\n- `CONCEPT_GAMMA` 規定甲\n- 另見 `CONCEPT_GAMMA`\n"
    root = _repo(tmp_path, XREF_SCRIPTS, {"docs/Y_SPEC.md": before})
    (root / "docs" / "Y_SPEC.md").write_text("# S\n\n- 另見 `CONCEPT_GAMMA`\n", encoding="utf-8")
    assert _xref_hook(root, "docs/Y_SPEC.md").returncode == 2


def _plain(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(root / "scripts" / "plain_docs_sync_check.sh"), *args], cwd=str(root),
                          capture_output=True, text=True)


NO_PLAIN_PREFIX = [["docs/Archived/", "HIST"], ["templates/", "LIVE-CONTRACT"]]


def test_new_unregistered_plain_doc_rc_nonzero(tmp_path):
    root = _repo(tmp_path, PLAIN_SCRIPTS, {"白話說明/新看板.md": "# 新看板\n"}, prefix=NO_PLAIN_PREFIX)
    r = _plain(root)
    assert r.returncode != 0 and "未登記" in r.stderr, r.stdout + r.stderr


def test_registered_plain_doc_not_reported_unregistered(tmp_path):
    root = _repo(tmp_path, PLAIN_SCRIPTS, {"白話說明/新看板.md": "# 新看板\n"})
    r = _plain(root)
    assert "未登記" not in r.stderr, r.stderr


def test_new_unregistered_plain_doc_staged_rc1(tmp_path):
    root = _repo(tmp_path, PLAIN_SCRIPTS, {"docs/KEEP.md": "x\n"}, prefix=NO_PLAIN_PREFIX)
    (root / "白話說明").mkdir()
    (root / "白話說明" / "新看板.md").write_text("# 新看板\n", encoding="utf-8")
    _git(root, "add", "-A")
    r = _plain(root, "--staged")
    assert r.returncode == 1 and "未登記" in r.stderr, r.stdout + r.stderr


def test_claude_md_and_precompact_have_no_handoff_line_limit():
    assert "30 行" not in (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert "30 行" not in (REPO / ".claude" / "settings.json").read_text(encoding="utf-8")


def test_settings_mounts_write_guard_on_pretooluse_edit_write():
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    hits = [h for e in settings["hooks"]["PreToolUse"] if e.get("matcher") == "Edit|Write"
            for h in e.get("hooks", []) if h.get("command") == "bash scripts/live_doc_write_guard.sh"]
    assert len(hits) == 1


def test_enforcement_registry_lists_b63_gates_and_docrot_claim_scope():
    fk = json.loads((REPO / "scripts" / "fact_keys.json").read_text(encoding="utf-8"))
    rows = [r for r in fk["governance-enforcement"]["rows"] if r[1] == "B-63"]
    mounts = {r[2] for r in rows}
    assert "PreToolUse:Edit,Write:scripts/live_doc_write_guard.sh" in mounts
    assert "PostToolUse:Edit,Write:scripts/spec_xref_hook.sh" in mounts
    assert any("live_doc_write_guard.sh --staged" in r[4] for r in rows)
    for task in ("1.1–1.3", "1.4、1.6", "1.5", "1.7", "1.8"):
        assert any(f"DOCROT Task {task}" in r[4] for r in rows), task
    claim = [r[4] for r in rows if "DOCROT Task 1.1–1.3" in r[4]][0]
    assert "不涵蓋交接檔" in claim


def test_real_tree_generator_check_rc0():
    r = subprocess.run(["bash", str(REPO / "scripts" / "gen_fact_key_blocks.sh"), "--check"], cwd=str(REPO),
                       capture_output=True, text=True, env={k: v for k, v in os.environ.items() if k != "GOVB1_FACTKEY_ROOT"})
    assert r.returncode == 0, r.stderr
