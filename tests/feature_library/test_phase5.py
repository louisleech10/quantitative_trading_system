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
    """In cross_sectional mode, IC service should load features via load_multi.

    驅動生產 `_run_analysis` 之 cross_sectional 分支（給 labels_path 以略過 kline 標籤附加），
    斷言 load_multi 以請求之 symbols／timeframe 被呼叫，且合併後之 (timestamp, _symbol) 框交給
    analyzer.analyze_cross_sectional。
    """
    import asyncio

    from api.models.ic_models import ICAnalyzeRequest
    from api.services.ic_analysis_service import ICAnalysisService

    service = ICAnalysisService()
    ts = pd.date_range("2024-01-01", periods=2, freq="h")
    mock_lib = MagicMock()
    mock_lib.load_multi.return_value = {
        "BTC": pd.DataFrame({"feat_a": [1.0, 2.0], "label": [0.0, 1.0]}, index=ts),
        "ETH": pd.DataFrame({"feat_a": [3.0, 4.0], "label": [1.0, 0.0]}, index=ts),
    }
    service._feature_library = mock_lib
    analyzer = MagicMock()
    analyzer.analyze_cross_sectional.return_value = {"summary_table": []}
    request = ICAnalyzeRequest(
        features_path="unused.h5",
        mode="cross_sectional",
        symbols=["BTC", "ETH"],
        timeframe="1h",
        labels_path="labels.h5",
    )
    service._tasks["t-xs"] = {"task_id": "t-xs", "status": "running", "result": None, "error": None}

    asyncio.run(service._run_analysis("t-xs", analyzer, request, None))

    mock_lib.load_multi.assert_called_once_with(["BTC", "ETH"], "1h", config_hashes=None)
    analyzer.analyze_cross_sectional.assert_called_once()
    kwargs = analyzer.analyze_cross_sectional.call_args.kwargs
    assert kwargs["labels_path"] == "labels.h5"
    assert kwargs["timeframe"] == "1h"
    cross_df = kwargs["features"]
    assert list(cross_df.index.names)[-1] == "_symbol"
    assert sorted(set(cross_df.index.get_level_values("_symbol"))) == ["BTC", "ETH"]
    assert len(cross_df) == 4


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
    mock_registry.find_latest_materialized.side_effect = lambda symbol, timeframe: {
        "symbol": symbol,
        "timeframe": timeframe,
        "config_hash": f"h_{symbol}",
    }

    values = {"h_SYM1": 1.0, "h_SYM2": 2.0}
    mock_reader = MagicMock()
    mock_reader.load_manifest_v2.return_value = {"run_status": "complete"}
    mock_reader.load_run_manifest_v2.return_value = {"run_status": "complete", "feature_naming_version": 2}  # FF-NAME 3.4
    mock_reader.list_features_v2.return_value = ["f"]
    mock_reader.load_columns_v2.side_effect = (
        lambda symbol, timeframe, config_hash, columns, **_kw: pd.DataFrame({"f": [values[config_hash]]})
    )
    mock_reader.load_row_index_v2.return_value = None

    mock_storage = MagicMock()

    library = FeatureLibrary(mock_registry, mock_storage, feature_reader=mock_reader)
    result = library.load_multi(["SYM1", "SYM2"], "1h")
    assert isinstance(result, dict)
    assert "SYM1" in result
    assert "SYM2" in result
    # 每個 symbol 鍵對應其自身 run 之資料（不得錯配）
    assert result["SYM1"]["f"].tolist() == [1.0]
    assert result["SYM2"]["f"].tolist() == [2.0]


def test_cross_sectional_ic_non_empty() -> None:
    """Cross-sectional IC should produce non-NaN value for valid data.

    經生產 `analyze_cross_sectional`；oracle：每時點跨 symbol 之 scipy Spearman 平均（獨立實作），
    以及 feature≡label ⇒ IC=1、feature≡-label ⇒ IC=-1。
    """
    from scipy.stats import spearmanr

    from momentum.factories import create_ic_analyzer

    rng = np.random.default_rng(7)
    ts = pd.date_range("2024-01-01", periods=40, freq="h")
    idx = pd.MultiIndex.from_product([ts, ["AAA", "BBB", "CCC", "DDD"]], names=["timestamp", "_symbol"])
    label = rng.normal(size=len(idx))
    df = pd.DataFrame(
        {"f_same": label, "f_neg": -label, "f_rand": rng.normal(size=len(idx)), "label": label},
        index=idx,
    )
    override = {"ic_train_test_split": False}
    report = create_ic_analyzer(override).analyze_cross_sectional(
        features=df, labels_path=None, config_override=override, timeframe="1h",
    )
    rows = {row["feature_name"]: row for row in report["summary_table"]}
    assert set(rows) == {"f_same", "f_neg", "f_rand"}

    ic_value = rows["f_rand"]["ic_mean"]
    assert not np.isnan(ic_value)
    expected = float(np.mean([spearmanr(g["f_rand"], g["label"])[0] for _, g in df.groupby(level=0)]))
    assert ic_value == pytest.approx(expected, abs=1e-12)
    assert rows["f_same"]["ic_mean"] == pytest.approx(1.0)
    assert rows["f_neg"]["ic_mean"] == pytest.approx(-1.0)


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
