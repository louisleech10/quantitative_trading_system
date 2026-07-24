#!/usr/bin/env python3
"""verify_task_provenance.py — W2/W3 委員派工 provenance 機械檢查。

讀 committee_dispatch JSON 事件（append 於審計 log），驗證 adversarial 輸出檔或
reconcile 戳記 task:<id> 有對應派工事件且輸出檔 hash 相符。誠實邊界：tamper-evident，
非防惡意偽造。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

COMMITTEE_AUDIT_ENV = "VERIFY_GATE_COMMITTEE_AUDIT_LOG"
DEFAULT_COMMITTEE_AUDIT = Path(".claude/gate/audit.log")

# ADV 家族群由治理 SoT 生成(含 grok);事故:寫死 CODEX|COMPOSER 使 grok ADV 檔漏(2026-07-23)。
_SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)
try:
    from governance_families_loader import load_upper as _load_upper

    _ADV_FAMS = "|".join(_load_upper("review_families"))
except Exception as _e:  # noqa: BLE001  fail-closed(委員 A):SoT 讀失敗 → 拋錯拒絕,不 fallback(fallback=fail-open)
    raise RuntimeError(
        f"verify_task_provenance: 治理家族 SoT 讀取失敗(fail-closed): {_e}"
    ) from _e
ADV_PATH_RE = re.compile(rf"^handoffs/.*-ADV-({_ADV_FAMS})\.md$", re.IGNORECASE)
# task id 允許連字號(如 p0ff3-r2);不含連字號會靜默截斷導致 allowlist/審計事件永不匹配
STAMP_TASK_RE = re.compile(r"task:([a-z0-9][a-z0-9-]*)", re.IGNORECASE)
STAMP_FAMILY_RE = re.compile(
    r"^RECONCILE-STAMP:\s*([a-z]+)\s+APPROVED",
    re.IGNORECASE,
)
STAMP_HASH_RE = re.compile(r"sha256:([0-9a-f]+)", re.IGNORECASE)

# 已知 legacy reconcile 戳記（file, family, task_id, body_hash）；非 allowlist 須有 committee_dispatch
LEGACY_STAMP_ALLOWLIST: frozenset[tuple[str, str, str, str]] = frozenset(
    {
        (
            "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
            "composer",
            "bwhprlh0j",
            "86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044",
        ),
        (
            "handoffs/20260701-VERIFYGATE-DELIB-RECONCILE.md",
            "codex",
            "b1eicjnuo",
            "86fe39f51ea28fadde135b0c0fd2f75feeb09b4adffaba8bbcde4fd590140044",
        ),
        # P0-FF-3 設計 reconcile:B4 provenance 制度(2026-07-02)前的真戳記;
        # 07-01 forensics 三方裁定設計 reconcile 有效(捏造的是驗證聲稱,非設計)
        (
            "handoffs/20260630-FF-P0FF3-RECONCILE.md",
            "codex",
            "p0ff3-r2",
            "5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd",
        ),
        (
            "handoffs/20260630-FF-P0FF3-RECONCILE.md",
            "composer",
            "p0ff3-r2",
            "5da75188a4eebde3ef41a054462273e2c9958af27b5ad2b24dd7b1c3f72d93cd",
        ),
    }
)


def _committee_audit_path() -> Path:
    """回傳委員派工審計 log 路徑。"""
    override = os.environ.get(COMMITTEE_AUDIT_ENV)
    return Path(override) if override else DEFAULT_COMMITTEE_AUDIT


def _sha256_file(path: Path) -> str:
    """計算檔案 sha256 hex。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_committee_events(audit_log: Path) -> list[dict]:
    """從審計 log 解析 committee_dispatch / committee_output JSON 行。"""
    if not audit_log.is_file():
        return []
    events: list[dict] = []
    for raw in audit_log.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("event") in {"committee_dispatch", "committee_output"}:
            events.append(obj)
    return events


def _norm_path(path: str) -> str:
    """正規化路徑分隔符。"""
    return path.replace("\\", "/")


def find_dispatch_by_task(task_id: str, events: list[dict]) -> dict | None:
    """依 task_id 找 committee_dispatch 事件。"""
    for event in events:
        if event.get("event") == "committee_dispatch" and event.get("task_id") == task_id:
            return event
    return None


def find_events_by_task(task_id: str, events: list[dict]) -> list[dict]:
    """依 task_id 找所有 committee provenance 事件。"""
    return [event for event in events if event.get("task_id") == task_id]


def find_dispatch_by_output(output_path: str, events: list[dict]) -> dict | None:
    """依 output_path 找 committee_dispatch 事件。"""
    norm = _norm_path(output_path)
    for event in events:
        if event.get("event") == "committee_dispatch" and _norm_path(str(event.get("output_path", ""))) == norm:
            return event
    return None


def _verify_output_hash(output_path: Path, expected_sha256: str) -> tuple[bool, str]:
    """驗證輸出檔存在且 hash 與審計事件一致。"""
    if expected_sha256 == "pending":
        return False, "輸出 hash 仍為 pending（須 register-output 補記）"
    if not output_path.is_file():
        return False, f"輸出檔不存在: {output_path}"
    if not expected_sha256:
        return True, ""
    actual = _sha256_file(output_path)
    if actual != expected_sha256:
        return (
            False,
            f"輸出 hash 不符(可能竄改): 審計 sha256:{expected_sha256[:16]}... "
            f"實際 sha256:{actual[:16]}...",
        )
    return True, ""


def _handoffs_relative(path: str) -> str:
    """取路徑中 handoffs/ 起的相對段（支援絕對路徑）。"""
    norm = _norm_path(path)
    marker = "handoffs/"
    idx = norm.find(marker)
    if idx >= 0:
        return norm[idx:]
    return norm


def _parse_stamp_fields(stamp_line: str) -> tuple[str, str, str]:
    """從戳記行解析 (family, task_id, body_hash)。"""
    family_match = STAMP_FAMILY_RE.search(stamp_line.strip())
    family = family_match.group(1).lower() if family_match else ""
    task_match = STAMP_TASK_RE.search(stamp_line)
    task_id = task_match.group(1) if task_match else ""
    hash_match = STAMP_HASH_RE.search(stamp_line)
    body_hash = hash_match.group(1).lower() if hash_match else ""
    return family, task_id, body_hash


def _event_output_rel(event: dict) -> str:
    """取事件 output_path 的 handoffs 相對路徑。"""
    return _handoffs_relative(str(event.get("output_path", "")))


def _stamp_event_satisfies(
    event: dict,
    *,
    reconcile_file: str,
    body_hash: str,
) -> bool:
    """判斷單一 provenance 事件是否可支撐 reconcile stamp。"""
    output_sha256 = str(event.get("output_sha256", ""))
    if not output_sha256 or output_sha256 == "pending":
        return False
    output_path = str(event.get("output_path", ""))
    rel_file = _handoffs_relative(reconcile_file) if reconcile_file else ""
    if rel_file and _event_output_rel(event) == rel_file:
        return True
    if body_hash and output_sha256.lower() == body_hash.lower():
        return True
    if event.get("event") == "committee_dispatch" and output_path:
        ok, _ = _verify_output_hash(Path(output_path), output_sha256)
        return ok
    return False


def _is_legacy_allowlisted_stamp(reconcile_file: str, stamp_line: str) -> bool:
    """戳記是否在已知 legacy allowlist 內。"""
    if not reconcile_file:
        return False
    rel_file = _handoffs_relative(reconcile_file)
    family, task_id, body_hash = _parse_stamp_fields(stamp_line)
    if not all((rel_file, family, task_id, body_hash)):
        return False
    return (rel_file, family, task_id, body_hash) in LEGACY_STAMP_ALLOWLIST


def check_adversarial_provenance(adversarial_path: str) -> tuple[int, str]:
    """W3：adversarial 路徑命名 + 派工事件 + 輸出 hash。"""
    rel = _handoffs_relative(adversarial_path)
    if not ADV_PATH_RE.match(rel):
        return (
            1,
            f"ERROR: adversarial 路徑不符合命名規則 handoffs/*-ADV-({_ADV_FAMS}).md: "
            f"{adversarial_path}",
        )
    path = Path(adversarial_path)
    if not path.is_file():
        return 1, f"ERROR: adversarial 檔不存在: {adversarial_path}"

    events = parse_committee_events(_committee_audit_path())
    dispatch = find_dispatch_by_output(rel, events)
    if dispatch is None:
        dispatch = find_dispatch_by_output(_norm_path(adversarial_path), events)
    if dispatch is None:
        return (
            1,
            f"ERROR: adversarial 無對應 committee_dispatch 審計事件: {adversarial_path}",
        )

    ok, detail = _verify_output_hash(path, str(dispatch.get("output_sha256", "")))
    if not ok:
        return 1, f"ERROR: adversarial {detail}"
    return 0, ""


def check_stamp_provenance(stamp_line: str, reconcile_file: str = "") -> tuple[int, str]:
    """W2：戳記 task:<id> 須有派工事件且輸出 hash 匹配（legacy allowlist 相容）。

    V-A（2026-07-24）：缺 task:<id> 一律 FAIL（無 grandfather）。
    legacy allowlist 條目皆帶 task，故不需為無 task 開例外。
    """
    task_match = STAMP_TASK_RE.search(stamp_line)
    if not task_match:
        return (
            1,
            "ERROR: 戳記缺 task:<id>，無 provenance 不予採信（legacy 除外）",
        )

    task_id = task_match.group(1)

    if _is_legacy_allowlisted_stamp(reconcile_file, stamp_line):
        return 0, ""

    events = parse_committee_events(_committee_audit_path())
    task_events = find_events_by_task(task_id, events)
    if not task_events:
        return (
            1,
            f"ERROR: 戳記 task:{task_id} 無 committee_dispatch 審計事件"
            f"（非 legacy allowlist 須有派工留痕）",
        )

    if any(
        _stamp_event_satisfies(event, reconcile_file=reconcile_file, body_hash=_parse_stamp_fields(stamp_line)[2])
        for event in task_events
    ):
        return 0, ""

    dispatch = find_dispatch_by_task(task_id, task_events)
    if dispatch is None:
        return 1, f"ERROR: task:{task_id} 無可用 committee_dispatch/committee_output 輸出事件"

    output_path = Path(str(dispatch.get("output_path", "")))
    ok, detail = _verify_output_hash(output_path, str(dispatch.get("output_sha256", "")))
    if not ok:
        return 1, f"ERROR: task:{task_id} {detail}"
    return 1, f"ERROR: task:{task_id} provenance 未指向 reconcile 檔或戳記 hash"


def main(argv: list[str] | None = None) -> int:
    """CLI：check-adversarial / check-stamp。"""
    parser = argparse.ArgumentParser(description="W2/W3 committee dispatch provenance checker")
    sub = parser.add_subparsers(dest="cmd", required=True)

    adv = sub.add_parser("check-adversarial", help="驗證 adversarial 檔 provenance")
    adv.add_argument("path", help="adversarial 檔路徑")

    stamp = sub.add_parser("check-stamp", help="驗證 reconcile 戳記 task provenance")
    stamp.add_argument("stamp_line", help="RECONCILE-STAMP 行全文")
    stamp.add_argument(
        "--file",
        default="",
        help="reconcile 檔路徑（legacy allowlist 比對用）",
    )

    args = parser.parse_args(argv)
    if args.cmd == "check-adversarial":
        code, message = check_adversarial_provenance(args.path)
    else:
        code, message = check_stamp_provenance(args.stamp_line, reconcile_file=args.file)

    if message:
        print(message, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
