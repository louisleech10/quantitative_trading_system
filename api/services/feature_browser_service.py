"""Feature browser service.

特徵瀏覽器頁面已併入 Feature Factory，本 service 僅保留跨 Symbol Coverage
Matrix 計算（委派 CoverageAnalyzer，只讀 V2 特徵 run）。舊特徵檔載入器
（HDF5 檔、FeatureLibrary／Parquet 舊位址字串、CSV）生產零呼叫者，已隨 FRAMEPATH 刪除。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from api.core.logging import get_logger
from momentum.factories import create_coverage_analyzer


logger = get_logger("api.feature_browser_service")


class FeatureBrowserService:
    """Service layer for feature browser APIs（僅 Coverage Matrix）。"""

    def __init__(self) -> None:
        self._coverage_analyzer = create_coverage_analyzer()

    def get_coverage_matrix(
        self,
        symbols: List[str],
        timeframe: str,
        feature_names: Optional[List[str]] = None,
        feature_base_path: str = "data_cache/features",
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        normalized_features = [item.strip() for item in (feature_names or []) if item and item.strip()]
        return self._coverage_analyzer.compute_symbol_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_names=normalized_features,
            feature_base_path=feature_base_path,
        )

    def get_group_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        feature_base_path: str = "data_cache/features",
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        return self._coverage_analyzer.compute_group_coverage_matrix(
            symbols=normalized_symbols,
            timeframe=timeframe,
            feature_base_path=feature_base_path,
        )

    def get_group_feature_coverage(
        self,
        symbols: List[str],
        timeframe: str,
        group_name: str,
        feature_base_path: str = "data_cache/features",
        top_n: int = 100,
    ) -> Dict[str, Any]:
        normalized_symbols = [item.strip().upper() for item in (symbols or []) if item and item.strip()]
        if len(normalized_symbols) < 2:
            raise ValueError("Coverage Matrix 需至少 2 個 Symbol")

        return self._coverage_analyzer.compute_group_feature_coverage(
            symbols=normalized_symbols,
            timeframe=timeframe,
            group_name=group_name,
            feature_base_path=feature_base_path,
            top_n=top_n,
        )


feature_browser_service = FeatureBrowserService()
