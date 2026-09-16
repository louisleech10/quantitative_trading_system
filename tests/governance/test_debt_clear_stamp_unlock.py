"""debt_clear：stamp 輪「success 檔 sha 不符 → 其後顯式 register-output」收窄解鎖（2026-09-13）。

病根（DOCROT stamp-r3 死鎖，使用者裁定修根因）：cx_run 對 stamp 輪**從未跑** completeness
--single 即記 success；debt_clear 要求 success 檔不得改、C-9 不得 abandon、cx_run 拒重派
⇒ 空殼交件無任何出路。解鎖**只限 stamp 輪**（committee_round_open.brief_kind == "stamp"），
且其後同 round 同家有 committee_output 且其 sha == 檔案當前 sha。非 stamp 輪維持原判。
hermetic：沿用 test_debt_clear 之 harness（DEBT_AUDIT_OVERRIDE）。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from tests.governance import _debt_probe_helper as _dph
from tests.governance.test_debt_clear import (
    _append,
    _build_session,
    _clear,
    _committee_output,
    _finding,
    _result,
    _setup,
    _sha256_file,
    _write_output,
)


def _open_round_kind(root: Path, audit: Path, *, round_id: str, session: str, family: str, brief_kind: str | None) -> None:
    outs = {family: f"handoffs/{session}-{family}.md"}
    args = [
        "--require-absent-session", session,
        "--event", "committee_round_open",
        "--field", f"round_id={round_id}",
        "--field", "task_id=t-stamp",
        "--field", "brief_path=handoffs/brief.md",
        "--field", "brief_sha256=" + ("a" * 64),
        "--field", "brief_sha256_norm=" + ("b" * 64),
        "--field", "lock_mode=review",
        "--field", f"participants=@{json.dumps([family])}",
        "--field", f"expected_outputs=@{json.dumps(outs, ensure_ascii=False)}",
        "--field", f"session_name={session}",
        "--field", "actor=test",
        "--field", "origin_script=committee_run.sh",
    ]
    if brief_kind is not None:
        args += ["--field", f"brief_kind={brief_kind}"]
        _append(root, audit, *args)
    else:
        # DOCROT2 Task 3.2 起 brief_kind 為必填：缺 brief_kind 之 round 以「規則上線前之寫入端」寫入
        with _dph.legacy_round_open_registry(root / "scripts"):
            _append(root, audit, *args)


def _prep(tmp_path: Path, *, session: str, brief_kind: str | None) -> tuple[Path, Path, str, Path, Path]:
    """一家 sentinel 交件記 success；回傳 (root, audit, rid, lock, out)。"""
    root, audit = _setup(tmp_path)
    rid = str(uuid.uuid4())
    fam = "codex"
    _open_round_kind(root, audit, round_id=rid, session=session, family=fam, brief_kind=brief_kind)
    out, sha = _write_output(root, session, fam, _finding("CODEX-R1-P3-00"))
    _result(root, audit, round_id=rid, family=fam, out_path=str(out.relative_to(root)), out_sha=sha)
    lock = _build_session(root, session=session, round_id=rid, families=[fam], mode="review",
                          bodies={fam: _finding("CODEX-R1-P3-00")})
    return root, audit, rid, lock, out


def _tamper(out: Path) -> None:
    out.write_text(out.read_text(encoding="utf-8") + "\nVERDICT: proceed\nBLOCKED-BY:\nCLOSED:\n", encoding="utf-8")


def test_stamp_round_edited_then_reregistered_unlocks(tmp_path: Path) -> None:
    """ASSERT stamp 輪：success 後改檔 + 其後 committee_output（sha 相符）⇒ rc=0（收窄解鎖）。

    mutation：把 debt_clear 的 `round_brief_kind(rid) == "stamp"` 分支拿掉 ⇒ 本條紅。
    """
    root, audit, rid, lock, out = _prep(tmp_path, session="st1", brief_kind="stamp")
    _tamper(out)
    _committee_output(root, audit, round_id=rid, family="codex",
                      out_path="handoffs/st1-codex.md", out_sha=_sha256_file(out))
    r = _clear(root, audit, "--round-id", rid, "--session", "st1", "--lock", str(lock))
    assert r.returncode == 0, r.stderr + r.stdout
    assert "stamp 輪 success 檔 sha 不符，但其後已顯式 register-output" in (r.stdout or "")


def test_review_round_edited_then_reregistered_still_blocked(tmp_path: Path) -> None:
    """ASSERT 非 stamp 輪（brief_kind=review）同樣操作 ⇒ 仍 rc≠0（解鎖只限 stamp，不擴）。"""
    root, audit, rid, lock, out = _prep(tmp_path, session="rv1", brief_kind="review")
    _tamper(out)
    _committee_output(root, audit, round_id=rid, family="codex",
                      out_path="handoffs/rv1-codex.md", out_sha=_sha256_file(out))
    r = _clear(root, audit, "--round-id", rid, "--session", "rv1", "--lock", str(lock))
    assert r.returncode != 0
    assert "sha 不符" in (r.stderr or "")


def test_round_without_brief_kind_is_fail_closed(tmp_path: Path) -> None:
    """ASSERT committee_round_open 缺 brief_kind ⇒ 視為非 stamp，維持原判 rc≠0（fail-closed）。"""
    root, audit, rid, lock, out = _prep(tmp_path, session="nk1", brief_kind=None)
    _tamper(out)
    _committee_output(root, audit, round_id=rid, family="codex",
                      out_path="handoffs/nk1-codex.md", out_sha=_sha256_file(out))
    r = _clear(root, audit, "--round-id", rid, "--session", "nk1", "--lock", str(lock))
    assert r.returncode != 0
    assert "sha 不符" in (r.stderr or "")


def test_stamp_round_reregistered_with_stale_sha_blocked(tmp_path: Path) -> None:
    """ASSERT stamp 輪：committee_output 之 sha 與檔案當前 sha 不符（登記後又改）⇒ rc≠0。"""
    root, audit, rid, lock, out = _prep(tmp_path, session="st2", brief_kind="stamp")
    _tamper(out)
    _committee_output(root, audit, round_id=rid, family="codex",
                      out_path="handoffs/st2-codex.md", out_sha=_sha256_file(out))
    out.write_text(out.read_text(encoding="utf-8") + "\nAGAIN\n", encoding="utf-8")
    r = _clear(root, audit, "--round-id", rid, "--session", "st2", "--lock", str(lock))
    assert r.returncode != 0
    assert "sha 不符" in (r.stderr or "")


def test_stamp_round_reregister_of_other_path_does_not_unlock(tmp_path: Path) -> None:
    """〔CODEX-R1-P1-01／GROK-R1-P1-01〕ASSERT 其後 committee_output 指向**異路徑**（例：cx_run 自動登記之
    stamp-target、或任意 handoff）⇒ 不得解鎖，rc≠0；解鎖只認同一份交件檔之重登。

    mutation：拿掉 `_norm(rr["output_path"]) == _norm(op)` ⇒ 本條紅。
    """
    root, audit, rid, lock, out = _prep(tmp_path, session="st4", brief_kind="stamp")
    _tamper(out)
    other = root / "handoffs" / "st4-stamp-target.md"
    other.write_text("## 戳記\n\nRECONCILE-STAMP: codex APPROVED 2026-09-13 sha256:deadbeef task:t-stamp\n", encoding="utf-8")
    _committee_output(root, audit, round_id=rid, family="codex",
                      out_path="handoffs/st4-stamp-target.md", out_sha=_sha256_file(other))
    r = _clear(root, audit, "--round-id", rid, "--session", "st4", "--lock", str(lock))
    assert r.returncode != 0, r.stdout + r.stderr
    assert "sha 不符" in (r.stderr or "")


def test_stamp_round_edited_without_reregister_blocked(tmp_path: Path) -> None:
    """ASSERT stamp 輪：改檔但**無**其後 committee_output ⇒ rc≠0（解鎖須主委顯式登記、留審計）。"""
    root, audit, rid, lock, out = _prep(tmp_path, session="st3", brief_kind="stamp")
    _tamper(out)
    r = _clear(root, audit, "--round-id", rid, "--session", "st3", "--lock", str(lock))
    assert r.returncode != 0
    assert "sha 不符" in (r.stderr or "")
