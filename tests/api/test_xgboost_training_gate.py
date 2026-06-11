"""Batch5 round2: XGBoost must not fallback when TrainingReadError is raised."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
import pytest

from api.services.xgboost_batch_service import XGBoostBatchService
from momentum.FeatureEngineering.consumer_gate import TrainingReadError


@pytest.mark.asyncio
async def test_xgboost_does_not_fallback_on_training_read_error() -> None:
    service = XGBoostBatchService.__new__(XGBoostBatchService)
    service.logger = MagicMock()
    service.task_manager = MagicMock()
    service._feature_library = MagicMock()
    service._feature_library.load_for_training.side_effect = TrainingReadError(
        "run_status='partial' is not consumable for strict consumer (allow_partial=False)"
    )
    service.feature_extractor = MagicMock()
    service._get_timeframe_seconds = MagicMock(return_value=3600)
    service._get_kline_data = MagicMock(
        return_value=pd.DataFrame(
            {
                "open": [1.0, 2.0, 3.0],
                "high": [1.0, 2.0, 3.0],
                "low": [1.0, 2.0, 3.0],
                "close": [1.0, 2.0, 3.0],
                "volume": [1.0, 2.0, 3.0],
            }
        )
    )

    case = SimpleNamespace(case_id="c1", timestamp=1_700_000_000)

    await service._run_batch_analysis(
        task_id="t1",
        symbols=["BTCUSDT"],
        timeframe="1h",
        cases=[case],
        indicators=[],
        selected_features=None,
        lookback_bars=10,
        sequence_length=None,
        sequence_feature_mode="aggregate",
        sequence_stride=1,
        aggregation_methods=None,
        multi_scale_windows=None,
        time_series_split=False,
        purge_gap=None,
        embargo_pct=None,
        xgboost_params=None,
        engine="xgboost",
        model_params=None,
        run_comparison=False,
        cv_folds=3,
        top_n_rules=5,
        min_support=10,
    )

    service.feature_extractor.extract_features_from_strategy.assert_not_called()
    service.task_manager.update_status.assert_called()
    failed_call = service.task_manager.update_status.call_args_list[-1]
    assert failed_call.args[1] == "failed"
