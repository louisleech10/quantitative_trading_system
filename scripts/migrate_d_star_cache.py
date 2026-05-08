"""Audit or migrate legacy Layer 6.5 d_star cache files."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from momentum.FeatureEngineering.preprocessing._d_star_cache import CACHE_VERSION  # noqa: E402
from momentum.core.config import is_dstar_legacy_migration_enabled  # noqa: E402


DEFAULT_CACHE_DIR = PROJECT_ROOT / "data_cache" / "feature_preprocessing"
AUDIT_FILE_NAME = "d_star_migration_audit.jsonl"
LEGACY_DEFAULT_NAME = "d_star_default_default.json"


@dataclass(frozen=True)
class MigrationRecord:
    old_path: str
    new_path: str
    decision: str
    reason: str
    timestamp: str
    entry_count: int
    config_hash: str
    data_fingerprint_status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "old_path": self.old_path,
            "new_path": self.new_path,
            "decision": self.decision,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "entry_count": self.entry_count,
            "config_hash": self.config_hash,
            "data_fingerprint_status": self.data_fingerprint_status,
        }


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _entry_count(payload: Optional[Dict[str, Any]]) -> int:
    if not isinstance(payload, dict):
        return 0
    entries = payload.get("entries")
    if isinstance(entries, dict):
        return len(entries)
    return sum(1 for value in payload.values() if isinstance(value, (int, float, dict)))


def _is_legacy_candidate(path: Path, payload: Optional[Dict[str, Any]]) -> bool:
    if path.name == LEGACY_DEFAULT_NAME:
        return True
    if payload is None:
        return path.name.startswith("d_star_") and path.suffix == ".json"
    cache_version = payload.get("cache_version")
    # v2 and v3 are structured cache files; skip them (cold-start on v3 is acceptable)
    if cache_version in (CACHE_VERSION, "v2"):
        return payload.get("symbol") == "default" or payload.get("timeframe") == "default"
    if cache_version is not None:
        # unknown older version — treat as legacy
        return True
    return True


def _new_cache_path(cache_dir: Path, payload: Dict[str, Any]) -> Optional[Path]:
    symbol = payload.get("symbol")
    timeframe = payload.get("timeframe")
    config_hash = str(payload.get("config_hash") or "")
    if not symbol or not timeframe or not config_hash:
        return None
    if symbol == "default" or timeframe == "default":
        return None
    return cache_dir / f"d_star_{symbol}_{timeframe}_{config_hash[:12]}.json"


def _legacy_entries(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries = payload.get("entries")
    if isinstance(entries, dict):
        normalized = {}
        for column, entry in entries.items():
            if isinstance(entry, dict):
                normalized[str(column)] = dict(entry)
            elif isinstance(entry, (int, float)):
                normalized[str(column)] = {"d_star": float(entry)}
        return normalized

    normalized = {}
    for column, value in payload.items():
        if isinstance(value, (int, float)):
            normalized[str(column)] = {"d_star": float(value)}
    return normalized


def _build_v2_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    entries = _legacy_entries(payload)
    return {
        "cache_version": CACHE_VERSION,
        "symbol": payload.get("symbol"),
        "timeframe": payload.get("timeframe"),
        "config_hash": payload.get("config_hash"),
        "adf_threshold": payload.get("adf_threshold"),
        "precision": payload.get("precision"),
        "max_lag": payload.get("max_lag"),
        "weight_threshold": payload.get("weight_threshold"),
        "adf_engine_version": payload.get("adf_engine_version", "statsmodels-v1"),
        "data_fingerprint": payload.get("data_fingerprint", ""),
        "data_fingerprint_status": payload.get("data_fingerprint_status", "unknown"),
        "feature_schema_hash": payload.get("feature_schema_hash", ""),
        "time_range": payload.get("time_range", []),
        "row_count": int(payload.get("row_count", 0) or 0),
        "sample_size": payload.get("sample_size"),
        "nan_policy": payload.get("nan_policy", "dropna"),
        "source_data_version": payload.get("source_data_version", ""),
        "entries": entries,
    }


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.migration.tmp")
    try:
        tmp_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _quarantine_path(cache_dir: Path, path: Path) -> Path:
    quarantine_dir = cache_dir / "legacy_quarantine"
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    return quarantine_dir / f"{path.name}.{_timestamp().replace(':', '')}"


def _record_for_path(cache_dir: Path, path: Path, dry_run: bool) -> MigrationRecord:
    payload = _read_json(path)
    entry_count = _entry_count(payload)
    timestamp = _timestamp()
    if payload is None:
        return MigrationRecord(
            old_path=str(path),
            new_path="",
            decision="quarantined",
            reason="invalid_json" if not dry_run else "dry-run invalid_json",
            timestamp=timestamp,
            entry_count=entry_count,
            config_hash="",
            data_fingerprint_status="unknown",
        )

    new_path = _new_cache_path(cache_dir, payload)
    config_hash = str(payload.get("config_hash") or "")
    data_status = str(payload.get("data_fingerprint_status") or "unknown")
    if new_path is None:
        return MigrationRecord(
            old_path=str(path),
            new_path="",
            decision="quarantined",
            reason="missing_symbol_timeframe_or_config_hash" if not dry_run else "dry-run missing_symbol_timeframe_or_config_hash",
            timestamp=timestamp,
            entry_count=entry_count,
            config_hash=config_hash,
            data_fingerprint_status=data_status,
        )

    if not payload.get("data_fingerprint"):
        return MigrationRecord(
            old_path=str(path),
            new_path=str(new_path),
            decision="quarantined",
            reason="missing_data_fingerprint" if not dry_run else "dry-run missing_data_fingerprint",
            timestamp=timestamp,
            entry_count=entry_count,
            config_hash=config_hash,
            data_fingerprint_status=data_status,
        )

    return MigrationRecord(
        old_path=str(path),
        new_path=str(new_path),
        decision="migrated",
        reason="dry-run would migrate" if dry_run else "migrated_to_v2_schema",
        timestamp=timestamp,
        entry_count=entry_count,
        config_hash=config_hash,
        data_fingerprint_status=data_status,
    )


def audit_legacy_cache_dir(
    cache_dir: Path,
    *,
    dry_run: bool = True,
    write_audit: bool = True,
) -> List[Dict[str, Any]]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    records: List[MigrationRecord] = []

    for path in sorted(cache_dir.glob("d_star_*.json")):
        payload = _read_json(path)
        if not _is_legacy_candidate(path, payload):
            continue
        record = _record_for_path(cache_dir, path, dry_run=dry_run)
        records.append(record)

        if dry_run:
            continue

        if record.decision == "migrated" and record.new_path:
            legacy_payload = _read_json(path)
            if legacy_payload is not None:
                _write_json_atomic(Path(record.new_path), _build_v2_payload(legacy_payload))
            shutil.move(str(path), str(_quarantine_path(cache_dir, path)))
        elif record.decision == "quarantined":
            shutil.move(str(path), str(_quarantine_path(cache_dir, path)))

    record_dicts = [record.to_dict() for record in records]
    if write_audit:
        audit_path = cache_dir / AUDIT_FILE_NAME
        with audit_path.open("a", encoding="utf-8") as handle:
            for record in record_dicts:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return record_dicts


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Audit without moving or migrating files")
    parser.add_argument("--execute", action="store_true", help="Perform migration/quarantine")
    parser.add_argument("--no-audit-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.dry_run and args.execute:
        raise SystemExit("--dry-run and --execute are mutually exclusive")
    dry_run = not args.execute
    if args.execute and not is_dstar_legacy_migration_enabled():
        raise SystemExit("Set FFACT_DSTAR_CACHE_MIGRATE_LEGACY=1 before --execute")

    records = audit_legacy_cache_dir(
        args.cache_dir,
        dry_run=dry_run,
        write_audit=not args.no_audit_write,
    )
    print(
        json.dumps(
            {
                "cache_dir": str(args.cache_dir),
                "dry_run": dry_run,
                "records": len(records),
                "audit_path": str(args.cache_dir / AUDIT_FILE_NAME),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
