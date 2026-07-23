"""B5 Task 6.1 — 5 completeness oracle（1:1 nodeid）+ P0 不稀釋子斷言 + retrofit 守門。

Oracle 契約表（TODO Phase6 Task6.1）：
  ① test_oracle1_id_completeness     — synth 漏 1 union ID → id_coverage<1.0, rc≠0
  ①b test_oracle1_p0_not_diluted     — 總 92% 含 1 P0 missing → p0p1_missing≠[], rc≠0
  ② test_oracle2_invalid_dup_unknown — unknown ID / 跨源 dup → 拒收 rc≠0
  ③ test_oracle3_closure_late_round  — freeze 後 late 檔 → sha 不符 rc≠0
  ④ test_oracle4_body_hash_mechanical— synth body≠source → body-hash 不符 rc≠0
  ⑤ test_oracle5_post_review_residual— committee_accepted 缺 1 ID → residual>0 rc≠0

+ test_retrofit_body_hash_preserved — replay strip-ID hash 守恆 + 非 vacuous coverage
+ B5C1-C4：獨立 coverage / 冪等+dup / nested-tail / missing_ids 一律列出
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"
REPLAY_SH = REPO_ROOT / "scripts" / "replay_convergence_coverage.sh"
WHOLEMAP = REPO_ROOT / "handoffs" / "20260722-ic-map-WHOLEMAP-v2.md"
UNION = REPO_ROOT / "handoffs" / "20260722-pipeline-design-review-UNION.md"


def _sha12(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finding(
    fid: str,
    *,
    assert_text: str = "assert body",
    code_text: str = "code proof",
    src: str = "sources/review.md",
) -> str:
    d = _sha12(f"{fid}|{assert_text}|{code_text}")
    return (
        f"## {fid}\n\n"
        f"**斷言**: {assert_text}\n\n"
        f"**碼證**: {code_text}\n\n"
        f"**來源摘要**: {src}#{d}\n"
    )


def _write_lock(
    session: Path,
    *,
    roster: list[str],
    sources: list[dict],
) -> Path:
    lock = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": roster,
        "sources": sorted(sources, key=lambda e: e["realpath"]),
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    path = session / "sources.lock"
    path.write_text(json.dumps(lock, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _session(
    tmp_path: Path,
    *,
    name: str,
    files: dict[str, str],
    synth: str,
    roster: list[str] | None = None,
) -> Path:
    """files: basename -> body；basename 須 *-<family>.md。"""
    session = tmp_path / name
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True)
    entries: list[dict] = []
    fams: list[str] = []
    for fname, body in files.items():
        p = sources_dir / fname
        p.write_text(body, encoding="utf-8")
        fam = fname.rsplit("-", 1)[-1].replace(".md", "").lower()
        fams.append(fam)
        entries.append(
            {
                "realpath": str(p.resolve()),
                "sha256": _sha256_file(p),
                "family": fam,
            }
        )
    (session / "synth.md").write_text(synth, encoding="utf-8")
    _write_lock(session, roster=roster or sorted(set(fams)), sources=entries)
    return session


def _run(session: Path) -> subprocess.CompletedProcess[str]:
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


def _combined(r: subprocess.CompletedProcess[str]) -> str:
    return (r.stdout or "") + (r.stderr or "")


# ---------------------------------------------------------------------------
# Oracle ① ID completeness
# ---------------------------------------------------------------------------


def test_oracle1_id_completeness(tmp_path: Path) -> None:
    """synth 漏 1 個 union ID → id_coverage<1.0 且 rc≠0。"""
    b1 = _finding("CODEX-R1-P2-01")
    b2 = _finding("COMPOSER-R1-P2-01")
    session = _session(
        tmp_path,
        name="o1_miss",
        files={"a-codex.md": b1, "b-composer.md": b2},
        synth=b1,  # 漏 COMPOSER
        roster=["codex", "composer"],
    )
    result = _run(session)
    assert result.returncode != 0, f"Oracle① 漏 ID 應 FAIL; out={_combined(result)!r}"
    # 可證偽：id_coverage = 1/2 = 0.5 < 1.0
    union = {"CODEX-R1-P2-01", "COMPOSER-R1-P2-01"}
    synth_ids = {"CODEX-R1-P2-01"}
    cov = len(union & synth_ids) / len(union)
    assert cov < 1.0
    assert "COMPOSER-R1-P2-01" in _combined(result)


# ---------------------------------------------------------------------------
# Oracle ①b P0 不稀釋（屬 Oracle① 子斷言，非第六 oracle）
# ---------------------------------------------------------------------------


def test_oracle1_p0_not_diluted(tmp_path: Path) -> None:
    """總覆蓋率 ~92% 但含 1 個 P0 missing → p0p1_missing≠[] 且 rc≠0。

    構造：12 個 ID，synth 含 11（漏 1 個 P0）→ coverage=11/12≈0.9167≥0.90，
    但仍須 hard-fail（比例不得稀釋 P0）。
    """
    ids = [f"GROK-R1-P2-{i:02d}" for i in range(1, 12)]  # 11 個 P2
    p0 = "GROK-R1-P0-01"
    all_ids = ids + [p0]
    assert len(all_ids) == 12
    blocks = {fid: _finding(fid) for fid in all_ids}
    src_body = "".join(blocks[fid] for fid in all_ids)
    # synth 漏 P0 → 11/12 ≈ 91.67%
    synth_body = "".join(blocks[fid] for fid in ids)
    cov = 11 / 12
    assert cov >= 0.90
    assert cov < 1.0

    session = _session(
        tmp_path,
        name="o1_p0",
        files={"review-grok.md": src_body},
        synth=synth_body,
        roster=["grok"],
    )
    result = _run(session)
    out = _combined(result)
    assert result.returncode != 0, f"P0 missing 即使 coverage≥90% 仍須 FAIL; out={out!r}"
    assert "p0p1_missing" in out, f"須顯式報告 p0p1_missing; out={out!r}"
    assert p0 in out


# ---------------------------------------------------------------------------
# Oracle ② invalid / dup / unknown
# ---------------------------------------------------------------------------


def test_oracle2_invalid_dup_unknown(tmp_path: Path) -> None:
    """unknown ID（synth 有、union 無）與跨源 dup → 拒收 rc≠0。"""
    # --- unknown ---
    b_ok = _finding("CODEX-R1-P2-01")
    b_unknown = _finding("GROK-R1-P2-99")  # 無來源
    session_u = _session(
        tmp_path,
        name="o2_unknown",
        files={"a-codex.md": b_ok},
        synth=b_ok + b_unknown,
        roster=["codex"],
    )
    r_u = _run(session_u)
    out_u = _combined(r_u)
    assert r_u.returncode != 0, f"unknown ID 應拒收; out={out_u!r}"
    assert "unknown" in out_u.lower() or "GROK-R1-P2-99" in out_u

    # --- cross-source dup ---
    session_d = _session(
        tmp_path,
        name="o2_dup",
        files={
            "a-codex.md": _finding("CODEX-R1-P0-01", assert_text="from-a"),
            "b-composer.md": _finding("CODEX-R1-P0-01", assert_text="from-b"),
        },
        synth=_finding("CODEX-R1-P0-01"),
        roster=["codex", "composer"],
    )
    r_d = _run(session_d)
    out_d = _combined(r_d)
    assert r_d.returncode != 0, f"跨源 dup 應拒收; out={out_d!r}"
    assert "duplicate" in out_d.lower() or "CODEX-R1-P0-01" in out_d


# ---------------------------------------------------------------------------
# Oracle ③ closure / late / round
# ---------------------------------------------------------------------------


def test_oracle3_closure_late_round(tmp_path: Path) -> None:
    """lock freeze 後改 source → sha≠lock → rc≠0。"""
    body = _finding("GROK-R1-P0-01", assert_text="frozen-body")
    session = _session(
        tmp_path,
        name="o3_late",
        files={"review-grok.md": body},
        synth=body,
        roster=["grok"],
    )
    late = session / "sources" / "review-grok.md"
    late.write_text(
        _finding("GROK-R1-P0-01", assert_text="LATE_AFTER_FREEZE"),
        encoding="utf-8",
    )
    lock = json.loads((session / "sources.lock").read_text(encoding="utf-8"))
    assert lock["sources"][0]["sha256"] != _sha256_file(late)

    result = _run(session)
    out = _combined(result)
    assert result.returncode != 0, f"late 檔應 FAIL; out={out!r}"
    assert "sha" in out.lower() or "late" in out.lower() or "lock" in out.lower()


# ---------------------------------------------------------------------------
# Oracle ④ body hash 機械（M2 owner；純 byte，不依賴 Phase7）
# ---------------------------------------------------------------------------


def test_oracle4_body_hash_mechanical(tmp_path: Path) -> None:
    """synth body≠source（同 ID）→ body-hash 不符 rc≠0。"""
    src = _finding(
        "GROK-R1-P0-01",
        assert_text="ORIGINAL_ASSERT_BODY",
        code_text="src-code",
    )
    synth = _finding(
        "GROK-R1-P0-01",
        assert_text="TAMPERED_ASSERT_BODY",
        code_text="src-code",
    )
    session = _session(
        tmp_path,
        name="o4_body",
        files={"review-grok.md": src},
        synth=synth,
        roster=["grok"],
    )
    result = _run(session)
    out = _combined(result)
    assert result.returncode != 0, f"body-hash 竄改應 FAIL; out={out!r}"
    assert "body-hash" in out.lower() or "body hash" in out.lower()


# ---------------------------------------------------------------------------
# Oracle ⑤ post-review residual（B5 固定 fixture committee_accepted.json）
# ---------------------------------------------------------------------------


def test_oracle5_post_review_residual(tmp_path: Path) -> None:
    """committee_accepted.json 缺 1 個 union ID → residual>0 rc≠0。

    schema: {"accepted_ids":[...]}（B5 fixture；Phase7 charter 在 B6）
    """
    b1 = _finding("CODEX-R1-P2-01")
    b2 = _finding("COMPOSER-R1-P2-01")
    session = _session(
        tmp_path,
        name="o5_residual",
        files={"a-codex.md": b1, "b-composer.md": b2},
        synth=b1 + b2,
        roster=["codex", "composer"],
    )
    # 故意只 accept 一個
    (session / "committee_accepted.json").write_text(
        json.dumps({"accepted_ids": ["CODEX-R1-P2-01"]}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    result = _run(session)
    out = _combined(result)
    assert result.returncode != 0, f"residual>0 應 FAIL; out={out!r}"
    assert "residual" in out.lower()
    assert "COMPOSER-R1-P2-01" in out


# ---------------------------------------------------------------------------
# retrofit + 非循環 coverage（Task 6.1 / TC10 + B5C1-C4）
# ---------------------------------------------------------------------------


def _canonical_body_hash(text: str) -> str:
    """strip heading-ID 行後正規化換行再 sha256（與 replay 腳本一致；恰 ##）。"""
    lines_out: list[str] = []
    id_heading = re.compile(
        r"^\s*##(?!#)\s+[A-Z]+-R[0-9]+-P[0-3]-[0-9]{2,}\s*$"
    )
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if id_heading.match(line):
            continue
        lines_out.append(line.rstrip())
    while lines_out and lines_out[-1] == "":
        lines_out.pop()
    body = "\n".join(lines_out) + ("\n" if lines_out else "")
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _run_replay(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(REPLAY_SH)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_replay_independent_coverage_drop_synth_id(tmp_path: Path) -> None:
    """B5C1：union 與 synth 獨立來源；抽掉 synth 1 ID → coverage<1 且 missing_ids 列缺。

    可證偽反例：若 union/synth 同源 retrofit，抽 synth 無法使 coverage<1（循環保證 1.0）。
    """
    assert REPLAY_SH.is_file(), f"缺 replay 腳本: {REPLAY_SH}"
    work = tmp_path / "cov_work"
    handoffs = work / "handoffs"
    handoffs.mkdir(parents=True)

    # 構造獨立 fixture：union 10 ID，synth 缺 1 → coverage=0.9
    union_ids = [f"CODEX-R1-P2-{i:02d}" for i in range(1, 11)]
    dropped = union_ids[-1]  # CODEX-R1-P2-10
    assert dropped == "CODEX-R1-P2-10"

    union_path = handoffs / "fixture-union-codex.md"
    body = "".join(
        f"## {fid}\n\n**斷言**: u\n\n**碼證**: c\n\n**來源摘要**: u#{_sha12(fid)}\n\n"
        for fid in union_ids
    )
    union_path.write_text(body, encoding="utf-8")

    synth_ids = union_ids[:-1]
    synth_path = handoffs / "fixture-synth-RECONCILE.md"
    # 表格提及（非 heading）— 模擬 RECONCILE 風格
    synth_path.write_text(
        "# fixture RECONCILE\n\n| # | 來源 ID |\n|---|--------|\n"
        + "\n".join(f"| C{i} | {fid} |" for i, fid in enumerate(synth_ids, 1))
        + "\n",
        encoding="utf-8",
    )

    out_dir = work / "out"
    env = os.environ.copy()
    env["REPLAY_REPO_ROOT"] = str(work)
    env["REPLAY_OUT_DIR"] = str(out_dir)
    env["REPLAY_UNION_FILES"] = "handoffs/fixture-union-codex.md"
    env["REPLAY_SYNTH_FILE"] = "handoffs/fixture-synth-RECONCILE.md"
    env["REPLAY_SKIP_RETROFIT"] = "1"
    env["REPLAY_MIN_COVERAGE"] = "0.0"  # 允許 <0.90 以觀測 missing（腳本仍寫 JSON）

    result = _run_replay(env)
    out = (result.stdout or "") + (result.stderr or "")
    cov_path = out_dir / "coverage.json"
    assert cov_path.is_file(), f"須寫 coverage.json; out={out!r}"
    cov = json.loads(cov_path.read_text(encoding="utf-8"))

    assert "missing_ids" in cov, f"coverage.json 一律須 missing_ids: {cov}"
    assert cov["union_size"] == 10
    assert cov["synth_size"] == 9
    assert float(cov["coverage"]) == pytest.approx(0.9)
    assert float(cov["coverage"]) < 1.0
    assert dropped in cov["missing_ids"], f"缺 ID 須列出: {cov['missing_ids']}"
    # 來源獨立（非同源）
    assert cov["union_sources"] != [cov["synth_source"]]
    assert "fixture-union" in cov["union_sources"][0]
    assert "fixture-synth" in cov["synth_source"]
    # min_cov=0 → PASS 仍可（缺項已可稽核）
    assert result.returncode == 0, f"min_cov=0 時缺 1 P2 應 PASS; out={out!r}"


def test_replay_missing_ids_always_listed_p2(tmp_path: Path) -> None:
    """B5C4：抽任何 ID（含 P2）→ coverage.json missing_ids 含該 ID（不論比例）。"""
    work = tmp_path / "b5c4"
    handoffs = work / "handoffs"
    handoffs.mkdir(parents=True)
    # 13 ID 漏 1 P2 → coverage≈0.923 ≥0.90 舊邏輯會靜默
    ids = [f"GROK-R1-P2-{i:02d}" for i in range(1, 14)]
    dropped = "GROK-R1-P2-13"
    (handoffs / "u-grok.md").write_text(
        "".join(
            f"## {fid}\n\n**斷言**: a\n\n**碼證**: c\n\n**來源摘要**: x#{_sha12(fid)}\n\n"
            for fid in ids
        ),
        encoding="utf-8",
    )
    kept = [i for i in ids if i != dropped]
    (handoffs / "synth.md").write_text(
        "reconcile mentions: " + " ".join(kept) + "\n",
        encoding="utf-8",
    )
    out_dir = work / "out"
    env = os.environ.copy()
    env["REPLAY_REPO_ROOT"] = str(work)
    env["REPLAY_OUT_DIR"] = str(out_dir)
    env["REPLAY_UNION_FILES"] = "handoffs/u-grok.md"
    env["REPLAY_SYNTH_FILE"] = "handoffs/synth.md"
    env["REPLAY_SKIP_RETROFIT"] = "1"
    env["REPLAY_MIN_COVERAGE"] = "0.90"

    result = _run_replay(env)
    out = (result.stdout or "") + (result.stderr or "")
    cov = json.loads((out_dir / "coverage.json").read_text(encoding="utf-8"))
    assert float(cov["coverage"]) >= 0.90
    assert float(cov["coverage"]) < 1.0
    assert dropped in cov["missing_ids"], f"P2 缺項須可稽核: {cov}"
    # 預設 min 0.90 且 coverage≈0.923 → PASS，但 missing 必列
    assert result.returncode == 0, f"coverage≥0.90 應 PASS; out={out!r}"
    assert cov["p0p1_missing"] == []


def test_replay_retrofit_idempotent_and_reject_dup(tmp_path: Path) -> None:
    """B5C2：retrofit 冪等（tmp 副本兩次結果一致）；同檔重複 canonical heading → 拒。"""
    work = tmp_path / "idem"
    handoffs = work / "handoffs"
    handoffs.mkdir(parents=True)
    # 乾淨無 ID 的 h2 文檔
    clean = "# title\n\n## Section Alpha\n\nbody-a\n\n## Section Beta\n\nbody-b\n"
    target = handoffs / "retro-doc.md"
    target.write_text(clean, encoding="utf-8")

    # 最小合法 union/synth 使 coverage 段 PASS
    (handoffs / "u-codex.md").write_text(
        "## CODEX-R1-P2-01\n\n**斷言**: a\n\n**碼證**: c\n\n**來源摘要**: u#abc\n",
        encoding="utf-8",
    )
    (handoffs / "s.md").write_text("mentions CODEX-R1-P2-01\n", encoding="utf-8")

    out1 = work / "out1"
    out2 = work / "out2"
    base_env = {
        **os.environ,
        "REPLAY_REPO_ROOT": str(work),
        "REPLAY_UNION_FILES": "handoffs/u-codex.md",
        "REPLAY_SYNTH_FILE": "handoffs/s.md",
        "REPLAY_RETROFIT_FILES": "handoffs/retro-doc.md",
        "REPLAY_IN_PLACE": "0",
        "REPLAY_MIN_COVERAGE": "0.90",
    }

    r1 = _run_replay({**base_env, "REPLAY_OUT_DIR": str(out1)})
    o1 = (r1.stdout or "") + (r1.stderr or "")
    assert r1.returncode == 0, f"首次 retrofit 應 PASS; out={o1!r}"
    copy1 = (out1 / "retro-doc.md").read_text(encoding="utf-8")
    # strip-ID body-hash 守恆
    assert _canonical_body_hash(copy1) == _canonical_body_hash(clean)
    # 原檔未改（IN_PLACE=0）
    assert target.read_text(encoding="utf-8") == clean

    # 第二次：以已 retrofit 副本為輸入 → 冪等不重加
    target.write_text(copy1, encoding="utf-8")
    r2 = _run_replay({**base_env, "REPLAY_OUT_DIR": str(out2)})
    o2 = (r2.stdout or "") + (r2.stderr or "")
    assert r2.returncode == 0, f"已 retrofit 再跑應冪等 PASS; out={o2!r}"
    copy2 = (out2 / "retro-doc.md").read_text(encoding="utf-8")
    assert copy2 == copy1, "冪等：第二次不得堆疊新 ID heading"

    # 同檔 duplicate canonical heading → 拒
    dup_doc = (
        "## CLAUDE-R1-P2-01\n\n**斷言**: a\n\n## Section A\n\n"
        "## CLAUDE-R1-P2-01\n\n**斷言**: b\n\n## Section B\n\n"
    )
    target.write_text(dup_doc, encoding="utf-8")
    out3 = work / "out3"
    r3 = _run_replay({**base_env, "REPLAY_OUT_DIR": str(out3)})
    o3 = (r3.stdout or "") + (r3.stderr or "")
    assert r3.returncode != 0, f"duplicate ID 應拒; out={o3!r}"
    assert "duplicate" in o3.lower()


def test_oracle4_nested_tail_body_hash(tmp_path: Path) -> None:
    """B5C3（oracle 層）：### Evidence 後 TAIL 改寫 → body-hash 不符 rc≠0。"""
    src = (
        "## GROK-R1-P0-01\n\n"
        "**斷言**: include nested\n\n"
        "**碼證**: code\n\n"
        "**來源摘要**: sources/review.md#fixeddigest1\n\n"
        "### Evidence\n\nORIGINAL_TAIL\n"
    )
    synth = (
        "## GROK-R1-P0-01\n\n"
        "**斷言**: include nested\n\n"
        "**碼證**: code\n\n"
        "**來源摘要**: sources/review.md#fixeddigest1\n\n"
        "### Evidence\n\nMUTATED_TAIL\n"
    )
    session = _session(
        tmp_path,
        name="o4_nested",
        files={"review-grok.md": src},
        synth=synth,
        roster=["grok"],
    )
    result = _run(session)
    out = _combined(result)
    assert result.returncode != 0, f"nested-tail 應 FAIL; out={out!r}"
    assert "body-hash" in out.lower() or "body hash" in out.lower()


def test_retrofit_body_hash_preserved(tmp_path: Path) -> None:
    """replay：構造 retrofit 目標只加 heading、strip-ID hash 不變；coverage 走獨立 fixture。"""
    assert REPLAY_SH.is_file(), f"缺 replay 腳本: {REPLAY_SH}"

    work = tmp_path / "replay_work"
    handoffs = work / "handoffs"
    handoffs.mkdir(parents=True)

    # retrofit 目標（乾淨 h2，無既有 ID）
    doc_a = "# A\n\n## Alpha Section\n\nalpha body\n\n## Beta Section\n\nbeta body\n"
    doc_b = "# B\n\n## Gamma Section\n\ngamma body\n"
    (handoffs / "doc-a.md").write_text(doc_a, encoding="utf-8")
    (handoffs / "doc-b.md").write_text(doc_b, encoding="utf-8")
    pre_hashes = {
        "doc-a.md": _canonical_body_hash(doc_a),
        "doc-b.md": _canonical_body_hash(doc_b),
    }

    # 獨立 coverage 語料（非 retrofit 同源）
    (handoffs / "review-codex.md").write_text(
        "## CODEX-R1-P2-01\n\n**斷言**: a\n\n**碼證**: c\n\n**來源摘要**: r#x\n",
        encoding="utf-8",
    )
    (handoffs / "review-composer.md").write_text(
        "## COMPOSER-R1-P2-01\n\n**斷言**: a\n\n**碼證**: c\n\n**來源摘要**: r#y\n",
        encoding="utf-8",
    )
    (handoffs / "RECONCILE.md").write_text(
        "C1 maps CODEX-R1-P2-01 and COMPOSER-R1-P2-01\n",
        encoding="utf-8",
    )

    out_dir = work / "reconcile_session"
    env = os.environ.copy()
    env["REPLAY_REPO_ROOT"] = str(work)
    env["REPLAY_OUT_DIR"] = str(out_dir)
    env["REPLAY_UNION_FILES"] = (
        "handoffs/review-codex.md,handoffs/review-composer.md"
    )
    env["REPLAY_SYNTH_FILE"] = "handoffs/RECONCILE.md"
    env["REPLAY_RETROFIT_FILES"] = "handoffs/doc-a.md,handoffs/doc-b.md"
    env["REPLAY_IN_PLACE"] = "0"

    result = _run_replay(env)
    out = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0, f"replay 應 PASS; out={out!r}"

    for name, pre in pre_hashes.items():
        post = _canonical_body_hash((out_dir / name).read_text(encoding="utf-8"))
        assert post == pre, f"{name}: retrofit 後 strip-ID body-hash 須不變"
        # 原檔不改
        assert _canonical_body_hash((handoffs / name).read_text(encoding="utf-8")) == pre

    cov_path = out_dir / "coverage.json"
    assert cov_path.is_file(), f"須寫 coverage.json; out={out!r}"
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    for key in (
        "session",
        "union_size",
        "synth_size",
        "coverage",
        "p0p1_missing",
        "missing_ids",
    ):
        assert key in cov, f"coverage.json 缺欄 {key}: {cov}"
    assert cov["union_size"] > 0, "union 空 → vacuous 守衛，不算 PASS"
    assert cov["coverage"] >= 0.90
    assert cov["p0p1_missing"] == []
    assert isinstance(cov["missing_ids"], list)
    assert 0.0 < float(cov["coverage"]) <= 1.0
    # 非循環：union 來源 ≠ synth
    assert cov["synth_source"] not in cov["union_sources"]
