"""list_features V2 query params 一致性測試。"""

from __future__ import annotations

import pytest

from api.services.ic_analysis_service import ICAnalysisService
from momentum.factories import create_feature_library

SYMBOL = "BTCUSDT"
TIMEFRAME = "12h"
# TESTREG Task 4.4：原寫死之 12h run `e53e2290…`（2026-10-03 已刪 ⇒ 恆 skip）改由共用外掛
# `tests/fixtures/tmp_feature_runs_plugin.py` 以真實 K 線於 tmp 物化（`btc_12h_a`；hash 由 fixture 提供）。
RUN_A = "btc_12h_a"


@pytest.mark.ic_run_selector
@pytest.mark.list_features
def test_list_features_v2_matches_load_columns(tmp_feature_run_env) -> None:
    run = tmp_feature_run_env.activate(RUN_A)[RUN_A]
    hash_a = run.config_hash
    library = create_feature_library()
    assert library._registry.get(SYMBOL, TIMEFRAME, hash_a) is not None, f"前提不成立：tmp registry 無 {hash_a}"

    service = ICAnalysisService()
    listed = service.list_features(symbol=SYMBOL, timeframe=TIMEFRAME, config_hash=hash_a)
    loaded = library.load(SYMBOL, TIMEFRAME, config_hash=hash_a)

    list_names = {item["feature_name"] for item in listed}
    load_names = set(loaded.columns)
    # 非空前提：兩邊皆空時集合相等恆真
    assert load_names, "前提不成立：載入之特徵欄為空"
    assert list_names == load_names
