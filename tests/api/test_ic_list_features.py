"""list_features V2 query params 一致性測試。"""

from __future__ import annotations

import pytest

from api.services.ic_analysis_service import ICAnalysisService
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
HASH_A = "1c4b825498449860a639b0ac37f66d73"


@pytest.mark.ic_run_selector
@pytest.mark.list_features
def test_list_features_v2_matches_load_columns() -> None:
    library = create_feature_library()
    if library._registry.get(SYMBOL, TIMEFRAME, HASH_A) is None:
        pytest.skip(f"missing registry run {HASH_A}")

    service = ICAnalysisService()
    listed = service.list_features(symbol=SYMBOL, timeframe=TIMEFRAME, config_hash=HASH_A)
    loaded = library.load(SYMBOL, TIMEFRAME, config_hash=HASH_A)

    list_names = {item["feature_name"] for item in listed}
    load_names = set(loaded.columns)
    assert list_names == load_names
