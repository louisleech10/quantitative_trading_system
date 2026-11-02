"""子代理交件判準（scripts/subagent_delivered.sh）與 Stop hook（stall_watch_required_check.sh）。

事故（2026-11-02）：已交件之子代理被背景通知喚醒、只回一句文字後，交件行被擠出末 3 行，
原「末 3 行含 SubagentHandback」判準把它當成在外 ⇒ Stop hook 誤擋、監看器誤報 STALL。
紀錄行形狀照真實子代理紀錄（assistant 訊息行、user 通知行、api-request-blob 請求副本）。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DELIVERED = REPO / "scripts" / "subagent_delivered.sh"
HOOK = REPO / "scripts" / "stall_watch_required_check.sh"


def _assistant(*content: dict) -> dict:
    return {"isSidechain": True, "agentId": "a0", "type": "assistant",
            "message": {"model": "m", "type": "message", "role": "assistant", "content": list(content)}}


def _tool_use(name: str, payload: str = "") -> dict:
    return {"type": "tool_use", "id": f"toolu_{name}", "name": name, "input": {"message": payload}}


def _text(t: str) -> dict:
    return {"type": "text", "text": t}


def _notification() -> dict:
    return {"isSidechain": True, "agentId": "a0", "type": "user",
            "message": {"role": "user", "content": "[SYSTEM NOTIFICATION - NOT USER INPUT]\n<task-notification>exit 144</task-notification>"}}


def _tool_result(tid: str) -> dict:
    return {"isSidechain": True, "agentId": "a0", "type": "user",
            "message": {"role": "user", "content": [{"tool_use_id": tid, "type": "tool_result", "content": "ok"}]}}


def _blob_with_history_tool_use() -> dict:
    # 請求副本含歷史中之 assistant tool_use；不是子代理新動作
    return {"type": "api-request-blob", "agentId": "a0",
            "message": {"role": "assistant", "content": [_tool_use("Edit")]}}


def _write(path: Path, rows: list) -> Path:
    # 緊湊分隔符＝真實紀錄之位元組格式（`"name":"X"` 無空格）
    path.write_text("".join((r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, separators=(",", ":")))
                            + "\n" for r in rows),
                    encoding="utf-8")
    return path


def _delivered(path: Path) -> int:
    return subprocess.run(["bash", str(DELIVERED), str(path)], cwd=REPO, capture_output=True).returncode


WORK = [_assistant(_tool_use("Bash")), _tool_result("toolu_Bash")]
HANDBACK = [_assistant(_tool_use("SubagentHandback", "## 回報\n" + "結論與測試。" * 6000)),
            _tool_result("toolu_SubagentHandback")]


def test_woken_by_notification_and_replied_text_only_is_delivered(tmp_path):
    rows = WORK + HANDBACK + [_notification(), _assistant(_text("舊守候被收掉，不需處理。")),
                              _notification(), _assistant(_text("同上。"))]
    assert _delivered(_write(tmp_path / "a.jsonl", rows)) == 0


def test_tool_call_after_handback_is_not_delivered(tmp_path):
    rows = WORK + HANDBACK + [_notification(), _assistant(_text("續做")), _assistant(_tool_use("Bash"))]
    assert _delivered(_write(tmp_path / "a.jsonl", rows)) == 1


def test_no_handback_is_not_delivered(tmp_path):
    assert _delivered(_write(tmp_path / "a.jsonl", WORK + [_assistant(_text("排隊等重型跑"))])) == 1


def test_request_blob_history_after_handback_is_ignored(tmp_path):
    rows = WORK + HANDBACK + [_notification(), _blob_with_history_tool_use(), _assistant(_text("不需處理"))]
    assert _delivered(_write(tmp_path / "a.jsonl", rows)) == 0


def test_second_handback_after_resumed_work_is_delivered(tmp_path):
    rows = WORK + HANDBACK + [_notification()] + WORK + HANDBACK
    assert _delivered(_write(tmp_path / "a.jsonl", rows)) == 0


def test_malformed_line_after_handback_is_ignored(tmp_path):
    rows = WORK + HANDBACK + ['{"type": "assistant", "message": {trunc', _assistant(_text("ok"))]
    assert _delivered(_write(tmp_path / "a.jsonl", rows)) == 0


def test_missing_file_is_not_delivered(tmp_path):
    assert _delivered(tmp_path / "missing.jsonl") == 1


def _hook(tmp_path: Path, rows: list) -> subprocess.CompletedProcess:
    transcript = tmp_path / "sess.jsonl"
    transcript.write_text("", encoding="utf-8")
    sub = tmp_path / "sess" / "subagents"
    sub.mkdir(parents=True)
    _write(sub / "agent-a0.jsonl", rows)
    return subprocess.run(["bash", str(HOOK)], cwd=REPO, capture_output=True, text=True,
                          input=json.dumps({"transcript_path": str(transcript)}))


def test_hook_passes_delivered_agent_woken_by_notification(tmp_path):
    r = _hook(tmp_path, WORK + HANDBACK + [_notification(), _assistant(_text("不需處理"))])
    assert r.returncode == 0, r.stderr


def test_hook_blocks_unwatched_agent_working_after_handback(tmp_path):
    r = _hook(tmp_path, WORK + HANDBACK + [_assistant(_tool_use("Bash"))])
    assert r.returncode == 2
    assert "agent-a0.jsonl" in r.stderr
