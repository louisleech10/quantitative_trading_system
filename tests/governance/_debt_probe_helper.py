"""P1-6 債務探針薄封裝：subprocess 呼叫真腳本；探針 monkeypatch 本模組常數。

SPEC Task 3.2 改法②：被 patch 的是真正決定行為的路徑常數，不是假 monkeypatch。
B3（Task 1.2／1.3）消費端測試與 mutation 共用此層。
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# 探針可 monkeypatch 的模組常數（真決定呼叫哪支腳本）
COMMITTEE_RUN_TARGET = REPO_ROOT / "scripts" / "committee_run.sh"
CX_RUN_TARGET = REPO_ROOT / "scripts" / "cx_run.sh"
AUDIT_APPEND_TARGET = REPO_ROOT / "scripts" / "audit_append.sh"
DEBT_LEDGER_TARGET = REPO_ROOT / "scripts" / "debt_ledger.sh"
DEBT_CLEAR_TARGET = REPO_ROOT / "scripts" / "debt_clear.sh"
GATE_TARGET = REPO_ROOT / "scripts" / "gate.sh"
GATE_CHECK_TARGET = REPO_ROOT / "scripts" / "gate_check.sh"


def run_cmd(
    script: Path,
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """執行 bash 腳本；rc 直接取，不經 pipe。

    hermetic 契約（P16-B3-FIX 群集 A）：
    - 若傳入 ``env``，以其為完整子程序環境（不繼承 parent 的 ambient 鍵）。
      測試若 ``env.pop("ROUND_ID")``，子程序就真的沒有 ROUND_ID——
      不得再被 parent 的 ``ROUND_ID``（如 committee_run 派工殼）污染。
    - 若未傳 ``env``，才以 ``os.environ.copy()`` 為底。
    - ``extra_env`` 永遠叠在 base 之上（覆寫同名鍵）。
    """
    if env is not None:
        # 完整置換：呼叫端負責帶 PATH/HOME 等必要鍵（_b3_harness 已帶）
        base = dict(env)
    else:
        base = os.environ.copy()
    if extra_env:
        base.update(extra_env)
    return subprocess.run(
        ["bash", str(script), *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        env=base,
    )


def run_committee_run(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(COMMITTEE_RUN_TARGET, *args, env=env, cwd=cwd)


def run_cx_run(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(CX_RUN_TARGET, *args, env=env, cwd=cwd)


def run_audit_append(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(AUDIT_APPEND_TARGET, *args, env=env, cwd=cwd)


def run_debt_ledger(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(DEBT_LEDGER_TARGET, *args, env=env, cwd=cwd)


def run_debt_clear(
    *args: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return run_cmd(DEBT_CLEAR_TARGET, *args, env=env, cwd=cwd)
