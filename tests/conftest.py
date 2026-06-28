from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import pytest

from momentum.factories import create_kline_storage_manager
from scripts.build_l65_golden import (
    TEST_INVENTORY_PATH,
    make_synthetic_l65_dataset,
    write_test_inventory_from_nodeids,
)
from tests.fixtures.data_manifest import (
    ManifestValidationError,
    verify_kline_entry,
)

FEATURE_KLINE_CACHE_DIR = "data_cache/feature_klines"
FEATURE_KLINE_H5_PATH = Path(FEATURE_KLINE_CACHE_DIR) / "kline_cache.h5"


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


@pytest.fixture
def requires_kline_data() -> Callable[..., pd.DataFrame]:
    """Factory fixture：要求真實 kline；缺檔或列數不足時 pytest.fail（非 skip）。"""

    def _require(
        symbol: str,
        timeframe: str,
        *,
        min_rows: Optional[int] = None,
        verify_manifest: bool = True,
    ) -> pd.DataFrame:
        if not FEATURE_KLINE_H5_PATH.is_file():
            pytest.fail(
                f"requires_kline: missing kline cache file: {FEATURE_KLINE_H5_PATH}"
            )

        if verify_manifest:
            try:
                verify_kline_entry(
                    symbol,
                    timeframe,
                    cache_dir=FEATURE_KLINE_CACHE_DIR,
                    min_rows=min_rows,
                )
            except (ManifestValidationError, KeyError) as exc:
                pytest.fail(f"requires_kline manifest mismatch: {exc}")

        storage = create_kline_storage_manager(cache_dir=FEATURE_KLINE_CACHE_DIR)
        try:
            df = storage.read_klines(symbol, timeframe, validate_continuity=False)
        except Exception as exc:
            pytest.fail(
                f"requires_kline: failed reading {symbol}/{timeframe}: {exc}"
            )

        if df is None or df.empty:
            pytest.fail(
                f"requires_kline: no data for {symbol}/{timeframe} in {FEATURE_KLINE_H5_PATH}"
            )

        effective_min = min_rows if min_rows is not None else 1
        if len(df) < effective_min:
            pytest.fail(
                f"requires_kline: {symbol}/{timeframe} has {len(df)} rows, "
                f"need >= {effective_min}"
            )
        return df

    return _require


def pytest_collection_modifyitems(config: Any, items: List[Any]) -> None:
    """Persist L6.5-related nodeids during the required collect-only gate."""

    if not getattr(config.option, "collectonly", False):
        return
    nodeids = [str(item.nodeid) for item in items]
    write_test_inventory_from_nodeids(nodeids, out_path=Path(TEST_INVENTORY_PATH))
