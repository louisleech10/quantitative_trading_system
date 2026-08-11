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

    # mut B: R2 command position only（並關掉 C3 cmdsub 抽取，否則 $() 仍被遞迴抓住）
    #
    # 🔴 GOVB0 B4 之後本案例受**三層**保護，逐層剝除才會漏放：
    #    ① 家族段正則的命令位置含 `$(`　② `_gate_lex_extract_cmdsubs` 遞迴
    #    ③ fail-closed 網的家族條件（B4 新增；`out=$(codex exec x)` 之命令位置
    #       token 含 `$` 且整條含家族名 ⇒ 接住）
    #    只剝 ①② 仍 BLOCK（③ 接住）——那不是本測要證的事，故三層一起剝。
    #    **這不是弱化**：本測要證的是「命令位置定義若縮回 R2 就會漏放」，
    #    前提是該案例只剩那一層；③ 是後來加的另一層，必須一併移除才能還原前提。
    # 🔴 B4 r3：命令位置定義已收斂成單一變數 `_GL_CMDPOS`。
    #    mutation 改為把該定義縮回 R2（僅 `^ ; & |`），比替換組裝後的整串正則穩定。
    old_pat = "_GL_CMDPOS='(^|[;&|(`]|\\$\\()[[:space:]]*'"
    new_pat = "_GL_CMDPOS='(^|[;&|][[:space:]]*)'"
    lex_b = lex_text.replace(old_pat, new_pat, 1)
    assert lex_b != lex_text, "mut B 錨點漂移：_GL_CMDPOS 定義"
    lex_b = lex_b.replace(
        'cmdsubs="$(_gate_lex_extract_cmdsubs "$raw")"',
        'cmdsubs=""',
        1,
    )
    # ③ 剝掉 fail-closed 網的家族條件（還原「只剩命令位置那一層」的前提）
    net_family = (
        '_famtok="claude[^|]*(-p|--print)|(^|[[:space:];&|(\\`=])${_GL_FAMS}${_GL_TOKEND}"'
    )
    assert net_family in lex_b, "mut B 錨點漂移：fail-closed 網之家族條件"
    lex_b = lex_b.replace(net_family, '_famtok="claude[^|]*(-p|--print)"', 1)
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


# ---------------------------------------------------------------------------
# B3-FIX C1／C2／C3（fail-open 關閉 + mutation）
# ---------------------------------------------------------------------------


def test_21_c1_oversize_suffix_blocks(tmp_path: Path) -> None:
    """C1-a／D-2b：8200 byte 前綴 + `; codex exec hi` → BLOCK（禁只掃前綴 ALLOW）。"""
    cmd = ("x" * 8200) + "; codex exec hi"
    assert _got(cmd, tmp_path / "c1a") == "BLOCK"


def test_21_d2_harmless_oversize_allows(tmp_path: Path) -> None:
    """D-2a：echo + 8200 字元無害字串 → ALLOW（不得因長度誤擋）。"""
    cmd = "echo " + ("a" * 8200)
    assert _got(cmd, tmp_path / "d2a") == "ALLOW"


def test_21_d2_oversize_gate_substr_still_blocks(tmp_path: Path) -> None:
    """D-2e／D-1 疊加：8200B + `; scripts/gate.sh; codex exec hi` → BLOCK。"""
    cmd = ("x" * 8200) + "; scripts/gate.sh; codex exec hi"
    assert _got(cmd, tmp_path / "d2e") == "BLOCK"


def test_21_d1_gate_substr_no_bypass(tmp_path: Path) -> None:
    """D-1：子字串嵌入 scripts/gate.sh 不得放行真派工；純自呼叫仍 ALLOW。"""
    assert _got("codex exec x; echo scripts/gate.sh", tmp_path / "d1a") == "BLOCK"
    assert _got("codex exec x  # scripts/gate.sh", tmp_path / "d1b") == "BLOCK"
    assert _got("bash scripts/gate.sh dispatch --task-id X", tmp_path / "d1c") == "ALLOW"
    assert _got("bash scripts/gate_check.sh", tmp_path / "d1d") == "ALLOW"


def test_21_c1_oversize_failclosed_bounded(tmp_path: Path) -> None:
    """D-2d：4MB 級輸入有界時間內回覆且不 fail-open（尾端真派工仍 BLOCK）。"""
    import time

    # 無害 4MB：不得卡死；無家族字樣 → ALLOW（非 fail-open）
    cmd_harmless = "y" * 4_000_000
    t0 = time.perf_counter()
    got_h = _got(cmd_harmless, tmp_path / "d2d_h")
    elapsed_h = time.perf_counter() - t0
    assert got_h == "ALLOW", f"4MB 無害不得誤擋；got={got_h}"
    assert elapsed_h < 30.0, f"4MB 無害判定逾時: {elapsed_h:.3f}s"

    # 尾端真派工：不得因長度 fail-open
    cmd_tp = ("y" * 4_000_000) + "; codex exec hi"
    t1 = time.perf_counter()
    got_tp = _got(cmd_tp, tmp_path / "d2d_tp")
    elapsed_tp = time.perf_counter() - t1
    assert got_tp == "BLOCK", f"4MB 尾端派工不得 fail-open ALLOW；got={got_tp}"
    assert elapsed_tp < 30.0, f"4MB 尾端派工判定逾時: {elapsed_tp:.3f}s"


def test_21_c1_mut_restore_prefix_truncate_allows(tmp_path: Path) -> None:
    """D-2 mutation：還原 head -c 截斷掃描 → 尾端真派工轉 ALLOW。"""
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    # 在 raw= 指派後注入截斷（突變為舊 C1 fail-open）
    anchor = '  raw="$cmd"\n'
    inject = (
        '  raw="$cmd"\n'
        "  local _max_lex=8192\n"
        '  if [ "${#cmd}" -gt "$_max_lex" ]; then\n'
        '    raw="$(printf \'%s\' "$cmd" | head -c "$_max_lex")"\n'
        "  fi\n"
    )
    assert anchor in lex_text, "D-2 mutation 錨點漂移：raw= 指派"
    # 只替換 _gate_cmd_is_dispatch 內第一處 raw=
    fn_start = lex_text.find("_gate_cmd_is_dispatch() {")
    assert fn_start >= 0, "D-2 mutation 錨點漂移：_gate_cmd_is_dispatch"
    fn_body = lex_text[fn_start:]
    assert anchor in fn_body, "D-2 mutation 錨點漂移：fn 內 raw="
    fn_mut = fn_body.replace(anchor, inject, 1)
    lex_m = lex_text[:fn_start] + fn_mut
    assert lex_m != lex_text, "D-2 mutation 錨點漂移"
    mut = _write_mut_pair(tmp_path / "c1m", "mut_c1.sh", gate_text, lex_m)
    cmd = ("x" * 8200) + "; codex exec hi"
    assert _got(cmd, tmp_path / "c1mbase") == "BLOCK"
    assert _got(cmd, tmp_path / "c1mmut", script=mut) == "ALLOW"


def test_21_d1_mut_substr_self_excludes_allows(tmp_path: Path) -> None:
    """D-1 mutation：還原子字串 gate 排除 → 真派工+echo gate 轉 ALLOW。"""
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    # 關掉 self_gate 早退，改在 is_dispatch 後子字串放行
    old = (
        "    if _gate_cmd_is_self_gate \"$cmd\"; then\n"
        "      exit 0\n"
        "    fi\n"
        "    if [ \"${GATE_LEGACY_DECISION:-0}\" = \"1\" ]; then\n"
        "      if printf '%s' \"$cmd\" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'; then\n"
        "        kind=\"dispatch\"\n"
        "      fi\n"
        "    elif _gate_cmd_is_dispatch \"$cmd\"; then\n"
        "      kind=\"dispatch\"\n"
        "    fi\n"
    )
    new = (
        "    if [ \"${GATE_LEGACY_DECISION:-0}\" = \"1\" ]; then\n"
        "      if printf '%s' \"$cmd\" | grep -Eq '(^|[;&|][[:space:]]*)(codex|cursor-agent|grok|agy)[[:space:]]|claude[^|]*(-p|--print)'; then\n"
        "        if printf '%s' \"$cmd\" | grep -Eq 'scripts/gate(_check)?\\.sh'; then exit 0; fi\n"
        "        kind=\"dispatch\"\n"
        "      fi\n"
        "    elif _gate_cmd_is_dispatch \"$cmd\"; then\n"
        "      if printf '%s' \"$cmd\" | grep -Eq 'scripts/gate(_check)?\\.sh'; then exit 0; fi\n"
        "      kind=\"dispatch\"\n"
        "    fi\n"
    )
    assert old in gate_text, "D-1 mutation 錨點漂移"
    gate_m = gate_text.replace(old, new, 1)
    assert gate_m != gate_text
    mut = _write_mut_pair(tmp_path / "d1m", "mut_d1.sh", gate_m, lex_text)
    victim = "codex exec x; echo scripts/gate.sh"
    assert _got(victim, tmp_path / "d1mb") == "BLOCK"
    assert _got(victim, tmp_path / "d1mm", script=mut) == "ALLOW"


def test_21_c2_quoted_env_prefix(tmp_path: Path) -> None:
    """C2：引號 env 前綴後家族 CLI → BLOCK；E-3 與無害 echo 不回歸。"""
    assert _got('FOO="bar" codex exec x', tmp_path / "c2a") == "BLOCK"
    assert _got("FOO='bar baz' codex exec x", tmp_path / "c2b") == "BLOCK"
    assert _got("out=$(codex exec x)", tmp_path / "c2c") == "BLOCK"
    assert _got('FOO="bar" echo hi', tmp_path / "c2d") == "ALLOW"


def test_21_c2_mut_simple_strip_allows_quoted_env(tmp_path: Path) -> None:
    """C2 mutation：關掉 quote-aware strip 函式 → FOO=\"bar\" codex 轉 ALLOW。"""
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    # 讓 _gate_strip_env_once 永遠回傳原字串（no-op）→ 引號賦值不被剝
    fn_head = "_gate_strip_env_once() {\n      local s=\"${1-}\" n\n"
    fn_mut = (
        "_gate_strip_env_once() {\n"
        "      # C2 mutation: no-op strip\n"
        "      printf '%s' \"${1-}\"\n"
        "      return 1\n"
        "      local s=\"${1-}\" n\n"
    )
    assert fn_head in gate_text, "C2 mutation 錨點漂移"
    gate_m = gate_text.replace(fn_head, fn_mut, 1)
    assert gate_m != gate_text
    mut = _write_mut_pair(tmp_path / "c2m", "mut_c2.sh", gate_m, lex_text)
    assert _got('FOO="bar" codex exec x', tmp_path / "c2mb") == "BLOCK"
    assert _got('FOO="bar" codex exec x', tmp_path / "c2mm", script=mut) == "ALLOW"
    # E-3 在 mutation 下仍應 BLOCK（未誤剝 $(...)）
    assert _got("out=$(codex exec x)", tmp_path / "c2me", script=mut) == "BLOCK"


def test_21_c3_dq_cmdsub_and_literal(tmp_path: Path) -> None:
    """C3：雙引號內 $()／反引號 → BLOCK；純字面與 commit 訊息 → ALLOW。"""
    assert _got('echo "$(codex exec x)"', tmp_path / "c3a") == "BLOCK"
    assert _got("echo \"`codex exec x`\"", tmp_path / "c3b") == "BLOCK"
    assert _got('echo "codex exec x"', tmp_path / "c3c") == "ALLOW"
    assert _got('git commit -m "x; codex closure review"', tmp_path / "c3d") == "ALLOW"


def test_21_c3_mut_drop_cmdsub_extract_allows(tmp_path: Path) -> None:
    """C3 mutation：關掉 cmdsub 抽取 → 雙引號內 $() 轉 ALLOW。"""
    gate_text = GATE_CHECK.read_text(encoding="utf-8")
    lex_text = GATE_LEX.read_text(encoding="utf-8")
    lex_m = lex_text.replace(
        'cmdsubs="$(_gate_lex_extract_cmdsubs "$raw")"',
        'cmdsubs=""',
        1,
    )
    assert lex_m != lex_text, "C3 mutation 錨點漂移"
    mut = _write_mut_pair(tmp_path / "c3m", "mut_c3.sh", gate_text, lex_m)
    assert _got('echo "$(codex exec x)"', tmp_path / "c3mb") == "BLOCK"
    assert _got('echo "$(codex exec x)"', tmp_path / "c3mm", script=mut) == "ALLOW"
    # 字面仍 ALLOW
    assert _got('echo "codex exec x"', tmp_path / "c3ml", script=mut) == "ALLOW"
