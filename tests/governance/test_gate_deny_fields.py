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
# B0 snapshot 目錄（option a）：gate_check.sh ＋ 執行期依賴，各檔各自 .sha256
SNAPSHOT_DIR = (
    REPO_ROOT
    / "tests"
    / "governance"
    / "fixtures"
    / "gate_check_pre_phase2"
)
SNAPSHOT = SNAPSHOT_DIR / "gate_check.sh"
# 舊路徑（單檔）仍保留 byte-identical 副本，供 B5 / TODO 路徑相容
SNAPSHOT_LEGACY = (
    REPO_ROOT
    / "tests"
    / "governance"
    / "fixtures"
    / "gate_check_pre_phase2.sh.snapshot"
)
# Phase 2 動工前 gate_check.sh 的已知 sha（596fcb4^；不可變）
PRE_PHASE2_GATE_CHECK_SHA256 = (
    "871258c9ea2e6817b0110e7efedcca6847ba196e9ffb3f7151f57adabe01606a"
)
SNAPSHOT_BUNDLE_FILES = (
    "gate_check.sh",
    "_debt_ledger_core.py",
    "debt_ledger.sh",
    "audit_events.json",
)
REGISTRY = REPO_ROOT / "scripts" / "audit_events.json"
CORPUS_A = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_invariance_corpus.txt"
)
CORPUS_B = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "gate_decision_corpus.txt"
)
# Phase 2 預期轉向清單（自 TODO 機械抽取；禁手挑／禁硬編於測試）
PHASE2_FLIPS = (
    REPO_ROOT / "tests" / "governance" / "fixtures" / "phase2_expected_flips.txt"
)
PHASE2_FLIPS_SHA = Path(str(PHASE2_FLIPS) + ".sha256")
EXTRACT_FLIPS = REPO_ROOT / "scripts" / "extract_phase2_expected_flips.py"


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


def _parse_branch_directive(raw: str) -> str | None:
    """解析 `# @branch allow_fresh_no_debt` → id。"""
    s = raw.strip()
    if not s.startswith("#"):
        return None
    body = s.lstrip("#").strip()
    if not body.startswith("@branch"):
        return None
    bid = body[len("@branch") :].strip().split()[0] if body[len("@branch") :].strip() else ""
    return bid or None


def _load_corpus_entries(path: Path) -> list[tuple[dict[str, str], str]]:
    """回傳 [(setup_dict, payload_json), ...]；setup 可為空 dict。

    setup 可含鍵 ``_branch``（來自 ``# @branch``），不影響 gate 子程序。
    """
    out: list[tuple[dict[str, str], str]] = []
    pending: dict[str, str] = {}
    pending_branch: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            setup = _parse_setup_directive(line)
            if setup is not None:
                pending = setup
                continue
            branch = _parse_branch_directive(line)
            if branch is not None:
                pending_branch = branch
            continue
        json.loads(line)  # 語料必須是合法 JSON
        meta = dict(pending)
        if pending_branch is not None:
            meta["_branch"] = pending_branch
        out.append((meta, line))
        pending = {}
        pending_branch = None
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
    """依 @setup 種 token／debt；回傳需併入 gate 子程序的 env。

    忽略 ``_branch`` 等 harness 元資料鍵（不傳入 gate）。
    """
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
# Phase 2 expected flips（機械抽取；供 INVARIANCE 排除）
# ---------------------------------------------------------------------------


def _payload_command(payload: str) -> str | None:
    """自 gate stdin JSON 取 Bash command；非 Bash 或無 command → None。"""
    try:
        obj = json.loads(payload)
    except json.JSONDecodeError:
        return None
    if obj.get("tool_name") != "Bash":
        return None
    ti = obj.get("tool_input") or {}
    cmd = ti.get("command")
    return str(cmd) if cmd is not None else None


def _norm_cmd(s: str) -> str:
    return s.replace("…", "...").replace("\u2026", "...").strip()


def _cmd_match(actual: str, pattern: str) -> bool:
    """pattern 可含 '...' 省略號；以 re 錨定非省略首尾。"""
    a = _norm_cmd(actual)
    p = _norm_cmd(pattern)
    if "..." not in p:
        return a == p
    parts = p.split("...")
    body = ".*".join(re.escape(part) for part in parts)
    if not p.startswith("..."):
        body = "^" + body
    if not p.endswith("..."):
        body = body + "$"
    return re.search(body, a) is not None

def _load_phase2_flips(
    path: Path = PHASE2_FLIPS,
) -> list[dict[str, str]]:
    """載入 phase2_expected_flips.txt → [{kind,test_id,from,to,command}, ...]。"""
    assert path.is_file(), f"phase2 flips fixture 缺失: {path}"
    rows: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        assert len(parts) >= 5, f"bad flip line: {raw!r}"
        rows.append(
            {
                "kind": parts[0],
                "test_id": parts[1],
                "from": parts[2],
                "to": parts[3],
                "command": "\t".join(parts[4:]),
            }
        )
    assert rows, "phase2 flips fixture empty"
    return rows


def _flip_matches_command(cmd: str, flips: list[dict[str, str]], *, kind: str = "flip") -> dict[str, str] | None:
    for fr in flips:
        if kind and fr["kind"] != kind:
            continue
        if _cmd_match(cmd, fr["command"]):
            return fr
    return None


def _corpus_b_commands(path: Path = CORPUS_B) -> list[str]:
    cmds: list[str] = []
    for _setup, payload in _load_corpus_entries(path):
        c = _payload_command(payload)
        if c is not None:
            cmds.append(c)
    return cmds


def _rc_to_decision(rc: int) -> str:
    return "ALLOW" if rc == 0 else "BLOCK"


def _decision_for_cmd(
    script: Path,
    cmd: str,
    base: Path,
) -> str:
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        ensure_ascii=False,
    )
    gate_dir = base / "g"
    gate_dir.mkdir(parents=True, exist_ok=True)
    proc = _run_gate(payload, gate_dir=gate_dir, script=script)
    return _rc_to_decision(proc.returncode)


# ---------------------------------------------------------------------------
# TEST-0.1-INVARIANCE
# ---------------------------------------------------------------------------


def test_01_phase2_flips_fixture_matches_todo() -> None:
    """phase2_expected_flips.txt 須可由 extract 腳本自 TODO 重現（禁手編漂移）。"""
    assert EXTRACT_FLIPS.is_file(), "extract_phase2_expected_flips.py 缺失"
    assert PHASE2_FLIPS.is_file()
    assert PHASE2_FLIPS_SHA.is_file()
    proc = subprocess.run(
        ["python3", str(EXTRACT_FLIPS), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, (
        f"flips fixture 與 TODO 抽取不一致 rc={proc.returncode}\n"
        f"stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    actual = _file_sha256(PHASE2_FLIPS)
    side = PHASE2_FLIPS_SHA.read_text(encoding="utf-8").strip().split()[0]
    assert actual == side, f"flips sha256 不符 sidecar: {actual} != {side}"


def test_01_c5_absolute_state_recurse_in_flips() -> None:
    """C5：TODO 絕對態（RECURSE 六條皆 BLOCK）須進 phase2 flips 為 maintain。

    模擬語料 A 含 RECURSE 命令時，排除清單前提不被削弱。
    """
    import importlib.util

    spec = importlib.util.spec_from_file_location("extract_flips", EXTRACT_FLIPS)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 真實 TODO 抽取：RECURSE 六條須在 rows 中
    todo = (REPO_ROOT / "docs" / "GOVB0_FRICTION_TODO.md").read_text(encoding="utf-8")
    rows = mod.extract(todo)
    recurse = [r for r in rows if r["test_id"] == "TEST-2.1-RECURSE"]
    assert len(recurse) == 6, f"RECURSE 應 6 條 maintain，got {len(recurse)}"
    for r in recurse:
        assert r["kind"] == "maintain"
        assert r["from"] == "BLOCK" and r["to"] == "BLOCK"

    # REGRESS 兩條須 BLOCK
    regress = [r for r in rows if r["test_id"] == "TEST-2.2-REGRESS"]
    assert len(regress) == 2, f"REGRESS 應 2 條，got {len(regress)}"
    for r in regress:
        assert r["kind"] == "maintain"
        assert r["from"] == "BLOCK"

    # mutation：自 _DIR_RE 移除絕對態枝 + 關掉 abs 分支 → RECURSE 不再抽出
    src = EXTRACT_FLIPS.read_text(encoding="utf-8")
    mut_src = src
    for frag in (
        '    r"|(?:[一二三四五六七八九十兩\\d]+條)?(?P<abs_all>皆)\\s*(?P<a1>BLOCK|ALLOW)"\n',
        '    r"|(?:[一二三四五六七八九十兩\\d]+條)?(?P<abs_must>須)\\s*(?P<a2>BLOCK|ALLOW)"\n',
    ):
        assert frag in mut_src, f"C5 mutation 錨點漂移: {frag!r}"
        mut_src = mut_src.replace(frag, "", 1)
    mut_src = mut_src.replace(
        'elif dm.group("abs_all") or dm.group("abs_must"):',
        'elif False:  # C5 mut: abs disabled',
        1,
    )
    assert mut_src != src, "C5 mutation 錨點漂移"
    mut_path = REPO_ROOT / "tests" / "governance" / "fixtures" / "_mut_extract_c5.py"
    try:
        mut_path.write_text(mut_src, encoding="utf-8")
        spec_m = importlib.util.spec_from_file_location("extract_flips_mut", mut_path)
        assert spec_m and spec_m.loader
        mod_m = importlib.util.module_from_spec(spec_m)
        spec_m.loader.exec_module(mod_m)
        rows_m = mod_m.extract(todo)
        recurse_m = [r for r in rows_m if r["test_id"] == "TEST-2.1-RECURSE"]
        assert len(recurse_m) == 0, (
            f"C5 mutation 後 RECURSE 應消失以證偽；got {len(recurse_m)}"
        )
    finally:
        if mut_path.is_file():
            mut_path.unlink()


def test_01_invariance_decision_trace(tmp_path: Path) -> None:
    """TEST-0.1-INVARIANCE：語料 A 排除 Phase2 預期翻轉後，snapshot vs 現行 (rc, kind) 逐項相等。

    反向斷言：
      1) 每個被排除的條目必須能在預期翻轉清單中找到對應（禁靜默排除）
      2) 預期翻轉清單中每一條 flip：若命中語料 A 或語料 B，必須在語料 B 有對應且確實翻轉
         （未進語料 B 的未來 Task 翻轉列為 residual，見產出說明；禁用其靜默排除 A）
    """
    assert SNAPSHOT.is_file(), "B0 snapshot 缺失"
    entries = _load_corpus_entries(CORPUS_A)
    corpus_a_n = len(entries)
    flips = _load_phase2_flips()
    flip_only = [f for f in flips if f["kind"] == "flip"]

    keep: list[tuple[dict[str, str], str]] = []
    excluded: list[tuple[dict[str, str], str, dict[str, str]]] = []
    for setup, payload in entries:
        cmd = _payload_command(payload)
        hit = _flip_matches_command(cmd, flip_only) if cmd else None
        if hit is not None:
            excluded.append((setup, payload, hit))
        else:
            keep.append((setup, payload))

    # --- 反向斷言 1：每個被排除的條目必須在預期翻轉清單 ---
    for setup, payload, hit in excluded:
        cmd = _payload_command(payload)
        assert hit is not None
        assert cmd is not None
        assert _cmd_match(cmd, hit["command"]), (
            f"靜默排除：語料 A 命令不在翻轉清單: {cmd!r}"
        )
        assert hit["kind"] == "flip"

    # --- 反向斷言 2：翻轉清單覆蓋（A 或 B 命中者必須在 B 且確實翻轉）---
    b_cmds = _corpus_b_commands()
    residuals: list[str] = []
    for fr in flip_only:
        in_a = any(
            (c := _payload_command(p)) is not None and _cmd_match(c, fr["command"])
            for _, p in entries
        )
        b_match = next((c for c in b_cmds if _cmd_match(c, fr["command"])), None)
        if in_a:
            assert b_match is not None, (
                f"反向2：語料 A 排除所依翻轉不在語料 B: {fr['test_id']} {fr['command']!r}"
            )
        if b_match is None:
            # 未來 Task（尚未進語料 B）— 不得用於排除 A（in_a 已 assert）
            residuals.append(f"{fr['test_id']}:{fr['command'][:60]}")
            continue
        # 在 B → 必須確實翻轉
        tag = hashlib.sha256(b_match.encode("utf-8")).hexdigest()[:12]
        before_d = _decision_for_cmd(SNAPSHOT, b_match, tmp_path / "r2b" / tag)
        after_d = _decision_for_cmd(GATE_CHECK, b_match, tmp_path / "r2a" / tag)
        assert before_d == fr["from"] and after_d == fr["to"], (
            f"反向2：語料 B 對應未依預期翻轉: {fr['test_id']} cmd={b_match!r} "
            f"want {fr['from']}->{fr['to']} got {before_d}->{after_d}"
        )
    # 主斷言：排除後 decision trace 相等
    before = _decision_trace(SNAPSHOT, keep, tmp_path / "before")
    after = _decision_trace(GATE_CHECK, keep, tmp_path / "after")
    assert before == after, (
        "decision trace diff 非空（排除預期翻轉後只應比 (rc, kind)）:\n"
        f"  excluded={[ _payload_command(p) for _, p, _ in excluded ]}\n"
        f"  residuals_not_in_B={residuals}\n"
        f"  before={before}\n  after={after}"
    )
    diff_lines = [f"{b}!={a}" for b, a in zip(before, after) if b != a]
    if len(before) != len(after):
        diff_lines.append(f"len {len(before)}!={len(after)}")
    assert len(diff_lines) == 0

    # 語料 A 條數不得因本機制減少（排除只影響比對，不刪檔）
    assert len(_load_corpus_entries(CORPUS_A)) == corpus_a_n
    assert corpus_a_n == 30, f"語料 A 條數異常: {corpus_a_n}（基線 30）"


def test_01_invariance_exclude_nonflip_mutation(tmp_path: Path) -> None:
    """C4 true mutation：隔離副本把 exclude 改為誤收 non-flip → reverse1 轉紅。

    驗收（brief D-3）：未突變 subject rc=0；突變後同一 reverse1 驗收 rc≠0。
    Subject 為磁碟副本（import 真實 helper），非測試內建 poisoned list。
    """
    import subprocess
    import sys
    import textwrap

    helper_path = Path(__file__).resolve()
    # 隔離 subject：建 excluded + reverse1（與 test_01_invariance_decision_trace 反向斷言 1 同語意）
    subject_ok = tmp_path / "c4_subject_ok.py"
    subject_mut = tmp_path / "c4_subject_mut.py"

    body = textwrap.dedent(
        f"""\
        import importlib.util
        import sys
        from pathlib import Path

        REPO = Path({str(REPO_ROOT)!r})
        HP = Path({str(helper_path)!r})
        spec = importlib.util.spec_from_file_location("tgdf_c4", HP)
        assert spec and spec.loader
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)

        MUTATE = {{MUTATE}}

        entries = m._load_corpus_entries(m.CORPUS_A)
        flips = m._load_phase2_flips()
        flip_only = [f for f in flips if f["kind"] == "flip"]
        excluded = []
        for setup, payload in entries:
            cmd = m._payload_command(payload)
            hit = m._flip_matches_command(cmd, flip_only) if cmd else None
            if hit is not None:
                excluded.append((setup, payload, hit))
            elif MUTATE and cmd is not None:
                # 移除正確 filter：誤把 non-flip 以假 flip hit 排除
                excluded.append((
                    setup,
                    payload,
                    {{
                        "kind": "flip",
                        "command": "__C4_MUT_NONMATCH__",
                        "from": "ALLOW",
                        "to": "BLOCK",
                        "test_id": "MUT",
                    }},
                ))

        # reverse1（decision_trace 反向斷言 1）
        for _s, payload, hit in excluded:
            cmd = m._payload_command(payload)
            assert hit is not None
            assert cmd is not None
            assert m._cmd_match(cmd, hit["command"]), (cmd, hit.get("command"))
            assert hit["kind"] == "flip"
        print("OK")
        """
    )
    subject_ok.write_text(body.replace("{MUTATE}", "False"), encoding="utf-8")
    subject_mut.write_text(body.replace("{MUTATE}", "True"), encoding="utf-8")

    before = subprocess.run(
        [sys.executable, str(subject_ok)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert before.returncode == 0, (
        f"C4 未突變 reverse1 應 rc=0；rc={before.returncode} "
        f"stdout={before.stdout!r} stderr={before.stderr!r}"
    )

    after = subprocess.run(
        [sys.executable, str(subject_mut)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert after.returncode != 0, (
        f"C4 mutation 後 reverse1 應 rc≠0；rc={after.returncode} "
        f"stdout={after.stdout!r} stderr={after.stderr!r}"
    )


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


def _decision_branches_from_gate_check(path: Path = GATE_CHECK) -> dict[str, int]:
    """自 gate_check.sh **結構**機械導出會產生 (rc, kind) 差異的判定分支。

    禁硬編分支清單：每個 id 必須在源碼中有可定位錨點；錨點漂移 → 本函式 assert 失敗。
    搜尋範圍限主判定段（``INPUT="$(cat)"`` 之後），避免命中 deny 後的 match_info 鏡像正則。
    回傳 ``{branch_id: 1-based line_no}``。
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    marker = 'INPUT="$(cat)"'
    assert marker in text, "gate_check 主判定段錨點 INPUT= 漂移"
    main_off = text.index(marker)
    main = text[main_off:]
    found: dict[str, int] = {}

    def _first_line(pattern: str, *, flags: int = 0) -> int:
        m = re.search(pattern, main, flags)
        assert m, f"gate_check 判定錨點漂移: {pattern!r}"
        # 絕對行號 = marker 之前行數 + main 內相對行
        return text[: main_off].count("\n") + main[: m.start()].count("\n") + 1

    # kind 指派 / 通道
    found["deny_task_no_token"] = _first_line(
        r'case "\$tool_name" in\s+Task\)\s+kind="dispatch"',
        flags=re.DOTALL,
    )
    # 源碼字面： (codex|cursor-agent|grok|agy)[[:space:]]
    found["deny_bash_family_cli"] = _first_line(
        r"\(codex\|cursor-agent\|grok\|agy\)\[\[:space:\]\]"
    )
    # 源碼字面： claude[^|]*(-p|--print)（判定段 executor 正則內）
    found["deny_bash_claude_agent"] = _first_line(
        r"claude\[\^\|\]\*\(-p\|--print\)"
    )
    # 源碼字面： scripts/gate(_check)?\.sh
    found["allow_gate_self"] = _first_line(r"scripts/gate\(_check\)\?\\.sh")
    found["deny_env_strip_family"] = _first_line(
        r"\^\[A-Za-z_\]\[A-Za-z0-9_\]\*="
    )
    # 分隔符後 executor：與 family_cli 同條判定正則的 command-position 前綴
    found["deny_sep_family"] = _first_line(
        r"\(\^\|\[;&\|\]\[\[:space:\]\]\*\)\(codex\|cursor-agent\|grok\|agy\)"
    )
    found["deny_write_artifact"] = _first_line(r'kind="artifact"')
    found["allow_write_existing"] = _first_line(
        r'\[ -f "\$fp" \] \|\| kind="artifact"'
    )
    # filename false-positive：註解錨「避免誤擋」
    found["allow_filename_fp"] = _first_line(r"避免誤擋")
    # kind 空放行
    found["allow_nongated"] = _first_line(r'\[ -z "\$kind" \] && exit 0')
    # token / recheck
    found["allow_fresh_no_debt"] = _first_line(
        r"if _gate_check_recheck_debt; then\s+exit 0",
        flags=re.DOTALL,
    )
    found["deny_open_debt"] = _first_line(r'deny_reason="open_debt"')
    found["deny_token_expired"] = _first_line(r'deny_reason="token_expired"')

    n = len(lines)
    for bid, ln in found.items():
        assert 1 <= ln <= n, f"branch {bid} line {ln} out of range 1..{n}"
    return found


def _corpus_a_branch_ids(path: Path = CORPUS_A) -> set[str]:
    """語料 A 中所有 ``# @branch`` 標籤集合。"""
    ids: set[str] = set()
    for setup, _payload in _load_corpus_entries(path):
        bid = setup.get("_branch")
        if bid:
            ids.add(bid)
    return ids


def test_01_snapshot_bundle_integrity() -> None:
    """B0 snapshot 目錄含 gate_check + debt 依賴，各 .sha256 吻合；gate_check 仍為 pre-Phase2。"""
    assert SNAPSHOT_DIR.is_dir(), f"snapshot 目錄缺失: {SNAPSHOT_DIR}"
    assert SNAPSHOT.is_file(), f"snapshot gate_check 缺失: {SNAPSHOT}"
    for name in SNAPSHOT_BUNDLE_FILES:
        body = SNAPSHOT_DIR / name
        side = SNAPSHOT_DIR / f"{name}.sha256"
        assert body.is_file(), f"bundle 缺檔: {name}"
        assert side.is_file(), f"bundle 缺 sha256: {name}.sha256"
        actual = _file_sha256(body)
        expected = side.read_text(encoding="utf-8").strip().split()[0]
        assert actual == expected, f"{name} sha256 不符 sidecar: {actual} != {expected}"
    # gate_check 不可變：必須等於 Phase 2 動工前狀態
    gate_sha = _file_sha256(SNAPSHOT)
    assert gate_sha == PRE_PHASE2_GATE_CHECK_SHA256, (
        f"snapshot gate_check sha 漂移: {gate_sha} != {PRE_PHASE2_GATE_CHECK_SHA256}"
    )
    # 舊路徑 byte-identical（B5 / TODO 路徑相容）
    assert SNAPSHOT_LEGACY.is_file(), "legacy snapshot 路徑缺失"
    assert _file_sha256(SNAPSHOT_LEGACY) == PRE_PHASE2_GATE_CHECK_SHA256
    legacy_side = Path(str(SNAPSHOT_LEGACY) + ".sha256")
    assert legacy_side.is_file()
    assert legacy_side.read_text(encoding="utf-8").strip().split()[0] == PRE_PHASE2_GATE_CHECK_SHA256


def test_01_snapshot_fresh_no_debt_allow(tmp_path: Path) -> None:
    """修 1 核心：bundled snapshot 在 fresh+no-debt 下可真正放行（非 fail-closed）。"""
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
        script=SNAPSHOT,
        env_extra=env_extra,
    )
    assert proc.returncode == 0, (
        f"bundled snapshot 應放行 fresh+no-debt，got rc={proc.returncode}\n"
        f"stderr={proc.stderr}"
    )


def test_01_mut_snapshot_missing_debt_dep_turns_fresh_allow_red(tmp_path: Path) -> None:
    """修 1 mutation：抽掉 _debt_ledger_core.py（與 debt_ledger.sh）→ fresh+no-debt 轉紅。"""
    mut_dir = tmp_path / "snap_mut"
    shutil.copytree(SNAPSHOT_DIR, mut_dir)
    (mut_dir / "_debt_ledger_core.py").unlink()
    (mut_dir / "debt_ledger.sh").unlink()
    mut_script = mut_dir / "gate_check.sh"
    mut_script.chmod(mut_script.stat().st_mode | 0o111)

    gate_dir = tmp_path / "g"
    gate_dir.mkdir()
    (gate_dir / "dispatch.token").write_text("fresh\n", encoding="utf-8")
    debt_audit = tmp_path / "debt_audit.log"
    debt_audit.write_text("", encoding="utf-8")
    env_extra = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(debt_audit),
    }
    proc = _run_gate(
        '{"tool_name":"Task"}',
        gate_dir=gate_dir,
        script=mut_script,
        env_extra=env_extra,
    )
    # 缺依賴 → fail-closed rc!=0；與「應放行」對立 → 斷言轉紅語意
    allow_oracle_green = proc.returncode == 0
    assert not allow_oracle_green, (
        "MUTATION 未使 fresh+no-debt 放行斷言轉紅：缺依賴後仍 rc=0"
    )


def test_01_corpus_a_covers_decision_branches() -> None:
    """修 2：語料 A 覆蓋 gate_check 機械導出的每一個判定分支至少一條。

    分支清單自 gate_check.sh 結構導出（非硬編）；語料以 ``# @branch`` 標籤對應。
    """
    catalog = _decision_branches_from_gate_check(GATE_CHECK)
    tagged = _corpus_a_branch_ids(CORPUS_A)
    missing = set(catalog) - tagged
    assert not missing, (
        f"語料 A 未覆蓋判定分支: {sorted(missing)}; "
        f"catalog={sorted(catalog)}; tagged={sorted(tagged)}"
    )
    # 反向：語料標籤不得憑空發明（防拼錯）
    extra = tagged - set(catalog)
    assert not extra, f"語料 A @branch 不在 gate_check 導出集合: {sorted(extra)}"


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

    現行腳本路徑煙霧；完整改前改後由語料 A ``allow_fresh_no_debt`` + INVARIANCE 覆蓋。
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
