"""VERDICTGATE B4（Task 4.1）— 群集歸戶閘；每條 SPEC ASSERT 對應一個 test，hook 與閘同一模組。

只跑本檔：venv/bin/python -m pytest tests/governance/test_verdictgate_p4.py -q
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts" / "reconcile_cluster_attribution_check.sh"
HOOK = ROOT / "scripts" / "synth_attribution_hook.sh"
MOD = ROOT / "scripts" / "_synth_attr.py"

_spec = importlib.util.spec_from_file_location("_synth_attr", MOD)
sa = importlib.util.module_from_spec(_spec); assert _spec.loader
sys.modules["_synth_attr"] = sa                     # py3.9 dataclasses 解析字串註解時要在 sys.modules 找得到
_spec.loader.exec_module(sa)                          # type: ignore[union-attr]
VALUES = sa.load_values(str(ROOT / "scripts" / "governance_verdicts.json"))

A1 = "helper 同批只留最早者，違反 SPEC 字面單值規定。"      # >20 字；去空白後前 20 字＝「helper同批只留最早者，違反SPEC」
A2 = "短斷言"                                                                  # <20 字 ⇒ 引用全文
Q1 = sa.nfc_strip(A1)[:20]


def _synth(row4: str = "採納", *, quote1: str = A1, quote2: str = A2, target: str = "docs/VERDICTGATE_SPEC.md", extra_rows: str = "") -> str:
    return (
        "# Reconcile — s\n\n## 群集 / 處置\n\n"
        + (f"**修訂標的**：{target}\n\n" if target else "")
        + "| 群集 | 嚴重度 | 來源 ID | 處置 |\n|---|---|---|---|\n"
        f"| X1「{quote1}」 | P1 | GROK-R2-P0-01 | {row4} |\n"
        f"| X2「{quote2}」 | P2 | CODEX-R2-P1-03 | {row4} |\n"
        + extra_rows +
        "\n## 附錄\n\n"
        f"## GROK-R2-P0-01\n**斷言**: {A1}\n**碼證**: x\n\n"
        f"## CODEX-R2-P1-03\n**斷言**: {A2}\n**碼證**: y\n"
    )


def _write(tmp_path: Path, body: str, session: str = "20260911-t-x-review-r1") -> Path:
    d = tmp_path / "handoffs" / "reconcile" / session; d.mkdir(parents=True, exist_ok=True)
    p = d / "synth.md"; p.write_text(body, encoding="utf-8"); return p


def _gate(p: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["bash", str(GATE), str(p), *extra], cwd=ROOT, capture_output=True, text=True, check=False)


def _hook(body: str, session: str) -> subprocess.CompletedProcess[str]:
    real = ROOT / "handoffs" / "reconcile" / f"zz-p4hook-{session}"; real.mkdir(parents=True, exist_ok=True)
    (real / "synth.md").write_text(body, encoding="utf-8")
    try:
        env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1", SYNTH_HOOK_TARGET=f"handoffs/reconcile/zz-p4hook-{session}/synth.md")
        return subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    finally:
        (real / "synth.md").unlink(missing_ok=True); real.rmdir()


def _todo(tmp_path: Path, text: str = "## §E 殘留\n| E-4 | x |\n### Task 4.1 — y\n") -> Path:
    p = tmp_path / "TODO.md"; p.write_text(text, encoding="utf-8"); return p


# ───────── SPEC Task 4.1 五條 ASSERT ─────────

def test_41_id_in_table_absent_rc_nonzero(tmp_path: Path) -> None:
    body = _synth().replace("| CODEX-R2-P1-03 |", "| （無） |")
    r = _gate(_write(tmp_path, body))
    assert r.returncode == 1 and "CODEX-R2-P1-03" in r.stderr and "①" in r.stderr


def test_41_quote20_mismatch_rc_nonzero(tmp_path: Path) -> None:
    body = _synth(quote1="helper 同批只留最晚者，違反 SPEC 字面單值規定。")   # 第 20 字內改一字（早→晚）
    r = _gate(_write(tmp_path, body))
    assert r.returncode == 1 and "GROK-R2-P0-01" in r.stderr and "②" in r.stderr


def test_41_disposition_absent_rc_nonzero(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth(row4="已處理")))
    assert r.returncode == 1 and "③" in r.stderr and "GROK-R2-P0-01" in r.stderr


def test_41_defer_target_missing_in_todo_rc_nonzero(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth(row4="延後→E-9")), "--todo", str(_todo(tmp_path)))
    assert r.returncode == 1 and "④" in r.stderr and "E-9" in r.stderr


def test_41_all_good_rc_zero(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth()))
    assert r.returncode == 0, r.stderr


# ───────── 邊界 ─────────

def test_41_defer_target_present_in_todo_ok(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth(row4="延後→Task 4.1")), "--todo", str(_todo(tmp_path)))
    assert r.returncode == 0, r.stderr
    r2 = _gate(_write(tmp_path, _synth(row4="延後→E-4")), "--todo", str(_todo(tmp_path)))
    assert r2.returncode == 0, r2.stderr


def test_41_defer_target_with_space_is_whole_token(tmp_path: Path) -> None:
    """主委自查（B4）：`延後→Task 9.9` 對只含 `Task 4.1` 之 TODO 必紅——目標不得被空白截成 `Task`。"""
    r = _gate(_write(tmp_path, _synth(row4="延後→Task 9.9")), "--todo", str(_todo(tmp_path)))
    assert r.returncode == 1 and "Task 9.9" in r.stderr
    doc = sa.parse_synth(_synth(row4="延後→Task 9.9 "), "handoffs/reconcile/20260911-t-x-review-r1/synth.md")
    assert sa.check_disposition(doc, VALUES, "Task 4.1 only", strict_defer=True) != []
    assert sa.check_disposition(doc, VALUES, "see Task 9.9 here", strict_defer=True) == []


def test_41_defer_without_todo_flag_rc_nonzero(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth(row4="延後→E-4")))
    assert r.returncode == 1 and "未提供 --todo" in r.stderr


def test_41_short_assertion_quotes_full_text(tmp_path: Path) -> None:
    """邊界①：斷言 <20 字 ⇒ 引用全文；少一字即紅。"""
    assert _gate(_write(tmp_path, _synth())).returncode == 0
    r = _gate(_write(tmp_path, _synth(quote2="短斷")))
    assert r.returncode == 1 and "CODEX-R2-P1-03" in r.stderr


def test_41_nfc_and_whitespace_tolerant_but_not_punctuation(tmp_path: Path) -> None:
    """邊界②：空白差異容忍（去空白）；標點差異不容忍。"""
    assert _gate(_write(tmp_path, _synth(quote1=A1.replace(" ", "")))).returncode == 0
    r = _gate(_write(tmp_path, _synth(quote1=A1.replace("，", ","))))
    assert r.returncode == 1


def test_41_two_rows_any_one_compliant_ok(tmp_path: Path) -> None:
    """邊界③：同一 finding 被兩列引用 ⇒ 任一列合規即可。"""
    extra = "| X3 另一列只提 ID | P1 | GROK-R2-P0-01 | 採納 |\n"
    assert _gate(_write(tmp_path, _synth(extra_rows=extra))).returncode == 0


def test_41_placeholder_row_ignored_for_quote_but_id_counts(tmp_path: Path) -> None:
    body = _synth().replace(f"| X1「{A1}」 | P1 | GROK-R2-P0-01 | 採納 |", "| X1 | P1 | GROK-R2-P0-01 | （待填） |")
    r = _gate(_write(tmp_path, body))
    assert r.returncode == 1 and "③ GROK-R2-P0-01" in r.stderr   # 佔位列不算已完成 ⇒ 無處置


def test_41_x_layer_target_required_b_layer_not(tmp_path: Path) -> None:
    r = _gate(_write(tmp_path, _synth(target=""), "20260911-t-x-review-r1"))
    assert r.returncode == 1 and "⑤" in r.stderr
    assert _gate(_write(tmp_path, _synth(target=""), "20260911-t-b1-review-r1")).returncode == 0


# ───────── hook（寫入時子集）與閘同一模組 ─────────

def test_41_hook_and_gate_agree_on_ids_target_quote(tmp_path: Path) -> None:
    """hook 與閘對同一 fixture 之 check_ids／check_target／check_quote20 結果逐字相同。"""
    for body in (_synth(), _synth().replace("| CODEX-R2-P1-03 |", "| （無） |"), _synth(quote1="改掉的引用"), _synth(target="")):
        doc = sa.parse_synth(body, "handoffs/reconcile/20260911-t-x-review-r1/synth.md")
        assert sa.check_ids(doc) == sa.check_ids(doc)
        hook_q = sa.check_quote20(doc, values=VALUES, completed_only=True)
        gate_q = sa.check_quote20(doc, values=VALUES, completed_only=False)
        assert hook_q == gate_q                      # 全部列皆已完成時兩模式必相同
        assert sa.check_target(doc) == sa.check_target(doc)


def test_41_hook_draft_row_without_token_not_quote_checked_but_gate_is(tmp_path: Path) -> None:
    """codex Q4：無 token 之列＝草稿 ⇒ hook 不驗 quote20；閘全量驗。"""
    body = _synth(quote1="草稿引用", row4="")           # 第 4 欄空 ⇒ placeholder（非已完成）
    doc = sa.parse_synth(body, "handoffs/reconcile/20260911-t-x-review-r1/synth.md")
    assert sa.check_quote20(doc, values=VALUES, completed_only=True) == []
    assert sa.check_quote20(doc, values=VALUES, completed_only=False) == []   # 佔位列亦非「非佔位 row」⇒ 無候選
    body2 = _synth(quote1="草稿引用", row4="草稿中")      # 第 4 欄有字但無 token ⇒ 非佔位、未完成
    doc2 = sa.parse_synth(body2, "handoffs/reconcile/20260911-t-x-review-r1/synth.md")
    assert sa.check_quote20(doc2, values=VALUES, completed_only=True) == []
    assert sa.check_quote20(doc2, values=VALUES, completed_only=False) != []


def test_41_check_disposition_two_modes(tmp_path: Path) -> None:
    doc = sa.parse_synth(_synth(row4="延後→E-9"), "handoffs/reconcile/20260911-t-x-review-r1/synth.md")
    assert sa.check_disposition(doc, VALUES, None, strict_defer=False) == []
    assert sa.check_disposition(doc, VALUES, None, strict_defer=True) != []
    assert sa.check_disposition(doc, VALUES, "E-9 在此", strict_defer=True) == []
    assert sa.check_disposition(doc, VALUES, "無", strict_defer=True) != []


def test_41_hook_blocks_missing_id_and_passes_good(tmp_path: Path) -> None:
    assert _hook(_synth(), "20260911-t-x-review-r1").returncode == 0
    r = _hook(_synth().replace("| CODEX-R2-P1-03 |", "| （無） |"), "20260911-t-x-review-r1")
    assert r.returncode == 2 and "CODEX-R2-P1-03" in r.stderr


def test_41_hook_defer_target_not_checked_gate_is(tmp_path: Path) -> None:
    body = _synth(row4="延後→E-9")
    assert _hook(body, "20260911-t-x-review-r1").returncode == 0
    r = _gate(_write(tmp_path, body), "--todo", str(_todo(tmp_path)))
    assert r.returncode == 1


def test_41_hook_completed_row_bad_quote_blocks(tmp_path: Path) -> None:
    r = _hook(_synth(quote1="填錯的引用"), "20260911-t-x-review-r1")
    assert r.returncode == 2 and "②" in r.stderr


def test_41_hook_module_missing_fails_open_gate_does_not(tmp_path: Path) -> None:
    """誠實邊界：hook 自身故障靜默放行；閘（debt_clear 前置）不受影響。"""
    env = dict(os.environ, GOVERNANCE_TEST_HARNESS="1", SYNTH_ATTR_MODULE="scripts/_no_such_module.py",
               SYNTH_HOOK_TARGET="handoffs/reconcile/20260911-verdictgate-b3-review-r1/synth.md")
    r = subprocess.run(["bash", str(HOOK)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0


def test_41_gate_usage_errors_rc2(tmp_path: Path) -> None:
    assert _gate(tmp_path / "nope.md").returncode == 2
    r = subprocess.run(["bash", str(GATE)], cwd=ROOT, capture_output=True, text=True, check=False)
    assert r.returncode == 2
