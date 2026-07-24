"""B6 Task 7.1 — 委員語意 stamp 行為 oracle + committee_accepted producer。

nodeid:
  test_semantic_stamp_after_completeness
  test_fresh_none_allows_final_stamp

契約:
  - 順序不可逆：機械層 PASS 在前，語意 stamp 在後
  - 機械 exit≠0 → 委員試蓋 final → gate 拒發
  - fresh=NONE（0 新 finding）+ 機械 PASS → 允許 final stamp
  - producer 真產 committee_accepted.json{accepted_ids:[]} 餵 Oracle⑤
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
PRODUCER_SH = REPO_ROOT / "scripts" / "write_committee_accepted.sh"
SPEC = REPO_ROOT / "docs" / "CONVERGENCE_METHOD_SPEC.md"
CHARTER = REPO_ROOT / "templates" / "COMMITTEE_SEMANTIC_REVIEW_TEMPLATE.md"


def _sha256_bytes(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _sha12(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _finding(
    fid: str,
    *,
    assert_text: str = "semantic assert",
    code_text: str = "path:1",
    src: str = "sources/review.md",
) -> str:
    d = _sha12(f"{fid}|{assert_text}|{code_text}")
    return (
        f"## {fid}\n\n"
        f"**斷言**: {assert_text}\n\n"
        f"**碼證**: {code_text}\n\n"
        f"**來源摘要**: {src}#{d}\n"
    )


def _conv_session(base: Path, name: str) -> Path:
    """合法 convergence 路徑：…/handoffs/reconcile/<session>/（觸發 completeness gate）。"""
    session = base / "handoffs" / "reconcile" / name
    (session / "sources").mkdir(parents=True)
    return session


def _write_lock(session: Path, *, roster: list[str], sources: list[dict]) -> None:
    lock = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": roster,
        "sources": sorted(sources, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    (session / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _stub_pass(path: Path) -> Path:
    path.write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            echo "STUB PASS: $*"
            exit 0
            """
        ),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def _run_gate_high_risk(
    *,
    gate_dir: Path,
    reconcile: Path,
    adversarial: Path,
    env_extra: dict[str, str] | None = None,
    task_id: str = "conv-semantic-stamp-unit",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    env.pop("RECONCILE_STAMPS_CHECK_OVERRIDE", None)
    env.pop("COMPLETENESS_CHECK_OVERRIDE", None)
    if env_extra:
        env.update(env_extra)
    cmd = [
        "bash",
        str(GATE_SH),
        "dispatch",
        "--intent",
        "B6 semantic stamp unit test",
        "--risk",
        "high",
        "--facts-asked",
        "none-needed:unit-test",
        "--review-role",
        "single-executor:n/a",
        "--template",
        "n/a:impl semantic stamp unit test",
        "--spec",
        str(SPEC),
        "--adversarial",
        str(adversarial),
        "--reconcile",
        str(reconcile),
        "--task-id",
        task_id,
        "--output",
        f"handoffs/{task_id}.md",
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_producer(
    session: Path, review: Path, *, force: bool = False
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if force:
        env["GOVERNANCE_TEST_HARNESS"] = "1"
    cmd = [
        "bash",
        str(PRODUCER_SH),
        "--session",
        str(session),
        "--review",
        str(review),
    ]
    if force:
        cmd.append("--force")
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_completeness(session: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)
    env.pop("COMPLETENESS_ALLOW_ARGV_SOURCES", None)
    return subprocess.run(
        ["bash", str(COMPLETENESS_SH), "--lock", str(session / "sources.lock")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _fresh_none_review(path: Path) -> Path:
    """合法語意審：Fresh findings: NONE + Mechanical precondition + Verdict APPROVED。"""
    path.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Scope
            只審語意（講水/降級/錯併）。

            ## Mechanical precondition
            - completeness: PASS（rc=0；由機器出口核實，非本檔自證）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ## Verdict
            APPROVED — Fresh findings: NONE → 收斂蓋章
            """
        ),
        encoding="utf-8",
    )
    return path


def _illegal_missing_id_review(path: Path) -> Path:
    """非法：只列漏掉的 ID（侵佔機械層）。"""
    path.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Mechanical precondition
            - completeness: PASS（rc=0）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ## 漏掉的 ID
            - CODEX-R1-P0-01
            - COMPOSER-R1-P1-02

            ## Verdict
            APPROVED
            """
        ),
        encoding="utf-8",
    )
    return path


def _session_with_union(tmp_path: Path, name: str = "sess_prod") -> Path:
    """最小合法 session：1 source / 1 canonical ID，供 producer 反例測試。"""
    session = tmp_path / name
    sources = session / "sources"
    sources.mkdir(parents=True)
    b1 = _finding("CODEX-R1-P2-01", src="sources/a-codex.md")
    f1 = sources / "a-codex.md"
    f1.write_text(b1, encoding="utf-8")
    (session / "synth.md").write_text(b1, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex"],
        sources=[
            {
                "realpath": str(f1.resolve()),
                "sha256": _sha256_bytes(b1.encode()),
                "family": "codex",
            },
        ],
    )
    return session


# ---------------------------------------------------------------------------
# Charter smoke（可證偽 grep 對齊 TODO 驗證）
# ---------------------------------------------------------------------------


def test_charter_forbids_missing_id_listing() -> None:
    """smoke：charter 須含 禁列…ID 或 只審語意（TODO 驗證 grep）。"""
    assert CHARTER.is_file(), f"缺 charter: {CHARTER}"
    text = CHARTER.read_text(encoding="utf-8")
    import re

    n = len(re.findall(r"禁列.*ID|只審語意", text))
    assert n >= 1, f"charter 須匹配 禁列.*ID|只審語意; n={n}"


# ---------------------------------------------------------------------------
# 行為 oracle 1：機械未 PASS → 委員試 final → gate 拒
# ---------------------------------------------------------------------------


def test_semantic_stamp_after_completeness(tmp_path: Path) -> None:
    """機械層 exit≠0 之下委員試蓋 final → gate final 拒發（順序不可逆）。

    構造：roster 3 家、sources 只 2 檔 → completeness rc≠0。
    即使寫了語意 stamp / 假 committee_accepted，gate dispatch 仍拒。
    """
    if not SPEC.is_file() or not GATE_SH.is_file():
        pytest.skip("gate/SPEC missing")

    session = _conv_session(tmp_path, "sess_mech_fail")
    sources = session / "sources"
    b_codex = _finding("CODEX-R1-P2-01", src="sources/review-codex.md")
    b_comp = _finding("COMPOSER-R1-P2-01", src="sources/review-composer.md")
    b_grok = _finding("GROK-R1-P2-01", src="sources/review-grok.md")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")
    # synth 假合併含 grok，但來源缺 grok
    (session / "synth.md").write_text(b_codex + "\n" + b_comp + "\n" + b_grok, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "composer", "grok"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )

    # 前置：機械層必須 rc≠0
    direct = _run_completeness(session)
    assert direct.returncode != 0, (
        f"前置機械層應 FAIL; rc={direct.returncode} "
        f"out={(direct.stdout or '') + (direct.stderr or '')!r}"
    )

    # 委員仍寫語意 stamp + 假 accepted（繞 residual 亦不可蓋 final）
    review = _fresh_none_review(session / "semantic_review.md")
    # producer 在 incomplete session 仍可能抽出 present sources 的 ID——
    # 但 gate 必須在 completeness 層拒發（順序：機械先於語意）
    prod = _run_producer(session, review)
    # producer 可成功寫 present union；重點是 gate 仍拒
    if prod.returncode == 0:
        assert (session / "committee_accepted.json").is_file()

    # V-B：--reconcile 指既有 synth.md（禁建 reconcile.md 覆蓋 synth union）
    recon = session / "synth.md"
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")

    stamp_stub = _stub_pass(tmp_path / "stamps_pass.sh")
    gate_dir = tmp_path / "gate_tokens"
    gate_dir.mkdir()

    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
            # 真 completeness，不 override
        },
        task_id="conv-semantic-after-mech",
    )
    assert result.returncode != 0, (
        f"機械層未 PASS 時 final 應拒; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "completeness" in combined.lower(), f"須到 completeness 層: {combined!r}"
    # 不得發 token
    tokens = list(gate_dir.glob("*.token"))
    assert tokens == [], f"不應發 token: {tokens}"


# ---------------------------------------------------------------------------
# 行為 oracle 2：fresh=NONE → 允許 final
# ---------------------------------------------------------------------------


def test_fresh_none_allows_final_stamp(tmp_path: Path) -> None:
    """一輪 fresh=NONE（0 新 finding）+ 機械 PASS → 允許 final stamp。

    真 producer 寫 committee_accepted.json → residual=0 → gate PASS。
    """
    if not SPEC.is_file() or not GATE_SH.is_file():
        pytest.skip("gate/SPEC missing")
    if not PRODUCER_SH.is_file():
        pytest.fail(f"缺 producer: {PRODUCER_SH}")

    session = _conv_session(tmp_path, "sess_fresh_none")
    sources = session / "sources"
    b_codex = _finding("CODEX-R1-P2-01", src="sources/review-codex.md")
    b_comp = _finding("COMPOSER-R1-P2-01", src="sources/review-composer.md")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")
    synth = b_codex + "\n" + b_comp
    (session / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "composer"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )

    # 機械 PASS（尚無 committee_accepted → residual 不強制）
    pre = _run_completeness(session)
    assert pre.returncode == 0, (
        f"前置機械應 PASS; rc={pre.returncode} "
        f"out={(pre.stdout or '') + (pre.stderr or '')!r}"
    )

    # 真 producer：fresh=NONE → accepted_ids = union
    review = _fresh_none_review(session / "semantic_review.md")
    prod = _run_producer(session, review)
    assert prod.returncode == 0, (
        f"producer 應 PASS; rc={prod.returncode} "
        f"stdout={prod.stdout!r} stderr={prod.stderr!r}"
    )
    acc_path = session / "committee_accepted.json"
    assert acc_path.is_file()
    acc = json.loads(acc_path.read_text(encoding="utf-8"))
    assert "accepted_ids" in acc
    assert set(acc["accepted_ids"]) == {"CODEX-R1-P2-01", "COMPOSER-R1-P2-01"}

    # residual=0 後 completeness 仍 PASS
    post = _run_completeness(session)
    assert post.returncode == 0, (
        f"residual=0 後應 PASS; rc={post.returncode} "
        f"out={(post.stdout or '') + (post.stderr or '')!r}"
    )
    assert "residual=0" in ((post.stdout or "") + (post.stderr or ""))

    # 非法 charter 路徑可證偽：只列漏 ID → producer 拒
    bad_review = _illegal_missing_id_review(tmp_path / "bad_semantic.md")
    bad = _run_producer(session, bad_review, force=True)
    assert bad.returncode != 0, (
        f"禁列漏掉的 ID 應拒; rc={bad.returncode} stderr={bad.stderr!r}"
    )
    assert "禁列" in bad.stderr or "漏掉" in bad.stderr or "機械" in bad.stderr

    # force 寫回合法 accepted（上一步 force 可能未覆寫；確保 residual 仍 0）
    ok2 = _run_producer(session, review, force=True)
    assert ok2.returncode == 0, f"合法 force 重寫應 PASS: {ok2.stderr!r}"

    # V-B：--reconcile 指既有 synth.md（禁建 reconcile.md 覆蓋 synth union）
    recon = session / "synth.md"
    adv = tmp_path / "adv.md"
    adv.write_text("# ADV\n\nVerdict: APPROVED\n", encoding="utf-8")

    stamp_stub = _stub_pass(tmp_path / "stamps_pass.sh")
    gate_dir = tmp_path / "gate_tokens"
    gate_dir.mkdir()

    result = _run_gate_high_risk(
        gate_dir=gate_dir,
        reconcile=recon,
        adversarial=adv,
        env_extra={
            "GOVERNANCE_TEST_HARNESS": "1",
            "RECONCILE_STAMPS_CHECK_OVERRIDE": str(stamp_stub),
        },
        task_id="conv-semantic-fresh-none",
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, (
        f"fresh=NONE + 機械 PASS 應允許 final; "
        f"rc={result.returncode} out={combined!r}"
    )
    assert "GATE PASS" in combined, f"須 GATE PASS: {combined!r}"
    tokens = list(gate_dir.glob("*.token"))
    assert len(tokens) >= 1, f"應發 token: gate_dir={list(gate_dir.iterdir())}"


# ---------------------------------------------------------------------------
# 可證偽：殘缺 accepted → residual 擋（接真 producer schema）
# ---------------------------------------------------------------------------


def test_producer_residual_feeds_oracle5(tmp_path: Path) -> None:
    """producer 寫全量 accepted 後若人手刪 1 ID → completeness residual>0。"""
    session = tmp_path / "sess_residual"
    sources = session / "sources"
    sources.mkdir(parents=True)
    b1 = _finding("CODEX-R1-P2-01", src="sources/a-codex.md")
    b2 = _finding("COMPOSER-R1-P2-01", src="sources/b-composer.md")
    f1 = sources / "a-codex.md"
    f2 = sources / "b-composer.md"
    f1.write_text(b1, encoding="utf-8")
    f2.write_text(b2, encoding="utf-8")
    (session / "synth.md").write_text(b1 + "\n" + b2, encoding="utf-8")
    _write_lock(
        session,
        roster=["codex", "composer"],
        sources=[
            {
                "realpath": str(f1.resolve()),
                "sha256": _sha256_bytes(b1.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f2.resolve()),
                "sha256": _sha256_bytes(b2.encode()),
                "family": "composer",
            },
        ],
    )
    review = _fresh_none_review(session / "sem.md")
    assert _run_producer(session, review).returncode == 0
    acc_path = session / "committee_accepted.json"
    data = json.loads(acc_path.read_text(encoding="utf-8"))
    data["accepted_ids"] = ["CODEX-R1-P2-01"]  # 缺 1
    acc_path.write_text(json.dumps(data) + "\n", encoding="utf-8")
    r = _run_completeness(session)
    assert r.returncode != 0
    out = (r.stdout or "") + (r.stderr or "")
    assert "residual" in out.lower()
    assert "COMPOSER-R1-P2-01" in out


# ---------------------------------------------------------------------------
# CODEX-B6-P1-01 反例：裸 ID 清單 / 缺語意欄位 → producer 拒
# ---------------------------------------------------------------------------


def test_producer_rejects_bare_id_list(tmp_path: Path) -> None:
    """裸列 canonical-ID 清單（無語意正文）冒充語意審 → producer exit≠0、不寫 accepted。

    可證偽：若 producer 只認 Fresh findings: NONE marker 就寫 accepted，本測紅。
    """
    if not PRODUCER_SH.is_file():
        pytest.fail(f"缺 producer: {PRODUCER_SH}")

    session = _session_with_union(tmp_path, "sess_bare_id")
    review = session / "bare_id_review.md"
    # Codex probe 形：marker + ## Findings 下裸 bullet ID（無 **斷言**/**碼證**）
    review.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Mechanical precondition
            - completeness: PASS（rc=0）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ## Findings
            - CODEX-R1-P0-01
            - COMPOSER-R1-P1-02

            ## Verdict
            APPROVED — Fresh findings: NONE → 收斂蓋章
            """
        ),
        encoding="utf-8",
    )
    acc = session / "committee_accepted.json"
    assert not acc.is_file()
    r = _run_producer(session, review)
    assert r.returncode != 0, (
        f"裸 ID 清單應拒; rc={r.returncode} stdout={r.stdout!r} stderr={r.stderr!r}"
    )
    err = (r.stderr or "") + (r.stdout or "")
    assert any(
        k in err
        for k in (
            "裸列",
            "canonical-ID",
            "非法語意審",
            "CODEX-R1-P0-01",
            "冒充",
        )
    ), f"須指向裸 ID / 非法語意審: {err!r}"
    assert not acc.is_file(), "拒寫時不得留下 committee_accepted.json"

    # 第二形：裸 ## FAM-R1-Pn-NN heading 無語意正文
    review2 = session / "bare_heading.md"
    review2.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Mechanical precondition
            - completeness: PASS（rc=0）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ## CODEX-R1-P0-01

            ## Verdict
            APPROVED
            """
        ),
        encoding="utf-8",
    )
    r2 = _run_producer(session, review2)
    assert r2.returncode != 0, (
        f"裸 heading ID 應拒; rc={r2.returncode} stderr={r2.stderr!r}"
    )
    assert not acc.is_file()

    # 對照：合法語意審仍可產 accepted（防誤殺）
    ok_review = _fresh_none_review(session / "ok_sem.md")
    ok = _run_producer(session, ok_review)
    assert ok.returncode == 0, f"合法語意審應 PASS: {ok.stderr!r}"
    assert acc.is_file()
    data = json.loads(acc.read_text(encoding="utf-8"))
    assert set(data["accepted_ids"]) == {"CODEX-R1-P2-01"}


def test_producer_requires_semantic_fields(tmp_path: Path) -> None:
    """SEM finding 缺 polarity / **斷言** / **碼證** → producer exit≠0、不寫 accepted。

    可證偽：若 SEM-01 僅有標題或空殼正文仍 rc=0，本測紅。
    """
    if not PRODUCER_SH.is_file():
        pytest.fail(f"缺 producer: {PRODUCER_SH}")

    session = _session_with_union(tmp_path, "sess_sem_fields")
    acc = session / "committee_accepted.json"

    # 缺 **斷言**/**碼證**/polarity 的 SEM 殼
    review = session / "sem_shell.md"
    review.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Mechanical precondition
            - completeness: PASS（rc=0）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ## Semantic findings
            ### SEM-01
            這裡只有空話，沒有斷言也沒有碼證。

            ## Verdict
            APPROVED
            """
        ),
        encoding="utf-8",
    )
    r = _run_producer(session, review)
    assert r.returncode != 0, (
        f"缺語意欄位的 SEM 應拒; rc={r.returncode} stderr={r.stderr!r}"
    )
    err = (r.stderr or "") + (r.stdout or "")
    assert any(
        k in err
        for k in (
            "語意欄位",
            "polarity",
            "斷言",
            "碼證",
            "SEM-01",
            "混淆",
        )
    ), f"須指向語意欄位/SEM: {err!r}"
    assert not acc.is_file()

    # 有 SEM 標題但完全無 body 欄位
    review2 = session / "sem_empty.md"
    review2.write_text(
        textwrap.dedent(
            """\
            # 委員語意審

            ## Mechanical precondition
            - completeness: PASS（rc=0）
            - sources.lock: FROZEN

            ## Fresh findings
            NONE

            ### SEM-02 錯併

            ## Verdict
            APPROVED
            """
        ),
        encoding="utf-8",
    )
    r2 = _run_producer(session, review2)
    assert r2.returncode != 0, (
        f"空殼 SEM-02 應拒; rc={r2.returncode} stderr={r2.stderr!r}"
    )
    assert not acc.is_file()

    # 對照：合法 NONE 路徑可寫
    ok = _run_producer(session, _fresh_none_review(session / "ok2.md"))
    assert ok.returncode == 0, f"合法應 PASS: {ok.stderr!r}"
    assert acc.is_file()
