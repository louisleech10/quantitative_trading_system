"""GOVFLOW Phase 2 — result_state 收窄（format-failed）＋ orphan-success 否定 oracle。

Test ID 對齊 docs/GOV_DISPATCH_FLOW_FIX_TODO.md Phase 2 測試表：
  T2-U1 / T2-U2 / T2-U3 / T2-N1 / T2-B1 / T2-B2 / T2-C1 / T2-C2 / T2-C3
  T2-M35 / T2-M36 / T2-M37 / T2-M38  （P16 §V M35–M38 常駐 mutation）

探針一律隔離副本（tmp_path）；rc 直接取，不經 pipe。
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path

import pytest

from tests.governance import _debt_probe_helper as _dph

REPO_ROOT = Path(__file__).resolve().parents[2]

_REF = "照 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文"
_FACT = "fact-verified: cx_run emit 順序 → format check 在 audit append 之前"
_ASSUMED = "assumed: CX_STUB_MODE=success 在 findings-kind 寫最小合法 finding"


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_lines(audit: Path) -> list[dict]:
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


def _events(audit: Path, name: str | None = None) -> list[dict]:
    rows = _read_json_lines(audit)
    if name is None:
        return rows
    return [r for r in rows if r.get("event") == name]


def _harness(tmp_path: Path, *, kind: str = "review") -> dict:
    """隔離 repo：scripts 副本 + 空 audit + handoffs。"""
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
        "cx_run.sh",
        "audit_append.sh",
        "audit_events.json",
        "governance_families.sh",
        "governance_families.json",
        "governance_roles.json",
        "brief_conformance_check.sh",
        "completeness_check.sh",
        "debt_clear.sh",
        "debt_ledger.sh",
        "_debt_ledger_core.py",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            shutil.copy2(src, scripts / name)
            if name.endswith(".sh"):
                (scripts / name).chmod(0o755)

    stamp_target = handoffs / "t2-stamp-target.md"
    stamp_target.write_text("## 戳記\n", encoding="utf-8")

    if kind in ("review", "consult", "closure"):
        brief_text = (
            f"brief-kind: {kind}\n\n"
            f"{_REF}\n"
            f"{_FACT}\n"
            f"{_ASSUMED}\n\n"
            "Phase 2 format-failed harness brief.\n"
        )
    elif kind == "impl":
        brief_text = "brief-kind: impl\n\n照 TODO 實作 B2（impl 路徑行為不變）。\n"
    elif kind == "stamp":
        brief_text = (
            "brief-kind: stamp\n"
            "stamp-target: handoffs/t2-stamp-target.md\n\n"
            "stamp path brief.\n"
        )
    else:
        raise ValueError(f"unknown kind={kind}")

    brief = handoffs / f"t2-brief-{kind}.md"
    brief.write_text(brief_text, encoding="utf-8")

    env = {
        "GOVERNANCE_TEST_HARNESS": "1",
        "DEBT_AUDIT_OVERRIDE": str(audit),
        "GATE_DIR_OVERRIDE": str(gate_dir),
        "CX_STUB_MODE": "success",
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": os.environ.get("LANG", "C"),
    }
    return {
        "root": root,
        "audit": audit,
        "gate_dir": gate_dir,
        "scripts": scripts,
        "brief": brief,
        "brief_rel": f"handoffs/t2-brief-{kind}.md",
        "env": env,
        "handoffs": handoffs,
        "kind": kind,
    }


def _open_round(
    h: dict,
    *,
    round_id: str,
    session: str,
    fams: list[str],
    out_prefix: str,
) -> None:
    brief_sha = _sha256_file(h["brief"])
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
        "task_id=GOVFLOW-B2-T2",
        "--field",
        f"brief_path={h['brief_rel']}",
        "--field",
        f"brief_sha256={brief_sha}",
        "--field",
        f"brief_sha256_norm={brief_sha}",
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


def _run_cx(
    h: dict,
    *,
    family: str,
    out_rel: str,
    round_id: str,
    stub: str | None = "success",
    extra_env: dict[str, str] | None = None,
    via_helper: bool = False,
) -> "subprocess.CompletedProcess[str]":
    """執行隔離副本 cx_run。

    via_helper=True 時走 ``_dph.CX_RUN_TARGET``（mutation 探針
    monkeypatch 此常數以注入變異腳本；禁只為靜態閘加空 monkeypatch）。
    """
    env = dict(h["env"])
    env["ROUND_ID"] = round_id
    if stub is None:
        env.pop("CX_STUB_MODE", None)
    else:
        env["CX_STUB_MODE"] = stub
    if extra_env:
        env.update(extra_env)
    script = _dph.CX_RUN_TARGET if via_helper else (h["scripts"] / "cx_run.sh")
    return _dph.run_cmd(
        script,
        family,
        h["brief_rel"],
        out_rel,
        env=env,
        cwd=h["root"],
    )


def _force_stub_bad_finding(scripts: Path) -> None:
    """隔離副本：findings-kind stub 改寫空殼 finding → completeness 必紅。"""
    path = scripts / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    old = (
        "      local fam_u\n"
        "      fam_u=\"$(printf '%s' \"${fam}\" | tr '[:lower:]' '[:upper:]')\"\n"
        "      {\n"
        "        printf '## %s-R1-P2-01\\n\\n' \"${fam_u}\"\n"
        "        printf '**斷言**: CX_STUB_MODE=success harness minimal legal finding\\n\\n'\n"
        "        printf '**碼證**: scripts/cx_run.sh CX_STUB_MODE=success\\n\\n'\n"
        "        printf '**來源摘要**: handoffs/stub-%s.md#aaaaaaaaaaaa\\n\\n' \"${fam}\"\n"
        "        printf 'stub harness body\\n'\n"
        "      } > \"${out}\"\n"
    )
    new = (
        "      local fam_u\n"
        "      fam_u=\"$(printf '%s' \"${fam}\" | tr '[:lower:]' '[:upper:]')\"\n"
        "      {\n"
        "        printf '## %s-R1-P0-01\\n\\n' \"${fam_u}\"\n"
        "        printf 'empty shell — missing required fields\\n'\n"
        "      } > \"${out}\"\n"
    )
    assert old in text, "stub success findings-kind anchor missing in isolated cx_run"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _restore_old_emit_before_format(scripts: Path) -> None:
    """隔離副本：還原舊順序（先 emit 再格式檢查）以證偽 orphan-success。

    突變後：格式紅時 audit 會先寫 success（舊 bug），T2-N1 應轉紅。
    """
    path = scripts / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    # 將「_fmt_rc=...; _emit...」改成先 emit（fmt=0）再跑格式檢查並改寫不了已寫的 success
    old = (
        '  _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"\n'
        '  _emit_family_result "${cli_rc}" "${_fmt_rc}" || {\n'
        '    echo "ERROR: 寫入 committee_family_result 失敗" >&2\n'
        "    exit 1\n"
        "  }\n"
    )
    # 舊順序：先以 fmt_rc=0 emit（必 success），再檢查格式（只 exit 3 不回滾）
    new = (
        '  _emit_family_result "${cli_rc}" 0 || {\n'
        '    echo "ERROR: 寫入 committee_family_result 失敗" >&2\n'
        "    exit 1\n"
        "  }\n"
        '  _fmt_rc="$(_run_format_check_if_needed "${cli_rc}")"\n'
    )
    assert old in text, "emit-after-format anchor missing; cannot restore old order"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _degrade_format_failed_to_success(scripts: Path) -> None:
    """隔離副本：format-failed 降級記成 success（三值退回二值；M36）。"""
    path = scripts / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    old = (
        '    if [ "${fmt_rc}" -ne 0 ] 2>/dev/null; then\n'
        '      result_state="format-failed"\n'
        "    else\n"
        '      result_state="success"\n'
        "    fi\n"
    )
    new = (
        '    if [ "${fmt_rc}" -ne 0 ] 2>/dev/null; then\n'
        '      result_state="success"  # MUTATED M36: degrade format-failed\n'
        "    else\n"
        '      result_state="success"\n'
        "    fi\n"
    )
    assert old in text, "format-failed branch anchor missing; cannot degrade"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _checker_missing_fail_open(scripts: Path) -> None:
    """隔離副本：checker 不存在時 fail-open（fmt_rc=0；M37）。"""
    path = scripts / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    old = (
        '        if [ ! -f "${_cc}" ] || [ ! -r "${_cc}" ]; then\n'
        '          echo "ERROR: completeness_check.sh 不存在或不可讀 → fail-closed（不得記 success）" >&2\n'
        "          _rc=127\n"
        "        else\n"
    )
    new = (
        '        if [ ! -f "${_cc}" ] || [ ! -r "${_cc}" ]; then\n'
        "          # MUTATED M37: fail-open when checker missing\n"
        "          _rc=0\n"
        "        else\n"
    )
    assert old in text, "checker fail-closed anchor missing; cannot fail-open"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _format_failed_exit_zero(scripts: Path) -> None:
    """隔離副本：format-failed 時 process rc 改成 0（M38）。"""
    path = scripts / "cx_run.sh"
    text = path.read_text(encoding="utf-8")
    old = (
        '  if [ "${_fmt_rc}" -ne 0 ]; then\n'
        '    echo "[cx_run] ⚠️ ${fam} 產出**格式不合規**（見上）：${out}" >&2\n'
        '    echo "[cx_run]    audit 已記 result_state=format-failed（可同輪重派；debt_clear 仍拒銷帳）。" >&2\n'
        '    echo "[cx_run]    請於此時修正或重派，勿等到收集節點才發現。" >&2\n'
        '    echo "[cx_run] ${fam} done rc=${cli_rc} out=${out}（格式不合規 → exit 3）"\n'
        "    exit 3\n"
        "  fi\n"
    )
    new = (
        '  if [ "${_fmt_rc}" -ne 0 ]; then\n'
        '    echo "[cx_run] MUTATED M38: format fail but exit 0" >&2\n'
        "    exit 0\n"
        "  fi\n"
    )
    assert old in text, "format-failed exit 3 anchor missing; cannot exit 0"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def _oracle_format_failed_green(
    h: dict,
    *,
    family: str,
    out_rel: str,
    round_id: str,
    via_helper: bool = False,
):
    """綠燈 oracle：格式紅 ⇒ result_state==format-failed 且 process rc==3。

    回傳 (process, latest_row)。呼叫端對綠路徑 assert 成功條件；
    對突變路徑證明同一條件不成立（轉紅）。
    via_helper=True：經 helper.CX_RUN_TARGET（供 mutation monkeypatch）。
    """
    r = _run_cx(
        h, family=family, out_rel=out_rel, round_id=round_id, via_helper=via_helper
    )
    rows = _events(h["audit"], "committee_family_result")
    latest = rows[-1] if rows else {}
    return r, latest


# ── T2-U1 ──────────────────────────────────────────────


def test_t2_u1_format_red_result_state_format_failed(tmp_path: Path) -> None:
    """T2-U1：格式紅 ⇒ result_state==format-failed。"""
    h = _harness(tmp_path, kind="review")
    _force_stub_bad_finding(h["scripts"])
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2u1"
    _open_round(h, round_id=rid, session="s-u1", fams=["codex"], out_prefix=out_prefix)
    r = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r.returncode == 3, r.stdout + r.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "format-failed"
    assert rows[0]["output_sha256"]  # 非空


# ── T2-U2 ──────────────────────────────────────────────


def test_t2_u2_format_green_success_redispatch_rejected(tmp_path: Path) -> None:
    """T2-U2：格式綠 ⇒ success，重派仍被拒。"""
    h = _harness(tmp_path, kind="review")
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2u2"
    _open_round(h, round_id=rid, session="s-u2", fams=["codex"], out_prefix=out_prefix)
    r1 = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r1.returncode == 0, r1.stdout + r1.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "success"
    n1 = len(_read_json_lines(h["audit"]))
    r2 = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r2.returncode != 0
    combined = r2.stdout + r2.stderr
    assert "success" in combined.lower() or "拒重派" in combined
    assert len(_read_json_lines(h["audit"])) == n1


# ── T2-U3 ──────────────────────────────────────────────


def test_t2_u3_format_failed_allows_same_round_redispatch(tmp_path: Path) -> None:
    """T2-U3：format-failed ⇒ 同輪重派允許。"""
    h = _harness(tmp_path, kind="review")
    _force_stub_bad_finding(h["scripts"])
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2u3"
    _open_round(h, round_id=rid, session="s-u3", fams=["codex"], out_prefix=out_prefix)
    r1 = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r1.returncode == 3, r1.stdout + r1.stderr
    assert _events(h["audit"], "committee_family_result")[-1]["result_state"] == "format-failed"
    # 恢復合法 stub → 重派應允許並寫第二筆
    # 重新從 repo 覆寫 cx_run（合法 stub）
    shutil.copy2(REPO_ROOT / "scripts" / "cx_run.sh", h["scripts"] / "cx_run.sh")
    (h["scripts"] / "cx_run.sh").chmod(0o755)
    r2 = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 2
    assert rows[0]["result_state"] == "format-failed"
    assert rows[1]["result_state"] == "success"


# ── T2-N1 ──────────────────────────────────────────────


def test_t2_n1_orphan_success_negative_oracle(tmp_path: Path) -> None:
    """T2-N1：orphan-success 否定 oracle——格式紅時 audit 最新不得為 success。"""
    h = _harness(tmp_path, kind="review")
    _force_stub_bad_finding(h["scripts"])
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2n1"
    _open_round(h, round_id=rid, session="s-n1", fams=["codex"], out_prefix=out_prefix)
    r = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r.returncode == 3, r.stdout + r.stderr
    latest = _events(h["audit"], "committee_family_result")[-1]
    # 否定 oracle：不得為 success
    assert latest["result_state"] != "success"
    assert latest["result_state"] == "format-failed"


# ── T2-B1 ──────────────────────────────────────────────


def test_t2_b1_empty_sha_exception_only_failed(tmp_path: Path) -> None:
    """T2-B1：空 sha 例外僅 failed；format-failed 用非空 sha。"""
    h = _harness(tmp_path, kind="review")
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2b1"
    _open_round(h, round_id=rid, session="s-b1", fams=["codex"], out_prefix=out_prefix)

    # failed 路徑（fail_rc）→ 空 sha
    r_fail = _run_cx(
        h,
        family="codex",
        out_rel=f"{out_prefix}-codex.md",
        round_id=rid,
        stub="fail_rc",
        extra_env={"CX_STUB_RC": "7"},
    )
    assert r_fail.returncode != 0
    failed_row = _events(h["audit"], "committee_family_result")[-1]
    assert failed_row["result_state"] == "failed"
    assert failed_row["output_sha256"] == ""

    # format-failed 路徑 → 非空 sha
    _force_stub_bad_finding(h["scripts"])
    r_ff = _run_cx(
        h,
        family="codex",
        out_rel=f"{out_prefix}-codex.md",
        round_id=rid,
        stub="success",
    )
    assert r_ff.returncode == 3, r_ff.stdout + r_ff.stderr
    ff_row = _events(h["audit"], "committee_family_result")[-1]
    assert ff_row["result_state"] == "format-failed"
    assert ff_row["output_sha256"]
    assert len(ff_row["output_sha256"]) == 64


# ── T2-B2 ──────────────────────────────────────────────


def test_t2_b2_checker_missing_fail_closed(tmp_path: Path) -> None:
    """T2-B2：checker 不可執行／不存在 ⇒ fail-closed，不得記 success。"""
    h = _harness(tmp_path, kind="review")
    # 刪除隔離副本內的 completeness_check
    cc = h["scripts"] / "completeness_check.sh"
    assert cc.is_file()
    cc.unlink()
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2b2"
    _open_round(h, round_id=rid, session="s-b2", fams=["codex"], out_prefix=out_prefix)
    r = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r.returncode == 3, r.stdout + r.stderr
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] != "success"
    assert rows[0]["result_state"] == "format-failed"
    assert "fail-closed" in (r.stdout + r.stderr) or "不存在" in (r.stdout + r.stderr)


# ── T2-C1 ──────────────────────────────────────────────


def test_t2_c1_debt_clear_rejects_format_failed(tmp_path: Path) -> None:
    """T2-C1：debt_clear 對 format-failed 仍拒銷帳（守衛⑤ 不放寬）。"""
    h = _harness(tmp_path, kind="review")
    rid = str(uuid.uuid4())
    session = "s-c1"
    fams = ["codex"]
    out_prefix = f"handoffs/{session}"
    _open_round(h, round_id=rid, session=session, fams=fams, out_prefix=out_prefix)

    # 合法產出檔 + format-failed 事件（模擬最新狀態）
    body = (
        "## CODEX-R1-P0-01\n\n"
        "**斷言**: clear reject test\n\n"
        "**碼證**: path:1\n\n"
        "**來源摘要**: sources/review-codex.md#aaaaaaaaaaaa\n"
    )
    out_path = h["root"] / f"{out_prefix}-codex.md"
    out_path.write_text(body, encoding="utf-8")
    out_sha = _sha256_file(out_path)
    r_append = _dph.run_cmd(
        h["scripts"] / "audit_append.sh",
        "--event",
        "committee_family_result",
        "--field",
        f"round_id={rid}",
        "--field",
        "family=codex",
        "--field",
        "attempt_id=att-ff",
        "--field",
        "cli_rc=0",
        "--field",
        f"output_path={out_prefix}-codex.md",
        "--field",
        f"output_sha256={out_sha}",
        "--field",
        "result_state=format-failed",
        "--field",
        "actor=test",
        "--field",
        "origin_script=cx_run.sh",
        env=h["env"],
        cwd=h["root"],
    )
    assert r_append.returncode == 0, r_append.stdout + r_append.stderr

    # 建 review lock + session（debt_clear 需要）
    sess = h["root"] / "handoffs" / "reconcile" / session
    sources = sess / "sources"
    sources.mkdir(parents=True)
    src = sources / "review-codex.md"
    src.write_text(body, encoding="utf-8")
    (sess / "synth.md").write_text(body, encoding="utf-8")
    lock = {
        "version": 1,
        "session_id": session,
        "round_id": rid,
        "expected_roster": fams,
        "sources": [
            {
                "realpath": str(src.resolve()),
                "sha256": _sha256_file(src),
                "family": "codex",
            }
        ],
        "freeze_ts": "2026-08-03T00:00:00Z",
        "closure_state": "FROZEN",
        "mode": "review",
    }
    lock_path = sess / "sources.lock"
    lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")

    r = _dph.run_cmd(
        h["scripts"] / "debt_clear.sh",
        "--round-id",
        rid,
        "--session",
        session,
        "--lock",
        str(lock_path),
        env=h["env"],
        cwd=h["root"],
    )
    assert r.returncode != 0, "debt_clear must reject format-failed"
    combined = r.stdout + r.stderr
    assert "success" in combined or "format-failed" in combined or "result_state" in combined
    # 不得寫入 committee_debt_clear
    assert _events(h["audit"], "committee_debt_clear") == []


# ── T2-C2 ──────────────────────────────────────────────


def test_t2_c2_impl_kind_unchanged(tmp_path: Path) -> None:
    """T2-C2：brief-kind=impl ⇒ 判準與行為皆不變（仍 success + stub-ok，不跑 format）。"""
    h = _harness(tmp_path, kind="impl")
    # impl 角色閘：implementer=grok
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2c2"
    _open_round(h, round_id=rid, session="s-c2", fams=["grok"], out_prefix=out_prefix)
    r = _run_cx(h, family="grok", out_rel=f"{out_prefix}-grok.md", round_id=rid)
    assert r.returncode == 0, r.stdout + r.stderr
    out_path = h["root"] / f"{out_prefix}-grok.md"
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert content.startswith("stub-ok family=grok")
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "success"
    assert rows[0]["output_sha256"] == _sha256_file(out_path)


# ── T2-C3 ──────────────────────────────────────────────


def test_t2_c3_format_failed_dual_track_audit_and_exit3(tmp_path: Path) -> None:
    """T2-C3：format-failed 雙軌——audit 記 format-failed 且 process rc==3。"""
    h = _harness(tmp_path, kind="review")
    _force_stub_bad_finding(h["scripts"])
    rid = str(uuid.uuid4())
    out_prefix = "handoffs/t2c3"
    _open_round(h, round_id=rid, session="s-c3", fams=["codex"], out_prefix=out_prefix)
    r = _run_cx(h, family="codex", out_rel=f"{out_prefix}-codex.md", round_id=rid)
    assert r.returncode == 3, f"expected exit 3, got {r.returncode}: {r.stdout + r.stderr}"
    rows = _events(h["audit"], "committee_family_result")
    assert len(rows) == 1
    assert rows[0]["result_state"] == "format-failed"


# ── T2-M35..M38 常駐 mutation probes（P16 §V M35–M38）──────────────
# 形態：不套用變異 ⇒ 綠 oracle 成立；套用變異 ⇒ 同一 oracle 條件不成立（轉紅）。
# 探針本身在雙路徑皆 assert 可觀測結果，禁止恆真斷言。
# 執行路徑：monkeypatch helper.CX_RUN_TARGET → 隔離副本（與 test_debt_gate 同配方；
# 真的重導向，不是為騙過 mutation_probe_static 而加的空 monkeypatch）。


def test_mutation_t2_m35_emit_order_orphan_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-M35／M35：emit 順序還原 ⇒ orphan-success 復發。

    不套用：result_state==format-failed（綠）
    套用 `_restore_old_emit_before_format`：result_state==success（綠 oracle 轉紅）
    """
    # ── 不套用變異 → 綠（CX_RUN_TARGET 指隔離未變異腳本）──
    h_fix = _harness(tmp_path / "m35-fix", kind="review")
    _force_stub_bad_finding(h_fix["scripts"])
    cx_fix = h_fix["scripts"] / "cx_run.sh"
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", cx_fix)
    rid_fix = str(uuid.uuid4())
    out_fix = "handoffs/t2m35-fix"
    _open_round(
        h_fix, round_id=rid_fix, session="s-m35-fix", fams=["codex"], out_prefix=out_fix
    )
    r_fix, latest_fix = _oracle_format_failed_green(
        h_fix,
        family="codex",
        out_rel=f"{out_fix}-codex.md",
        round_id=rid_fix,
        via_helper=True,
    )
    assert r_fix.returncode == 3, r_fix.stdout + r_fix.stderr
    assert latest_fix.get("result_state") == "format-failed"
    assert latest_fix.get("result_state") != "success"

    # ── 套用變異 → 綠 oracle 條件不成立（orphan-success）──
    h_mut = _harness(tmp_path / "m35-mut", kind="review")
    _force_stub_bad_finding(h_mut["scripts"])
    _restore_old_emit_before_format(h_mut["scripts"])
    cx_mut = h_mut["scripts"] / "cx_run.sh"
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", cx_mut)
    rid_mut = str(uuid.uuid4())
    out_mut = "handoffs/t2m35-mut"
    _open_round(
        h_mut, round_id=rid_mut, session="s-m35-mut", fams=["codex"], out_prefix=out_mut
    )
    r_mut, latest_mut = _oracle_format_failed_green(
        h_mut,
        family="codex",
        out_rel=f"{out_mut}-codex.md",
        round_id=rid_mut,
        via_helper=True,
    )
    # process 仍 exit 3（格式檢查在 emit 後仍失敗），但 audit 已是 success
    assert r_mut.returncode == 3, r_mut.stdout + r_mut.stderr
    # 綠 oracle「不得為 success」在此不成立 → 證明 T2-N1 會轉紅
    assert latest_mut.get("result_state") == "success", (
        f"M35 mutation must reintroduce orphan-success; got {latest_mut!r}"
    )
    green_oracle_holds = (
        latest_mut.get("result_state") == "format-failed"
        and latest_mut.get("result_state") != "success"
    )
    assert not green_oracle_holds, "M35: green oracle must turn red under emit-order mutation"


def test_mutation_t2_m36_degrade_format_failed_to_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-M36／M36：format-failed 降級記 success ⇒ 三態／format-failed 斷言轉紅。

    不套用：format-failed + 非空 sha（綠）
    套用：result_state==success（format-failed 分支消失）
    """
    # ── 不套用 → 綠（三態 format-failed 支）──
    h_fix = _harness(tmp_path / "m36-fix", kind="review")
    _force_stub_bad_finding(h_fix["scripts"])
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_fix["scripts"] / "cx_run.sh")
    rid_fix = str(uuid.uuid4())
    out_fix = "handoffs/t2m36-fix"
    _open_round(
        h_fix, round_id=rid_fix, session="s-m36-fix", fams=["codex"], out_prefix=out_fix
    )
    r_fix, latest_fix = _oracle_format_failed_green(
        h_fix,
        family="codex",
        out_rel=f"{out_fix}-codex.md",
        round_id=rid_fix,
        via_helper=True,
    )
    assert r_fix.returncode == 3, r_fix.stdout + r_fix.stderr
    assert latest_fix.get("result_state") == "format-failed"
    assert latest_fix.get("output_sha256"), "format-failed 須非空 sha"
    assert len(latest_fix["output_sha256"]) == 64

    # ── 套用變異 → format-failed 斷言轉紅 ──
    h_mut = _harness(tmp_path / "m36-mut", kind="review")
    _force_stub_bad_finding(h_mut["scripts"])
    _degrade_format_failed_to_success(h_mut["scripts"])
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_mut["scripts"] / "cx_run.sh")
    rid_mut = str(uuid.uuid4())
    out_mut = "handoffs/t2m36-mut"
    _open_round(
        h_mut, round_id=rid_mut, session="s-m36-mut", fams=["codex"], out_prefix=out_mut
    )
    r_mut, latest_mut = _oracle_format_failed_green(
        h_mut,
        family="codex",
        out_rel=f"{out_mut}-codex.md",
        round_id=rid_mut,
        via_helper=True,
    )
    assert r_mut.returncode == 3, r_mut.stdout + r_mut.stderr
    assert latest_mut.get("result_state") == "success", (
        f"M36 mutation must degrade format-failed→success; got {latest_mut!r}"
    )
    # 三態中 format-failed 支：result_state==format-failed 不成立
    three_state_ff_holds = latest_mut.get("result_state") == "format-failed"
    assert not three_state_ff_holds, "M36: format-failed three-state arm must turn red"


def test_mutation_t2_m37_checker_missing_fail_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-M37／M37：checker 缺失 fail-open ⇒ fail-closed 斷言轉紅。

    不套用：刪 checker ⇒ format-failed（綠）
    套用 fail-open：刪 checker ⇒ success
    """
    # ── 不套用 → 綠 ──
    h_fix = _harness(tmp_path / "m37-fix", kind="review")
    cc_fix = h_fix["scripts"] / "completeness_check.sh"
    assert cc_fix.is_file()
    cc_fix.unlink()
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_fix["scripts"] / "cx_run.sh")
    rid_fix = str(uuid.uuid4())
    out_fix = "handoffs/t2m37-fix"
    _open_round(
        h_fix, round_id=rid_fix, session="s-m37-fix", fams=["codex"], out_prefix=out_fix
    )
    r_fix = _run_cx(
        h_fix,
        family="codex",
        out_rel=f"{out_fix}-codex.md",
        round_id=rid_fix,
        via_helper=True,
    )
    assert r_fix.returncode == 3, r_fix.stdout + r_fix.stderr
    latest_fix = _events(h_fix["audit"], "committee_family_result")[-1]
    assert latest_fix["result_state"] == "format-failed"
    assert latest_fix["result_state"] != "success"

    # ── 套用變異 → fail-closed 斷言轉紅 ──
    h_mut = _harness(tmp_path / "m37-mut", kind="review")
    _checker_missing_fail_open(h_mut["scripts"])
    cc_mut = h_mut["scripts"] / "completeness_check.sh"
    assert cc_mut.is_file()
    cc_mut.unlink()
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_mut["scripts"] / "cx_run.sh")
    rid_mut = str(uuid.uuid4())
    out_mut = "handoffs/t2m37-mut"
    _open_round(
        h_mut, round_id=rid_mut, session="s-m37-mut", fams=["codex"], out_prefix=out_mut
    )
    r_mut = _run_cx(
        h_mut,
        family="codex",
        out_rel=f"{out_mut}-codex.md",
        round_id=rid_mut,
        via_helper=True,
    )
    # fail-open：格式檢查跳過 ⇒ success + process rc==0
    assert r_mut.returncode == 0, (
        f"M37 fail-open should yield rc=0; got {r_mut.returncode}: "
        f"{r_mut.stdout + r_mut.stderr}"
    )
    latest_mut = _events(h_mut["audit"], "committee_family_result")[-1]
    assert latest_mut["result_state"] == "success", (
        f"M37 mutation must fail-open to success; got {latest_mut!r}"
    )
    fail_closed_holds = latest_mut["result_state"] != "success"
    assert not fail_closed_holds, "M37: fail-closed oracle must turn red under fail-open mutation"


def test_mutation_t2_m38_format_failed_exit_zero(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """T2-M38／M38：format-failed 時 process rc 改 0 ⇒ exit 3 斷言轉紅。

    不套用：rc==3（綠）
    套用：rc==0（exit 3 斷言轉紅）；audit 仍可為 format-failed
    """
    # ── 不套用 → 綠 ──
    h_fix = _harness(tmp_path / "m38-fix", kind="review")
    _force_stub_bad_finding(h_fix["scripts"])
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_fix["scripts"] / "cx_run.sh")
    rid_fix = str(uuid.uuid4())
    out_fix = "handoffs/t2m38-fix"
    _open_round(
        h_fix, round_id=rid_fix, session="s-m38-fix", fams=["codex"], out_prefix=out_fix
    )
    r_fix, latest_fix = _oracle_format_failed_green(
        h_fix,
        family="codex",
        out_rel=f"{out_fix}-codex.md",
        round_id=rid_fix,
        via_helper=True,
    )
    assert r_fix.returncode == 3, r_fix.stdout + r_fix.stderr
    assert latest_fix.get("result_state") == "format-failed"

    # ── 套用變異 → exit 3 斷言轉紅 ──
    h_mut = _harness(tmp_path / "m38-mut", kind="review")
    _force_stub_bad_finding(h_mut["scripts"])
    _format_failed_exit_zero(h_mut["scripts"])
    monkeypatch.setattr(_dph, "CX_RUN_TARGET", h_mut["scripts"] / "cx_run.sh")
    rid_mut = str(uuid.uuid4())
    out_mut = "handoffs/t2m38-mut"
    _open_round(
        h_mut, round_id=rid_mut, session="s-m38-mut", fams=["codex"], out_prefix=out_mut
    )
    r_mut, latest_mut = _oracle_format_failed_green(
        h_mut,
        family="codex",
        out_rel=f"{out_mut}-codex.md",
        round_id=rid_mut,
        via_helper=True,
    )
    assert r_mut.returncode == 0, (
        f"M38 mutation must exit 0 on format fail; got {r_mut.returncode}: "
        f"{r_mut.stdout + r_mut.stderr}"
    )
    # audit 仍記 format-failed（只改 process rc）
    assert latest_mut.get("result_state") == "format-failed", latest_mut
    exit3_holds = r_mut.returncode == 3
    assert not exit3_holds, "M38: exit-3 oracle must turn red under exit-0 mutation"

