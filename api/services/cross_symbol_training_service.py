"""Cross-symbol training service - loads features via FeatureLibrary and feeds CrossSymbolValidator."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from api.core.logging import get_logger
from momentum.factories import create_cross_symbol_validator, create_feature_library


logger = get_logger(__name__)


class CrossSymbolTrainingService:
    """Orchestrates cross-symbol validation using FeatureLibrary as data source."""

    def __init__(self) -> None:
        self._feature_library = create_feature_library()
        self._validator = create_cross_symbol_validator()

    async def run_cross_symbol_validation(
        self,
        symbols: List[str],
        timeframe: str,
        label_column: str = "label",
        feature_columns: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run leave-one-symbol-out validation using FeatureLibrary features."""

        if len(symbols) < 2:
            raise ValueError("cross-symbol validation requires at least 2 symbols")

        multi_features = self._feature_library.load_multi(symbols, timeframe)

        x_by_symbol: Dict[str, np.ndarray] = {}
        y_by_symbol: Dict[str, np.ndarray] = {}

        for symbol, feature_df in multi_features.items():
            if label_column not in feature_df.columns:
                raise ValueError(f"Label column '{label_column}' not found in {symbol}/{timeframe}")

            if feature_columns:
                x_matrix = feature_df[feature_columns].to_numpy()
            else:
                selected_cols = [
                    name
                    for name in feature_df.select_dtypes(include="number").columns
                    if name != label_column
                ]
                if not selected_cols:
                    raise ValueError(f"No numeric feature columns found in {symbol}/{timeframe}")
                x_matrix = feature_df[selected_cols].to_numpy()

            y_vector = feature_df[label_column].to_numpy()
            valid_mask = np.isfinite(x_matrix).all(axis=1) & np.isfinite(y_vector)
            if not np.any(valid_mask):
                raise ValueError(f"No valid samples after NaN filtering in {symbol}/{timeframe}")

            x_by_symbol[symbol] = x_matrix[valid_mask].astype(np.float32)
            y_by_symbol[symbol] = y_vector[valid_mask]

        results = self._validator.run_leave_one_symbol_out(
            symbols=symbols,
            X_by_symbol=x_by_symbol,
            y_by_symbol=y_by_symbol,
        )

        logger.info(
            "Cross-symbol validation completed: symbols=%s timeframe=%s results=%d",
            symbols,
            timeframe,
            len(results),
        )

        return {
            "symbols": symbols,
            "timeframe": timeframe,
            "n_symbols": len(symbols),
            "results": [
                {
                    "source_symbol": item.source_symbol,
                    "target_symbol": item.target_symbol,
                    "source_auc": item.source_auc,
                    "target_auc": item.target_auc,
                    "generalization_gap": item.generalization_gap,
                    "verdict": item.verdict,
                }
                for item in results
            ],
        }
