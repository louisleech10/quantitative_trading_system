"""P1-6 債務探針薄封裝：subprocess 呼叫真腳本；探針 monkeypatch 本模組常數。

SPEC Task 3.2 改法②：被 patch 的是真正決定行為的路徑常數，不是假 monkeypatch。
B3（Task 1.2／1.3）消費端測試與 mutation 共用此層。
"""

from __future__ import annotations

import contextlib
import json
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

# DOCROT2 Task 3.1／3.2：隔離沙箱須一併複製之共用判定模組與其設定（completeness_check --single 之類別判定、
#   _synth_attr 之 check_category、debt_clear 收案前量測事件皆 fail-closed 依賴之）。
DOCROT2_HELPER_SCRIPTS = (
    "_finding_category.py",
    "governance_verdicts.json",
    "_docrot2_metrics.py",
    "docrot2_metric_contract.json",
)


@contextlib.contextmanager
def legacy_round_open_registry(scripts_dir: Path):
    """模擬 DOCROT2 Task 3.2 之前的寫入端（`committee_round_open.brief_kind` 尚非必填）。

    僅供「上線前 legacy round」之測試：寫入期間暫時自**沙箱副本** audit_events.json 之必填清單移除 brief_kind，
    離開時逐 bytes 還原。🔴 路徑解析到 repo 真實 scripts/ 即 fail-closed（不得改生產登記檔）。
    """
    p = Path(scripts_dir) / "audit_events.json"
    if p.resolve() == (REPO_ROOT / "scripts" / "audit_events.json").resolve():
        raise AssertionError("legacy_round_open_registry 只准用於沙箱副本")
    orig = p.read_bytes()
    d = json.loads(orig.decode("utf-8"))
    req = d["required_fields_per_event"]["committee_round_open"]
    d["required_fields_per_event"]["committee_round_open"] = [x for x in req if x != "brief_kind"]
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        yield
    finally:
        p.write_bytes(orig)


def brief_kind_of(brief: Path) -> str:
    """讀 brief 行首 `brief-kind:` 之值（committee_run.sh 開輪時寫入 committee_round_open.brief_kind 之同一來源）。"""
    for line in Path(brief).read_text(encoding="utf-8").splitlines():
        if line.startswith("brief-kind:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError(f"brief 缺 brief-kind: 行：{brief}")


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
