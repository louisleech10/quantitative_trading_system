"""NOCAP Task 0.2b：寫碼當下擋新增之時間上限（scripts/timeout_write_guard.py）。秒級、不跑重型。"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "timeout_write_guard.py"
_spec = importlib.util.spec_from_file_location("timeout_write_guard", SCRIPT)
g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(g)  # type: ignore[union-attr]


def _edit(path: str, old: str, new: str) -> Dict[str, Any]:
    return {"tool_name": "Edit", "tool_input": {"file_path": str(REPO / path), "old_string": old, "new_string": new}}


def _run(payload: Any) -> int:
    return g.main(json.dumps(payload) if not isinstance(payload, str) else payload)


@pytest.mark.parametrize("line", [
    "    subprocess.run(cmd, timeout=600)",
    "    await asyncio.wait_for(task, 30)",
    "    out = future.result(timeout=5.0)",
    "    signal.alarm(60)",
    "    if time.monotonic() - started > 900:",
    "    deadline = now + 1800",
    "    runner = Runner(out, max_seconds=3600)",
    "timeout 300 python x.py",
])
def test_new_time_cap_in_code_is_blocked(line: str) -> None:
    """運算路徑新增各類時間上限寫法 ⇒ rc 2。"""
    assert _run(_edit("scripts/ffprod_measure.py", "x = 1\n", f"x = 1\n{line}\n")) == 2


def test_unchanged_existing_line_and_none_timeout_pass() -> None:
    """既有行未變（只改他處）⇒ 放行；`timeout=None` 不算上限 ⇒ 放行；非程式檔（.md）不管轄。"""
    old = "a = 1\nsubprocess.run(cmd, timeout=600)\n"
    assert _run(_edit("scripts/ffprod_measure.py", old, old.replace("a = 1", "a = 2"))) == 0
    assert _run(_edit("scripts/ffprod_measure.py", "", "study.optimize(f, timeout=None)\n")) == 0
    assert _run(_edit("docs/NOCAP_SPEC.md", "", "subprocess.run(cmd, timeout=600)\n")) == 0


def test_registered_external_wait_passes() -> None:
    """白名單已登記之 C 類（監看之 sysctl 掛住保險）：於已登記之函式內改寫該呼叫（函式＋被呼叫者＋字面值相同）⇒ 放行；
    同檔未登記之新寫法 ⇒ 擋（NOCAP v2 精確綁定：模組層插入同字面呼叫不再因子字串相符而放行，見 boundary 21）。"""
    path = "handoffs/run_receipts/numview_probes/_watchdog.py"
    old = '            text = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True, timeout=5).stdout\n'
    new = '            text = subprocess.run(["sysctl", "-n", "vm.swapusage"], text=True, capture_output=True, timeout=5).stdout\n'
    assert _run(_edit(path, old, new)) == 0
    assert _run(_edit(path, "", "proc.communicate(timeout=900)\n")) == 2


def test_write_tool_scans_only_added_content(tmp_path: Path) -> None:
    """Write：只掃新內容相對現有檔之增量。"""
    target = REPO / "scripts" / "ffprod_measure.py"
    existing = target.read_text(encoding="utf-8")
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": existing}}
    assert _run(payload) == 0
    payload["tool_input"]["content"] = existing + "\nsubprocess.run(cmd, timeout=60)\n"
    assert _run(payload) == 2


def test_registry_rejects_class_a_and_unreasoned(tmp_path: Path) -> None:
    """登記檔含 A 類、缺理由、或非守衛自身之整檔放行 ⇒ 整份無效（擋）。"""
    base = json.loads(g.REGISTRY.read_text(encoding="utf-8"))
    for bad in ({"path": "scripts/x.py", "contains": "timeout=", "class": "A", "reason": "長運算"},
                {"path": "scripts/x.py", "contains": "timeout=", "class": "B", "reason": ""},
                {"path": "scripts/x.py", "contains": "", "class": "D", "reason": "整檔"}):
        reg = tmp_path / "r.json"
        reg.write_text(json.dumps({"entries": base["entries"] + [bad]}), encoding="utf-8")
        with pytest.raises(ValueError):
            g.load_registry(reg)
    g.load_registry()  # 現行登記檔有效


def test_unreadable_payload_blocks_and_other_tools_pass() -> None:
    assert _run("not json") == 2
    assert _run({"tool_name": "Bash", "tool_input": {"command": "timeout 5 ls"}}) == 0


def test_hook_is_wired_and_fast() -> None:
    """掛於 .claude/settings.json 之 Edit｜Write PreToolUse；單次 < 1 秒。"""
    settings = json.loads((REPO / ".claude" / "settings.json").read_text(encoding="utf-8"))
    cmds = [h["command"] for m in settings["hooks"]["PreToolUse"] if "Edit" in m["matcher"] or "Write" in m["matcher"]
            for h in m["hooks"]]
    assert "bash scripts/timeout_write_guard.sh" in cmds
    payload = json.dumps(_edit("scripts/ffprod_measure.py", "", "x = 1\n"))
    start = time.perf_counter()
    rc = subprocess.run(["bash", str(REPO / "scripts" / "timeout_write_guard.sh")], input=payload, text=True,
                        capture_output=True).returncode
    assert rc == 0 and time.perf_counter() - start < 1.0


def _bash(command: str) -> Dict[str, Any]:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_boundary_21_same_literal_in_unregistered_function_blocked() -> None:
    """NOCAP v2 Task 0.2b②：白名單精確綁定——`_watchdog.py` 已登記之 sysctl `timeout=5` 不放行同檔另一函式之同字面呼叫。"""
    new = "def long_job_runner(cmd):\n    subprocess.run([\"long_job\"], timeout=5)\n"
    assert _run(_edit("handoffs/run_receipts/numview_probes/_watchdog.py", "", new)) == 2


@pytest.mark.parametrize("command", [
    "printf '%s\\n' 'subprocess.run(cmd, timeout=60)' >> scripts/new_runtime.py",
    "sed -i '' 's/a/b/' scripts/new_runtime.py",
    "echo 'timeout 5 ls' | tee scripts/new_helper.sh",
    "perl -pi -e 's/a/b/' momentum/x.py",
    "bash -c \"echo 'x = 1' >> scripts/new_runtime.py\"",  # 內層命令（b1 審碼 r1 CODEX-R1-P1-04）
    "eval \"sed -i '' 's/a/b/' scripts/new_runtime.py\"",
])
def test_boundary_22_bash_write_into_code_file_blocked(command: str) -> None:
    """NOCAP v2 Task 0.2b③：Bash 以重導向／tee／sed -i／perl -i 寫入 .py／.sh ⇒ 擋並要求改用 Edit。"""
    assert _run(_bash(command)) == 2


@pytest.mark.parametrize("command", ["echo hi > /tmp/x.log", "jq . a.json > handoffs/run_receipts/b.json",
                                     "cat scripts/x.py > /dev/null", "timeout 5 ls",
                                     "git commit -q -F - <<'EOF'\nfix: sed -i 寫入 scripts/x.py 與 > scripts/y.sh 之說明\nEOF",
                                     "git commit -m 'echo x >> scripts/x.py 之說明'"])
def test_boundary_23_bash_non_code_write_or_read_allowed(command: str) -> None:
    """Bash 寫入非程式檔（log、收據 JSON）或只讀程式檔 ⇒ 放行。"""
    assert _run(_bash(command)) == 0


def test_boundary_24_precommit_staged_content_scan_rejects(tmp_path: Path) -> None:
    """其他工具（git apply、腳本、他 agent）寫入之未登記逾時呼叫 ⇒ pre-commit 讀暫存區完整內容掃描攔下。"""
    spec = importlib.util.spec_from_file_location("timeout_scan_wg", REPO / "scripts" / "timeout_scan.py")
    scan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scan
    spec.loader.exec_module(scan)  # type: ignore[union-attr]
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "new_job.py").write_text("import subprocess\n\ndef go(cmd):\n    subprocess.run(cmd, timeout=60)\n",
                                                    encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "scripts/new_job.py"], check=True)
    hits = scan.scan_staged(tmp_path)
    assert [(h.path, h.function, h.literal) for h in hits] == [("scripts/new_job.py", "go", "60")]


def _scan_mod() -> Any:
    spec = importlib.util.spec_from_file_location("timeout_scan_wg2", REPO / "scripts" / "timeout_scan.py")
    scan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = scan
    spec.loader.exec_module(scan)  # type: ignore[union-attr]
    return scan


def test_boundary_60_precommit_call_moved_to_other_function_counts_as_new(tmp_path: Path) -> None:
    """pre-commit 之新增判定依綁定：同一行逾時呼叫自 f 搬到 g ⇒ 算新命中（不因整行文字相同而略過；b1 審碼 r1 P1-02）。"""
    scan = _scan_mod()
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for k, v in (("user.email", "t@t"), ("user.name", "t")):
        subprocess.run(["git", "-C", str(tmp_path), "config", k, v], check=True)
    (tmp_path / "scripts").mkdir()
    f = tmp_path / "scripts" / "job.py"
    f.write_text("import subprocess\n\ndef f(cmd):\n    subprocess.run(cmd, timeout=5)\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-q", "-m", "x", "--no-verify"], check=True)
    f.write_text("import subprocess\n\ndef f(cmd):\n    pass\n\ndef g(cmd):\n    subprocess.run(cmd, timeout=5)\n",
                 encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    new = scan.new_vs_head(tmp_path, scan.scan_staged(tmp_path))
    assert [(h.function, h.literal) for h in new] == [("g", "5")]


def test_boundary_61_whole_file_outside_allowlist_rejected() -> None:
    """登記檔 whole_file 列不在守衛／掃描器本身名單 ⇒ 驗證拒收（pre-commit 與守衛共用；b1 審碼 r1 P1-03）。"""
    scan = _scan_mod()
    with pytest.raises(ValueError):
        scan.validate_registry([{"path": "scripts/ffprod_measure.py", "whole_file": True, "class": "D", "reason": "x"}])


def test_boundary_62_cli_reports_stale_registry_entries(tmp_path: Path) -> None:
    """全庫掃描命令列回報過期登記（已無對應命中之列）⇒ rc=1（b1 審碼 r1 P1-06）。"""
    scan = _scan_mod()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "scripts" / "timeout_registry.json").write_text(json.dumps({"entries": [
        {"path": "scripts/a.py", "line": "subprocess.run(cmd, timeout=5)", "class": "C", "reason": "已刪除之舊呼叫"}]}),
        encoding="utf-8")
    assert scan.main(["--repo", str(tmp_path)]) == 1


def test_boundary_25_precommit_hook_invokes_staged_scan() -> None:
    """pre-commit（`core.hooksPath`＝scripts/git_hooks）呼叫 `scripts/timeout_scan.py --staged`。"""
    hook = (REPO / "scripts" / "git_hooks" / "pre-commit").read_text(encoding="utf-8")
    assert "scripts/timeout_scan.py --staged" in hook


def test_mutation_empty_patterns_lets_cap_through(monkeypatch: pytest.MonkeyPatch) -> None:
    """改壞：掃描器之樣式清空 ⇒ 新增之 `subprocess.run(cmd, timeout=600)` 不再被擋（本檔各擋案之鑑別力）。"""
    scan = g._scanner()
    suffixes, _ = scan._load_patterns()
    monkeypatch.setattr(scan, "_load_patterns", lambda *a, **k: (suffixes, []))
    monkeypatch.setattr(g, "_scanner", lambda: scan)
    assert _run(_edit("scripts/ffprod_measure.py", "", "    subprocess.run(cmd, timeout=600)\n")) == 0
