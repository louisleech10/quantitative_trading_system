from __future__ import annotations

import json

import pandas as pd

from scripts.build_l65_golden import (
    TEST_INVENTORY_PATH,
    TIER1_DIR,
    TIER2_DIR,
    build_tier1_structure,
    build_tier2_real_shortwindow,
    build_tier2_synthetic,
    collect_existing_l65_tests,
)


def test_l65_golden_tier1_structure_exists() -> None:
    """T0.1: Tier 1 structure baseline should be reproducible and non-empty."""

    build_tier1_structure(TIER1_DIR)

    inventory_path = TIER1_DIR / "column_inventory.json"
    schema_hash_path = TIER1_DIR / "schema_hash.txt"
    assert inventory_path.exists()
    assert schema_hash_path.exists()

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    schema_hash = schema_hash_path.read_text(encoding="utf-8").strip()
    assert len(inventory) == 100
    assert {"name", "dtype", "layer", "source"}.issubset(inventory[0])
    assert len(schema_hash) == 64
    assert all(char in "0123456789abcdef" for char in schema_hash)


def test_l65_golden_tier2a_synthetic_baseline_exists() -> None:
    """T0.1: Tier 2A synthetic baseline should have 1000 rows x 100 columns."""

    build_tier2_synthetic(TIER2_DIR)

    parquet_path = TIER2_DIR / "synthetic_baseline.parquet"
    d_star_path = TIER2_DIR / "d_star_synthetic.json"
    assert parquet_path.exists()
    assert d_star_path.exists()

    frame = pd.read_parquet(parquet_path)
    d_star = json.loads(d_star_path.read_text(encoding="utf-8"))
    assert frame.shape == (1000, 100)
    assert d_star
    assert all(isinstance(value, float) for value in d_star.values())


def test_l65_golden_inventory_exists() -> None:
    """T0.1: test inventory should contain measured L6.5/preprocessing nodeids."""

    if not TEST_INVENTORY_PATH.exists():
        collect_existing_l65_tests(TEST_INVENTORY_PATH)

    content = TEST_INVENTORY_PATH.read_text(encoding="utf-8").strip().splitlines()
    assert content
    assert not content[0].startswith("BLOCKER")
    assert any("l65" in line.lower() or "preprocess" in line.lower() for line in content)


def test_l65_golden_tier2b_real_shortwindow_supported_or_blocked() -> None:
    """T0.1: Tier 2B should either write artifacts or an explicit blocked marker."""

    build_tier2_real_shortwindow("ETHUSDT", "1h", max_rows=2000, max_cols=500, out_dir=TIER2_DIR)

    parquet_path = TIER2_DIR / "ETHUSDT_1h_2000rows.parquet"
    blocked_path = TIER2_DIR / "ETHUSDT_1h_2000rows.BLOCKED"
    assert parquet_path.exists() or blocked_path.exists()

    if blocked_path.exists():
        payload = json.loads(blocked_path.read_text(encoding="utf-8"))
        assert payload["status"] == "blocked-not-pass"
    else:
        frame = pd.read_parquet(parquet_path)
        assert 1500 <= frame.shape[0] <= 2000
        assert frame.shape[1] <= 500
