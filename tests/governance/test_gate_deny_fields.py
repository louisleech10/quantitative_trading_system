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
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["GATE_DIR_OVERRIDE"] = str(gate_dir)
    if env_extra:
        env.update(env_extra)
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


def _parse_setup_directive(raw: str) -> dict[str, str] | None:
    """解析 `# @setup token=dispatch:expired debt=open` → dict。"""
    s = raw.strip()
    if not s.startswith("#"):
        return None
    body = s.lstrip("#").strip()
    if not body.startswith("@setup"):
        return None
    rest = body[len("@setup") :].strip()
    out: dict[str, str] = {}
    for tok in rest.split():
        if "=" not in tok:
            continue
        k, v = tok.split("=", 1)
        out[k.strip()] = v.strip()
    return out or None


def _load_corpus_entries(path: Path) -> list[tuple[dict[str, str], str]]:
    """回傳 [(setup_dict, payload_json), ...]；setup 可為空 dict。"""
    out: list[tuple[dict[str, str], str]] = []
    pending: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            setup = _parse_setup_directive(line)
            if setup is not None:
                pending = setup
            continue
        json.loads(line)  # 語料必須是合法 JSON
        out.append((dict(pending), line))
        pending = {}
    assert out, f"corpus empty: {path}"
    return out


def _load_corpus(path: Path) -> list[str]:
    return [payload for _, payload in _load_corpus_entries(path)]


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


def _plant_open_debt(audit: Path) -> None:
    """隔離 audit 寫入一筆 OPEN 輪（sequence=1，ts 過 cutoff）。"""
    rec = {
        "event": "committee_round_open",
        "round_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "task_id": "GOVB0-CORPUS-A-OPEN",
        "brief_path": "handoffs/corpus-a-setup.md",
        "brief_sha256": "0" * 64,
        "brief_sha256_norm": "0" * 64,
        "lock_mode": "discovery",
        "participants": ["codex"],
        "expected_outputs": {"codex": "handoffs/out-codex.md"},
        "session_name": "corpus-a-open",
        "actor": "test",
        "origin_script": "committee_run.sh",
        "schema_version": 1,
        "sequence": 1,
        "ts": "2026-08-01T00:00:00Z",
        "event_id": "00000000-0000-4000-8000-0000000000aa",
        "producer": "test",
    }
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps(rec, ensure_ascii=False) + "\n", encoding="utf-8")


def _apply_setup(gate_dir: Path, setup: dict[str, str], debt_dir: Path) -> dict[str, str]:
    """依 @setup 種 token／debt；回傳需併入 gate 子程序的 env。"""
    env_extra: dict[str, str] = {}
    token_spec = setup.get("token", "")
    debt_spec = setup.get("debt", "")

    if token_spec:
        # token=<kind>:<fresh|expired>
        if ":" not in token_spec:
            raise AssertionError(f"bad token setup: {token_spec!r}")
        kind, state = token_spec.split(":", 1)
        token_path = gate_dir / f"{kind}.token"
        token_path.write_text("corpus-a-token\n", encoding="utf-8")
        if state == "expired":
            old = time.time() - 1200
            os.utime(token_path, (old, old))
        elif state == "fresh":
            now = time.time()
            os.utime(token_path, (now, now))
        else:
            raise AssertionError(f"bad token state: {state!r}")

    if debt_spec:
        debt_dir.mkdir(parents=True, exist_ok=True)
        audit = debt_dir / "debt_audit.log"
        if debt_spec == "none":
            audit.write_text("", encoding="utf-8")
        elif debt_spec == "open":
            _plant_open_debt(audit)
        else:
            raise AssertionError(f"bad debt setup: {debt_spec!r}")
        env_extra["GOVERNANCE_TEST_HARNESS"] = "1"
        env_extra["DEBT_AUDIT_OVERRIDE"] = str(audit)

    return env_extra


def _decision_trace(
    script: Path,
    entries: list[tuple[dict[str, str], str]],
    base: Path,
) -> list[tuple[int, str]]:
    """對語料逐條跑 script，回傳 (rc, kind) 序列（與 audit 欄位無關）。"""
    trace: list[tuple[int, str]] = []
    for i, (setup, payload) in enumerate(entries):
        gate_dir = base / f"g{i}"
        gate_dir.mkdir(parents=True, exist_ok=True)
        debt_dir = base / f"debt{i}"
        env_extra = _apply_setup(gate_dir, setup, debt_dir)
        proc = _run_gate(payload, gate_dir=gate_dir, script=script, env_extra=env_extra)
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
    entries = _load_corpus_entries(CORPUS_A)
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


def _emittable_match_rules_from_gate_check() -> set[str]:
    """從 gate_check.sh 的 _gate_deny_match_info 靜態擷取可發出的 match_rule（含 default unknown）。"""
    text = GATE_CHECK.read_text(encoding="utf-8")
    # 函式體範圍：_gate_deny_match_info … 下一個頂層函式
    m = re.search(
        r"_gate_deny_match_info\(\)\s*\{(.*?)\n\}",
        text,
        flags=re.DOTALL,
    )
    assert m, "_gate_deny_match_info 函式錨點漂移"
    body = m.group(1)
    vals = set(re.findall(r'\bmr="([a-z_]+)"', body))
    # default mr="unknown" 亦在 body
    assert "unknown" in vals
    return vals


def test_01_corpus_a_covers_match_rule_closed_set(tmp_path: Path) -> None:
    """語料 A 覆蓋 match_rule 封閉集合中每一個**現行可發出**值至少一次。

    封閉集合 SoT＝`scripts/audit_events.json` enums.match_rule（jq 讀，非硬編）。
    現行 gate_check 可發出集合 ⊆ 封閉集合；outer_script／role_gate 已登記但
    `_gate_deny_match_info` 尚未賦值（Phase 2 契約預留），不要求語料 A 觸發。
    """
    enum = _match_rule_enum()  # from registry via jq-equivalent json load
    emittable = _emittable_match_rules_from_gate_check()
    assert emittable <= enum, f"emittable 超出封閉集合: {emittable - enum}"

    observed: set[str] = set()
    entries = _load_corpus_entries(CORPUS_A)
    for i, (setup, payload) in enumerate(entries):
        gate_dir = tmp_path / f"cov{i}"
        gate_dir.mkdir(parents=True, exist_ok=True)
        debt_dir = tmp_path / f"covdebt{i}"
        env_extra = _apply_setup(gate_dir, setup, debt_dir)
        proc = _run_gate(payload, gate_dir=gate_dir, env_extra=env_extra)
        audit = gate_dir / "audit.log"
        if proc.returncode != 0 and audit.is_file():
            try:
                event = _last_gate_deny(audit)
            except AssertionError:
                continue
            mr = event.get("match_rule")
            if isinstance(mr, str) and mr:
                observed.add(mr)
                assert mr in enum, f"match_rule 不在封閉集合: {mr}"

    missing = emittable - observed
    assert not missing, (
        f"語料 A 未覆蓋現行可發出 match_rule: {sorted(missing)}; "
        f"observed={sorted(observed)}; emittable={sorted(emittable)}; enum={sorted(enum)}"
    )


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


def test_01_cmd_fields_value_equal_full_command(tmp_path: Path) -> None:
    """CODEX-R10-P2-02：cmd_sha256 == sha256(完整 command)；cmd_head == 前 512 bytes。"""
    cmd = "codex exec value-equal-probe " + ("Z" * 600)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    cmd_bytes = cmd.encode("utf-8")
    expected_sha = hashlib.sha256(cmd_bytes).hexdigest()
    expected_head = cmd_bytes[:512].decode("utf-8", errors="surrogateescape")
    # 值相等（非僅長度／非空）
    assert event["cmd_sha256"] == expected_sha, (
        f"cmd_sha256 應為完整 command 的 sha256，got={event['cmd_sha256']}"
    )
    assert event["cmd_head"] == expected_head, (
        f"cmd_head 應為前 512 bytes，len={len(event['cmd_head'].encode('utf-8'))}"
    )
    # 明確：不可等於「截斷後字串」的 sha256
    truncated_sha = hashlib.sha256(cmd_bytes[:512]).hexdigest()
    assert event["cmd_sha256"] != truncated_sha


def test_01_fresh_token_allow_when_no_open_debt(tmp_path: Path) -> None:
    """fresh token + 無 OPEN 債 → 放行（gate_check.sh:196-199）。

    不進語料 A（snapshot SCRIPT_DIR 無法載入 debt core，見 corpus 註解）。
    """
    gate_dir = tmp_path / "g"
    gate_dir.mkdir()
    token = gate_dir / "dispatch.token"
    token.write_text("fresh\n", encoding="utf-8")
    debt_audit = tmp_path / "debt_audit.log"
    debt_audit.write_text("", encoding="utf-8")
    env_extra = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(debt_audit),
    }
    proc = _run_gate(
        '{"tool_name":"Task"}',
        gate_dir=gate_dir,
        env_extra=env_extra,
    )
    assert proc.returncode == 0, proc.stderr


def test_01_cmd_sha256_mutation_truncated_turns_red(tmp_path: Path) -> None:
    """CODEX-R10-P2-02 mutation：若實作改對截斷字串算 sha → 值相等斷言轉紅。

    貼實跑：本測以隔離副本把 sha 輸入改為 head -c 512 的結果，
    然後重跑等價斷言，斷言必須失敗（rc 語意＝assertion 轉紅）。
    """
    mut = tmp_path / "gate_check_mut_sha.sh"
    shutil.copy2(GATE_CHECK, mut)
    mut.chmod(mut.stat().st_mode | 0o111)
    text = mut.read_text(encoding="utf-8")
    # 錨點：sha 必須對完整 $cmd；改成對 head 截斷後字串
    anchor = 'sha="$(printf \'%s\' "$cmd" | sha256sum | awk \'{print $1}\')"'
    # mac 上可能走 shasum；兩分支都改
    alt_anchor = 'sha="$(printf \'%s\' "$cmd" | shasum -a 256 | awk \'{print $1}\')"'
    repl = (
        'sha="$(printf \'%s\' "$cmd" | head -c 512 | sha256sum | awk \'{print $1}\')"\n'
        '    : # MUTATED: sha of truncated'
    )
    repl_alt = (
        'sha="$(printf \'%s\' "$cmd" | head -c 512 | shasum -a 256 | awk \'{print $1}\')"\n'
        '    : # MUTATED: sha of truncated'
    )
    mutated = text
    if anchor in mutated:
        mutated = mutated.replace(anchor, repl, 1)
    if alt_anchor in mutated:
        mutated = mutated.replace(alt_anchor, repl_alt, 1)
    assert mutated != text, "mutation 錨點漂移：找不到 sha 計算行"
    mut.write_text(mutated, encoding="utf-8")

    cmd = "codex exec mut-trunc " + ("Y" * 600)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}})
    gate_dir = tmp_path / "g"
    proc = _run_gate(payload, gate_dir=gate_dir, script=mut)
    assert proc.returncode != 0
    event = _last_gate_deny(gate_dir / "audit.log")
    expected_full = hashlib.sha256(cmd.encode("utf-8")).hexdigest()
    # 值相等斷言應轉紅：mutated event 的 sha ≠ full-command sha
    fields_equal = event["cmd_sha256"] == expected_full
    assert not fields_equal, (
        "MUTATION 未使值相等斷言轉紅：mutated cmd_sha256 仍等於完整 command sha256"
    )


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
