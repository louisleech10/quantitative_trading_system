"""GOVB0 Task 2.1 — 引號感知 ＋ -c 遞迴（判定轉向）。

TEST-2.1-* 對應 docs/GOVB0_FRICTION_TODO.md Phase 2 / Task 2.1。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_CHECK = REPO_ROOT / "scripts" / "gate_check.sh"
GATE_LEX = REPO_ROOT / "scripts" / "_gate_lex.sh"


def _run_gate(
    cmd: str,
    *,
    gate_dir: Path,
    script: Path = GATE_CHECK,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        ensure_ascii=False,
    )
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
        encoding="utf-8",
        errors="replace",
        check=False,
        env=env,
    )


def _got(cmd: str, gate_dir: Path, **kw) -> str:
    proc = _run_gate(cmd, gate_dir=gate_dir, **kw)
    return "BLOCK" if proc.returncode != 0 else "ALLOW"


def test_21_fp_pgrep_and_commit(tmp_path: Path) -> None:
    """TEST-2.1-FP：pgrep／commit 訊息由 BLOCK 轉 ALLOW。"""
    assert _got("pgrep -fl 'codex exec|cursor-agent|grok '", tmp_path / "a") == "ALLOW"
    assert (
        _got('git commit -m "fix: x; codex closure review done"', tmp_path / "b")
        == "ALLOW"
    )


def test_21_e3_five_vectors(tmp_path: Path) -> None:
    """TEST-2.1-E3：五條由 ALLOW 轉 BLOCK。"""
    vectors = [
        'eval "codex exec x"',
        "out=$(codex exec x)",
        "out=`codex exec x`",
        "(codex exec x)",
        "eval 'grok -m grok-4.5 -p x'",
    ]
    for i, cmd in enumerate(vectors):
        assert _got(cmd, tmp_path / f"e{i}") == "BLOCK", cmd


def test_21_recurse_six(tmp_path: Path) -> None:
    """TEST-2.1-RECURSE：六條皆 BLOCK。"""
    vectors = [
        'bash -c "codex exec x"',
        "sh -c 'grok -m grok-4.5 -p x'",
        'bash -c "claude -p x"',
        "true && codex exec x",
        "false || grok -m x -p y",
        "echo x | xargs codex exec",
    ]
    for i, cmd in enumerate(vectors):
        assert _got(cmd, tmp_path / f"r{i}") == "BLOCK", cmd


def test_21_outside_semi_still_block(tmp_path: Path) -> None:
    """TEST-2.1-OUTSIDE：引號外分號後真派工維持 BLOCK。"""
    assert _got('echo start; grok -m grok-4.5 -p "x"', tmp_path / "o") == "BLOCK"


def test_21_1b_multiline_four(tmp_path: Path) -> None:
    """TEST-2.1-1B：跨行剝引號 4/4（F-6）。"""
    cases = [
        (
            'git commit -m "fix: something\ncodex 並獨立重跑探針確認\ndone"',
            "ALLOW",
        ),
        (
            'git commit -m "line1\ngrok 那邊已複核\nline3"',
            "ALLOW",
        ),
        (
            'echo start\ncodex exec -s workspace-write "p"',
            "BLOCK",
        ),
        (
            'set -e\ngrok -m grok-4.5 -p "x"',
            "BLOCK",
        ),
    ]
    for i, (cmd, want) in enumerate(cases):
        assert _got(cmd, tmp_path / f"m{i}") == want, f"case{i} {want}"


def _write_mut_pair(dir_path: Path, name: str, gate_text: str, lex_text: str) -> Path:
    """寫入 gate 腳本 + 同目錄 _gate_lex.sh（source 相對 SCRIPT_DIR）。"""
    dir_path.mkdir(parents=True, exist_ok=True)
    gate = dir_path / name
    gate.write_text(gate_text, encoding="utf-8")
    gate.chmod(0o755)
    (dir_path / "_gate_lex.sh").write_text(lex_text, encoding="utf-8")
    return gate


def test_21_mut_remove_recurse_and_narrow_pos(tmp_path: Path) -> None:
    """TEST-2.1-MUT：移除 -c/eval 遞迴 → RECURSE 轉 ALLOW；縮回 R2 位置 → E-3 轉 ALLOW。"""
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")

    # mut A: no inners
    lex_a = lex_text.replace(
        'inners="$(_gate_lex_extract_inners "$raw")"',
        'inners=""',
        1,
    )
    assert lex_a != lex_text
    mut_a = _write_mut_pair(tmp_path / "a", "mut_a.sh", gate_text, lex_a)
    assert _got('bash -c "codex exec x"', tmp_path / "ra", script=mut_a) == "ALLOW"

    # mut B: R2 command position only
    old_pat = (
        "(^|[;&|(`]|\\$\\()[[:space:]]*((eval|xargs)[[:space:]]+)?"
        "((\\S*/)?)((codex|cursor-agent|grok|agy)[[:space:]]|(codex|cursor-agent|grok|agy)$)"
    )
    new_pat = "(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]"
    lex_b = lex_text.replace(old_pat, new_pat, 1)
    if lex_b == lex_text:
        # 後備：較短錨
        lex_b = lex_text.replace(
            "(codex|cursor-agent|grok|agy)[[:space:]]|(codex|cursor-agent|grok|agy)$",
            "(codex|cursor-agent|grok|agy)[[:space:]]",
            1,
        )
        # 並縮命令位置前綴
        lex_b = lex_b.replace(
            "(^|[;&|(`]|\\$\\()[[:space:]]*((eval|xargs)[[:space:]]+)?",
            "(^|[;&|][[:space:]]*)",
            1,
        )
    assert lex_b != lex_text
    mut_b = _write_mut_pair(tmp_path / "b", "mut_b.sh", gate_text, lex_b)
    e3 = [
        'eval "codex exec x"',
        "out=$(codex exec x)",
        "out=`codex exec x`",
        "(codex exec x)",
        "eval 'grok -m grok-4.5 -p x'",
    ]
    for i, cmd in enumerate(e3):
        if "eval" in cmd:
            continue
        assert _got(cmd, tmp_path / f"eb{i}", script=mut_b) == "ALLOW", cmd

    # mut C: sed 行內剝引號 → 1b ①② 轉 BLOCK
    lex_c = re.sub(
        r"_gate_lex_preprocess\(\) \{.*?\n\}",
        '_gate_lex_preprocess() {\n'
        "  printf '%s' \"${1-}\" | sed -E \"s/'[^']*'//g; s/\\\"[^\\\"]*\\\"//g\"\n"
        "}",
        lex_text,
        count=1,
        flags=re.DOTALL,
    )
    assert lex_c != lex_text
    mut_c = _write_mut_pair(tmp_path / "c", "mut_c.sh", gate_text, lex_c)
    ml = 'git commit -m "fix: something\ncodex 並獨立重跑探針確認\ndone"'
    assert _got(ml, tmp_path / "mc", script=mut_c) == "BLOCK"
