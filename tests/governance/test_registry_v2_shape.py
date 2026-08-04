"""P1-6 B1：registry v2 契約與 lock identity binding 的最小守衛。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = REPO_ROOT / "scripts" / "audit_events.json"
RECONCILE_SH = REPO_ROOT / "scripts" / "reconcile_build.sh"
WRITE_LOCK_SH = REPO_ROOT / "scripts" / "write_sources_lock.sh"
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
RECONCILE_TARGET = RECONCILE_SH
WRITE_LOCK_TARGET = WRITE_LOCK_SH


def _run(command: list[str], *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """在 repo 根目錄執行治理命令。"""
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_registry_is_v2_shape() -> None:
    """registry 僅保留四事件、三輪次狀態與二結果狀態。"""
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    deleted_events = {
        "committee_round_amendment",
        "committee_family_dispatch",
        "committee_family_degrade",
        "committee_debt_clear_format_failure",
        "committee_debt_clear_all_degraded",
        "committee_debt_supersede",
        "round_open_failed",
    }

    assert set(registry["debt_events"]) == {
        "committee_round_open",
        "committee_family_result",
        "committee_debt_clear",
        "debt_abandon",
    }
    assert registry["enums"]["abandon_kind"] == [
        "no-findings-expected",
        "collection-failed",
    ]
    assert registry["enums"]["round_state"] == ["OPEN", "CLOSED", "ABANDONED"]
    # 契約擴張（GOVFLOW Task 2.2 / D-003）：二值 → 三值。
    # 非弱化——新增 format-failed 收窄 success 語意；failed 保留；
    # 空 sha 例外仍僅 failed。舊 assert 鎖的是「僅 success|failed」舊契約。
    assert registry["enums"]["result_state"] == [
        "success",
        "failed",
        "format-failed",
    ]
    assert "abandon_kind" in registry["debt_events"]["debt_abandon"]["fields"]
    assert "remediation_owner" not in registry["debt_events"]["debt_abandon"]["fields"]
    assert "output_sha256" in registry["debt_events"]["committee_family_result"]["fields"]
    assert "session_name" in registry["debt_events"]["committee_round_open"]["fields"]
    assert "attempt_cap" not in REGISTRY.read_text(encoding="utf-8")
    assert not deleted_events.intersection(registry["required_fields_per_event"])
    assert "clear_kind_event_map" not in registry


def test_reconcile_help_lists_mode_and_rebuild() -> None:
    """reconcile_build 的 help 必須暴露本批兩個旗標。"""
    result = _run(["bash", str(RECONCILE_SH), "--help"])
    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "--mode" in combined
    assert "--rebuild" in combined


def _finding(family: str) -> str:
    """建立 discovery/review 都可解析的最小 canonical finding。"""
    upper = family.upper()
    return (
        f"## {upper}-R1-P0-01\n\n"
        "**斷言**: identity binding must be tested through the lock writer.\n\n"
        "**碼證**: scripts/reconcile_build.sh and scripts/write_sources_lock.sh\n\n"
        f"**來源摘要**: sources/review-{family}.md#aaaaaaaaaaaa\n"
    )


def _harness(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """建立只含本批腳本的隔離 repo，避免測試污染真實 audit。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    for source in (RECONCILE_SH, WRITE_LOCK_SH, COMPLETENESS_SH, REGISTRY):
        shutil.copy2(source, scripts / source.name)
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    return root, scripts / RECONCILE_SH.name, scripts / WRITE_LOCK_SH.name, audit


def _audit_open(
    audit: Path,
    session_name: str,
    round_id: str,
    *,
    duplicate_round_ids: tuple[str, ...] = (),
    terminal_event: str | None = None,
) -> None:
    """寫入本批測試所需的最小 audit 事件。"""
    records = [
        {
            "event": "committee_round_open",
            "sequence": index,
            "round_id": value,
            "session_name": session_name,
        }
        for index, value in enumerate((round_id, *duplicate_round_ids), 1)
    ]
    if terminal_event is not None:
        records.append(
            {
                "event": terminal_event,
                "sequence": len(records) + 1,
                "round_id": round_id,
            }
        )
    audit.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _writer_session(root: Path, name: str, family: str = "codex") -> Path:
    """建立 writer 可掃描的 sources 目錄。"""
    session = root / "sessions" / name
    sources = session / "sources"
    sources.mkdir(parents=True)
    (sources / f"review-{family}.md").write_text(_finding(family), encoding="utf-8")
    return session


def _run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """執行隔離 harness 內的治理腳本並保留原始 rc。"""
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=script.parents[1],
        capture_output=True,
        text=True,
        check=False,
    )


def _mutate_script(path: Path, old: str, new: str) -> str:
    """以明確字串變異真實腳本副本，回傳原始內容供復原。"""
    original = path.read_text(encoding="utf-8")
    assert old in original, f"mutation anchor missing: {old!r}"
    path.write_text(original.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return original


def test_reconcile_fresh_discovery_does_not_require_audit(tmp_path: Path) -> None:
    """fresh discovery 不反查 audit，且建立的 lock 不帶 round_id。"""
    root, reconcile, _, audit = _harness(tmp_path)
    codex = root / "review-codex.md"
    grok = root / "review-grok.md"
    codex.write_text(_finding("codex"), encoding="utf-8")
    grok.write_text(_finding("grok"), encoding="utf-8")
    session_name = "p16-b1-discovery-no-audit"

    result = _run_script(reconcile, session_name, str(codex), str(grok))
    assert result.returncode == 0, result.stdout + result.stderr
    lock = json.loads(
        (root / "handoffs" / "reconcile" / session_name / "sources.lock").read_text(
            encoding="utf-8"
        )
    )
    assert lock["mode"] == "discovery"
    assert "round_id" not in lock
    assert audit.read_text(encoding="utf-8") == ""


def test_reconcile_fresh_review_requires_audit(tmp_path: Path) -> None:
    """fresh review 沒有對應 committee_round_open 時 fail-closed。"""
    root, reconcile, _, _ = _harness(tmp_path)
    source = root / "review-codex.md"
    source.write_text(_finding("codex"), encoding="utf-8")
    result = _run_script(
        reconcile,
        "p16-b1-review-without-audit",
        "--mode",
        "review",
        str(source),
    )
    assert result.returncode != 0
    assert "session_name" in (result.stdout + result.stderr)
    assert not (root / "handoffs" / "reconcile" / "p16-b1-review-without-audit").exists()


def test_lock_round_id_and_rebuild_preserve_identity_inputs(tmp_path: Path) -> None:
    """review rebuild 由 audit 導出 round_id，且只改 mode/round_id。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "session")
    (session / "sources" / "review-grok.md").write_text(_finding("grok"), encoding="utf-8")
    _audit_open(audit, session.name, "round-b1-rebound")

    fresh = _run_script(
        writer,
        "--session",
        str(session),
        "--roster",
        "codex,grok",
        "--mode",
        "discovery",
        "--round-id",
        "round-b1",
    )
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    before = json.loads((session / "sources.lock").read_text(encoding="utf-8"))
    before_sources = before["sources"]
    before_roster = before["expected_roster"]

    rebuild = _run_script(
        writer,
        "--session",
        str(session),
        "--mode",
        "review",
        "--rebuild",
    )
    assert rebuild.returncode == 0, rebuild.stdout + rebuild.stderr
    after = json.loads((session / "sources.lock").read_text(encoding="utf-8"))

    assert after["mode"] == "review"
    assert after["round_id"] == "round-b1-rebound"
    assert after["sources"] == before_sources
    assert after["expected_roster"] == before_roster


def test_mutation_fresh_review_requires_exactly_one_audit(
    tmp_path: Path, monkeypatch
) -> None:
    """閹割 fresh review 的恰一筆守衛後，重複 session 不得變成可建 lock。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "fresh-review-duplicate")
    _audit_open(audit, session.name, "round-one", duplicate_round_ids=("round-two",))
    args = (
        "--session",
        str(session),
        "--roster",
        "codex",
        "--mode",
        "review",
    )

    baseline = _run_script(writer, *args)
    assert baseline.returncode != 0

    original = _mutate_script(writer, "if len(hits) != 1:", "if len(hits) < 1:")
    monkeypatch.setattr(sys.modules[__name__], "WRITE_LOCK_TARGET", writer)
    mutated = _run_script(WRITE_LOCK_TARGET, *args)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr

    writer.write_text(original, encoding="utf-8")
    repaired = _run_script(WRITE_LOCK_TARGET, *args)
    assert repaired.returncode != 0


def test_mutation_rebuild_requires_exactly_one_audit(
    tmp_path: Path, monkeypatch
) -> None:
    """閹割 rebuild 的恰一筆守衛後，多筆 identity 不得升級 lock。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "rebuild-duplicate")
    _audit_open(audit, session.name, "round-one", duplicate_round_ids=("round-two",))
    fresh = _run_script(
        writer,
        "--session",
        str(session),
        "--roster",
        "codex",
        "--mode",
        "discovery",
    )
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    args = ("--session", str(session), "--mode", "review", "--rebuild")

    baseline = _run_script(writer, *args)
    assert baseline.returncode != 0

    original = _mutate_script(writer, "if len(hits) != 1:", "if len(hits) < 1:")
    monkeypatch.setattr(sys.modules[__name__], "WRITE_LOCK_TARGET", writer)
    mutated = _run_script(WRITE_LOCK_TARGET, *args)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr

    lock = json.loads((session / "sources.lock").read_text(encoding="utf-8"))
    lock["mode"] = "discovery"
    (session / "sources.lock").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    writer.write_text(original, encoding="utf-8")
    repaired = _run_script(WRITE_LOCK_TARGET, *args)
    assert repaired.returncode != 0


def test_mutation_rebuild_requires_open_round(tmp_path: Path, monkeypatch) -> None:
    """閹割 rebuild 的 OPEN 守衛後，已結束輪次不得升級 lock。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "rebuild-closed")
    _audit_open(audit, session.name, "round-closed", terminal_event="committee_debt_clear")
    fresh = _run_script(
        writer,
        "--session",
        str(session),
        "--roster",
        "codex",
        "--mode",
        "discovery",
    )
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    args = ("--session", str(session), "--mode", "review", "--rebuild")

    baseline = _run_script(writer, *args)
    assert baseline.returncode != 0

    original = _mutate_script(
        writer,
        '  _assert_round_open "${ROUND_ID}" || exit 1\n',
        '  : # mutation: bypass OPEN guard\n',
    )
    monkeypatch.setattr(sys.modules[__name__], "WRITE_LOCK_TARGET", writer)
    mutated = _run_script(WRITE_LOCK_TARGET, *args)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr

    writer.write_text(original, encoding="utf-8")
    repaired = _run_script(WRITE_LOCK_TARGET, *args)
    assert repaired.returncode != 0


def test_mutation_rebuild_is_one_way(tmp_path: Path, monkeypatch) -> None:
    """閹割 discovery→review 單向守衛後，review→discovery 不得成功。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "rebuild-reverse")
    _audit_open(audit, session.name, "round-reverse")
    fresh = _run_script(
        writer,
        "--session",
        str(session),
        "--roster",
        "codex",
        "--mode",
        "review",
    )
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    args = ("--session", str(session), "--mode", "discovery", "--rebuild")

    baseline = _run_script(writer, *args)
    assert baseline.returncode != 0

    original = _mutate_script(
        writer,
        '  [ "${MODE}" = "review" ] || {\n    echo "ERROR: --rebuild 僅允許目標 mode=review" >&2\n    exit 1\n  }\n',
        '  : # mutation: bypass target-mode guard\n',
    )
    mutated_text = writer.read_text(encoding="utf-8")
    mutated_text = mutated_text.replace("if target_mode != \"review\":", "if False:", 1)
    mutated_text = mutated_text.replace('if lock.get("mode") != "discovery":', "if False:", 1)
    writer.write_text(mutated_text, encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "WRITE_LOCK_TARGET", writer)
    mutated = _run_script(WRITE_LOCK_TARGET, *args)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr

    writer.write_text(original, encoding="utf-8")
    repaired = _run_script(WRITE_LOCK_TARGET, *args)
    assert repaired.returncode != 0


def test_mutation_rebuild_rejects_external_round_id(
    tmp_path: Path, monkeypatch
) -> None:
    """閹割外來 round_id 拒絕後，BOGUS identity 不得使 rebuild 成功。"""
    root, _, writer, audit = _harness(tmp_path)
    session = _writer_session(root, "rebuild-external-round")
    _audit_open(audit, session.name, "round-authoritative")
    fresh = _run_script(
        writer,
        "--session",
        str(session),
        "--roster",
        "codex",
        "--mode",
        "discovery",
    )
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr
    args = (
        "--session",
        str(session),
        "--mode",
        "review",
        "--round-id",
        "BOGUS",
        "--rebuild",
    )

    baseline = _run_script(writer, *args)
    assert baseline.returncode != 0

    original = _mutate_script(
        writer,
        '  [ -z "${ROUND_ID}" ] || {\n    echo "ERROR: --rebuild 拒收呼叫端 --round-id；identity 必須由 audit 導出" >&2\n    exit 1\n  }\n',
        '  : # mutation: accept caller round-id\n',
    )
    monkeypatch.setattr(sys.modules[__name__], "WRITE_LOCK_TARGET", writer)
    mutated = _run_script(WRITE_LOCK_TARGET, *args)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr

    writer.write_text(original, encoding="utf-8")
    repaired = _run_script(WRITE_LOCK_TARGET, *args)
    assert repaired.returncode != 0


def test_mutation_fresh_discovery_does_not_recheck_audit(
    tmp_path: Path, monkeypatch
) -> None:
    """閹割 discovery bootstrap bypass 後，空 audit 不得讓正常建立轉紅。"""
    root, reconcile, _, audit = _harness(tmp_path)
    codex = root / "review-codex.md"
    codex.write_text(_finding("codex"), encoding="utf-8")
    args = ("p16-b1-discovery-mutation", str(codex))

    baseline = _run_script(reconcile, *args)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert audit.read_text(encoding="utf-8") == ""

    original = _mutate_script(
        reconcile,
        'if [ "${mode}" = "review" ]; then\n',
        'if [ "${mode}" != "review" ] || [ "${mode}" = "review" ]; then\n',
    )
    monkeypatch.setattr(sys.modules[__name__], "RECONCILE_TARGET", reconcile)
    mutated = _run_script(RECONCILE_TARGET, "p16-b1-discovery-mutated", str(codex))
    assert mutated.returncode != 0

    reconcile.write_text(original, encoding="utf-8")
    repaired = _run_script(RECONCILE_TARGET, "p16-b1-discovery-repaired", str(codex))
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
