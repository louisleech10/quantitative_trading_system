#!/usr/bin/env python3
"""verify_audit_chain.py — W7 輔助：印 receipt 審計鏈對照表（純報告，不 fail-closed）。

讀 verify_audit.log，對每筆 receipt 事件驗證 receipt/log 檔存在且 hash 與審計事件一致。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

AUDIT_LOG_ENV = "VERIFY_GATE_AUDIT_LOG"
RECEIPTS_DIR_ENV = "VERIFY_GATE_RECEIPTS_DIR"
DEFAULT_AUDIT_LOG = Path(".claude/gate/verify_audit.log")
DEFAULT_RECEIPTS_DIR = Path("handoffs/run_receipts")


def _audit_log_path() -> Path:
    """回傳 verify_audit.log 路徑。"""
    override = os.environ.get(AUDIT_LOG_ENV)
    return Path(override) if override else DEFAULT_AUDIT_LOG


def _receipts_dir() -> Path:
    """回傳 receipt 目錄。"""
    override = os.environ.get(RECEIPTS_DIR_ENV)
    return Path(override) if override else DEFAULT_RECEIPTS_DIR


def _sha256_bytes(data: bytes) -> str:
    """計算 bytes sha256 hex。"""
    return hashlib.sha256(data).hexdigest()


def _check_event(event: dict, receipts_dir: Path) -> tuple[str, str, str]:
    """回傳 (receipt_status, log_status, overall_status)。"""
    receipt_id = str(event.get("receipt_id", "?"))
    json_path = receipts_dir / f"{receipt_id}.json"
    log_path = receipts_dir / f"{receipt_id}.log"

    receipt_status = "OK"
    log_status = "OK"
    issues: list[str] = []

    if not json_path.is_file():
        receipt_status = "MISSING"
        issues.append("receipt_missing")
    else:
        actual_receipt_sha = _sha256_bytes(json_path.read_bytes())
        expected_receipt_sha = str(event.get("receipt_sha256", ""))
        if expected_receipt_sha and actual_receipt_sha != expected_receipt_sha:
            receipt_status = "TAMPER"
            issues.append("receipt_tamper")

    if not log_path.is_file():
        log_status = "MISSING"
        issues.append("log_missing")
    else:
        actual_log_sha = _sha256_bytes(log_path.read_bytes())
        expected_log_sha = str(event.get("log_sha256", ""))
        if expected_log_sha and actual_log_sha != expected_log_sha:
            log_status = "TAMPER"
            issues.append("log_tamper")

    overall = "OK" if not issues else "TAMPER"
    return receipt_status, log_status, overall


def run_report(audit_path: Path, receipts_dir: Path) -> int:
    """印審計鏈對照表；永遠回傳 0（純報告）。"""
    if not audit_path.is_file():
        print(f"verify_audit_chain: audit log 不存在: {audit_path}")
        return 0

    print(f"{'receipt_id':<48} {'receipt':<8} {'log':<8} status")
    print("-" * 80)

    tamper_count = 0
    ok_count = 0
    for raw in audit_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") != "receipt":
            continue

        receipt_id = str(event.get("receipt_id", "?"))
        receipt_status, log_status, overall = _check_event(event, receipts_dir)
        if overall == "OK":
            ok_count += 1
        else:
            tamper_count += 1
        print(f"{receipt_id:<48} {receipt_status:<8} {log_status:<8} {overall}")

    print("-" * 80)
    print(f"Summary: OK={ok_count} TAMPER/MISSING={tamper_count}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI 進入點。"""
    parser = argparse.ArgumentParser(description="Print receipt audit chain report (non-blocking)")
    parser.add_argument(
        "--audit-log",
        default=None,
        help="override audit log path (default: VERIFY_GATE_AUDIT_LOG or .claude/gate/verify_audit.log)",
    )
    parser.add_argument(
        "--receipts-dir",
        default=None,
        help="override receipts dir (default: VERIFY_GATE_RECEIPTS_DIR or handoffs/run_receipts)",
    )
    args = parser.parse_args(argv)

    audit_path = Path(args.audit_log) if args.audit_log else _audit_log_path()
    receipts_dir = Path(args.receipts_dir) if args.receipts_dir else _receipts_dir()
    return run_report(audit_path, receipts_dir)


if __name__ == "__main__":
    sys.exit(main())
