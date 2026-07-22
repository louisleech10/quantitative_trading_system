"""B1 — completeness 變異先紅（M1-M9）+ M3 守衛 + M4b OOS。

鐵律：
- 不改 scripts/completeness_check.sh
- 禁 pytest.mark.xfail
- 8 先紅案：v0 rc==0 → assert rc!=0 失敗=紅
- M3 守衛：v0 STRICT 已 rc=1 → assert rc!=0 綠
- M4b：out-of-scope，不 assert 機械抓到
"""
from __future__ import annotations

import json
from pathlib import Path

from tests.governance.mutation_red.conftest import (
    _make_session,
    _sha256_file,
    completeness_cmd,
    finding_block,
    receipt_entry,
    run_completeness,
)

# 標準三家 roster
ROSTER3 = ["codex", "composer", "grok"]


def _write_receipt(session: Path, entry: dict) -> Path:
    """寫/附加 mutation-red.receipt（JSONL，測試期落 session 下）。"""
    path = session / "mutation-red.receipt"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


# ---------------------------------------------------------------------------
# 8 先紅案：v0 漏抓 → assert rc!=0 亮紅
# ---------------------------------------------------------------------------


def test_m1_missing_source(tmp_path: Path) -> None:
    """M1 少來源：roster 3 家，sources 只放 2 檔 → v0 信任 argv → rc==0。"""
    sources = {
        "review-codex.md": finding_block("CODEX-R1-P0-01"),
        "review-composer.md": finding_block("COMPOSER-R1-P0-01"),
        # grok 缺席
    }
    synth = (
        finding_block("CODEX-R1-P0-01")
        + finding_block("COMPOSER-R1-P0-01")
        + finding_block("GROK-R1-P0-01")
    )
    session = _make_session(tmp_path, sources, synth, ROSTER3)
    result = run_completeness(session)
    entry = receipt_entry(
        name="M1",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M1 應被機械擋（少來源/roster 缺席）"


def test_m2_body_tamper(tmp_path: Path) -> None:
    """M2 body 竄改：同 ID，synth 正文≠來源 → v0 只比 ID → rc==0。"""
    sources = {
        "review-grok.md": finding_block(
            "GROK-R1-P0-01",
            assert_text="ORIGINAL_ASSERT_BODY",
            code_text="src-code",
        ),
    }
    synth = finding_block(
        "GROK-R1-P0-01",
        assert_text="TAMPERED_ASSERT_BODY",
        code_text="src-code",
    )
    session = _make_session(tmp_path, sources, synth, ["grok"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M2",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M2 應被機械擋（body 竄改）"


def test_m4a_empty_shell(tmp_path: Path) -> None:
    """M4a 空殼 heading：有 ## ID 但無 **斷言** → v0 只比 ID → rc==0。"""
    sources = {
        "review-grok.md": "## GROK-R1-P0-01\n\n(empty shell — no assert/code fields)\n",
    }
    synth = "## GROK-R1-P0-01\n\n(empty shell in synth too)\n"
    session = _make_session(tmp_path, sources, synth, ["grok"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M4a",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M4a 應被機械擋（空殼 heading）"


def test_m5_malformed_id(tmp_path: Path) -> None:
    """M5 缺欄 ID：## GROK-01（缺 ROUND/SEVERITY）→ v0 仍當合法 ID → rc==0。"""
    sources = {
        "review-grok.md": finding_block("GROK-01"),
    }
    synth = finding_block("GROK-01")
    session = _make_session(tmp_path, sources, synth, ["grok"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M5",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M5 應被機械擋（malformed ID 缺 ROUND/SEVERITY）"


def test_m6_cross_dup(tmp_path: Path) -> None:
    """M6 跨源 dup：兩來源同 ## CODEX-R1-P0-01 → v0 不查跨源 → rc==0。"""
    sources = {
        "a-codex.md": finding_block("CODEX-R1-P0-01", assert_text="from-a"),
        "b-composer.md": finding_block("CODEX-R1-P0-01", assert_text="from-b"),
    }
    synth = finding_block("CODEX-R1-P0-01")
    session = _make_session(tmp_path, sources, synth, ["codex", "composer"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M6",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M6 應被機械擋（跨源 duplicate ID）"


def test_m7_late_file(tmp_path: Path) -> None:
    """M7 late 檔：freeze 後改 source 內容（sha≠lock）但 ID 不變 → v0 不查 sha → rc==0。"""
    sources = {
        "review-grok.md": finding_block(
            "GROK-R1-P0-01",
            assert_text="frozen-body",
        ),
    }
    synth = finding_block("GROK-R1-P0-01", assert_text="frozen-body")
    session = _make_session(tmp_path, sources, synth, ["grok"])

    # freeze 後竄改：改 body，ID 仍在
    late_path = session / "sources" / "review-grok.md"
    late_path.write_text(
        finding_block("GROK-R1-P0-01", assert_text="LATE_TAMPER_AFTER_FREEZE"),
        encoding="utf-8",
    )
    # lock 仍記舊 sha（不更新）
    lock_path = session / "sources.lock"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    old_sha = lock["sources"][0]["sha256"]
    new_sha = _sha256_file(late_path)
    assert old_sha != new_sha, "fixture 須確保 late 改檔後 sha 變化"

    result = run_completeness(session)
    entry = receipt_entry(
        name="M7",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M7 應被機械擋（late 檔 sha≠lock）"


def test_m8_cross_round(tmp_path: Path) -> None:
    """M8 跨 round：sources 混入他 round 舊檔 → v0 全傳且 ID 在 synth → rc==0。"""
    sources = {
        "review-codex.md": finding_block("CODEX-R1-P0-01"),
        # 他 round 舊檔（檔名仍符合 family 慣例，會被 v0 harness 傳入）
        "legacy-r0-codex.md": finding_block("CODEX-R0-P0-99", assert_text="old-round"),
    }
    synth = (
        finding_block("CODEX-R1-P0-01")
        + finding_block("CODEX-R0-P0-99", assert_text="old-round")
    )
    session = _make_session(tmp_path, sources, synth, ["codex"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M8",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M8 應被機械擋（跨 round 舊檔混入）"


def test_m9_readme_pollution(tmp_path: Path) -> None:
    """M9 README 汙染：sources 放 README.md → v0 只傳 family 檔 → 汙染不可見 → rc==0。"""
    sources = {
        "review-grok.md": finding_block("GROK-R1-P0-01"),
        "README.md": "# pollution\n\nNot a family source file.\n",
    }
    synth = finding_block("GROK-R1-P0-01")
    session = _make_session(tmp_path, sources, synth, ["grok"])
    # 確認 README 在 sources 但不會進 v0 argv
    assert (session / "sources" / "README.md").is_file()
    cmd = completeness_cmd(session)
    assert not any(p.endswith("README.md") for p in cmd), "v0 harness 不傳 README"

    result = run_completeness(session)
    entry = receipt_entry(
        name="M9",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M9 應被機械擋（README/非 family 檔汙染）"


# ---------------------------------------------------------------------------
# M3 守衛：v0 已綠（STRICT vacuous FAIL）
# ---------------------------------------------------------------------------


def test_m3_prose_no_id(tmp_path: Path) -> None:
    """M3 純 prose 無 ## ID：v0 STRICT=1 已 rc=1 → 守衛綠（非先紅案）。"""
    sources = {
        "review-codex.md": (
            "This is pure prose review content without any canonical "
            "heading IDs. Findings are buried in bullet lists.\n"
        ),
    }
    synth = "## CODEX-R1-P0-01\n\nmerged somehow\n"
    session = _make_session(tmp_path, sources, synth, ["codex"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M3",
        session=session,
        result=result,
        is_mechanical=True,
    )
    _write_receipt(session, entry)
    assert result.returncode != 0, "M3 守衛：純 prose 無 ID 須持續被擋（不退化 vacuous）"


# ---------------------------------------------------------------------------
# M4b OOS：蓄意假 body + digest 對 — 不 assert 機械抓到
# ---------------------------------------------------------------------------


def test_m4b_fake_body_out_of_scope(tmp_path: Path) -> None:
    """M4b 假 body 但 sha/digest 對齊：out-of-scope，只記 receipt，不 assert 抓到。

    蓄意偽造不在機械門檻；語意/Oracle④ 後續處理。
    """
    fake_body = finding_block(
        "GROK-R1-P0-01",
        assert_text="INTENTIONALLY_FAKE_BUT_DIGEST_ALIGNED",
        code_text="fake-code",
    )
    sources = {"review-grok.md": fake_body}
    # synth 同文 → digest 對；機械 ID 層亦 PASS
    synth = fake_body
    session = _make_session(tmp_path, sources, synth, ["grok"])
    result = run_completeness(session)
    entry = receipt_entry(
        name="M4b",
        session=session,
        result=result,
        is_mechanical=False,
    )
    # OOS：expected_predicate 仍記 rc!=0 契約欄位，但不 assert
    entry["note"] = "out-of-scope: intentional fake body with matching digest; not mechanical gate"
    _write_receipt(session, entry)
    # 刻意不 assert result.returncode — OOS 不宣稱機械抓到
    assert entry["is_mechanical"] is False
    assert entry["name"] == "M4b"
