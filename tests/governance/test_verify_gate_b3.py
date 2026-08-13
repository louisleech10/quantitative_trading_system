"""VERIFY_GATE Phase 3 (B3) — PreToolUse / git hooks / CI / health 測試。"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
from tests.governance._pyenv import link_python_env  # CI 無 venv 相容
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
from tests.governance._pyenv import PYTHON  # CI 無 venv → fallback sys.executable
PRETOOLUSE = REPO_ROOT / "scripts" / "verify_pretooluse.sh"
INSTALL_HOOKS = REPO_ROOT / "scripts" / "install_verify_hooks.sh"
HEALTH = REPO_ROOT / "scripts" / "verify_hooks_health.sh"
PREFLIGHT = REPO_ROOT / "scripts" / "agent_preflight.sh"
CLAIM_CHECK = REPO_ROOT / "scripts" / "verification_claim_check.py"
VERIFY_TASK_PROVENANCE = REPO_ROOT / "scripts" / "verify_task_provenance.py"

RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
PENDING_LEDGER_ENV = "VERIFY_GATE_PENDING_LEDGER"


@pytest.fixture(autouse=True)
def isolated_b3_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """B3 測試用臨時 receipt/audit 路徑，避免污染真實目錄。"""
    receipts_dir = tmp_path / "run_receipts"
    audit_log = tmp_path / "gate" / "verify_audit.log"
    pending_ledger = tmp_path / "pending_verifications.jsonl"
    monkeypatch.setenv(RECEIPTS_DIR_ENV, str(receipts_dir))
    monkeypatch.setenv(AUDIT_LOG_ENV, str(audit_log))
    monkeypatch.setenv(PENDING_LEDGER_ENV, str(pending_ledger))


@pytest.fixture(scope="module", autouse=True)
def guard_real_repo_state() -> None:
    """跑測試前後真實 audit.log / git config 不得變化（module 級，降並發 flake）。"""
    audit_path = REPO_ROOT / ".claude" / "gate" / "audit.log"
    verify_audit = REPO_ROOT / ".claude" / "gate" / "verify_audit.log"
    hooks_before = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    audit_before = audit_path.read_bytes() if audit_path.is_file() else None
    verify_audit_before = verify_audit.read_bytes() if verify_audit.is_file() else None
    yield
    hooks_after = subprocess.run(
        ["git", "config", "--get", "core.hooksPath"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    assert hooks_after == hooks_before, "core.hooksPath changed on real repo"
    if audit_before is None:
        assert not audit_path.is_file(), "audit.log created on real repo"
    else:
        assert audit_path.read_bytes() == audit_before, "audit.log mutated"
    if verify_audit_before is None:
        assert not verify_audit.is_file() or verify_audit.read_bytes() == b"", "verify_audit.log polluted"
    else:
        assert verify_audit.read_bytes() == verify_audit_before, "verify_audit.log mutated"


def _receipts_dir() -> Path:
    override = os.environ.get(RECEIPTS_DIR_ENV)
    return Path(override) if override else REPO_ROOT / "handoffs" / "run_receipts"


def _audit_log() -> Path:
    override = os.environ.get(AUDIT_LOG_ENV)
    return Path(override) if override else REPO_ROOT / ".claude" / "gate" / "verify_audit.log"


def _create_manual_receipt(claim_id: str) -> str:
    """手動建立 receipt + 審計事件（測試隔離路徑）。"""
    receipts_dir = _receipts_dir()
    receipts_dir.mkdir(parents=True, exist_ok=True)
    receipt_id = f"20990101T000000Z-{claim_id}"
    json_path = receipts_dir / f"{receipt_id}.json"
    log_path = receipts_dir / f"{receipt_id}.log"
    log_path.write_bytes(b"ok\n")
    log_sha256 = hashlib.sha256(log_path.read_bytes()).hexdigest()
    receipt = {
        "schema_version": "1.0",
        "receipt_id": receipt_id,
        "claim_id": claim_id,
        "command": [str(PYTHON), "-c", "print('1 passed')"],
        "command_sha256": "test",
        "cwd": str(REPO_ROOT),
        "git_head": "test",
        "tree_dirty": False,
        "started_at": "2099-01-01T00:00:00Z",
        "ended_at": "2099-01-01T00:00:01Z",
        "duration_seconds": 0.1,
        "exit_code": 0,
        "runtime_class": "helper_smoke",
        "requested_class": None,
        "pytest_summary": "1 passed",
        "selected_node_ids": [],
        "markers": [],
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "stdout_sha256": "test",
        "stderr_sha256": "test",
        "log_sha256": log_sha256,
        "log_path": str(log_path),
        "tail_excerpt": ["ok"],
    }
    json_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    audit_log = _audit_log()
    audit_log.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "receipt",
        "receipt_id": receipt_id,
        "emitter": "run_with_receipt.py",
        "command_sha256": receipt["command_sha256"],
        "receipt_sha256": hashlib.sha256(json_path.read_bytes()).hexdigest(),
        "log_sha256": log_sha256,
        "git_head": "test",
        "exit_code": 0,
        "runtime_class": "helper_smoke",
        "started_at": receipt["started_at"],
        "ended_at": receipt["ended_at"],
        "ts": receipt["ended_at"],
    }
    with audit_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    return receipt_id


def _run_pretooluse(payload: dict) -> int:
    proc = subprocess.run(
        ["bash", str(PRETOOLUSE)],
        input=json.dumps(payload),
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    return proc.returncode


def _run_health(cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(HEALTH)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _setup_temp_git_repo(tmp_path: Path) -> Path:
    """建立含 repo-tracked hooks 的臨時 git repo（不動真實 repo hooksPath）。"""
    repo = tmp_path / "mini_repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "b3@test.local"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "B3 Test"], cwd=repo, check=True)

    scripts = repo / "scripts"
    scripts.mkdir()
    shutil.copytree(REPO_ROOT / "scripts" / "git_hooks", scripts / "git_hooks")
    for hook in (scripts / "git_hooks").iterdir():
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    for name in (
        "verification_claim_check.py",
        "install_verify_hooks.sh",
        "verify_hooks_health.sh",
        "verify_pretooluse.sh",
        # GOV-DOC-CHECK-AT-WRITE（2026-08-02，CODEX-R2-P1-01）：治理文件格式檢查鏈
        # 已納入 verify_hooks_health.sh 的 health gate（缺任一支＝格式防線有洞）。
        # mini_repo 少了它們，health 會如實報 FAIL —— 那是**檢查正確**，不是測試該放寬，
        # 故補進 fixture 而非弱化檢查。
        "doc_format_precheck.sh",
        "template_check.sh",
        "brief_conformance_check.sh",
    ):
        (scripts / name).symlink_to(REPO_ROOT / "scripts" / name)
    link_python_env(repo)

    # CODEX-R3-P1-01：health gate 現在**強制**驗證 `.claude/settings.json` 於 PostToolUse
    # 的 `Edit|Write` matcher 下掛了 doc_format_precheck（缺設定檔／掛錯 matcher 皆 FAIL）。
    # 舊 fixture 沒有這個檔 ⇒ 新契約完全沒被測到（codex 指出「補 symlink 正確但不完整」）。
    # 這裡放**最小且合法**的設定，讓契約真的走過一次；不是為了讓測試變綠而放寬檢查。
    settings_dir = repo / ".claude"
    settings_dir.mkdir(exist_ok=True)
    (settings_dir / "settings.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Edit|Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "bash scripts/doc_format_precheck.sh",
                                }
                            ],
                        }
                    ]
                }
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    (repo / "README.md").write_text("# temp\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return repo


# --- Task 3.1 PreToolUse ---


def test_pretooluse_blocks_operational_fake_claim() -> None:
  """Edit HANDOFF 加 operational 假 claim 無 backing → exit 2。"""
  payload = {
      "tool_name": "Edit",
      "tool_input": {
          "file_path": "HANDOFF.md",
          "new_string": "## 正在做\n\n- align 已驗真紅\n",
      },
  }
  assert _run_pretooluse(payload) == 2


def test_pretooluse_allows_ref_citation() -> None:
  """Edit HANDOFF 加 REF 引用（有 backing）→ exit 0。"""
  receipt_id = _create_manual_receipt("b3-ref-cite")
  payload = {
      "tool_name": "Edit",
      "tool_input": {
          "file_path": "HANDOFF.md",
          "new_string": f"- 進度見 REF:{receipt_id}\n",
      },
  }
  assert _run_pretooluse(payload) == 0


def test_pretooluse_ignores_non_handoff_edit() -> None:
  """Edit momentum/foo.py → 不觸發。"""
  payload = {
      "tool_name": "Edit",
      "tool_input": {
          "file_path": "momentum/foo.py",
          "new_string": "已驗真紅\n",
      },
  }
  assert _run_pretooluse(payload) == 0


# --- Task 3.2 git hooks ---


def test_git_hook_rejects_partial_stage_fake_claim(tmp_path: Path) -> None:
  """partial-stage：staged 假 claim + working tree 乾淨 → commit 仍須被拒。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  handoff = repo / "HANDOFF.md"
  handoff.write_text("## 正在做\n\n- align 已驗真紅\n", encoding="utf-8")
  subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
  handoff.write_text("## 正在做\n\n- clean note\n", encoding="utf-8")
  proc = subprocess.run(
      ["git", "commit", "-m", "docs: update handoff"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode != 0


def test_git_hook_allows_code_only_commit(tmp_path: Path) -> None:
  """只 staged 非 scannable 檔（foo.py）→ commit 須通過。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  (repo / "foo.py").write_text("x = 1\n", encoding="utf-8")
  subprocess.run(["git", "add", "foo.py"], cwd=repo, check=True, capture_output=True)
  proc = subprocess.run(
      ["git", "commit", "-m", "feat: add foo"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 0, proc.stderr


def test_git_hook_rejects_fake_claim_handoff(tmp_path: Path) -> None:
  """staged HANDOFF 含假 claim → commit 非 0。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  (repo / "HANDOFF.md").write_text("## 正在做\n\n- align 已驗真紅\n", encoding="utf-8")
  subprocess.run(["git", "add", "HANDOFF.md"], cwd=repo, check=True, capture_output=True)
  proc = subprocess.run(
      ["git", "commit", "-m", "docs: update handoff"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode != 0


def test_git_hook_rejects_commit_msg_fake_claim(tmp_path: Path) -> None:
  """commit subject 含假 claim 無 VERIFY → 拒。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  proc = subprocess.run(
      ["git", "commit", "--allow-empty", "-m", "fix: 已驗真紅"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode != 0


def test_git_hook_allows_normal_docs_commit(tmp_path: Path) -> None:
  """正常 docs: commit → 過。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  docs = repo / "docs"
  docs.mkdir()
  (docs / "note.md").write_text("# note\n\nplain text\n", encoding="utf-8")
  subprocess.run(["git", "add", "docs/note.md"], cwd=repo, check=True, capture_output=True)
  proc = subprocess.run(
      ["git", "commit", "-m", "docs: add note"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 0, proc.stderr


def test_git_hook_allows_verify_exempt_discussion(tmp_path: Path) -> None:
  """VERIFY-EXEMPT 討論檔 → 過。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  handoffs = repo / "handoffs"
  handoffs.mkdir()
  (handoffs / "discussion.md").write_text(
      "# VERIFY-EXEMPT:doc-example:B3-1\n\n已驗真紅\n",
      encoding="utf-8",
  )
  subprocess.run(["git", "add", "handoffs/discussion.md"], cwd=repo, check=True, capture_output=True)
  proc = subprocess.run(
      ["git", "commit", "-m", "docs: discussion excerpt"],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 0, proc.stderr


# --- Task 3.3 CI workflow ---
# 🔴 三條 workflow 測試已刪除(2026-08-13,使用者定刪除全部 CI 之連帶)。
#   原測 verify_claim.yml 之 YAML 可解析/無 fail-open/pathspec 範圍;
#   該 workflow 連同 governance.yml 已刪(連續全紅、無人查看=零保護純噪音),
#   受測對象不存在 ⇒ 測試一併移除,非「因為紅所以刪」。
#   本檔其餘測試(PreToolUse 判定、git hook、health)測的是本地機制,不受影響。


def test_explicit_files_binary_non_utf8_no_crash(tmp_path: Path) -> None:
  """--files 帶 non-UTF scannable 檔 → exit 2 可診斷，非 traceback。"""
  evil = tmp_path / "docs" / "evil.md"
  evil.parent.mkdir(parents=True)
  evil.write_bytes(b"\xff\xfe\x00")
  proc = subprocess.run(
      [str(PYTHON), str(CLAIM_CHECK), "--files", str(evil)],
      cwd=REPO_ROOT,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 2
  combined = proc.stderr + proc.stdout
  assert "Traceback" not in combined
  assert "cannot read" in combined.lower() or "not valid UTF-8" in combined


def test_explicit_files_non_scannable_skipped_no_crash(tmp_path: Path) -> None:
  """--files 帶 non-scannable binary → 過濾後 no input files exit 2，非 crash。"""
  blob = tmp_path / "blob.bin"
  blob.write_bytes(b"\xff\xfe\x00")
  proc = subprocess.run(
      [str(PYTHON), str(CLAIM_CHECK), "--files", str(blob)],
      cwd=REPO_ROOT,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 2
  assert "Traceback" not in proc.stderr
  assert "no input files" in proc.stderr


# --- Task 3.4 health ---


def test_health_warns_without_hooks_installed(tmp_path: Path) -> None:
  """未 install hooks → WARN + exit 0（附 setup 指引）。"""
  repo = _setup_temp_git_repo(tmp_path)
  proc = _run_health(repo)
  assert proc.returncode == 0
  combined = proc.stderr + proc.stdout
  assert "install_verify_hooks.sh" in combined
  assert "WARN" in combined


def test_preflight_usable_without_hooks_installed(tmp_path: Path) -> None:
  """交付狀態（hooks 未裝）→ preflight exit 0 且印 setup 指引。"""
  repo = _setup_temp_git_repo(tmp_path)
  snap = tmp_path / "preflight_snap.txt"
  proc = subprocess.run(
      ["bash", str(PREFLIGHT), str(snap)],
      cwd=repo,
      capture_output=True,
      text=True,
      check=False,
  )
  assert proc.returncode == 0, proc.stderr + proc.stdout
  combined = proc.stderr + proc.stdout
  assert "install_verify_hooks.sh" in combined
  assert snap.is_file()


def test_health_passes_with_hooks_installed(tmp_path: Path) -> None:
  """裝好 hooks → health exit 0。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  assert _run_health(repo).returncode == 0


def test_mutation_removed_precommit_checker_fails_health(tmp_path: Path) -> None:
  """mutation：砍 pre-commit 內 checker 調用 → health 須轉紅。"""
  repo = _setup_temp_git_repo(tmp_path)
  subprocess.run(["bash", str(INSTALL_HOOKS)], cwd=repo, check=True, capture_output=True)
  assert _run_health(repo).returncode == 0
  hook = repo / "scripts" / "git_hooks" / "pre-commit"
  hook.write_text(
        textwrap.dedent(
            """\
        #!/usr/bin/env bash
        set -u
        echo "noop pre-commit"
        """
        ),
        encoding="utf-8",
    )
  hook.chmod(hook.stat().st_mode | stat.S_IXUSR)
  assert _run_health(repo).returncode == 1


# --- NB-1 verify_task_provenance ---


def _load_verify_task_provenance():
    spec = importlib.util.spec_from_file_location("verify_task_provenance", VERIFY_TASK_PROVENANCE)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_stamp_task_id_hyphen_not_truncated() -> None:
  """task:p0ff3-r2 不被截成 p0ff3。"""
  mod = _load_verify_task_provenance()
  stamp = (
      "RECONCILE-STAMP: codex APPROVED task:p0ff3-r2 "
      "sha256:5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd"
  )
  _, task_id, _ = mod._parse_stamp_fields(stamp)
  assert task_id == "p0ff3-r2"


def test_non_allowlist_p0ff3_r2_requires_committee_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
  """非 allowlist 檔案的 task:p0ff3-r2 仍須 committee_dispatch。"""
  mod = _load_verify_task_provenance()
  audit = tmp_path / "audit.log"
  audit.write_text("", encoding="utf-8")
  monkeypatch.setenv("VERIFY_GATE_COMMITTEE_AUDIT_LOG", str(audit))
  stamp = (
      "RECONCILE-STAMP: codex APPROVED task:p0ff3-r2 "
      "sha256:deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
  )
  code, message = mod.check_stamp_provenance(
      stamp,
      reconcile_file="handoffs/20260702-OTHER-RECONCILE.md",
  )
  assert code == 1
  assert "committee_dispatch" in message
  assert "p0ff3-r2" in message
