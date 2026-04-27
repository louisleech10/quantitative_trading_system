from __future__ import annotations

import json
from pathlib import Path

from scripts.migrate_d_star_cache import AUDIT_FILE_NAME, audit_legacy_cache_dir


def test_d_star_legacy_migration_audit_quarantines_default_cache(tmp_path: Path) -> None:
    legacy_path = tmp_path / "d_star_default_default.json"
    legacy_path.write_text(json.dumps({"L1_close": 0.5}), encoding="utf-8")

    records = audit_legacy_cache_dir(tmp_path, dry_run=True)

    assert len(records) == 1
    record = records[0]
    assert record["old_path"] == str(legacy_path)
    assert record["new_path"] == ""
    assert record["decision"] == "quarantined"
    assert "missing_symbol_timeframe_or_config_hash" in record["reason"]
    assert legacy_path.exists()

    audit_path = tmp_path / AUDIT_FILE_NAME
    audit_lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(audit_lines) == 1
    audit_record = json.loads(audit_lines[0])
    assert audit_record["decision"] == "quarantined"
    assert "reason" in audit_record


def test_d_star_legacy_migration_audit_skips_v2_cache(tmp_path: Path) -> None:
    v2_path = tmp_path / "d_star_ETHUSDT_1h_aaaaaaaaaaaa.json"
    v2_path.write_text(
        json.dumps(
            {
                "cache_version": "v2",
                "symbol": "ETHUSDT",
                "timeframe": "1h",
                "config_hash": "a" * 32,
                "data_fingerprint": "fingerprint",
                "entries": {},
            }
        ),
        encoding="utf-8",
    )

    records = audit_legacy_cache_dir(tmp_path, dry_run=True)

    assert records == []
