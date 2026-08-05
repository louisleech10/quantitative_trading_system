"""GOVB0 Task 0.1 — gate_deny 新增 match_rule / cmd_sha256 / cmd_head。

TEST-0.1-* 對應 docs/GOVB0_FRICTION_TODO.md Phase 0 / Task 0.1。
不變式只比 (rc, kind) decision trace，不比 audit JSON（本 Task 故意改 audit）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
SNAPSHOT = (
    REPO_ROOT
    / "tests"
    / "governance"
    / "fixtures"
    / "gate_check_pre_phase2.sh.snapshot"
)
REGISTRY = REPO_ROOT / "scripts" / "audit_events.json"
CORPUS_A = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_invariance_corpus.txt"
)
CORPUS_B = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_decision_corpus.txt"
)


def _run_gate(
    payload: str,
    *,
    gate_dir: Path,
    script: Path = GATE_CHECK,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    return subprocess.run(
        ["bash", str(script)],
        input=payload,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _last_gate_deny(audit_log: Path) -> dict:
    lines = [ln for ln in audit_log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "audit.log 為空"
    for ln in reversed(lines):
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if obj.get("event") == "gate_deny":
            return obj
    raise AssertionError("audit.log 無 gate_deny 事件")


def _load_corpus(path: Path) -> list[str]:
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        json.loads(line)  # 語料必須是合法 JSON
        out.append(line)
    assert out, f"corpus empty: {path}"
    return out


def _extract_kind(stderr: str, audit: Path | None) -> str:
    m = re.search(r"kind=([A-Za-z0-9_]+)", stderr or "")
    if m:
        return m.group(1)
    if audit is not None and audit.is_file():
        try:
            return str(_last_gate_deny(audit).get("kind") or "")
        except AssertionError:
            return ""
    return ""


def _decision_trace(script: Path, entries: list[str], base: Path) -> list[tuple[int, str]]:
    """對語料逐條跑 script，回傳 (rc, kind) 序列（與 audit 欄位無關）。"""
    trace: list[tuple[int, str]] = []
    for i, payload in enumerate(entries):
        gate_dir = base / f"g{i}"
        gate_dir.mkdir(parents=True, exist_ok=True)
        proc = _run_gate(payload, gate_dir=gate_dir, script=script)
        kind = ""
        if proc.returncode != 0:
            kind = _extract_kind(proc.stderr, gate_dir / "audit.log")
        trace.append((proc.returncode, kind))
    return trace


def _required_gate_deny_fields() -> list[str]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    fields = reg["required_fields_per_event"]["gate_deny"]
    assert isinstance(fields, list) and fields
    return list(fields)


def _match_rule_enum() -> set[str]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    vals = reg["enums"]["match_rule"]
    assert isinstance(vals, list) and vals
    return set(vals)


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _git_tracked(rel: str) -> bool:
    """已追蹤（committed 或 index）即 True。"""
    proc = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


# ---------------------------------------------------------------------------
# TEST-0.1-RC-BLOCK / RC-ALLOW
# ---------------------------------------------------------------------------


def test_01_rc_block_task(tmp_path: Path) -> None:
    """TEST-0.1-RC-BLOCK：blocked_cmd → rc!=0。"""
    proc = _run_gate('{"tool_name":"Task"}', gate_dir=tmp_path / "g")
    assert proc.returncode != 0


def test_01_rc_block_family_cli(tmp_path: Path) -> None:
    """TEST-0.1-RC-BLOCK：Bash family CLI → rc!=0。"""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "codex exec -s workspace-write p"}}
    )
    proc = _run_gate(payload, gate_dir=tmp_path / "g")
    assert proc.returncode != 0


def test_01_rc_allow_read(tmp_path: Path) -> None:
    """TEST-0.1-RC-ALLOW：allowed_cmd → rc=0。"""
    proc = _run_gate('{"tool_name":"Read"}', gate_dir=tmp_path / "g")
    assert proc.returncode == 0


def test_01_rc_allow_cat(tmp_path: Path) -> None:
    """TEST-0.1-RC-ALLOW：非 executor Bash → rc=0。"""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "cat handoffs/foo.md"}}
    )
    proc = _run_gate(payload, gate_dir=tmp_path / "g")
    assert proc.returncode == 0


# ---------------------------------------------------------------------------
# TEST-0.1-INVARIANCE
# ---------------------------------------------------------------------------


def test_01_invariance_decision_trace(tmp_path: Path) -> None:
    """TEST-0.1-INVARIANCE：語料 A 上 snapshot vs 現行 (rc, kind) 逐項相等。"""
    assert SNAPSHOT.is_file(), "B0 snapshot 缺失"
    entries = _load_corpus(CORPUS_A)
    before = _decision_trace(SNAPSHOT, entries, tmp_path / "before")
    after = _decision_trace(GATE_CHECK, entries, tmp_path / "after")
    assert before == after, (
        "decision trace diff 非空（只應比 (rc, kind)）:\n"
        f"  before={before}\n  after={after}"
    )
    # 差分行數 == 0（具名）
    diff_lines = [f"{b}!={a}" for b, a in zip(before, after) if b != a]
    if len(before) != len(after):
        diff_lines.append(f"len {len(before)}!={len(after)}")
    assert len(diff_lines) == 0


# ---------------------------------------------------------------------------
# TEST-0.1-FIELDS / ENUM
# ---------------------------------------------------------------------------


def test_01_fields_match_registry(tmp_path: Path) -> None:
    """TEST-0.1-FIELDS：gate_deny 欄位集合 == required_fields_per_event.gate_deny。"""
    required = set(_required_gate_deny_fields())
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "codex exec hi"}}
    )
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    assert set(event.keys()) == required


def test_01_enum_match_rule_and_cmd_head(tmp_path: Path) -> None:
    """TEST-0.1-ENUM：match_rule ∈ SoT 集合；有 command 時 cmd_head 非空。"""
    allowed = _match_rule_enum()
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "codex exec hi"}}
    )
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    assert event["match_rule"] in allowed
    assert event["cmd_head"], "cmd_head 應非空"
    assert event["match_rule"] == "family_cli"
    assert len(event["cmd_sha256"]) == 64


def test_01_enum_token_expired(tmp_path: Path) -> None:
    """match_rule=token_expired（過期 token）。"""
    allowed = _match_rule_enum()
    gate_dir = tmp_path / "g"
    gate_dir.mkdir()
    token = gate_dir / "dispatch.token"
    token.write_text("stale", encoding="utf-8")
    old = time.time() - 1200
    os.utime(token, (old, old))
    proc = _run_gate('{"tool_name":"Task"}', gate_dir=gate_dir)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    assert event["reason"] == "token_expired"
    assert event["match_rule"] == "token_expired"
    assert event["match_rule"] in allowed


def test_01_enum_claude_agent(tmp_path: Path) -> None:
    """match_rule=claude_agent。"""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "claude -p do something"}}
    )
    proc = _run_gate(payload, gate_dir=tmp_path / "g")
    assert proc.returncode != 0
    event = _last_gate_deny(tmp_path / "g" / "audit.log")
    assert event["match_rule"] == "claude_agent"
    assert event["match_rule"] in _match_rule_enum()


# ---------------------------------------------------------------------------
# TEST-0.1-CORPUS-DISTINCT
# ---------------------------------------------------------------------------


def test_01_corpus_distinct_and_tracked() -> None:
    """TEST-0.1-CORPUS-DISTINCT：兩份語料 sha256 不同且皆已追蹤。"""
    assert CORPUS_A.is_file() and CORPUS_B.is_file()
    sha_a = _file_sha256(CORPUS_A)
    sha_b = _file_sha256(CORPUS_B)
    assert sha_a != sha_b, f"語料 A/B sha256 不得相同: {sha_a}"
    rel_a = "tests/governance/fixtures/gate_invariance_corpus.txt"
    rel_b = "tests/governance/fixtures/gate_decision_corpus.txt"
    assert _git_tracked(rel_a), f"未追蹤: {rel_a}"
    assert _git_tracked(rel_b), f"未追蹤: {rel_b}"


# ---------------------------------------------------------------------------
# 邊界
# ---------------------------------------------------------------------------


def test_01_boundary_control_chars_valid_json(tmp_path: Path) -> None:
    """邊界①：指令含換行與控制字元 → audit 行仍為合法 JSON。"""
    cmd = "codex exec line1\nline2\t\x01end"
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir)
    assert proc.returncode != 0
    raw = (gate_dir / "audit.log").read_text(encoding="utf-8").strip().splitlines()[-1]
    # jq -e . 等價
    parsed = json.loads(raw)
    assert parsed["event"] == "gate_deny"
    assert "\n" in parsed["cmd_head"] or "line1" in parsed["cmd_head"]


def test_01_boundary_missing_command_empty_fields(tmp_path: Path) -> None:
    """邊界②：tool_input.command 缺失 → 空字串欄位、不例外中止。"""
    # Task 無 command
    proc = _run_gate('{"tool_name":"Task"}', gate_dir=tmp_path / "g")
    assert proc.returncode != 0
    event = _last_gate_deny(tmp_path / "g" / "audit.log")
    assert event["cmd_head"] == ""
    assert event["cmd_sha256"] == hashlib.sha256(b"").hexdigest()
    assert "cmd_head" in event and "cmd_sha256" in event


def test_01_boundary_4mb_audit_line_le_1kb(tmp_path: Path) -> None:
    """邊界③：4 MB prompt → audit 單行 ≤1 KB。"""
    huge = "codex exec " + ("X" * (4 * 1024 * 1024))
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": huge}})
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir)
    assert proc.returncode != 0
    lines = (gate_dir / "audit.log").read_text(encoding="utf-8").splitlines()
    assert lines
    over = [ln for ln in lines if len(ln.encode("utf-8")) > 1024]
    assert over == [], f"audit 行超過 1KB: {[len(x) for x in over]}"


# ---------------------------------------------------------------------------
# TEST-0.1-MUT
# ---------------------------------------------------------------------------


def test_01_mut_remove_new_fields_turns_fields_red(tmp_path: Path) -> None:
    """TEST-0.1-MUT：移除新欄位寫入 → FIELDS 斷言轉紅（貼實跑 rc 語意）。"""
    mut = tmp_path / "gate_check_mut.sh"
    shutil.copy2(GATE_CHECK, mut)
    mut.chmod(mut.stat().st_mode | 0o111)
    text = mut.read_text(encoding="utf-8")
    # 錨點：把 jq 組出來的新欄位剝成舊四欄（event/ts/tool/kind/reason 近似）
    anchor = (
        "'{event:\"gate_deny\",ts:$ts,tool:$tool,kind:$kind,reason:$reason,"
        "match_rule:$match_rule,cmd_sha256:$cmd_sha256,cmd_head:$cmd_head}'"
    )
    replacement = "'{event:\"gate_deny\",ts:$ts,tool:$tool,kind:$kind,reason:$reason}'"
    assert anchor in text, "mutation 錨點漂移：找不到 jq 欄位模板"
    # 兩處 jq 模板（主路徑 + 超長縮減路徑）都剝掉
    mutated = text.replace(anchor, replacement)
    assert mutated != text
    mut.write_text(mutated, encoding="utf-8")

    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "codex exec hi"}}
    )
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir, script=mut)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    required = set(_required_gate_deny_fields())
    # FIELDS 等價斷言：欄位集合應不相等 → 本 mutation 測試本身通過當且僅當集合不等
    fields_equal = set(event.keys()) == required
    assert not fields_equal, (
        "MUTATION 未使 FIELDS 轉紅：mutated event keys 仍等於 required_fields"
    )
    # 明確缺少新欄
    assert "match_rule" not in event or "cmd_sha256" not in event or "cmd_head" not in event
