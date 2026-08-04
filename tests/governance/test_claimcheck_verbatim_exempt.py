"""GOVFLOW-B4 — claim checker 逐字豁免（Task 4.1 sources/ ＋ Task 4.2 synth 附錄 unit 級）。

對齊 docs/GOV_DISPATCH_FLOW_FIX_TODO.md Phase 4 測試表。
hermetic：隔離 committee audit／receipt／pending；不污染真實 .claude/gate/。
mutation 探針：module-level 常數 ＋ monkeypatch 真重導向待測符號（禁空 monkeypatch）。
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
import verification_claim_check as vcc  # noqa: E402

from tests.governance._pyenv import PYTHON  # noqa: E402

CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"

# mutation 探針可 monkeypatch 的 module-level 鉤子（指向待測函式／常數）
APPENDIX_LINES_TARGET = vcc._appendix_exempt_line_numbers
SOURCES_EXEMPT_TARGET = vcc._is_committee_process_exempt
REGISTRY_EVENTS_TARGET = vcc._COMMITTEE_SOURCES_REGISTRY_EVENTS

# 可觸發 operational claim 的無 backing 文句（含 strong polarity）
OP_CLAIM = "align mutation 已驗真紅\n"
OP_CLAIM_LINE = "align mutation 已驗真紅"


@pytest.fixture(autouse=True)
def isolated_verify_gate_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """隔離 receipt/audit/ledger，避免污染真實 .claude/gate/。"""
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(tmp_path / "run_receipts"))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(tmp_path / "gate" / "verify_audit.log"))
    monkeypatch.setenv(COMMITTEE_AUDIT_ENV, str(tmp_path / "gate" / "audit.log"))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(tmp_path / "pending_verifications.jsonl"))


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _sha(data: bytes | str) -> str:
    raw = data if isinstance(data, bytes) else data.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _append_committee_event(
    audit_log: Path,
    *,
    event: str,
    output_path: str,
    sha256: str,
    result_state: str | None = None,
) -> None:
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "event": event,
        "task_id": "govflow-b4-test",
        "family": "codex",
        "output_path": output_path,
        "output_sha256": sha256,
        "ts": "2099-01-01T00:00:00Z",
    }
    # 真實 cx_run 的 committee_family_result 帶 result_state（success／format-failed／failed）
    if result_state is not None:
        payload["result_state"] = result_state
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _append_committee_output(audit_log: Path, *, output_path: str, sha256: str) -> None:
    _append_committee_event(
        audit_log,
        event="committee_output",
        output_path=output_path,
        sha256=sha256,
    )


def _append_committee_family_result(
    audit_log: Path,
    *,
    output_path: str,
    sha256: str,
    result_state: str = "success",
) -> None:
    """模擬 cx_run 委員完成時自動寫入的 family_result 事件。

    result_state 預設 success；`format-failed` 亦帶非空 sha（`cx_run.sh:253`），
    但**不得**進 registry —— 見 `T4-N15`。
    """
    _append_committee_event(
        audit_log,
        event="committee_family_result",
        output_path=output_path,
        sha256=sha256,
        result_state=result_state,
    )


def _write_sources_lock(
    session_dir: Path,
    *,
    session_id: str,
    name: str,
    sha256: str,
    realpath: str | None = None,
) -> Path:
    lock = session_dir / "sources.lock"
    entry_path = realpath or str((session_dir / "sources" / name).resolve())
    payload = {
        "version": 1,
        "session_id": session_id,
        "expected_roster": ["codex"],
        "sources": [
            {
                "realpath": entry_path,
                "sha256": sha256,
                "family": "codex",
            }
        ],
        "freeze_ts": "2099-01-01T00:00:00Z",
        "closure_state": "open",
        "mode": "review",
        "round_id": "b4-test-round",
    }
    lock.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock


def _run_checker(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), str(CLAIM_CHECK), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env or os.environ.copy(),
    )


def _synth_doc(*, cluster_body: str, appendix_body: str, extra_h2_after_appendix: str = "") -> str:
    """組最小 reconcile synth：群集 ＋ 附錄（標題為實戰前綴形態）。"""
    parts = [
        "# Reconcile — b4-test\n",
        "\n",
        "## 群集 / 處置\n",
        "\n",
        cluster_body,
        "\n",
        "## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）\n",
        "\n",
        appendix_body,
    ]
    if extra_h2_after_appendix:
        parts.append(extra_h2_after_appendix)
    return "".join(parts)


# ── T4-U1 ──────────────────────────────────────────────────────────


def test_t4_u1_sources_copy_registered_hash_commit_ok(tmp_path: Path) -> None:
    """T4-U1：reconcile sources/ 副本 hash 相符 ＋ lock 綁定 ⇒ 豁免（可 commit 路徑）。"""
    session = "20990101-b4-u1"
    name = "20990101-b4-u1-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    origin_rel = f"handoffs/{name}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(copy.read_bytes())
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=origin_rel,
        sha256=digest,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )

    # in-process 驗豁免
    assert vcc._is_committee_process_exempt(
        f"handoffs/reconcile/{session}/sources/{name}",
        copy,
        content_bytes=copy.read_bytes(),
    )

    proc = _run_checker("--files", str(copy))
    assert proc.returncode == 0, proc.stderr

    # 隔離 git commit 路徑（不碰主樹 hook 狀態）
    repo = tmp_path / "commit-repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "b4@test.local"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "b4-test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # 最小 pre-commit：只跑 checker --staged
    hook = repo / ".git" / "hooks" / "pre-commit"
    hook.write_text(
        "#!/bin/sh\n"
        f'exec "{PYTHON}" "{CLAIM_CHECK}" --staged\n',
        encoding="utf-8",
    )
    hook.chmod(0o755)
    # 在 clone 內建 handoffs 樹 ＋ 指向測試 audit
    dest = repo / "handoffs" / "reconcile" / session / "sources" / name
    dest.parent.mkdir(parents=True)
    shutil.copy2(copy, dest)
    shutil.copy2(
        tmp_path / "handoffs" / "reconcile" / session / "sources.lock",
        repo / "handoffs" / "reconcile" / session / "sources.lock",
    )
    env = os.environ.copy()
    env[COMMITTEE_AUDIT_ENV] = os.environ[COMMITTEE_AUDIT_ENV]
    env[RECEIPTS_DIR_ENV] = os.environ[RECEIPTS_DIR_ENV]
    env[AUDIT_LOG_ENV] = os.environ[AUDIT_LOG_ENV]
    env[PENDING_LEDGER_ENV] = os.environ[PENDING_LEDGER_ENV]
    subprocess.run(["git", "add", "-f", str(dest.relative_to(repo))], cwd=repo, check=True)
    # sources.lock 亦 stage（不掃描 md 以外；pre-commit 只掃 md）
    subprocess.run(
        ["git", "add", "-f", f"handoffs/reconcile/{session}/sources.lock"],
        cwd=repo,
        check=True,
    )
    commit = subprocess.run(
        ["git", "commit", "-m", "test: b4 u1 sources exempt"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert commit.returncode == 0, commit.stdout + commit.stderr


# ── T4-N1 ──────────────────────────────────────────────────────────


def test_t4_n1_tampered_sources_copy_not_exempt(tmp_path: Path) -> None:
    """T4-N1：副本被竄改（hash 不符）⇒ 不豁免，rc!=0。"""
    session = "20990101-b4-n1"
    name = "20990101-b4-n1-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    good = _sha(body)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=good,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=good,
        realpath=str(copy.resolve()),
    )
    # 竄改一個 byte
    copy.write_text(body + "X", encoding="utf-8")
    proc = _run_checker("--files", str(copy))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── T4-N2 ──────────────────────────────────────────────────────────


def test_t4_n2_out_of_session_symlink_duplicate_not_exempt(tmp_path: Path) -> None:
    """T4-N2：session 外路徑／symlink／非精確 sources 形態 ⇒ 不豁免。"""
    name = "20990101-b4-n2-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    digest = _sha(body)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )

    # session 外：handoffs/other/sources/name.md
    outside = _write(tmp_path / "handoffs" / "other" / "sources" / name, body)
    proc1 = _run_checker("--files", str(outside))
    assert proc1.returncode != 0

    # symlink 副本
    session = "20990101-b4-n2"
    real = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(real.resolve()),
    )
    link = tmp_path / "handoffs" / "reconcile" / session / "sources" / f"link-{name}"
    link.symlink_to(real)
    proc2 = _run_checker("--files", str(link))
    assert proc2.returncode != 0

    # duplicate basename 形態但不在 sources/（handoffs/reconcile/session/name.md）
    dup = _write(tmp_path / "handoffs" / "reconcile" / session / name, body)
    proc3 = _run_checker("--files", str(dup))
    assert proc3.returncode != 0


# ── T4-C1 ──────────────────────────────────────────────────────────


def test_t4_c1_staged_and_worktree_use_same_bytes(tmp_path: Path) -> None:
    """T4-C1：staged 與 worktree 內容不同 ⇒ 豁免判定與掃描取同一份 bytes（content_map）。"""
    session = "20990101-b4-c1"
    name = "20990101-b4-c1-codex.md"
    staged_body = f"## 已完成\n\n{OP_CLAIM}"
    worktree_body = f"## 已完成\n\n{OP_CLAIM}TAMPERED\n"
    digest = _sha(staged_body)
    origin_rel = f"handoffs/{name}"
    rel = f"handoffs/reconcile/{session}/sources/{name}"
    copy = _write(tmp_path / rel, worktree_body)  # worktree 已竄改
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=origin_rel,
        sha256=digest,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )

    # 若誤用 worktree bytes → hash 不符 → 不豁免 → 有 violation
    # 若用 staged bytes（content_map）→ 豁免
    violations = vcc.check_files(
        [copy],
        content_map={rel: staged_body},
    )
    assert violations == [], f"staged bytes 應豁免: {violations}"

    # 對照：無 content_map 時走 worktree → 不豁免
    violations_wt = vcc.check_files([copy])
    assert violations_wt, "worktree 竄改應不豁免"


# ── T4-U2 ──────────────────────────────────────────────────────────


def test_t4_u2_appendix_claim_passes(tmp_path: Path) -> None:
    """T4-U2：附錄段內無 backing 的 claim ⇒ PASS。"""
    rel = "handoffs/reconcile/20990101-b4-u2/synth.md"
    content = _synth_doc(
        cluster_body="主委彙整段落無 operational 強極性。\n",
        appendix_body=f"## CODEX-B4-P1-01\n\n{OP_CLAIM}",
    )
    path = _write(tmp_path / rel, content)
    proc = _run_checker("--files", str(path))
    assert proc.returncode == 0, proc.stderr


# ── T4-N3 ──────────────────────────────────────────────────────────


def test_t4_n3_cluster_section_same_text_fails(tmp_path: Path) -> None:
    """T4-N3：`## 群集 / 處置` 段同樣文字 ⇒ FAIL。"""
    rel = "handoffs/reconcile/20990101-b4-n3/synth.md"
    content = _synth_doc(
        cluster_body=f"{OP_CLAIM}",
        appendix_body="附錄無 claim。\n",
    )
    path = _write(tmp_path / rel, content)
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── T4-N4 ──────────────────────────────────────────────────────────


def test_t4_n4_cluster_nested_h3_h4_fails(tmp_path: Path) -> None:
    """T4-N4：群集段下 nested H3/H4 內 claim ⇒ FAIL。"""
    rel = "handoffs/reconcile/20990101-b4-n4/synth.md"
    cluster = (
        "### 群 1\n\n"
        f"{OP_CLAIM}"
        "#### 子節\n\n"
        "另一段敘述。\n"
    )
    content = _synth_doc(cluster_body=cluster, appendix_body="附錄空。\n")
    path = _write(tmp_path / rel, content)
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── T4-N5 ──────────────────────────────────────────────────────────


def test_t4_n5_forged_appendix_on_normal_handoff_fails(tmp_path: Path) -> None:
    """T4-N5：一般 handoff 檔偽造 `## 附錄` ⇒ 仍 FAIL（非 synth 路徑）。"""
    rel = "handoffs/20990101-b4-n5-forged.md"
    content = (
        "# note\n\n"
        "## 附錄：findings 逐字保留（byte-faithful；勿改動下方任一 ## 區塊）\n\n"
        f"{OP_CLAIM}"
    )
    path = _write(tmp_path / rel, content)
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── T4-B1 ──────────────────────────────────────────────────────────


def test_t4_b1_two_appendix_sections_both_exempt_named(tmp_path: Path) -> None:
    """T4-B1：兩個 `## 附錄` ⇒ 具名行為：兩段皆豁免；中間 finding H2 亦豁免。"""
    rel = "handoffs/reconcile/20990101-b4-b1/synth.md"
    content = (
        "# Reconcile — b4-b1\n\n"
        "## 群集 / 處置\n\n"
        "主委段無 claim。\n\n"
        "## 附錄：findings 逐字保留（byte-faithful；第一段）\n\n"
        f"## ID-A\n\n{OP_CLAIM}"
        "## 附錄：findings 逐字保留（byte-faithful；第二段）\n\n"
        f"## ID-B\n\n{OP_CLAIM}"
    )
    path = _write(tmp_path / rel, content)
    lines = vcc._appendix_exempt_line_numbers(rel, content)
    # 兩個 附錄 標題行都在集合內
    text_lines = content.splitlines()
    appendix_idxs = [i + 1 for i, l in enumerate(text_lines) if l.startswith("## 附錄")]
    assert len(appendix_idxs) == 2
    for i in appendix_idxs:
        assert i in lines
    proc = _run_checker("--files", str(path))
    assert proc.returncode == 0, proc.stderr


# ── T4-B2 ──────────────────────────────────────────────────────────


def test_t4_b2_missing_lock_or_unregistered_origin_not_exempt(tmp_path: Path) -> None:
    """T4-B2：sources.lock 缺失 或 原註冊不存在 ⇒ 不豁免。"""
    session = "20990101-b4-b2"
    name = "20990101-b4-b2-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(body)

    # lock 缺失、即使 audit 有註冊
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    proc1 = _run_checker("--files", str(copy))
    assert proc1.returncode != 0

    # lock 在、但無原註冊（清 audit 後只寫 lock）
    Path(os.environ[COMMITTEE_AUDIT_ENV]).write_text("", encoding="utf-8")
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    proc2 = _run_checker("--files", str(copy))
    assert proc2.returncode != 0


# ── T4-N6 ──────────────────────────────────────────────────────────


def test_t4_n6_docs_claim_still_fails(tmp_path: Path) -> None:
    """T4-N6：docs/ 一般文件無 backing 的 claim ⇒ 仍 FAIL。"""
    path = _write(
        tmp_path / "docs" / "20990101-b4-n6.md",
        f"## 已完成\n\n{OP_CLAIM}",
    )
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── 額外可證偽：順序顛倒 ──────────────────────────────────────────


def test_t4_boundary_appendix_then_cluster_cluster_still_blocked(tmp_path: Path) -> None:
    """邊界①：附錄在前、群集在後 ⇒ 群集段仍不豁免。"""
    rel = "handoffs/reconcile/20990101-b4-order/synth.md"
    content = (
        "# Reconcile — order\n\n"
        "## 附錄：findings 逐字保留（byte-faithful）\n\n"
        f"## FIND-1\n\n{OP_CLAIM}"
        "## 群集 / 處置\n\n"
        f"{OP_CLAIM}"
    )
    path = _write(tmp_path / rel, content)
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    # 附錄應豁免、群集應擋 → 至少 1 條 violation
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── Mutation probes ────────────────────────────────────────────────


def test_mutation_appendix_lines_always_empty_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4-M1：`_appendix_exempt_line_numbers` 恒回空集合 ⇒ 附錄 claim 由綠轉紅。"""
    rel = "handoffs/reconcile/20990101-b4-m1/synth.md"
    content = _synth_doc(
        cluster_body="主委無 claim。\n",
        appendix_body=f"## CODEX-M1\n\n{OP_CLAIM}",
    )
    path = _write(tmp_path / rel, content)

    # baseline 綠
    base = vcc.check_files([path])
    assert base == [], f"baseline 應豁免附錄: {base}"

    def _empty(_rel: str, _content: str) -> set[int]:
        return set()

    original = vcc._appendix_exempt_line_numbers
    monkeypatch.setattr(vcc, "_appendix_exempt_line_numbers", _empty)
    monkeypatch.setattr(sys.modules[__name__], "APPENDIX_LINES_TARGET", _empty)
    mutated = vcc.check_files([path])
    assert mutated, "mutation 後附錄應不再豁免"
    monkeypatch.setattr(vcc, "_appendix_exempt_line_numbers", original)
    monkeypatch.setattr(sys.modules[__name__], "APPENDIX_LINES_TARGET", original)
    restored = vcc.check_files([path])
    assert restored == [], f"還原後應再綠: {restored}"


def test_mutation_sources_exempt_always_false_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4-M2：`_is_committee_process_exempt` 恒 False ⇒ sources 副本由綠轉紅。"""
    session = "20990101-b4-m2"
    name = "20990101-b4-m2-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(body)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )

    base = vcc.check_files([copy])
    assert base == [], f"baseline sources 應豁免: {base}"

    def _never(*_a: object, **_k: object) -> bool:
        return False

    original = vcc._is_committee_process_exempt
    monkeypatch.setattr(vcc, "_is_committee_process_exempt", _never)
    monkeypatch.setattr(sys.modules[__name__], "SOURCES_EXEMPT_TARGET", _never)
    mutated = vcc.check_files([copy])
    assert mutated, "mutation 後 sources 應不豁免"
    monkeypatch.setattr(vcc, "_is_committee_process_exempt", original)
    monkeypatch.setattr(sys.modules[__name__], "SOURCES_EXEMPT_TARGET", original)
    restored = vcc.check_files([copy])
    assert restored == [], f"還原後應再綠: {restored}"


# ── B4-FIX P0/P1 回歸（豁免收窄；禁放寬）──────────────────────────


def test_t4_n7_direct_sources_registry_without_lock_not_exempt(tmp_path: Path) -> None:
    """T4-N7／P0-01：sources path 本身已註冊、無 lock ⇒ 不豁免（禁 direct 短路）。"""
    session = "20990101-b4-n7"
    name = "20990101-b4-n7-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    rel = f"handoffs/reconcile/{session}/sources/{name}"
    copy = _write(tmp_path / rel, body)
    digest = _sha(body)
    # 只註冊 sources 路徑本身（無 origin、無 lock）
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=rel,
        sha256=digest,
    )
    assert not vcc._is_committee_process_exempt(rel, copy, content_bytes=copy.read_bytes())
    proc = _run_checker("--files", str(copy))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_t4_n8_lock_duplicate_basename_other_path_not_exempt(tmp_path: Path) -> None:
    """T4-N8／P0-02：lock 以 realpath 指向同 basename 的**別的檔** ⇒ 不豁免。"""
    session = "20990101-b4-n8"
    name = "duplicate.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    digest = _sha(body)
    actual = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    other = _write(tmp_path / "handoffs" / "other" / name, body)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    # lock 只列 other 路徑（同 basename、同 sha）
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(other.resolve()),
    )
    assert not vcc._is_committee_process_exempt(
        f"handoffs/reconcile/{session}/sources/{name}",
        actual,
        content_bytes=actual.read_bytes(),
    )
    proc = _run_checker("--files", str(actual))
    assert proc.returncode != 0


def test_t4_n9_parent_directory_symlink_not_exempt(tmp_path: Path) -> None:
    """T4-N9／P0-03：sources/ 父目錄是 symlink ⇒ 不豁免（leaf 非 symlink）。"""
    session = "20990101-b4-n9"
    name = "20990101-b4-n9-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    digest = _sha(body)
    outside = tmp_path / "outside"
    outside.mkdir()
    real_file = _write(outside / name, body)
    session_dir = tmp_path / "handoffs" / "reconcile" / session
    session_dir.mkdir(parents=True)
    sources_link = session_dir / "sources"
    sources_link.symlink_to(outside)
    copy = sources_link / name
    assert copy.is_file()
    assert not copy.is_symlink()  # leaf 非 symlink；父目錄是
    assert sources_link.is_symlink()
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    _write_sources_lock(
        session_dir,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    rel = f"handoffs/reconcile/{session}/sources/{name}"
    assert not vcc._is_committee_process_exempt(
        rel, copy, content_bytes=copy.read_bytes()
    )
    proc = _run_checker("--files", str(copy))
    assert proc.returncode != 0
    # 用不到 real_file 僅防 linter
    assert real_file.is_file()


def test_t4_c2_staged_lock_not_worktree_lock(tmp_path: Path) -> None:
    """T4-C2／P0-04：staged lock 與 worktree lock 不同 ⇒ 以 staged 為準。"""
    session = "20990101-b4-c2"
    name = "20990101-b4-c2-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    digest = _sha(body)
    rel = f"handoffs/reconcile/{session}/sources/{name}"
    lock_rel = f"handoffs/reconcile/{session}/sources.lock"
    copy = _write(tmp_path / rel, body)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    # worktree lock：合法 entry（若誤讀 worktree 會豁免）
    good_lock = _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    good_lock_text = good_lock.read_text(encoding="utf-8")
    # staged lock：空 sources（不授權）
    empty_lock_text = json.dumps(
        {
            "version": 1,
            "session_id": session,
            "expected_roster": ["codex"],
            "sources": [],
            "freeze_ts": "2099-01-01T00:00:00Z",
            "closure_state": "open",
            "mode": "review",
            "round_id": "b4-c2",
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    # staged 空 lock + worktree 合法 lock ⇒ 不豁免
    assert not vcc._is_committee_process_exempt(
        rel,
        copy,
        content_bytes=body.encode("utf-8"),
        lock_text=empty_lock_text,
        prefer_staged_lock=True,
    )
    viol_empty = vcc.check_files(
        [copy],
        content_map={rel: body},
        lock_text_map={lock_rel: empty_lock_text},
        prefer_staged_lock=True,
    )
    assert viol_empty, "staged 空 lock 應不豁免"

    # staged 合法 lock + worktree 可被改壞仍豁免（同源 staged）
    good_lock.write_text('{"version":1,"sources":[]}\n', encoding="utf-8")  # wt 破壞
    viol_good = vcc.check_files(
        [copy],
        content_map={rel: body},
        lock_text_map={lock_rel: good_lock_text},
        prefer_staged_lock=True,
    )
    assert viol_good == [], f"staged 合法 lock 應豁免: {viol_good}"


def test_t4_n10_no_blank_h2_cluster_not_exempt(tmp_path: Path) -> None:
    """T4-N10／P1-05：附錄後 finding H2 與群集 H2 無空行 ⇒ 跨段 unit 不整段豁免。"""
    rel = "handoffs/reconcile/20990101-b4-n10/synth.md"
    # 故意：附錄 finding 標題後直接接群集 H2，中間無空行
    content = (
        "# Reconcile — n10\n\n"
        "## 附錄：findings 逐字保留（byte-faithful）\n\n"
        f"## FIND-1\n{OP_CLAIM_LINE}\n"
        "## 群集 / 處置\n"
        f"{OP_CLAIM_LINE}\n"
    )
    path = _write(tmp_path / rel, content)
    # 有空行的對照：群集應單獨被擋
    control = (
        "# Reconcile — n10c\n\n"
        "## 附錄：findings 逐字保留（byte-faithful）\n\n"
        f"## FIND-1\n\n{OP_CLAIM}"
        "## 群集 / 處置\n\n"
        f"{OP_CLAIM}"
    )
    control_path = _write(tmp_path / "handoffs/reconcile/20990101-b4-n10c/synth.md", control)
    control_v = vcc.check_files([control_path])
    assert control_v, "對照：有空行時群集 claim 應被擋"
    # 無空行注入：不得整段因附錄起始行而放行
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    viol = vcc.check_files([path])
    assert viol, "無空行 H2 邊界下群集 claim 不得豁免"


def test_t4_n11_registered_synth_cluster_not_file_exempt(tmp_path: Path) -> None:
    """T4-N11／P1-06：synth path 被 audit 直註冊 ⇒ 仍不得整檔豁免群集段。"""
    rel = "handoffs/reconcile/20990101-b4-n11/synth.md"
    content = _synth_doc(
        cluster_body=f"{OP_CLAIM}",
        appendix_body="附錄無 claim。\n",
    )
    path = _write(tmp_path / rel, content)
    digest = _sha(content)
    _append_committee_output(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=rel,
        sha256=digest,
    )
    # 檔級必須 False
    assert not vcc._is_committee_process_exempt(
        rel, path, content_bytes=path.read_bytes()
    )
    proc = _run_checker("--files", str(path))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


# ── B4-FIX2：committee_family_result 納入 origin registry ──────────


def test_t4_u3_family_result_registered_sources_exempt(tmp_path: Path) -> None:
    """T4-U3／FIX2：僅 committee_family_result 登錄原檔 ⇒ sources 副本可豁免。"""
    session = "20990101-b4-u3"
    name = "20990101-b4-u3-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    origin_rel = f"handoffs/{name}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(copy.read_bytes())
    _append_committee_family_result(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=origin_rel,
        sha256=digest,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    assert vcc._is_committee_process_exempt(
        f"handoffs/reconcile/{session}/sources/{name}",
        copy,
        content_bytes=copy.read_bytes(),
    )
    proc = _run_checker("--files", str(copy))
    assert proc.returncode == 0, proc.stderr


def test_t4_n12_family_result_sha_mismatch_not_exempt(tmp_path: Path) -> None:
    """T4-N12／FIX2：family_result 登錄但副本 sha 不符 ⇒ 不豁免（對照組）。"""
    session = "20990101-b4-n12"
    name = "20990101-b4-n12-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    good = _sha(body)
    _append_committee_family_result(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=good,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=good,
        realpath=str(copy.resolve()),
    )
    copy.write_text(body + "X", encoding="utf-8")
    assert not vcc._is_committee_process_exempt(
        f"handoffs/reconcile/{session}/sources/{name}",
        copy,
        content_bytes=copy.read_bytes(),
    )
    proc = _run_checker("--files", str(copy))
    assert proc.returncode != 0
    assert "operational claim" in proc.stderr or "缺少" in proc.stderr


def test_t4_n13_family_result_pending_or_empty_sha_not_exempt(tmp_path: Path) -> None:
    """T4-N13／FIX2：family_result 的 output_sha256 為 pending 或空 ⇒ 不豁免。"""
    session = "20990101-b4-n13"
    name = "20990101-b4-n13-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    digest = _sha(body)
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    audit.parent.mkdir(parents=True, exist_ok=True)
    for bad_sha in ("pending", ""):
        audit.write_text("", encoding="utf-8")
        _append_committee_family_result(
            audit,
            output_path=f"handoffs/{name}",
            sha256=bad_sha,
        )
        registered = vcc._committee_registered_files(
            vcc._COMMITTEE_SOURCES_REGISTRY_EVENTS
        )
        assert f"handoffs/{name}" not in registered, f"bad_sha={bad_sha!r} 不得入 registry"
        assert not vcc._is_committee_process_exempt(
            f"handoffs/reconcile/{session}/sources/{name}",
            copy,
            content_bytes=copy.read_bytes(),
        )
        proc = _run_checker("--files", str(copy))
        assert proc.returncode != 0, f"bad_sha={bad_sha!r} 應不豁免"


def test_t4_n14_family_result_does_not_exempt_plain_origin(tmp_path: Path) -> None:
    """T4-N14／R15-P1-01：一般 `handoffs/<name>.md` 原檔（**非** sources 副本）
    僅有 `committee_family_result` 登錄 ⇒ **不得**豁免。

    這是修補二的前後退步：family_result 曾進全域 registry，
    導致同一份原檔 rc 由 1 變 0（實測 `handoffs/20260803-govflow-todo-r2-grok.md`）。
    修法＝family_result 只供 `sources/` 回退用；本測固定該邊界。
    """
    name = "20990101-b4-n14-codex.md"
    rel = f"handoffs/{name}"
    body = f"## 已完成\n\n{OP_CLAIM}"
    origin = _write(tmp_path / "handoffs" / name, body)
    digest = _sha(body)
    _append_committee_family_result(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=rel,
        sha256=digest,
    )
    # direct registry 不得收 family_result
    direct = vcc._committee_registered_files(vcc._COMMITTEE_DIRECT_REGISTRY_EVENTS)
    assert rel not in direct, "family_result 不得進 direct registry"
    # 但 sources registry 收得到（證明事件本身有效，本測不是因為事件沒寫進去才綠）
    sources_reg = vcc._committee_registered_files(vcc._COMMITTEE_SOURCES_REGISTRY_EVENTS)
    assert rel in sources_reg, "對照：sources registry 應收得到同一筆"

    assert not vcc._is_committee_process_exempt(
        rel, origin, content_bytes=origin.read_bytes()
    )
    proc = _run_checker("--files", str(origin))
    assert proc.returncode != 0, "一般原檔不得因 family_result 取得豁免"


def test_t4_n15_format_failed_family_result_not_exempt(tmp_path: Path) -> None:
    """T4-N15／R15-P1-01：`result_state=format-failed` 的 family_result ⇒ 不入 registry。

    `cx_run.sh:253` 明定 format-failed 仍帶**非空** sha，故 `pending`／空值那道門擋不住它。
    """
    session = "20990101-b4-n15"
    name = "20990101-b4-n15-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(body)
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )
    audit = Path(os.environ[COMMITTEE_AUDIT_ENV])
    rel_copy = f"handoffs/reconcile/{session}/sources/{name}"

    # 對照組先行：同一筆若是 success ⇒ 必須豁免（否則本測的陰性結果是量測失效）
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text("", encoding="utf-8")
    _append_committee_family_result(
        audit, output_path=f"handoffs/{name}", sha256=digest, result_state="success"
    )
    assert vcc._is_committee_process_exempt(
        rel_copy, copy, content_bytes=copy.read_bytes()
    ), "對照組：success 應豁免"

    # 主測：改成 format-failed（sha 完全相同）⇒ 不得豁免
    audit.write_text("", encoding="utf-8")
    _append_committee_family_result(
        audit,
        output_path=f"handoffs/{name}",
        sha256=digest,
        result_state="format-failed",
    )
    assert not vcc._is_committee_process_exempt(
        rel_copy, copy, content_bytes=copy.read_bytes()
    ), "format-failed 的產出不得取得豁免"
    proc = _run_checker("--files", str(copy))
    assert proc.returncode != 0


def test_mutation_family_result_removed_from_whitelist_turns_red(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T4-M3／FIX2：白名單移除 committee_family_result ⇒ 僅靠 family_result 登錄的副本轉紅。"""
    session = "20990101-b4-m3"
    name = "20990101-b4-m3-codex.md"
    body = f"## 已完成\n\n{OP_CLAIM}"
    copy = _write(
        tmp_path / "handoffs" / "reconcile" / session / "sources" / name,
        body,
    )
    digest = _sha(body)
    _append_committee_family_result(
        Path(os.environ[COMMITTEE_AUDIT_ENV]),
        output_path=f"handoffs/{name}",
        sha256=digest,
    )
    _write_sources_lock(
        tmp_path / "handoffs" / "reconcile" / session,
        session_id=session,
        name=name,
        sha256=digest,
        realpath=str(copy.resolve()),
    )

    base = vcc.check_files([copy])
    assert base == [], f"baseline family_result 應豁免: {base}"

    narrowed = frozenset({"committee_dispatch", "committee_output"})
    original = vcc._COMMITTEE_SOURCES_REGISTRY_EVENTS
    monkeypatch.setattr(vcc, "_COMMITTEE_SOURCES_REGISTRY_EVENTS", narrowed)
    monkeypatch.setattr(sys.modules[__name__], "REGISTRY_EVENTS_TARGET", narrowed)
    mutated = vcc.check_files([copy])
    assert mutated, "白名單去掉 family_result 後應不豁免"
    monkeypatch.setattr(vcc, "_COMMITTEE_SOURCES_REGISTRY_EVENTS", original)
    monkeypatch.setattr(sys.modules[__name__], "REGISTRY_EVENTS_TARGET", original)
    restored = vcc.check_files([copy])
    assert restored == [], f"還原後應再綠: {restored}"
