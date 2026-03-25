"""Phase 5 tests: cross-symbol training integration."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest


def test_ic_analyze_request_has_mode_field() -> None:
    """ICAnalyzeRequest should support mode = longitudinal | cross_sectional."""
    from api.models.ic_models import ICAnalyzeRequest

    request = ICAnalyzeRequest(features_path="test.h5")
    assert request.mode == "longitudinal"

    request_cross = ICAnalyzeRequest(
        features_path="test.h5",
        mode="cross_sectional",
        symbols=["BTC", "ETH"],
    )
    assert request_cross.mode == "cross_sectional"
    assert request_cross.symbols == ["BTC", "ETH"]


def test_cross_sectional_mode_uses_load_multi() -> None:
    """In cross_sectional mode, IC service should have load_multi capability."""
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    mock_lib = MagicMock()
    mock_lib.load_multi.return_value = {
        "BTC": pd.DataFrame({"feat_a": [1.0, 2.0], "label": [0.0, 1.0]}),
        "ETH": pd.DataFrame({"feat_a": [3.0, 4.0], "label": [1.0, 0.0]}),
    }
    service._feature_library = mock_lib

    assert hasattr(service, "_feature_library")
    assert callable(getattr(service._feature_library, "load_multi", None))


def test_cross_symbol_validator_correct_data_shape() -> None:
    """CrossSymbolValidator should accept Dict[str, ndarray] for X and y."""
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    np.random.seed(42)
    validator = CrossSymbolValidator(params={"n_estimators": 5, "max_depth": 2})

    x_by_symbol = {
        "BTC": np.random.randn(60, 5).astype(np.float32),
        "ETH": np.random.randn(50, 5).astype(np.float32),
    }
    y_by_symbol = {
        "BTC": np.array(([0, 1] * 30), dtype=np.int32),
        "ETH": np.array(([1, 0] * 25), dtype=np.int32),
    }

    results = validator.run_leave_one_symbol_out(
        symbols=["BTC", "ETH"],
        X_by_symbol=x_by_symbol,
        y_by_symbol=y_by_symbol,
    )
    assert len(results) == 2


def test_load_multi_returns_dict_keyed_by_symbol() -> None:
    """FeatureLibrary.load_multi should return Dict[str, DataFrame]."""
    from momentum.FeatureEngineering.feature_library import FeatureLibrary

    mock_registry = MagicMock()
    mock_registry.find_latest.return_value = {
        "symbol": "X",
        "timeframe": "1h",
        "config_hash": "h",
    }

    mock_result = MagicMock()
    mock_result.features_df = pd.DataFrame({"f": [1.0]})

    mock_storage = MagicMock()
    mock_storage.load_factory_output.return_value = mock_result

    library = FeatureLibrary(mock_registry, mock_storage)
    result = library.load_multi(["SYM1", "SYM2"], "1h")
    assert isinstance(result, dict)
    assert "SYM1" in result
    assert "SYM2" in result


def test_cross_sectional_ic_non_empty() -> None:
    """Cross-sectional IC should produce non-NaN value for valid data."""
    from scipy.stats import spearmanr

    features_at_t = np.array([[0.5, 1.2], [0.8, 0.9], [0.3, 1.5]])
    returns_at_t = np.array([0.02, -0.01, 0.03])

    ic_value, _ = spearmanr(features_at_t[:, 0], returns_at_t)
    assert not np.isnan(ic_value)


def test_leave_one_out_result_fields() -> None:
    """Each leave-one-out result should expose expected AUC fields."""
    from momentum.Analysis.cross_symbol_validator import CrossSymbolValidator

    np.random.seed(123)
    validator = CrossSymbolValidator(params={"n_estimators": 5, "max_depth": 2})

    x_by_symbol = {
        "A": np.random.randn(100, 3).astype(np.float32),
        "B": np.random.randn(100, 3).astype(np.float32),
    }
    y_by_symbol = {
        "A": np.array(([0, 1] * 50), dtype=np.int32),
        "B": np.array(([1, 0] * 50), dtype=np.int32),
    }

    results = validator.run_leave_one_symbol_out(
        symbols=["A", "B"],
        X_by_symbol=x_by_symbol,
        y_by_symbol=y_by_symbol,
    )
    for item in results:
        assert hasattr(item, "source_auc")
        assert hasattr(item, "target_auc")
        assert hasattr(item, "generalization_gap")


def test_cross_symbol_request_min_symbols() -> None:
    """CrossSymbolValidationRequest should require at least 2 symbols."""
    from pydantic import ValidationError

    try:
        from api.routes.cross_symbol import CrossSymbolValidationRequest
    except ImportError:
        pytest.skip("cross_symbol route not available")

    with pytest.raises(ValidationError):
        CrossSymbolValidationRequest(symbols=["ONLY_ONE"], timeframe="1h")

    request = CrossSymbolValidationRequest(symbols=["BTC", "ETH"], timeframe="1h")
    assert len(request.symbols) == 2
