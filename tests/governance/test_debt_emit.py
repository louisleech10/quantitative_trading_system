"""P1-6 B2 Task 1.1：audit_append.sh 唯一寫入點 + 原子 predicate+append。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_APPEND_SH = REPO_ROOT / "scripts" / "audit_append.sh"
REGISTRY = REPO_ROOT / "scripts" / "audit_events.json"
# 探針可 monkeypatch 的模組常數（真決定呼叫哪支腳本）
AUDIT_APPEND_TARGET = AUDIT_APPEND_SH


def _run(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """執行 audit_append；rc 直接取，不經 pipe。"""
    base = os.environ.copy()
    if env:
        base.update(env)
    return subprocess.run(
        ["bash", str(AUDIT_APPEND_TARGET), *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=base,
    )


def _harness(tmp_path: Path) -> tuple[Path, Path, Path]:
    """隔離 repo 副本：scripts + 空 audit。"""
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(AUDIT_APPEND_SH, scripts / "audit_append.sh")
    shutil.copy2(REGISTRY, scripts / "audit_events.json")
    (scripts / "audit_append.sh").chmod(0o755)
    audit = root / ".claude" / "gate" / "audit.log"
    audit.parent.mkdir(parents=True)
    audit.write_text("", encoding="utf-8")
    return root, scripts / "audit_append.sh", audit


def _open_fields(
    *,
    round_id: str = "round-1",
    task_id: str = "task-1",
    session_name: str = "sess-a",
    actor: str = "test-actor",
) -> list[str]:
    """committee_round_open 最小必填欄位 argv 片段。"""
    return [
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"task_id={task_id}",
        "--field",
        "brief_path=handoffs/brief.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        'participants=@["codex","composer"]',
        "--field",
        'expected_outputs=@{"codex":"handoffs/x-codex.md","composer":"handoffs/x-composer.md"}',
        "--field",
        f"session_name={session_name}",
        "--field",
        f"actor={actor}",
        "--field",
        "origin_script=committee_run.sh",
    ]


def _result_fields(
    *,
    round_id: str = "round-1",
    family: str = "codex",
    actor: str = "test-actor",
) -> list[str]:
    """committee_family_result 最小必填。"""
    return [
        "--event",
        "committee_family_result",
        "--field",
        f"round_id={round_id}",
        "--field",
        f"family={family}",
        "--field",
        "attempt_id=att-1",
        "--field",
        "cli_rc=0",
        "--field",
        "output_path=handoffs/out.md",
        "--field",
        "output_sha256=" + ("c" * 64),
        "--field",
        "result_state=success",
        "--field",
        f"actor={actor}",
        "--field",
        "origin_script=cx_run.sh",
    ]


def _read_json_lines(audit: Path) -> list[dict]:
    """只讀 { 開頭且可解析的 JSON 行。"""
    out: list[dict] = []
    if not audit.is_file():
        return out
    for line in audit.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            rec = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(rec, dict):
            out.append(rec)
    return out


def _env_for(audit: Path) -> dict[str, str]:
    return {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
    }


def _mutate_script(path: Path, old: str, new: str) -> str:
    """就地變異腳本副本；回傳原文供復原。"""
    original = path.read_text(encoding="utf-8")
    assert old in original, f"mutation anchor missing: {old!r}"
    path.write_text(original.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)
    return original


# ── 基本行為 ──────────────────────────────────────────────


def test_audit_missing_creates_file(tmp_path: Path) -> None:
    """邊界：audit 檔不存在 → 建立而非崩潰。"""
    root, script, audit = _harness(tmp_path)
    audit.unlink()
    assert not audit.exists()
    global AUDIT_APPEND_TARGET
    prev = AUDIT_APPEND_TARGET
    try:
        # 直接改模組常數給本測用
        import tests.governance.test_debt_emit as self_mod

        self_mod.AUDIT_APPEND_TARGET = script
        result = _run(*_open_fields(), env=_env_for(audit), cwd=root)
    finally:
        import tests.governance.test_debt_emit as self_mod

        self_mod.AUDIT_APPEND_TARGET = prev
    assert result.returncode == 0, result.stdout + result.stderr
    assert audit.is_file()
    recs = _read_json_lines(audit)
    assert len(recs) == 1
    assert recs[0]["event"] == "committee_round_open"
    assert recs[0]["sequence"] == 1


def test_producer_forced_ignores_caller(tmp_path: Path) -> None:
    """呼叫端傳 producer=fake → 落地值為 audit_append.sh。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        args = _open_fields() + ["--field", "producer=fake"]
        result = _run(*args, env=_env_for(audit), cwd=root)
        assert result.returncode == 0, result.stdout + result.stderr
        rec = _read_json_lines(audit)[0]
        assert rec["producer"] == "audit_append.sh"
        assert rec["producer"] != "fake"
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_missing_required_field_fail_closed(tmp_path: Path) -> None:
    """缺必填欄 → rc≠0。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        # 故意省略 actor
        args = [a for a in _open_fields() if not a.startswith("actor=") and a != "test-actor"]
        # 上面過濾不完整；明確組一組缺 actor
        args = [
            "--event",
            "committee_round_open",
            "--field",
            "round_id=r1",
            "--field",
            "task_id=t1",
            "--field",
            "brief_path=b.md",
            "--field",
            "brief_sha256=" + ("a" * 64),
            "--field",
            "brief_sha256_norm=" + ("b" * 64),
            "--field",
            "lock_mode=discovery",
            "--field",
            'participants=@["codex"]',
            "--field",
            'expected_outputs=@{"codex":"o.md"}',
            "--field",
            "session_name=s1",
            "--field",
            "origin_script=committee_run.sh",
            # 缺 actor
        ]
        result = _run(*args, env=_env_for(audit), cwd=root)
        assert result.returncode != 0
        assert "缺必填" in (result.stdout + result.stderr)
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_registry_missing_or_corrupt_fail_closed(tmp_path: Path) -> None:
    """registry 缺檔 / JSON 壞 → rc≠0。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    reg = root / "scripts" / "audit_events.json"
    try:
        # corrupt
        reg.write_text("{not json", encoding="utf-8")
        result = _run(*_open_fields(), env=_env_for(audit), cwd=root)
        assert result.returncode != 0

        # missing
        reg.unlink()
        result2 = _run(*_open_fields(), env=_env_for(audit), cwd=root)
        assert result2.returncode != 0
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_illegal_json_field_rejected(tmp_path: Path) -> None:
    """--field k=@<非法 JSON> → 拒寫。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        args = _open_fields()
        # 覆寫 participants 為壞 JSON
        args = [a for a in args if a != 'participants=@["codex","composer"]']
        # remove the pair properly
        cleaned: list[str] = []
        skip_next = False
        for i, a in enumerate(args):
            if skip_next:
                skip_next = False
                continue
            if a == "--field" and i + 1 < len(args) and args[i + 1].startswith("participants="):
                skip_next = True
                continue
            cleaned.append(a)
        cleaned += ["--field", "participants=@[not-json"]
        result = _run(*cleaned, env=_env_for(audit), cwd=root)
        assert result.returncode != 0
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_debt_audit_override_requires_harness(tmp_path: Path) -> None:
    """DEBT_AUDIT_OVERRIDE 未綁 harness → fail-closed。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = {"DEBT_AUDIT_OVERRIDE": str(audit)}
        # 明確不設 harness
        env_full = os.environ.copy()
        env_full.pop("GOVERNANCE_TEST_HARNESS", None)
        env_full["DEBT_AUDIT_OVERRIDE"] = str(audit)
        result = subprocess.run(
            ["bash", str(script), *_open_fields()],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            env=env_full,
        )
        assert result.returncode != 0
        assert "GOVERNANCE_TEST_HARNESS" in (result.stdout + result.stderr)
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_legacy_lines_do_not_break_sequence(tmp_path: Path) -> None:
    """混入 legacy 紀錄 → 不誤報缺號；debt sequence 仍連續。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        # 預置 legacy 行（無 sequence）
        legacy = {
            "event": "committee_dispatch",
            "task_id": "legacy-1",
            "family": "codex",
            "output_path": "",
            "output_sha256": "pending",
            "ts": "2026-07-01T00:00:00Z",
        }
        audit.write_text(json.dumps(legacy, ensure_ascii=False) + "\n", encoding="utf-8")
        r1 = _run(*_result_fields(family="codex"), env=_env_for(audit), cwd=root)
        r2 = _run(*_result_fields(family="composer"), env=_env_for(audit), cwd=root)
        assert r1.returncode == 0, r1.stdout + r1.stderr
        assert r2.returncode == 0, r2.stdout + r2.stderr
        debt = [x for x in _read_json_lines(audit) if x.get("event") == "committee_family_result"]
        seqs = sorted(int(x["sequence"]) for x in debt)
        assert seqs == [1, 2]
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_lock_timeout_fail_closed(tmp_path: Path) -> None:
    """取鎖逾時 → rc≠0。"""
    root, script, audit = _harness(tmp_path)
    lockdir = Path(str(audit) + ".lock")
    lockdir.mkdir(parents=True)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        env["AUDIT_APPEND_MAX_RETRY"] = "3"
        env["AUDIT_APPEND_RETRY_INTERVAL"] = "0.01"
        result = _run(*_open_fields(), env=env, cwd=root)
        assert result.returncode != 0
        assert "取鎖逾時" in (result.stdout + result.stderr)
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev
        if lockdir.is_dir():
            lockdir.rmdir()


def test_caller_holding_lock_cannot_succeed(tmp_path: Path) -> None:
    """呼叫端自行持鎖後再呼叫本腳本 → 不得成功（證偽鎖交接）。"""
    root, script, audit = _harness(tmp_path)
    lockdir = Path(str(audit) + ".lock")
    lockdir.mkdir(parents=True)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        env["AUDIT_APPEND_MAX_RETRY"] = "5"
        env["AUDIT_APPEND_RETRY_INTERVAL"] = "0.01"
        result = _run(
            "--require-absent-session",
            "sess-held",
            *_open_fields(session_name="sess-held"),
            env=env,
            cwd=root,
        )
        assert result.returncode != 0
        assert not any(
            r.get("session_name") == "sess-held" for r in _read_json_lines(audit)
        )
    finally:
        m.AUDIT_APPEND_TARGET = prev
        if lockdir.is_dir():
            lockdir.rmdir()


# ── 改法⑥ 三態 ──────────────────────────────────────────


def test_require_absent_session_rejects_duplicate(tmp_path: Path) -> None:
    """已有同名 committee_round_open → rc≠0 且 audit 行數不變。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        r1 = _run(
            "--require-absent-session",
            "S",
            *_open_fields(session_name="S", round_id="r-a"),
            env=_env_for(audit),
            cwd=root,
        )
        assert r1.returncode == 0, r1.stdout + r1.stderr
        before = audit.read_text(encoding="utf-8")
        n_before = len(_read_json_lines(audit))
        r2 = _run(
            "--require-absent-session",
            "S",
            *_open_fields(session_name="S", round_id="r-b"),
            env=_env_for(audit),
            cwd=root,
        )
        assert r2.returncode != 0
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_session_uniqueness_is_atomic_with_append(tmp_path: Path) -> None:
    """兩程序同時 --require-absent-session S → 恰一筆成功；audit 中 S 恆一筆（M34）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        env["AUDIT_APPEND_MAX_RETRY"] = "200"
        env["AUDIT_APPEND_RETRY_INTERVAL"] = "0.02"

        def one(tag: str) -> int:
            r = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--require-absent-session",
                    "S",
                    *_open_fields(session_name="S", round_id=f"r-{tag}", task_id=f"t-{tag}"),
                ],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, **env},
            )
            return r.returncode

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(one, "a"), pool.submit(one, "b")]
            rcs = [f.result() for f in as_completed(futs)]
        assert sorted(rcs).count(0) == 1, f"expected exactly one success, got rcs={rcs}"
        assert any(rc != 0 for rc in rcs)
        opens = [
            r
            for r in _read_json_lines(audit)
            if r.get("event") == "committee_round_open" and r.get("session_name") == "S"
        ]
        assert len(opens) == 1
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_concurrent_append_sequence_unique(tmp_path: Path) -> None:
    """兩程序併發各寫 100 筆 → sorted(seqs) == range(1, 201)。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        env["AUDIT_APPEND_MAX_RETRY"] = "500"
        env["AUDIT_APPEND_RETRY_INTERVAL"] = "0.01"
        n = 100

        def worker(wid: int) -> list[int]:
            codes: list[int] = []
            for i in range(n):
                r = subprocess.run(
                    [
                        "bash",
                        str(script),
                        *_result_fields(
                            round_id=f"r-{wid}",
                            family="codex" if wid == 0 else "composer",
                            actor=f"w{wid}-{i}",
                        ),
                    ],
                    cwd=str(root),
                    capture_output=True,
                    text=True,
                    check=False,
                    env={**os.environ, **env},
                )
                codes.append(r.returncode)
            return codes

        with ThreadPoolExecutor(max_workers=2) as pool:
            futs = [pool.submit(worker, 0), pool.submit(worker, 1)]
            all_codes = []
            for f in as_completed(futs):
                all_codes.extend(f.result())
        assert all(c == 0 for c in all_codes), f"some append failed: {all_codes[:10]}..."
        debt = [
            r
            for r in _read_json_lines(audit)
            if r.get("event") == "committee_family_result"
        ]
        seqs = sorted(int(r["sequence"]) for r in debt)
        assert seqs == list(range(1, 2 * n + 1)), f"seqs broken: len={len(seqs)} head={seqs[:5]} tail={seqs[-5:]}"
    finally:
        m.AUDIT_APPEND_TARGET = prev


# ── Mutation oracles（閹割→紅、復原→綠）──────────────────


def test_mutation_producer_forced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M10：閹割 producer 強制覆寫 → 呼叫端 fake 可落地；復原後再擋。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    args = _open_fields() + ["--field", "producer=fake"]

    baseline = _run(*args, env=_env_for(audit), cwd=root)
    assert baseline.returncode == 0
    assert _read_json_lines(audit)[-1]["producer"] == "audit_append.sh"

    # 清空 audit 再測 mutation
    audit.write_text("", encoding="utf-8")
    original = _mutate_script(
        script,
        'fields["producer"] = producer',
        '# mutation: keep caller producer\npass  # fields["producer"] = producer',
    )
    # 若 caller 傳了 producer=fake，fields 已有 fake；不覆寫則落地 fake
    mutated = _run(*args, env=_env_for(audit), cwd=root)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr
    assert _read_json_lines(audit)[-1]["producer"] == "fake"

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=_env_for(audit), cwd=root)
    assert repaired.returncode == 0
    assert _read_json_lines(audit)[-1]["producer"] == "audit_append.sh"


def test_mutation_absent_session_must_use_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M34：把 --require-absent-session 改成鎖外 check-then-append → 併發可寫兩筆。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)

    # 基線：原子路徑下併發恰一筆
    env = _env_for(audit)
    env["AUDIT_APPEND_MAX_RETRY"] = "200"
    env["AUDIT_APPEND_RETRY_INTERVAL"] = "0.02"

    def race() -> list[int]:
        def one(tag: str) -> int:
            r = subprocess.run(
                [
                    "bash",
                    str(script),
                    "--require-absent-session",
                    "S",
                    *_open_fields(session_name="S", round_id=f"r-{tag}"),
                ],
                cwd=str(root),
                capture_output=True,
                text=True,
                check=False,
                env={**os.environ, **env},
            )
            return r.returncode

        with ThreadPoolExecutor(max_workers=2) as pool:
            return [f.result() for f in as_completed([pool.submit(one, "a"), pool.submit(one, "b")])]

    base_rcs = race()
    assert sorted(base_rcs).count(0) == 1
    assert (
        len(
            [
                r
                for r in _read_json_lines(audit)
                if r.get("session_name") == "S" and r.get("event") == "committee_round_open"
            ]
        )
        == 1
    )

    # 閹割：_append_with_absent_guard 改為先掃（無鎖）再一般 append（各自取鎖）→ TOCTOU
    original = script.read_text(encoding="utf-8")
    # 把 guard 函式替換成非原子版本
    broken = original.replace(
        "_append_with_absent_guard() {\n"
        "  # $1=session_name, 其餘未使用（事件欄位已在全域 FIELD_PAIRS）\n"
        '  local session="$1"\n'
        "  shift || true\n"
        "\n"
        "  _acquire_lock || return 2\n"
        "\n"
        '  _scan_session_locked "${session}"\n'
        "  case $? in\n"
        "    0)\n"
        "      _release_lock\n"
        '      echo "ERROR: session_name 已存在: ${session}" >&2\n'
        "      return 1\n"
        "      ;;\n"
        "    1) : ;;\n"
        "    *)\n"
        "      _release_lock\n"
        "      return 2\n"
        "      ;;\n"
        "  esac\n"
        "\n"
        "  local next_seq\n"
        '  next_seq="$(_next_seq_locked)" || {\n'
        "    local rc=$?\n"
        "    _release_lock\n"
        '    return "${rc}"\n'
        "  }\n"
        "\n"
        '  _append_event_locked "${next_seq}" 1\n'
        "  local rc=$?\n"
        "  _release_lock\n"
        '  return "${rc}"\n'
        "}",
        "_append_with_absent_guard() {\n"
        '  local session="$1"\n'
        "  # mutation: check then append outside single critical section\n"
        "  if [ -f \"${AUDIT_PATH}\" ] && grep -q \"\\\"session_name\\\": \\\"${session}\\\"\" \"${AUDIT_PATH}\" 2>/dev/null; then\n"
        '    echo "ERROR: session_name 已存在: ${session}" >&2\n'
        "    return 1\n"
        "  fi\n"
        "  sleep 0.05\n"
        "  _append_normal 1\n"
        "  return $?\n"
        "}",
    )
    assert broken != original, "mutation did not apply"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")

    mut_rcs = race()
    opens = [
        r
        for r in _read_json_lines(audit)
        if r.get("session_name") == "S" and r.get("event") == "committee_round_open"
    ]
    # 閹割後應可觀察到非原子行為：兩筆成功或 opens>1（至少與基線不同）
    assert len(opens) > 1 or mut_rcs.count(0) == 2, (
        f"mutation did not break atomicity: opens={len(opens)} rcs={mut_rcs}"
    )

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    fixed_rcs = race()
    assert sorted(fixed_rcs).count(0) == 1
    opens2 = [
        r
        for r in _read_json_lines(audit)
        if r.get("session_name") == "S" and r.get("event") == "committee_round_open"
    ]
    assert len(opens2) == 1


def test_mutation_scan_errors_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """掃描三態：掃描出錯必須 fail-closed；若把所有非零當 absent 則會誤 append。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    args = [
        "--require-absent-session",
        "Sbad",
        *_open_fields(session_name="Sbad"),
    ]

    # 基線：空 audit、scan 正常 → 成功
    baseline = _run(*args, env=_env_for(audit), cwd=root)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    audit.write_text("", encoding="utf-8")

    # 讓 _scan_session_locked 永遠 exit 2（模擬掃描錯誤；audit 本身仍乾淨以便 next_seq/append 可走）
    original = _mutate_script(
        script,
        "sys.exit(0 if found else 1)",
        "sys.exit(2)  # mutation: force scan error",
    )
    # 正確 case * → 掃描錯誤 fail-closed
    guarded = _run(*args, env=_env_for(audit), cwd=root)
    assert guarded.returncode != 0
    assert _read_json_lines(audit) == []

    # 再閹割 case：所有非零當 absent → 誤 append 成功
    with_case = script.read_text(encoding="utf-8")
    broken = with_case.replace(
        "  _scan_session_locked \"${session}\"\n"
        "  case $? in\n"
        "    0)\n"
        "      _release_lock\n"
        "      echo \"ERROR: session_name 已存在: ${session}\" >&2\n"
        "      return 1\n"
        "      ;;\n"
        "    1) : ;;\n"
        "    *)\n"
        "      _release_lock\n"
        "      return 2\n"
        "      ;;\n"
        "  esac",
        "  _scan_session_locked \"${session}\"\n"
        "  # mutation: treat all nonzero as absent (swallows scan errors)\n"
        "  if [ $? -eq 0 ]; then\n"
        "      _release_lock\n"
        "      echo \"ERROR: session_name 已存在: ${session}\" >&2\n"
        "      return 1\n"
        "  fi",
    )
    assert broken != with_case, "case mutation anchor missing"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    mutated = _run(*args, env=_env_for(audit), cwd=root)
    assert mutated.returncode == 0, mutated.stdout + mutated.stderr
    assert len(_read_json_lines(audit)) == 1

    # 復原全文
    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    # 僅 scan 強制錯誤、case 已復原 → 再拒
    script.write_text(
        original.replace(
            "sys.exit(0 if found else 1)",
            "sys.exit(2)  # mutation: force scan error",
        ),
        encoding="utf-8",
    )
    script.chmod(script.stat().st_mode | 0o111)
    repaired = _run(*args, env=_env_for(audit), cwd=root)
    assert repaired.returncode != 0
    assert _read_json_lines(audit) == []

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)


# ── B2-FIX：F1–F4 ────────────────────────────────────────


def test_retry_env_requires_harness(tmp_path: Path) -> None:
    """F1：AUDIT_APPEND_MAX_RETRY 未綁 harness → fail-closed。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env_full = os.environ.copy()
        env_full.pop("GOVERNANCE_TEST_HARNESS", None)
        env_full["DEBT_AUDIT_OVERRIDE"] = str(audit)
        env_full["AUDIT_APPEND_MAX_RETRY"] = "3"
        result = subprocess.run(
            ["bash", str(script), *_open_fields()],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
            env=env_full,
        )
        assert result.returncode != 0
        assert "GOVERNANCE_TEST_HARNESS" in (result.stdout + result.stderr)
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_require_absent_rejects_duplicate_session_name(tmp_path: Path) -> None:
    """F2：重複 session_name 欄位 → 歧義拒寫；predicate 與落地不得分離。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        # 第一次：S + 重複 session_name=S / session_name=T → 拒
        args = [
            "--require-absent-session",
            "S",
            *_open_fields(session_name="S"),
            "--field",
            "session_name=T",
        ]
        r1 = _run(*args, env=_env_for(audit), cwd=root)
        assert r1.returncode != 0, r1.stdout + r1.stderr
        assert "重複" in (r1.stdout + r1.stderr) or "歧義" in (r1.stdout + r1.stderr)
        assert _read_json_lines(audit) == []

        # 對照：單一 session_name 仍可成功
        r2 = _run(
            "--require-absent-session",
            "S",
            *_open_fields(session_name="S"),
            env=_env_for(audit),
            cwd=root,
        )
        assert r2.returncode == 0, r2.stdout + r2.stderr
        opens = [
            r
            for r in _read_json_lines(audit)
            if r.get("event") == "committee_round_open"
        ]
        assert len(opens) == 1
        assert opens[0]["session_name"] == "S"
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_event_id_forced_uuid_ignores_caller(tmp_path: Path) -> None:
    """F3：呼叫端 event_id=not-a-uuid → 落地仍為腳本 mint 的 UUID。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m
    import uuid as uuid_mod

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        args = _open_fields() + ["--field", "event_id=not-a-uuid"]
        result = _run(*args, env=_env_for(audit), cwd=root)
        assert result.returncode == 0, result.stdout + result.stderr
        rec = _read_json_lines(audit)[0]
        assert rec["event_id"] != "not-a-uuid"
        uuid_mod.UUID(rec["event_id"])  # 須為合法 UUID
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_shift_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4：閹割 shift 防線（把 next_seq 換成 $1/session）→ happy path 轉紅；復原轉綠。

    經典坑①：缺 shift 使 session 名被當事件／序號參數。現行欄位走 FIELD_PAIRS，
    純刪 `shift` 行為不變；oracle 直接閹割「不得把 session 當 append 參數」這道防線。
    """
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    args = [
        "--require-absent-session",
        "S",
        *_open_fields(session_name="S"),
    ]

    baseline = _run(*args, env=_env_for(audit), cwd=root)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert len(_read_json_lines(audit)) == 1
    baseline_rc = baseline.returncode

    audit.write_text("", encoding="utf-8")
    original = script.read_text(encoding="utf-8")
    # 閹割：去掉 shift，並把 next_seq 換成 $1（session 名當序號）
    broken = original.replace("  shift || true\n", "  # mutation: no shift\n", 1)
    broken = broken.replace(
        '  _append_event_locked "${next_seq}" 1\n',
        '  _append_event_locked "$1" 1\n',
        1,
    )
    assert broken != original, "shift mutation did not apply"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=_env_for(audit), cwd=root)
    mutated_rc = mutated.returncode
    # 閹割後：session 當 seq → int() 失敗或錯誤寫入 → 不得與 baseline 同為成功落地
    assert mutated_rc != 0, (
        f"shift mutation should break happy path: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} "
        f"err={mutated.stderr}"
    )
    assert _read_json_lines(audit) == []

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=_env_for(audit), cwd=root)
    assert repaired.returncode == 0, repaired.stdout + repaired.stderr
    assert len(_read_json_lines(audit)) == 1


def test_require_absent_empty_string_fail_closed(tmp_path: Path) -> None:
    """CODEX-R2-P1-01：--require-absent-session \"\" 須 fail-closed；audit 行數不變。

    事故：用 [ -n \"$值\" ] 當「旗標出現」→ 空字串整段跳過唯一性守衛，同名可寫兩列。
    """
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        # 先正常寫一筆（不傳 require-absent 旗標）當基線行數
        r0 = _run(*_open_fields(session_name="pre"), env=env, cwd=root)
        assert r0.returncode == 0, r0.stdout + r0.stderr
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")

        # 反例 1：空值旗標 → 拒寫
        r_empty = _run(
            "--require-absent-session",
            "",
            *_open_fields(session_name="empty-try"),
            env=env,
            cwd=root,
        )
        assert r_empty.returncode != 0, (
            f"empty session must be rejected: rc={r_empty.returncode} "
            f"out={r_empty.stdout} err={r_empty.stderr}"
        )
        assert "空" in (r_empty.stdout + r_empty.stderr) or "不可為空" in (
            r_empty.stdout + r_empty.stderr
        )
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before

        # 反例 3：完全不傳旗標 → 行為與修法前相同（可正常 append）
        r_nof = _run(
            *_open_fields(session_name="noflag"),
            env=env,
            cwd=root,
        )
        assert r_nof.returncode == 0, r_nof.stdout + r_nof.stderr
        assert any(
            r.get("session_name") == "noflag" for r in _read_json_lines(audit)
        )
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_require_absent_empty_does_not_bypass_uniqueness(tmp_path: Path) -> None:
    """反例 2：旗標+正常值時，同名第二次仍須 rc≠0 且不增行（原行為不得回歸）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r1 = _run(
            "--require-absent-session",
            "S-uniq",
            *_open_fields(session_name="S-uniq", round_id="r-a"),
            env=env,
            cwd=root,
        )
        assert r1.returncode == 0, r1.stdout + r1.stderr
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")
        r2 = _run(
            "--require-absent-session",
            "S-uniq",
            *_open_fields(session_name="S-uniq", round_id="r-b"),
            env=env,
            cwd=root,
        )
        assert r2.returncode != 0
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_empty_require_absent_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割「空值拒寫」→ 空字串可寫入；復原轉紅。

    閹割方式＝把 REQUIRE_ABSENT_SET 判定改回 [ -n 值 ]（事故原狀），並刪空值 die。
    """
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    empty_args = [
        "--require-absent-session",
        "",
        *_open_fields(session_name="mut-empty"),
    ]

    # 基線：空值須拒
    baseline = _run(*empty_args, env=env, cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, baseline.stdout + baseline.stderr
    assert _read_json_lines(audit) == []

    original = script.read_text(encoding="utf-8")
    # 閹割 1：刪空值 die 區塊
    broken = original.replace(
        '  if [ -z "${REQUIRE_ABSENT_SESSION}" ]; then\n'
        '    die "--require-absent-session 值不可為空（旗標出現即須生效；空值 fail-closed）"\n'
        "  fi\n",
        "  # mutation: no empty reject\n",
        1,
    )
    # 閹割 2：旗標判定改回值非空（事故原狀）
    broken = broken.replace(
        'if [ "${REQUIRE_ABSENT_SET}" = "1" ]; then\n',
        'if [ -n "${REQUIRE_ABSENT_SESSION}" ]; then\n',
        1,
    )
    assert broken != original, "empty-guard mutation did not apply"
    assert 'if [ -n "${REQUIRE_ABSENT_SESSION}" ]; then' in broken
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    # 事故行為：空字串 ≡ 沒傳 → 守衛跳過 → 正常寫入成功
    mutated = _run(*empty_args, env=env, cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"castrated empty-guard should allow empty session write: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} "
        f"err={mutated.stderr}"
    )
    assert len(_read_json_lines(audit)) == 1

    # 復原 → 再拒
    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*empty_args, env=env, cwd=root)
    assert repaired.returncode != 0, repaired.stdout + repaired.stderr
    assert _read_json_lines(audit) == []


def test_mutation_rc_propagation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F4：閹割 rc 傳播（return rc → return 0）→ 失敗被吞成 rc=0；復原轉回 rc≠0。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    # 缺 actor → append 必敗；正確碼須 rc≠0
    args = [
        "--require-absent-session",
        "Src",
        "--event",
        "committee_round_open",
        "--field",
        "round_id=r1",
        "--field",
        "task_id=t1",
        "--field",
        "brief_path=b.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        'participants=@["codex"]',
        "--field",
        'expected_outputs=@{"codex":"o.md"}',
        "--field",
        "session_name=Src",
        "--field",
        "origin_script=committee_run.sh",
        # 缺 actor
    ]

    baseline = _run(*args, env=_env_for(audit), cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, "缺必填應失敗"
    assert _read_json_lines(audit) == []

    original = script.read_text(encoding="utf-8")
    # 只改 _append_with_absent_guard 尾端 return（第一處 return "${rc}" 在該函式）
    broken = original.replace(
        '  _append_event_locked "${next_seq}" 1\n'
        "  local rc=$?\n"
        "  _release_lock\n"
        '  return "${rc}"\n'
        "}",
        '  _append_event_locked "${next_seq}" 1\n'
        "  local rc=$?\n"
        "  _release_lock\n"
        "  return 0  # mutation: swallow rc\n"
        "}",
        1,
    )
    assert broken != original, "rc mutation did not apply"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=_env_for(audit), cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"rc-swallow mutation should report success: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc}"
    )
    # 失敗被吞：audit 仍無列（append 真失敗），但 rc=0
    assert _read_json_lines(audit) == []

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    repaired = _run(*args, env=_env_for(audit), cwd=root)
    assert repaired.returncode != 0
    assert _read_json_lines(audit) == []


def test_require_absent_rejects_rs_injection(tmp_path: Path) -> None:
    """B2-FIX3：--require-absent-session 含 RS(\\x1e) 須拒寫；audit 行數不變。

    攻擊：session 名含 FIELD_PAIRS 分隔符 → 守衛掃 A、落地 session_name 變 B。
    """
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r0 = _run(*_open_fields(session_name="pre-rs"), env=env, cwd=root)
        assert r0.returncode == 0, r0.stdout + r0.stderr
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")

        rs = "\x1e"
        poisoned = f"looks-unique{rs}session_name=S-real"
        r_rs = _run(
            "--require-absent-session",
            poisoned,
            # 不帶 session_name field，讓腳本注入 require-absent 值
            "--event",
            "committee_round_open",
            "--field",
            "round_id=r-rs",
            "--field",
            "task_id=t-rs",
            "--field",
            "brief_path=handoffs/brief.md",
            "--field",
            "brief_sha256=" + ("a" * 64),
            "--field",
            "brief_sha256_norm=" + ("b" * 64),
            "--field",
            "lock_mode=discovery",
            "--field",
            'participants=@["codex"]',
            "--field",
            'expected_outputs=@{"codex":"handoffs/x.md"}',
            "--field",
            "actor=test-actor",
            "--field",
            "origin_script=committee_run.sh",
            env=env,
            cwd=root,
        )
        assert r_rs.returncode != 0, (
            f"RS in require-absent-session must be rejected: "
            f"rc={r_rs.returncode} err={r_rs.stderr}"
        )
        err = r_rs.stdout + r_rs.stderr
        assert "RS" in err or "\\x1e" in err or "x1e" in err, err
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_require_absent_rs_fix_does_not_break_uniqueness(tmp_path: Path) -> None:
    """反例 2：修 RS 後，正常同名第二次仍 rc≠0 且不增行。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r1 = _run(
            "--require-absent-session",
            "S-rs-uniq",
            *_open_fields(session_name="S-rs-uniq", round_id="r-a"),
            env=env,
            cwd=root,
        )
        assert r1.returncode == 0, r1.stdout + r1.stderr
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")
        r2 = _run(
            "--require-absent-session",
            "S-rs-uniq",
            *_open_fields(session_name="S-rs-uniq", round_id="r-b"),
            env=env,
            cwd=root,
        )
        assert r2.returncode != 0
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_require_absent_normal_session_unaffected(tmp_path: Path) -> None:
    """反例 3：正常 session 名不受 RS/換行守衛誤擋。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(
            "--require-absent-session",
            "sess-normal-ok",
            *_open_fields(session_name="sess-normal-ok"),
            env=env,
            cwd=root,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        opens = [
            rec
            for rec in _read_json_lines(audit)
            if rec.get("event") == "committee_round_open"
        ]
        assert len(opens) == 1
        assert opens[0]["session_name"] == "sess-normal-ok"
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_field_rejects_newline(tmp_path: Path) -> None:
    """--field 含換行須拒（與 RS 同一套控制字元驗證）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(
            "--event",
            "committee_round_open",
            "--field",
            "round_id=r1\nextra",
            env=env,
            cwd=root,
        )
        assert r.returncode != 0
        assert "換行" in (r.stdout + r.stderr)
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_event_rejects_rs(tmp_path: Path) -> None:
    """--event 含 RS 須拒（會落地為 event 欄）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(
            "--event",
            "committee_round_open\x1eevil",
            "--field",
            "actor=x",
            env=env,
            cwd=root,
        )
        assert r.returncode != 0
        err = r.stdout + r.stderr
        assert "RS" in err or "x1e" in err or "\\x1e" in err
        assert _read_json_lines(audit) == []
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_rs_reject_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割 _reject_serialized_control_chars 的 RS 拒 → 含 RS 可寫入；復原轉紅。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    rs = "\x1e"
    # 後半必須是合法 k=v，否則 RS 切開後會被「缺 =」擋掉，測不到 RS 守衛本身
    poisoned = f"uniq-rs{rs}note=injected"
    args = [
        "--require-absent-session",
        poisoned,
        "--event",
        "committee_round_open",
        "--field",
        "round_id=r-mut-rs",
        "--field",
        "task_id=t-mut-rs",
        "--field",
        "brief_path=handoffs/brief.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        'participants=@["codex"]',
        "--field",
        'expected_outputs=@{"codex":"handoffs/x.md"}',
        "--field",
        "actor=test-actor",
        "--field",
        "origin_script=committee_run.sh",
    ]

    baseline = _run(*args, env=env, cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, baseline.stdout + baseline.stderr
    assert _read_json_lines(audit) == []

    original = script.read_text(encoding="utf-8")
    # 閹割：RS case 改為永不匹配（改比對不可能字元序列）
    broken = original.replace(
        '    *"$FIELD_RS"*) die "${label} 不得含 RS(\\\\x1e) 字元" ;;\n',
        '    *"__MUTATION_NEVER_RS__"*) die "${label} 不得含 RS(\\\\x1e) 字元" ;;\n',
        1,
    )
    assert broken != original, "RS-reject mutation did not apply"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=env, cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"castrated RS-reject should allow write: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} "
        f"err={mutated.stderr}"
    )
    rows = _read_json_lines(audit)
    assert len(rows) == 1
    # 落地 session_name 被 RS 切開，只剩 delimiter 前半 → 與 predicate 分離
    assert rows[0].get("session_name") == "uniq-rs"
    assert rows[0].get("note") == "injected"

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=env, cwd=root)
    assert repaired.returncode != 0, repaired.stdout + repaired.stderr
    assert _read_json_lines(audit) == []


# ── B2-FIX4：splitlines 全集 + JSON 遞迴字串驗證 ─────────────────

# Python str.splitlines() 行界全集（消費端定義；codepoint 序，非人工黑名單）
_SPLITLINES_BREAKS = (
    "\n",  # 0x0a
    "\v",  # 0x0b
    "\f",  # 0x0c
    "\r",  # 0x0d
    "\x1c",
    "\x1d",
    "\x1e",
    "\x85",
    "\u2028",
    "\u2029",
)


def test_splitlines_set_matches_python_definition() -> None:
    """守衛集合 ≡ 全 unicode 掃 splitlines 邊界（防日後漏字元）。"""
    derived = [
        chr(cp)
        for cp in range(0x110000)
        if len(("a" + chr(cp) + "b").splitlines()) > 1
    ]
    assert derived == list(_SPLITLINES_BREAKS)


@pytest.mark.parametrize("break_ch", _SPLITLINES_BREAKS)
def test_field_rejects_splitlines_break_chars(
    tmp_path: Path, break_ch: str
) -> None:
    """F1：--field 含任一 splitlines 行界 → rc≠0，audit 不變。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r0 = _run(*_open_fields(session_name="pre-sl"), env=env, cwd=root)
        assert r0.returncode == 0, r0.stdout + r0.stderr
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")

        r = _run(
            "--event",
            "committee_round_open",
            "--field",
            f"round_id=poison{break_ch}x",
            env=env,
            cwd=root,
        )
        assert r.returncode != 0, (
            f"splitlines break {break_ch!r} must be rejected: "
            f"rc={r.returncode} err={r.stderr}"
        )
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_field_normal_value_not_blocked_by_splitlines_guard(
    tmp_path: Path,
) -> None:
    """F1 反例：正常欄位值不受誤擋。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(*_open_fields(session_name="sess-sl-ok"), env=env, cwd=root)
        assert r.returncode == 0, r.stdout + r.stderr
        opens = [
            rec
            for rec in _read_json_lines(audit)
            if rec.get("event") == "committee_round_open"
        ]
        assert len(opens) == 1
        assert opens[0]["session_name"] == "sess-sl-ok"
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_json_field_rejects_u2028_via_escape(tmp_path: Path) -> None:
    """F2：k=@json 內 \\u2028 轉義 loads 後須拒（CLI 字元守衛看不到）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r0 = _run(*_open_fields(session_name="pre-j1"), env=env, cwd=root)
        assert r0.returncode == 0
        n_before = len(_read_json_lines(audit))
        before = audit.read_text(encoding="utf-8")

        # JSON 轉義：raw CLI 無 U+2028 字元本體，只有 \\u2028
        r = _run(
            *_open_fields(session_name="sess-j-u2028"),
            "--field",
            'note=@{"a":"x\\u2028y"}',
            env=env,
            cwd=root,
        )
        assert r.returncode != 0, r.stdout + r.stderr
        err = r.stdout + r.stderr
        assert "splitlines" in err or "行界" in err, err
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_json_field_rejects_rs_via_escape(tmp_path: Path) -> None:
    """F2：k=@json 內 \\u001e (RS) loads 後須拒。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        n_before = len(_read_json_lines(audit))
        r = _run(
            *_open_fields(session_name="sess-j-rs"),
            "--field",
            'note=@{"a":"x\\u001ey"}',
            env=env,
            cwd=root,
        )
        assert r.returncode != 0, r.stdout + r.stderr
        assert len(_read_json_lines(audit)) == n_before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_json_field_rejects_nested_u2028(tmp_path: Path) -> None:
    """F2：巢狀 object/array 內字串含 U+2028 亦拒（遞迴涵蓋）。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        n_before = len(_read_json_lines(audit))
        r = _run(
            *_open_fields(session_name="sess-j-nest"),
            "--field",
            'note=@{"a":{"b":["nest\\u2028ed"]}}',
            env=env,
            cwd=root,
        )
        assert r.returncode != 0, r.stdout + r.stderr
        err = r.stdout + r.stderr
        assert "splitlines" in err or "行界" in err, err
        assert len(_read_json_lines(audit)) == n_before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_json_field_normal_string_ok(tmp_path: Path) -> None:
    """F2 反例：正常 JSON 字串不誤擋。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(
            *_open_fields(session_name="sess-j-ok"),
            "--field",
            'note=@{"a":"normal-string"}',
            env=env,
            cwd=root,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        rows = _read_json_lines(audit)
        assert len(rows) == 1
        assert rows[0].get("note") == {"a": "normal-string"}
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_splitlines_fullset_reject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割 bash splitlines 其餘行界 case → U+2028 可寫入；復原轉紅。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    ls = "\u2028"
    args = [
        "--event",
        "committee_round_open",
        "--field",
        f"round_id=r-mut-ls{ls}x",
        "--field",
        "task_id=t-mut-ls",
        "--field",
        "brief_path=handoffs/brief.md",
        "--field",
        "brief_sha256=" + ("a" * 64),
        "--field",
        "brief_sha256_norm=" + ("b" * 64),
        "--field",
        "lock_mode=discovery",
        "--field",
        'participants=@["codex"]',
        "--field",
        'expected_outputs=@{"codex":"handoffs/x.md"}',
        "--field",
        "session_name=sess-mut-ls",
        "--field",
        "actor=test-actor",
        "--field",
        "origin_script=committee_run.sh",
    ]

    baseline = _run(*args, env=env, cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, baseline.stdout + baseline.stderr
    assert _read_json_lines(audit) == []

    original = script.read_text(encoding="utf-8")
    # 閹割：其餘 splitlines case 改為永不匹配
    needle = (
        "    *$'\\v'* | *$'\\f'* | *$'\\x1c'* | *$'\\x1d'* | "
        "*$'\\xc2\\x85'* | *$'\\xe2\\x80\\xa8'* | *$'\\xe2\\x80\\xa9'*)\n"
    )
    replacement = (
        "    *\"__MUTATION_NEVER_SPLITLINES__\"*)\n"
    )
    assert needle in original, "splitlines case needle not found for mutation"
    broken = original.replace(needle, replacement, 1)
    # FIX5 後落地前最終防線會再擋 CLI 毒值；一併拿掉呼叫才證明 bash case 曾是必要層
    final_call = "_reject_all_landed_strings(fields)\n"
    assert final_call in broken, "final landed-strings guard call missing"
    broken = broken.replace(
        final_call,
        "pass  # mutation: skip final landed-string guard\n",
        1,
    )
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=env, cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"castrated splitlines-fullset should allow U+2028 write: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} err={mutated.stderr}"
    )
    # 寫入成功但含 U+2028 → splitlines 會切壞 JSON 行，故用 raw 驗落地
    raw = audit.read_text(encoding="utf-8")
    assert ls in raw, f"U+2028 must land in audit after castration: {raw!r}"
    assert len(raw.strip()) > 0

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=env, cwd=root)
    assert repaired.returncode != 0, repaired.stdout + repaired.stderr
    assert audit.read_text(encoding="utf-8") == ""


def test_mutation_json_recursive_string_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割 JSON 遞迴字串驗證 → \\u2028 可寫入；復原轉紅。"""
    root, script, audit = _harness(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    args = [
        *_open_fields(session_name="sess-mut-json"),
        "--field",
        'note=@{"a":"x\\u2028y"}',
    ]

    baseline = _run(*args, env=env, cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, baseline.stdout + baseline.stderr
    assert _read_json_lines(audit) == []

    original = script.read_text(encoding="utf-8")
    # 閹割：_reject_json_string_values 變 no-op（仍保留 def 供呼叫）
    needle = (
        "def _reject_json_string_values(obj, path: str) -> None:\n"
        '    """json.loads 後遞迴驗所有字串值（含巢狀 object/array）；違反 fail-closed。\n'
        "\n"
        "    繞過面：CLI 字元守衛只看 raw 字串；JSON \\\\uXXXX 轉義在 loads 後才成行界字元。\n"
        '    """\n'
    )
    # 改為函式一進來就 return
    if needle not in original:
        # 容許 docstring 空白差異：改匹配函式簽名後第一行邏輯
        needle = "def _reject_json_string_values(obj, path: str) -> None:\n"
        assert needle in original, "json recursive guard def not found"
        # 在 def 後插入 early return：找 def 行，下一非 docstring 前插入困難
        # 改：把 _has_splitlines_break 本體改成 always False 不夠——那是共用。
        # 直接把呼叫點拿掉
        call = "            _reject_json_string_values(parsed, k)\n"
        assert call in original, "json recursive call site not found"
        broken = original.replace(
            call,
            "            pass  # mutation: skip json string walk\n",
            1,
        )
    else:
        broken = original.replace(
            needle,
            needle + "    return  # mutation: skip all json string checks\n",
            1,
        )
    # FIX5 後落地前最終防線會再擋 JSON 毒值；一併拿掉
    final_call = "_reject_all_landed_strings(fields)\n"
    assert final_call in broken, "final landed-strings guard call missing"
    broken = broken.replace(
        final_call,
        "pass  # mutation: skip final landed-string guard\n",
        1,
    )
    assert broken != original, "json-recursive mutation did not apply"
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=env, cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"castrated json-recursive should allow \\u2028: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} err={mutated.stderr}"
    )
    # 落地含 U+2028 會被 splitlines 切行，改用 raw + 非 splitlines 解析
    raw = audit.read_text(encoding="utf-8")
    assert "\u2028" in raw, raw
    # 以 keepends 拼回或逐字找 JSON 物件
    assert '"note"' in raw and "x" in raw and "y" in raw

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=env, cwd=root)
    assert repaired.returncode != 0, repaired.stdout + repaired.stderr
    assert audit.read_text(encoding="utf-8") == ""


# ── B2-FIX5：registry 衍生值不得以「來源可信」豁免 guard ─────────────


def _poison_registry(reg_path: Path, mutator) -> None:
    """就地改 harness 內 registry 副本（不碰 repo 真檔）。"""
    data = json.loads(reg_path.read_text(encoding="utf-8"))
    mutator(data)
    reg_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _open_fields_no_origin(**kwargs: str) -> list[str]:
    """committee_round_open 必填，但省略 origin_script → 走 registry 預設。"""
    args = _open_fields(**kwargs)
    out: list[str] = []
    skip_next = False
    for i, a in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if a == "--field" and i + 1 < len(args) and args[i + 1].startswith(
            "origin_script="
        ):
            skip_next = True
            continue
        out.append(a)
    return out


def test_registry_schema_version_u2028_rejected(tmp_path: Path) -> None:
    """FIX5：registry schema_version 含 U+2028 → rc≠0，錯誤點名 registry 鍵。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    ls = "\u2028"
    _poison_registry(reg, lambda d: d.__setitem__("schema_version", f"1{ls}x"))

    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        before = audit.read_text(encoding="utf-8")
        r = _run(*_open_fields(session_name="sess-reg-sv"), env=env, cwd=root)
        assert r.returncode != 0, r.stdout + r.stderr
        err = r.stdout + r.stderr
        assert "registry" in err.lower() or "registry" in err, err
        assert "schema_version" in err, err
        assert "splitlines" in err or "行界" in err, err
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_registry_default_origin_script_u2028_rejected(tmp_path: Path) -> None:
    """FIX5：registry 預設 origin_script 含 U+2028 → rc≠0，點名 debt_events.*.origin_script。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    ls = "\u2028"
    poisoned = f"committee_run.sh{ls}"

    def _mut(d: dict) -> None:
        d["debt_events"]["committee_round_open"]["origin_script"] = poisoned
        # 同步白名單，避免先被 allowed_origin 擋而誤報（守衛須點名 registry 鍵）
        d["allowed_origin_scripts"] = list(d.get("allowed_origin_scripts") or []) + [
            poisoned
        ]

    _poison_registry(reg, _mut)

    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        before = audit.read_text(encoding="utf-8")
        r = _run(
            *_open_fields_no_origin(session_name="sess-reg-origin"),
            env=env,
            cwd=root,
        )
        assert r.returncode != 0, r.stdout + r.stderr
        err = r.stdout + r.stderr
        assert "registry" in err, err
        assert "origin_script" in err, err
        assert "debt_events.committee_round_open.origin_script" in err, err
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_registry_normal_values_not_blocked(tmp_path: Path) -> None:
    """FIX5 回歸：正常 registry schema_version / origin 預設不受誤擋。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        # 省略 CLI origin_script，確認 registry 預設路徑仍可寫
        r = _run(
            *_open_fields_no_origin(session_name="sess-reg-ok"),
            env=env,
            cwd=root,
        )
        assert r.returncode == 0, r.stdout + r.stderr
        rows = _read_json_lines(audit)
        assert len(rows) == 1
        assert rows[0].get("origin_script") == "committee_run.sh"
        assert rows[0].get("schema_version") == 1
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_registry_value_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割 registry 值 guard 共用原語 → schema_version U+2028 可寫；復原轉紅。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    ls = "\u2028"
    _poison_registry(reg, lambda d: d.__setitem__("schema_version", f"1{ls}x"))
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    args = _open_fields(session_name="sess-mut-reg")

    baseline = _run(*args, env=env, cwd=root)
    baseline_rc = baseline.returncode
    assert baseline_rc != 0, baseline.stdout + baseline.stderr
    assert audit.read_text(encoding="utf-8") == ""

    original = script.read_text(encoding="utf-8")
    # 閹割：_has_splitlines_break 一律 False → Python 側 registry/JSON/落地 守衛全滅
    # （本測只餵 registry 毒值；CLI 字面 U+2028 仍受 bash 擋，不在本 mutation 範圍）
    needle = (
        "def _has_splitlines_break(s: str) -> bool:\n"
        "    for ch in s:\n"
        '        if len(("a" + ch + "b").splitlines()) > 1:\n'
        "            return True\n"
        "    return False\n"
    )
    replacement = (
        "def _has_splitlines_break(s: str) -> bool:\n"
        "    return False  # mutation: disable all python splitlines guards\n"
    )
    assert needle in original, "registry-guard mutation needle (_has_splitlines_break) missing"
    broken = original.replace(needle, replacement, 1)
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    mutated = _run(*args, env=env, cwd=root)
    mutated_rc = mutated.returncode
    assert mutated_rc == 0, (
        f"castrated registry-value guard should allow U+2028 schema_version: "
        f"baseline_rc={baseline_rc} mutated_rc={mutated_rc} err={mutated.stderr}"
    )
    raw = audit.read_text(encoding="utf-8")
    assert ls in raw, f"U+2028 must land after castration: {raw!r}"

    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    repaired = _run(*args, env=env, cwd=root)
    assert repaired.returncode != 0, repaired.stdout + repaired.stderr
    assert audit.read_text(encoding="utf-8") == ""


# ── FIX6：開債事件名從 registry opens_debt 推導（禁硬編）────────


def _rename_open_event(reg_path: Path, old: str, new: str) -> None:
    """harness 內將 opens_debt 事件改名（同步 debt_events + required_fields_per_event）。"""

    def _mut(d: dict) -> None:
        de = d.get("debt_events") or {}
        assert old in de, f"open event {old!r} missing in registry"
        de[new] = de.pop(old)
        d["debt_events"] = de
        rfp = d.get("required_fields_per_event") or {}
        if old in rfp:
            rfp[new] = rfp.pop(old)
            d["required_fields_per_event"] = rfp

    _poison_registry(reg_path, _mut)


def _open_fields_named(event: str, **kwargs: str) -> list[str]:
    """與 _open_fields 相同，但 --event 可改名（對應 registry 改名探針）。"""
    args = _open_fields(**kwargs)
    out: list[str] = []
    i = 0
    while i < len(args):
        if args[i] == "--event" and i + 1 < len(args):
            out.extend(["--event", event])
            i += 2
            continue
        out.append(args[i])
        i += 1
    return out


def test_require_absent_survives_open_event_rename(tmp_path: Path) -> None:
    """CODEX-R6-P1-01：registry 開債事件改名後，唯一性仍須生效（第二次 rc≠0、行數不增）。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    old, new = "committee_round_open", "committee_round_open_v2"
    _rename_open_event(reg, old, new)

    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r1 = _run(
            "--require-absent-session",
            "s-hardcode",
            *_open_fields_named(new, session_name="s-hardcode", round_id="r-a"),
            env=env,
            cwd=root,
        )
        assert r1.returncode == 0, r1.stdout + r1.stderr
        n_before = len(_read_json_lines(audit))
        assert n_before == 1
        before = audit.read_text(encoding="utf-8")

        r2 = _run(
            "--require-absent-session",
            "s-hardcode",
            *_open_fields_named(new, session_name="s-hardcode", round_id="r-b"),
            env=env,
            cwd=root,
        )
        assert r2.returncode != 0, (
            f"rename must keep uniqueness: second append rc={r2.returncode} "
            f"err={r2.stderr}"
        )
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
        rows = [
            r
            for r in _read_json_lines(audit)
            if r.get("event") == new and r.get("session_name") == "s-hardcode"
        ]
        assert len(rows) == 1
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_scan_derives_open_event_from_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割「從 registry 推導開債事件名」→ 改名後唯一性失效；復原轉綠。

    閹割方式＝把 open_event 推導改回硬編字串 committee_round_open（事故原狀）。
    探針條件＝registry 已將開債事件改名為 *_v2。
    """
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    old, new = "committee_round_open", "committee_round_open_v2"
    _rename_open_event(reg, old, new)
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    args = [
        "--require-absent-session",
        "s-mut-hardcode",
        *_open_fields_named(new, session_name="s-mut-hardcode", round_id="r-base"),
    ]

    # 基線（修後）：第一次 OK，第二次拒
    b1 = _run(*args, env=env, cwd=root)
    assert b1.returncode == 0, b1.stdout + b1.stderr
    b2 = _run(
        "--require-absent-session",
        "s-mut-hardcode",
        *_open_fields_named(new, session_name="s-mut-hardcode", round_id="r-dup"),
        env=env,
        cwd=root,
    )
    baseline_second_rc = b2.returncode
    assert baseline_second_rc != 0, b2.stdout + b2.stderr
    assert len(_read_json_lines(audit)) == 1

    original = script.read_text(encoding="utf-8")
    # 閹割：鎖內掃描改回硬編事件名（與 opens_debt 改名脫鉤）
    needle = 'if rec.get("event") == open_event and rec.get("session_name") == session:'
    replacement = (
        'if rec.get("event") == "committee_round_open" '
        "and rec.get(\"session_name\") == session:"
    )
    assert needle in original, "opens_debt derivation needle missing in _scan_session_locked"
    broken = original.replace(needle, replacement, 1)
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    audit.write_text("", encoding="utf-8")
    m1 = _run(*args, env=env, cwd=root)
    assert m1.returncode == 0, m1.stdout + m1.stderr
    m2 = _run(
        "--require-absent-session",
        "s-mut-hardcode",
        *_open_fields_named(new, session_name="s-mut-hardcode", round_id="r-dup2"),
        env=env,
        cwd=root,
    )
    mutated_second_rc = m2.returncode
    # 事故：硬編舊名 → 掃描永遠 miss → 第二次也成功、audit 兩行
    assert mutated_second_rc == 0, (
        f"hardcoded open-event name must bypass uniqueness after rename: "
        f"baseline_second_rc={baseline_second_rc} mutated_second_rc={mutated_second_rc} "
        f"err={m2.stderr}"
    )
    assert len(_read_json_lines(audit)) == 2

    # 復原 → 唯一性恢復
    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    r1 = _run(*args, env=env, cwd=root)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    r2 = _run(
        "--require-absent-session",
        "s-mut-hardcode",
        *_open_fields_named(new, session_name="s-mut-hardcode", round_id="r-dup3"),
        env=env,
        cwd=root,
    )
    assert r2.returncode != 0, r2.stdout + r2.stderr
    assert len(_read_json_lines(audit)) == 1


# ── FIX7：opens_debt 須嚴格布林（is True），非 truthy ────────


def _set_opens_debt_flags(reg_path: Path, mapping: dict[str, object]) -> None:
    """harness 內覆寫各事件 opens_debt（值可為非布林以測型別邊界）。"""

    def _mut(d: dict) -> None:
        de = d.get("debt_events") or {}
        for name, val in mapping.items():
            assert name in de, f"event {name!r} missing in debt_events"
            de[name]["opens_debt"] = val
        d["debt_events"] = de

    _poison_registry(reg_path, _mut)


def test_opens_debt_truthy_string_false_not_selected(tmp_path: Path) -> None:
    """CODEX-R7-P1-01：真開債 opens_debt=0、另一事件 opens_debt=\"false\" →
    0 筆嚴格 true → fail-closed rc=2；第二次亦拒寫、audit 不增行。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    # 事故形：0 為 falsy、非空字串 \"false\" 為 truthy → 舊碼選錯事件
    _set_opens_debt_flags(
        reg,
        {
            "committee_round_open": 0,
            "committee_family_result": "false",
        },
    )
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r1 = _run(
            "--require-absent-session",
            "s-truthy",
            *_open_fields(session_name="s-truthy", round_id="r-t1"),
            env=env,
            cwd=root,
        )
        # 恰 0 筆 opens_debt is True → fail-closed
        assert r1.returncode == 2, (
            f"non-boolean opens_debt must fail-closed rc=2, got {r1.returncode}: "
            f"{r1.stdout}{r1.stderr}"
        )
        assert "opens_debt" in (r1.stderr + r1.stdout)
        assert audit.read_text(encoding="utf-8") == ""

        r2 = _run(
            "--require-absent-session",
            "s-truthy",
            *_open_fields(session_name="s-truthy", round_id="r-t2"),
            env=env,
            cwd=root,
        )
        assert r2.returncode != 0, r2.stdout + r2.stderr
        assert audit.read_text(encoding="utf-8") == ""
    finally:
        m.AUDIT_APPEND_TARGET = prev


@pytest.mark.parametrize(
    "bad_val",
    ["true", 1, None],
    ids=["str_true", "int_1", "null"],
)
def test_opens_debt_non_bool_true_not_accepted(
    tmp_path: Path, bad_val: object
) -> None:
    """opens_debt=\"true\"／1／null 皆不得當 true；恰 0 筆 → rc=2。"""
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    _set_opens_debt_flags(
        reg,
        {
            "committee_round_open": bad_val,
            "committee_family_result": False,
            "committee_debt_clear": False,
            "debt_abandon": False,
        },
    )
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r = _run(
            "--require-absent-session",
            "s-nonbool",
            *_open_fields(session_name="s-nonbool", round_id="r-nb"),
            env=env,
            cwd=root,
        )
        assert r.returncode == 2, (
            f"opens_debt={bad_val!r} must not count as True: rc={r.returncode} "
            f"err={r.stderr}"
        )
        assert audit.read_text(encoding="utf-8") == ""
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_opens_debt_strict_true_still_uniqueness(tmp_path: Path) -> None:
    """正常 boolean registry：第二次同名 --require-absent-session rc≠0、行數=1。"""
    root, script, audit = _harness(tmp_path)
    import tests.governance.test_debt_emit as m

    prev = m.AUDIT_APPEND_TARGET
    m.AUDIT_APPEND_TARGET = script
    try:
        env = _env_for(audit)
        r1 = _run(
            "--require-absent-session",
            "s-bool-ok",
            *_open_fields(session_name="s-bool-ok", round_id="r-ok1"),
            env=env,
            cwd=root,
        )
        assert r1.returncode == 0, r1.stdout + r1.stderr
        n_before = len(_read_json_lines(audit))
        assert n_before == 1
        before = audit.read_text(encoding="utf-8")
        r2 = _run(
            "--require-absent-session",
            "s-bool-ok",
            *_open_fields(session_name="s-bool-ok", round_id="r-ok2"),
            env=env,
            cwd=root,
        )
        assert r2.returncode != 0, r2.stdout + r2.stderr
        assert len(_read_json_lines(audit)) == n_before
        assert audit.read_text(encoding="utf-8") == before
    finally:
        m.AUDIT_APPEND_TARGET = prev


def test_mutation_opens_debt_must_be_strict_true(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """mutation：閹割「is True」→ 退回 truthy → codex 反例下唯一性失效；復原轉綠。

    閹割：`spec.get(\"opens_debt\") is True` → `spec.get(\"opens_debt\")`
    探針條件：真開債 opens_debt=0、另一事件 opens_debt=\"false\"。
    """
    root, script, audit = _harness(tmp_path)
    reg = root / "scripts" / "audit_events.json"
    _set_opens_debt_flags(
        reg,
        {
            "committee_round_open": 0,
            "committee_family_result": "false",
        },
    )
    monkeypatch.setattr(sys.modules[__name__], "AUDIT_APPEND_TARGET", script)
    env = _env_for(audit)
    sess = "s-mut-truthy"
    args1 = [
        "--require-absent-session",
        sess,
        *_open_fields(session_name=sess, round_id="r-m1"),
    ]
    args2 = [
        "--require-absent-session",
        sess,
        *_open_fields(session_name=sess, round_id="r-m2"),
    ]

    # 基線（修後）：fail-closed rc=2、audit 空
    b1 = _run(*args1, env=env, cwd=root)
    assert b1.returncode == 2, b1.stdout + b1.stderr
    assert audit.read_text(encoding="utf-8") == ""

    original = script.read_text(encoding="utf-8")
    needle = "if isinstance(spec, dict) and spec.get(\"opens_debt\") is True"
    replacement = 'if isinstance(spec, dict) and spec.get("opens_debt")'
    assert needle in original, "strict opens_debt is True needle missing"
    broken = original.replace(needle, replacement, 1)
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)

    # 事故：truthy 選到 family_result（\"false\"）→ 掃描 miss 開債 → 兩次都寫入
    audit.write_text("", encoding="utf-8")
    m1 = _run(*args1, env=env, cwd=root)
    assert m1.returncode == 0, (
        f"truthy path should wrongly accept open with opens_debt=0: "
        f"rc={m1.returncode} err={m1.stderr}"
    )
    m2 = _run(*args2, env=env, cwd=root)
    mutated_second_rc = m2.returncode
    assert mutated_second_rc == 0, (
        f"truthy opens_debt must break uniqueness: baseline_rc=2 "
        f"mutated_second_rc={mutated_second_rc} err={m2.stderr}"
    )
    assert len(_read_json_lines(audit)) == 2

    # 復原 → fail-closed 恢復
    script.write_text(original, encoding="utf-8")
    script.chmod(script.stat().st_mode | 0o111)
    audit.write_text("", encoding="utf-8")
    r1 = _run(*args1, env=env, cwd=root)
    assert r1.returncode == 2, r1.stdout + r1.stderr
    assert audit.read_text(encoding="utf-8") == ""
# =============================================================================
# P1-6 B3 — Task 1.2 (committee_run 開債) + Task 1.3 (cx_run 記結果)
# =============================================================================

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor, as_completed as _as_completed

from tests.governance import _debt_probe_helper as _dph


COMMITTEE_RUN_SH = REPO_ROOT / "scripts" / "committee_run.sh"
CX_RUN_SH = REPO_ROOT / "scripts" / "cx_run.sh"
GATE_SH = REPO_ROOT / "scripts" / "gate.sh"


def _b3_harness(tmp_path: Path) -> dict:
    """隔離 repo：scripts 副本 + 空 audit + handoffs + gate dir。

    回傳 dict: root, audit, gate_dir, scripts, brief, env
    """
    root = tmp_path / "repo"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    handoffs = root / "handoffs"
    handoffs.mkdir()
    gate_dir = root / ".claude" / "gate"
    gate_dir.mkdir(parents=True)
    audit = gate_dir / "audit.log"
    audit.write_text("", encoding="utf-8")

    for name in (
        "committee_run.sh",
        "cx_run.sh",
        "audit_append.sh",
        "gate.sh",
        "audit_events.json",
        "governance_families.sh",
        "governance_families.json",
        "governance_roles.json",
        # GOV-DOC-CHECK-AT-WRITE（2026-08-02）：cx_run.sh 的 brief 合規閘 + stamp-target
        # 驗證抽成獨立腳本（一份實作、兩個呼叫點）。隔離 repo 少了它 → cx_run rc=127。
        "brief_conformance_check.sh",
        # GOVFLOW Task 3.1：角色閘 + task_id 白名單 SSOT
        "_role_gate.sh",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)

    # gate.sh 依賴多支工具；低風險 dispatch 最小路徑通常只寫 token。
    # 為避免缺依賴，提供 always-pass / always-fail stub gate（仍經 committee_run 呼叫）。
    (scripts / "gate_pass.sh").write_text(
        "#!/usr/bin/env bash\n"
        "echo GATE PASS stub\n"
        "exit 0\n",
        encoding="utf-8",
    )
    (scripts / "gate_pass.sh").chmod(0o755)
    (scripts / "gate_fail.sh").write_text(
        "#!/usr/bin/env bash\n"
        "echo GATE DENY stub >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    (scripts / "gate_fail.sh").chmod(0o755)

    # stamp-target 檔（D-001 契約：brief-kind=stamp 必填且檔須存在）
    stamp_target = handoffs / "b3-stamp-target.md"
    stamp_target.write_text("## 戳記\n", encoding="utf-8")

    brief = handoffs / "b3-brief.md"
    # stamp：角色閘不限家族（impl 會被 SoT implementer=grok 擋）
    brief.write_text(
        "brief-kind: stamp\n"
        "stamp-target: handoffs/b3-stamp-target.md\n\n"
        "B3 stub brief for debt emit tests.\n",
        encoding="utf-8",
    )

    env = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
        "GATE_DIR_OVERRIDE": str(gate_dir),
        "CX_STUB_MODE": "success",
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
    }
    return {
        "root": root,
        "audit": audit,
        "gate_dir": gate_dir,
        "scripts": scripts,
        "brief": brief,
        "env": env,
        "handoffs": handoffs,
    }


def _patch_committee_gate(scripts: Path, which: str = "pass") -> None:
    """把 committee_run 內的 gate.sh 呼叫改成 stub（pass/fail）。"""
    path = scripts / "committee_run.sh"
    text = path.read_text(encoding="utf-8")
    old = 'bash "${SCRIPT_DIR}/gate.sh" dispatch "${gate_args[@]}"'
    new = f'bash "${{SCRIPT_DIR}}/gate_{which}.sh" dispatch "${{gate_args[@]}}"'
    assert old in text, "gate call anchor missing in committee_run"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _run_committee(
    h: dict,
    *,
    session: str = "sess-b3",
    fams: str = "codex,composer,grok",
    out_prefix: str = "handoffs/b3-out",
    task_id: str = "P16-B3-T1",
    extra_args: list[str] | None = None,
    env_overlay: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = dict(h["env"])
    if env_overlay:
        env.update(env_overlay)
    args = [
        "--session",
        session,
        str(h["brief"].relative_to(h["root"]))
        if str(h["brief"]).startswith(str(h["root"]))
        else "handoffs/b3-brief.md",
        out_prefix,
        fams,
        "--",
        "--intent",
        "b3-test",
        "--risk",
        "low",
        "--facts-asked",
        "none-needed:unit",
        "--review-role",
        "advisory",
        "--template",
        "n/a:stub",
        "--task-id",
        task_id,
    ]
    if extra_args:
        args = extra_args
    # helper 常數 seam（Task 3.2 改法②）：mutation 可 monkeypatch COMMITTEE_RUN_TARGET。
    # 未 patch 時若 harness 有副本 → 用隔離副本；已 patch → 一律走常數。
    harness_cr = h["scripts"] / "committee_run.sh"
    default_cr = _dph.REPO_ROOT / "scripts" / "committee_run.sh"
    target = _dph.COMMITTEE_RUN_TARGET
    if target.resolve() == default_cr.resolve() and harness_cr.is_file():
        script = harness_cr
    else:
        script = target
    return _dph.run_cmd(script, *args, env=env, cwd=h["root"])


def _open_via_append(
    h: dict,
    *,
    round_id: str,
    session: str,
    fams: list[str],
    out_prefix: str,
    brief_path: str,
    brief_sha: str | None = None,
) -> str:
    """直接用 audit_append 開債（給 cx_run 單測用）；回傳 round_id。"""
    if brief_sha is None:
        brief_sha = hashlib.sha256(h["brief"].read_bytes()).hexdigest()
    brief_norm = brief_sha  # 測試可共用
    participants = json.dumps(fams)
    outputs = json.dumps({f: f"{out_prefix}-{f}.md" for f in fams})
    r = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--require-absent-session",
        session,
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={round_id}",
        "--field",
        "task_id=P16-B3-T1",
        "--field",
        f"brief_path={brief_path}",
        "--field",
        f"brief_sha256={brief_sha}",
        "--field",
        f"brief_sha256_norm={brief_norm}",
        "--field",
        "lock_mode=discovery",
        "--field",
        f"participants=@{participants}",
        "--field",
        f"expected_outputs=@{outputs}",
        "--field",
        f"session_name={session}",
        "--field",
        "actor=test",
        "--field",
        "origin_script=committee_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    return round_id


def _events(audit: Path, name: str | None = None) -> list[dict]:
    rows = _read_json_lines(audit)
    if name is None:
        return rows
    return [r for r in rows if r.get("event") == name]


# ── Task 1.2 ──────────────────────────────────────────────


def test_b3_open_three_families_one_round_open(tmp_path: Path) -> None:
    """派 3 家 → 恰 1 筆 committee_round_open 且 participants 長度 3。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    r = _run_committee(h, fams="codex,composer,grok")
    assert r.returncode == 0, r.stdout + r.stderr
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) == 1, opens
    assert len(opens[0]["participants"]) == 3
    assert set(opens[0]["participants"]) == {"codex", "composer", "grok"}
    assert opens[0].get("session_name")
    assert opens[0].get("brief_sha256")
    assert opens[0].get("round_id")
    # 每家一筆 result
    results = _events(h["audit"], "committee_family_result")
    assert len(results) == 3
    assert all(x.get("family") != "unknown" for x in results)


def test_b3_open_one_family_still_writes(tmp_path: Path) -> None:
    """派 1 家也必須寫 committee_round_open。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    r = _run_committee(h, fams="codex", session="sess-one")
    assert r.returncode == 0, r.stdout + r.stderr
    opens = _events(h["audit"], "committee_round_open")
    assert len(opens) == 1
    assert opens[0]["participants"] == ["codex"]
    assert len(_events(h["audit"], "committee_family_result")) == 1


def test_b3_missing_session_rc_nonzero(tmp_path: Path) -> None:
    """缺 --session → rc≠0。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    r = _dph.run_cmd(
        h["scripts"] / "committee_run.sh",
        "handoffs/b3-brief.md",
        "handoffs/b3-out",
        "codex",
        "--",
        "--task-id",
        "T",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert "session" in (r.stdout + r.stderr).lower()
    assert _events(h["audit"], "committee_round_open") == []


def test_b3_missing_task_id_rc_nonzero(tmp_path: Path) -> None:
    """gate flags 缺 --task-id → rc≠0。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    r = _dph.run_cmd(
        h["scripts"] / "committee_run.sh",
        "--session",
        "s1",
        "handoffs/b3-brief.md",
        "handoffs/b3-out",
        "codex",
        "--",
        "--intent",
        "x",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert "task-id" in (r.stdout + r.stderr).lower()


def test_b3_gate_deny_zero_new_debt_events(tmp_path: Path) -> None:
    """gate 拒發 token → audit 零新增 debt 事件。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "fail")
    before = h["audit"].read_text(encoding="utf-8")
    r = _run_committee(h, session="sess-deny")
    assert r.returncode != 0
    assert h["audit"].read_text(encoding="utf-8") == before
    assert _events(h["audit"], "committee_round_open") == []


def test_b3_open_does_not_create_session_dir(tmp_path: Path) -> None:
    """開債後 handoffs/reconcile/<name>/ 仍不存在。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    name = "sess-nosessdir"
    r = _run_committee(h, session=name, fams="codex")
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (h["root"] / "handoffs" / "reconcile" / name).exists()


def test_b3_duplicate_session_rejected(tmp_path: Path) -> None:
    """第二次同一 --session → rc≠0 且 audit 事件數不增長。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    r1 = _run_committee(h, session="sess-dup", fams="codex")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    n1 = len(_read_json_lines(h["audit"]))
    r2 = _run_committee(h, session="sess-dup", fams="codex", task_id="P16-B3-T2")
    assert r2.returncode != 0
    n2 = len(_read_json_lines(h["audit"]))
    assert n2 == n1
    assert len(_events(h["audit"], "committee_round_open")) == 1


def test_b3_parallel_same_session_one_wins(tmp_path: Path) -> None:
    """兩程序並行同 session → 恰一筆成功、audit 該 session 恆一筆。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")

    def once(i: int) -> int:
        # 每程序獨立 out 前綴避免檔衝突；session 相同
        env = dict(h["env"])
        return _dph.run_cmd(
            h["scripts"] / "committee_run.sh",
            "--session",
            "sess-par",
            "handoffs/b3-brief.md",
            f"handoffs/b3-par{i}",
            "codex",
            "--",
            "--task-id",
            f"P16-B3-PAR{i}",
            env=env,
            cwd=h["root"],
        ).returncode

    with ThreadPoolExecutor(max_workers=2) as ex:
        rcs = list(ex.map(once, [1, 2]))
    assert sorted(rcs).count(0) == 1, rcs
    assert sorted(rcs).count(0) + sum(1 for x in rcs if x != 0) == 2
    opens = _events(h["audit"], "committee_round_open")
    sess = [o for o in opens if o.get("session_name") == "sess-par"]
    assert len(sess) == 1


def test_b3_open_fail_does_not_start_cx_run(tmp_path: Path) -> None:
    """寫入失敗 → 不啟動 cx_run（無 runlog / 無 result）。"""
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    # 先佔用 session
    assert _run_committee(h, session="sess-block", fams="codex").returncode == 0
    # 清掉 runlog 計數基準
    runlogs_before = list(h["handoffs"].glob("*.runlog"))
    # 再開同 session → 開債失敗，不得新派
    r = _run_committee(
        h,
        session="sess-block",
        fams="codex",
        out_prefix="handoffs/b3-should-not-run",
        task_id="P16-B3-BLOCK",
    )
    assert r.returncode != 0
    assert "不啟動" in (r.stdout + r.stderr) or "開債失敗" in (r.stdout + r.stderr)
    assert not (h["handoffs"] / "b3-should-not-run-codex.runlog").exists()
    assert not (h["handoffs"] / "b3-should-not-run-codex.md").exists()
    # result 筆數不因第二次而增加（仍只有第一輪 1 家）
    assert len(_events(h["audit"], "committee_family_result")) == 1


# ── Task 1.3 ──────────────────────────────────────────────


def test_b3_family_field_not_unknown(tmp_path: Path) -> None:
    """合法呼叫後 family 欄為實際家族名（非 unknown）。"""
    h = _b3_harness(tmp_path)
    rid = "11111111-1111-4111-8111-111111111111"
    _open_via_append(
        h,
        round_id=rid,
        session="s-fam",
        fams=["codex"],
        out_prefix="handoffs/b3f",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3f-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["family"] == "codex"
    assert rows[0]["family"] != "unknown"


def test_b3_round_id_missing_rejected(tmp_path: Path) -> None:
    """ROUND_ID 未設 → rc≠0。"""
    h = _b3_harness(tmp_path)
    env = dict(h["env"])
    env.pop("ROUND_ID", None)
    # 確保未設
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/out-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert "ROUND_ID" in (r.stdout + r.stderr)


def test_b3_round_id_unknown_zero_new(tmp_path: Path) -> None:
    """ROUND_ID=不存在的值 → rc≠0 且 audit 零新增 result。"""
    h = _b3_harness(tmp_path)
    before = len(_read_json_lines(h["audit"]))
    env = dict(h["env"])
    env["ROUND_ID"] = "00000000-0000-4000-8000-000000000000"
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/out-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert len(_read_json_lines(h["audit"])) == before
    assert _events(h["audit"], "committee_family_result") == []


def test_b3_family_not_in_roster_rejected(tmp_path: Path) -> None:
    """家族不在該輪名單 → rc≠0。"""
    h = _b3_harness(tmp_path)
    rid = "22222222-2222-4222-8222-222222222222"
    _open_via_append(
        h,
        round_id=rid,
        session="s-roster",
        fams=["codex"],
        out_prefix="handoffs/b3r",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    # 登記 expected 只有 codex；派 composer 且 path 也對 composer 會先被 roster 擋
    # 需先有 expected_outputs 含 composer 才測得到 roster——故用 codex open 派 grok
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "grok",
        "handoffs/b3-brief.md",
        "handoffs/b3r-grok.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert "不在該輪名單" in (r.stdout + r.stderr) or "名單" in (r.stdout + r.stderr)


def test_b3_brief_sha_mismatch_rejected(tmp_path: Path) -> None:
    """換一份 brief 掛在既有 round → rc≠0（第 5 道前置）。"""
    h = _b3_harness(tmp_path)
    rid = "33333333-3333-4333-8333-333333333333"
    _open_via_append(
        h,
        round_id=rid,
        session="s-brief",
        fams=["codex"],
        out_prefix="handoffs/b3b",
        brief_path="handoffs/b3-brief.md",
    )
    other = h["handoffs"] / "other-brief.md"
    other.write_text(
        "brief-kind: stamp\n"
        "stamp-target: handoffs/b3-stamp-target.md\n\n"
        "DIFFERENT\n",
        encoding="utf-8",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/other-brief.md",
        "handoffs/b3b-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    assert "brief_sha256" in (r.stdout + r.stderr) or "brief" in (r.stdout + r.stderr).lower()
    assert _events(h["audit"], "committee_family_result") == []


def test_b3_cli_nonzero_still_writes_failed(tmp_path: Path) -> None:
    """CLI 回非 0 → 仍寫一筆 result 且帶 cli_rc；output_sha256 空字串。"""
    h = _b3_harness(tmp_path)
    rid = "44444444-4444-4444-8444-444444444444"
    _open_via_append(
        h,
        round_id=rid,
        session="s-fail",
        fams=["codex"],
        out_prefix="handoffs/b3e",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "fail_rc"
    env["CX_STUB_RC"] = "7"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3e-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "failed"
    assert str(rows[0]["cli_rc"]) == "7"
    assert rows[0]["output_sha256"] == ""


def test_b3_success_output_sha_matches_file(tmp_path: Path) -> None:
    """success 的 result 含非空 output_sha256 且等於產出檔。"""
    h = _b3_harness(tmp_path)
    rid = "55555555-5555-4555-8555-555555555555"
    _open_via_append(
        h,
        round_id=rid,
        session="s-ok",
        fams=["codex"],
        out_prefix="handoffs/b3ok",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    out_rel = "handoffs/b3ok-codex.md"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        out_rel,
        env=env,
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    out_path = h["root"] / out_rel
    assert out_path.is_file() and out_path.stat().st_size > 0
    want = hashlib.sha256(out_path.read_bytes()).hexdigest()
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "success"
    assert rows[0]["output_sha256"]
    assert rows[0]["output_sha256"] == want


def test_b3_reject_redispatch_after_success(tmp_path: Path) -> None:
    """對最新已 success 的家族重派 → rc≠0 且 audit 零新增。"""
    h = _b3_harness(tmp_path)
    rid = "66666666-6666-4666-8666-666666666666"
    _open_via_append(
        h,
        round_id=rid,
        session="s-redisp",
        fams=["codex"],
        out_prefix="handoffs/b3rd",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    r1 = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3rd-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r1.returncode == 0, r1.stdout + r1.stderr
    n1 = len(_read_json_lines(h["audit"]))
    r2 = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3rd-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r2.returncode != 0
    assert "success" in (r2.stdout + r2.stderr).lower() or "拒重派" in (r2.stdout + r2.stderr)
    assert len(_read_json_lines(h["audit"])) == n1


def test_b3_retry_after_failed_allowed(tmp_path: Path) -> None:
    """failed 後可重派（append-only 第二筆）。"""
    h = _b3_harness(tmp_path)
    rid = "77777777-7777-4777-8777-777777777777"
    _open_via_append(
        h,
        round_id=rid,
        session="s-retry",
        fams=["codex"],
        out_prefix="handoffs/b3rt",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "fail_rc"
    env["CX_STUB_RC"] = "1"
    r1 = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3rt-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r1.returncode != 0
    env["CX_STUB_MODE"] = "success"
    env.pop("CX_STUB_RC", None)
    r2 = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3rt-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r2.returncode == 0, r2.stdout + r2.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 2
    assert rows[0]["result_state"] == "failed"
    assert rows[1]["result_state"] == "success"


def test_b3_concurrent_three_families(tmp_path: Path) -> None:
    """並發 3 家 → 3 筆完整不交錯。"""
    h = _b3_harness(tmp_path)
    rid = "88888888-8888-4888-8888-888888888888"
    fams = ["codex", "composer", "grok"]
    _open_via_append(
        h,
        round_id=rid,
        session="s-conc",
        fams=fams,
        out_prefix="handoffs/b3c",
        brief_path="handoffs/b3-brief.md",
    )

    def one(fam: str) -> int:
        env = dict(h["env"])
        env["ROUND_ID"] = rid
        env["CX_STUB_MODE"] = "success"
        return _dph.run_cmd(
            h["scripts"] / "cx_run.sh",
            fam,
            "handoffs/b3-brief.md",
            f"handoffs/b3c-{fam}.md",
            env=env,
            cwd=h["root"],
        ).returncode

    with ThreadPoolExecutor(max_workers=3) as ex:
        rcs = list(ex.map(one, fams))
    assert rcs == [0, 0, 0], rcs
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 3
    assert {r["family"] for r in rows} == set(fams)
    # 每行可獨立 json 解析（不交錯）— _read_json_lines 已保證
    for r in rows:
        assert r.get("result_state") == "success"
        assert r.get("output_sha256")


def test_b3_audit_missing_creates_not_crash(tmp_path: Path) -> None:
    """audit 檔不存在 → 建立而非崩潰（前置會 touch 後判 round 不存在）。"""
    h = _b3_harness(tmp_path)
    h["audit"].unlink()
    assert not h["audit"].exists()
    env = dict(h["env"])
    env["ROUND_ID"] = "99999999-9999-4999-8999-999999999999"
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/out-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0  # round 不存在
    assert h["audit"].exists()  # 已建立


def test_b3_cx_stub_requires_harness(tmp_path: Path) -> None:
    """CX_STUB_MODE 未綁 harness → 專屬訊息 fail-closed（不得先被其他守衛擋住）。

    其他條件全滿足／移除：只留 CX_STUB 守衛可擋，並比對專屬錯誤訊息。
    """
    h = _b3_harness(tmp_path)
    env = dict(h["env"])
    env["CX_STUB_MODE"] = "success"
    env.pop("GOVERNANCE_TEST_HARNESS", None)
    # 移除 DEBT_AUDIT_OVERRIDE，避免（若順序變動）被 harness-override 守衛先擋
    env.pop("DEBT_AUDIT_OVERRIDE", None)
    env.pop("GATE_DIR_OVERRIDE", None)
    # CX_STUB 檢查在前置之前；不需 open round 即可打到該守衛
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        "handoffs/b3h-codex.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "CX_STUB_MODE 須綁 GOVERNANCE_TEST_HARNESS=1" in combined, combined
    # 不得只被其他守衛擋住
    assert "DEBT_AUDIT_OVERRIDE" not in combined


def test_b3_expected_outputs_family_unregistered(tmp_path: Path) -> None:
    """guard④ 子路徑：家族在 participants 但未登記於 expected_outputs → 專屬拒。"""
    h = _b3_harness(tmp_path)
    rid = "a0a0a0a0-a0a0-4a0a-8a0a-a0a0a0a0a0a0"
    brief_sha = hashlib.sha256(h["brief"].read_bytes()).hexdigest()
    # participants 含 codex+composer；expected_outputs 只登記 codex
    r_open = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--require-absent-session",
        "s-exp-miss",
        "--event",
        "committee_round_open",
        "--field",
        f"round_id={rid}",
        "--field",
        "task_id=P16-B3-T1",
        "--field",
        "brief_path=handoffs/b3-brief.md",
        "--field",
        f"brief_sha256={brief_sha}",
        "--field",
        f"brief_sha256_norm={brief_sha}",
        "--field",
        "lock_mode=discovery",
        "--field",
        'participants=@["codex","composer"]',
        "--field",
        'expected_outputs=@{"codex":"handoffs/b3ex-codex.md"}',
        "--field",
        "session_name=s-exp-miss",
        "--field",
        "actor=test",
        "--field",
        "origin_script=committee_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r_open.returncode == 0, r_open.stdout + r_open.stderr
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "composer",
        "handoffs/b3-brief.md",
        "handoffs/b3ex-composer.md",
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "expected_outputs 未登記家族" in combined, combined
    assert _events(h["audit"], "committee_family_result") == []


def test_b3_cli_binary_absent_still_writes_failed(tmp_path: Path) -> None:
    """CLI binary 不存在 → 仍寫 failed result 帶 cli_rc（SPEC 1.3 改法④）。"""
    h = _b3_harness(tmp_path)
    rid = "b1b1b1b1-b1b1-4b1b-8b1b-b1b1b1b1b1b1"
    _open_via_append(
        h,
        round_id=rid,
        session="s-miss-bin",
        fams=["codex"],
        out_prefix="handoffs/b3mb",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    # 不用 stub → 走真 CLI 路徑；把 cx_run 內 CODEX 路徑改成不存在
    env.pop("CX_STUB_MODE", None)
    script = h["scripts"] / "cx_run.sh"
    text = script.read_text(encoding="utf-8")
    broken = text.replace(
        'CODEX="/opt/homebrew/bin/codex"',
        'CODEX="/definitely/missing/codex"',
        1,
    )
    assert broken != text
    script.write_text(broken, encoding="utf-8")
    script.chmod(0o755)
    out_rel = "handoffs/b3mb-codex.md"
    r = _dph.run_cmd(
        script,
        "codex",
        "handoffs/b3-brief.md",
        out_rel,
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert "不存在" in (r.stdout + r.stderr)
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1, f"result_count 須為 1，得 {len(rows)}"
    assert rows[0]["result_state"] == "failed"
    assert str(rows[0]["cli_rc"]) != ""
    assert int(rows[0]["cli_rc"]) != 0
    # CLI 未啟動 → 產出不應由 stub 寫入（binary 缺時也不會寫）
    assert not (h["root"] / out_rel).exists() or (h["root"] / out_rel).stat().st_size == 0


def test_b3_malformed_audit_rejected_before_cli(tmp_path: Path) -> None:
    """audit 含無法解析 JSON 行 → CLI 前 fail-closed，無 result、無產出。"""
    h = _b3_harness(tmp_path)
    rid = "c2c2c2c2-c2c2-4c2c-8c2c-c2c2c2c2c2c2"
    _open_via_append(
        h,
        round_id=rid,
        session="s-corrupt",
        fams=["codex"],
        out_prefix="handoffs/b3cr",
        brief_path="handoffs/b3-brief.md",
    )
    # 追加 malformed 行（與 audit_append reject 同一類）
    with h["audit"].open("a", encoding="utf-8") as fh:
        fh.write("{not-json\n")
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    out_rel = "handoffs/b3cr-codex.md"
    before = len(_events(h["audit"], "committee_family_result"))
    r = _dph.run_cmd(
        h["scripts"] / "cx_run.sh",
        "codex",
        "handoffs/b3-brief.md",
        out_rel,
        env=env,
        cwd=h["root"],
    )
    assert r.returncode != 0
    combined = r.stdout + r.stderr
    assert "無法解析的 JSON 行" in combined, combined
    assert len(_events(h["audit"], "committee_family_result")) == before
    assert not (h["root"] / out_rel).exists()


# ── Mutation probes（閹割守衛 → 轉紅；復原 → 轉綠）────────
# 一律經 helper 模組常數 seam + monkeypatch；三態：baseline 綠 → mutant 紅訊號 → restore 綠


def test_b3_mutation_round_id_guard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """M：閹割 ROUND_ID 檢查 → 無 ROUND_ID 可進入 stub；復原轉紅。

    三態 + 守衛專屬訊號（rc + ROUND_ID 未設訊息）。
    """
    h = _b3_harness(tmp_path)
    script = h["scripts"] / "cx_run.sh"
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", script)
    original = script.read_text(encoding="utf-8")
    rid = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    _open_via_append(
        h,
        round_id=rid,
        session="s-mut-rid",
        fams=["codex"],
        out_prefix="handoffs/b3m1",
        brief_path="handoffs/b3-brief.md",
    )

    env = dict(h["env"])
    env.pop("ROUND_ID", None)
    env["CX_STUB_MODE"] = "success"

    # baseline：拒 + 專屬訊息
    base = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m1-codex.md",
        env=env, cwd=h["root"],
    )
    assert base.returncode != 0, "baseline must reject missing ROUND_ID"
    assert "ROUND_ID 未設" in (base.stdout + base.stderr)

    # 閹割：ROUND_ID 未設時改注入已知 rid
    broken = original.replace(
        'if [ -z "${ROUND_ID:-}" ]; then\n'
        '    echo "ERROR: ROUND_ID 未設（須由 committee_run 開債後注入，或直呼時帶合法 round）" >&2\n'
        "    return 1\n"
        "  fi\n",
        '  if [ -z "${ROUND_ID:-}" ]; then\n'
        f'    ROUND_ID="{rid}"  # MUTATED: inject instead of reject\n'
        "    export ROUND_ID\n"
        "  fi\n",
        1,
    )
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(0o755)

    mut = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m1-codex.md",
        env=env, cwd=h["root"],
    )
    assert mut.returncode == 0, (
        f"mutated must allow missing ROUND_ID: {mut.stdout}{mut.stderr}"
    )
    assert len(_events(h["audit"], "committee_family_result")) == 1

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    h["audit"].write_text("", encoding="utf-8")
    rid2 = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    _open_via_append(
        h,
        round_id=rid2,
        session="s-mut-rid2",
        fams=["codex"],
        out_prefix="handoffs/b3m1b",
        brief_path="handoffs/b3-brief.md",
    )
    restored = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m1b-codex.md",
        env=env, cwd=h["root"],
    )
    assert restored.returncode != 0
    assert "ROUND_ID 未設" in (restored.stdout + restored.stderr)


def test_b3_mutation_brief_sha_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M：閹割 brief_sha 比對 → 換 brief 可掛既有 round；復原轉紅。"""
    h = _b3_harness(tmp_path)
    script = h["scripts"] / "cx_run.sh"
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", script)
    original = script.read_text(encoding="utf-8")
    rid = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    _open_via_append(
        h,
        round_id=rid,
        session="s-mut-brief",
        fams=["codex"],
        out_prefix="handoffs/b3m2",
        brief_path="handoffs/b3-brief.md",
    )
    other = h["handoffs"] / "mut-brief.md"
    other.write_text(
        "brief-kind: stamp\n"
        "stamp-target: handoffs/b3-stamp-target.md\n\n"
        "MUT\n",
        encoding="utf-8",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"

    base = _dph.run_cx_run(
        "codex", "handoffs/mut-brief.md", "handoffs/b3m2-codex.md",
        env=env, cwd=h["root"],
    )
    assert base.returncode != 0
    assert "brief_sha256" in (base.stdout + base.stderr) or "brief" in (
        base.stdout + base.stderr
    ).lower()

    anchor = "if brief_sha != recorded:"
    assert anchor in original
    broken = original.replace(
        anchor,
        "if False and brief_sha != recorded:  # MUTATED",
        1,
    )
    script.write_text(broken, encoding="utf-8")
    script.chmod(0o755)
    mut = _dph.run_cx_run(
        "codex", "handoffs/mut-brief.md", "handoffs/b3m2-codex.md",
        env=env, cwd=h["root"],
    )
    assert mut.returncode == 0, mut.stdout + mut.stderr

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    h["audit"].write_text("", encoding="utf-8")
    rid2 = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    _open_via_append(
        h,
        round_id=rid2,
        session="s-mut-brief2",
        fams=["codex"],
        out_prefix="handoffs/b3m2b",
        brief_path="handoffs/b3-brief.md",
    )
    env["ROUND_ID"] = rid2
    restored = _dph.run_cx_run(
        "codex", "handoffs/mut-brief.md", "handoffs/b3m2b-codex.md",
        env=env, cwd=h["root"],
    )
    assert restored.returncode != 0


def test_b3_mutation_success_block_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M：閹割「已 success 拒重派」→ 可重派；復原轉紅。"""
    h = _b3_harness(tmp_path)
    script = h["scripts"] / "cx_run.sh"
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", script)
    original = script.read_text(encoding="utf-8")
    rid = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    _open_via_append(
        h,
        round_id=rid,
        session="s-mut-suc",
        fams=["codex"],
        out_prefix="handoffs/b3m3",
        brief_path="handoffs/b3-brief.md",
    )
    env = dict(h["env"])
    env["ROUND_ID"] = rid
    env["CX_STUB_MODE"] = "success"
    assert (
        _dph.run_cx_run(
            "codex", "handoffs/b3-brief.md", "handoffs/b3m3-codex.md",
            env=env, cwd=h["root"],
        ).returncode
        == 0
    )
    base = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m3-codex.md",
        env=env, cwd=h["root"],
    )
    assert base.returncode != 0
    assert "success" in (base.stdout + base.stderr).lower() or "拒重派" in (
        base.stdout + base.stderr
    )
    n1 = len(_events(h["audit"], "committee_family_result"))

    broken = original.replace(
        'if latest.get("result_state") == "success":',
        'if False and latest.get("result_state") == "success":  # MUTATED',
        1,
    )
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(0o755)
    mut = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m3-codex.md",
        env=env, cwd=h["root"],
    )
    assert mut.returncode == 0, mut.stdout + mut.stderr
    assert len(_events(h["audit"], "committee_family_result")) == n1 + 1

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    restored = _dph.run_cx_run(
        "codex", "handoffs/b3-brief.md", "handoffs/b3m3-codex.md",
        env=env, cwd=h["root"],
    )
    assert restored.returncode != 0
    assert "success" in (restored.stdout + restored.stderr).lower() or "拒重派" in (
        restored.stdout + restored.stderr
    )


def test_b3_mutation_committee_skips_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M：committee_run 跳過開債 → 無 open；mutant 仍派工但 cx_run 失敗（可觀察訊號）。

    三態：baseline 綠（有 open+rc0）→ mutant 紅（rc≠0 + 無 open + 無 result
    + runlog 含 round_open 缺失）→ restore 綠。
    """
    h = _b3_harness(tmp_path)
    _patch_committee_gate(h["scripts"], "pass")
    script = h["scripts"] / "committee_run.sh"
    monkeypatch.setattr(_dph, "COMMITTEE_RUN_TARGET", script)
    original = script.read_text(encoding="utf-8")

    r0 = _run_committee(h, session="s-mut-open0", fams="codex", out_prefix="handoffs/b3mo0")
    assert r0.returncode == 0, r0.stdout + r0.stderr
    assert len(_events(h["audit"], "committee_round_open")) >= 1
    assert len(_events(h["audit"], "committee_family_result")) >= 1

    h["audit"].write_text("", encoding="utf-8")
    broken = original.replace(
        'if ! _open_debt "${round_id}"; then',
        'if ! true; then  # MUTATED skip open',
        1,
    )
    assert broken != original
    script.write_text(broken, encoding="utf-8")
    script.chmod(0o755)
    r1 = _run_committee(h, session="s-mut-open1", fams="codex", out_prefix="handoffs/b3mo1")
    # mutant 必須可觀察地紅：rc≠0 + 無 open + 無 family result
    assert r1.returncode != 0, (
        f"mutant must fail overall (not silent skip): {r1.stdout}{r1.stderr}"
    )
    assert len(_events(h["audit"], "committee_round_open")) == 0
    assert len(_events(h["audit"], "committee_family_result")) == 0
    # 專屬訊號：派工有嘗試、且因無 open 被擋（寫在 runlog）
    runlog = h["root"] / "handoffs/b3mo1-codex.runlog"
    assert runlog.is_file(), "cx_run 應被啟動並寫 runlog"
    log_txt = runlog.read_text(encoding="utf-8")
    assert "committee_round_open" in log_txt or "ROUND_ID" in log_txt, log_txt

    script.write_text(original, encoding="utf-8")
    script.chmod(0o755)
    r2 = _run_committee(h, session="s-mut-open2", fams="codex", out_prefix="handoffs/b3mo2")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert len(_events(h["audit"], "committee_round_open")) == 1
    assert len(_events(h["audit"], "committee_family_result")) == 1


def test_b3_empty_output_sha256_failed_contract(tmp_path: Path) -> None:
    """契約：failed 可寫空 output_sha256；success 空字串仍拒。"""
    h = _b3_harness(tmp_path)
    # failed ok
    r = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--event",
        "committee_family_result",
        "--field",
        "round_id=r-empty",
        "--field",
        "family=codex",
        "--field",
        "attempt_id=a1",
        "--field",
        "cli_rc=1",
        "--field",
        "output_path=handoffs/x.md",
        "--field",
        "output_sha256=",
        "--field",
        "result_state=failed",
        "--field",
        "actor=t",
        "--field",
        "origin_script=cx_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode == 0, r.stdout + r.stderr
    row = _events(h["audit"], "committee_family_result")[0]
    assert row["output_sha256"] == ""
    # success + empty 拒
    r2 = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--event",
        "committee_family_result",
        "--field",
        "round_id=r-empty2",
        "--field",
        "family=codex",
        "--field",
        "attempt_id=a2",
        "--field",
        "cli_rc=0",
        "--field",
        "output_path=handoffs/x.md",
        "--field",
        "output_sha256=",
        "--field",
        "result_state=success",
        "--field",
        "actor=t",
        "--field",
        "origin_script=cx_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r2.returncode != 0


def test_b3_carveout_narrowed_other_event_rejects_empty_sha(tmp_path: Path) -> None:
    """群集 D：carve-out 僅限 committee_family_result+failed+output_sha256。

    其他事件即使 required 含 output_sha256 且 result_state=failed，空字串仍 rc≠0。
    """
    h = _b3_harness(tmp_path)
    # 在 harness registry 副本把 output_sha256 加進 debt_abandon required
    reg_path = h["scripts"] / "audit_events.json"
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    req = reg["required_fields_per_event"]["debt_abandon"]
    if "output_sha256" not in req:
        req.append("output_sha256")
    if "result_state" not in req:
        req.append("result_state")
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    r = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--event",
        "debt_abandon",
        "--field",
        "round_id=r-other",
        "--field",
        "reason=probe-other-event-carveout-narrowing-xx",
        "--field",
        "approver=t",
        "--field",
        "abandon_kind=collection-failed",
        "--field",
        "output_sha256=",
        "--field",
        "result_state=failed",
        "--field",
        "actor=t",
        "--field",
        "origin_script=debt_clear.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode != 0, (
        f"other event must reject empty output_sha256: {r.stdout}{r.stderr}"
    )
    assert "output_sha256" in (r.stdout + r.stderr) or "缺必填" in (r.stdout + r.stderr)
