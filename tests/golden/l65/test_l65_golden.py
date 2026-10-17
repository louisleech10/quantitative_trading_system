from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.build_l65_golden import (
    TIER1_DIR,
    GoldenBuildError,
    build_tier1_structure,
    build_tier2_real_shortwindow,
    build_tier2_synthetic,
    collect_existing_l65_tests,
)


def test_l65_golden_tier1_structure_exists(tmp_path) -> None:
    """T0.1: Tier 1 structure baseline should be reproducible and non-empty.

    建到 tmp_path 後與入版控之凍結 Tier 1 檔逐位元組比對（原寫法就地覆寫凍結檔再讀回，
    golden 恆等於本次產出、漂移不可見，「reproducible」從未被驗）。
    """

    build_tier1_structure(tmp_path)

    inventory_path = tmp_path / "column_inventory.json"
    schema_hash_path = tmp_path / "schema_hash.txt"
    assert inventory_path.exists()
    assert schema_hash_path.exists()

    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    schema_hash = schema_hash_path.read_text(encoding="utf-8").strip()
    assert len(inventory) == 100
    assert {"name", "dtype", "layer", "source"}.issubset(inventory[0])
    assert len(schema_hash) == 64
    assert all(char in "0123456789abcdef" for char in schema_hash)
    # 可重現：本次產出與凍結 baseline 逐位元組相等
    assert inventory_path.read_bytes() == (TIER1_DIR / "column_inventory.json").read_bytes()
    assert schema_hash_path.read_bytes() == (TIER1_DIR / "schema_hash.txt").read_bytes()


def test_l65_golden_tier2a_synthetic_baseline_exists(tmp_path) -> None:
    """T0.1: Tier 2A synthetic baseline should have 1000 rows x 100 columns."""

    # 寫到 tmp_path：原寫法就地覆寫入版控之 tier2_reduced 檔（弄髒工作區）
    build_tier2_synthetic(tmp_path)

    parquet_path = tmp_path / "synthetic_baseline.parquet"
    d_star_path = tmp_path / "d_star_synthetic.json"
    assert parquet_path.exists()
    assert d_star_path.exists()

    frame = pd.read_parquet(parquet_path)
    d_star = json.loads(d_star_path.read_text(encoding="utf-8"))
    assert frame.shape == (1000, 100)
    assert d_star
    assert all(isinstance(value, float) for value in d_star.values())


@pytest.mark.xfail(
    strict=True,
    raises=GoldenBuildError,
    reason=(
        "生產缺陷：scripts/build_l65_golden.py collect_existing_l65_tests 以 `--collect-only -q` 收集，"
        "與 pytest.ini addopts `-v` 相抵成樹狀輸出，:678 以「含 ::」解析得不到 nodeid ⇒ 寫 BLOCKER 並 raise；"
        "見 白話說明/還沒做的事.md"
    ),
)
def test_l65_golden_inventory_exists(tmp_path) -> None:
    """T0.1: test inventory should contain measured L6.5/preprocessing nodeids.

    以當下之全量 collect 實測產生清單（寫到 tmp_path），不讀入庫之 TEST_INVENTORY_PATH：
    入庫檔會被 tests/conftest.py 之 collect-only hook 以「子集 collect」覆寫（e6cc51a1 即入庫了
    只含 7 支 fracdiff MR 之子集），舊寫法「檔存在就不重收」會讀到過期子集而恆紅。
    """

    out_path = tmp_path / "test_inventory.txt"
    count = collect_existing_l65_tests(out_path)

    content = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert content
    assert count == len(content)
    assert not content[0].startswith("BLOCKER")
    assert any("l65" in line.lower() or "preprocess" in line.lower() for line in content)
    # 實測性：本檔自身之 nodeid 必在全量 collect 之清單內（子集／過期清單會缺）
    assert "tests/golden/l65/test_l65_golden.py::test_l65_golden_inventory_exists" in content


def test_l65_golden_tier2b_real_shortwindow_supported_or_blocked(tmp_path) -> None:
    """T0.1: Tier 2B should either write artifacts or an explicit blocked marker."""

    # 寫到 tmp_path：原寫法就地覆寫入版控之 tier2_reduced 檔、成功時刪入版控之 BLOCKED
    build_tier2_real_shortwindow("ETHUSDT", "1h", max_rows=2000, max_cols=500, out_dir=tmp_path)

    parquet_path = tmp_path / "ETHUSDT_1h_2000rows.parquet"
    blocked_path = tmp_path / "ETHUSDT_1h_2000rows.BLOCKED"
    assert parquet_path.exists() or blocked_path.exists()

    if blocked_path.exists():
        payload = json.loads(blocked_path.read_text(encoding="utf-8"))
        assert payload["status"] == "blocked-not-pass"
    else:
        frame = pd.read_parquet(parquet_path)
        assert 1500 <= frame.shape[0] <= 2000
        assert frame.shape[1] <= 500
