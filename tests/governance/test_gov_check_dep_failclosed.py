"""CODEX-R2-P1-01：`gov_check.sh` 對格式檢查鏈的依賴必須 fail-closed。

第一版寫成 `if [ -f scripts/doc_format_precheck.sh ] && ...`，檔案不在就**靜默跳過
整段 1b 且 rc=0**。pre-push hook 只呼叫 gov_check，所以刪掉那支腳本就能讓格式防線
假綠——是真的 fail-open，不是理論風險。

codex 在 R2 提出此條時明講「缺檔 runtime probe 受沙箱阻擋，未宣稱已驗」。本檔補上
那個它跑不了的實測：在**隔離副本**上真的把依賴移走，確認 rc≠0 且訊息具名。

紀律：一律操作 tmp 隔離副本，絕不變異 repo 內 scripts/*.sh。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_DEPS = (
    "doc_format_precheck.sh",
    "template_check.sh",
    "brief_conformance_check.sh",
)


def _iso_repo(tmp_path: Path) -> Path:
    """隔離 repo：gov_check 需要 scripts/ + git 倉庫（它用 merge-base 決定掃描範圍）。"""
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "docs").mkdir()
    for src in (REPO_ROOT / "scripts").glob("*.sh"):
        dst = root / "scripts" / src.name
        shutil.copy2(src, dst)
        dst.chmod(0o755)
    for extra in ("template_lifecycle_legacy.txt", "govflow_lifecycle.json"):
        s = REPO_ROOT / "scripts" / extra
        if s.is_file():
            shutil.copy2(s, root / "scripts" / extra)
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    for cmd in (
        ["git", "init", "-q"],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init"],
    ):
        subprocess.run(cmd, cwd=root, env=env, capture_output=True, check=False)
    return root


def _run_fast(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "scripts/gov_check.sh", "--fast"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=180,
    )


def test_gov_check_fast_green_with_all_deps(tmp_path: Path) -> None:
    """基線：依賴齊全時 --fast 通過。沒有這條，下面的紅就可能是別的原因造成的。"""
    root = _iso_repo(tmp_path)
    r = _run_fast(root)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.parametrize("dep", _DEPS)
def test_gov_check_fails_closed_when_dep_missing(tmp_path: Path, dep: str) -> None:
    """移走任一依賴 → rc≠0，且訊息具名指出缺哪支。"""
    root = _iso_repo(tmp_path)
    target = root / "scripts" / dep
    assert target.is_file(), f"隔離副本缺 {dep}，測試前提不成立"
    target.unlink()

    r = _run_fast(root)
    assert r.returncode != 0, (
        f"移走 {dep} 後 gov_check --fast 仍回 0 ＝ fail-open（格式防線可被靜默關掉）\n"
        + r.stdout
        + r.stderr
    )
    assert dep in (r.stdout + r.stderr), f"訊息未具名指出缺 {dep}，使用者無從診斷"


# ───────── CODEX-R3-P1-01：settings.json 掛載檢查必須 fail-closed ─────────

_HEALTH = REPO_ROOT / "scripts" / "verify_hooks_health.sh"

_GOOD_SETTINGS = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {"type": "command", "command": "bash scripts/doc_format_precheck.sh"}
                ],
            }
        ]
    }
}


def _health_repo(tmp_path: Path, settings: dict | None) -> Path:
    """最小 repo：只放 health gate 需要的東西，settings 由參數決定。"""
    root = tmp_path / "hrepo"
    (root / "scripts" / "git_hooks").mkdir(parents=True)
    for name in (
        "verify_hooks_health.sh",
        "verify_pretooluse.sh",
        "verification_claim_check.py",
        "doc_format_precheck.sh",
        "template_check.sh",
        "brief_conformance_check.sh",
    ):
        src = REPO_ROOT / "scripts" / name
        if src.is_file():
            dst = root / "scripts" / name
            shutil.copy2(src, dst)
            dst.chmod(0o755)
    for hook in (REPO_ROOT / "scripts" / "git_hooks").iterdir():
        if hook.is_file():
            dst = root / "scripts" / "git_hooks" / hook.name
            shutil.copy2(hook, dst)
            dst.chmod(0o755)
    venv_bin = root / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python").symlink_to(shutil.which("python3") or "/usr/bin/python3")
    if settings is not None:
        (root / ".claude").mkdir()
        (root / ".claude" / "settings.json").write_text(
            json.dumps(settings, ensure_ascii=False), encoding="utf-8"
        )
    # verify_hooks_health.sh 前置要求「在 git repo 內」，否則會先以「不在 git repo」FAIL，
    # 使後面的掛載檢查根本沒跑到 —— 那樣測出來的紅是假紅（紅在別的原因）。
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    subprocess.run(["git", "init", "-q"], cwd=root, env=env, capture_output=True, check=False)
    # verify_hooks_health.sh 對「hooks 未安裝」是 WARN + **exit 0** 並提早返回
    # （設計如此：未安裝 ≠ 工具壞掉）。不設 core.hooksPath 的話，腳本在到達掛載檢查前
    # 就已 exit 0 ⇒ 測試會綠得毫無意義。必須先讓它進入「已安裝」路徑。
    subprocess.run(
        ["git", "config", "core.hooksPath", "scripts/git_hooks"],
        cwd=root,
        env=env,
        capture_output=True,
        check=False,
    )
    return root


def _run_health(root: Path) -> subprocess.CompletedProcess[str]:
    """跑**隔離副本內**的腳本，不是 repo 內的真腳本。

    第一版寫成 `bash str(_HEALTH)`（repo 內的真檔）。因為該腳本會自己
    `cd "$(git rev-parse --show-toplevel)"`，非變異測試照樣通過，
    但變異測試改的是副本 ⇒ **變異對實際執行的檔完全無效**，探針在測空氣。
    """
    local = root / "scripts" / "verify_hooks_health.sh"
    assert local.is_file(), "隔離副本缺 verify_hooks_health.sh"
    return subprocess.run(
        ["bash", str(local)], cwd=root, capture_output=True, text=True, timeout=120
    )


def test_health_green_with_correct_mount(tmp_path: Path) -> None:
    """基線：settings 正確掛載時通過。沒有這條，下面的紅可能紅在別的原因。"""
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    r = _run_health(_health_repo(tmp_path, _GOOD_SETTINGS))
    assert r.returncode == 0, r.stdout + r.stderr


def test_health_fails_when_settings_missing(tmp_path: Path) -> None:
    """缺 settings.json → FAIL（第一版會靜默通過＝刪檔即可讓 health 回綠）。"""
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    r = _run_health(_health_repo(tmp_path, None))
    assert r.returncode != 0, "缺 settings.json 仍回 0 ＝ fail-open\n" + r.stdout + r.stderr
    assert "settings.json" in (r.stdout + r.stderr)


def test_health_fails_when_mounted_under_wrong_matcher(tmp_path: Path) -> None:
    """掛在非 `Edit|Write` 的 matcher 下 → FAIL。

    第一版只查 command 字串，故掛到 `Bash`（對寫檔永不觸發）也判健康 ——
    腳本在、設定在、但**永遠不會跑**，是最難察覺的一種 fail-open。
    """
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    bad = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "bash scripts/doc_format_precheck.sh",
                        }
                    ],
                }
            ]
        }
    }
    r = _run_health(_health_repo(tmp_path, bad))
    assert r.returncode != 0, "掛錯 matcher 仍回 0 ＝ fail-open\n" + r.stdout + r.stderr


def test_health_fails_when_matcher_only_partially_matches(tmp_path: Path) -> None:
    """matcher 只有 `Edit` 沒有 `Write` → FAIL（Write 寫出的檔會漏檢）。"""
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    partial = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "bash scripts/doc_format_precheck.sh",
                        }
                    ],
                }
            ]
        }
    }
    r = _run_health(_health_repo(tmp_path, partial))
    assert r.returncode != 0, "matcher 只含 Edit 仍回 0\n" + r.stdout + r.stderr


def test_health_fails_when_command_missing(tmp_path: Path) -> None:
    """matcher 對但沒掛 checker → FAIL。"""
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    nocmd = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Edit|Write",
                    "hooks": [{"type": "command", "command": "bash scripts/ts_stamp.sh OUT"}],
                }
            ]
        }
    }
    r = _run_health(_health_repo(tmp_path, nocmd))
    assert r.returncode != 0, "未掛 checker 仍回 0\n" + r.stdout + r.stderr


def test_mutation_restore_conditional_mount_check_turns_red(tmp_path: Path) -> None:
    """把掛載檢查改回「檔在才驗」→ 缺 settings 時又變 rc=0。

    上面四條的可證偽性證明：隔離出「掛載檢查 fail-closed」這件事本身。
    """
    if not shutil.which("jq"):
        pytest.skip("jq 不在 PATH")
    root = _health_repo(tmp_path, None)
    hp = root / "scripts" / "verify_hooks_health.sh"
    text = hp.read_text(encoding="utf-8")
    # ⚠️ 不能只把條件改成 `if false`：那樣控制流會落到後面的 `elif jq …` 分支，
    #    jq 讀不到不存在的檔照樣 FAIL ⇒ 測試紅，但**紅的原因不是我要隔離的那個 guard**。
    #    正確變異＝保留分支命中、把**該分支的動作**掏空（重現第一版「缺檔即靜默通過」）。
    old = (
        "if [ ! -f .claude/settings.json ]; then\n"
        '  echo "HEALTH FAIL: 缺 .claude/settings.json（無法確認產出端檢查已上線）→ fail-closed" >&2\n'
        "  fail=1\n"
    )
    assert old in text, "掛載檢查錨點不存在"
    hp.write_text(
        text.replace(
            old, "if [ ! -f .claude/settings.json ]; then\n  :  # MUTATED: 缺 settings 不再 FAIL\n", 1
        ),
        encoding="utf-8",
    )
    r = _run_health(root)
    assert r.returncode == 0, (
        "變異後缺 settings 應回 rc=0（重現 fail-open）；若仍非 0，"
        "表示上面四條紅的原因不是掛載檢查\n" + r.stdout + r.stderr
    )


def test_mutation_restore_conditional_skip_turns_red(tmp_path: Path) -> None:
    """把 fail-closed 改回「缺檔就跳過」→ 缺檔時又變成 rc=0。

    這是上面那組測試的可證偽性證明：若不做此變異就無法讓它們轉綠，
    代表它們沒有在測「fail-closed」這件事本身。
    """
    root = _iso_repo(tmp_path)
    gc = root / "scripts" / "gov_check.sh"
    text = gc.read_text(encoding="utf-8")
    old = "for _dep in scripts/doc_format_precheck.sh scripts/template_check.sh scripts/brief_conformance_check.sh; do"
    assert old in text, "fail-closed 迴圈錨點不存在"
    # 變異＝把依賴檢查迴圈整段換成永不觸發的形式（重現第一版的靜默跳過）
    mutated = text.replace(old, "for _dep in ; do  # MUTATED: 依賴檢查失效", 1)
    assert mutated != text
    gc.write_text(mutated, encoding="utf-8")

    (root / "scripts" / "doc_format_precheck.sh").unlink()
    r = _run_fast(root)
    assert r.returncode == 0, (
        "變異後缺檔應回 rc=0（重現 fail-open）；若仍非 0，"
        "表示上面的 fail-closed 測試紅的原因不是我以為的那個\n" + r.stdout + r.stderr
    )
