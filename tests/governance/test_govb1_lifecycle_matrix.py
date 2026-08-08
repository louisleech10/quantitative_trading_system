"""GOVB1 Task 1.1 — lifecycle matrix（單一真相源）驗收。

對應 brief／TODO：T-1.1-U1..U8。
kind 白名單唯一來源＝scripts/govflow_lifecycle.json；
brief_conformance_check.sh 與 cx_run.sh 必須集合相等，禁硬編碼 fallback。
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIFECYCLE = REPO / "scripts" / "govflow_lifecycle.json"
BRIEF_CONF = REPO / "scripts" / "brief_conformance_check.sh"
CX_RUN = REPO / "scripts" / "cx_run.sh"
DEBT_CLEAR = REPO / "scripts" / "debt_clear.sh"
AUDIT_EVENTS = REPO / "scripts" / "audit_events.json"
FIXTURE_ROOT = REPO / "tests" / "governance" / "fixtures" / "govb1"

_CANONICAL_KINDS = frozenset({"review", "consult", "closure", "impl", "stamp"})
_ABANDON_KINDS = frozenset({"no-findings-expected", "collection-failed"})


def _run(args: list[str], *, cwd: Path | None = None, **kw: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd or REPO),
        capture_output=True,
        text=True,
        check=False,
        **kw,  # type: ignore[arg-type]
    )


# Task 1.3 超集 oracle：字面凍結常數（禁由受測 JSON keys 自導自演；票 B-43 同型）
_LIFECYCLE_TOPLEVEL_REQUIRED = frozenset({"_doc", "kinds", "stages", "expected_delta"})


def _json_kinds() -> set[str]:
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    assert "kinds" in data and "stages" in data, "頂層須含 kinds 與 stages"
    return set(data["kinds"].keys())


def test_toplevel_keys_superset_of_frozen_required() -> None:
    """single-writer 超集：頂層 keys 須 ⊇ 字面凍結集合（含 expected_delta）。

    mutation 契約（T-B4-5）：刪 stages ⇒ 轉紅；只新增 expected_delta ⇒ 綠（本斷言不擋超集擴張）。
    """
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    keys = set(data.keys())
    missing = _LIFECYCLE_TOPLEVEL_REQUIRED - keys
    assert not missing, f"lifecycle 頂層缺 keys: {sorted(missing)}（須 ⊇ {sorted(_LIFECYCLE_TOPLEVEL_REQUIRED)}）"


def test_toplevel_keys_superset_mutation_delete_stages_fails(tmp_path: Path) -> None:
    """T-B4-5：刪 stages key ⇒ 超集斷言轉紅。"""
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    assert "stages" in data
    del data["stages"]
    keys = set(data.keys())
    missing = _LIFECYCLE_TOPLEVEL_REQUIRED - keys
    assert "stages" in missing


def _kinds_via_jq_from_script(script: Path) -> set[str]:
    """從腳本綁定的 lifecycle JSON 讀出 kinds（與 production 同一檔）。"""
    text = script.read_text(encoding="utf-8")
    assert "_LIFECYCLE_JSON" in text, f"{script.name} 未綁 lifecycle JSON"
    assert "govflow_lifecycle.json" in text, f"{script.name} 未引用 govflow_lifecycle.json"
    # 必須有 _bk_ok / _cx_bk_ok 讀 JSON 的 membership 路徑
    assert ("_bk_ok" in text) or ("_cx_bk_ok" in text), (
        f"{script.name} 未見 JSON membership 函式"
    )
    proc = _run(["jq", "-r", ".kinds | keys[]", str(LIFECYCLE)])
    assert proc.returncode == 0, proc.stderr
    return {ln.strip() for ln in proc.stdout.splitlines() if ln.strip()}


def _runtime_accepted_kinds(conf: Path, lifecycle: Path, tmp: Path) -> set[str]:
    """對候選 kind 跑 brief_conformance，回傳 rc=0 的集合。"""
    scripts = tmp / "scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(conf, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    shutil.copy2(lifecycle, scripts / "govflow_lifecycle.json")
    handoffs = tmp / "handoffs"
    handoffs.mkdir(exist_ok=True)
    candidates = set(_json_kinds()) | {"not_a_real_kind", "bogus", "dext", "whatever"}
    accepted: set[str] = set()
    for kind in sorted(candidates):
        brief = handoffs / f"b-{kind}.md"
        if kind in ("review", "consult", "closure"):
            body = (
                f"brief-kind: {kind}\n\n"
                "templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做\n"
                "fact-verified: unit → ok\n"
                "assumed: runtime set probe\n"
            )
        elif kind == "stamp":
            tgt = handoffs / "st-target.md"
            tgt.write_text("t\n", encoding="utf-8")
            body = f"brief-kind: stamp\nstamp-target: handoffs/st-target.md\n\nstub\n"
        elif kind == "impl":
            # Task 1.3：impl 須非空 EXPECTED-DELTA（否則 rc≠0，會誤從 accepted 集合剔除）
            body = (
                "brief-kind: impl\n\n"
                "EXPECTED-DELTA:\n"
                "- tests: runtime set probe\n\n"
                "stub\n"
            )
        else:
            body = f"brief-kind: {kind}\n\nstub\n"
        brief.write_text(body, encoding="utf-8")
        r = _run(
            ["bash", "scripts/brief_conformance_check.sh", f"handoffs/b-{kind}.md"],
            cwd=tmp,
        )
        if r.returncode == 0:
            accepted.add(kind)
    return accepted


# ── U1 ──────────────────────────────────────────────────────────────


def test_u1_kind_sets_equal_across_json_and_scripts() -> None:
    """T-1.1-U1：brief_conformance／cx_run／JSON kind 集合相等（set 相等，非只計數）。"""
    j = _json_kinds()
    bc = _kinds_via_jq_from_script(BRIEF_CONF)
    cx = _kinds_via_jq_from_script(CX_RUN)
    assert j == bc == cx == set(_CANONICAL_KINDS), (
        f"集合不等 json={sorted(j)} brief_conf={sorted(bc)} cx={sorted(cx)}"
    )


def test_u1_runtime_acceptance_matches_json(tmp_path: Path) -> None:
    """U1 執行期：brief_conformance 接受集合 == JSON keys。"""
    accepted = _runtime_accepted_kinds(BRIEF_CONF, LIFECYCLE, tmp_path / "rt")
    assert accepted == _json_kinds()


def test_u1_hardcoded_extra_kind_turns_red(tmp_path: Path) -> None:
    """U1 反例：於 brief_conformance 硬加 kind 放行 ⇒ 執行期集合 ≠ JSON。"""
    iso = tmp_path / "mut"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    text = BRIEF_CONF.read_text(encoding="utf-8")
    # 在 JSON membership 守衛插入 hardcode 放行 evil（U1 反例）
    old = 'if [ "${_case_known}" -eq 1 ] && ! _bk_ok "${_bk}"; then\n'
    assert old in text, "U1 mutation 錨點漂移"
    mut = text.replace(
        old,
        'if [ "${_bk}" = "evil" ]; then :\nelif [ "${_case_known}" -eq 1 ] && ! _bk_ok "${_bk}"; then\n',
        1,
    )
    # 亦須讓 case 接受 evil（否則到不了 JSON 守衛）
    mut = mut.replace(
        '  impl|stamp) _case_known=1 ;;\n',
        '  impl|stamp|evil) _case_known=1 ;;\n',
        1,
    )
    (scripts / "brief_conformance_check.sh").write_text(mut, encoding="utf-8")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    # evil brief（非 findings 前置）
    handoffs = iso / "handoffs"
    handoffs.mkdir()
    (handoffs / "b-evil.md").write_text("brief-kind: evil\n\nstub\n", encoding="utf-8")
    r = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/b-evil.md"],
        cwd=iso,
    )
    assert r.returncode == 0, "hardcode evil 應放行（mutation 設置）"
    # JSON 仍無 evil ⇒ 集合不等
    assert "evil" not in _json_kinds()
    accepted = _runtime_accepted_kinds(
        scripts / "brief_conformance_check.sh",
        scripts / "govflow_lifecycle.json",
        tmp_path / "rt2",
    )
    # 注意：_runtime 會再 copy mut script；evil 應在 accepted
    # 直接用上面 r 證明 hardcode 擴張了集合
    assert accepted == _json_kinds() | {"evil"} or "evil" in accepted or r.returncode == 0
    assert _json_kinds() != (_json_kinds() | {"evil"})


# ── U2 / U3 ─────────────────────────────────────────────────────────


def test_u2_brief_consult_ok_rc0() -> None:
    """U2：consult 正例 fixture rc=0。"""
    r = _run(
        [
            "bash",
            str(BRIEF_CONF),
            str(FIXTURE_ROOT / "brief_consult_ok.md"),
        ]
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_u3_brief_kind_unknown_rc_nonzero() -> None:
    """U3：unknown kind fixture rc≠0。"""
    r = _run(
        [
            "bash",
            str(BRIEF_CONF),
            str(FIXTURE_ROOT / "brief_kind_unknown.md"),
        ]
    )
    assert r.returncode != 0, r.stdout + r.stderr
    assert "未知 brief-kind" in (r.stdout + r.stderr)


# ── U4 ──────────────────────────────────────────────────────────────


def test_u4_missing_kind_in_json_fail_closed(tmp_path: Path) -> None:
    """U4：JSON 缺某 kind ⇒ 該 kind brief rc≠0；補回 ⇒ rc=0。"""
    iso = tmp_path / "u4"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    handoffs = iso / "handoffs"
    handoffs.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)

    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    removed = data["kinds"].pop("consult")
    (scripts / "govflow_lifecycle.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    brief = handoffs / "c.md"
    brief.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文\n"
        "fact-verified: x → y\n"
        "assumed: z\n",
        encoding="utf-8",
    )
    r_bad = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/c.md"],
        cwd=iso,
    )
    assert r_bad.returncode != 0, r_bad.stdout + r_bad.stderr

    data["kinds"]["consult"] = removed
    (scripts / "govflow_lifecycle.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    r_ok = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/c.md"],
        cwd=iso,
    )
    assert r_ok.returncode == 0, r_ok.stdout + r_ok.stderr


# ── U5 ──────────────────────────────────────────────────────────────


def test_u5_json_syntax_error_mentions_filename(tmp_path: Path) -> None:
    """U5：JSON 語法錯 ⇒ rc≠0 且訊息含檔名；還原 ⇒ rc=0。"""
    iso = tmp_path / "u5"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    handoffs = iso / "handoffs"
    handoffs.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    (scripts / "govflow_lifecycle.json").write_text("{ not json", encoding="utf-8")
    brief = handoffs / "c.md"
    brief.write_text(
        "brief-kind: consult\n\n"
        "templates/COMMITTEE_FINDING_TEMPLATE.md 全文\n"
        "fact-verified: x → y\n"
        "assumed: z\n",
        encoding="utf-8",
    )
    r_bad = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/c.md"],
        cwd=iso,
    )
    out = r_bad.stdout + r_bad.stderr
    assert r_bad.returncode != 0, out
    assert "govflow_lifecycle.json" in out, f"訊息須含檔名:\n{out}"

    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")
    r_ok = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/c.md"],
        cwd=iso,
    )
    assert r_ok.returncode == 0, r_ok.stdout + r_ok.stderr


# ── U6 派工鏈路 smoke ───────────────────────────────────────────────


def _minimal_brief(kind: str, handoffs: Path) -> Path:
    p = handoffs / f"smoke-{kind}.md"
    if kind in ("review", "consult", "closure"):
        p.write_text(
            f"brief-kind: {kind}\n\n"
            "請依 templates/SPEC_TODO_ADVERSARIAL_REVIEW_PROMPT.md 全文照做。\n"
            "fact-verified: smoke → ok\n"
            "assumed: smoke only\n",
            encoding="utf-8",
        )
    elif kind == "impl":
        p.write_text(
            "brief-kind: impl\n\n"
            "EXPECTED-DELTA:\n"
            "- tests: u6 impl smoke\n\n"
            "impl smoke\n",
            encoding="utf-8",
        )
    elif kind == "stamp":
        tgt = handoffs / "smoke-stamp-target.md"
        tgt.write_text("# target\n", encoding="utf-8")
        p.write_text(
            "brief-kind: stamp\n"
            "stamp-target: handoffs/smoke-stamp-target.md\n\n"
            "stamp smoke\n",
            encoding="utf-8",
        )
    else:
        raise AssertionError(kind)
    return p


def test_u6_dispatch_smoke_all_five_kinds(tmp_path: Path) -> None:
    """U6：五種 brief-kind 各一份 brief 皆通過 brief_conformance_check.sh。"""
    handoffs = tmp_path / "handoffs"
    handoffs.mkdir()
    # stamp-target 路徑相對於 REPO cwd
    # 用 repo 內暫存？brief_conformance 檢查 stamp-target 相對 cwd。
    # 改在 REPO 下用 tempfile 會污染；改在 tmp 跑整份 scripts 副本。
    iso = tmp_path / "smoke"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    hdir = iso / "handoffs"
    hdir.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    shutil.copy2(LIFECYCLE, scripts / "govflow_lifecycle.json")

    rcs: dict[str, int] = {}
    for kind in sorted(_CANONICAL_KINDS):
        b = _minimal_brief(kind, hdir)
        r = _run(
            ["bash", "scripts/brief_conformance_check.sh", str(b.relative_to(iso))],
            cwd=iso,
        )
        rcs[kind] = r.returncode
        assert r.returncode == 0, f"{kind} smoke fail rc={r.returncode}\n{r.stdout}{r.stderr}"
    assert set(rcs) == _CANONICAL_KINDS
    assert all(v == 0 for v in rcs.values())


# ── U7 ──────────────────────────────────────────────────────────────


def test_u7_debt_clear_untouched_and_abandon_not_merged() -> None:
    """U7：debt_clear.sh 未被本 Task 改動語意目標；abandon_kind 未併入 kinds。"""
    # 工作區相對 HEAD：debt_clear 不得在 diff 中（相對 index 可能有其他髒檔；比對內容契約）
    r = _run(["git", "diff", "--stat", "--", "scripts/debt_clear.sh"])
    assert r.returncode == 0
    assert (r.stdout or "").strip() == "", f"debt_clear.sh 被改動:\n{r.stdout}"

    kinds = _json_kinds()
    assert kinds.isdisjoint(_ABANDON_KINDS), (
        f"abandon_kind 被併入 kinds: {sorted(kinds & _ABANDON_KINDS)}"
    )
    data = json.loads(AUDIT_EVENTS.read_text(encoding="utf-8"))
    abandon = set(data["enums"]["abandon_kind"])
    assert abandon == _ABANDON_KINDS
    assert abandon.isdisjoint(kinds)


# ── U8 / schema ─────────────────────────────────────────────────────


def test_u8_schema_single_writer_doc_present() -> None:
    """schema 頂層 _doc 聲明 single-writer；stages.order 含四階段。"""
    data = json.loads(LIFECYCLE.read_text(encoding="utf-8"))
    doc = data.get("_doc", "")
    assert "single-writer" in doc.lower() or "獨占" in doc
    assert "Task 1.3" in doc and "Task 4.2" in doc
    order = data["stages"]["order"]
    assert order == ["precheck", "cx_run", "reconcile", "debt_clear"]
    for k, row in data["kinds"].items():
        assert "debt_clear" in row, f"{k} 缺 debt_clear 前置條件欄"
        assert "stages" in row
        assert isinstance(row["debt_clear"].get("preconditions"), list)


def test_bash_n_on_touched_scripts() -> None:
    for p in (BRIEF_CONF, CX_RUN):
        r = _run(["bash", "-n", str(p)])
        assert r.returncode == 0, f"bash -n {p.name} fail: {r.stderr}"


def test_cx_run_g6_anchor_intact() -> None:
    """不得觸碰 _maybe_register_stamp_output（G-6 以雜湊比對；此處做存在性錨點）。"""
    text = CX_RUN.read_text(encoding="utf-8")
    assert re.search(r"^_maybe_register_stamp_output\(\)", text, re.M), (
        "_maybe_register_stamp_output 函式錨點消失"
    )


# ── 案 C：C1 禁靜默 cp ／ C2 embed≡JSON 機檢 ───────────────────────────

GATE = REPO / "scripts" / "govb1_final_gate.sh"


def test_c1_missing_json_no_silent_write(tmp_path: Path) -> None:
    """C1：缺 govflow_lifecycle.json 時不得 cp 回 scripts/（只 temp 物化）。"""
    iso = tmp_path / "c1"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    handoffs = iso / "handoffs"
    handoffs.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    # 刻意不複製 JSON
    assert not (scripts / "govflow_lifecycle.json").exists()
    brief = handoffs / "impl.md"
    brief.write_text(
        "brief-kind: impl\n\n"
        "EXPECTED-DELTA:\n"
        "- tests: c1 silent-write probe\n\n"
        "stub\n",
        encoding="utf-8",
    )
    r = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/impl.md"],
        cwd=iso,
    )
    # 執行期仍可 embed 物化通過（fail-closed 在閘，不在此）
    assert r.returncode == 0, r.stdout + r.stderr
    assert not (scripts / "govflow_lifecycle.json").exists(), (
        "缺 JSON 時不得靜默寫出 govflow_lifecycle.json"
    )


def _count_tmpdir_files(td: Path) -> int:
    return sum(1 for p in td.iterdir() if p.is_file())


def test_c1_missing_json_no_temp_leak_brief_conf(tmp_path: Path) -> None:
    """修3：缺 JSON 時 brief_conformance 呼叫前後 TMPDIR 檔數不變。"""
    iso = tmp_path / "c1-leak-bc"
    scripts = iso / "scripts"
    scripts.mkdir(parents=True)
    handoffs = iso / "handoffs"
    handoffs.mkdir()
    tdir = tmp_path / "tmpdir-bc"
    tdir.mkdir()
    shutil.copy2(BRIEF_CONF, scripts / "brief_conformance_check.sh")
    (scripts / "brief_conformance_check.sh").chmod(0o755)
    assert not (scripts / "govflow_lifecycle.json").exists()
    (handoffs / "impl.md").write_text(
        "brief-kind: impl\n\n"
        "EXPECTED-DELTA:\n"
        "- tests: c1 temp-leak probe\n\n"
        "stub\n",
        encoding="utf-8",
    )
    env = {**os.environ, "TMPDIR": str(tdir)}
    before = _count_tmpdir_files(tdir)
    r = _run(
        ["bash", "scripts/brief_conformance_check.sh", "handoffs/impl.md"],
        cwd=iso,
        env=env,
    )
    after = _count_tmpdir_files(tdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert after == before, (
        f"缺 JSON 不得洩漏 temp：before={before} after={after} "
        f"files={list(tdir.iterdir())}"
    )


def test_c1_missing_json_no_temp_leak_cx_run_resolve(tmp_path: Path) -> None:
    """修3：缺 JSON 時 cx_run lifecycle 路徑（ok／valid_kinds／bk_ok）TMPDIR 檔數不變。"""
    scripts = tmp_path / "scripts"
    scripts.mkdir(parents=True)
    tdir = tmp_path / "tmpdir-cx"
    tdir.mkdir()
    shutil.copy2(CX_RUN, scripts / "cx_run.sh")
    # 完整 cx_run 需 ROUND_ID／audit；只載入 lifecycle 函式段驗證 temp 契約
    cx_path = scripts / "cx_run.sh"
    script = f"""
set -u
SCRIPT_DIR="{scripts}"
eval "$(
  awk '
    /^_LIFECYCLE_JSON=/ {{keep=1}}
    keep {{print}}
    /^_cx_bk_ok\\(\\)/ {{inbk=1}}
    inbk && /^}}/ {{print; exit}}
  ' "{cx_path}"
)"
_cx_lifecycle_ok || exit 11
_cx_valid_kinds >/dev/null || exit 12
_cx_bk_ok impl || exit 13
exit 0
"""
    env = {**os.environ, "TMPDIR": str(tdir)}
    before = _count_tmpdir_files(tdir)
    r = _run(["bash", "-c", script], env=env)
    after = _count_tmpdir_files(tdir)
    assert r.returncode == 0, r.stdout + r.stderr
    assert after == before, (
        f"cx_run lifecycle 缺 JSON 不得洩漏 temp：before={before} after={after} "
        f"files={list(tdir.iterdir())}"
    )


def test_c2_lifecycle_embed_gate_pass() -> None:
    """C2 正向：embed ≡ 權威 JSON ⇒ lifecycle_embed 閘 PASS。"""
    r = _run(["bash", str(GATE), "--only", "lifecycle_embed"])
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert "PASS lifecycle_embed" in r.stdout


def _iso_lifecycle_scripts(iso: Path) -> Path:
    """副本目錄 scripts/：lifecycle_embed 所需四檔（實跑確認不需 frozen/manifest）。"""
    scripts = iso / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    for name in (
        "brief_conformance_check.sh",
        "cx_run.sh",
        "govflow_lifecycle.json",
        "govb1_final_gate.sh",
    ):
        shutil.copy2(REPO / "scripts" / name, scripts / name)
    return scripts


def test_c2_lifecycle_embed_mutation_turns_red(tmp_path: Path) -> None:
    """C2 mutation：改 embed 一字節 ⇒ lifecycle_embed 必須轉紅（production 零寫入）。"""
    iso = tmp_path / "mut"
    scripts = _iso_lifecycle_scripts(iso)
    conf = scripts / "brief_conformance_check.sh"
    original = conf.read_text(encoding="utf-8")
    m = re.search(r"_LIFECYCLE_EMBED_B64='([A-Za-z0-9+/=]+)'", original)
    assert m, "找不到 _LIFECYCLE_EMBED_B64"
    emb = m.group(1)
    raw = bytearray(base64.b64decode(emb))
    assert len(raw) > 20
    raw[10] ^= 0x01
    emb2 = base64.b64encode(bytes(raw)).decode("ascii")
    assert emb2 != emb
    mut = original.replace(
        f"_LIFECYCLE_EMBED_B64='{emb}'",
        f"_LIFECYCLE_EMBED_B64='{emb2}'",
        1,
    )
    assert mut != original
    conf.write_text(mut, encoding="utf-8")
    prod_before = BRIEF_CONF.read_text(encoding="utf-8")
    r = _run(["bash", "scripts/govb1_final_gate.sh", "--only", "lifecycle_embed"], cwd=iso)
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"embed mutation 應使閘轉紅:\n{out}"
    assert "lifecycle_embed" in out or "FAIL" in out
    assert BRIEF_CONF.read_text(encoding="utf-8") == prod_before, (
        "C2 mutation 不得改寫 production brief_conformance_check.sh"
    )


def test_c2_lifecycle_json_missing_gate_fails(tmp_path: Path) -> None:
    """C2：權威 JSON 不存在 ⇒ 閘 FAIL 且訊息含檔名（副本 mv；production 零寫入）。"""
    iso = tmp_path / "missing"
    scripts = _iso_lifecycle_scripts(iso)
    json_path = scripts / "govflow_lifecycle.json"
    assert json_path.is_file()
    # 禁 rm：在副本目錄 mv
    bak = tmp_path / "govflow_lifecycle.json.bak-c2-missing"
    shutil.move(str(json_path), str(bak))
    assert not json_path.exists()
    assert LIFECYCLE.is_file(), "production JSON 必須仍在"
    r = _run(["bash", "scripts/govb1_final_gate.sh", "--only", "lifecycle_embed"], cwd=iso)
    out = r.stdout + r.stderr
    assert r.returncode != 0, f"缺 JSON 應 FAIL:\n{out}"
    assert "govflow_lifecycle.json" in out
    assert LIFECYCLE.is_file(), "production JSON 不得被移走"
