from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List

import pandas as pd
import pytest

from scripts.build_l65_golden import (
    TEST_INVENTORY_PATH,
    make_synthetic_l65_dataset,
    write_test_inventory_from_nodeids,
)


@pytest.fixture(scope="session")
def synthetic_l65_dataset() -> pd.DataFrame:
    """Deterministic Layer 6.5 fixture: 1000 rows x 100 mixed-stationarity columns."""

    return make_synthetic_l65_dataset(rows=1000, cols=100, stationary_ratio=0.6)


@pytest.fixture
def ic_first_factory(tmp_path: Path) -> Callable[[str, str], Dict[str, Path]]:
    """Return isolated IC-First scaffold paths for tests."""

    def _factory(symbol: str = "SYNTHETIC", tf: str = "fixture") -> Dict[str, Path]:
        run_dir = tmp_path / "features" / symbol / tf / "ic_first"
        raw_dir = run_dir / "raw"
        processed_dir = run_dir / "processed"
        raw_dir.mkdir(parents=True, exist_ok=True)
        processed_dir.mkdir(parents=True, exist_ok=True)
        return {
            "run_dir": run_dir,
            "raw_dir": raw_dir,
            "processed_dir": processed_dir,
            "selected_path": run_dir / f"ic_selected_features_{symbol}_{tf}.json",
        }

    return _factory


def pytest_collection_modifyitems(config: Any, items: List[Any]) -> None:
    """Persist L6.5-related nodeids during the required collect-only gate."""

    if not getattr(config.option, "collectonly", False):
        return
    nodeids = [str(item.nodeid) for item in items]
    write_test_inventory_from_nodeids(nodeids, out_path=Path(TEST_INVENTORY_PATH))
