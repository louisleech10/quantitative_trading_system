from __future__ import annotations

import hashlib
import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
BASELINE_PATH = BASE_DIR / "baseline_btc_1h.json"
META_PATH = BASE_DIR / "baseline_meta.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_baseline_exists() -> None:
    assert BASELINE_PATH.exists()
    assert BASELINE_PATH.stat().st_size > 0
    assert META_PATH.exists()

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    assert meta["config_hash"] == "a384e6d22ca15fc639757cb3162e7cb3"
    assert meta["baseline_sha256"] == _sha256(BASELINE_PATH)
