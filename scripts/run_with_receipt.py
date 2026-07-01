#!/usr/bin/env python3
"""run_with_receipt.py — 包裝任意命令，產 receipt JSON/log 並 append 審計事件。

誠實邊界：careless-proof + tamper-evident，非防惡意偽造；receipt 與 audit 由同一
可寫主體產生。runtime_class 由命令推導（authoritative），--requested-class 僅稽核存檔。
分類器為 router，非 judge。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
DEFAULT_RECEIPTS_DIR = Path("handoffs/run_receipts")
DEFAULT_AUDIT_LOG_PATH = Path(".claude/gate/verify_audit.log")
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"


def _receipts_dir() -> Path:
    """回傳 receipt 目錄（可由 VERIFY_GATE_RECEIPTS_DIR 覆蓋）。"""
    override = os.environ.get(RECEIPTS_DIR_ENV)
    return Path(override) if override else DEFAULT_RECEIPTS_DIR


def _audit_log_path() -> Path:
    """回傳審計 log 路徑（可由 VERIFY_GATE_AUDIT_LOG 覆蓋）。"""
    override = os.environ.get(AUDIT_LOG_ENV)
    return Path(override) if override else DEFAULT_AUDIT_LOG_PATH
TAIL_EXCERPT_MAX_LINES = 40
FEW_NODE_THRESHOLD = 5
HELPER_SMOKE_DURATION_SEC = 5.0
SLOW_RUNTIME_DURATION_SEC = 60.0

RECEIPT_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "receipt_id",
    "claim_id",
    "command",
    "command_sha256",
    "cwd",
    "git_head",
    "tree_dirty",
    "started_at",
    "ended_at",
    "duration_seconds",
    "exit_code",
    "runtime_class",
    "requested_class",
    "pytest_summary",
    "selected_node_ids",
    "markers",
    "passed",
    "failed",
    "skipped",
    "stdout_sha256",
    "stderr_sha256",
    "log_sha256",
    "log_path",
    "tail_excerpt",
)


def _utc_now_iso() -> str:
    """回傳 UTC ISO-8601 時間字串。"""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc_stamp() -> str:
    """回傳 receipt 檔名用 UTC 時間戳。"""
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _sha256_bytes(data: bytes) -> str:
    """計算 bytes 的 sha256 hex。"""
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    """計算 UTF-8 文字 sha256（替換無法編碼字元）。"""
    return _sha256_bytes(text.encode("utf-8", errors="replace"))


def _sha256_json(value: Any) -> str:
    """計算 JSON 序列化後的 sha256（鍵排序、緊湊）。"""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return _sha256_text(payload)


def _run_git(args: list[str]) -> str | None:
    """執行 git 子命令，失敗回 None。"""
    try:
        proc = subprocess.run(
            ["git", *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace").strip()


def _git_head() -> str:
    """取得目前 git HEAD。"""
    return _run_git(["rev-parse", "HEAD"]) or "unknown"


def _git_tree_dirty() -> bool:
    """判斷 worktree 是否有未提交變更。"""
    status = _run_git(["status", "--porcelain"])
    return bool(status)


def _is_pytest_cmd(cmd: list[str]) -> bool:
    """判斷 argv 是否為 pytest 呼叫。"""
    if not cmd:
        return False
    executable = Path(cmd[0]).name
    if executable in {"pytest", "py.test"}:
        return True
    if executable in {"python", "python3"} or executable.endswith("python") or executable.endswith("python3"):
        return any("pytest" in part or part.endswith("py.test") for part in cmd[1:])
    return False


def _extract_flag_value(cmd: list[str], flag: str) -> str:
    """從 argv 取出 -k/-m 等旗標值（支援 -kexpr 與 -k expr）。"""
    values: list[str] = []
    skip_next = False
    for idx, arg in enumerate(cmd):
        if skip_next:
            skip_next = False
            continue
        if arg == flag:
            if idx + 1 < len(cmd):
                values.append(cmd[idx + 1])
            skip_next = True
            continue
        if arg.startswith(f"{flag}="):
            values.append(arg.split("=", 1)[1])
            continue
        if flag in {"-k", "-m"} and arg.startswith(flag) and len(arg) > len(flag):
            values.append(arg[len(flag) :])
    return " ".join(values)


def _extract_markers(cmd: list[str]) -> list[str]:
    """從 pytest -m 旗標解析 marker 名稱。"""
    marker_expr = _extract_flag_value(cmd, "-m")
    if not marker_expr:
        return []
    tokens = re.split(r"\s+and\s+|\s+or\s+|\s+not\s+|\(|\)|\s+", marker_expr)
    return [tok.strip() for tok in tokens if tok.strip() and tok.strip() not in {"and", "or", "not"}]


_NODE_ID_RESULT_RE = re.compile(r"^(.+::\S+)\s+(PASSED|FAILED|SKIPPED|ERROR)\b", re.MULTILINE)


def _extract_node_ids_from_argv(cmd: list[str]) -> list[str]:
    """從 argv 解析 pytest node-id 參數（含 path::test_name）。"""
    node_ids: list[str] = []
    for arg in cmd:
        if "::" in arg and not arg.startswith("-"):
            node_ids.append(arg)
    return node_ids


def parse_pytest_node_ids(output: str) -> list[str]:
    """從 pytest 輸出 PASSED/FAILED/SKIPPED/ERROR 行解析 node id。"""
    seen: set[str] = set()
    node_ids: list[str] = []
    for match in _NODE_ID_RESULT_RE.finditer(output):
        node_id = match.group(1).strip()
        if node_id not in seen:
            seen.add(node_id)
            node_ids.append(node_id)
    return node_ids


def collect_selected_node_ids(cmd: list[str], output: str) -> list[str]:
    """合併 argv 與 pytest 輸出中的 node id（argv 優先、去重保序）。"""
    seen: set[str] = set()
    selected: list[str] = []
    for node_id in _extract_node_ids_from_argv(cmd) + parse_pytest_node_ids(output):
        if node_id not in seen:
            seen.add(node_id)
            selected.append(node_id)
    return selected


def _argv_indicates_mutation(cmd: list[str]) -> bool:
    """判斷 argv 是否指向 mutation 測試（-k 或 node-id）。"""
    k_value = _extract_flag_value(cmd, "-k")
    if k_value and "test_mutation_" in k_value:
        return True
    return any("::test_mutation_" in arg or arg.endswith("::test_mutation_") for arg in cmd)


def _output_indicates_mutation(output: str) -> bool:
    """判斷 pytest 輸出是否含 mutation node id。"""
    return any("::test_mutation_" in node_id for node_id in parse_pytest_node_ids(output))


def parse_pytest_summary(output: str) -> tuple[dict[str, int] | None, str | None]:
    """解析 pytest 摘要行；失敗回 (None, None)。"""
    for line in reversed(output.splitlines()):
        lower = line.lower()
        if "no tests ran" in lower:
            return {"passed": 0, "failed": 0, "skipped": 0}, line.strip()
        if not any(token in lower for token in (" passed", " failed", " skipped", " error")):
            continue
        passed_match = re.search(r"(\d+)\s+passed", line)
        failed_match = re.search(r"(\d+)\s+failed", line)
        skipped_match = re.search(r"(\d+)\s+skipped", line)
        error_match = re.search(r"(\d+)\s+error", line)
        if not any([passed_match, failed_match, skipped_match, error_match]):
            continue
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        skipped = int(skipped_match.group(1)) if skipped_match else 0
        if error_match:
            failed += int(error_match.group(1))
        return {"passed": passed, "failed": failed, "skipped": skipped}, line.strip()
    return None, None


def derive_runtime_class(
    cmd: list[str],
    duration_seconds: float,
    pytest_counts: dict[str, int] | None,
    markers: list[str],
    combined_output: str = "",
) -> str:
    """依命令與執行特徵推導 runtime_class（覆蓋 requested_class）。"""
    k_value = _extract_flag_value(cmd, "-k")
    marker_blob = " ".join(markers)
    if _argv_indicates_mutation(cmd) or _output_indicates_mutation(combined_output):
        return "mutation_runtime"
    if "requires_kline" in marker_blob or "requires_kline" in k_value:
        return "requires_kline_runtime"

    is_pytest = _is_pytest_cmd(cmd)
    if not is_pytest:
        return "static_only"
    if pytest_counts is None:
        return "static_only"

    node_count = pytest_counts["passed"] + pytest_counts["failed"] + pytest_counts["skipped"]
    if node_count == 0:
        return "static_only"
    if duration_seconds < HELPER_SMOKE_DURATION_SEC and node_count <= FEW_NODE_THRESHOLD:
        return "helper_smoke"
    if duration_seconds >= SLOW_RUNTIME_DURATION_SEC:
        return "requires_kline_runtime"
    return "helper_smoke"


def _stream_reader(pipe: Any, chunks: list[bytes], stream: Any) -> None:
    """背景讀 pipe，即時 tee 到 stream 並收集 bytes。"""
    try:
        while True:
            data = pipe.read(4096)
            if not data:
                break
            chunks.append(data)
            stream.buffer.write(data)
            stream.buffer.flush()
    finally:
        pipe.close()


def _run_command(cmd: list[str]) -> tuple[int, bytes, bytes]:
    """執行子命令，即時 tee stdout/stderr 並回傳 exit code 與輸出 bytes。"""
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError:
        msg = f"command not found: {cmd[0]}\n"
        msg_bytes = msg.encode("utf-8")
        sys.stderr.buffer.write(msg_bytes)
        sys.stderr.buffer.flush()
        return 127, b"", msg_bytes
    assert proc.stdout is not None
    assert proc.stderr is not None
    stdout_thread = threading.Thread(
        target=_stream_reader,
        args=(proc.stdout, stdout_chunks, sys.stdout),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_stream_reader,
        args=(proc.stderr, stderr_chunks, sys.stderr),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    exit_code = proc.wait()
    stdout_thread.join()
    stderr_thread.join()
    stdout_bytes = b"".join(stdout_chunks)
    stderr_bytes = b"".join(stderr_chunks)
    return exit_code, stdout_bytes, stderr_bytes


def _tail_excerpt(stdout_text: str, stderr_text: str) -> list[str]:
    """取合併輸出尾端 ≤40 行。"""
    combined = (stdout_text + stderr_text).splitlines()
    return combined[-TAIL_EXCERPT_MAX_LINES:]


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    """寫入 receipt JSON（UTF-8，ensure_ascii=False）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def append_audit_event(
    audit_path: Path,
    *,
    receipt_id: str,
    command_sha256: str,
    receipt_sha256: str,
    log_sha256: str,
    git_head: str,
    exit_code: int,
    runtime_class: str,
    started_at: str,
    ended_at: str,
) -> None:
    """append 一行 JSON 審計事件到 verify_audit.log。"""
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "event": "receipt",
        "receipt_id": receipt_id,
        "emitter": "run_with_receipt.py",
        "command_sha256": command_sha256,
        "receipt_sha256": receipt_sha256,
        "log_sha256": log_sha256,
        "git_head": git_head,
        "exit_code": exit_code,
        "runtime_class": runtime_class,
        "started_at": started_at,
        "ended_at": ended_at,
        "ts": _utc_now_iso(),
    }
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


def validate_receipt_schema(receipt: dict[str, Any]) -> None:
    """斷言 receipt 含全必填欄位；缺欄拋 AssertionError。"""
    missing = [field for field in RECEIPT_REQUIRED_FIELDS if field not in receipt]
    if missing:
        raise AssertionError(f"receipt missing required fields: {missing}")


def main(argv: list[str] | None = None) -> int:
    """CLI 進入點；回傳子命令 exit code。"""
    parser = argparse.ArgumentParser(description="Wrap a command and emit verification receipt.")
    parser.add_argument("--claim-id", required=True, help="Claim identifier for this run")
    parser.add_argument(
        "--requested-class",
        default=None,
        help="Caller-requested runtime class (audit only; not authoritative)",
    )
    parser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Command after -- separator",
    )
    args = parser.parse_args(argv)

    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("run_with_receipt.py: missing command after --", file=sys.stderr)
        return 2

    started_at = _utc_now_iso()
    start_mono = datetime.now(timezone.utc)
    exit_code, stdout_bytes, stderr_bytes = _run_command(cmd)
    ended_at = _utc_now_iso()
    duration_seconds = (datetime.now(timezone.utc) - start_mono).total_seconds()

    stdout_text = stdout_bytes.decode("utf-8", errors="replace")
    stderr_text = stderr_bytes.decode("utf-8", errors="replace")
    combined_text = stdout_text + stderr_text

    pytest_counts, pytest_summary_line = parse_pytest_summary(combined_text)
    markers = _extract_markers(cmd) if _is_pytest_cmd(cmd) else []
    selected_node_ids = collect_selected_node_ids(cmd, combined_text) if _is_pytest_cmd(cmd) else []
    runtime_class = derive_runtime_class(
        cmd, duration_seconds, pytest_counts, markers, combined_text
    )

    passed = pytest_counts["passed"] if pytest_counts else 0
    failed = pytest_counts["failed"] if pytest_counts else 0
    skipped = pytest_counts["skipped"] if pytest_counts else 0

    stamp = _utc_stamp()
    receipt_id = f"{stamp}-{args.claim_id}"
    receipts_dir = _receipts_dir()
    audit_log_path = _audit_log_path()
    json_path = receipts_dir / f"{receipt_id}.json"
    log_path = receipts_dir / f"{receipt_id}.log"

    log_bytes = stdout_bytes + stderr_bytes
    receipts_dir.mkdir(parents=True, exist_ok=True)
    log_path.write_bytes(log_bytes)

    command_sha256 = _sha256_json(cmd)
    stdout_sha256 = _sha256_bytes(stdout_bytes)
    stderr_sha256 = _sha256_bytes(stderr_bytes)
    log_sha256 = _sha256_bytes(log_bytes)
    git_head = _git_head()
    tree_dirty = _git_tree_dirty()
    cwd = os.getcwd()

    receipt: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "receipt_id": receipt_id,
        "claim_id": args.claim_id,
        "command": cmd,
        "command_sha256": command_sha256,
        "cwd": cwd,
        "git_head": git_head,
        "tree_dirty": tree_dirty,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_seconds": duration_seconds,
        "exit_code": exit_code,
        "runtime_class": runtime_class,
        "requested_class": args.requested_class,
        "pytest_summary": pytest_summary_line,
        "selected_node_ids": selected_node_ids,
        "markers": markers,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "stdout_sha256": stdout_sha256,
        "stderr_sha256": stderr_sha256,
        "log_sha256": log_sha256,
        "log_path": str(log_path),
        "tail_excerpt": _tail_excerpt(stdout_text, stderr_text),
    }

    write_receipt(json_path, receipt)
    receipt_sha256 = _sha256_bytes(json_path.read_bytes())
    append_audit_event(
        audit_log_path,
        receipt_id=receipt_id,
        command_sha256=command_sha256,
        receipt_sha256=receipt_sha256,
        log_sha256=log_sha256,
        git_head=git_head,
        exit_code=exit_code,
        runtime_class=runtime_class,
        started_at=started_at,
        ended_at=ended_at,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
