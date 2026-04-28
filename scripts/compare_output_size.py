#!/usr/bin/env python3
"""Compare Phase 0 Layer 6.5 benchmark output sizes against golden baselines."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ensure_project_venv() -> None:
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
    if not venv_python.exists():
        return
    try:
        current_python = Path(sys.executable).absolute()
        target_python = venv_python.absolute()
    except OSError:
        return
    if current_python == target_python:
        return
    os.execv(str(target_python), [str(target_python), str(Path(__file__).resolve())] + sys.argv[1:])


if Path(sys.argv[0]).resolve() == Path(__file__).resolve():
    _ensure_project_venv()

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_l65_golden import _atomic_write_json  # noqa: E402

RESULT_DIR = PROJECT_ROOT / "benchmark_results" / "l65"
STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_BLOCKED = "BLOCKED"
SIZE_DELTA_LIMIT_PCT = 5.0
DSTAR_JSON_LIMIT_BYTES = 5 * 1024 * 1024


@dataclass
class SizeComparison:
    result_file: str
    gate_id: str
    symbol: str
    timeframe: str
    output_path: str
    baseline_path: str
    output_size_bytes: int
    baseline_size_bytes: int
    delta_pct: float
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_file": self.result_file,
            "gate_id": self.gate_id,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "output_path": self.output_path,
            "baseline_path": self.baseline_path,
            "output_size_bytes": self.output_size_bytes,
            "baseline_size_bytes": self.baseline_size_bytes,
            "delta_pct": self.delta_pct,
            "status": self.status,
        }


def _resolve_repo_path(raw_path: Optional[str]) -> Optional[Path]:
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def _load_result(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)
    if not isinstance(payload, dict):
        raise ValueError("Invalid result payload: %s" % path)
    return payload


def _phase_result_files(phase: int, result_dir: Path) -> List[Path]:
    if phase != 0:
        raise ValueError("Only --phase=0 is supported by Task 0.8")
    return sorted(result_dir.glob("phase0_gate_*.json"))


def _baseline_mismatch_reason(entry: Dict[str, Any], baseline_path: Path) -> str:
    baseline_name = baseline_path.name
    rows_per_item = entry.get("rows_per_item")
    input_columns = entry.get("input_columns")

    if baseline_name == "synthetic_baseline.parquet":
        if rows_per_item != 1000 or input_columns != 100:
            return "synthetic workload is not 1000 rows x 100 input columns"
        return ""

    if baseline_name.endswith("rows.parquet"):
        row_token = baseline_name.rsplit("_", 1)[-1].replace("rows.parquet", "")
        try:
            expected_rows = int(row_token)
        except ValueError:
            return ""
        if rows_per_item != expected_rows:
            return "real workload row count does not match %d-row baseline" % expected_rows
    return ""


def _compare_entry(result_file: Path, entry: Dict[str, Any]) -> Tuple[Optional[SizeComparison], str]:
    output_path = _resolve_repo_path(entry.get("output_path"))
    baseline_path = _resolve_repo_path(entry.get("baseline_path"))
    if output_path is None or baseline_path is None:
        return None, "missing_baseline"
    if not output_path.exists() or not baseline_path.exists():
        return None, "missing_baseline"

    mismatch_reason = _baseline_mismatch_reason(entry, baseline_path)
    if mismatch_reason:
        return None, mismatch_reason

    output_size = output_path.stat().st_size
    baseline_size = baseline_path.stat().st_size
    if baseline_size <= 0:
        return None, "invalid_baseline"

    delta_pct = round((output_size - baseline_size) / float(baseline_size) * 100.0, 6)
    status = STATUS_PASS if abs(delta_pct) <= SIZE_DELTA_LIMIT_PCT else STATUS_FAIL
    return SizeComparison(
        result_file=_display_path(result_file),
        gate_id=str(entry.get("gate_id", "unknown")),
        symbol=str(entry.get("symbol", "unknown")),
        timeframe=str(entry.get("timeframe", "unknown")),
        output_path=_display_path(output_path),
        baseline_path=_display_path(baseline_path),
        output_size_bytes=output_size,
        baseline_size_bytes=baseline_size,
        delta_pct=delta_pct,
        status=status,
    ), ""


def _dstar_cache_findings(result_file: Path, entries: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for entry in entries:
        cache_path = _resolve_repo_path(entry.get("dstar_cache_path"))
        if cache_path is None or not cache_path.exists():
            continue
        size_bytes = cache_path.stat().st_size
        findings.append({
            "result_file": _display_path(result_file),
            "gate_id": entry.get("gate_id"),
            "symbol": entry.get("symbol"),
            "timeframe": entry.get("timeframe"),
            "dstar_cache_path": _display_path(cache_path),
            "dstar_json_size_bytes": size_bytes,
            "status": STATUS_PASS if size_bytes <= DSTAR_JSON_LIMIT_BYTES else STATUS_FAIL,
        })
    return findings


def compare_phase_outputs(phase: int, result_dir: Path = RESULT_DIR) -> Dict[str, Any]:
    result_files = _phase_result_files(phase, result_dir)
    comparisons: List[SizeComparison] = []
    skipped_without_baseline = 0
    skipped_incompatible_workload = 0
    dstar_findings: List[Dict[str, Any]] = []

    for result_file in result_files:
        payload = _load_result(result_file)
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            comparison, skip_reason = _compare_entry(result_file, entry)
            if comparison is None:
                if skip_reason == "missing_baseline":
                    skipped_without_baseline += 1
                else:
                    skipped_incompatible_workload += 1
            else:
                comparisons.append(comparison)
        dstar_findings.extend(_dstar_cache_findings(result_file, entries))

    failed_size = [item for item in comparisons if item.status != STATUS_PASS]
    failed_dstar = [item for item in dstar_findings if item.get("status") != STATUS_PASS]

    if not comparisons:
        status = STATUS_BLOCKED
        reason = "no benchmark outputs with matching golden baselines were found"
    elif failed_size or failed_dstar:
        status = STATUS_FAIL
        reason = "size_failures=%d dstar_failures=%d" % (len(failed_size), len(failed_dstar))
    else:
        status = STATUS_PASS
        reason = ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "phase": phase,
        "status": status,
        "timestamp": timestamp,
        "result_files_scanned": len(result_files),
        "comparisons": [item.to_dict() for item in comparisons],
        "dstar_cache_findings": dstar_findings,
        "skipped_without_baseline": skipped_without_baseline,
        "skipped_incompatible_workload": skipped_incompatible_workload,
        "delta_limit_pct": SIZE_DELTA_LIMIT_PCT,
        "dstar_json_limit_bytes": DSTAR_JSON_LIMIT_BYTES,
        "blocking_reason": reason,
    }

    result_dir.mkdir(parents=True, exist_ok=True)
    output_name = "output_size_phase%d_%s.json" % (phase, timestamp)
    output_path = result_dir / output_name
    _atomic_write_json(output_path, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare L6.5 benchmark output sizes")
    parser.add_argument("--phase", type=int, required=True)
    parser.add_argument("--result-dir", default=str(RESULT_DIR))
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    payload = compare_phase_outputs(int(args.phase), Path(args.result_dir))
    if payload.get("status") == STATUS_PASS:
        return 0
    if payload.get("status") == STATUS_BLOCKED:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
