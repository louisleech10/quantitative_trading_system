"""B1 mutation_red session fixtures — 不改 completeness_check.sh。

`_make_session` 建隔離 session 目錄（sources/ + sources.lock + synth.md）。
`run_completeness` 以 v0 argv 介面呼叫腳本（只傳既有 `*-<family>.md`，
反映 argv 信任邊界；roster/lock/sha 機檢屬後續 Task）。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPLETENESS_SH = REPO_ROOT / "scripts" / "completeness_check.sh"

# 檔名慣例：<name>-<family>.md（family 小寫）
_FAMILY_FILE_RE = re.compile(
    r"^.+-(codex|composer|grok|claude|agy)\.md$",
    re.IGNORECASE,
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _family_from_name(filename: str) -> str:
    """從 `<name>-<family>.md` 抽出 family；否則回 unknown。"""
    m = _FAMILY_FILE_RE.match(filename)
    if not m:
        return "unknown"
    return m.group(1).lower()


def _make_session(
    tmp_path: Path,
    sources: dict[str, str],
    synth: str,
    roster: list[str],
) -> Path:
    """建 session 目錄：sources/ 寫各檔 + sources.lock + synth.md。

    sources 鍵 = 檔名（如 ``review-codex.md``），值 = 正文。
    roster = 預期家族清單（寫入 lock.expected_roster；v0 腳本尚不讀）。
    回傳 session Path。
    """
    session = tmp_path / "session"
    sources_dir = session / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)

    source_entries: list[dict[str, str]] = []
    for name, body in sources.items():
        path = sources_dir / name
        path.write_text(body, encoding="utf-8")
        source_entries.append(
            {
                "realpath": str(path.resolve()),
                "sha256": _sha256_file(path),
                "family": _family_from_name(name),
            }
        )

    source_entries.sort(key=lambda e: e["realpath"])

    lock: dict[str, Any] = {
        "version": 1,
        "session_id": session.name,
        "expected_roster": list(roster),
        "sources": source_entries,
        "freeze_ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "closure_state": "FROZEN",
    }
    (session / "sources.lock").write_text(
        json.dumps(lock, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (session / "synth.md").write_text(synth, encoding="utf-8")
    return session


def list_family_sources(session: Path) -> list[Path]:
    """列出 sources/ 下符合 `*-<family>.md` 的檔（不含 README 等汙染）。"""
    sources_dir = session / "sources"
    if not sources_dir.is_dir():
        return []
    return sorted(
        p
        for p in sources_dir.iterdir()
        if p.is_file() and _FAMILY_FILE_RE.match(p.name)
    )


def run_completeness(session: Path) -> subprocess.CompletedProcess[str]:
    """以 v0 介面跑 completeness_check.sh：synth + 既有 family 來源檔。

    不傳 lock、不傳缺失 roster 槽、不傳非 family 檔——此為 v0 信任邊界，
    使 M1/M7/M8/M9 在 v0 下 rc==0（先紅）。
    """
    synth = session / "synth.md"
    srcs = list_family_sources(session)
    cmd = ["bash", str(COMPLETENESS_SH), str(synth), *[str(s) for s in srcs]]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def completeness_cmd(session: Path) -> list[str]:
    """回傳 run_completeness 使用的命令列（供 receipt）。"""
    synth = session / "synth.md"
    srcs = list_family_sources(session)
    return ["bash", str(COMPLETENESS_SH), str(synth), *[str(s) for s in srcs]]


def git_commit_short() -> str:
    """目前 HEAD short sha；失敗則 unknown。"""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except OSError:
        pass
    return "unknown"


def receipt_entry(
    *,
    name: str,
    session: Path,
    result: subprocess.CompletedProcess[str],
    is_mechanical: bool,
    stdout_limit: int = 2000,
) -> dict[str, Any]:
    """組 red-receipt 單案 schema（TODO Task1.1 / TC26）。"""
    stdout = (result.stdout or "") + (result.stderr or "")
    if len(stdout) > stdout_limit:
        stdout = stdout[:stdout_limit] + "\n...[truncated]..."
    return {
        "name": name,
        "cmd": completeness_cmd(session),
        "fixture_path": str(session),
        "stdout": stdout,
        "observed_rc_v0": result.returncode,
        "expected_predicate": "rc!=0",
        "is_mechanical": is_mechanical,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "commit": git_commit_short(),
    }


# 供測試 import 的共用 finding body 片段
def finding_block(fid: str, assert_text: str = "assert body", code_text: str = "code proof") -> str:
    """合法 finding 區塊（含 **斷言** / **碼證**）。"""
    return f"## {fid}\n\n**斷言**: {assert_text}\n\n**碼證**: {code_text}\n"


@pytest.fixture
def make_session(tmp_path: Path):
    """pytest fixture 包裝 _make_session。"""

    def _factory(
        sources: dict[str, str],
        synth: str,
        roster: list[str] | None = None,
    ) -> Path:
        if roster is None:
            roster = ["codex", "composer", "grok"]
        return _make_session(tmp_path, sources, synth, roster)

    return _factory
