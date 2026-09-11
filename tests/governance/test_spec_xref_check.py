"""spec_xref_check.sh — 「改一處漏一處」閘之可證偽測試。

每條對應腳本檔頭一個判準；含一條 mutation（把判準關掉 ⇒ 測試必紅）。
只跑本檔：pytest tests/governance/test_spec_xref_check.py -q
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "spec_xref_check.sh"


def _run(old: str, new: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    o = tmp_path / "old.md"
    n = tmp_path / "new.md"
    o.write_text(old, encoding="utf-8")
    n.write_text(new, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), "--files", str(o), str(n)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


OLD = (
    "- 改法：視窗用 `origin/main..HEAD` 取聯集。\n"
    "- 邊界：首次 push 時 `origin/main..HEAD` 為空。\n"
    "- 其他：`unrelated_token_x` 不動。\n"
)


def test_dropped_token_with_untagged_residue_fails(tmp_path: Path) -> None:
    """改了改法那行、邊界那行漏改且沒標版本 ⇒ rc=1 並指名行號。"""
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "`origin/main..HEAD` @L2" in r.stdout


def test_residue_tagged_with_version_passes(tmp_path: Path) -> None:
    """同一殘留行標了 v3 ⇒ 視為歷史敘述，rc=0（對照組）。"""
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    new = new.replace("首次 push 時 `origin/main..HEAD` 為空", "（v3 曾用 `origin/main..HEAD`，首次 push 為空）")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_all_references_synced_passes(tmp_path: Path) -> None:
    """兩處都改掉 ⇒ rc=0。"""
    new = OLD.replace("`origin/main..HEAD`", "`audit 持續視窗`")
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_token_still_in_added_lines_is_not_dropped(tmp_path: Path) -> None:
    """token 只是被搬到另一行（added 行仍含它）⇒ 不算被拿掉，rc=0。"""
    new = OLD.replace(
        "- 改法：視窗用 `origin/main..HEAD` 取聯集。",
        "- 改法：取聯集，範圍＝`origin/main..HEAD`（維持）。",
    )
    r = _run(OLD, new, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_unchanged_file_passes(tmp_path: Path) -> None:
    r = _run(OLD, OLD, tmp_path)
    assert r.returncode == 0


def test_mutation_disabling_check_turns_red(tmp_path: Path) -> None:
    """mutation：把違規判準改成永不成立 ⇒ 第一條測試必須翻紅（證明測試不是廉價綠燈）。"""
    src = SCRIPT.read_text(encoding="utf-8")
    mutated = src.replace("if t in line and not ver_re.search(line):", "if False:")
    assert mutated != src
    m = tmp_path / "mutated.sh"
    m.write_text(mutated, encoding="utf-8")
    new = OLD.replace("視窗用 `origin/main..HEAD` 取聯集", "視窗讀 audit 持續視窗取聯集")
    o = tmp_path / "o.md"; n = tmp_path / "n.md"
    o.write_text(OLD, encoding="utf-8"); n.write_text(new, encoding="utf-8")
    r = subprocess.run(["bash", str(m), "--files", str(o), str(n)], cwd=ROOT,
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, "mutation 後仍擋 ⇒ 測試沒在測判準"


SYNTH = (
    "# Reconcile — s\n\n## 群集 / 處置\n\n"
    "| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n"
    "| **X1 `old_window_range` 可被繞** | P1 | GROK-R2-P0-01 | **採納**。改讀 `audit_persistent_window`；見 `GROK-R2-P0-01`。 |\n\n"
    "## 附錄：findings 逐字保留\n\n## GROK-R2-P0-01\n**斷言**: `never_in_spec_token` 之類。\n"
)


def _run_synth(synth: str, target: str, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    s = tmp_path / "synth.md"; t = tmp_path / "SPEC.md"
    s.write_text(synth, encoding="utf-8"); t.write_text(target, encoding="utf-8")
    return subprocess.run(["bash", str(SCRIPT), "--synth", str(s), str(t)], cwd=ROOT,
                          capture_output=True, text=True, check=False)


def test_synth_disposition_token_missing_in_target_fails(tmp_path: Path) -> None:
    """synth 處置欄說改成 `audit_persistent_window`，SPEC 沒有 ⇒ rc=1 並指名。"""
    r = _run_synth(SYNTH, "- 改法：視窗用 `origin/main..HEAD`。\n", tmp_path)
    assert r.returncode == 1, r.stdout
    assert "`audit_persistent_window`" in r.stdout


def test_synth_disposition_token_present_passes(tmp_path: Path) -> None:
    r = _run_synth(SYNTH, "- 改法：視窗讀 `audit_persistent_window`。\n", tmp_path)
    assert r.returncode == 0, r.stdout


def test_synth_ignores_finding_ids_and_cluster_column_and_appendix(tmp_path: Path) -> None:
    """群集欄的 `old_window_range`、附錄的 `never_in_spec_token`、ID 都不是處置概念 ⇒ 不要求在 SPEC。"""
    r = _run_synth(SYNTH, "- 改法：視窗讀 `audit_persistent_window`。\n", tmp_path)
    assert r.returncode == 0
    assert "old_window_range" not in r.stdout and "never_in_spec_token" not in r.stdout


def test_synth_skips_evidence_commands_memory_names_and_line_refs(tmp_path: Path) -> None:
    """處置欄裡的實跑指令／記憶檔名／行號引用不是概念 ⇒ 不要求在 SPEC。"""
    synth = SYNTH.replace(
        "見 `GROK-R2-P0-01`。",
        "見 `GROK-R2-P0-01`；主委實跑 `git remote | wc -l`、`sed -n '202p' x.sh`；記憶 `feedback_cross_reference_sync`；碼證 `gate.sh:791-798`。",
    )
    r = _run_synth(synth, "- 改法：視窗讀 `audit_persistent_window`。\n", tmp_path)
    assert r.returncode == 0, r.stdout


HOOK = ROOT / "scripts" / "spec_xref_hook.sh"


def test_hook_fires_on_handoffs_file_declared_as_target(tmp_path: Path) -> None:
    """偵察稿在 handoffs/ 而非 docs/——只要某份 synth 宣告它為修訂標的，寫它就要驗。"""
    import os
    rd = ROOT / "handoffs" / "reconcile" / "zz-xreftest-x-consult-r1"
    rd.mkdir(parents=True, exist_ok=True)
    recon = ROOT / "handoffs" / "zz-xreftest-RECON-claude.md"
    try:
        (rd / "synth.md").write_text(
            "## 群集 / 處置\n\n**修訂標的**：handoffs/zz-xreftest-RECON-claude.md\n\n"
            "| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n"
            "| V1 | P1 | GROK-R1-P1-01 | 採納，改成 `concept_only_in_synth` |\n\n## 附錄\n\n## GROK-R1-P1-01\n**斷言**: x\n",
            encoding="utf-8")
        recon.write_text("# recon\n\n- 沒有那個概念。\n", encoding="utf-8")
        env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1", SPEC_XREF_HOOK_TARGET="handoffs/zz-xreftest-RECON-claude.md")
        r = subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        assert r.returncode == 2 and "concept_only_in_synth" in r.stderr, r.stdout + r.stderr  # hook 理由走 stderr
        recon.write_text("# recon\n\n- 改讀 `concept_only_in_synth`。\n", encoding="utf-8")
        r = subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        assert r.returncode == 0, r.stdout + r.stderr
    finally:
        recon.unlink(missing_ok=True)
        (rd / "synth.md").unlink(missing_ok=True)
        rd.rmdir()


def test_hook_noop_on_undeclared_handoffs_file() -> None:
    import os
    env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1", SPEC_XREF_HOOK_TARGET="HANDOFF.md")
    r = subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0 and r.stdout == ""


@pytest.mark.parametrize("args", [["--bogus"], ["--files", "only_one"], ["--synth", "a"]])
def test_usage_error_rc2(args: list[str]) -> None:
    r = subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 2
