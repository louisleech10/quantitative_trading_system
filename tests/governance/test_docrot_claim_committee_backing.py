"""DOCROT consult-r3 Task 1.5（grok 原文，三家定案 2026-09-13）：
commit 訊息之「三家共同結論」類背書語須有同 task-id 之委員 audit 佐證。

病根（review-r1 三家 G2）：commit `3e009126` 以「落地三家共同結論」為題，背書一批
未經任何委員審查的實作；`verification_claim_check.py --commit-msg` 對該主旨 rc=0
（三家 R3 實跑）。封閉字面、不做語意；佐證＝`.claude/gate/audit.log` 中該 task-id 之
`committee_family_result`／`committee_output` 涵蓋家數 ≥ review roster。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CHECK = REPO / "scripts" / "verification_claim_check.py"
AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"
TASK = "20260912-DEMO-X-REVIEW-R1"


def _audit(tmp: Path, families: list[str]) -> Path:
    log = tmp / "audit.log"
    lines = [
        json.dumps(
            {
                "event": "committee_family_result",
                "task_id": TASK,
                "family": fam,
                "output_path": f"handoffs/x-{fam}.md",
            }
        )
        for fam in families
    ]
    log.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return log


def _run(tmp: Path, msg: str, audit: Path) -> subprocess.CompletedProcess[str]:
    m = tmp / "COMMIT_MSG"
    m.write_text(msg, encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(CHECK), "--commit-msg", str(m)],
        capture_output=True, text=True, check=False, cwd=str(REPO),
        env={**os.environ, AUDIT_ENV: str(audit)},
    )


def test_consensus_claim_without_task_id_rejected(tmp_path: Path) -> None:
    """ASSERT 逐字重現 `3e009126` 主旨（無 task-id）⇒ rc≠0（前版 rc=0）。

    mutation：拿掉 `_consensus_backing_violations` 呼叫 ⇒ 本條紅。
    """
    audit = _audit(tmp_path, ["codex", "composer", "grok"])
    r = _run(tmp_path, "fix(docrot): 落地三家共同結論前兩項\n", audit)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "三家共同結論" in r.stderr


def test_consensus_claim_with_full_roster_backing_passes(tmp_path: Path) -> None:
    """ASSERT 同 task-id 三家 committee_family_result 齊 ⇒ rc=0（證明非恆紅）。"""
    audit = _audit(tmp_path, ["codex", "composer", "grok"])
    r = _run(tmp_path, f"docs: 依三家共同結論（{TASK}）落地\n", audit)
    assert r.returncode == 0, r.stdout + r.stderr


def test_consensus_claim_with_partial_roster_rejected(tmp_path: Path) -> None:
    """ASSERT 只有兩家有 audit ⇒ 「三家」背書不成立，rc≠0（擋多數決冒充一致）。"""
    audit = _audit(tmp_path, ["codex", "grok"])
    r = _run(tmp_path, f"docs: 三家一致落地（{TASK}）\n", audit)
    assert r.returncode != 0, r.stdout + r.stderr
    assert "家數不足" in r.stderr, r.stderr


def test_consensus_claim_with_unknown_task_rejected(tmp_path: Path) -> None:
    """ASSERT task-id 在 audit 無任何家 ⇒ rc≠0。"""
    audit = _audit(tmp_path, [])
    r = _run(tmp_path, f"docs: 三家共同結論（{TASK}）\n", audit)
    assert r.returncode != 0, r.stdout + r.stderr


def test_message_without_consensus_phrase_unaffected(tmp_path: Path) -> None:
    """ASSERT 無該字面之一般訊息不受本閘影響（既有行為不變）。"""
    audit = _audit(tmp_path, [])
    r = _run(tmp_path, "docs: 交接更新到現況\n", audit)
    assert r.returncode == 0, r.stdout + r.stderr


def test_verify_exempt_allows_consensus_phrase(tmp_path: Path) -> None:
    """ASSERT 帶既有 `VERIFY-EXEMPT:` 類別 ⇒ 放行（grok 原文允許既有豁免）。"""
    audit = _audit(tmp_path, [])
    r = _run(tmp_path, "docs: 引述舊 commit「三家共同結論」 VERIFY-EXEMPT:doc-example:docrot-quote\n", audit)
    assert r.returncode == 0, r.stdout + r.stderr
