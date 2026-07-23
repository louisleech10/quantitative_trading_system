"""B4 Task 4.1 — self-check advisory + write-once first_draft receipt。

nodeid:
  test_selfcheck_advisory_exit0
  test_first_draft_write_once_tamper_fails
  test_selfcheck_input_error_exit1
  test_deleted_receipt_downstream_still_fails
  test_write_receipt_coverage_dir_exit1
  test_write_once_concurrent_single_success
  test_coverage_json_write_once_tamper_fails
"""
from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _finding(fid: str) -> str:
    d = hashlib.sha256(fid.encode()).hexdigest()[:12]
    return (
        f"## {fid}\n\n"
        f"**斷言**: selfcheck assert\n\n"
        f"**碼證**: path:1\n\n"
        f"**來源摘要**: sources/review.md#{d}\n"
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


def _session_with_gap(tmp_path: Path, *, name: str = "sess_selfcheck") -> Path:
    """兩家來源各 1 ID；synth 只含 1 個 → self-check 應 ADVISORY_MISSING exit0。"""
    session = tmp_path / name
    sources = session / "sources"
    sources.mkdir(parents=True)

    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")
    f_codex = sources / "review-codex.md"
    f_comp = sources / "review-composer.md"
    f_codex.write_text(b_codex, encoding="utf-8")
    f_comp.write_text(b_comp, encoding="utf-8")

    # synth 故意漏 COMPOSER
    (session / "synth.md").write_text(b_codex, encoding="utf-8")

    _write_lock(
        session,
        roster=["codex", "composer"],
        sources=[
            {
                "realpath": str(f_codex.resolve()),
                "sha256": _sha256_bytes(b_codex.encode()),
                "family": "codex",
            },
            {
                "realpath": str(f_comp.resolve()),
                "sha256": _sha256_bytes(b_comp.encode()),
                "family": "composer",
            },
        ],
    )
    return session


def _run(
    session: Path,
    *extra: str,
    env_extra: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("COMPLETENESS_ADVISORY_ONLY", None)
    env.pop("COMPLETENESS_ALLOW_ARGV_SOURCES", None)
    if env_extra:
        env.update(env_extra)
    lock = session / "sources.lock"
    cmd = ["bash", str(COMPLETENESS_SH), "--lock", str(lock), *extra]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_selfcheck_advisory_exit0(tmp_path: Path) -> None:
    """漏 ID → ADVISORY_MISSING + exit 0；寫 first_draft.sha256 + coverage.json。"""
    session = _session_with_gap(tmp_path)
    result = _run(session, "--self-check")
    assert result.returncode == 0, (
        f"self-check 漏 ID 應 exit0 advisory; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "ADVISORY_MISSING" in combined, f"須含 ADVISORY_MISSING: {combined!r}"
    assert "COMPOSER-R1-P2-01" in combined

    receipt = session / "first_draft.sha256"
    cov = session / "coverage.json"
    assert receipt.is_file(), "須寫 first_draft.sha256"
    assert cov.is_file(), "須寫 coverage.json"

    draft_sha = receipt.read_text(encoding="utf-8").strip()
    assert len(draft_sha) == 64
    expected = _sha256_bytes((session / "synth.md").read_bytes())
    assert draft_sha == expected

    data = json.loads(cov.read_text(encoding="utf-8"))
    assert "missing_ids" in data and "draft_sha256" in data and "id_coverage" in data
    assert "COMPOSER-R1-P2-01" in data["missing_ids"]
    assert data["draft_sha256"] == expected
    assert 0.0 <= float(data["id_coverage"]) < 1.0


def test_first_draft_write_once_tamper_fails(tmp_path: Path) -> None:
    """初稿 receipt 已存在 → 再次 --self-check 回寫 → exit 1（write-once）。"""
    session = _session_with_gap(tmp_path)
    first = _run(session, "--self-check")
    assert first.returncode == 0, f"第一次 self-check 應成功: {first.stderr!r}"
    assert (session / "first_draft.sha256").is_file()

    second = _run(session, "--self-check")
    assert second.returncode == 1, (
        f"回寫初稿 receipt 應 FAIL; "
        f"rc={second.returncode} stdout={second.stdout!r} stderr={second.stderr!r}"
    )
    combined = (second.stdout or "") + (second.stderr or "")
    assert (
        "write-once" in combined.lower()
        or "不可回寫" in combined
        or "已存在" in combined
    ), f"須提示 write-once: {combined!r}"


def test_selfcheck_input_error_exit1(tmp_path: Path) -> None:
    """輸入/執行錯誤（lock 壞、synth 缺）→ exit 1（不當 advisory 吞）。"""
    session = _session_with_gap(tmp_path)

    # 壞 lock version
    lock_path = session / "sources.lock"
    bad = json.loads(lock_path.read_text(encoding="utf-8"))
    bad["version"] = 99
    lock_path.write_text(json.dumps(bad) + "\n", encoding="utf-8")
    r1 = _run(session, "--self-check")
    assert r1.returncode == 1, (
        f"壞 lock 應 exit1; rc={r1.returncode} {r1.stdout!r} {r1.stderr!r}"
    )
    assert "ADVISORY_MISSING" not in ((r1.stdout or "") + (r1.stderr or ""))

    # 還原合法 lock，刪 synth
    bad["version"] = 1
    lock_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    (session / "synth.md").unlink()
    r2 = _run(session, "--self-check")
    assert r2.returncode == 1, (
        f"缺 synth 應 exit1; rc={r2.returncode} {r2.stdout!r} {r2.stderr!r}"
    )
    combined = (r2.stdout or "") + (r2.stderr or "")
    assert "ADVISORY_MISSING" not in combined
    assert "FAIL" in combined or "不存在" in combined or "輸入" in combined


def test_deleted_receipt_downstream_still_fails(tmp_path: Path) -> None:
    """BF6 mutation-style：下游因**真實內容不完整** FAIL，非只因 receipt 缺。

    可證偽：
    - 對照：補齊 synth 漏 ID 後無 receipt → 須 PASS（若壞下游只檢 receipt 存在→此步紅）
    - 主斷言：漏 ID 內容 + 無 receipt → FAIL 且訊息含 missing ID（非 first_draft）
    """
    session = _session_with_gap(tmp_path, name="sess_del_receipt")
    b_codex = _finding("CODEX-R1-P2-01")
    b_comp = _finding("COMPOSER-R1-P2-01")

    sc = _run(session, "--self-check")
    assert sc.returncode == 0
    assert (session / "first_draft.sha256").is_file()

    # 刪 receipt + coverage（下游不得依賴自檢產物）
    (session / "first_draft.sha256").unlink()
    cov = session / "coverage.json"
    if cov.is_file():
        cov.unlink()
    assert not (session / "first_draft.sha256").exists()

    # --- 主路徑：內容仍缺 COMPOSER → 獨立出口 FAIL，且因內容 ---
    downstream = _run(session)  # 正式 --lock，無 --self-check
    assert downstream.returncode != 0, (
        f"獨立出口對漏 ID 應 FAIL; "
        f"rc={downstream.returncode} stdout={downstream.stdout!r} stderr={downstream.stderr!r}"
    )
    combined = (downstream.stdout or "") + (downstream.stderr or "")
    # 內容證據：須點名漏掉的 ID（非 tautological returncode-only）
    assert "COMPOSER-R1-P2-01" in combined, (
        f"FAIL 須因真實漏 ID（COMPOSER-R1-P2-01），非僅 receipt 缺: {combined!r}"
    )
    assert "ADVISORY_MISSING" not in combined
    # 不得把失敗歸因於 receipt 產物缺失
    assert "first_draft" not in combined.lower(), (
        f"下游不得只因 first_draft 缺而 FAIL: {combined!r}"
    )

    # --- 對照（可證偽反例）: 補齊內容、仍無 receipt → 必須 PASS ---
    # 若下游被改成「只檢 receipt 存在」→ 此步會紅，測試本身可證偽。
    (session / "synth.md").write_text(b_codex + "\n" + b_comp, encoding="utf-8")
    control = _run(session)
    assert control.returncode == 0, (
        f"完整內容且無 receipt 應 PASS（證 FAIL 非因 receipt 缺）; "
        f"rc={control.returncode} stdout={control.stdout!r} stderr={control.stderr!r}"
    )
    assert not (session / "first_draft.sha256").exists()


def test_write_receipt_coverage_dir_exit1(tmp_path: Path) -> None:
    """BF1: coverage.json 為目錄 → 寫入失敗 exit1（不吞成 advisory rc0）。"""
    session = _session_with_gap(tmp_path, name="sess_cov_dir")
    # 預置 coverage.json 為目錄，迫使寫入失敗
    (session / "coverage.json").mkdir()
    result = _run(session, "--self-check")
    assert result.returncode == 1, (
        f"coverage 為目錄應 exit1; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "ADVISORY_MISSING" not in combined
    assert "FAIL" in combined or "寫入" in combined or "COVERAGE" in combined


def test_write_once_concurrent_single_success(tmp_path: Path) -> None:
    """BF1: 同 session 並發 self-check → 僅 1 次成功建 receipt（O_EXCL）。"""
    session = _session_with_gap(tmp_path, name="sess_race")
    n = 8

    def _one(_: int) -> int:
        return _run(session, "--self-check").returncode

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        rcs = list(pool.map(_one, range(n)))

    n_ok = sum(1 for r in rcs if r == 0)
    n_fail = sum(1 for r in rcs if r != 0)
    assert n_ok == 1, (
        f"並發 write-once 應恰 1 次成功; rc_counts ok={n_ok} fail={n_fail} all={rcs}"
    )
    assert n_fail == n - 1
    assert (session / "first_draft.sha256").is_file()
    assert (session / "coverage.json").is_file()
    # receipt 內容單一合法 sha
    draft = (session / "first_draft.sha256").read_text(encoding="utf-8").strip()
    assert len(draft) == 64
    assert draft == _sha256_bytes((session / "synth.md").read_bytes())


def test_coverage_json_write_once_tamper_fails(tmp_path: Path) -> None:
    """New-08: pre-existing coverage.json 不得覆寫；self-check exit1；原內容不變。

    可證偽反例：
    - 還原 coverage 為 temp+os.replace 覆寫 → 本測 rc 變 0 且 content 被改 → 紅
    - 若只擋目錄不擋 regular file → 本測紅
    """
    session = _session_with_gap(tmp_path, name="sess_cov_once")
    cov = session / "coverage.json"
    tampered = {
        "missing_ids": ["TAMPERED-ID-99"],
        "draft_sha256": "0" * 64,
        "id_coverage": 0.123,
        "marker": "pre-existing-must-not-overwrite",
    }
    original_text = json.dumps(tampered, indent=2, ensure_ascii=False) + "\n"
    cov.write_text(original_text, encoding="utf-8")
    assert not (session / "first_draft.sha256").exists()

    result = _run(session, "--self-check")
    assert result.returncode == 1, (
        f"pre-existing coverage.json 應 write-once FAIL; "
        f"rc={result.returncode} stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    combined = (result.stdout or "") + (result.stderr or "")
    assert "ADVISORY_MISSING" not in combined
    assert (
        "write-once" in combined.lower()
        or "不可回寫" in combined
        or "已存在" in combined
        or "COVERAGE" in combined
    ), f"須提示 coverage write-once: {combined!r}"

    # 原檔不得被覆寫
    after = cov.read_text(encoding="utf-8")
    assert after == original_text, (
        f"pre-existing coverage.json 不得被覆寫; before={original_text!r} after={after!r}"
    )
    data = json.loads(after)
    assert data.get("marker") == "pre-existing-must-not-overwrite"
    assert data.get("missing_ids") == ["TAMPERED-ID-99"]
    # 半寫不得留下孤立 receipt（若先 O_EXCL receipt 再撞 coverage 須撤銷）
    assert not (session / "first_draft.sha256").exists(), (
        "coverage write-once 失敗後不得殘留 first_draft.sha256"
    )
