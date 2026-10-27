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
    """白名單已登記之 C 類（監看之 sysctl 掛住保險）⇒ 放行；同檔未登記之新寫法 ⇒ 擋。"""
    path = "handoffs/run_receipts/numview_probes/_watchdog.py"
    assert _run(_edit(path, "", 'text = subprocess.run(["sysctl"], capture_output=True, text=True, timeout=5).stdout\n')) == 0
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
