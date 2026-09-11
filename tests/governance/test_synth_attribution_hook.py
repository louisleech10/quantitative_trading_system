"""synth_attribution_hook.sh — 收斂檔產出端閘之可證偽測試（只跑本檔）。
Task 4.1 起 hook 為 scripts/_synth_attr.py 之「寫入時子集」包裝；判準測試主體在 test_verdictgate_p4.py。"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "scripts" / "synth_attribution_hook.sh"
MOD = ROOT / "scripts" / "_synth_attr.py"

SYNTH_OK = (
    "# Reconcile — s\n\n## 群集 / 處置\n\n**修訂標的**：docs/VERDICTGATE_SPEC.md\n\n"
    "| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n"
    "| X1「斷言甲」「斷言乙」 | P1 | GROK-R2-P0-01、CODEX-R2-P1-03 | 採納 |\n\n"
    "## 附錄\n\n## GROK-R2-P0-01\n**斷言**: 斷言甲\n## CODEX-R2-P1-03\n**斷言**: 斷言乙\n"
)


def _run(body: str, session: str, tmp_path: Path, env_extra: dict | None = None) -> subprocess.CompletedProcess[str]:
    real = ROOT / "handoffs" / "reconcile" / f"zz-hooktest-{session}"
    real.mkdir(parents=True, exist_ok=True)
    (real / "synth.md").write_text(body, encoding="utf-8")
    try:
        env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1",
                   SYNTH_HOOK_TARGET=f"handoffs/reconcile/zz-hooktest-{session}/synth.md", **(env_extra or {}))
        return subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    finally:
        (real / "synth.md").unlink(missing_ok=True)
        real.rmdir()


def test_all_ids_in_table_and_target_declared_passes(tmp_path: Path) -> None:
    r = _run(SYNTH_OK, "20260911-t-x-review-r1", tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr


def test_missing_id_in_table_blocks(tmp_path: Path) -> None:
    body = SYNTH_OK.replace("、CODEX-R2-P1-03", "")
    r = _run(body, "20260911-t-x-review-r1", tmp_path)
    assert r.returncode == 2
    assert "CODEX-R2-P1-03" in r.stderr  # 阻塞理由走 stderr（harness 只回灌 stderr）


def test_x_layer_without_target_blocks(tmp_path: Path) -> None:
    body = SYNTH_OK.replace("**修訂標的**：docs/VERDICTGATE_SPEC.md\n\n", "")
    r = _run(body, "20260911-t-x-consult-r1", tmp_path)
    assert r.returncode == 2
    assert "修訂標的" in r.stderr


def test_b_layer_without_target_passes(tmp_path: Path) -> None:
    """程式碼審查層（-b1-）不要求修訂標的。"""
    body = SYNTH_OK.replace("**修訂標的**：docs/VERDICTGATE_SPEC.md\n\n", "")
    r = _run(body, "20260911-t-b1-review-r1", tmp_path)
    assert r.returncode == 0, r.stdout


def test_skeleton_placeholder_with_ids_blocks(tmp_path: Path) -> None:
    body = SYNTH_OK.replace("| X1「斷言甲」「斷言乙」 | P1 | GROK-R2-P0-01、CODEX-R2-P1-03 | 採納 |",
                            "（待填）\n| X1「斷言甲」「斷言乙」 | P1 | GROK-R2-P0-01、CODEX-R2-P1-03 | 採納 |")
    r = _run(body, "20260911-t-x-review-r1", tmp_path)
    assert r.returncode == 2
    assert "待填" in r.stderr


def test_non_synth_path_is_noop() -> None:
    env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1", SYNTH_HOOK_TARGET="HANDOFF.md")
    r = subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0 and r.stdout == ""


def test_mutation_disabling_id_check_turns_red(tmp_path: Path) -> None:
    """把共用模組的 check_ids 關掉 ⇒ hook 對掉項不再擋（證明 hook 真的在用該判準）。"""
    src = MOD.read_text(encoding="utf-8")
    mutated = src.replace("miss = [f.id for f in doc.findings if not rows_for(doc, f.id)]", "miss = []")
    assert mutated != src
    m = tmp_path / "_synth_attr_mut.py"; m.write_text(mutated, encoding="utf-8")
    r = _run(SYNTH_OK.replace("、CODEX-R2-P1-03", ""), "mut-x-review-r1", tmp_path, {"SYNTH_ATTR_MODULE": str(m)})
    assert r.returncode == 0, "mutation 後仍擋 ⇒ 測試沒在測判準"
